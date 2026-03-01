"""
Adaptive retrieval: adjust search strategy based on query type.

Different queries need different retrieval approaches:
- Definition queries ("What is X?") → high precision, boost BM25
- Comparison queries ("X vs Y") → diverse sources, more results
- Procedural queries ("How to X?") → sequential context, larger chunks
- General → balanced hybrid search
"""

import logging
import re
from typing import List, Optional

from core.models.document import DocumentSearchResult
from core.vectors.hybrid_search import HybridSearchService
from core.vectors.search import SemanticSearchService

logger = logging.getLogger(__name__)


class QueryType:
    DEFINITION = "definition"
    COMPARISON = "comparison"
    PROCEDURAL = "procedural"
    CODE = "code"
    GENERAL = "general"


def classify_query(query: str) -> str:
    """Classify query into a retrieval-relevant type."""
    q = query.lower().strip()

    if re.match(r"(what is|what are|define|explain|describe)\b", q):
        return QueryType.DEFINITION

    if re.search(r"\bvs\.?\b|versus|difference between|compare|comparing", q):
        return QueryType.COMPARISON

    if re.match(r"(how to|how do|how can|steps to|implement|write)\b", q):
        if re.search(r"(code|implement|write|python|function|class)\b", q):
            return QueryType.CODE
        return QueryType.PROCEDURAL

    if re.search(r"(code|implement|write.*function|python|snippet)\b", q):
        return QueryType.CODE

    return QueryType.GENERAL


class AdaptiveRetriever:
    """
    Adapt retrieval strategy based on query type.

    Wraps HybridSearchService and adjusts parameters per query type
    for better precision/recall tradeoffs.
    """

    def __init__(
        self,
        hybrid_search: Optional[HybridSearchService] = None,
    ):
        self.hybrid_search = hybrid_search or HybridSearchService()

    def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        use_reranking: bool = True,
        **kwargs,
    ) -> List[DocumentSearchResult]:
        """
        Retrieve with query-appropriate strategy.

        Returns results adapted for the query type.
        """
        query_type = classify_query(query)
        logger.info(f"Query type: {query_type} for '{query[:50]}'")

        if query_type == QueryType.DEFINITION:
            return self._retrieve_definition(query, user_id, top_k, use_reranking, **kwargs)
        elif query_type == QueryType.COMPARISON:
            return self._retrieve_comparison(query, user_id, top_k, use_reranking, **kwargs)
        elif query_type == QueryType.CODE:
            return self._retrieve_code(query, user_id, top_k, use_reranking, **kwargs)
        elif query_type == QueryType.PROCEDURAL:
            return self._retrieve_procedural(query, user_id, top_k, use_reranking, **kwargs)
        else:
            return self._retrieve_general(query, user_id, top_k, use_reranking, **kwargs)

    def _retrieve_definition(
        self, query, user_id, top_k, use_reranking, **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Definition queries: fewer, high-precision results with BM25 boost.

        "What is PCA?" → exact term matching matters.
        """
        original_bm25 = self.hybrid_search.weight_bm25
        original_vec = self.hybrid_search.weight_vector
        try:
            self.hybrid_search.weight_bm25 = 0.4
            self.hybrid_search.weight_vector = 0.6
            if use_reranking:
                return self.hybrid_search.hybrid_search_with_reranking(
                    query=query,
                    user_id=user_id,
                    top_k=min(top_k, 3),
                    **kwargs,
                )
            return self.hybrid_search.hybrid_search(
                query=query,
                user_id=user_id,
                top_k=min(top_k, 3),
                **kwargs,
            )
        finally:
            self.hybrid_search.weight_bm25 = original_bm25
            self.hybrid_search.weight_vector = original_vec

    def _retrieve_comparison(
        self, query, user_id, top_k, use_reranking, **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Comparison queries: more diverse results from multiple sources.

        "PCA vs t-SNE" → need chunks covering both topics.
        """
        if use_reranking:
            results = self.hybrid_search.hybrid_search_with_reranking(
                query=query,
                user_id=user_id,
                top_k=top_k * 2,
                **kwargs,
            )
        else:
            results = self.hybrid_search.hybrid_search(
                query=query,
                user_id=user_id,
                top_k=top_k * 2,
                **kwargs,
            )
        return self._diversify(results, top_k)

    def _retrieve_code(
        self, query, user_id, top_k, use_reranking, **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Code queries: filter for code-containing chunks.

        "Write PCA from scratch" → prefer chunks with code blocks.
        """
        kwargs["filter_has_code"] = True
        if use_reranking:
            code_results = self.hybrid_search.hybrid_search_with_reranking(
                query=query, user_id=user_id, top_k=top_k, **kwargs,
            )
        else:
            code_results = self.hybrid_search.hybrid_search(
                query=query, user_id=user_id, top_k=top_k, **kwargs,
            )

        # Fall back to general search if not enough code chunks
        if len(code_results) < 2:
            kwargs.pop("filter_has_code", None)
            fallback = self.hybrid_search.hybrid_search(
                query=query, user_id=user_id, top_k=top_k, **kwargs,
            )
            seen = {(r.chunk.document_id, r.chunk.chunk_index) for r in code_results}
            for r in fallback:
                if (r.chunk.document_id, r.chunk.chunk_index) not in seen:
                    code_results.append(r)
                if len(code_results) >= top_k:
                    break

        return code_results[:top_k]

    def _retrieve_procedural(
        self, query, user_id, top_k, use_reranking, **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Procedural queries: standard search (steps often in sequential chunks).
        """
        if use_reranking:
            return self.hybrid_search.hybrid_search_with_reranking(
                query=query, user_id=user_id, top_k=top_k, **kwargs,
            )
        return self.hybrid_search.hybrid_search(
            query=query, user_id=user_id, top_k=top_k, **kwargs,
        )

    def _retrieve_general(
        self, query, user_id, top_k, use_reranking, **kwargs
    ) -> List[DocumentSearchResult]:
        """General queries: balanced hybrid search."""
        if use_reranking:
            return self.hybrid_search.hybrid_search_with_reranking(
                query=query, user_id=user_id, top_k=top_k, **kwargs,
            )
        return self.hybrid_search.hybrid_search(
            query=query, user_id=user_id, top_k=top_k, **kwargs,
        )

    def _diversify(
        self,
        results: List[DocumentSearchResult],
        top_k: int,
    ) -> List[DocumentSearchResult]:
        """
        Select diverse results: spread across different documents/sections.

        Greedy maximal marginal relevance (MMR)-style selection.
        """
        if len(results) <= top_k:
            return results

        selected = [results[0]]
        remaining = results[1:]

        while len(selected) < top_k and remaining:
            best_idx = 0
            best_diversity = -1

            for i, candidate in enumerate(remaining):
                min_overlap = min(
                    self._content_similarity(candidate, s) for s in selected
                )
                diversity = candidate.score * (1 - 0.5 * min_overlap)
                if diversity > best_diversity:
                    best_diversity = diversity
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        for i, r in enumerate(selected):
            r.rank = i + 1
        return selected

    def _content_similarity(
        self,
        a: DocumentSearchResult,
        b: DocumentSearchResult,
    ) -> float:
        """Rough content similarity via word overlap."""
        words_a = set(a.chunk.content.lower().split())
        words_b = set(b.chunk.content.lower().split())
        union = words_a | words_b
        if not union:
            return 0.0
        return len(words_a & words_b) / len(union)
