"""
Deterministic fallback chain for graceful degradation.

When an external service fails (OpenAI unavailable, reranker timeout, Pinecone
down), the system should degrade predictably rather than raise an unhandled
exception or silently return garbage.

Usage
-----
Wrap any fallible call with ``fallback()``:

    result = fallback(
        primary=lambda: openai_llm.invoke(prompt),
        fallbacks=[
            lambda: gemini_llm.invoke(prompt),   # try alternate provider
        ],
        default="I could not process your request.",  # last resort
        label="response_grader",                      # for logging
    )

Or use the ``@with_fallback`` decorator for simpler cases.

Design
------
- Each stage has an explicit **ordered** list of alternatives.
- The chain always terminates (``default`` is required when no fallback list
  is provided).
- Every attempt and its outcome are logged — feed these into stage metrics.
"""

import functools
import logging
import time
from typing import Any, Callable, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackExhausted(Exception):
    """All fallback options failed."""


def fallback(
    primary: Callable[[], T],
    *,
    fallbacks: Optional[List[Callable[[], T]]] = None,
    default: Optional[T] = None,
    label: str = "unknown",
    timeout_ms: Optional[int] = None,
) -> T:
    """
    Try ``primary``, then each fallback in order, then return ``default``.

    Args:
        primary:     The preferred callable.
        fallbacks:   Ordered list of alternative callables.
        default:     Value returned when every callable fails.
                     If None and everything fails, ``FallbackExhausted`` is raised.
        label:       Human-readable name for logging.
        timeout_ms:  Optional per-attempt wall-clock timeout (in milliseconds).
                     If exceeded, the attempt counts as failed.

    Returns:
        The first successful return value.

    Raises:
        FallbackExhausted: when every option (including default) is exhausted.
    """
    attempts = [("primary", primary)] + [
        (f"fallback_{i+1}", fn) for i, fn in enumerate(fallbacks or [])
    ]

    last_error: Optional[Exception] = None

    for tag, fn in attempts:
        start = time.time()
        try:
            result = fn()
            elapsed = (time.time() - start) * 1000
            if timeout_ms and elapsed > timeout_ms:
                logger.warning(
                    "[%s/%s] succeeded but exceeded timeout (%.0fms > %dms), accepting result",
                    label, tag, elapsed, timeout_ms,
                )
            else:
                logger.debug("[%s/%s] succeeded in %.0fms", label, tag, elapsed)
            return result
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            last_error = exc
            logger.warning(
                "[%s/%s] failed in %.0fms: %s", label, tag, elapsed, exc
            )

    if default is not None:
        logger.info("[%s] all attempts failed, using default", label)
        return default

    raise FallbackExhausted(
        f"[{label}] all {len(attempts)} attempts failed. Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# Decorator variant
# ---------------------------------------------------------------------------

def with_fallback(
    default: Any = None,
    label: Optional[str] = None,
):
    """
    Decorator that wraps a function with a try/except returning ``default``.

    Simpler than ``fallback()`` for functions that only need one alternative.

    Usage::

        @with_fallback(default=[], label="reranker")
        def rerank(query, results):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            fn_label = label or fn.__qualname__
            start = time.time()
            try:
                result = fn(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                logger.debug("[%s] succeeded in %.0fms", fn_label, elapsed)
                return result
            except Exception as exc:
                elapsed = (time.time() - start) * 1000
                logger.warning(
                    "[%s] failed in %.0fms: %s — returning default",
                    fn_label, elapsed, exc,
                )
                return default
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Pre-built fallback strategies for the main failure modes
# ---------------------------------------------------------------------------

class FallbackStrategies:
    """
    Canonical degradation strategies for each external dependency.

    These are factory methods that return the right ``default`` value for
    each stage so callers don't have to guess.
    """

    @staticmethod
    def llm_grading_default() -> dict:
        """When the grader LLM is unreachable, auto-pass the response."""
        return {"verdict": "pass", "reason": "grader_unavailable"}

    @staticmethod
    def llm_rewrite_default(original_query: str) -> str:
        """When rewriting fails, use the original query unchanged."""
        return original_query

    @staticmethod
    def reranker_default(results: list) -> list:
        """When the cross-encoder is unavailable, return results as-is."""
        return results

    @staticmethod
    def vector_search_default() -> list:
        """When Pinecone is unreachable, return empty results."""
        return []

    @staticmethod
    def cache_default() -> None:
        """When cache lookup/write fails, treat as miss."""
        return None

    @staticmethod
    def kg_default() -> str:
        """When KG traversal fails, return empty context."""
        return ""
