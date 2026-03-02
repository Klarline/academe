"""
Per-stage value metrics for the RAG pipeline.

Answers the question: "Did this stage actually help?"

For each enrichment stage (query rewriting, multi-query, reranking,
self-RAG, decomposition, KG), we log whether the stage:
  - was enabled and ran
  - changed the input  (e.g. rewrite produced a different query)
  - changed the output (e.g. reranking reordered the top-5)
  - how long it took

Over many requests this data lets you:
  1. Prune low-ROI stages from the balanced/deep profiles.
  2. Justify expensive stages in the portfolio ("reranking improved top-5
     ordering in 73% of queries").
  3. Detect regressions ("self-RAG retry rate jumped from 8% to 40%").

The collector is intentionally lightweight — dict-of-counters in memory
with a ``to_dict()`` export.  Hook it into Prometheus counters or
structured logging for production.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StageEvent:
    """Record of a single stage execution within one request."""

    stage: str
    enabled: bool
    ran: bool = False
    changed_input: bool = False
    changed_output: bool = False
    elapsed_ms: float = 0.0
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "enabled": self.enabled,
            "ran": self.ran,
            "changed_input": self.changed_input,
            "changed_output": self.changed_output,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "detail": self.detail,
        }


class RequestMetrics:
    """
    Collects stage-level metrics for a single user request.

    Create one per ``query_with_context`` call (or per graph invocation),
    call ``record_*`` helpers during the pipeline, then ``to_dict()`` at the
    end to get a summary.
    """

    def __init__(self):
        self._events: List[StageEvent] = []
        self._start = time.time()

    # ── Recording helpers ─────────────────────────────────────────────

    def record_query_rewrite(
        self,
        enabled: bool,
        original: str,
        rewritten: str,
        elapsed_ms: float = 0.0,
    ) -> None:
        changed = original != rewritten
        self._events.append(StageEvent(
            stage="query_rewrite",
            enabled=enabled,
            ran=enabled,
            changed_input=changed,
            elapsed_ms=elapsed_ms,
            detail=f"'{original[:30]}' → '{rewritten[:30]}'" if changed else "unchanged",
        ))
        if changed:
            logger.info("Stage metric: query_rewrite changed input")

    def record_multi_query(
        self,
        enabled: bool,
        num_variants: int = 0,
        elapsed_ms: float = 0.0,
    ) -> None:
        self._events.append(StageEvent(
            stage="multi_query",
            enabled=enabled,
            ran=enabled and num_variants > 1,
            changed_input=num_variants > 1,
            elapsed_ms=elapsed_ms,
            detail=f"{num_variants} variants" if num_variants > 1 else "single query",
        ))

    def record_decomposition(
        self,
        enabled: bool,
        num_sub_queries: int = 0,
        elapsed_ms: float = 0.0,
    ) -> None:
        self._events.append(StageEvent(
            stage="decomposition",
            enabled=enabled,
            ran=enabled and num_sub_queries > 1,
            changed_input=num_sub_queries > 1,
            elapsed_ms=elapsed_ms,
            detail=f"{num_sub_queries} sub-queries" if num_sub_queries > 1 else "simple",
        ))

    def record_reranking(
        self,
        enabled: bool,
        top5_before: Optional[List[str]] = None,
        top5_after: Optional[List[str]] = None,
        elapsed_ms: float = 0.0,
    ) -> None:
        changed = (
            top5_before is not None
            and top5_after is not None
            and top5_before != top5_after
        )
        self._events.append(StageEvent(
            stage="reranking",
            enabled=enabled,
            ran=enabled,
            changed_output=changed,
            elapsed_ms=elapsed_ms,
            detail="reordered top-5" if changed else "order unchanged",
        ))
        if changed:
            logger.info("Stage metric: reranking changed top-5 order")

    def record_self_rag(
        self,
        enabled: bool,
        retries: int = 0,
        reformulated: bool = False,
        elapsed_ms: float = 0.0,
    ) -> None:
        self._events.append(StageEvent(
            stage="self_rag",
            enabled=enabled,
            ran=enabled,
            changed_input=reformulated,
            changed_output=retries > 0,
            elapsed_ms=elapsed_ms,
            detail=f"{retries} retries, reformulated={reformulated}",
        ))
        if retries > 0:
            logger.info("Stage metric: self_rag triggered %d retries", retries)

    def record_knowledge_graph(
        self,
        enabled: bool,
        triples_added: int = 0,
        elapsed_ms: float = 0.0,
    ) -> None:
        self._events.append(StageEvent(
            stage="knowledge_graph",
            enabled=enabled,
            ran=enabled and triples_added > 0,
            changed_output=triples_added > 0,
            elapsed_ms=elapsed_ms,
            detail=f"{triples_added} triples added to context",
        ))

    def record_cache(
        self,
        hit: bool,
        elapsed_ms: float = 0.0,
    ) -> None:
        self._events.append(StageEvent(
            stage="cache",
            enabled=True,
            ran=True,
            changed_output=hit,
            elapsed_ms=elapsed_ms,
            detail="HIT" if hit else "MISS",
        ))

    def record_response_grader(
        self,
        verdict: str,
        elapsed_ms: float = 0.0,
    ) -> None:
        self._events.append(StageEvent(
            stage="response_grader",
            enabled=True,
            ran=True,
            changed_output=verdict != "pass",
            elapsed_ms=elapsed_ms,
            detail=verdict,
        ))

    # ── Summaries ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        total_ms = (time.time() - self._start) * 1000
        return {
            "total_ms": round(total_ms, 1),
            "stages": [e.to_dict() for e in self._events],
            "stages_that_changed_input": [
                e.stage for e in self._events if e.changed_input
            ],
            "stages_that_changed_output": [
                e.stage for e in self._events if e.changed_output
            ],
        }

    def log_summary(self) -> None:
        """Emit a single structured log line summarizing stage value."""
        summary = self.to_dict()
        changed_in = summary["stages_that_changed_input"]
        changed_out = summary["stages_that_changed_output"]
        logger.info(
            "Pipeline metrics: total=%.0fms, stages_ran=%d, "
            "changed_input=%s, changed_output=%s",
            summary["total_ms"],
            sum(1 for e in self._events if e.ran),
            changed_in or "none",
            changed_out or "none",
        )


# ---------------------------------------------------------------------------
# Aggregate counters (singleton, survives across requests)
# ---------------------------------------------------------------------------

class AggregateMetrics:
    """
    Running counters aggregated across all requests.

    Thread-safe via simple dict increments (GIL-protected for CPython).
    """

    def __init__(self):
        self._counters: Dict[str, int] = {}

    def inc(self, key: str, amount: int = 1) -> None:
        self._counters[key] = self._counters.get(key, 0) + amount

    def absorb(self, request_metrics: RequestMetrics) -> None:
        """Fold a completed request's metrics into the aggregate counters."""
        for event in request_metrics._events:
            self.inc(f"{event.stage}.enabled", int(event.enabled))
            self.inc(f"{event.stage}.ran", int(event.ran))
            self.inc(f"{event.stage}.changed_input", int(event.changed_input))
            self.inc(f"{event.stage}.changed_output", int(event.changed_output))
        self.inc("requests_total")

    def to_dict(self) -> Dict[str, int]:
        return dict(self._counters)

    def reset(self) -> None:
        self._counters.clear()


_global_metrics = AggregateMetrics()


def get_aggregate_metrics() -> AggregateMetrics:
    """Return the process-wide aggregate metrics singleton."""
    return _global_metrics
