"""
Self-RAG / Corrective RAG: verify retrieval quality and retry if needed.

After retrieving context, an LLM judge evaluates whether the context is
sufficient to answer the query.  If not, the query is reformulated and
retrieval is retried (up to max_retries).

This catches retrieval failures early instead of letting the generation
LLM hallucinate from irrelevant context.
"""

import logging
from typing import List, Optional, Callable

from core.config import get_openai_llm
from core.models.document import DocumentSearchResult

logger = logging.getLogger(__name__)


class RetrievalVerifier:
    """
    Judge whether retrieved context is sufficient to answer a query.

    Uses a fast LLM (gpt-4o-mini) to make a binary decision with a
    confidence score, plus an optional reformulated query for retry.
    """

    def __init__(self, llm=None):
        self._llm = llm

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_openai_llm(model="gpt-4o-mini", temperature=0.0)
        return self._llm

    def verify(
        self,
        query: str,
        results: List[DocumentSearchResult],
        min_results: int = 1,
    ) -> "VerificationResult":
        """
        Check if retrieved context can answer the query.

        Args:
            query: User's question.
            results: Retrieved search results.
            min_results: Minimum results to consider retrieval valid.

        Returns:
            VerificationResult with verdict and optional reformulation.
        """
        if len(results) < min_results:
            return VerificationResult(
                sufficient=False,
                reason="too_few_results",
                reformulated_query=query,
            )

        context_preview = "\n".join(
            r.chunk.content[:200] for r in results[:5]
        )

        prompt = f"""You are a retrieval quality judge. Decide whether the retrieved context
is sufficient to answer the user's question.

Question: {query}

Retrieved context (truncated):
{context_preview}

Respond with EXACTLY one of these formats:
SUFFICIENT
INSUFFICIENT: <brief reason>
REFORMULATE: <better search query>

Only respond INSUFFICIENT or REFORMULATE if the context is clearly
irrelevant or missing key information needed to answer the question."""

        try:
            response = self.llm.invoke(prompt)
            text = response.content.strip()

            if text.startswith("SUFFICIENT"):
                return VerificationResult(sufficient=True)
            elif text.startswith("REFORMULATE:"):
                new_query = text[len("REFORMULATE:"):].strip()
                return VerificationResult(
                    sufficient=False,
                    reason="reformulate",
                    reformulated_query=new_query if new_query else query,
                )
            else:
                reason = text[len("INSUFFICIENT:"):].strip() if text.startswith("INSUFFICIENT:") else text
                return VerificationResult(
                    sufficient=False,
                    reason=reason,
                    reformulated_query=query,
                )
        except Exception as e:
            logger.warning(f"Retrieval verification failed: {e}")
            return VerificationResult(sufficient=True)


class VerificationResult:
    __slots__ = ("sufficient", "reason", "reformulated_query")

    def __init__(
        self,
        sufficient: bool,
        reason: str = "",
        reformulated_query: str = "",
    ):
        self.sufficient = sufficient
        self.reason = reason
        self.reformulated_query = reformulated_query

    def __repr__(self):
        return f"VerificationResult(sufficient={self.sufficient}, reason='{self.reason}')"


class SelfRAGController:
    """
    Orchestrates retrieval → verify → retry loop.

    Wraps any search function and adds self-correction on top.
    """

    def __init__(
        self,
        verifier: Optional[RetrievalVerifier] = None,
        max_retries: int = 2,
    ):
        self.verifier = verifier or RetrievalVerifier()
        self.max_retries = max_retries

    def search_with_verification(
        self,
        query: str,
        search_fn: Callable[..., List[DocumentSearchResult]],
        **search_kwargs,
    ) -> List[DocumentSearchResult]:
        """
        Search, verify, and retry if context is insufficient.

        Args:
            query: User's question.
            search_fn: The search function to call (accepts query= kwarg).
            **search_kwargs: Additional arguments passed to search_fn.

        Returns:
            Best search results after verification.
        """
        current_query = query
        best_results: List[DocumentSearchResult] = []

        for attempt in range(1 + self.max_retries):
            results = search_fn(query=current_query, **search_kwargs)

            if not results:
                logger.info(f"Self-RAG attempt {attempt+1}: no results for '{current_query[:40]}'")
                if attempt == 0 and current_query != query:
                    current_query = query
                    continue
                return best_results

            if not best_results or len(results) > len(best_results):
                best_results = results

            verdict = self.verifier.verify(current_query, results)
            logger.info(f"Self-RAG attempt {attempt+1}: {verdict}")

            if verdict.sufficient:
                return results

            if verdict.reformulated_query and verdict.reformulated_query != current_query:
                current_query = verdict.reformulated_query
                logger.info(f"Self-RAG reformulated: '{current_query[:60]}'")
            else:
                break

        return best_results
