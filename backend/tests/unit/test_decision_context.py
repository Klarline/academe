"""
Tests for DecisionContext — the unified decision object.

Covers:
- Recording and querying routing signals
- Recording and querying grading signals
- Loop counter management (refine, reroute)
- Limit enforcement (can_refine, can_reroute, loops_exhausted)
- next_action property for conditional edges
- Backward compatibility: _decision() creates from legacy state fields
- Serialization (to_dict, __str__)
- Integration: nodes write through DecisionContext and sync to legacy fields
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.graph.decision_context import DecisionContext
from core.graph.nodes import (
    _decision,
    _sync_decision_to_state,
    response_grader_node,
    router_node,
    re_router_node,
)
from core.graph.state import WorkflowState
from core.graph.workflow import confidence_gate, grading_decision


# ===================================================================
# DecisionContext unit tests
# ===================================================================

class TestDecisionContextDefaults:

    def test_default_values(self):
        ctx = DecisionContext()
        assert ctx.route == "concept"
        assert ctx.routing_confidence == 1.0
        assert ctx.grader_verdict is None
        assert ctx.refinement_count == 0
        assert ctx.reroute_count == 0
        assert ctx.previous_agents == []

    def test_should_clarify_false_by_default(self):
        ctx = DecisionContext()
        assert not ctx.should_clarify

    def test_next_action_defaults_to_pass(self):
        ctx = DecisionContext()
        assert ctx.next_action == "pass"


class TestRecordRouting:

    def test_records_all_fields(self):
        ctx = DecisionContext()
        ctx.record_routing("research", 0.85, "question mentions documents")
        assert ctx.route == "research"
        assert ctx.routing_confidence == 0.85
        assert ctx.routing_reasoning == "question mentions documents"

    def test_low_confidence_triggers_clarify(self):
        ctx = DecisionContext()
        ctx.record_routing("concept", 0.2, "ambiguous")
        assert ctx.should_clarify


class TestRecordGrading:

    def test_pass_verdict(self):
        ctx = DecisionContext()
        ctx.record_grading("pass")
        assert ctx.grader_verdict == "pass"
        assert ctx.next_action == "pass"
        assert ctx.refinement_count == 0

    def test_refine_increments_counter(self):
        ctx = DecisionContext()
        ctx.record_grading("refine", "missing math derivation")
        assert ctx.grader_verdict == "refine"
        assert ctx.grader_feedback == "missing math derivation"
        assert ctx.refinement_count == 1
        assert ctx.next_action == "refine"

    def test_reroute_increments_counter(self):
        ctx = DecisionContext()
        ctx.record_grading("reroute", "wrong agent")
        assert ctx.reroute_count == 1
        assert ctx.next_action == "reroute"

    def test_multiple_refines(self):
        ctx = DecisionContext()
        ctx.record_grading("refine", "feedback 1")
        ctx.record_grading("refine", "feedback 2")
        assert ctx.refinement_count == 2
        assert ctx.grader_feedback == "feedback 2"


class TestLimits:

    def test_can_refine_within_limit(self):
        ctx = DecisionContext(max_refinements=2)
        assert ctx.can_refine
        ctx.record_grading("refine", "f1")
        assert ctx.can_refine
        ctx.record_grading("refine", "f2")
        assert not ctx.can_refine

    def test_can_reroute_within_limit(self):
        ctx = DecisionContext(max_reroutes=1)
        assert ctx.can_reroute
        ctx.record_grading("reroute", "wrong")
        assert not ctx.can_reroute

    def test_loops_exhausted(self):
        ctx = DecisionContext(max_refinements=1, max_reroutes=1)
        assert not ctx.loops_exhausted
        ctx.record_grading("refine", "f")
        assert not ctx.loops_exhausted
        ctx.record_grading("reroute", "r")
        assert ctx.loops_exhausted


class TestAgentTracking:

    def test_record_agent_used(self):
        ctx = DecisionContext()
        ctx.record_agent_used("concept")
        ctx.record_agent_used("code")
        ctx.record_agent_used("concept")  # duplicate
        assert ctx.previous_agents == ["concept", "code"]

    def test_is_route_untried(self):
        ctx = DecisionContext()
        ctx.record_agent_used("concept")
        assert not ctx.is_route_untried("concept")
        assert ctx.is_route_untried("code")


class TestRecordReroute:

    def test_resets_transient_fields(self):
        ctx = DecisionContext()
        ctx.record_grading("reroute", "wrong agent")
        ctx.record_reroute("code")
        assert ctx.route == "code"
        assert ctx.grader_feedback is None
        assert ctx.grader_verdict is None


class TestSerialization:

    def test_to_dict(self):
        ctx = DecisionContext()
        ctx.record_routing("research", 0.9, "docs question")
        ctx.record_grading("pass")
        d = ctx.to_dict()
        assert d["route"] == "research"
        assert d["routing_confidence"] == 0.9
        assert d["grader_verdict"] == "pass"

    def test_str_repr(self):
        ctx = DecisionContext()
        s = str(ctx)
        assert "Decision(" in s
        assert "route=concept" in s


# ===================================================================
# _decision() helper — backward compatibility
# ===================================================================

class TestDecisionHelper:

    def test_creates_from_legacy_fields(self):
        state = WorkflowState(
            question="test",
            user_id="u1",
            route="code",
            routing_confidence=0.7,
            routing_reasoning="has code keywords",
            refinement_count=1,
            reroute_count=0,
            previous_agents=["concept"],
            grader_verdict="refine",
            grader_feedback="add more detail",
        )
        ctx = _decision(state)
        assert ctx.route == "code"
        assert ctx.routing_confidence == 0.7
        assert ctx.refinement_count == 1
        assert ctx.previous_agents == ["concept"]
        assert ctx.grader_verdict == "refine"

    def test_reuses_existing_context(self):
        ctx = DecisionContext(route="research")
        state = WorkflowState(
            question="test",
            user_id="u1",
            decision=ctx,
        )
        assert _decision(state) is ctx

    def test_attaches_to_state(self):
        state = WorkflowState(question="test", user_id="u1")
        ctx = _decision(state)
        assert state["decision"] is ctx


class TestSyncDecisionToState:

    def test_syncs_all_fields(self):
        ctx = DecisionContext()
        ctx.record_routing("code", 0.8, "code question")
        ctx.record_grading("refine", "needs examples")
        ctx.record_agent_used("concept")
        state = WorkflowState(question="test", user_id="u1", decision=ctx)
        _sync_decision_to_state(state)
        assert state["route"] == "code"
        assert state["routing_confidence"] == 0.8
        assert state["grader_verdict"] == "refine"
        assert state["grader_feedback"] == "needs examples"
        assert state["refinement_count"] == 1
        assert state["previous_agents"] == ["concept"]


# ===================================================================
# Conditional edges with DecisionContext
# ===================================================================

class TestConfidenceGateWithContext:

    def test_uses_decision_context(self):
        ctx = DecisionContext()
        ctx.record_routing("concept", 0.2, "ambiguous")
        state = WorkflowState(question="t", user_id="u", decision=ctx)
        assert confidence_gate(state) == "clarify"

    def test_proceed_via_context(self):
        ctx = DecisionContext()
        ctx.record_routing("concept", 0.9, "clear")
        state = WorkflowState(question="t", user_id="u", decision=ctx)
        assert confidence_gate(state) == "proceed"


class TestGradingDecisionWithContext:

    def test_uses_decision_context(self):
        ctx = DecisionContext()
        ctx.record_grading("refine", "feedback")
        state = WorkflowState(question="t", user_id="u", decision=ctx)
        assert grading_decision(state) == "refine"

    def test_pass_via_context(self):
        ctx = DecisionContext()
        ctx.record_grading("pass")
        state = WorkflowState(question="t", user_id="u", decision=ctx)
        assert grading_decision(state) == "pass"

    def test_reroute_via_context(self):
        ctx = DecisionContext()
        ctx.record_grading("reroute", "wrong")
        state = WorkflowState(question="t", user_id="u", decision=ctx)
        assert grading_decision(state) == "reroute"


# ===================================================================
# Integration: nodes write through DecisionContext
# ===================================================================

class TestRouterNodeIntegration:

    @patch("core.graph.nodes.route_query_structured")
    def test_router_writes_to_decision_context(self, mock_route):
        mock_route.return_value = Mock(route="research", confidence=0.88, reasoning="mentions papers")
        ctx = DecisionContext()
        state = WorkflowState(
            question="Find papers on attention",
            user_id="u1",
            has_documents=True,
            decision=ctx,
        )
        result = router_node(state)
        assert ctx.route == "research"
        assert ctx.routing_confidence == 0.88
        assert result["route"] == "research"


class TestGraderNodeIntegration:

    @patch("core.config.get_openai_llm")
    def test_grader_writes_to_decision_context(self, mock_llm_fn):
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="REFINE: needs more depth")
        mock_llm_fn.return_value = mock_llm

        ctx = DecisionContext()
        state = WorkflowState(
            question="Explain PCA",
            user_id="u1",
            response="PCA reduces dimensions.",
            agent_used="concept",
            decision=ctx,
        )
        response_grader_node(state)
        assert ctx.grader_verdict == "refine"
        assert ctx.refinement_count == 1
        assert state["grader_verdict"] == "refine"
        assert state["refinement_count"] == 1


class TestReRouterNodeIntegration:

    def test_re_router_writes_to_decision_context(self):
        ctx = DecisionContext()
        ctx.record_grading("reroute", "wrong agent")
        ctx.route = "code"
        ctx.record_agent_used("concept")
        state = WorkflowState(
            question="test",
            user_id="u1",
            route="code",
            previous_agents=["concept"],
            decision=ctx,
            grader_feedback="wrong agent",
            error="some error",
            response="old",
        )
        result = re_router_node(state)
        assert ctx.grader_feedback is None
        assert ctx.grader_verdict is None
        assert result["error"] is None
        assert result["response"] == ""
        assert result["grader_feedback"] is None
