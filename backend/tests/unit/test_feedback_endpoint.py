"""
Tests for chat feedback API endpoint.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.v1.deps import get_current_user_id


async def override_get_current_user_id():
    return "user123"


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer fake-token"}


class TestFeedbackEndpoint:
    """Test POST /api/v1/chat/feedback."""

    @patch("api.v1.endpoints.chat.conv_repo")
    def test_feedback_rag_response_not_found(self, mock_conv_repo, client, auth_headers):
        """404 when message has no rag_response."""
        mock_conv_repo.get_rag_response_by_message_id.return_value = None

        response = client.post(
            "/api/v1/chat/feedback",
            json={"message_id": "nonexistent", "rating": 1},
            headers=auth_headers,
        )

        assert response.status_code == 404
        mock_conv_repo.get_rag_response_by_message_id.assert_called_once_with("nonexistent")

    @patch("api.v1.endpoints.chat.conv_repo")
    @patch("core.rag.feedback.RetrievalFeedback")
    def test_feedback_success(self, MockRetrievalFeedback, mock_conv_repo, client, auth_headers):
        """200 and feedback_id when rag_response exists."""
        mock_conv_repo.get_rag_response_by_message_id.return_value = {
            "user_id": "user123",
            "query": "What is PCA?",
            "answer": "PCA is...",
            "sources": [],
        }
        mock_fb = Mock()
        mock_fb.record.return_value = "fb_abc123"
        MockRetrievalFeedback.return_value = mock_fb

        response = client.post(
            "/api/v1/chat/feedback",
            json={"message_id": "msg123", "rating": 1, "comment": "Great!"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback_id"] == "fb_abc123"
        mock_fb.record.assert_called_once_with(
            user_id="user123",
            query="What is PCA?",
            answer="PCA is...",
            sources=[],
            rating=1,
            comment="Great!",
        )

    @patch("api.v1.endpoints.chat.conv_repo")
    def test_feedback_forbidden_wrong_user(self, mock_conv_repo, client, auth_headers):
        """403 when rag_response belongs to different user."""
        mock_conv_repo.get_rag_response_by_message_id.return_value = {
            "user_id": "other_user",
            "query": "What is PCA?",
            "answer": "PCA is...",
            "sources": [],
        }

        response = client.post(
            "/api/v1/chat/feedback",
            json={"message_id": "msg123", "rating": -1},
            headers=auth_headers,
        )

        assert response.status_code == 403
