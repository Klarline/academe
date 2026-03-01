"""
Retrieval-Only Evaluator for Academe (Level 1 Evaluation).

Measures retrieval quality without LLM: P@k, R@k, MRR.
Fast feedback loop for testing hybrid search, reranking, chunking improvements.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set, Tuple

from core.vectors import SemanticSearchService, HybridSearchService
from core.evaluation.test_data import TEST_QUESTIONS, create_test_dataset

logger = logging.getLogger(__name__)


def _chunk_id(doc_id: str, chunk_index: int) -> str:
    """Standard chunk ID format."""
    return f"{doc_id}_{chunk_index}"


def _content_overlap_score(chunk_content: str, ground_truth: str) -> float:
    """Jaccard-like overlap: |intersection| / |ground_truth|."""
    if not ground_truth or not chunk_content:
        return 0.0
    gt_words = set(ground_truth.lower().split())
    chunk_words = set(chunk_content.lower().split())
    if not gt_words:
        return 0.0
    overlap = len(gt_words & chunk_words) / len(gt_words)
    return min(1.0, overlap)


def _is_relevant_by_content(
    chunk_content: str,
    ground_truth: str,
    threshold: float = 0.15,
) -> bool:
    """Chunk is relevant if it overlaps with ground_truth above threshold."""
    return _content_overlap_score(chunk_content, ground_truth) >= threshold


class RetrievalEvaluator:
    """
    Evaluate retrieval quality (P@k, R@k, MRR) without LLM.

    Use for fast iteration on hybrid search, reranking, chunking.
    """

    def __init__(
        self,
        search_service: Optional[SemanticSearchService] = None,
        relevance_threshold: float = 0.15,
    ):
        self.search_service = search_service or SemanticSearchService()
        self.relevance_threshold = relevance_threshold

    def _get_relevant_ids(
        self,
        query_data: Dict[str, Any],
        user_chunks: Optional[List[Tuple[str, int]]] = None,
    ) -> Set[str]:
        """
        Get set of relevant chunk IDs for a query.

        Uses relevant_chunk_ids from test data if present,
        else derives from content overlap with ground_truth (requires user_chunks).
        """
        # Explicit IDs: [{"document_id": "x", "chunk_index": 0}, ...]
        explicit = query_data.get("relevant_chunk_ids")
        if explicit:
            return {
                _chunk_id(r["document_id"], r["chunk_index"])
                for r in explicit
                if isinstance(r, dict)
            }
        if isinstance(explicit, list) and all(isinstance(x, int) for x in explicit):
            # [0, 1, 2] with document_id
            doc_id = query_data.get("document_id", "")
            return {_chunk_id(doc_id, i) for i in explicit}

        return set()

    def _evaluate_query(
        self,
        query: str,
        user_id: str,
        results: List[Any],
        ground_truth: str,
        relevant_ids: Set[str],
        k_values: List[int] = [5, 10],
    ) -> Dict[str, float]:
        """
        Compute metrics for a single query.

        If relevant_ids is empty, uses content overlap with ground_truth.
        """
        metrics = {}

        # Build relevance for each result
        def is_relevant(result) -> bool:
            vec_id = _chunk_id(result.chunk.document_id, result.chunk.chunk_index)
            if relevant_ids:
                return vec_id in relevant_ids
            return _is_relevant_by_content(
                result.chunk.content, ground_truth, self.relevance_threshold
            )

        # Precision@k
        for k in k_values:
            top_k = results[:k]
            rel_in_k = sum(1 for r in top_k if is_relevant(r))
            metrics[f"precision@{k}"] = rel_in_k / k if k > 0 else 0.0

        # Recall@k (only when we have explicit relevant IDs; else skip)
        if relevant_ids:
            total_relevant = len(relevant_ids)
            for k in k_values:
                top_k = results[:k]
                rel_in_k = sum(1 for r in top_k if is_relevant(r))
                metrics[f"recall@{k}"] = rel_in_k / total_relevant if total_relevant else 0.0
        else:
            for k in k_values:
                metrics[f"recall@{k}"] = None  # Unknown without ground-truth IDs

        # MRR
        for i, r in enumerate(results):
            if is_relevant(r):
                metrics["mrr"] = 1.0 / (i + 1)
                break
        else:
            metrics["mrr"] = 0.0

        return metrics

    def evaluate(
        self,
        user_id: str,
        test_queries: Optional[List[Dict[str, Any]]] = None,
        limit: Optional[int] = None,
        k_values: List[int] = [5, 10],
        use_reranking: bool = True,
    ) -> Dict[str, Any]:
        """
        Run retrieval evaluation.

        Args:
            user_id: User ID (must have indexed documents)
            test_queries: Override default TEST_QUESTIONS
            limit: Max queries to evaluate
            k_values: K for P@k and R@k
            use_reranking: Use reranking when available

        Returns:
            Aggregated metrics and per-query details
        """
        queries = test_queries or create_test_dataset(limit=limit)
        if limit:
            queries = queries[:limit]

        all_metrics = []
        latencies = []

        for i, q in enumerate(queries):
            question = q.get("question", "")
            ground_truth = q.get("ground_truth", "")
            relevant_ids = self._get_relevant_ids(q)

            start = time.perf_counter()
            if isinstance(self.search_service, HybridSearchService):
                if use_reranking:
                    results = self.search_service.hybrid_search_with_reranking(
                        query=question,
                        user_id=user_id,
                        top_k=max(k_values),
                    )
                else:
                    results = self.search_service.hybrid_search(
                        query=question,
                        user_id=user_id,
                        top_k=max(k_values),
                    )
            elif use_reranking:
                results = self.search_service.search_with_reranking(
                    query=question,
                    user_id=user_id,
                    top_k=max(k_values) * 2,
                    rerank_top_k=max(k_values),
                )
            else:
                results = self.search_service.search(
                    query=question,
                    user_id=user_id,
                    top_k=max(k_values),
                )
            latencies.append(time.perf_counter() - start)

            m = self._evaluate_query(
                question, user_id, results, ground_truth, relevant_ids, k_values
            )
            m["query"] = question[:50]
            all_metrics.append(m)

        # Aggregate
        n = len(all_metrics)
        agg = {}
        for k in k_values:
            agg[f"precision@{k}"] = sum(m[f"precision@{k}"] for m in all_metrics) / n
            recall_vals = [m[f"recall@{k}"] for m in all_metrics if m.get(f"recall@{k}") is not None]
            agg[f"recall@{k}"] = sum(recall_vals) / len(recall_vals) if recall_vals else None
        agg["mrr"] = sum(m["mrr"] for m in all_metrics) / n
        agg["avg_latency_ms"] = sum(latencies) / n * 1000
        agg["num_queries"] = n

        return {
            "metrics": agg,
            "per_query": all_metrics,
        }
