"""
LangGraph workflow definition for Academe

Defines the complete multi-agent workflow using LangGraph.
Supports both batch processing and real-time streaming.

Graph topology:

    check_documents → router → confidence_gate
        ├── low confidence  → clarify_query → END
        └── sufficient      → agent_executor → response_grader
                                  ↑                 │
                                  │   ┌─────────────┤
                                  │   │ PASS → END
                                  │   │ REFINE (max 2) ──→ agent_executor
                                  │   │ WRONG_AGENT (max 1) → re_router ──→ agent_executor
"""

import logging
from typing import Literal, AsyncGenerator, Dict, Any

from langgraph.graph import StateGraph, END

from core.graph.state import WorkflowState
from core.rag.request_budget import RequestBudget
from core.graph.nodes import (
    check_documents_node,
    router_node,
    agent_executor_node,
    response_grader_node,
    clarify_query_node,
    re_router_node,
    CONFIDENCE_THRESHOLD,
    # Legacy individual nodes kept for streaming path
    concept_explainer_node_streaming,
    code_helper_node_streaming,
    research_agent_node_streaming,
    practice_generator_node_streaming,
)

logger = logging.getLogger(__name__)


# ─── Conditional edge functions ───────────────────────────────────────────────

def confidence_gate(state: WorkflowState) -> Literal["proceed", "clarify"]:
    """Route based on routing confidence: low → clarify, sufficient → execute."""
    confidence = state.get("routing_confidence", 1.0)
    if confidence < CONFIDENCE_THRESHOLD:
        logger.info(f"Confidence gate: {confidence:.2f} < {CONFIDENCE_THRESHOLD} → clarify")
        return "clarify"
    return "proceed"


def grading_decision(state: WorkflowState) -> Literal["pass", "refine", "reroute"]:
    """Route based on grader verdict: pass → END, refine → agent, reroute → re_router."""
    verdict = state.get("grader_verdict", "pass")
    if verdict == "refine":
        return "refine"
    if verdict == "reroute":
        return "reroute"
    return "pass"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Build the enhanced LangGraph workflow with quality gate and loops.

    Topology:
        check_documents → router → confidence_gate
            ├── clarify  → clarify_query → END
            └── proceed  → agent_executor → response_grader
                              ↑                   │
                              ├── refine ─────────┘
                              └── reroute → re_router
    """
    workflow = StateGraph(WorkflowState)

    # ── Nodes ──
    workflow.add_node("check_documents", check_documents_node)
    workflow.add_node("router", router_node)
    workflow.add_node("clarify_query", clarify_query_node)
    workflow.add_node("agent_executor", agent_executor_node)
    workflow.add_node("response_grader", response_grader_node)
    workflow.add_node("re_router", re_router_node)

    # ── Edges ──
    workflow.set_entry_point("check_documents")
    workflow.add_edge("check_documents", "router")

    # After router: confidence gate decides clarify vs proceed
    workflow.add_conditional_edges(
        "router",
        confidence_gate,
        {
            "proceed": "agent_executor",
            "clarify": "clarify_query",
        },
    )

    workflow.add_edge("clarify_query", END)

    # Agent executor always goes to grader
    workflow.add_edge("agent_executor", "response_grader")

    # Grader decides: pass → END, refine → agent_executor, reroute → re_router
    workflow.add_conditional_edges(
        "response_grader",
        grading_decision,
        {
            "pass": END,
            "refine": "agent_executor",
            "reroute": "re_router",
        },
    )

    # Re-router feeds back into agent executor
    workflow.add_edge("re_router", "agent_executor")

    return workflow.compile()


# Compiled workflow singleton
compiled_workflow = build_workflow()


# ─── Batch entry point ────────────────────────────────────────────────────────

def process_with_langgraph(
    question: str,
    user_id: str,
    conversation_id: str,
    user_profile: dict = None,
) -> WorkflowState:
    """
    Process query using LangGraph workflow with memory context.

    Args:
        question: User's question
        user_id: User ID
        conversation_id: Conversation ID
        user_profile: User profile dict

    Returns:
        Final workflow state
    """
    memory_context = None
    try:
        from core.memory.context_manager import ContextManager
        from core.database import UserRepository

        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)

        if user:
            context_manager = ContextManager()
            memory_context = context_manager.build_agent_context(
                user=user,
                query=question,
                conversation_id=conversation_id,
            )
            logger.info(f"Built memory context for user {user_id}")
            if memory_context.get("relevant_concepts"):
                logger.info(f"Relevant concepts: {memory_context['relevant_concepts']}")
            if memory_context.get("weak_areas"):
                logger.info(f"Weak areas: {memory_context['weak_areas']}")

    except Exception as e:
        logger.warning(f"Failed to build memory context: {e}")
        memory_context = None

    initial_state = WorkflowState(
        question=question,
        user_id=user_id,
        conversation_id=conversation_id,
        user_profile=user_profile,
        memory_context=memory_context,
        refinement_count=0,
        reroute_count=0,
        previous_agents=[],
        budget=RequestBudget(),
    )

    final_state = compiled_workflow.invoke(initial_state)
    return final_state


# ─── Streaming entry point ────────────────────────────────────────────────────

async def process_with_langgraph_streaming(
    question: str,
    user_id: str,
    conversation_id: str,
    user_profile: dict = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process query with token-by-token streaming from agents.

    Handles the enhanced workflow: confidence gate → stream → grade → possibly
    refine/re-route and re-stream.
    """
    from core.graph.nodes import (
        check_documents_node,
        router_node,
        response_grader_node,
        re_router_node,
        CONFIDENCE_THRESHOLD,
        MAX_REFINEMENTS,
        MAX_REROUTES,
    )

    # Build memory context
    memory_context = None
    try:
        from core.memory.context_manager import ContextManager
        from core.database import UserRepository

        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)

        if user:
            context_manager = ContextManager()
            memory_context = context_manager.build_agent_context(
                user=user,
                query=question,
                conversation_id=conversation_id,
            )
            logger.info(f"Built memory context for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to build memory context: {e}")

    # Initialise state
    state = WorkflowState(
        question=question,
        user_id=user_id,
        conversation_id=conversation_id,
        user_profile=user_profile,
        memory_context=memory_context,
        refinement_count=0,
        reroute_count=0,
        previous_agents=[],
        budget=RequestBudget(),
    )

    # ── Batch pre-processing (router doesn't need streaming) ──
    state = check_documents_node(state)
    state = router_node(state)

    route = state.get("route", "concept")
    confidence = state.get("routing_confidence", 1.0)

    # ── Confidence gate ──
    if confidence < CONFIDENCE_THRESHOLD:
        state = clarify_query_node(state)
        yield {
            "type": "clarification",
            "content": state.get("response", ""),
            "agent": "clarify",
            "confidence": confidence,
        }
        return

    # Yield routing info
    yield {
        "type": "routed",
        "route": route,
        "confidence": confidence,
    }

    # ── Stream → grade → possibly loop ──
    iteration = 0
    max_iterations = 1 + MAX_REFINEMENTS + MAX_REROUTES

    while iteration < max_iterations:
        iteration += 1
        current_route = state.get("route", "concept")

        # Stream from the selected agent, collecting full response
        full_response_parts = []
        streamer = _get_streaming_agent(current_route, state)

        async for event in streamer:
            full_response_parts.append(event.get("content", ""))
            yield event

        # Capture full response for grading
        state["response"] = "".join(full_response_parts)
        state["agent_used"] = current_route
        previous = list(state.get("previous_agents") or [])
        if current_route not in previous:
            previous.append(current_route)
        state["previous_agents"] = previous

        # Grade
        state = response_grader_node(state)
        verdict = state.get("grader_verdict", "pass")

        if verdict == "pass":
            return

        if verdict == "refine":
            yield {
                "type": "refining",
                "feedback": state.get("grader_feedback", ""),
                "attempt": state.get("refinement_count", 1),
            }
            continue

        if verdict == "reroute":
            state = re_router_node(state)
            new_route = state.get("route", "concept")
            yield {
                "type": "rerouting",
                "from_agent": current_route,
                "to_agent": new_route,
                "reason": state.get("grader_feedback", ""),
            }
            continue

        return


def _get_streaming_agent(route: str, state: WorkflowState):
    """Return the appropriate async streaming generator for a route."""
    if route == "concept":
        return concept_explainer_node_streaming(state)
    elif route == "code":
        return code_helper_node_streaming(state)
    elif route == "practice":
        return practice_generator_node_streaming(state)
    elif route == "research":
        return research_agent_node_streaming(state)
    else:
        return concept_explainer_node_streaming(state)


# Export
__all__ = [
    "build_workflow",
    "compiled_workflow",
    "process_with_langgraph",
    "process_with_langgraph_streaming",
]
