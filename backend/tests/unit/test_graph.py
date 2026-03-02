"""
Comprehensive tests for LangGraph workflow module.

Tests cover:
- Workflow state management
- Node implementations
- Routing logic
- Workflow compilation
- End-to-end workflow execution
- Enhanced workflow: response grader, clarification, re-routing, agent executor
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.graph import (
    WorkflowState,
    check_documents_node,
    router_node,
    build_workflow,
    process_with_langgraph,
    agent_executor_node,
    response_grader_node,
    clarify_query_node,
    re_router_node,
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
            "agent_executor_node",
            "response_grader_node",
            "clarify_query_node",
            "re_router_node",
            "build_workflow",
            "compiled_workflow",
            "process_with_langgraph",
            "process_with_langgraph_streaming",
        ]
        
        for symbol in expected:
            assert symbol in __all__

    def test_can_import_all_symbols(self):
        """Test that all exported symbols can be imported."""
        from core.graph import (
            WorkflowState,
            check_documents_node,
            router_node,
            agent_executor_node,
            response_grader_node,
            clarify_query_node,
            re_router_node,
            build_workflow,
            compiled_workflow,
            process_with_langgraph,
            process_with_langgraph_streaming,
        )
        
        assert WorkflowState is not None
        assert callable(check_documents_node)
        assert callable(router_node)
        assert callable(agent_executor_node)
        assert callable(response_grader_node)
        assert callable(clarify_query_node)
        assert callable(re_router_node)
        assert callable(build_workflow)
        assert compiled_workflow is not None
        assert callable(process_with_langgraph)
        assert callable(process_with_langgraph_streaming)


# ======================================================================
# Enhanced Workflow Tests
# ======================================================================


class TestWorkflowStateLoopFields:
    """Test the new loop-control fields on WorkflowState."""

    def test_loop_fields_default_absent(self):
        """Loop-control fields are optional (total=False)."""
        state = WorkflowState(question="test", user_id="u1")
        assert state.get("refinement_count") is None
        assert state.get("reroute_count") is None
        assert state.get("grader_feedback") is None
        assert state.get("grader_verdict") is None
        assert state.get("previous_agents") is None

    def test_loop_fields_can_be_set(self):
        state = WorkflowState(
            question="test",
            user_id="u1",
            refinement_count=0,
            reroute_count=0,
            previous_agents=[],
        )
        assert state["refinement_count"] == 0
        assert state["reroute_count"] == 0
        assert state["previous_agents"] == []


class TestAgentExecutorNode:
    """Test agent_executor_node dispatching."""

    @patch("core.graph.nodes.UserRepository")
    @patch("core.graph.nodes._get_concept_explainer")
    def test_dispatches_to_concept(self, mock_explainer_fn, mock_user_repo):
        mock_user_repo.return_value.get_user_by_id.return_value = Mock()
        mock_explainer = Mock()
        mock_explainer.explain.return_value = "PCA explanation"
        mock_explainer_fn.return_value = mock_explainer

        state = WorkflowState(
            question="What is PCA?",
            user_id="u1",
            route="concept",
            refinement_count=0,
            reroute_count=0,
            previous_agents=[],
        )

        result = agent_executor_node(state)
        assert result["response"] == "PCA explanation"
        assert result["agent_used"] == "concept"
        assert "concept" in result["previous_agents"]

    @patch("core.graph.nodes.UserRepository")
    @patch("core.graph.nodes._get_code_helper")
    def test_dispatches_to_code(self, mock_code_fn, mock_user_repo):
        mock_user_repo.return_value.get_user_by_id.return_value = Mock()
        mock_helper = Mock()
        mock_helper.generate_code.return_value = "def pca(): ..."
        mock_code_fn.return_value = mock_helper

        state = WorkflowState(
            question="Write PCA in Python",
            user_id="u1",
            route="code",
            refinement_count=0,
            reroute_count=0,
            previous_agents=[],
        )

        result = agent_executor_node(state)
        assert result["response"] == "def pca(): ..."
        assert result["agent_used"] == "code"

    @patch("core.graph.nodes.UserRepository")
    @patch("core.graph.nodes._get_concept_explainer")
    def test_appends_grader_feedback_to_question(self, mock_explainer_fn, mock_user_repo):
        mock_user_repo.return_value.get_user_by_id.return_value = Mock()
        mock_explainer = Mock()
        mock_explainer.explain.return_value = "Improved response"
        mock_explainer_fn.return_value = mock_explainer

        state = WorkflowState(
            question="Explain PCA",
            user_id="u1",
            route="concept",
            grader_feedback="Please include the math",
            refinement_count=1,
            reroute_count=0,
            previous_agents=["concept"],
        )

        agent_executor_node(state)
        call_args = mock_explainer.explain.call_args
        assert "Please include the math" in call_args.kwargs["question"]

    @patch("core.graph.nodes.UserRepository")
    @patch("core.graph.nodes._get_concept_explainer")
    def test_handles_error_gracefully(self, mock_explainer_fn, mock_user_repo):
        mock_user_repo.return_value.get_user_by_id.return_value = Mock()
        mock_explainer = Mock()
        mock_explainer.explain.side_effect = RuntimeError("LLM timeout")
        mock_explainer_fn.return_value = mock_explainer

        state = WorkflowState(
            question="test",
            user_id="u1",
            route="concept",
            refinement_count=0,
            reroute_count=0,
            previous_agents=[],
        )

        result = agent_executor_node(state)
        assert "Error" in result["response"]
        assert result["error"] == "LLM timeout"


class TestResponseGraderNode:
    """Test response_grader_node quality gate."""

    @patch("core.config.get_openai_llm")
    def test_pass_verdict(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="PASS")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="What is PCA?",
            user_id="u1",
            response="PCA is a dimensionality reduction technique...",
            agent_used="concept",
            refinement_count=0,
            reroute_count=0,
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "pass"

    @patch("core.config.get_openai_llm")
    def test_refine_verdict(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="REFINE: Missing mathematical formulation")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="Derive PCA mathematically",
            user_id="u1",
            response="PCA is used for dimensionality reduction.",
            agent_used="concept",
            refinement_count=0,
            reroute_count=0,
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "refine"
        assert "mathematical" in result["grader_feedback"].lower()
        assert result["refinement_count"] == 1

    @patch("core.config.get_openai_llm")
    def test_wrong_agent_verdict(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="WRONG_AGENT: code")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="Write PCA in Python",
            user_id="u1",
            response="PCA is a technique...",
            agent_used="concept",
            refinement_count=0,
            reroute_count=0,
            previous_agents=["concept"],
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "reroute"
        assert result["route"] == "code"
        assert result["reroute_count"] == 1

    @patch("core.config.get_openai_llm")
    def test_refine_respects_max_iterations(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="REFINE: still bad")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="test",
            user_id="u1",
            response="some response",
            agent_used="concept",
            refinement_count=2,  # already at max
            reroute_count=1,     # already at max
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "pass"

    @patch("core.config.get_openai_llm")
    def test_wrong_agent_skips_already_tried(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="WRONG_AGENT: concept")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="test",
            user_id="u1",
            response="some response",
            agent_used="concept",
            refinement_count=0,
            reroute_count=0,
            previous_agents=["concept"],  # already tried concept
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "pass"

    def test_error_state_triggers_reroute(self):
        """If agent errored, grader should try re-routing."""
        state = WorkflowState(
            question="test",
            user_id="u1",
            response="",
            agent_used="research",
            error="Connection timeout",
            refinement_count=0,
            reroute_count=0,
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "reroute"

    def test_error_state_passes_when_reroute_exhausted(self):
        state = WorkflowState(
            question="test",
            user_id="u1",
            response="",
            agent_used="research",
            error="Connection timeout",
            refinement_count=0,
            reroute_count=1,  # already used reroute
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "pass"

    @patch("core.config.get_openai_llm")
    def test_llm_failure_defaults_to_pass(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.side_effect = RuntimeError("API down")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="test",
            user_id="u1",
            response="some response",
            agent_used="concept",
            refinement_count=0,
            reroute_count=0,
        )

        result = response_grader_node(state)
        assert result["grader_verdict"] == "pass"


class TestClarifyQueryNode:
    """Test clarify_query_node."""

    @patch("core.config.get_openai_llm")
    def test_generates_clarification(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content="Are you looking for a concept explanation of PCA or a Python implementation?"
        )
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="PCA",
            user_id="u1",
            route="concept",
            routing_confidence=0.3,
            routing_reasoning="Ambiguous query",
        )

        result = clarify_query_node(state)
        assert result["agent_used"] == "clarify"
        assert len(result["response"]) > 0
        assert result["grader_verdict"] == "pass"

    @patch("core.config.get_openai_llm")
    def test_fallback_on_llm_error(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.side_effect = RuntimeError("API error")
        mock_llm_fn.return_value = mock_llm

        state = WorkflowState(
            question="PCA",
            user_id="u1",
            route="concept",
            routing_confidence=0.2,
        )

        result = clarify_query_node(state)
        assert "clarify" in result["response"].lower() or "concept explanation" in result["response"].lower()


class TestReRouterNode:
    """Test re_router_node."""

    def test_resets_transient_fields(self):
        state = WorkflowState(
            question="test",
            user_id="u1",
            route="code",
            previous_agents=["concept"],
            grader_feedback="wrong agent was used",
            error="some error",
            response="old response",
        )

        result = re_router_node(state)
        assert result["route"] == "code"
        assert result["grader_feedback"] is None
        assert result["error"] is None
        assert result["response"] == ""


class TestConfidenceGate:
    """Test confidence_gate conditional edge."""

    def test_low_confidence_returns_clarify(self):
        from core.graph.workflow import confidence_gate

        state = WorkflowState(
            question="test", user_id="u1", routing_confidence=0.3
        )
        assert confidence_gate(state) == "clarify"

    def test_high_confidence_returns_proceed(self):
        from core.graph.workflow import confidence_gate

        state = WorkflowState(
            question="test", user_id="u1", routing_confidence=0.9
        )
        assert confidence_gate(state) == "proceed"

    def test_threshold_boundary(self):
        from core.graph.workflow import confidence_gate
        from core.graph.nodes import CONFIDENCE_THRESHOLD

        state = WorkflowState(
            question="test", user_id="u1", routing_confidence=CONFIDENCE_THRESHOLD
        )
        assert confidence_gate(state) == "proceed"

        below = WorkflowState(
            question="test", user_id="u1", routing_confidence=CONFIDENCE_THRESHOLD - 0.01
        )
        assert confidence_gate(below) == "clarify"


class TestGradingDecision:
    """Test grading_decision conditional edge."""

    def test_pass_verdict(self):
        from core.graph.workflow import grading_decision

        state = WorkflowState(question="t", user_id="u", grader_verdict="pass")
        assert grading_decision(state) == "pass"

    def test_refine_verdict(self):
        from core.graph.workflow import grading_decision

        state = WorkflowState(question="t", user_id="u", grader_verdict="refine")
        assert grading_decision(state) == "refine"

    def test_reroute_verdict(self):
        from core.graph.workflow import grading_decision

        state = WorkflowState(question="t", user_id="u", grader_verdict="reroute")
        assert grading_decision(state) == "reroute"

    def test_missing_verdict_defaults_to_pass(self):
        from core.graph.workflow import grading_decision

        state = WorkflowState(question="t", user_id="u")
        assert grading_decision(state) == "pass"


class TestEnhancedWorkflowCompilation:
    """Test that the enhanced workflow compiles correctly."""

    def test_enhanced_workflow_compiles(self):
        workflow = build_workflow()
        assert workflow is not None
        assert callable(workflow.invoke)

    def test_workflow_singleton_is_valid(self):
        from core.graph.workflow import compiled_workflow

        assert compiled_workflow is not None
        assert callable(compiled_workflow.invoke)
