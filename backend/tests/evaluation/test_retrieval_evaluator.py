"""Tests for retrieval-only evaluator."""

import pytest
from unittest.mock import MagicMock

from core.evaluation.retrieval_evaluator import (
    RetrievalEvaluator,
    _chunk_id,
    _content_overlap_score,
    _is_relevant_by_content,
)
from core.models.document import DocumentChunk, Document, DocumentSearchResult, DocumentStatus, DocumentType


@pytest.fixture
def mock_search_service():
    """Mock search service returning controlled results."""
    service = MagicMock()
    return service


@pytest.fixture
def sample_results():
    """Sample DocumentSearchResult list for testing."""
    doc = Document(
        user_id="test",
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        file_size=1000,
        file_hash="abc",
        document_type=DocumentType.PDF,
        processing_status=DocumentStatus.READY,
    )
    doc.id = "doc1"

    def make_result(doc_id: str, chunk_idx: int, content: str, score: float):
        chunk = DocumentChunk(
            document_id=doc_id,
            user_id="test",
            chunk_index=chunk_idx,
            content=content,
            char_count=len(content),
            word_count=len(content.split()),
        )
        return DocumentSearchResult(chunk=chunk, document=doc, score=score, rank=chunk_idx + 1)

    return [
        make_result("doc1", 0, "PCA finds principal components via eigenvectors", 0.9),
        make_result("doc1", 1, "Eigenvectors represent directions of max variance", 0.85),
        make_result("doc1", 2, "Unrelated content about cooking", 0.5),
        make_result("doc1", 3, "Principal Component Analysis reduces dimensions", 0.8),
    ]


class TestChunkId:
    def test_chunk_id_format(self):
        assert _chunk_id("doc1", 0) == "doc1_0"
        assert _chunk_id("abc123", 42) == "abc123_42"


class TestContentOverlap:
    def test_high_overlap(self):
        gt = "Principal Component Analysis eigenvectors"
        chunk = "PCA uses eigenvectors of the covariance matrix"
        assert _content_overlap_score(chunk, gt) > 0.2  # eigenvectors, covariance overlap

    def test_low_overlap(self):
        gt = "Principal Component Analysis"
        chunk = "Today we will discuss cooking recipes"
        assert _content_overlap_score(chunk, gt) < 0.2

    def test_empty_ground_truth(self):
        assert _content_overlap_score("some content", "") == 0.0


class TestIsRelevantByContent:
    def test_relevant(self):
        assert _is_relevant_by_content(
            "PCA finds eigenvectors of covariance matrix",
            "Principal Component Analysis uses eigenvectors",
            threshold=0.15,
        )

    def test_not_relevant(self):
        assert not _is_relevant_by_content(
            "Cooking recipes for pasta",
            "Principal Component Analysis",
            threshold=0.15,
        )


class TestRetrievalEvaluator:
    def test_evaluate_query_with_content_overlap(self, mock_search_service, sample_results):
        mock_search_service.search.return_value = sample_results
        mock_search_service.search_with_reranking.return_value = sample_results

        evaluator = RetrievalEvaluator(search_service=mock_search_service)
        query_data = {
            "question": "What is PCA?",
            "ground_truth": "PCA uses eigenvectors of the covariance matrix for dimensionality reduction",
        }
        relevant_ids = evaluator._get_relevant_ids(query_data)

        metrics = evaluator._evaluate_query(
            query="What is PCA?",
            user_id="test",
            results=sample_results,
            ground_truth=query_data["ground_truth"],
            relevant_ids=relevant_ids,
            k_values=[2, 4],
        )

        assert "precision@2" in metrics
        assert "precision@4" in metrics
        assert "mrr" in metrics
        assert 0 <= metrics["precision@2"] <= 1
        assert 0 <= metrics["mrr"] <= 1
