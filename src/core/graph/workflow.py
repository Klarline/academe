"""
LangGraph workflow definition for Academe

Defines the complete multi-agent workflow using LangGraph.
Supports both batch processing and real-time streaming.
"""

import logging
from typing import Literal, AsyncGenerator, Dict, Any

from langgraph.graph import StateGraph, END

from core.graph.state import WorkflowState
from core.graph.nodes import (
    check_documents_node,
    router_node,
    concept_explainer_node,
    code_helper_node,
    research_agent_node
)

logger = logging.getLogger(__name__)


def should_use_research(state: WorkflowState) -> Literal["research", "concept", "code"]:
    """
    Conditional edge - determine which agent to use based on routing.
    
    Args:
        state: Current workflow state
    
    Returns:
        Next node to execute
    """
    route = state.get("route", "concept")
    return route


def build_workflow() -> StateGraph:
    """
    Build the complete LangGraph workflow.
    
    Returns:
        Configured StateGraph
    """
    # Create workflow
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("check_documents", check_documents_node)
    workflow.add_node("router", router_node)
    workflow.add_node("concept_explainer", concept_explainer_node)
    workflow.add_node("code_helper", code_helper_node)
    workflow.add_node("research_agent", research_agent_node)
    
    # Define edges
    workflow.set_entry_point("check_documents")
    workflow.add_edge("check_documents", "router")
    
    # Conditional routing based on router decision
    workflow.add_conditional_edges(
        "router",
        should_use_research,
        {
            "concept": "concept_explainer",
            "code": "code_helper",
            "research": "research_agent"
        }
    )
    
    # All agents lead to END
    workflow.add_edge("concept_explainer", END)
    workflow.add_edge("code_helper", END)
    workflow.add_edge("research_agent", END)
    
    return workflow.compile()


# Create compiled workflow
compiled_workflow = build_workflow()


def process_with_langgraph(
    question: str,
    user_id: str,
    conversation_id: str,
    user_profile: dict = None
) -> WorkflowState:
    """
    Process query using LangGraph workflow with memory context.
    
    v0.4: Now builds memory context before processing.
    
    Args:
        question: User's question
        user_id: User ID
        conversation_id: Conversation ID
        user_profile: User profile dict
    
    Returns:
        Final workflow state
    """
    # Build memory context (v0.4 NEW!)
    memory_context = None
    try:
        from core.memory.context_manager import ContextManager
        from core.database import UserRepository
        
        # Get full user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        if user:
            # Build intelligent memory context
            context_manager = ContextManager()
            memory_context = context_manager.build_agent_context(
                user=user,
                query=question,
                conversation_id=conversation_id
            )
            
            logger.info(f"Built memory context for user {user_id}")
            
            # Log what memory found
            if memory_context.get("relevant_concepts"):
                logger.info(f"Relevant concepts: {memory_context['relevant_concepts']}")
            if memory_context.get("weak_areas"):
                logger.info(f"Weak areas: {memory_context['weak_areas']}")
                
    except Exception as e:
        logger.warning(f"Failed to build memory context: {e}")
        memory_context = None
    
    # Create initial state with memory
    initial_state = WorkflowState(
        question=question,
        user_id=user_id,
        conversation_id=conversation_id,
        user_profile=user_profile,
        memory_context=memory_context  # Pass memory to workflow
    )
    
    # Run workflow
    final_state = compiled_workflow.invoke(initial_state)
    
    return final_state


async def process_with_langgraph_streaming(
    question: str,
    user_id: str,
    conversation_id: str,
    user_profile: dict = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process query using LangGraph workflow with REAL token-by-token streaming.
    
    Uses LangGraph's .astream_events() to stream tokens as the LLM generates them.
    This provides true real-time streaming where users see responses as they're created.
    
    Args:
        question: User's question
        user_id: User ID
        conversation_id: Conversation ID
        user_profile: User profile dict
        
    Yields:
        Stream events with types:
        - {"type": "thinking", "agent": "router", "message": "..."}
        - {"type": "routed", "route": "concept", "message": "..."}
        - {"type": "token", "content": "PCA", "agent": "concept_explainer"}
        - {"type": "token", "content": " is", "agent": "concept_explainer"}
        - {"type": "done", "response": "...", "agent": "...", "metadata": {...}}
    """
    # Build memory context (same as batch)
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
                conversation_id=conversation_id
            )
            
            logger.info(f"Built memory context for user {user_id}")
            
            if memory_context.get("relevant_concepts"):
                logger.info(f"Relevant concepts: {memory_context['relevant_concepts']}")
            if memory_context.get("weak_areas"):
                logger.info(f"Weak areas: {memory_context['weak_areas']}")
                
    except Exception as e:
        logger.warning(f"Failed to build memory context: {e}")
        memory_context = None
    
    # Create initial state
    initial_state = WorkflowState(
        question=question,
        user_id=user_id,
        conversation_id=conversation_id,
        user_profile=user_profile,
        memory_context=memory_context
    )
    
    # Track streaming state
    current_agent = None
    current_route = None
    full_response = ""
    
    # Stream workflow execution with LangGraph's astream_events
    async for event in compiled_workflow.astream_events(initial_state, version="v2"):
        event_type = event.get("event")
        event_name = event.get("name", "")
        
        # Node execution started
        if event_type == "on_chain_start":
            if event_name == "router":
                yield {
                    "type": "thinking",
                    "agent": "router",
                    "message": "Analyzing your question..."
                }
            elif event_name in ["concept_explainer", "code_helper", "research_agent"]:
                current_agent = event_name
                yield {
                    "type": "thinking",
                    "agent": current_agent,
                    "message": f"Preparing {current_agent.replace('_', ' ')}..."
                }
        
        # LLM streaming tokens (REAL-TIME!)
        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content"):
                content = chunk.content
                if content:
                    full_response += content
                    yield {
                        "type": "token",
                        "content": content,
                        "agent": current_agent
                    }
        
        # Node completed
        elif event_type == "on_chain_end":
            if event_name == "router":
                # Router completed - get routing decision
                output = event.get("data", {}).get("output", {})
                route = output.get("route")
                if route:
                    current_route = route
                    yield {
                        "type": "routed",
                        "route": route,
                        "confidence": output.get("confidence", 0.0),
                        "message": f"Routing to {route} agent"
                    }
            
            elif event_name in ["concept_explainer", "code_helper", "research_agent"]:
                # Agent completed
                yield {
                    "type": "agent_done",
                    "agent": event_name,
                    "message": f"{event_name} completed"
                }
    
    # Send final completion event
    yield {
        "type": "done",
        "response": full_response,
        "agent": current_agent,
        "route": current_route,
        "metadata": {
            "agent_used": current_agent,
            "route": current_route,
            "has_memory": memory_context is not None,
            "total_tokens": len(full_response.split())
        }
    }


# Export
__all__ = [
    "build_workflow",
    "compiled_workflow",
    "process_with_langgraph",
    "process_with_langgraph_streaming"  # NEW!
]