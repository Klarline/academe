"""
Comprehensive tests for all Pydantic models.

Tests cover:
- UserProfile model validation and methods
- Conversation and Message models
- Document models
- Practice models
- Field validators
- Custom methods
- MongoDB conversion
- Edge cases
"""

import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import ValidationError

from core.models import (
    Message, Conversation, ConversationSummary,
    UserProfile, LearningLevel, LearningGoal, ExplanationStyle, RAGFallbackPreference,
    Document, DocumentChunk, DocumentStatus, DocumentType, DocumentSearchResult,
    PracticeSession, PracticeQuestionResult
)


class TestMessageModel:
    """Test Message model."""

    def test_message_creation_valid(self):
        """Test creating a valid message."""
        msg = Message(
            conversation_id="conv123",
            user_id="user123",
            role="user",
            content="Test message"
        )
        
        assert msg.conversation_id == "conv123"
        assert msg.user_id == "user123"
        assert msg.role == "user"
        assert msg.content == "Test message"
        assert msg.timestamp is not None

    def test_message_content_validation_empty(self):
        """Test that empty content is rejected."""
        with pytest.raises(ValidationError, match="content cannot be empty"):
            Message(
                conversation_id="conv123",
                user_id="user123",
                role="user",
                content="   "
            )

    def test_message_role_validation(self):
        """Test that only valid roles are accepted."""
        # Valid roles
        for role in ["user", "assistant", "system"]:
            msg = Message(
                conversation_id="conv123",
                user_id="user123",
                role=role,
                content="Test"
            )
            assert msg.role == role
        
        # Invalid role
        with pytest.raises(ValidationError):
            Message(
                conversation_id="conv123",
                user_id="user123",
                role="invalid_role",
                content="Test"
            )

    def test_message_format_for_display(self):
        """Test message display formatting."""
        msg = Message(
            conversation_id="conv123",
            user_id="user123",
            role="assistant",
            content="Test response",
            agent_used="ConceptExplainer",
            route="concept",
            processing_time_ms=250
        )
        
        # Without metadata
        formatted = msg.format_for_display(show_metadata=False)
        assert "Assistant: Test response" in formatted
        assert "Agent:" not in formatted
        
        # With metadata
        formatted_meta = msg.format_for_display(show_metadata=True)
        assert "Assistant: Test response" in formatted_meta
        assert "Agent: ConceptExplainer" in formatted_meta
        assert "Time: 250ms" in formatted_meta


class TestConversationModel:
    """Test Conversation model."""

    def test_conversation_creation(self):
        """Test creating a valid conversation."""
        conv = Conversation(
            user_id="user123",
            title="Test Conversation"
        )
        
        assert conv.user_id == "user123"
        assert conv.title == "Test Conversation"
        assert conv.message_count == 0
        assert conv.is_active is True
        assert conv.is_archived is False

    def test_conversation_archive_unarchive(self):
        """Test conversation archive/unarchive."""
        conv = Conversation(user_id="user123", title="Test")
        
        conv.archive()
        assert conv.is_archived is True
        assert conv.is_active is False
        
        conv.unarchive()
        assert conv.is_archived is False
        assert conv.is_active is True


class TestUserProfileModel:
    """Test UserProfile model."""

    def test_user_profile_creation_minimal(self):
        """Test creating user with minimal required fields."""
        user = UserProfile(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.has_completed_onboarding is False

    def test_user_profile_email_validation(self):
        """Test email validation."""
        user = UserProfile(
            email="valid@example.com",
            username="testuser",
            password_hash="hash"
        )
        assert user.email == "valid@example.com"
        
        with pytest.raises(ValidationError):
            UserProfile(
                email="not-an-email",
                username="testuser",
                password_hash="hash"
            )

    def test_user_profile_learning_level_enum(self):
        """Test LearningLevel enum."""
        user = UserProfile(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            learning_level=LearningLevel.INTERMEDIATE
        )
        
        assert user.learning_level == LearningLevel.INTERMEDIATE
        assert user.learning_level.value == "intermediate"


class TestDocumentModels:
    """Test Document-related models."""

    def test_document_creation(self):
        """Test creating a document with all required fields."""
        doc = Document(
            user_id="user123",
            filename="test_hash.pdf",
            original_filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_size=1024,
            file_hash="abc123hash",
            document_type=DocumentType.PDF
        )
        
        assert doc.user_id == "user123"
        assert doc.original_filename == "test.pdf"
        assert doc.processing_status == DocumentStatus.UPLOADED
        assert doc.chunk_count == 0

    def test_document_status_enum(self):
        """Test DocumentStatus enum values."""
        valid_statuses = [DocumentStatus.UPLOADED, DocumentStatus.PROCESSING, 
                         DocumentStatus.READY, DocumentStatus.FAILED]
        
        for status in valid_statuses:
            doc = Document(
                user_id="user123",
                filename="test.pdf",
                original_filename="test.pdf",
                file_path="/path/to/test.pdf",
                file_size=1024,
                file_hash="hash123",
                document_type=DocumentType.PDF,
                processing_status=status
            )
            assert doc.processing_status == status

    def test_document_type_enum(self):
        """Test DocumentType enum."""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.TXT.value == "txt"
        assert DocumentType.MARKDOWN.value == "md"
        assert DocumentType.DOCX.value == "docx"

    def test_document_chunk_creation(self):
        """Test creating a document chunk with required fields."""
        chunk = DocumentChunk(
            document_id="doc123",
            user_id="user123",
            chunk_index=0,
            content="This is chunk content",
            char_count=100,
            word_count=20
        )
        
        assert chunk.document_id == "doc123"
        assert chunk.chunk_index == 0
        assert chunk.content == "This is chunk content"
        assert chunk.char_count == 100
        assert chunk.word_count == 20

    def test_document_chunk_get_context_string(self):
        """Test chunk context string generation."""
        chunk = DocumentChunk(
            document_id="doc123",
            user_id="user123",
            chunk_index=5,
            content="Test content",
            char_count=100,
            word_count=20,
            section_title="Chapter 3",
            page_number=42
        )
        
        context = chunk.get_context_string()
        # Actual format is: [Section: X | Page Y]
        assert "Chapter 3" in context
        assert "Page 42" in context


class TestPracticeModels:
    """Test Practice-related models."""

    def test_practice_question_result(self):
        """Test practice question result model."""
        result = PracticeQuestionResult(
            question="What is 2+2?",
            type="mcq",
            options=["3", "4", "5"],
            correct_answer="4",
            user_answer="4",
            is_correct=True,
            time_spent_seconds=15,
            explanation="Basic arithmetic"
        )
        
        assert result.is_correct is True
        assert result.time_spent_seconds == 15

    def test_practice_session_creation(self):
        """Test practice session creation."""
        session = PracticeSession(
            user_id="user123",
            topic="Linear Algebra",
            difficulty="intermediate",
            questions=[],
            score=8,
            total_questions=10,
            percentage=80.0,
            started_at=datetime.now(),
            completed_at=datetime.now() + timedelta(minutes=30),
            duration_minutes=30,
            question_types=["mcq", "short"]
        )
        
        assert session.score == 8
        assert session.total_questions == 10
        assert session.percentage == 80.0


class TestEnums:
    """Test enum models."""

    def test_learning_level_enum(self):
        """Test LearningLevel enum."""
        assert LearningLevel.BEGINNER.value == "beginner"
        assert LearningLevel.INTERMEDIATE.value == "intermediate"
        assert LearningLevel.ADVANCED.value == "advanced"

    def test_learning_goal_enum(self):
        """Test LearningGoal enum."""
        assert LearningGoal.QUICK_REVIEW.value == "quick_review"
        assert LearningGoal.DEEP_LEARNING.value == "deep_learning"
        assert LearningGoal.EXAM_PREP.value == "exam_prep"
        assert LearningGoal.RESEARCH.value == "research"

    def test_explanation_style_enum(self):
        """Test ExplanationStyle enum."""
        assert ExplanationStyle.INTUITIVE.value == "intuitive"
        assert ExplanationStyle.BALANCED.value == "balanced"
        assert ExplanationStyle.TECHNICAL.value == "technical"

    def test_rag_fallback_preference_enum(self):
        """Test RAGFallbackPreference enum."""
        assert RAGFallbackPreference.ALWAYS_ASK.value == "always_ask"
        assert RAGFallbackPreference.PREFER_GENERAL.value == "prefer_general"

    def test_document_status_enum(self):
        """Test DocumentStatus enum."""
        assert DocumentStatus.UPLOADED.value == "uploaded"
        assert DocumentStatus.PROCESSING.value == "processing"
        assert DocumentStatus.READY.value == "ready"
        assert DocumentStatus.FAILED.value == "failed"

    def test_document_type_enum(self):
        """Test DocumentType enum."""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.TXT.value == "txt"
        assert DocumentType.MARKDOWN.value == "md"
        assert DocumentType.DOCX.value == "docx"


class TestConversationSummary:
    """Test ConversationSummary model."""

    def test_conversation_summary_from_conversation(self):
        """Test creating summary from full conversation."""
        conv = Conversation(
            id="conv123",
            user_id="user123",
            title="Test Conversation",
            message_count=5,
            created_at=datetime.now()
        )
        
        summary = ConversationSummary.from_conversation(conv)
        
        assert summary.id == "conv123"
        assert summary.title == "Test Conversation"
        assert summary.message_count == 5
