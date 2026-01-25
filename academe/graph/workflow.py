"""
LangGraph workflow for the Academe multi-agent system.

This module defines the complete workflow graph that connects
all agents together.
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from academe.graph.state import AcademicAssistantState
from academe.graph.nodes import (
    router_node,
    concept_explainer_node,
    code_helper_node
)


def route_to_agent(state: AcademicAssistantState) -> Literal["concept", "code"]:
    """
    Conditional routing function.
    
    This function is used by LangGraph to decide which path to take
    after the router node. It reads the routing decision from the state.
    
    Args:
        state: Current workflow state
    
    Returns:
        Name of the node to route to ("concept" or "code")
    """
    return state["route"]


def create_workflow():
    """
    Creates the complete LangGraph workflow for Academe.
    
    The workflow structure:
    1. Start with router_node (analyzes query)
    2. Router conditionally routes to either:
       - concept_explainer_node (for explanations)
       - code_helper_node (for code generation)
    3. Both agents end the workflow
    
    Returns:
        Compiled LangGraph application ready to process queries
    """
    
    # Initialize the graph with our state type
    workflow = StateGraph(AcademicAssistantState)
    
    # Add nodes to the graph
    workflow.add_node("router", router_node)
    workflow.add_node("concept", concept_explainer_node)
    workflow.add_node("code", code_helper_node)
    
    # Set entry point (where the workflow starts)
    workflow.set_entry_point("router")
    
    # Add conditional routing from router to agents
    # After router_node runs, call route_to_agent() to decide the next node
    workflow.add_conditional_edges(
        "router",           # From this node
        route_to_agent,     # Use this function to decide
        {
            "concept": "concept",  # If returns "concept", go to concept node
            "code": "code"          # If returns "code", go to code node
        }
    )
    
    # Both agents end the workflow
    workflow.add_edge("concept", END)
    workflow.add_edge("code", END)
    
    # Compile the graph into an executable application
    app = workflow.compile()
    
    return app


# Convenience function to process a query
def process_query(question: str) -> dict:
    """
    Process a user query through the complete workflow.
    
    This is a convenience function that:
    1. Creates the initial state
    2. Runs the workflow
    3. Returns the final result
    
    Args:
        question: User's question or request
    
    Returns:
        Dictionary containing the final state with response
    
    Example:
        >>> result = process_query("What is gradient descent?")
        >>> print(result["response"])
    """
    
    # Create the workflow
    app = create_workflow()
    
    # Create initial state
    initial_state: AcademicAssistantState = {
        "question": question,
        "route": "concept",  # Will be overwritten by router
        "response": "",
        "agent_used": "",
        "error": None
    }
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    return final_state


# Export main functions
__all__ = [
    "create_workflow",
    "process_query"
]