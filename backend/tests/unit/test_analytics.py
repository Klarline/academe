"""
Tests for RAG analytics module.
"""

import time
from unittest.mock import Mock, patch

import pytest

from core.rag.analytics import RAGAnalytics


class TestRAGAnalytics:
    """Test RAGAnalytics with mocked MongoDB."""

    @pytest.fixture
    def mock_feedback_data(self):
        """Sample feedback documents."""
        now = time.time()
        return [
            {"user_id": "u1", "query": "What is PCA?", "rating": 1, "created_at": now - 86400, "sources": []},
            {"user_id": "u1", "query": "Compare SVM vs RF", "rating": -1, "created_at": now - 86400, "sources": [{"document_id": "doc1", "document": "ML Book"}]},
            {"user_id": "u1", "query": "How to implement gradient descent", "rating": -1, "created_at": now - 172800, "sources": [{"document_id": "doc1", "document": "ML Book"}]},
        ]

    def test_satisfaction_trends_empty(self):
        """Empty collection returns empty DataFrame."""
        mock_coll = Mock()
        mock_coll.aggregate.return_value = []
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_coll}

        analytics = RAGAnalytics(db=mock_db)
        df = analytics.satisfaction_trends(days=7)

        assert df.empty or "date" in df.columns
        mock_coll.aggregate.assert_called_once()

    def test_satisfaction_trends_with_data(self):
        """Aggregation returns DataFrame with expected columns."""
        mock_coll = Mock()
        mock_coll.aggregate.return_value = [
            {"_id": "2025-03-01", "positive": 5, "negative": 2, "total": 7},
            {"_id": "2025-03-02", "positive": 3, "negative": 1, "total": 4},
        ]
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_coll}

        analytics = RAGAnalytics(db=mock_db)
        df = analytics.satisfaction_trends(days=7)

        assert not df.empty
        assert "date" in df.columns
        assert "rate" in df.columns
        assert "rolling_rate" in df.columns
        assert len(df) == 2

    def test_weak_documents_empty(self):
        """No negative feedback returns empty DataFrame."""
        mock_coll = Mock()
        mock_coll.aggregate.return_value = []
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_coll}

        analytics = RAGAnalytics(db=mock_db)
        df = analytics.weak_documents()

        assert df.empty or "document_id" in df.columns

    def test_weak_documents_with_data(self):
        """Returns documents ranked by negative count."""
        mock_coll = Mock()
        mock_coll.aggregate.return_value = [
            {"_id": "doc1", "negative_count": 5, "queries": ["q1", "q2", "q3"]},
            {"_id": "doc2", "negative_count": 2, "queries": ["q4"]},
        ]
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_coll}

        analytics = RAGAnalytics(db=mock_db)
        df = analytics.weak_documents()

        assert not df.empty
        assert df.iloc[0]["document_id"] == "doc1"
        assert df.iloc[0]["negative_count"] == 5

    def test_query_type_performance(self):
        """Classifies queries and aggregates by type."""
        mock_coll = Mock()
        mock_coll.find.return_value = [
            {"query": "What is machine learning?", "rating": 1},
            {"query": "Compare X vs Y", "rating": -1},
            {"query": "How to write a function in Python", "rating": -1},
        ]
        mock_db = Mock()
        mock_db.get_database.return_value = {"retrieval_feedback": mock_coll}

        analytics = RAGAnalytics(db=mock_db)
        df = analytics.query_type_performance(days=30)

        assert not df.empty
        assert "query_type" in df.columns
        assert "sat_rate" in df.columns

    def test_generate_report_structure(self):
        """Report has expected keys."""
        mock_fb = Mock()
        mock_fb.aggregate.return_value = []
        mock_fb.find.return_value = []
        mock_metrics = Mock()
        mock_metrics.find.return_value = []
        mock_db = Mock()
        mock_db.get_database.return_value = {
            "retrieval_feedback": mock_fb,
            "rag_metrics": mock_metrics,
        }

        analytics = RAGAnalytics(db=mock_db)
        report = analytics.generate_report(days=7)

        assert "period_days" in report
        assert "satisfaction_trends" in report
        assert "weak_documents" in report
        assert "query_type_performance" in report
        assert "recommendations" in report
        assert "satisfaction_declining" in report
