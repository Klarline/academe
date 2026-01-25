"""
Node functions for the LangGraph workflow.

Each node is a function that takes the state, performs an action,
and returns the updated state.
"""

from academe.graph.state import AcademicAssistantState
from academe.agents import (
    route_query,
    explain_concept,
    generate_code
)


def router_node(state: AcademicAssistantState) -> AcademicAssistantState:
    """
    Router node - decides which agent should handle the query.
    
    This is the entry point of the workflow. It analyzes the user's
    question and determines whether it should go to the Concept Explainer
    or Code Helper.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with routing decision
    """
    print("🧭 Router analyzing query...")
    
    question = state["question"]
    
    # Use router agent to decide
    route = route_query(question)
    
    print(f"   → Routing to: {route.upper()} agent\n")
    
    # Update state with routing decision
    return {
        **state,
        "route": route,
        "error": None
    }


def concept_explainer_node(state: AcademicAssistantState) -> AcademicAssistantState:
    """
    Concept Explainer node - generates multi-level explanations.
    
    This node handles conceptual questions by providing both intuitive
    and technical explanations of concepts.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with explanation response
    """
    print("💡 Concept Explainer working...")
    
    question = state["question"]
    
    try:
        # Generate multi-level explanation
        response = explain_concept(question, level="both")
        
        print("   ✓ Explanation generated\n")
        
        return {
            **state,
            "response": response,
            "agent_used": "concept_explainer",
            "error": None
        }
    
    except Exception as e:
        print(f"   ✗ Error: {str(e)}\n")
        return {
            **state,
            "response": f"Sorry, I encountered an error: {str(e)}",
            "agent_used": "concept_explainer",
            "error": str(e)
        }


def code_helper_node(state: AcademicAssistantState) -> AcademicAssistantState:
    """
    Code Helper node - generates educational code.
    
    This node handles code requests by generating clean, well-commented
    Python implementations with examples.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with code response
    """
    print("💻 Code Helper generating...")
    
    question = state["question"]
    
    try:
        # Generate code with explanations
        response = generate_code(question)
        
        print("   ✓ Code generated\n")
        
        return {
            **state,
            "response": response,
            "agent_used": "code_helper",
            "error": None
        }
    
    except Exception as e:
        print(f"   ✗ Error: {str(e)}\n")
        return {
            **state,
            "response": f"Sorry, I encountered an error: {str(e)}",
            "agent_used": "code_helper",
            "error": str(e)
        }


# Export node functions
__all__ = [
    "router_node",
    "concept_explainer_node",
    "code_helper_node"
]