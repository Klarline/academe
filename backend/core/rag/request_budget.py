"""
Request budget: caps total LLM calls and latency for a single user query.

Every LLM-calling stage (query rewriting, decomposition, self-RAG, response
grading, refinement loops) checks the budget before making a call.  When the
budget is exhausted the stage gracefully skips or returns its best-effort
result instead of making another call.

This prevents worst-case cost/latency explosions in the cyclic graph where
a query could otherwise trigger 10+ LLM calls.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RequestBudget:
    """
    Tracks resource consumption for a single user request.

    Passed through WorkflowState and into RAG pipeline calls.
    Mutable — callers call ``use_llm_call()`` before each LLM invocation
    and ``can_call_llm()`` to check remaining capacity.
    """

    max_llm_calls: int = 8
    max_retries: int = 3
    max_latency_ms: int = 30_000

    llm_calls_used: int = field(default=0, repr=False)
    retries_used: int = field(default=0, repr=False)
    _start_time: float = field(default_factory=time.time, repr=False)

    # ── queries ───────────────────────────────────────────────────────

    def can_call_llm(self) -> bool:
        """True if we still have LLM call headroom *and* time budget."""
        if self.llm_calls_used >= self.max_llm_calls:
            logger.debug("Budget: LLM call limit reached (%d/%d)",
                         self.llm_calls_used, self.max_llm_calls)
            return False
        if self.elapsed_ms >= self.max_latency_ms:
            logger.debug("Budget: latency limit reached (%dms/%dms)",
                         self.elapsed_ms, self.max_latency_ms)
            return False
        return True

    def can_retry(self) -> bool:
        return self.retries_used < self.max_retries and self.can_call_llm()

    # ── mutations ─────────────────────────────────────────────────────

    def use_llm_call(self) -> bool:
        """Record one LLM call. Returns False if budget was already spent."""
        if not self.can_call_llm():
            return False
        self.llm_calls_used += 1
        return True

    def use_retry(self) -> bool:
        if not self.can_retry():
            return False
        self.retries_used += 1
        return True

    # ── introspection ─────────────────────────────────────────────────

    @property
    def elapsed_ms(self) -> int:
        return int((time.time() - self._start_time) * 1000)

    @property
    def remaining_llm_calls(self) -> int:
        return max(0, self.max_llm_calls - self.llm_calls_used)

    def to_dict(self) -> dict:
        return {
            "llm_calls_used": self.llm_calls_used,
            "max_llm_calls": self.max_llm_calls,
            "retries_used": self.retries_used,
            "max_retries": self.max_retries,
            "elapsed_ms": self.elapsed_ms,
            "max_latency_ms": self.max_latency_ms,
        }

    def __str__(self) -> str:
        return (
            f"Budget(llm={self.llm_calls_used}/{self.max_llm_calls}, "
            f"retries={self.retries_used}/{self.max_retries}, "
            f"elapsed={self.elapsed_ms}ms/{self.max_latency_ms}ms)"
        )
