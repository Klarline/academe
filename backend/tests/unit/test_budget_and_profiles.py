"""
Tests for RequestBudget and RetrievalProfiles.

Covers:
- RequestBudget call tracking, exhaustion, retry limits, latency cap
- RetrievalProfile presets and pipeline-kwargs generation
- Profile auto-selection heuristic
- Budget wiring into graph nodes (grader, clarify)
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from core.rag.request_budget import RequestBudget
from core.rag.retrieval_profiles import (
    RetrievalProfile,
    ProfileName,
    get_profile,
    select_profile_for_query,
    FAST,
    BALANCED,
    DEEP,
)


# ---------------------------------------------------------------------------
# RequestBudget
# ---------------------------------------------------------------------------

class TestRequestBudget:

    def test_fresh_budget_allows_calls(self):
        b = RequestBudget()
        assert b.can_call_llm()
        assert b.can_retry()
        assert b.remaining_llm_calls == 8

    def test_use_llm_call_decrements(self):
        b = RequestBudget(max_llm_calls=3)
        assert b.use_llm_call()
        assert b.llm_calls_used == 1
        assert b.remaining_llm_calls == 2

    def test_budget_exhaustion_blocks_calls(self):
        b = RequestBudget(max_llm_calls=2)
        assert b.use_llm_call()
        assert b.use_llm_call()
        assert not b.can_call_llm()
        assert not b.use_llm_call()
        assert b.llm_calls_used == 2

    def test_retry_limits(self):
        b = RequestBudget(max_retries=1, max_llm_calls=10)
        assert b.can_retry()
        assert b.use_retry()
        assert not b.can_retry()
        assert not b.use_retry()

    def test_latency_cap(self):
        b = RequestBudget(max_latency_ms=1)
        time.sleep(0.01)
        assert not b.can_call_llm()

    def test_elapsed_ms(self):
        b = RequestBudget()
        time.sleep(0.05)
        assert b.elapsed_ms >= 40  # generous lower bound

    def test_to_dict(self):
        b = RequestBudget(max_llm_calls=5, max_retries=2, max_latency_ms=10_000)
        b.use_llm_call()
        d = b.to_dict()
        assert d["llm_calls_used"] == 1
        assert d["max_llm_calls"] == 5
        assert d["retries_used"] == 0
        assert d["max_retries"] == 2

    def test_str_repr(self):
        b = RequestBudget()
        s = str(b)
        assert "Budget(" in s
        assert "llm=" in s

    def test_retry_requires_llm_headroom(self):
        b = RequestBudget(max_llm_calls=0, max_retries=5)
        assert not b.can_retry()


# ---------------------------------------------------------------------------
# RetrievalProfiles
# ---------------------------------------------------------------------------

class TestRetrievalProfiles:

    def test_fast_disables_llm_enrichments(self):
        assert not FAST.use_query_rewriting
        assert not FAST.use_hyde
        assert not FAST.use_self_rag
        assert not FAST.use_query_decomposition
        assert not FAST.use_multi_query
        assert not FAST.use_propositions
        assert not FAST.use_knowledge_graph

    def test_fast_keeps_baseline_features(self):
        assert FAST.use_hybrid_search
        assert FAST.use_adaptive_retrieval
        assert FAST.use_response_cache

    def test_balanced_enables_quality_features(self):
        assert BALANCED.use_query_rewriting
        assert BALANCED.use_multi_query
        assert BALANCED.use_self_rag
        assert not BALANCED.use_hyde
        assert not BALANCED.use_query_decomposition

    def test_deep_enables_everything(self):
        assert DEEP.use_hyde
        assert DEEP.use_query_decomposition
        assert DEEP.use_propositions
        assert DEEP.use_knowledge_graph

    def test_to_pipeline_kwargs_keys(self):
        kwargs = BALANCED.to_pipeline_kwargs()
        expected_keys = {
            "use_hybrid_search", "use_query_rewriting", "use_hyde",
            "use_adaptive_retrieval", "use_multi_query", "use_self_rag",
            "use_query_decomposition", "use_response_cache",
            "use_propositions", "use_knowledge_graph",
        }
        assert set(kwargs.keys()) == expected_keys

    def test_get_profile_by_string(self):
        assert get_profile("fast") is FAST
        assert get_profile("balanced") is BALANCED
        assert get_profile("deep") is DEEP

    def test_get_profile_by_enum(self):
        assert get_profile(ProfileName.FAST) is FAST

    def test_get_profile_unknown_raises(self):
        with pytest.raises(ValueError):
            get_profile("turbo")

    def test_profiles_are_immutable(self):
        with pytest.raises(AttributeError):
            FAST.use_hyde = True


# ---------------------------------------------------------------------------
# Profile auto-selection heuristic
# ---------------------------------------------------------------------------

class TestProfileSelection:

    def test_short_query_selects_fast(self):
        assert select_profile_for_query("What is PCA?") is FAST

    def test_comparison_selects_deep(self):
        assert select_profile_for_query("Compare PCA vs t-SNE for visualization") is DEEP

    def test_step_by_step_selects_deep(self):
        assert select_profile_for_query("Walk me through the backpropagation algorithm step by step") is DEEP

    def test_medium_query_selects_balanced(self):
        assert select_profile_for_query(
            "Explain how gradient descent converges on a convex loss surface"
        ) is BALANCED


# ---------------------------------------------------------------------------
# Budget wiring in graph nodes
# ---------------------------------------------------------------------------

class TestBudgetInGraderNode:
    """Verify that response_grader_node respects budget exhaustion."""

    def test_grader_auto_passes_on_exhausted_budget(self):
        from core.graph.nodes import response_grader_node

        budget = RequestBudget(max_llm_calls=0)
        state = {
            "question": "What is PCA?",
            "response": "PCA is a dimensionality reduction technique.",
            "refinement_count": 0,
            "reroute_count": 0,
            "agent_used": "concept",
            "budget": budget,
        }
        result = response_grader_node(state)
        assert result["grader_verdict"] == "pass"

    @patch("core.config.get_openai_llm")
    def test_grader_uses_budget_when_available(self, mock_llm_factory):
        from core.graph.nodes import response_grader_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="PASS")
        mock_llm_factory.return_value = mock_llm

        budget = RequestBudget(max_llm_calls=5)
        state = {
            "question": "What is PCA?",
            "response": "PCA is a dimensionality reduction technique.",
            "refinement_count": 0,
            "reroute_count": 0,
            "agent_used": "concept",
            "budget": budget,
        }
        response_grader_node(state)
        assert budget.llm_calls_used == 1


class TestBudgetInClarifyNode:
    """Verify that clarify_query_node respects budget exhaustion."""

    def test_clarify_uses_static_fallback_on_exhausted_budget(self):
        from core.graph.nodes import clarify_query_node

        budget = RequestBudget(max_llm_calls=0)
        state = {
            "question": "PCA",
            "routing_reasoning": "ambiguous",
            "route": "concept",
            "budget": budget,
        }
        result = clarify_query_node(state)
        assert "clarify" in result["response"].lower() or "concept explanation" in result["response"].lower()
        assert result["agent_used"] == "clarify"

    @patch("core.config.get_openai_llm")
    def test_clarify_charges_budget(self, mock_llm_factory):
        from core.graph.nodes import clarify_query_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Could you clarify what you need?")
        mock_llm_factory.return_value = mock_llm

        budget = RequestBudget(max_llm_calls=5)
        state = {
            "question": "PCA",
            "routing_reasoning": "ambiguous",
            "route": "concept",
            "budget": budget,
        }
        clarify_query_node(state)
        assert budget.llm_calls_used == 1


# ---------------------------------------------------------------------------
# WorkflowState includes budget field
# ---------------------------------------------------------------------------

class TestBudgetInWorkflowState:

    def test_state_accepts_budget(self):
        from core.graph.state import WorkflowState

        budget = RequestBudget()
        state = WorkflowState(
            question="test",
            user_id="u1",
            conversation_id="c1",
            budget=budget,
        )
        assert state["budget"] is budget
