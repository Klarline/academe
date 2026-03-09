"""
Semantic response cache for RAG answers.

Caches (query, answer, sources) keyed by query embedding similarity,
**scoped per user** to prevent cross-user data leakage.

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

# ---------------------------------------------------------------------------
# Process-global Prometheus counters (shared across all cache instances)
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge

    CACHE_HITS = Counter(
        "academe_cache_hits_total",
        "Total semantic response cache hits",
        ["backend"],  # "memory" or "redis"
    )
    CACHE_MISSES = Counter(
        "academe_cache_misses_total",
        "Total semantic response cache misses",
        ["backend"],
    )
    CACHE_ENTRIES = Gauge(
        "academe_cache_entries",
        "Current number of cached entries",
        ["backend"],
    )
    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False


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
    In-memory semantic cache with cosine-similarity lookup, scoped per user.

    Each user's entries are stored in a separate partition to prevent
    cross-user data leakage (answers cite user-specific documents).

    Parameters:
        similarity_threshold: Minimum cosine similarity for a cache hit (0-1).
        ttl_seconds: Time-to-live for cache entries. 0 = no expiry.
        max_entries: Maximum entries per user. Evicts oldest when exceeded.
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

        # Outer key: user_id, inner key: md5(query)
        self._entries: Dict[str, Dict[str, CacheEntry]] = {}
        self._lock = threading.Lock()

        # Hit/miss counters for monitoring
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        user_id: str,
        query: str,
        query_embedding: List[float],
    ) -> Optional[Tuple[str, List[Any]]]:
        """
        Look up a cached answer by semantic similarity within a user's partition.

        Args:
            user_id: User whose cache to search.
            query: The user query (for logging).
            query_embedding: Embedding of the query.

        Returns:
            (answer, sources) if cache hit, else None.
        """
        now = time.time()
        best_score = -1.0
        best_entry: Optional[CacheEntry] = None

        with self._lock:
            user_entries = self._entries.get(user_id, {})
            expired_keys = []
            for key, entry in user_entries.items():
                if self.ttl_seconds and (now - entry.created_at) > self.ttl_seconds:
                    expired_keys.append(key)
                    continue
                score = self._cosine_similarity(query_embedding, entry.embedding)
                if score > best_score:
                    best_score = score
                    best_entry = entry

            for k in expired_keys:
                del user_entries[k]

        if best_entry and best_score >= self.similarity_threshold:
            self._hits += 1
            if _PROM_AVAILABLE:
                CACHE_HITS.labels(backend="memory").inc()
            logger.info(
                "Cache HIT (user=%s, score=%.3f): '%s' matched '%s'",
                user_id[:8], best_score, query[:40], best_entry.query[:40],
            )
            return best_entry.answer, best_entry.sources

        self._misses += 1
        if _PROM_AVAILABLE:
            CACHE_MISSES.labels(backend="memory").inc()
        return None

    def put(
        self,
        user_id: str,
        query: str,
        query_embedding: List[float],
        answer: str,
        sources: List[Any],
    ) -> None:
        """
        Store a query/answer pair in the user's cache partition.

        Args:
            user_id: User whose cache to store in.
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
            if user_id not in self._entries:
                self._entries[user_id] = {}
            self._entries[user_id][key] = entry
            if len(self._entries[user_id]) > self.max_entries:
                self._evict_oldest(user_id)

        logger.debug(
            "Cache PUT (user=%s): '%s' (size=%d)",
            user_id[:8], query[:40], len(self._entries[user_id]),
        )
        if _PROM_AVAILABLE:
            CACHE_ENTRIES.labels(backend="memory").set(self.size)

    def invalidate(self, user_id: Optional[str] = None) -> int:
        """
        Clear cache entries. Called when documents change.

        Args:
            user_id: If provided, clear only this user's entries.
                     If None, clear all entries for all users.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            if user_id is not None:
                user_entries = self._entries.pop(user_id, {})
                count = len(user_entries)
            else:
                count = sum(len(v) for v in self._entries.values())
                self._entries.clear()
        logger.info(
            "Cache invalidated (user=%s): %d entries cleared",
            user_id or "ALL", count,
        )
        return count

    @property
    def size(self) -> int:
        """Total entries across all users."""
        return sum(len(v) for v in self._entries.values())

    def user_size(self, user_id: str) -> int:
        """Number of entries for a specific user."""
        return len(self._entries.get(user_id, {}))

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics including hit rate."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_lookups": total,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "entries": self.size,
            "users": len(self._entries),
        }

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

    def _evict_oldest(self, user_id: str) -> None:
        """Remove the oldest entry (by created_at) for a given user."""
        user_entries = self._entries.get(user_id, {})
        if not user_entries:
            return
        oldest_key = min(user_entries, key=lambda k: user_entries[k].created_at)
        del user_entries[oldest_key]


# ---------------------------------------------------------------------------
# Redis-backed cache
# ---------------------------------------------------------------------------

class RedisResponseCache:
    """
    Redis-backed semantic response cache, scoped per user.

    Persists across restarts and works with multiple backend instances.
    Falls back to in-memory ``SemanticResponseCache`` if Redis is unavailable.

    Redis key scheme (per-user):
        ``academe:cache:{user_id}:entries``     — Hash: md5(query) → JSON blob
        ``academe:cache:{user_id}:embeddings``  — Hash: md5(query) → JSON list

    Similarity search still runs in-process (loads all embeddings on lookup).
    This is fine up to ~1000 entries per user; beyond that, consider a
    vector-DB cache index.
    """

    ENTRIES_KEY_TPL = "academe:cache:{user_id}:entries"
    EMBEDDINGS_KEY_TPL = "academe:cache:{user_id}:embeddings"

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

    def _entries_key(self, user_id: str) -> str:
        return self.ENTRIES_KEY_TPL.format(user_id=user_id)

    def _embeddings_key(self, user_id: str) -> str:
        return self.EMBEDDINGS_KEY_TPL.format(user_id=user_id)

    # ── Public API (mirrors SemanticResponseCache) ────────────────────

    def get(
        self,
        user_id: str,
        query: str,
        query_embedding: List[float],
    ) -> Optional[Tuple[str, List[Any]]]:
        if self._fallback:
            return self._fallback.get(user_id, query, query_embedding)

        try:
            emb_key = self._embeddings_key(user_id)
            all_embeddings = self._redis.hgetall(emb_key)
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
                ent_key = self._entries_key(user_id)
                entry_json = self._redis.hget(ent_key, best_key)
                if entry_json:
                    entry = json.loads(entry_json)
                    if self.ttl_seconds and (now - entry["created_at"]) > self.ttl_seconds:
                        self._redis.hdel(ent_key, best_key)
                        self._redis.hdel(emb_key, best_key)
                        return None
                    logger.info(
                        "Redis cache HIT (user=%s, score=%.3f): '%s'",
                        user_id[:8], best_score, query[:40],
                    )
                    if _PROM_AVAILABLE:
                        CACHE_HITS.labels(backend="redis").inc()
                    return entry["answer"], entry["sources"]

        except Exception as e:
            logger.warning("Redis cache get failed: %s", e)

        if _PROM_AVAILABLE:
            CACHE_MISSES.labels(backend="redis").inc()
        return None

    def put(
        self,
        user_id: str,
        query: str,
        query_embedding: List[float],
        answer: str,
        sources: List[Any],
    ) -> None:
        if self._fallback:
            self._fallback.put(user_id, query, query_embedding, answer, sources)
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
            ent_key = self._entries_key(user_id)
            emb_key = self._embeddings_key(user_id)
            self._redis.hset(ent_key, key, json.dumps(entry))
            self._redis.hset(emb_key, key, json.dumps(query_embedding))

            if self._redis.hlen(ent_key) > self.max_entries:
                self._evict_oldest_redis(user_id)

            logger.debug("Redis cache PUT (user=%s): '%s'", user_id[:8], query[:40])
        except Exception as e:
            logger.warning("Redis cache put failed: %s", e)

    def invalidate(self, user_id: Optional[str] = None) -> int:
        if self._fallback:
            return self._fallback.invalidate(user_id)
        try:
            if user_id is not None:
                ent_key = self._entries_key(user_id)
                emb_key = self._embeddings_key(user_id)
                count = self._redis.hlen(ent_key)
                self._redis.delete(ent_key, emb_key)
            else:
                # Scan for all user cache keys and delete them
                count = 0
                for key in self._redis.scan_iter("academe:cache:*:entries"):
                    count += self._redis.hlen(key)
                    emb_sibling = key.replace(":entries", ":embeddings")
                    self._redis.delete(key, emb_sibling)
            logger.info(
                "Redis cache invalidated (user=%s): %d entries cleared",
                user_id or "ALL", count,
            )
            return count
        except Exception as e:
            logger.warning("Redis cache invalidate failed: %s", e)
            return 0

    @property
    def size(self) -> int:
        """Total entries across all users."""
        if self._fallback:
            return self._fallback.size
        try:
            total = 0
            for key in self._redis.scan_iter("academe:cache:*:entries"):
                total += self._redis.hlen(key)
            return total
        except Exception:
            return 0

    def user_size(self, user_id: str) -> int:
        """Number of entries for a specific user."""
        if self._fallback:
            return self._fallback.user_size(user_id)
        try:
            return self._redis.hlen(self._entries_key(user_id))
        except Exception:
            return 0

    def _evict_oldest_redis(self, user_id: str) -> None:
        """Remove the oldest entry by created_at for a given user."""
        try:
            ent_key = self._entries_key(user_id)
            emb_key = self._embeddings_key(user_id)
            all_entries = self._redis.hgetall(ent_key)
            if not all_entries:
                return
            oldest_key = min(
                all_entries,
                key=lambda k: json.loads(all_entries[k]).get("created_at", 0),
            )
            self._redis.hdel(ent_key, oldest_key)
            self._redis.hdel(emb_key, oldest_key)
        except Exception as e:
            logger.warning("Redis eviction failed: %s", e)


# ---------------------------------------------------------------------------
# Global cache stats for analytics / monitoring
# ---------------------------------------------------------------------------

def get_cache_metrics() -> Dict[str, Any]:
    """
    Return process-global cache metrics from Prometheus counters.

    Safe to call from RAGAnalytics or any monitoring endpoint.
    Returns zeros if prometheus_client is not installed.
    """
    if not _PROM_AVAILABLE:
        return {
            "memory_hits": 0,
            "memory_misses": 0,
            "redis_hits": 0,
            "redis_misses": 0,
            "total_hits": 0,
            "total_misses": 0,
            "total_lookups": 0,
            "hit_rate": 0.0,
        }

    mem_hits = CACHE_HITS.labels(backend="memory")._value.get()
    mem_misses = CACHE_MISSES.labels(backend="memory")._value.get()
    redis_hits = CACHE_HITS.labels(backend="redis")._value.get()
    redis_misses = CACHE_MISSES.labels(backend="redis")._value.get()
    total_hits = mem_hits + redis_hits
    total_misses = mem_misses + redis_misses
    total = total_hits + total_misses

    return {
        "memory_hits": int(mem_hits),
        "memory_misses": int(mem_misses),
        "redis_hits": int(redis_hits),
        "redis_misses": int(redis_misses),
        "total_hits": int(total_hits),
        "total_misses": int(total_misses),
        "total_lookups": int(total),
        "hit_rate": total_hits / total if total > 0 else 0.0,
    }
