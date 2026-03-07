"""
Graph module for Academe.

Contains the LangGraph workflow that coordinates all agents.
"""

from .state import WorkflowState
from .decision_context import DecisionContext
from core.rag.request_budget import RequestBudget
from .nodes import (
    check_documents_node,
    router_node,
    concept_explainer_node,
    code_helper_node,
    research_agent_node,
    practice_generator_node,
    agent_executor_node,
    response_grader_node,
    clarify_query_node,
    re_router_node,
)
from .workflow import (
    build_workflow,
    compiled_workflow,
    process_with_langgraph,
    process_with_langgraph_streaming,
)

__all__ = [
    # State
    "WorkflowState",
    "DecisionContext",
    "RequestBudget",

    # Legacy individual agent nodes
    "check_documents_node",
    "router_node",
    "concept_explainer_node",
    "code_helper_node",
    "research_agent_node",
    "practice_generator_node",

    # Enhanced workflow nodes
    "agent_executor_node",
    "response_grader_node",
    "clarify_query_node",
    "re_router_node",

    # Workflow
    "build_workflow",
    "compiled_workflow",
    "process_with_langgraph",
    "process_with_langgraph_streaming",
]
