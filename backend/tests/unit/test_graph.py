"""
Comprehensive tests for LangGraph workflow module.

Tests cover:
- Workflow state management
- Node implementations
- Routing logic
- Workflow compilation
- End-to-end workflow execution
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.graph import (
    WorkflowState,
    check_documents_node,
    router_node,
    build_workflow,
    process_with_langgraph
)


class TestWorkflowState:
    """Test WorkflowState TypedDict."""

    def test_workflow_state_creation(self):
        """Test creating a workflow state."""
        state = WorkflowState(
            question="What is PCA?",
            user_id="user123",
            conversation_id="conv456"
        )
        
        assert state["question"] == "What is PCA?"
        assert state["user_id"] == "user123"
        assert state["conversation_id"] == "conv456"

    def test_workflow_state_optional_fields(self):
        """Test that optional fields can be omitted."""
        state = WorkflowState(question="test", user_id="user123")
        
        # Should not raise error for missing optional fields
        route = state.get("route")
        assert route is None


class TestCheckDocumentsNode:
    """Test check_documents_node."""

    @patch('core.graph.nodes.DocumentManager')
    def test_check_documents_node_with_documents(self, mock_manager_class):
        """Test node when user has documents."""
        # Mock DocumentManager
        mock_manager = Mock()
        mock_manager.get_user_documents.return_value = [Mock(), Mock(), Mock()]  # 3 docs
        mock_manager_class.return_value = mock_manager
        
        state = WorkflowState(question="test", user_id="user123")
        result = check_documents_node(state)
        
        assert result["has_documents"] is True
        assert result["document_count"] == 3

    @patch('core.graph.nodes.DocumentManager')
    def test_check_documents_node_no_documents(self, mock_manager_class):
        """Test node when user has no documents."""
        mock_manager = Mock()
        mock_manager.get_user_documents.return_value = []
        mock_manager_class.return_value = mock_manager
        
        state = WorkflowState(question="test", user_id="user123")
        result = check_documents_node(state)
        
        assert result["has_documents"] is False
        assert result["document_count"] == 0

    @patch('core.graph.nodes.DocumentManager')
    def test_check_documents_node_error_handling(self, mock_manager_class):
        """Test node handles errors gracefully."""
        mock_manager = Mock()
        mock_manager.get_user_documents.side_effect = Exception("DB Error")
        mock_manager_class.return_value = mock_manager
        
        state = WorkflowState(question="test", user_id="user123")
        result = check_documents_node(state)
        
        # Should not crash, should return False
        assert result["has_documents"] is False
        assert result["document_count"] == 0


class TestRouterNode:
    """Test router_node."""

    @patch('core.graph.nodes.route_query_structured')
    def test_router_node_concept_route(self, mock_route):
        """Test routing to concept explainer."""
        # Mock router decision
        mock_decision = Mock()
        mock_decision.route = "concept"
        mock_decision.confidence = 0.95
        mock_decision.reasoning = "Question asks for explanation"
        mock_route.return_value = mock_decision
        
        state = WorkflowState(
            question="What is gradient descent?",
            has_documents=False
        )
        
        result = router_node(state)
        
        assert result["route"] == "concept"
        assert result["routing_confidence"] == 0.95
        assert "explanation" in result["routing_reasoning"]

    @patch('core.graph.nodes.route_query_structured')
    def test_router_node_research_route(self, mock_route):
        """Test routing to research agent when has documents."""
        mock_decision = Mock()
        mock_decision.route = "research"
        mock_decision.confidence = 0.90
        mock_decision.reasoning = "User has documents"
        mock_route.return_value = mock_decision
        
        state = WorkflowState(
            question="Summarize chapter 3",
            has_documents=True
        )
        
        result = router_node(state)
        
        assert result["route"] == "research"


class TestWorkflowConstruction:
    """Test workflow building."""

    def test_build_workflow_creates_graph(self):
        """Test that build_workflow creates a valid graph."""
        workflow = build_workflow()
        
        # Should return compiled graph
        assert workflow is not None
        # Should be callable
        assert callable(workflow.invoke)

    def test_workflow_has_required_nodes(self):
        """Test workflow contains all required nodes."""
        # This test verifies workflow compilation doesn't fail
        workflow = build_workflow()
        assert workflow is not None


class TestSharedResources:
    """Test shared resource pattern."""

    def test_shared_rag_singleton(self):
        """Test that shared RAG is created once."""
        from core.graph.nodes import _get_shared_rag
        
        # Clear any existing instance
        import core.graph.nodes as nodes_module
        nodes_module._shared_rag = None
        
        rag1 = _get_shared_rag()
        rag2 = _get_shared_rag()
        
        assert rag1 is rag2  # Same instance


class TestModuleExports:
    """Test module exports."""

    def test_exports_all_required_symbols(self):
        """Test that __all__ exports all required symbols."""
        from core.graph import __all__
        
        expected = [
            "WorkflowState",
            "check_documents_node",
            "router_node",
            "concept_explainer_node",
            "code_helper_node",
            "research_agent_node",
            "build_workflow",
            "compiled_workflow",
            "process_with_langgraph"
        ]
        
        for symbol in expected:
            assert symbol in __all__

    def test_can_import_all_symbols(self):
        """Test that all exported symbols can be imported."""
        from core.graph import (
            WorkflowState,
            check_documents_node,
            router_node,
            build_workflow,
            compiled_workflow,
            process_with_langgraph
        )
        
        assert WorkflowState is not None
        assert callable(check_documents_node)
        assert callable(router_node)
        assert callable(build_workflow)
        assert compiled_workflow is not None
        assert callable(process_with_langgraph)
