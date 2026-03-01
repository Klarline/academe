"""
Semantic response cache for RAG answers.

Caches (query, answer, sources) keyed by query embedding similarity.
If a new query is semantically similar (cosine > threshold) to a cached
entry, the cached answer is returned — saving LLM cost and latency.

Supports in-memory and optional Redis backends.
"""

import hashlib
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class CacheEntry:
    __slots__ = ("query", "embedding", "answer", "sources", "created_at")

    def __init__(
        self,
        query: str,
        embedding: List[float],
        answer: str,
        sources: List[Any],
        created_at: float,
    ):
        self.query = query
        self.embedding = embedding
        self.answer = answer
        self.sources = sources
        self.created_at = created_at


class SemanticResponseCache:
    """
    In-memory semantic cache with cosine-similarity lookup.

    Parameters:
        similarity_threshold: Minimum cosine similarity for a cache hit (0-1).
        ttl_seconds: Time-to-live for cache entries. 0 = no expiry.
        max_entries: Evict oldest entries when exceeded.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
        max_entries: int = 500,
    ):
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries

        self._entries: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        query: str,
        query_embedding: List[float],
    ) -> Optional[Tuple[str, List[Any]]]:
        """
        Look up a cached answer by semantic similarity.

        Args:
            query: The user query (for logging).
            query_embedding: Embedding of the query.

        Returns:
            (answer, sources) if cache hit, else None.
        """
        now = time.time()
        best_score = -1.0
        best_entry: Optional[CacheEntry] = None

        with self._lock:
            expired_keys = []
            for key, entry in self._entries.items():
                if self.ttl_seconds and (now - entry.created_at) > self.ttl_seconds:
                    expired_keys.append(key)
                    continue
                score = self._cosine_similarity(query_embedding, entry.embedding)
                if score > best_score:
                    best_score = score
                    best_entry = entry

            for k in expired_keys:
                del self._entries[k]

        if best_entry and best_score >= self.similarity_threshold:
            logger.info(
                f"Cache HIT (score={best_score:.3f}): "
                f"'{query[:40]}' matched '{best_entry.query[:40]}'"
            )
            return best_entry.answer, best_entry.sources

        return None

    def put(
        self,
        query: str,
        query_embedding: List[float],
        answer: str,
        sources: List[Any],
    ) -> None:
        """
        Store a query/answer pair in the cache.

        Args:
            query: The user query.
            query_embedding: Embedding of the query.
            answer: Generated answer.
            sources: Source chunks.
        """
        key = hashlib.md5(query.encode()).hexdigest()
        entry = CacheEntry(
            query=query,
            embedding=query_embedding,
            answer=answer,
            sources=sources,
            created_at=time.time(),
        )

        with self._lock:
            self._entries[key] = entry
            if len(self._entries) > self.max_entries:
                self._evict_oldest()

        logger.debug(f"Cache PUT: '{query[:40]}' (size={len(self._entries)})")

    def invalidate(self, user_id: Optional[str] = None) -> int:
        """
        Clear cache entries. Called when documents change.

        Args:
            user_id: If provided, only clear for this user (not yet
                     implemented — clears all for now).

        Returns:
            Number of entries removed.
        """
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
        logger.info(f"Cache invalidated: {count} entries cleared")
        return count

    @property
    def size(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _evict_oldest(self) -> None:
        """Remove the oldest entry (by created_at)."""
        if not self._entries:
            return
        oldest_key = min(self._entries, key=lambda k: self._entries[k].created_at)
        del self._entries[oldest_key]
