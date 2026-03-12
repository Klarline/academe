"""
Celery task monitoring: Prometheus counters + MongoDB failure logging.

Level 2: Prometheus counters for task success/failure/retry, auto-exposed
at /metrics via the existing Instrumentator. Enables Grafana alerting on
elevated failure rates by task name.

Level 3: Structured failure records written to MongoDB ``task_failures``
collection. Captures task name, args, exception, traceback, and retry
count for offline analysis via RAGAnalytics.

Wired into Celery via signal handlers — no changes to individual task
functions required.
"""

import logging
import os
import time
import traceback as tb_module
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus counters (Level 2)
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter

    TASK_SUCCESS = Counter(
        "academe_celery_task_success_total",
        "Celery tasks completed successfully",
        ["task"],
    )
    TASK_FAILURE = Counter(
        "academe_celery_task_failure_total",
        "Celery tasks that exhausted all retries",
        ["task"],
    )
    TASK_RETRY = Counter(
        "academe_celery_task_retry_total",
        "Celery task retry attempts",
        ["task"],
    )
    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False


TASK_FAILURES_COLLECTION = "task_failures"


# ---------------------------------------------------------------------------
# MongoDB failure logging (Level 3)
# ---------------------------------------------------------------------------

def _log_failure_to_mongodb(
    task_name: str,
    task_id: str,
    args: Optional[tuple],
    kwargs: Optional[dict],
    exception: Optional[Exception],
    traceback_str: str,
    retries: int,
) -> None:
    """Write a structured failure record to MongoDB."""
    try:
        from core.database import get_database
        db = get_database()
        collection = db.get_database()[TASK_FAILURES_COLLECTION]
        collection.insert_one({
            "task_name": task_name,
            "task_id": task_id,
            "args": list(args) if args else [],
            "kwargs": kwargs or {},
            "exception_type": type(exception).__name__ if exception else "Unknown",
            "exception_message": str(exception)[:1000] if exception else "",
            "traceback": traceback_str[:3000],
            "retries": retries,
            "created_at": time.time(),
        })
    except Exception as e:
        logger.warning("Failed to log task failure to MongoDB: %s", e)


# ---------------------------------------------------------------------------
# Celery signal handlers
# ---------------------------------------------------------------------------

def on_task_success(sender=None, **kwargs):
    """Celery task_success signal: increment Prometheus counter."""
    task_name = sender.name if sender else "unknown"
    if _PROM_AVAILABLE:
        TASK_SUCCESS.labels(task=task_name).inc()
    logger.debug("Task succeeded: %s", task_name)


def on_task_failure(sender=None, task_id=None, args=None, kwargs=None,
                    exception=None, traceback=None, **kw):
    """Celery task_failure signal: Prometheus counter + MongoDB record."""
    task_name = sender.name if sender else "unknown"
    retries = sender.request.retries if sender and hasattr(sender, "request") else 0

    if _PROM_AVAILABLE:
        TASK_FAILURE.labels(task=task_name).inc()

    traceback_str = ""
    if traceback is not None:
        try:
            traceback_str = "".join(tb_module.format_tb(traceback))
        except Exception:
            traceback_str = str(traceback)

    _log_failure_to_mongodb(
        task_name=task_name,
        task_id=task_id or "",
        args=args,
        kwargs=kwargs,
        exception=exception,
        traceback_str=traceback_str,
        retries=retries,
    )
    logger.error("Task failed: %s (id=%s, retries=%d): %s",
                 task_name, task_id, retries, exception)


def on_task_retry(sender=None, reason=None, **kwargs):
    """Celery task_retry signal: increment Prometheus counter."""
    task_name = sender.name if sender else "unknown"
    if _PROM_AVAILABLE:
        TASK_RETRY.labels(task=task_name).inc()
    logger.warning("Task retrying: %s (reason: %s)", task_name, reason)


def connect_signals():
    """
    Register all signal handlers with Celery.

    Call this once from celery_config.py after app creation.
    Idempotent — safe to call multiple times.
    """
    from celery.signals import task_success, task_failure, task_retry

    task_success.connect(on_task_success)
    task_failure.connect(on_task_failure)
    task_retry.connect(on_task_retry)
    logger.info("Celery monitoring signals connected (Prometheus=%s, MongoDB=enabled)",
                _PROM_AVAILABLE)


# ---------------------------------------------------------------------------
# Metrics reader for analytics / monitoring
# ---------------------------------------------------------------------------

def get_celery_metrics() -> Dict[str, Any]:
    """
    Return process-global Celery task metrics from Prometheus counters.

    Safe to call from RAGAnalytics or any monitoring endpoint.
    Returns zeros if prometheus_client is not installed.
    """
    if not _PROM_AVAILABLE:
        return {
            "tasks": {},
            "total_success": 0,
            "total_failure": 0,
            "total_retry": 0,
        }

    task_names = set()
    for metric in [TASK_SUCCESS, TASK_FAILURE, TASK_RETRY]:
        for sample in metric.collect()[0].samples:
            task_label = dict(sample.labels).get("task")
            if task_label:
                task_names.add(task_label)

    tasks = {}
    for name in sorted(task_names):
        tasks[name] = {
            "success": int(TASK_SUCCESS.labels(task=name)._value.get()),
            "failure": int(TASK_FAILURE.labels(task=name)._value.get()),
            "retry": int(TASK_RETRY.labels(task=name)._value.get()),
        }

    total_success = sum(t["success"] for t in tasks.values())
    total_failure = sum(t["failure"] for t in tasks.values())
    total_retry = sum(t["retry"] for t in tasks.values())

    return {
        "tasks": tasks,
        "total_success": total_success,
        "total_failure": total_failure,
        "total_retry": total_retry,
    }


# ---------------------------------------------------------------------------
# Queue depth protection
# ---------------------------------------------------------------------------

# Maximum tasks allowed per queue before rejecting new dispatches.
# Prevents unbounded Redis memory growth under load.
MAX_QUEUE_DEPTH = int(os.environ.get("CELERY_MAX_QUEUE_DEPTH", "500"))


class QueueFullError(Exception):
    """Raised when a Celery queue exceeds MAX_QUEUE_DEPTH."""
    pass


def get_queue_depth(queue_name: str = "default") -> int:
    """
    Return the number of pending tasks in a Celery queue.

    Reads the Redis list length directly (Celery stores queues as lists).
    Returns 0 if Redis is unreachable.
    """
    try:
        import redis as redis_lib
        broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        r = redis_lib.from_url(broker_url, socket_connect_timeout=2)
        return r.llen(queue_name) or 0
    except Exception as e:
        logger.warning("Could not read queue depth for '%s': %s", queue_name, e)
        return 0


def check_queue_before_dispatch(queue_name: str = "default") -> None:
    """
    Raise QueueFullError if the queue exceeds MAX_QUEUE_DEPTH.

    Call this before dispatching a task to prevent unbounded growth.
    No-op if Redis is unreachable (fail-open: allow the dispatch).
    """
    depth = get_queue_depth(queue_name)
    if depth >= MAX_QUEUE_DEPTH:
        raise QueueFullError(
            f"Queue '{queue_name}' has {depth} pending tasks "
            f"(limit: {MAX_QUEUE_DEPTH}). Try again later."
        )
