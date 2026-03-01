"""
Query decomposition for complex multi-part questions.

Splits compound questions into atomic sub-queries, retrieves for each
independently, and merges/deduplicates the results.  This handles
multi-hop reasoning that single retrieval would miss.

Example:
  "Compare PCA and t-SNE, and when would you use each?"
  → ["What is PCA and how does it work?",
     "What is t-SNE and how does it work?",
     "When to use PCA vs t-SNE?"]
"""

import logging
from typing import Callable, Dict, List, Optional

from core.config import get_openai_llm
from core.models.document import DocumentSearchResult

logger = logging.getLogger(__name__)


class QueryDecomposer:
    """
    Decompose complex queries into simpler sub-queries.

    Uses a fast LLM to decide whether decomposition is needed and
    to generate sub-queries.
    """

    def __init__(self, llm=None):
        self._llm = llm

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_openai_llm(model="gpt-4o-mini", temperature=0.0)
        return self._llm

    def decompose(self, query: str, max_sub_queries: int = 4) -> List[str]:
        """
        Split a query into sub-queries if it's complex.

        Returns the original query alone if it's already simple.

        Args:
            query: User's question.
            max_sub_queries: Maximum number of sub-queries.

        Returns:
            List of sub-queries (always includes the original).
        """
        prompt = f"""Analyze this question and decide if it needs to be broken into simpler sub-questions for search.

Question: {query}

If the question is simple (single topic, single ask), respond with:
SIMPLE

If it's complex (multiple topics, comparison, multi-step), respond with sub-questions, one per line:
1. <sub-question>
2. <sub-question>
...

Maximum {max_sub_queries} sub-questions. Each must be self-contained."""

        try:
            response = self.llm.invoke(prompt)
            text = response.content.strip()

            if text.upper().startswith("SIMPLE"):
                return [query]

            sub_queries = [query]
            for line in text.split("\n"):
                cleaned = line.strip().lstrip("0123456789.-) ").strip()
                if cleaned and len(cleaned) > 5 and cleaned != query:
                    sub_queries.append(cleaned)
                if len(sub_queries) > max_sub_queries:
                    break

            if len(sub_queries) > 1:
                logger.info(
                    f"Decomposed '{query[:40]}' into {len(sub_queries)} sub-queries"
                )
            return sub_queries

        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}")
            return [query]


def retrieve_with_decomposition(
    query: str,
    search_fn: Callable[..., List[DocumentSearchResult]],
    decomposer: QueryDecomposer,
    top_k: int = 5,
    **search_kwargs,
) -> List[DocumentSearchResult]:
    """
    Decompose → retrieve per sub-query → merge and deduplicate.

    Args:
        query: User's question.
        search_fn: Search function (accepts query= and top_k= kwargs).
        decomposer: QueryDecomposer instance.
        top_k: Final number of results to return.
        **search_kwargs: Passed through to search_fn.

    Returns:
        Merged, deduplicated, score-sorted results.
    """
    sub_queries = decomposer.decompose(query)

    if len(sub_queries) <= 1:
        return search_fn(query=query, top_k=top_k, **search_kwargs)

    all_results: Dict[str, DocumentSearchResult] = {}

    per_query_k = max(3, top_k // len(sub_queries) + 1)

    for sq in sub_queries:
        results = search_fn(query=sq, top_k=per_query_k, **search_kwargs)
        for r in results:
            key = f"{r.chunk.document_id}_{r.chunk.chunk_index}"
            if key not in all_results or r.score > all_results[key].score:
                all_results[key] = r

    merged = sorted(all_results.values(), key=lambda r: r.score, reverse=True)

    for i, r in enumerate(merged):
        r.rank = i + 1

    return merged[:top_k]
