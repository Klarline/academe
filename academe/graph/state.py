"""
State definition for the Academe multi-agent system.

The state is passed between nodes in the LangGraph workflow and contains
all the information needed to process a query.
"""

from typing import TypedDict, Literal


class AcademicAssistantState(TypedDict):
    """
    State that flows through the LangGraph workflow.
    
    This state is passed between all nodes (router, agents) and contains:
    - The original user question
    - The routing decision
    - The final response
    - Metadata about which agent handled the request
    
    Attributes:
        question: The user's original query
        route: Which agent should handle this ("concept" or "code")
        response: The final response from the selected agent
        agent_used: Name of the agent that generated the response
        error: Any error message if something goes wrong (optional)
    """
    question: str
    route: Literal["concept", "code"]
    response: str
    agent_used: str
    error: str | None