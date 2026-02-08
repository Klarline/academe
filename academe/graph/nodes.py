"""
Node implementations for LangGraph workflow.

Each node represents a specific processing step in the workflow.
"""

import logging
from datetime import datetime

from academe.models import UserProfile
from academe.agents.router import route_query_structured
from academe.agents.concept_explainer import explain_concept_with_context
from academe.agents.code_helper import generate_code_with_context
from academe.agents.research_agent import ResearchAgent
from academe.documents import DocumentManager
from academe.database import UserRepository
from academe.graph.state import WorkflowState

logger = logging.getLogger(__name__)


def check_documents_node(state: WorkflowState) -> WorkflowState:
    """
    Check if user has documents - preprocessing node.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with document information
    """
    user_id = state["user_id"]
    
    try:
        doc_manager = DocumentManager()
        user_docs = doc_manager.get_user_documents(user_id)
        
        state["has_documents"] = len(user_docs) > 0
        state["document_count"] = len(user_docs)
        
        logger.info(f"User {user_id} has {len(user_docs)} documents")
        
    except Exception as e:
        logger.error(f"Error checking documents: {e}")
        state["has_documents"] = False
        state["document_count"] = 0
    
    return state


def router_node(state: WorkflowState) -> WorkflowState:
    """
    Router node - determines which agent should handle the query.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with routing decision
    """
    question = state["question"]
    has_documents = state.get("has_documents", False)
    
    try:
        # Route with structured output
        decision = route_query_structured(question, has_documents)
        
        # Update state
        state["route"] = decision.route
        state["routing_confidence"] = decision.confidence
        state["routing_reasoning"] = decision.reasoning
        state["timestamp"] = datetime.utcnow()
        
        logger.info(f"Router decision: {decision.route} (confidence: {decision.confidence:.2f})")
        
    except Exception as e:
        logger.error(f"Routing failed: {e}, defaulting to concept")
        state["route"] = "concept"
        state["routing_confidence"] = 0.5
        state["routing_reasoning"] = f"Fallback due to error: {str(e)}"
        state["timestamp"] = datetime.utcnow()
    
    return state


def concept_explainer_node(state: WorkflowState) -> WorkflowState:
    """
    Concept Explainer node - generates conceptual explanations.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with response
    """
    question = state["question"]
    user_id = state["user_id"]
    
    start_time = datetime.utcnow()
    
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        # Generate explanation with RAG and memory support
        response = explain_concept_with_context(
            question=question,
            user_profile=user,
            context=None,  # Legacy RAG parameter
            memory_context=state.get("memory_context")  # v0.4 memory context
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update state
        state["response"] = response
        state["agent_used"] = "concept_explainer"
        state["processing_time_ms"] = int(processing_time)
        
        logger.info(f"Concept explainer completed in {processing_time:.0f}ms")
        
    except Exception as e:
        logger.error(f"Concept explainer failed: {e}")
        state["response"] = f"Error generating explanation: {str(e)}"
        state["agent_used"] = "concept_explainer"
        state["error"] = str(e)
    
    return state


def code_helper_node(state: WorkflowState) -> WorkflowState:
    """
    Code Helper node - generates code examples.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with response
    """
    question = state["question"]
    user_id = state["user_id"]
    
    start_time = datetime.utcnow()
    
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        # Generate code with RAG and memory support
        response = generate_code_with_context(
            question=question,
            user_profile=user,
            context=None,  # Legacy RAG parameter
            memory_context=state.get("memory_context")  # v0.4 memory context
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update state
        state["response"] = response
        state["agent_used"] = "code_helper"
        state["processing_time_ms"] = int(processing_time)
        
        logger.info(f"Code helper completed in {processing_time:.0f}ms")
        
    except Exception as e:
        logger.error(f"Code helper failed: {e}")
        state["response"] = f"Error generating code: {str(e)}"
        state["agent_used"] = "code_helper"
        state["error"] = str(e)
    
    return state


def research_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Research Agent node - performs RAG-based document Q&A.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with response
    """
    question = state["question"]
    user_id = state["user_id"]
    
    start_time = datetime.utcnow()
    
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        # Use research agent
        research_agent = ResearchAgent()
        
        response = research_agent.answer_question(
            question=question,
            user=user,
            use_citations=True,
            top_k=5
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update state (research_agent returns string)
        state["response"] = response
        state["agent_used"] = "research_agent"
        state["processing_time_ms"] = int(processing_time)
        
        logger.info(f"Research agent completed in {processing_time:.0f}ms")
        
    except Exception as e:
        logger.error(f"Research agent failed: {e}")
        state["response"] = f"Error searching documents: {str(e)}"
        state["agent_used"] = "research_agent"
        state["error"] = str(e)
    
    return state


# Export node functions
__all__ = [
    "check_documents_node",
    "router_node",
    "concept_explainer_node",
    "code_helper_node",
    "research_agent_node"
]