"""
State management for LangGraph workflows.

Defines the state structure passed between nodes in the workflow graph.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class WorkflowState(TypedDict, total=False):
    """
    State for workflow processing.
    
    This is passed between nodes in the LangGraph workflow.
    """
    # Input
    question: str
    user_id: str
    conversation_id: str
    
    # User context
    user_profile: Optional[Dict[str, Any]]
    has_documents: bool
    document_count: int
    
    # Routing
    route: str  # "concept", "code", "research"
    routing_confidence: float
    routing_reasoning: str
    
    # Processing
    agent_used: str
    response: str
    
    # RAG-specific
    rag_context: Optional[str]
    sources: Optional[List[Dict[str, Any]]]
    sources_used: int
    rag_fallback_needed: bool
    
    # Memory
    memory_context: Optional[Dict[str, Any]]
    
    # Metadata
    processing_time_ms: Optional[int]
    timestamp: Optional[datetime]
    error: Optional[str]


class RouterState(TypedDict, total=False):
    """State specific to router node."""
    question: str
    has_documents: bool
    route: str
    confidence: float
    reasoning: str


class ConceptExplainerState(TypedDict, total=False):
    """State specific to concept explainer node."""
    question: str
    user_profile: Dict[str, Any]
    rag_context: Optional[str]
    has_rag_context: bool
    response: str


class CodeHelperState(TypedDict, total=False):
    """State specific to code helper node."""
    question: str
    user_profile: Dict[str, Any]
    rag_context: Optional[str]
    has_rag_context: bool
    code_language: str
    response: str


class ResearchAgentState(TypedDict, total=False):
    """State specific to research agent node."""
    question: str
    user_profile: Dict[str, Any]
    rag_result_type: str
    sources: List[Dict[str, Any]]
    response: str
    fallback_needed: bool


# Export state types
__all__ = [
    "WorkflowState",
    "RouterState",
    "ConceptExplainerState",
    "CodeHelperState",
    "ResearchAgentState"
]