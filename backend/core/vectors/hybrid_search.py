"""Hybrid search combining BM25 and vector similarity for Academe."""

import logging
import re
from typing import List, Optional, Dict, Any, Tuple

from core.vectors.search import SemanticSearchService
from core.models.document import DocumentSearchResult, DocumentChunk, Document
from core.documents.storage import ChunkRepository, DocumentRepository

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer for BM25 - lowercase, split on non-alphanumeric."""
    text = text.lower().strip()
    tokens = re.findall(r"\b\w+\b", text)
    return tokens if tokens else [""]  # BM25Okapi needs non-empty


class HybridSearchService:
    """
    Combines BM25 (keyword) and vector search for better retrieval.

    BM25 handles exact keyword matching (e.g. "PCA", "eigenvalue");
    vectors handle semantic similarity. Uses lazy index building with
    invalidation on document upload.
    """

    def __init__(
        self,
        vector_search: Optional[SemanticSearchService] = None,
        chunk_repo: Optional[ChunkRepository] = None,
        doc_repo: Optional[DocumentRepository] = None,
        weight_bm25: float = 0.3,
        weight_vector: float = 0.7,
    ):
        self.vector_search = vector_search or SemanticSearchService()
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.doc_repo = doc_repo or DocumentRepository()
        self.weight_bm25 = weight_bm25
        self.weight_vector = weight_vector

        # In-memory BM25 index cache: user_id -> (BM25Okapi, vec_id_list)
        self._bm25_cache: Dict[str, tuple] = {}

    def index_document(
        self,
        document: Document,
        chunks: List[DocumentChunk],
    ) -> Tuple[bool, str]:
        """Index document in vector DB and invalidate BM25 cache."""
        success, message = self.vector_search.index_document(document, chunks)
        if success:
            self.invalidate_user_index(document.user_id)
        return success, message

    def invalidate_user_index(self, user_id: str) -> None:
        """Invalidate BM25 index for user (call on document upload/delete)."""
        if user_id in self._bm25_cache:
            del self._bm25_cache[user_id]
            logger.info(f"Invalidated BM25 index for user {user_id}")

    def _build_bm25_index(self, user_id: str) -> Optional[tuple]:
        """Build BM25 index for user's chunks. Returns (bm25, vec_ids) or None."""
        if not BM25_AVAILABLE:
            return None

        chunks = self.chunk_repo.get_user_chunks(user_id)
        if not chunks:
            logger.debug(f"No chunks for user {user_id}, skipping BM25")
            return None

        corpus = [_tokenize(c.content) for c in chunks]
        vec_ids = [f"{c.document_id}_{c.chunk_index}" for c in chunks]

        # Filter empty token lists (BM25Okapi fails on empty)
        valid_indices = [i for i, t in enumerate(corpus) if t and t != [""]]
        if not valid_indices:
            return None

        corpus = [corpus[i] for i in valid_indices]
        vec_ids = [vec_ids[i] for i in valid_indices]

        bm25 = BM25Okapi(corpus)
        self._bm25_cache[user_id] = (bm25, vec_ids)
        logger.info(f"Built BM25 index for user {user_id}: {len(vec_ids)} chunks")
        return (bm25, vec_ids)

    def _get_bm25_scores(
        self,
        user_id: str,
        query: str,
    ) -> Dict[str, float]:
        """Get BM25 scores for query. Keys are vec_ids."""
        cached = self._bm25_cache.get(user_id)
        if cached is None:
            cached = self._build_bm25_index(user_id)
        if cached is None:
            return {}

        bm25, vec_ids = cached
        query_tokens = _tokenize(query)
        if not query_tokens or query_tokens == [""]:
            return {}

        scores = bm25.get_scores(query_tokens)
        return {vec_ids[i]: float(scores[i]) for i in range(len(vec_ids))}

    def hybrid_search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        retrieval_multiplier: int = 2,
        filter_document_id: Optional[str] = None,
        filter_has_code: Optional[bool] = None,
        filter_has_equations: Optional[bool] = None,
        score_threshold: float = 0.2,
    ) -> List[DocumentSearchResult]:
        """
        Perform hybrid search combining BM25 and vector similarity.

        Args:
            query: Search query
            user_id: User ID
            top_k: Number of results to return
            retrieval_multiplier: Fetch top_k * multiplier from vector search for fusion
            filter_*: Optional filters passed to vector search
            score_threshold: Minimum vector score

        Returns:
            Fused and re-ranked search results
        """
        # 1. Vector search (retrieve more for fusion)
        vector_results = self.vector_search.search(
            query=query,
            user_id=user_id,
            top_k=top_k * retrieval_multiplier,
            filter_document_id=filter_document_id,
            filter_has_code=filter_has_code,
            filter_has_equations=filter_has_equations,
            score_threshold=score_threshold,
        )

        if not vector_results:
            return []

        # 2. BM25 scores (if available)
        bm25_scores = self._get_bm25_scores(user_id, query)

        if not bm25_scores:
            # Fallback: vector-only, return top_k
            return vector_results[:top_k]

        # 3. Normalize scores for fusion
        max_vec = max(r.score for r in vector_results) or 1.0
        max_bm25 = max(bm25_scores.values()) or 1.0

        for result in vector_results:
            vec_id = f"{result.chunk.document_id}_{result.chunk.chunk_index}"
            vec_norm = result.score / max_vec
            bm25_norm = bm25_scores.get(vec_id, 0) / max_bm25
            result.score = (
                self.weight_vector * vec_norm + self.weight_bm25 * bm25_norm
            )

        # 4. Re-sort by fused score
        vector_results.sort(key=lambda r: r.score, reverse=True)

        # 5. Update ranks
        for i, result in enumerate(vector_results[:top_k]):
            result.rank = i + 1

        return vector_results[:top_k]

    def hybrid_search_with_reranking(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        retrieval_multiplier: int = 4,
        **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Hybrid search followed by cross-encoder reranking.

        Retrieves more candidates with hybrid search, then reranks
        for best precision.
        """
        results = self.hybrid_search(
            query=query,
            user_id=user_id,
            top_k=top_k * retrieval_multiplier,
            retrieval_multiplier=2,
            **kwargs
        )
        if len(results) <= top_k:
            return results
        return self.vector_search.rerank_results(query, results, top_k=top_k)
