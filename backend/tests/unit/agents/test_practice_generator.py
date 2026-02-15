"""
Tests for PracticeGenerator Agent.

Tests practice question generation with memory-adaptive difficulty.
"""

import pytest
from unittest.mock import Mock, patch
from core.agents import PracticeGenerator
from core.models import UserProfile, LearningLevel, RAGFallbackPreference


class TestPracticeGeneratorInitialization:
    """Test PracticeGenerator initialization."""
    
    def test_should_initialize_with_defaults(self):
        """Should create RAG and DocumentManager if not provided."""
        generator = PracticeGenerator()
        
        assert generator.rag_pipeline is not None
        assert generator.document_manager is not None
    
    def test_should_use_injected_dependencies(self, mock_rag_pipeline):
        """Should use provided dependencies."""
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline)
        
        assert generator.rag_pipeline is mock_rag_pipeline


class TestPracticeGeneratorQuestionGeneration:
    """Test practice question generation."""
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_generate_questions_with_documents(
        self, mock_get_llm, mock_rag_pipeline_with_sources, sample_user
    ):
        """Should generate questions using document context."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        
        # Mock response with questions
        from core.models.agent_responses import PracticeSetResponse, PracticeQuestion
        mock_questions = [
            PracticeQuestion(
                question_text="What is gradient descent?",
                question_type="mcq",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation here"
            )
        ]
        mock_practice_response = PracticeSetResponse(
            questions=mock_questions,
            topic="Machine Learning",
            difficulty_level="intermediate"
        )
        mock_structured_llm.invoke.return_value = mock_practice_response
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline_with_sources)
        
        # Act
        result = generator.generate_practice_set(
            topic="Machine Learning",
            user=sample_user,
            num_questions=5
        )
        
        # Assert
        assert "questions" in result
        assert len(result["questions"]) > 0
        assert result["topic"] == "Machine Learning"
        mock_rag_pipeline_with_sources.query_with_context.assert_called_once()
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_handle_strict_documents_preference(
        self, mock_get_llm, mock_rag_pipeline
    ):
        """Should return error when user wants strict documents but has none."""
        # Arrange
        mock_rag_pipeline.query_with_context.return_value = ("", [])
        
        user = Mock()
        user.rag_fallback_preference = RAGFallbackPreference.STRICT_DOCUMENTS
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline)
        
        # Act
        result = generator.generate_practice_set(
            topic="PCA",
            user=user,
            num_questions=5
        )
        
        # Assert
        assert "error" in result
        assert "upload" in result["error"].lower()
        assert result["questions"] == []
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_use_general_knowledge_with_prefer_general(
        self, mock_get_llm, mock_rag_pipeline, sample_user
    ):
        """Should use general knowledge when user prefers it."""
        # Arrange
        mock_rag_pipeline.query_with_context.return_value = ("", [])
        sample_user.rag_fallback_preference = RAGFallbackPreference.PREFER_GENERAL
        
        # Mock LLM
        mock_llm = Mock()
        mock_structured_llm = Mock()
        from core.models.agent_responses import PracticeSetResponse, PracticeQuestion
        mock_q = PracticeQuestion(
            question_text="Q1",
            question_type="short",
            correct_answer="A1",
            explanation="Exp"
        )
        mock_structured_llm.invoke.return_value = PracticeSetResponse(
            questions=[mock_q],
            topic="Neural Networks",
            difficulty_level="intermediate"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline)
        
        # Act
        result = generator.generate_practice_set(
            topic="Neural Networks",
            user=sample_user,
            num_questions=3
        )
        
        # Assert
        assert "questions" in result
        assert len(result["questions"]) > 0
        assert "General knowledge" in result["sources"]
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_generate_different_question_types(
        self, mock_get_llm, mock_rag_pipeline_with_sources, sample_user
    ):
        """Should generate MCQ, short answer, and explain question types."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        
        from core.models.agent_responses import PracticeSetResponse, PracticeQuestion
        mock_questions = [
            PracticeQuestion(
                question_text="MCQ question",
                question_type="mcq",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="MCQ explanation"
            ),
            PracticeQuestion(
                question_text="Short answer question",
                question_type="short",
                correct_answer="Short answer",
                explanation="Short explanation"
            ),
            PracticeQuestion(
                question_text="Explain question",
                question_type="explain",
                correct_answer="Detailed explanation",
                explanation="Explanation of explanation"
            )
        ]
        mock_structured_llm.invoke.return_value = PracticeSetResponse(
            questions=mock_questions,
            topic="Test",
            difficulty_level="intermediate"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline_with_sources)
        
        # Act
        result = generator.generate_practice_set(
            topic="ML",
            user=sample_user,
            num_questions=3,
            question_types=["mcq", "short", "explain"]
        )
        
        # Assert
        questions = result["questions"]
        assert len(questions) == 3
        types = [q["type"] for q in questions]
        assert "mcq" in types
        assert "short" in types
        assert "explain" in types
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_skip_questions_with_empty_answers(
        self, mock_get_llm, mock_rag_pipeline_with_sources, sample_user
    ):
        """Should skip questions that have empty answers."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        
        from core.models.agent_responses import PracticeSetResponse, PracticeQuestion
        mock_questions = [
            PracticeQuestion(
                question_text="Good question",
                question_type="short",
                correct_answer="Good answer",
                explanation="Good explanation"
            ),
            PracticeQuestion(
                question_text="Bad question",
                question_type="short",
                correct_answer="",  # Empty answer - should be skipped!
                explanation="Explanation"
            )
        ]
        mock_structured_llm.invoke.return_value = PracticeSetResponse(
            questions=mock_questions,
            topic="Test",
            difficulty_level="intermediate"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline_with_sources)
        
        # Act
        result = generator.generate_practice_set("Test", sample_user, num_questions=2)
        
        # Assert
        assert len(result["questions"]) == 1  # Only valid question
        assert result["questions"][0]["answer"] == "Good answer"
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_skip_mcq_without_options(
        self, mock_get_llm, mock_rag_pipeline_with_sources, sample_user
    ):
        """Should skip MCQ questions that don't have 4 options."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        
        from core.models.agent_responses import PracticeSetResponse, PracticeQuestion
        mock_questions = [
            PracticeQuestion(
                question_text="Good MCQ",
                question_type="mcq",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation"
            ),
            PracticeQuestion(
                question_text="Bad MCQ",
                question_type="mcq",
                options=["A", "B"],  # Only 2 options - invalid!
                correct_answer="A",
                explanation="Explanation"
            )
        ]
        mock_structured_llm.invoke.return_value = PracticeSetResponse(
            questions=mock_questions,
            topic="Test",
            difficulty_level="intermediate"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline_with_sources)
        
        # Act
        result = generator.generate_practice_set("Test", sample_user, num_questions=2)
        
        # Assert
        assert len(result["questions"]) == 1  # Only valid MCQ
        assert result["questions"][0]["type"] == "mcq"
        assert len(result["questions"][0]["options"]) == 4


class TestPracticeGeneratorMemoryIntegration:
    """Test memory-adaptive question generation."""
    
    @patch('core.agents.practice_generator.get_llm')
    def test_should_focus_on_weak_areas_from_memory(
        self, mock_get_llm, mock_rag_pipeline_with_sources, sample_user
    ):
        """Should generate more questions on weak areas from memory."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        from core.models.agent_responses import PracticeSetResponse, PracticeQuestion
        mock_q = PracticeQuestion(
            question_text="Q", question_type="short",
            correct_answer="A", explanation="E"
        )
        mock_structured_llm.invoke.return_value = PracticeSetResponse(
            questions=[mock_q],
            topic="Statistics",
            difficulty_level="intermediate"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        generator = PracticeGenerator(rag_pipeline=mock_rag_pipeline_with_sources)
        
        memory_context = {
            "weak_areas": ["calculus", "probability"]
        }
        
        # Act
        result = generator.generate_practice_set(
            topic="Statistics",
            user=sample_user,
            num_questions=5,
            memory_context=memory_context
        )
        
        # Assert
        # Check that LLM prompt included weak areas
        call_args = mock_structured_llm.invoke.call_args
        prompt = call_args[0][0]
        assert "weak" in prompt.lower() or "struggling" in prompt.lower()
        assert "calculus" in prompt or "probability" in prompt
