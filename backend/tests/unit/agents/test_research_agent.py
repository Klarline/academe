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
        """Should fall back to arXiv, then show message if arXiv also fails."""
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline,
            document_manager=mock_document_manager_empty
        )

        # arXiv returns no results → falls through to _no_documents_response
        with patch('core.agents.research_agent.arxiv_search_papers', return_value=[{"message": "No papers found"}]):
            result = agent.answer_question(
                question="What is in my documents?",
                user=sample_user
            )

        assert "haven't uploaded any documents" in result

    def test_should_use_arxiv_fallback_when_no_documents(
        self, mock_rag_pipeline, mock_document_manager_empty, sample_user
    ):
        """Should return arXiv-based answer when user has no documents but arXiv has results."""
        agent = ResearchAgent(
            rag_pipeline=mock_rag_pipeline,
            document_manager=mock_document_manager_empty
        )

        fake_papers = [
            {"title": "RAG Survey", "authors": ["Author A"], "abstract": "About RAG.",
             "published": "2024-01-01", "arxiv_url": "https://arxiv.org/abs/1234"}
        ]
        with patch('core.agents.research_agent.arxiv_search_papers', return_value=fake_papers), \
             patch('core.agents.research_agent.get_llm') as mock_llm_fn:
            mock_llm = Mock()
            mock_llm.invoke.return_value = Mock(content="RAG is a technique...")
            mock_llm_fn.return_value = mock_llm

            result = agent.answer_question(question="What is RAG?", user=sample_user)

        assert "RAG is a technique" in result
        assert "📄 Sources (arXiv)" in result
    
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
        """Should try arXiv fallback when RAG fails, then return error if both fail."""
        mock_rag = Mock()
        mock_rag.query_with_context.side_effect = Exception("RAG error")
        
        agent = ResearchAgent(
            rag_pipeline=mock_rag,
            document_manager=mock_document_manager_with_docs
        )

        # arXiv also fails → should return friendly error
        with patch('core.agents.research_agent.arxiv_search_papers', side_effect=Exception("Network error")):
            result = agent.answer_question("What is PCA?", sample_user)
        
        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "try again" in result.lower()

    def test_should_use_arxiv_when_rag_fails(
        self, mock_document_manager_with_docs, sample_user
    ):
        """Should fall back to arXiv successfully when RAG pipeline errors."""
        mock_rag = Mock()
        mock_rag.query_with_context.side_effect = Exception("RAG error")

        agent = ResearchAgent(
            rag_pipeline=mock_rag,
            document_manager=mock_document_manager_with_docs
        )

        fake_papers = [
            {"title": "PCA Explained", "authors": ["Auth"], "abstract": "PCA reduces dimensions.",
             "published": "2024-01-01", "arxiv_url": "https://arxiv.org/abs/5678"}
        ]
        with patch('core.agents.research_agent.arxiv_search_papers', return_value=fake_papers), \
             patch('core.agents.research_agent.get_llm') as mock_llm_fn:
            mock_llm = Mock()
            mock_llm.invoke.return_value = Mock(content="PCA is a dimensionality reduction method.")
            mock_llm_fn.return_value = mock_llm

            result = agent.answer_question("What is PCA?", sample_user)

        assert "PCA" in result
        assert "📄 Sources (arXiv)" in result
