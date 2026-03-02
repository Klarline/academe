"""
Tests for fallback chain, per-stage value metrics, and Redis response cache.

Covers:
- fallback() ordering, exhaustion, default, logging
- @with_fallback decorator
- FallbackStrategies canonical defaults
- RequestMetrics recording and summary
- AggregateMetrics cross-request accumulation
- RedisResponseCache with mock Redis and fallback to in-memory
- SemanticResponseCache (original) regression
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from core.rag.fallback import (
    fallback,
    with_fallback,
    FallbackExhausted,
    FallbackStrategies,
)
from core.rag.stage_metrics import (
    RequestMetrics,
    AggregateMetrics,
    StageEvent,
    get_aggregate_metrics,
)
from core.rag.response_cache import SemanticResponseCache, RedisResponseCache


# ===================================================================
# Fallback chain
# ===================================================================

class TestFallback:

    def test_primary_succeeds(self):
        result = fallback(
            primary=lambda: "ok",
            label="test",
        )
        assert result == "ok"

    def test_primary_fails_fallback_succeeds(self):
        result = fallback(
            primary=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            fallbacks=[lambda: "recovered"],
            label="test",
        )
        assert result == "recovered"

    def test_all_fail_returns_default(self):
        result = fallback(
            primary=lambda: (_ for _ in ()).throw(RuntimeError("a")),
            fallbacks=[lambda: (_ for _ in ()).throw(RuntimeError("b"))],
            default="safe",
            label="test",
        )
        assert result == "safe"

    def test_all_fail_no_default_raises(self):
        with pytest.raises(FallbackExhausted):
            fallback(
                primary=lambda: (_ for _ in ()).throw(RuntimeError("a")),
                label="test",
            )

    def test_fallback_order_is_respected(self):
        calls = []

        def fn1():
            calls.append(1)
            raise RuntimeError

        def fn2():
            calls.append(2)
            return "from_2"

        def fn3():
            calls.append(3)
            return "from_3"

        result = fallback(
            primary=fn1,
            fallbacks=[fn2, fn3],
            label="test",
        )
        assert result == "from_2"
        assert calls == [1, 2]

    def test_none_default_is_valid(self):
        """default=None means raise on exhaustion, not 'return None'."""
        with pytest.raises(FallbackExhausted):
            fallback(
                primary=lambda: (_ for _ in ()).throw(RuntimeError),
                default=None,
                label="test",
            )


class TestWithFallbackDecorator:

    def test_success_returns_value(self):
        @with_fallback(default="nope", label="dec")
        def good():
            return "yes"

        assert good() == "yes"

    def test_failure_returns_default(self):
        @with_fallback(default=[], label="dec")
        def bad():
            raise RuntimeError("boom")

        assert bad() == []

    def test_preserves_function_name(self):
        @with_fallback(default=None)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestFallbackStrategies:

    def test_grading_default(self):
        d = FallbackStrategies.llm_grading_default()
        assert d["verdict"] == "pass"

    def test_rewrite_default(self):
        assert FallbackStrategies.llm_rewrite_default("hello") == "hello"

    def test_reranker_default(self):
        results = [1, 2, 3]
        assert FallbackStrategies.reranker_default(results) is results

    def test_vector_search_default(self):
        assert FallbackStrategies.vector_search_default() == []

    def test_cache_default(self):
        assert FallbackStrategies.cache_default() is None

    def test_kg_default(self):
        assert FallbackStrategies.kg_default() == ""


# ===================================================================
# Stage metrics
# ===================================================================

class TestStageEvent:

    def test_to_dict(self):
        e = StageEvent(stage="reranking", enabled=True, ran=True, changed_output=True, elapsed_ms=12.3)
        d = e.to_dict()
        assert d["stage"] == "reranking"
        assert d["changed_output"] is True
        assert d["elapsed_ms"] == 12.3


class TestRequestMetrics:

    def test_record_query_rewrite_changed(self):
        m = RequestMetrics()
        m.record_query_rewrite(enabled=True, original="explain it", rewritten="explain PCA", elapsed_ms=50)
        summary = m.to_dict()
        assert "query_rewrite" in summary["stages_that_changed_input"]

    def test_record_query_rewrite_unchanged(self):
        m = RequestMetrics()
        m.record_query_rewrite(enabled=True, original="what is PCA", rewritten="what is PCA", elapsed_ms=10)
        summary = m.to_dict()
        assert "query_rewrite" not in summary["stages_that_changed_input"]

    def test_record_reranking_changed(self):
        m = RequestMetrics()
        m.record_reranking(
            enabled=True,
            top5_before=["a", "b", "c"],
            top5_after=["b", "a", "c"],
            elapsed_ms=30,
        )
        summary = m.to_dict()
        assert "reranking" in summary["stages_that_changed_output"]

    def test_record_reranking_unchanged(self):
        m = RequestMetrics()
        m.record_reranking(
            enabled=True,
            top5_before=["a", "b"],
            top5_after=["a", "b"],
            elapsed_ms=20,
        )
        summary = m.to_dict()
        assert "reranking" not in summary["stages_that_changed_output"]

    def test_record_self_rag_with_retry(self):
        m = RequestMetrics()
        m.record_self_rag(enabled=True, retries=1, reformulated=True, elapsed_ms=100)
        summary = m.to_dict()
        assert "self_rag" in summary["stages_that_changed_input"]
        assert "self_rag" in summary["stages_that_changed_output"]

    def test_record_cache_hit(self):
        m = RequestMetrics()
        m.record_cache(hit=True, elapsed_ms=1)
        summary = m.to_dict()
        assert "cache" in summary["stages_that_changed_output"]

    def test_record_cache_miss(self):
        m = RequestMetrics()
        m.record_cache(hit=False, elapsed_ms=1)
        summary = m.to_dict()
        assert "cache" not in summary["stages_that_changed_output"]

    def test_record_knowledge_graph(self):
        m = RequestMetrics()
        m.record_knowledge_graph(enabled=True, triples_added=5, elapsed_ms=200)
        summary = m.to_dict()
        assert "knowledge_graph" in summary["stages_that_changed_output"]

    def test_record_multi_query(self):
        m = RequestMetrics()
        m.record_multi_query(enabled=True, num_variants=3, elapsed_ms=80)
        summary = m.to_dict()
        assert "multi_query" in summary["stages_that_changed_input"]

    def test_record_decomposition(self):
        m = RequestMetrics()
        m.record_decomposition(enabled=True, num_sub_queries=3, elapsed_ms=60)
        summary = m.to_dict()
        assert "decomposition" in summary["stages_that_changed_input"]

    def test_record_response_grader(self):
        m = RequestMetrics()
        m.record_response_grader(verdict="refine", elapsed_ms=200)
        summary = m.to_dict()
        assert "response_grader" in summary["stages_that_changed_output"]

    def test_total_ms_is_positive(self):
        m = RequestMetrics()
        time.sleep(0.01)
        summary = m.to_dict()
        assert summary["total_ms"] > 0

    def test_log_summary_does_not_raise(self):
        m = RequestMetrics()
        m.record_cache(hit=False)
        m.log_summary()


class TestAggregateMetrics:

    def test_inc_and_to_dict(self):
        a = AggregateMetrics()
        a.inc("foo")
        a.inc("foo")
        a.inc("bar", 5)
        d = a.to_dict()
        assert d["foo"] == 2
        assert d["bar"] == 5

    def test_absorb_request_metrics(self):
        a = AggregateMetrics()
        m = RequestMetrics()
        m.record_query_rewrite(enabled=True, original="a", rewritten="b")
        m.record_cache(hit=True)
        a.absorb(m)
        d = a.to_dict()
        assert d["query_rewrite.enabled"] == 1
        assert d["query_rewrite.changed_input"] == 1
        assert d["cache.changed_output"] == 1
        assert d["requests_total"] == 1

    def test_reset(self):
        a = AggregateMetrics()
        a.inc("x")
        a.reset()
        assert a.to_dict() == {}

    def test_global_singleton(self):
        g = get_aggregate_metrics()
        assert isinstance(g, AggregateMetrics)


# ===================================================================
# Redis response cache
# ===================================================================

class TestRedisResponseCacheFallback:
    """When Redis is unavailable, RedisResponseCache falls back to in-memory."""

    def test_falls_back_to_memory_on_connection_error(self):
        cache = RedisResponseCache(redis_url="redis://nonexistent:9999")
        assert cache._fallback is not None
        assert cache._redis is None or cache._fallback is not None

    def test_fallback_put_and_get(self):
        cache = RedisResponseCache(redis_url="redis://nonexistent:9999")
        emb = [0.1, 0.2, 0.3]
        cache.put("what is PCA", emb, "PCA is...", [])
        result = cache.get("what is PCA", emb)
        assert result is not None
        assert result[0] == "PCA is..."

    def test_fallback_invalidate(self):
        cache = RedisResponseCache(redis_url="redis://nonexistent:9999")
        emb = [0.1, 0.2, 0.3]
        cache.put("q", emb, "a", [])
        assert cache.size == 1
        cache.invalidate()
        assert cache.size == 0


class TestRedisResponseCacheWithMockRedis:
    """Test the Redis path using a directly-injected mock Redis client."""

    def _make_cache(self):
        """Create a RedisResponseCache with an injected mock Redis."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hgetall.return_value = {}
        mock_redis.hlen.return_value = 0

        cache = RedisResponseCache.__new__(RedisResponseCache)
        cache.similarity_threshold = 0.95
        cache.ttl_seconds = 3600
        cache.max_entries = 500
        cache._redis = mock_redis
        cache._fallback = None
        return cache, mock_redis

    def test_put_calls_hset(self):
        cache, mock_redis = self._make_cache()
        cache.put("q", [0.1, 0.2], "answer", [])
        assert mock_redis.hset.call_count == 2

    def test_get_returns_none_on_empty(self):
        cache, mock_redis = self._make_cache()
        mock_redis.hgetall.return_value = {}
        result = cache.get("q", [0.1, 0.2])
        assert result is None

    def test_invalidate_calls_delete(self):
        cache, mock_redis = self._make_cache()
        mock_redis.hlen.return_value = 3
        count = cache.invalidate()
        assert count == 3
        mock_redis.delete.assert_called_once()

    def test_size_delegates_to_hlen(self):
        cache, mock_redis = self._make_cache()
        mock_redis.hlen.return_value = 42
        assert cache.size == 42


# ===================================================================
# SemanticResponseCache (regression)
# ===================================================================

class TestSemanticResponseCacheRegression:
    """Ensure the original in-memory cache still works after refactoring."""

    def test_put_and_get_exact_match(self):
        cache = SemanticResponseCache(similarity_threshold=0.99)
        emb = [1.0, 0.0, 0.0]
        cache.put("q1", emb, "answer1", ["s1"])
        result = cache.get("q1", emb)
        assert result is not None
        assert result[0] == "answer1"

    def test_miss_below_threshold(self):
        cache = SemanticResponseCache(similarity_threshold=0.99)
        cache.put("q1", [1.0, 0.0, 0.0], "answer1", [])
        result = cache.get("q2", [0.0, 1.0, 0.0])
        assert result is None

    def test_ttl_expiry(self):
        cache = SemanticResponseCache(similarity_threshold=0.5, ttl_seconds=1)
        emb = [1.0, 0.0]
        cache.put("q", emb, "a", [])
        time.sleep(1.1)
        result = cache.get("q", emb)
        assert result is None

    def test_eviction_on_max_entries(self):
        cache = SemanticResponseCache(max_entries=2)
        cache.put("q1", [1.0, 0.0], "a1", [])
        cache.put("q2", [0.0, 1.0], "a2", [])
        cache.put("q3", [0.5, 0.5], "a3", [])
        assert cache.size == 2
