"""
Tests for CodeHelper Agent - FIXED VERSION

Tests code generation functionality with RAG support for code examples.
"""

import pytest
from unittest.mock import Mock, patch
from core.agents import CodeHelper
from core.models import UserProfile, LearningLevel


class TestCodeHelperInitialization:
    """Test CodeHelper initialization."""
    
    def test_should_initialize_with_defaults(self):
        """Should create RAG pipeline and DocumentManager if not provided."""
        helper = CodeHelper()
        
        assert helper.rag_pipeline is not None
        assert helper.document_manager is not None
    
    def test_should_use_injected_dependencies(self, mock_rag_pipeline, mock_document_manager_empty):
        """Should use provided dependencies instead of creating new ones."""
        helper = CodeHelper(
            rag_pipeline=mock_rag_pipeline,
            document_manager=mock_document_manager_empty
        )
        
        assert helper.rag_pipeline is mock_rag_pipeline
        assert helper.document_manager is mock_document_manager_empty


class TestCodeHelperGenerateCode:
    """Test main generate_code() method."""
    
    @patch('core.agents.code_helper.get_llm')
    def test_should_generate_code_without_user(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        mock_llm_code_response, setup_mock_llm
    ):
        """Should generate code even without user profile."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_code_response)
        
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = helper.generate_code("Implement binary search")
        
        # Assert
        assert isinstance(result, str)
        assert "## Implementation" in result
        assert "```python" in result
        assert "def example" in result
    
    @patch('core.agents.code_helper.get_llm')
    def test_should_generate_code_with_user_profile(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        sample_user, mock_llm_code_response, setup_mock_llm
    ):
        """Should personalize code based on user profile."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_code_response)
        
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = helper.generate_code("Implement gradient descent", sample_user)
        
        # Assert
        assert isinstance(result, str)
        assert "## Implementation" in result
        assert "## Usage Example" in result
        assert "## How It Works" in result
    
    @patch('core.vectors.SemanticSearchService')
    @patch('core.agents.code_helper.get_llm')
    def test_should_search_for_code_examples_when_documents_exist(
        self, mock_get_llm, mock_search_service_class,
        mock_document_manager_with_docs, sample_user, mock_llm_code_response, setup_mock_llm
    ):
        """Should search for code chunks when user has documents."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_code_response)
        
        # Mock search service
        mock_search_instance = Mock()
        mock_result = Mock()
        mock_result.document.title = "Code Examples"
        mock_result.chunk.content = "def example(): pass"
        mock_result.chunk.page_number = 10
        mock_search_instance.search.return_value = [mock_result]
        mock_search_service_class.return_value = mock_search_instance
        
        mock_rag = Mock()
        helper = CodeHelper(mock_rag, mock_document_manager_with_docs)
        
        # Act
        result = helper.generate_code("Implement sorting", sample_user)
        
        # Assert
        mock_search_instance.search.assert_called_once()
        call_kwargs = mock_search_instance.search.call_args[1]
        assert call_kwargs['filter_has_code'] is True
        assert "Informed by examples from your documents" in result
    
    @patch('core.agents.code_helper.get_llm')
    def test_should_include_memory_context(
        self, mock_get_llm, mock_rag_pipeline, mock_document_manager_empty,
        sample_user, sample_memory_context, mock_llm_code_response, setup_mock_llm
    ):
        """Should include memory context about user's knowledge."""
        # Arrange
        mock_llm = setup_mock_llm(mock_get_llm, mock_llm_code_response)
        
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        # Act
        result = helper.generate_code(
            "Implement matrix multiplication",
            sample_user,
            sample_memory_context
        )
        
        # Assert
        call_args = mock_llm.with_structured_output.return_value.invoke.call_args
        prompt = call_args[0][0]
        assert "CONTEXT" in prompt or "familiar with" in prompt.lower()


class TestCodeHelperPrivateMethods:
    """Test private helper methods."""
    
    def test_build_memory_context_formats_correctly(
        self, mock_rag_pipeline, mock_document_manager_empty
    ):
        """Should format memory context string."""
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        memory = {
            "relevant_concepts": ["numpy", "pandas"],
            "weak_areas": ["optimization"]
        }
        
        result = helper._build_memory_context(memory)
        
        assert "User familiar with: numpy, pandas" in result
        assert "simpler approach for: optimization" in result
    
    def test_get_code_instructions_for_beginner(
        self, mock_rag_pipeline, mock_document_manager_empty, beginner_user
    ):
        """Should generate beginner-appropriate code instructions."""
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        instructions = helper._get_code_instructions(beginner_user)
        
        assert "simple" in instructions.lower()
        assert "comments" in instructions.lower()
        assert "beginner" in instructions.lower()
    
    def test_get_code_instructions_for_advanced(
        self, mock_rag_pipeline, mock_document_manager_empty, advanced_user
    ):
        """Should generate advanced-level code instructions."""
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        instructions = helper._get_code_instructions(advanced_user)
        
        assert "advanced" in instructions.lower() or "optimize" in instructions.lower()
    
    def test_format_response_includes_complexity_analysis(
        self, mock_rag_pipeline, mock_document_manager_empty, mock_llm_code_response, sample_user
    ):
        """Should include complexity analysis in formatted output."""
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        result = helper._format_response(mock_llm_code_response, sample_user, False)
        
        assert "## Complexity Analysis" in result
        assert "Time: O(n)" in result
        assert "Space: O(1)" in result
    
    def test_format_response_uses_correct_language(
        self, mock_rag_pipeline, mock_document_manager_empty, mock_llm_code_response
    ):
        """Should use user's preferred programming language."""
        helper = CodeHelper(mock_rag_pipeline, mock_document_manager_empty)
        
        user = Mock()
        user.preferred_code_language = "javascript"
        
        result = helper._format_response(mock_llm_code_response, user, False)
        
        assert "```javascript" in result


class TestCodeHelperEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('core.vectors.SemanticSearchService')
    @patch('core.agents.code_helper.get_llm')
    def test_should_fallback_to_general_search_when_no_code_chunks(
        self, mock_get_llm, mock_search_service_class,
        mock_document_manager_with_docs, sample_user, mock_llm_code_response, setup_mock_llm
    ):
        """Should use general RAG search if no code chunks found."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_code_response)
        
        # Mock search service returns no code chunks
        mock_search_instance = Mock()
        mock_search_instance.search.return_value = []
        mock_search_service_class.return_value = mock_search_instance
        
        # But RAG has general context
        mock_rag = Mock()
        mock_source = Mock()
        mock_rag.query_with_context.return_value = ("general content", [mock_source])
        
        helper = CodeHelper(mock_rag, mock_document_manager_with_docs)
        
        # Act
        result = helper.generate_code("Implement sorting", sample_user)
        
        # Assert
        mock_search_instance.search.assert_called_once()
        mock_rag.query_with_context.assert_called_once()  # Fallback was used
    
    @patch('core.agents.code_helper.get_llm')
    def test_should_handle_rag_failure_gracefully(
        self, mock_get_llm, sample_user, mock_llm_code_response, setup_mock_llm
    ):
        """Should generate code even if RAG fails."""
        # Arrange
        setup_mock_llm(mock_get_llm, mock_llm_code_response)
        
        mock_rag = Mock()
        mock_rag.query_with_context.side_effect = Exception("RAG error")
        
        mock_doc_manager = Mock()
        mock_doc_manager.get_user_documents.return_value = ["doc.pdf"]
        
        helper = CodeHelper(mock_rag, mock_doc_manager)
        
        # Act
        result = helper.generate_code("Implement search", sample_user)
        
        # Assert - should still generate code
        assert isinstance(result, str)
        assert "## Implementation" in result
