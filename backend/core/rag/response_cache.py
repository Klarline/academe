"""
Semantic response cache for RAG answers.

Caches (query, answer, sources) keyed by query embedding similarity.
If a new query is semantically similar (cosine > threshold) to a cached
entry, the cached answer is returned — saving LLM cost and latency.

Supports in-memory and optional Redis backends.  ``RedisResponseCache``
persists entries across restarts and supports multi-instance deployments.
"""

import hashlib
import json
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


# ---------------------------------------------------------------------------
# Redis-backed cache
# ---------------------------------------------------------------------------

class RedisResponseCache:
    """
    Redis-backed semantic response cache.

    Persists across restarts and works with multiple backend instances.
    Falls back to in-memory ``SemanticResponseCache`` if Redis is unavailable.

    Redis key scheme:
        ``academe:cache:entries``  — Redis Hash mapping md5(query) → JSON blob
        ``academe:cache:embeddings`` — Redis Hash mapping md5(query) → JSON list

    Similarity search still runs in-process (loads all embeddings on lookup).
    This is fine up to ~1000 entries; beyond that, consider a vector-DB
    cache index.
    """

    ENTRIES_KEY = "academe:cache:entries"
    EMBEDDINGS_KEY = "academe:cache:embeddings"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
        max_entries: int = 500,
    ):
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._redis = None
        self._fallback: Optional[SemanticResponseCache] = None

        try:
            import redis
            url = redis_url or self._default_redis_url()
            self._redis = redis.Redis.from_url(url, decode_responses=True)
            self._redis.ping()
            logger.info("RedisResponseCache connected to %s", url)
        except Exception as e:
            logger.warning(
                "Redis unavailable (%s), falling back to in-memory cache", e
            )
            self._fallback = SemanticResponseCache(
                similarity_threshold=similarity_threshold,
                ttl_seconds=ttl_seconds,
                max_entries=max_entries,
            )

    @staticmethod
    def _default_redis_url() -> str:
        try:
            from core.config import get_settings
            return get_settings().redis_url
        except Exception:
            return "redis://localhost:6379/0"

    # ── Public API (mirrors SemanticResponseCache) ────────────────────

    def get(
        self,
        query: str,
        query_embedding: List[float],
    ) -> Optional[Tuple[str, List[Any]]]:
        if self._fallback:
            return self._fallback.get(query, query_embedding)

        try:
            all_embeddings = self._redis.hgetall(self.EMBEDDINGS_KEY)
            if not all_embeddings:
                return None

            now = time.time()
            best_score = -1.0
            best_key: Optional[str] = None

            for key, emb_json in all_embeddings.items():
                stored_emb = json.loads(emb_json)
                score = SemanticResponseCache._cosine_similarity(
                    query_embedding, stored_emb
                )
                if score > best_score:
                    best_score = score
                    best_key = key

            if best_key and best_score >= self.similarity_threshold:
                entry_json = self._redis.hget(self.ENTRIES_KEY, best_key)
                if entry_json:
                    entry = json.loads(entry_json)
                    if self.ttl_seconds and (now - entry["created_at"]) > self.ttl_seconds:
                        self._redis.hdel(self.ENTRIES_KEY, best_key)
                        self._redis.hdel(self.EMBEDDINGS_KEY, best_key)
                        return None
                    logger.info(
                        "Redis cache HIT (score=%.3f): '%s'",
                        best_score, query[:40],
                    )
                    return entry["answer"], entry["sources"]

        except Exception as e:
            logger.warning("Redis cache get failed: %s", e)

        return None

    def put(
        self,
        query: str,
        query_embedding: List[float],
        answer: str,
        sources: List[Any],
    ) -> None:
        if self._fallback:
            self._fallback.put(query, query_embedding, answer, sources)
            return

        key = hashlib.md5(query.encode()).hexdigest()

        # Serialize sources — DocumentSearchResult objects need conversion
        serializable_sources = []
        for s in sources:
            if hasattr(s, "chunk"):
                serializable_sources.append({
                    "document_id": s.chunk.document_id,
                    "chunk_index": s.chunk.chunk_index,
                    "score": getattr(s, "score", 0),
                    "content_preview": s.chunk.content[:200],
                })
            else:
                serializable_sources.append(s)

        entry = {
            "query": query,
            "answer": answer,
            "sources": serializable_sources,
            "created_at": time.time(),
        }

        try:
            self._redis.hset(self.ENTRIES_KEY, key, json.dumps(entry))
            self._redis.hset(self.EMBEDDINGS_KEY, key, json.dumps(query_embedding))

            if self._redis.hlen(self.ENTRIES_KEY) > self.max_entries:
                self._evict_oldest_redis()

            logger.debug("Redis cache PUT: '%s'", query[:40])
        except Exception as e:
            logger.warning("Redis cache put failed: %s", e)

    def invalidate(self, user_id: Optional[str] = None) -> int:
        if self._fallback:
            return self._fallback.invalidate(user_id)
        try:
            count = self._redis.hlen(self.ENTRIES_KEY)
            self._redis.delete(self.ENTRIES_KEY, self.EMBEDDINGS_KEY)
            logger.info("Redis cache invalidated: %d entries cleared", count)
            return count
        except Exception as e:
            logger.warning("Redis cache invalidate failed: %s", e)
            return 0

    @property
    def size(self) -> int:
        if self._fallback:
            return self._fallback.size
        try:
            return self._redis.hlen(self.ENTRIES_KEY)
        except Exception:
            return 0

    def _evict_oldest_redis(self) -> None:
        """Remove the oldest entry by created_at."""
        try:
            all_entries = self._redis.hgetall(self.ENTRIES_KEY)
            if not all_entries:
                return
            oldest_key = min(
                all_entries,
                key=lambda k: json.loads(all_entries[k]).get("created_at", 0),
            )
            self._redis.hdel(self.ENTRIES_KEY, oldest_key)
            self._redis.hdel(self.EMBEDDINGS_KEY, oldest_key)
        except Exception as e:
            logger.warning("Redis eviction failed: %s", e)
