"""
Tests for ResearchAgent.

Tests RAG-powered document Q&A with citations.
"""

import pytest
from unittest.mock import Mock, patch
from core.agents import ResearchAgent
from core.models import UserProfile


class TestResearchAgentInitialization:
    """Test ResearchAgent initialization."""
    
    def test_should_initialize_with_defaults(self):
        """Should create all dependencies if not provided."""
        agent = ResearchAgent()
        
        assert agent.rag_pipeline is not None
        assert agent.search_service is not None
        assert agent.document_manager is not None
    
    def test_should_use_injected_dependencies(
        self, mock_rag_pipeline, mock_document_manager_empty
    ):
        """Should use provided dependencies."""
        mock_search = Mock()
        
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline,
            search_service=mock_search,
            document_manager=mock_document_manager_empty
        )
        
        assert agent.rag_pipeline is mock_rag_pipeline
        assert agent.search_service is mock_search
        assert agent.document_manager is mock_document_manager_empty


class TestResearchAgentAnswerQuestion:
    """Test answer_question() method."""
    
    def test_should_return_no_documents_message_when_user_has_no_docs(
        self, mock_rag_pipeline, mock_document_manager_empty, sample_user
    ):
        """Should return helpful message when user has no documents."""
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline,
            document_manager=mock_document_manager_empty
        )
        
        result = agent.answer_question(
            question="What is in my documents?",
            user=sample_user
        )
        
        assert "haven't uploaded any documents" in result
        assert "upload" in result.lower()
    
    def test_should_query_rag_when_user_has_documents(
        self, mock_rag_pipeline_with_sources, mock_document_manager_with_docs, sample_user
    ):
        """Should use RAG to answer from documents."""
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline_with_sources,
            document_manager=mock_document_manager_with_docs
        )
        
        result = agent.answer_question(
            question="What does the document say about PCA?",
            user=sample_user
        )
        
        # Assert
        mock_rag_pipeline_with_sources.query_with_context.assert_called_once()
        assert isinstance(result, str)
    
    def test_should_include_citations_when_requested(
        self, mock_rag_pipeline_with_sources, mock_document_manager_with_docs, sample_user
    ):
        """Should add source citations to answer."""
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline_with_sources,
            document_manager=mock_document_manager_with_docs
        )
        
        result = agent.answer_question(
            question="What is transformers?",
            user=sample_user,
            use_citations=True
        )
        
        assert "📚 Sources:" in result
        assert "Machine Learning Textbook" in result
        assert "p. 42" in result
    
    def test_should_not_include_citations_when_not_requested(
        self, mock_rag_pipeline_with_sources, mock_document_manager_with_docs, sample_user
    ):
        """Should skip citations if use_citations=False."""
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline_with_sources,
            document_manager=mock_document_manager_with_docs
        )
        
        result = agent.answer_question(
            question="What is transformers?",
            user=sample_user,
            use_citations=False
        )
        
        assert "📚 Sources:" not in result


class TestResearchAgentOtherMethods:
    """Test other ResearchAgent methods."""
    
    def test_summarize_document_calls_rag_pipeline(
        self, mock_rag_pipeline, mock_document_manager_with_docs, sample_user
    ):
        """Should delegate to RAG pipeline for summarization."""
        mock_rag_pipeline.generate_summary.return_value = "Document summary here."
        
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline,
            document_manager=mock_document_manager_with_docs
        )
        
        result = agent.summarize_document("doc_123", sample_user)
        
        mock_rag_pipeline.generate_summary.assert_called_once_with(
            document_id="doc_123",
            user_id=sample_user.id,
            user=sample_user
        )
        assert result == "Document summary here."
    
    def test_compare_concepts_queries_both_concepts(
        self, mock_rag_pipeline, mock_document_manager_with_docs, sample_user
    ):
        """Should query RAG for both concepts when comparing."""
        mock_rag_pipeline.query_with_context.return_value = ("info", [])
        
        with patch('core.agents.research_agent.get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.invoke.return_value = Mock(content="Comparison result")
            mock_get_llm.return_value = mock_llm
            
            agent = ResearchAgent(
                rag_pipeline=mock_rag_pipeline,
                document_manager=mock_document_manager_with_docs
            )
            
            result = agent.compare_concepts("PCA", "LDA", sample_user)
            
            # Should query for both concepts
            assert mock_rag_pipeline.query_with_context.call_count == 2


class TestResearchAgentEdgeCases:
    """Test edge cases and error handling."""
    
    def test_should_handle_rag_failure_gracefully(
        self, mock_document_manager_with_docs, sample_user
    ):
        """Should return friendly error message when RAG fails."""
        mock_rag = Mock()
        mock_rag.query_with_context.side_effect = Exception("RAG error")
        
        agent = ResearchAgent(
            rag_pipeline=mock_rag,
            document_manager=mock_document_manager_with_docs
        )
        
        # Should NOT raise exception, should return friendly message
        result = agent.answer_question("What is PCA?", sample_user)
        
        # Should return error message string
        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "try again" in result.lower()
