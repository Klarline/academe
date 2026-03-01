"""
Tests for advanced RAG pipeline features.

Covers:
- AdaptiveRetriever wiring
- Multi-query search
- Semantic response cache
- Self-RAG / Corrective RAG
- Query decomposition
- Retrieval feedback loop
- Module exports
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from core.models.document import (
    Document, DocumentChunk, DocumentSearchResult, DocumentType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(doc_id="doc1", chunk_idx=0, content="text", score=0.9):
    chunk = DocumentChunk(
        document_id=doc_id,
        user_id="user1",
        chunk_index=chunk_idx,
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
    )
    doc = Document(
        id=doc_id, user_id="user1",
        filename="test.pdf", original_filename="test.pdf",
        file_path="/tmp/test.pdf", file_size=1024,
        file_hash="abc", document_type=DocumentType.PDF,
        title="Test Doc",
    )
    return DocumentSearchResult(chunk=chunk, document=doc, score=score, rank=1)


# ---------------------------------------------------------------------------
# 1. Semantic Response Cache
# ---------------------------------------------------------------------------

class TestSemanticResponseCache:
    def test_put_and_get_exact(self):
        from core.rag.response_cache import SemanticResponseCache
        cache = SemanticResponseCache(similarity_threshold=0.99)
        emb = [1.0, 0.0, 0.0]
        cache.put("What is PCA?", emb, "PCA is ...", [])
        result = cache.get("What is PCA?", emb)
        assert result is not None
        assert result[0] == "PCA is ..."

    def test_miss_on_different_embedding(self):
        from core.rag.response_cache import SemanticResponseCache
        cache = SemanticResponseCache(similarity_threshold=0.99)
        cache.put("What is PCA?", [1.0, 0.0, 0.0], "PCA is ...", [])
        result = cache.get("Unrelated", [0.0, 1.0, 0.0])
        assert result is None

    def test_ttl_expiry(self):
        from core.rag.response_cache import SemanticResponseCache
        cache = SemanticResponseCache(similarity_threshold=0.9, ttl_seconds=1)
        emb = [1.0, 0.0, 0.0]
        cache.put("q", emb, "answer", [])
        time.sleep(1.1)
        assert cache.get("q", emb) is None

    def test_max_entries_eviction(self):
        from core.rag.response_cache import SemanticResponseCache
        cache = SemanticResponseCache(max_entries=3, ttl_seconds=0)
        for i in range(5):
            cache.put(f"q{i}", [float(i), 0.0, 0.0], f"a{i}", [])
        assert cache.size <= 3

    def test_invalidate(self):
        from core.rag.response_cache import SemanticResponseCache
        cache = SemanticResponseCache()
        cache.put("q", [1.0], "a", [])
        count = cache.invalidate()
        assert count == 1
        assert cache.size == 0


# ---------------------------------------------------------------------------
# 2. Self-RAG / Corrective RAG
# ---------------------------------------------------------------------------

class TestSelfRAG:
    def test_verification_result_repr(self):
        from core.rag.self_rag import VerificationResult
        v = VerificationResult(sufficient=True)
        assert "sufficient=True" in repr(v)

    def test_verifier_returns_sufficient_on_good_context(self):
        from core.rag.self_rag import RetrievalVerifier, VerificationResult

        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="SUFFICIENT")
        verifier = RetrievalVerifier(llm=mock_llm)

        result = verifier.verify("What is PCA?", [_make_result()])
        assert result.sufficient is True

    def test_verifier_returns_reformulation(self):
        from core.rag.self_rag import RetrievalVerifier

        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content="REFORMULATE: What is Principal Component Analysis dimensionality reduction?"
        )
        verifier = RetrievalVerifier(llm=mock_llm)
        result = verifier.verify("What is PCA?", [_make_result()])
        assert not result.sufficient
        assert "Principal Component Analysis" in result.reformulated_query

    def test_verifier_too_few_results(self):
        from core.rag.self_rag import RetrievalVerifier
        verifier = RetrievalVerifier()
        result = verifier.verify("query", [], min_results=1)
        assert not result.sufficient
        assert result.reason == "too_few_results"

    def test_controller_retries_on_insufficient(self):
        from core.rag.self_rag import SelfRAGController, RetrievalVerifier, VerificationResult

        mock_llm = Mock()
        call_count = [0]
        def fake_invoke(prompt):
            call_count[0] += 1
            if call_count[0] <= 1:
                return Mock(content="REFORMULATE: better query")
            return Mock(content="SUFFICIENT")
        mock_llm.invoke.side_effect = fake_invoke

        verifier = RetrievalVerifier(llm=mock_llm)
        controller = SelfRAGController(verifier=verifier, max_retries=2)

        search_fn = Mock(return_value=[_make_result()])
        results = controller.search_with_verification(
            query="vague query",
            search_fn=search_fn,
            user_id="user1",
            top_k=5,
            use_reranking=True,
        )
        assert len(results) > 0
        assert search_fn.call_count >= 2


# ---------------------------------------------------------------------------
# 3. Query Decomposition
# ---------------------------------------------------------------------------

class TestQueryDecomposition:
    def test_simple_query_returns_single(self):
        from core.rag.query_decomposer import QueryDecomposer

        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="SIMPLE")
        decomposer = QueryDecomposer(llm=mock_llm)

        result = decomposer.decompose("What is PCA?")
        assert result == ["What is PCA?"]

    def test_complex_query_returns_sub_queries(self):
        from core.rag.query_decomposer import QueryDecomposer

        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content="1. What is PCA and how does it work?\n"
                    "2. What is t-SNE and how does it work?\n"
                    "3. When should you use PCA vs t-SNE?"
        )
        decomposer = QueryDecomposer(llm=mock_llm)
        result = decomposer.decompose("Compare PCA and t-SNE")

        assert len(result) >= 3
        assert result[0] == "Compare PCA and t-SNE"

    def test_retrieve_with_decomposition_merges_results(self):
        from core.rag.query_decomposer import QueryDecomposer, retrieve_with_decomposition

        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content="1. What is the first sub-topic in detail?\n"
                    "2. What is the second sub-topic in detail?"
        )
        decomposer = QueryDecomposer(llm=mock_llm)

        r1 = _make_result("doc1", 0, "chunk A", 0.9)
        r2 = _make_result("doc2", 0, "chunk B", 0.8)
        r3 = _make_result("doc1", 0, "chunk A dup", 0.95)

        call_num = [0]
        def fake_search(**kwargs):
            call_num[0] += 1
            if call_num[0] == 1:
                return [r1]
            elif call_num[0] == 2:
                return [r2]
            return [r3]
        
        results = retrieve_with_decomposition(
            "complex query about multiple things",
            search_fn=fake_search,
            decomposer=decomposer,
            top_k=5,
            user_id="user1",
            use_reranking=True,
        )
        assert len(results) == 2
        doc1_result = next(r for r in results if r.chunk.document_id == "doc1")
        assert doc1_result.score == 0.95


# ---------------------------------------------------------------------------
# 4. Retrieval Feedback
# ---------------------------------------------------------------------------

class TestRetrievalFeedback:
    def test_record_feedback(self):
        from core.rag.feedback import RetrievalFeedback

        mock_collection = Mock()
        mock_collection.insert_one.return_value = Mock(inserted_id="fb123")
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_collection}

        fb = RetrievalFeedback(db=mock_db)

        result = fb.record(
            user_id="user1",
            query="What is PCA?",
            answer="PCA is a dimensionality reduction technique.",
            sources=[{"document": "ML Book", "page": 42}],
            rating=1,
        )
        assert result == "fb123"
        mock_collection.insert_one.assert_called_once()
        entry = mock_collection.insert_one.call_args[0][0]
        assert entry["rating"] == 1
        assert entry["user_id"] == "user1"

    def test_get_feedback_stats_empty(self):
        from core.rag.feedback import RetrievalFeedback

        mock_collection = Mock()
        mock_collection.find.return_value = []
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_collection}

        fb = RetrievalFeedback(db=mock_db)

        stats = fb.get_feedback_stats()
        assert stats["total"] == 0


# ---------------------------------------------------------------------------
# 5. Multi-query (via pipeline wiring)
# ---------------------------------------------------------------------------

class TestMultiQueryWiring:
    def test_multi_query_generates_variants(self):
        from core.rag.query_rewriter import QueryRewriter

        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content="1. What is principal component analysis?\n"
                    "2. How does PCA reduce dimensions?\n"
                    "3. PCA dimensionality reduction explained"
        )
        rewriter = QueryRewriter(llm=mock_llm)
        variants = rewriter.generate_multi_query("What is PCA?", num_queries=3)

        assert len(variants) >= 2
        assert variants[0] == "What is PCA?"


# ---------------------------------------------------------------------------
# 6. Adaptive Retriever in Pipeline
# ---------------------------------------------------------------------------

class TestAdaptiveRetrieverWiring:
    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.DocumentManager")
    def test_pipeline_creates_adaptive_retriever(self, MockDM, MockCR):
        from core.rag.pipeline import RAGPipeline
        from core.vectors.hybrid_search import HybridSearchService

        mock_hs = Mock(spec=HybridSearchService)
        pipeline = RAGPipeline(
            search_service=mock_hs,
            document_manager=MockDM(),
            use_hybrid_search=False,
            use_query_rewriting=False,
            use_self_rag=False,
            use_query_decomposition=False,
            use_response_cache=False,
            use_multi_query=False,
            use_adaptive_retrieval=True,
        )
        assert pipeline.adaptive_retriever is not None

    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.DocumentManager")
    @patch("core.rag.pipeline.SemanticSearchService")
    def test_pipeline_no_adaptive_without_hybrid(self, MockSS, MockDM, MockCR):
        from core.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline(
            search_service=MockSS(),
            document_manager=MockDM(),
            use_hybrid_search=False,
            use_query_rewriting=False,
            use_self_rag=False,
            use_query_decomposition=False,
            use_response_cache=False,
            use_adaptive_retrieval=True,
        )
        assert pipeline.adaptive_retriever is None


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

class TestRAGModuleExports:
    def test_new_exports_present(self):
        from core.rag import __all__
        expected_new = [
            "SemanticResponseCache",
            "SelfRAGController",
            "RetrievalVerifier",
            "QueryDecomposer",
            "RetrievalFeedback",
        ]
        for name in expected_new:
            assert name in __all__, f"{name} not in __all__"

    def test_can_import_all(self):
        from core.rag import (
            SemanticResponseCache,
            SelfRAGController,
            RetrievalVerifier,
            QueryDecomposer,
            RetrievalFeedback,
        )
        assert SemanticResponseCache is not None
        assert SelfRAGController is not None
        assert RetrievalVerifier is not None
        assert QueryDecomposer is not None
        assert RetrievalFeedback is not None
