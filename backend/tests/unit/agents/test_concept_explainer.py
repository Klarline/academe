"""
Tests for ConceptExplainer Agent - FIXED VERSION

Tests the personalized concept explanation functionality with RAG and memory support.
"""

import pytest
from unittest.mock import Mock, patch
from core.agents import ConceptExplainer
from core.models import UserProfile, LearningLevel, ExplanationStyle


class TestConceptExplainerInitialization:
    """Test ConceptExplainer initialization."""
    
    def test_should_initialize_with_defaults(self):
        """Should create RAG pipeline and DocumentManager if not provided."""
        explainer = ConceptExplainer()
        
        assert explainer.rag_pipeline is not None
        assert explainer.document_manager is not None
    
    def test_should_use_injected_rag_pipeline(self, mock_rag_pipeline):
        """Should use provided RAG pipeline instead of creating new one."""
        explainer = ConceptExplainer(rag_pipeline=mock_rag_pipeline)
        
        assert explainer.rag_pipeline is mock_rag_pipeline
    
    def test_should_use_injected_document_manager(self, mock_document_manager_empty):
        """Should use provided DocumentManager instead of creating new one."""
        explainer = ConceptExplainer(document_manager=mock_document_manager_empty)
        
        assert explainer.document_manager is mock_document_manager_empty
    
    def test_should_use_both_injected_dependencies(
        self, mock_rag_pipeline, mock_document_manager_empty
    ):
        """Should use both injected dependencies."""
        explainer = ConceptExplainer(
            rag_pipeline=mock_rag_pipeline,
            document_manager=mock_document_manager_empty
        )
        
        assert explainer.rag_pipeline is mock_rag_pipeline
        assert explainer.document_manager is mock_document_manager_empty


class TestConceptExplainerExplain:
    """Test main explain() method."""
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_explain_without_user_profile(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        mock_llm_concept_response, setup_mock_llm
    ):
        """Should generate explanation even without user profile."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_concept_response)
        
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = explainer.explain("What is PCA?")
        
        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Intuitive Explanation" in result
        assert "Technical Explanation" in result
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_explain_with_user_profile(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        sample_user, mock_llm_concept_response, setup_mock_llm
    ):
        """Should personalize explanation based on user profile."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_concept_response)
        
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = explainer.explain("What is gradient descent?", sample_user)
        
        # Assert
        assert isinstance(result, str)
        assert "Key Takeaway" in result
        assert "Why This Matters" in result
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_use_rag_when_user_has_documents(
        self, mock_get_llm, mock_rag_pipeline_with_sources,
        mock_document_manager_with_docs, sample_user, mock_llm_concept_response, setup_mock_llm
    ):
        """Should query RAG pipeline when user has documents."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_concept_response)
        
        explainer = ConceptExplainer(
            mock_rag_pipeline_with_sources,
            mock_document_manager_with_docs
        )
        
        # Act
        result = explainer.explain("What is PCA?", sample_user)
        
        # Assert
        mock_rag_pipeline_with_sources.query_with_context.assert_called_once()
        assert "Enhanced using your documents" in result
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_not_use_rag_when_no_documents(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        sample_user, mock_llm_concept_response, setup_mock_llm
    ):
        """Should not query RAG when user has no documents."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_concept_response)
        
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = explainer.explain("What is PCA?", sample_user)
        
        # Assert
        mock_rag_pipeline.query_with_context.assert_not_called()
        assert "Enhanced using your documents" not in result
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_include_memory_context(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        sample_user, sample_memory_context, mock_llm_concept_response, setup_mock_llm
    ):
        """Should include memory context in prompt."""
        # Arrange
        mock_llm = setup_mock_llm(mock_get_llm, mock_llm_concept_response)
        
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = explainer.explain("What is PCA?", sample_user, sample_memory_context)
        
        # Assert
        call_args = mock_llm.with_structured_output.return_value.invoke.call_args
        prompt = call_args[0][0]
        
        assert "LEARNING CONTEXT" in prompt
        assert "linear algebra" in prompt
        assert "weak areas" in prompt.lower() or "struggling" in prompt.lower()


class TestConceptExplainerPrivateMethods:
    """Test private helper methods."""
    
    def test_get_document_context_returns_empty_when_no_user(
        self, mock_rag_pipeline, mock_document_manager_empty
    ):
        """Should return empty context when no user profile."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        doc_context, has_rag = explainer._get_document_context("What is PCA?", None)
        
        assert doc_context == ""
        assert has_rag is False
    
    def test_build_memory_context_formats_correctly(
        self, mock_rag_pipeline, mock_document_manager_empty, sample_memory_context
    ):
        """Should format memory context into readable string."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        result = explainer._build_memory_context(sample_memory_context)
        
        assert "Recently studied: linear algebra, matrices, eigenvalues" in result
        assert "Struggling with: calculus, probability" in result
        assert "Current focus: PCA" in result
        assert "follow-up" in result.lower()
    
    def test_build_memory_context_returns_empty_when_none(
        self, mock_rag_pipeline, mock_document_manager_empty
    ):
        """Should return empty string when no memory context."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        result = explainer._build_memory_context(None)
        assert result == ""
        
        result = explainer._build_memory_context({})
        assert result == ""
    
    def test_get_personalized_instructions_for_beginner(
        self, mock_rag_pipeline, mock_document_manager_empty, beginner_user
    ):
        """Should generate beginner-appropriate instructions."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        instructions = explainer._get_personalized_instructions(beginner_user)
        
        assert "simple" in instructions.lower()
        assert "analogies" in instructions.lower()
        assert "BEGINNER" in instructions or "beginner" in instructions.lower()
    
    def test_get_personalized_instructions_for_advanced(
        self, mock_rag_pipeline, mock_document_manager_empty, advanced_user
    ):
        """Should generate advanced-level instructions."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        instructions = explainer._get_personalized_instructions(advanced_user)
        
        assert "rigorous" in instructions.lower() or "advanced" in instructions.lower()
        assert "mathematical" in instructions.lower() or "formulas" in instructions.lower()
    
    def test_format_response_includes_all_sections(
        self, mock_rag_pipeline, mock_document_manager_empty, mock_llm_concept_response
    ):
        """Should format response with all required sections."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        result = explainer._format_response(mock_llm_concept_response, has_rag_context=False)
        
        assert "## Intuitive Explanation" in result
        assert "## Technical Explanation" in result
        assert "## Key Takeaway" in result
        assert "## Why This Matters" in result
    
    def test_format_response_includes_rag_note_when_used(
        self, mock_rag_pipeline, mock_document_manager_empty, mock_llm_concept_response
    ):
        """Should add document enhancement note when RAG is used."""
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        result = explainer._format_response(mock_llm_concept_response, has_rag_context=True)
        
        assert "Enhanced using your documents" in result


class TestConceptExplainerEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_handle_rag_failure_gracefully(
        self, mock_get_llm, sample_user, mock_llm_concept_response, setup_mock_llm
    ):
        """Should continue without RAG if it fails."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_concept_response)
        
        mock_rag = Mock()
        mock_rag.query_with_context.side_effect = Exception("RAG failed")
        
        mock_doc_manager = Mock()
        mock_doc_manager.get_user_documents.return_value = ["doc.pdf"]
        
        explainer = ConceptExplainer(mock_rag, mock_doc_manager)
        
        # Act
        result = explainer.explain("What is PCA?", sample_user)
        
        # Assert - should still return result
        assert isinstance(result, str)
        assert len(result) > 0
    
    @patch('core.agents.concept_explainer.get_llm')
    def test_should_handle_response_with_missing_fields(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty, setup_mock_llm
    ):
        """Should handle response even if some fields are None."""
        # Arrange
        mock_response = Mock()
        mock_response.intuitive_explanation = "Simple explanation"
        mock_response.technical_explanation = None  
        mock_response.key_takeaway = "Key point"
        mock_response.why_matters = "Matters"
        mock_response.concepts_covered = []
        
        setup_mock_llm(mock_get_llm, mock_response)
        
        explainer = ConceptExplainer(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = explainer.explain("What is PCA?")
        
        # Assert
        assert isinstance(result, str)
        assert "Intuitive Explanation" in result
        assert "Technical Explanation" not in result 
