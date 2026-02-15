"""
Node implementations for LangGraph workflow.

Each node represents a specific processing step in the workflow.
"""

import logging
from datetime import datetime
from typing import Dict, Any, AsyncGenerator

from core.models import UserProfile
from core.agents.router import route_query_structured
from core.agents.concept_explainer import ConceptExplainer
from core.agents.code_helper import CodeHelper
from core.agents.research_agent import ResearchAgent
from core.documents import DocumentManager
from core.database import UserRepository
from core.graph.state import WorkflowState
from core.utils.datetime_utils import get_current_time
from core.rag import RAGPipeline

logger = logging.getLogger(__name__)

# Shared RAG pipeline and agents for efficient resource use
_shared_rag = None
_shared_concept_explainer = None
_shared_code_helper = None


def _get_shared_rag():
    """Get or create shared RAG pipeline."""
    global _shared_rag
    if _shared_rag is None:
        _shared_rag = RAGPipeline()
    return _shared_rag


def _get_concept_explainer():
    """Get or create shared ConceptExplainer with shared RAG."""
    global _shared_concept_explainer
    if _shared_concept_explainer is None:
        _shared_concept_explainer = ConceptExplainer(
            rag_pipeline=_get_shared_rag()
        )
    return _shared_concept_explainer


def _get_code_helper():
    """Get or create shared CodeHelper with shared RAG."""
    global _shared_code_helper
    if _shared_code_helper is None:
        _shared_code_helper = CodeHelper(
            rag_pipeline=_get_shared_rag()
        )
    return _shared_code_helper


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
        state["timestamp"] = get_current_time()
        
        logger.info(f"Router decision: {decision.route} (confidence: {decision.confidence:.2f})")
        logger.info(f"Router reasoning: {decision.reasoning}")
        logger.info(f"STATE ROUTE SET TO: {state['route']}")
        
    except Exception as e:
        logger.error(f"Routing failed: {e}, defaulting to concept")
        state["route"] = "concept"
        state["routing_confidence"] = 0.5
        state["routing_reasoning"] = f"Fallback due to error: {str(e)}"
        state["timestamp"] = get_current_time()
    
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
    
    start_time = get_current_time()
    
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        # Use shared ConceptExplainer for efficient resource usage
        explainer = _get_concept_explainer()
        response = explainer.explain(
            question=question,
            user_profile=user,
            memory_context=state.get("memory_context")
        )
        
        processing_time = (get_current_time() - start_time).total_seconds() * 1000
        
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
    
    start_time = get_current_time()
    
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        # Use shared CodeHelper for efficient resource usage
        code_helper = _get_code_helper()
        response = code_helper.generate_code(
            question=question,
            user_profile=user,
            memory_context=state.get("memory_context")
        )
        
        processing_time = (get_current_time() - start_time).total_seconds() * 1000
        
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
    
    start_time = get_current_time()
    
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
        
        processing_time = (get_current_time() - start_time).total_seconds() * 1000
        
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

# ==========================================
# STREAMING NODE VERSIONS
# ==========================================

async def concept_explainer_node_streaming(state: WorkflowState):
    """
    Concept Explainer node - STREAMING version.
    
    Yields tokens as they're generated.
    """
    from core.agents.concept_explainer import explain_concept_streaming
    
    question = state["question"]
    user_id = state["user_id"]
    
    try:
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        async for chunk in explain_concept_streaming(
            question=question,
            user_profile=user,
            memory_context=state.get("memory_context")
        ):
            yield {"type": "token", "content": chunk, "agent": "concept_explainer"}
        
        yield {"type": "done", "agent": "concept_explainer"}
        
    except Exception as e:
        logger.error(f"Concept explainer streaming failed: {e}")
        yield {"type": "error", "content": str(e)}


async def code_helper_node_streaming(state: WorkflowState):
    """Code Helper node - STREAMING version."""
    from core.agents.code_helper import generate_code_streaming
    
    question = state["question"]
    user_id = state["user_id"]
    
    try:
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        async for chunk in generate_code_streaming(
            question=question,
            user_profile=user,
            memory_context=state.get("memory_context")
        ):
            yield {"type": "token", "content": chunk, "agent": "code_helper"}
        
        yield {"type": "done", "agent": "code_helper"}
        
    except Exception as e:
        logger.error(f"Code helper streaming failed: {e}")
        yield {"type": "error", "content": str(e)}


async def research_agent_node_streaming(state: WorkflowState):
    """Research Agent node - STREAMING version."""
    from core.agents.research_agent import research_streaming
    
    question = state["question"]
    user_id = state["user_id"]
    
    try:
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        async for chunk in research_streaming(question=question, user_profile=user):
            yield {"type": "token", "content": chunk, "agent": "research_agent"}
        
        yield {"type": "done", "agent": "research_agent"}
        
    except Exception as e:
        logger.error(f"Research agent streaming failed: {e}")
        yield {"type": "error", "content": str(e)}


# Export streaming nodes
__all__ = [
    "check_documents_node",
    "router_node",
    "concept_explainer_node",
    "code_helper_node",
    "research_agent_node",
    "practice_generator_node",
    "concept_explainer_node_streaming",
    "code_helper_node_streaming",
    "research_agent_node_streaming",
    "practice_generator_node_streaming"
]


def practice_generator_node(state: WorkflowState) -> WorkflowState:
    """
    Practice Generator node - creates practice questions.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state with practice questions
    """
    from core.agents.practice_generator import PracticeGenerator
    
    question = state["question"]
    user_id = state["user_id"]
    start_time = get_current_time()
    
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        if not user:
            state["response"] = "Error: User profile not found"
            state["agent"] = "practice_generator"
            return state
        
        # Extract topic from question
        topic = question.lower()
        for phrase in ["quiz me on", "practice", "give me questions about", "test me on", "give me problems on"]:
            topic = topic.replace(phrase, "").strip()
        
        # Extract number of questions if specified
        num_questions = 5
        for num in [3, 5, 10, 15, 20]:
            if str(num) in question:
                num_questions = num
                break
        
        # Initialize practice generator
        practice_gen = PracticeGenerator()
        
        logger.info(f"Practice generator: topic={topic}, num_questions={num_questions}")
        
        # Generate practice set with memory context
        result = practice_gen.generate_practice_set(
            topic=topic or "general",
            user=user,
            num_questions=num_questions,
            question_types=None,
            memory_context=state.get("memory_context")
        )
        
        logger.info(f"Practice generator result: error={result.get('error')}, questions={len(result.get('questions', []))}")
        
        # Format response
        if result.get("error"):
            response = f"❌ {result['error']}"
            logger.warning(f"Practice generator returned error: {result['error']}")
        else:
            response = f"## 📝 Practice Questions: {result['topic']}\n\n"
            
            for i, q in enumerate(result.get('questions', []), 1):
                response += f"**Question {i}** ({q['type'].upper()})\n"
                response += f"{q['question']}\n\n"
                
                if q['type'] == 'mcq' and 'options' in q:
                    for idx, opt in enumerate(q['options'], 1):
                        response += f"{idx}. {opt}\n"
                    response += "\n"
            
            response += f"\n✨ Generated {len(result.get('questions', []))} questions\n"
            response += f"📚 Sources: {', '.join(result.get('sources', ['General knowledge']))}\n"
            response += "\n💡 *Ask me to reveal the answers when you're ready!*"
        
        state["response"] = response
        state["agent"] = "practice_generator"
        state["metadata"] = {
            "questions_count": len(result.get('questions', [])),
            "topic": result.get('topic'),
            "sources": result.get('sources', [])
        }
        
    except Exception as e:
        logger.error(f"Practice generator error: {e}")
        state["response"] = f"Sorry, I encountered an error generating practice questions: {str(e)}"
        state["agent"] = "practice_generator"
    
    end_time = get_current_time()
    state["processing_time"] = (end_time - start_time).total_seconds()
    
    return state


async def practice_generator_node_streaming(state: WorkflowState) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming version of practice generator node."""
    from core.agents.practice_generator import PracticeGenerator
    
    question = state["question"]
    user_id = state["user_id"]
    
    try:
        yield {"type": "thinking", "agent": "practice_generator", "message": "Generating practice questions..."}
        
        # Get user
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(user_id)
        
        if not user:
            yield {"type": "token", "content": "Error: User profile not found", "agent": "practice_generator"}
            return
        
        # Extract topic
        topic = question.lower()
        for phrase in ["quiz me on", "practice", "give me questions about", "test me on"]:
            topic = topic.replace(phrase, "").strip()
        
        # Generate practice
        practice_gen = PracticeGenerator()
        result = practice_gen.generate_practice_set(
            topic=topic or "general",
            user=user,
            num_questions=5,
            question_types=None,
            memory_context=state.get("memory_context")
        )
        
        # Stream response
        if result.get("error"):
            yield {"type": "token", "content": f"❌ {result['error']}", "agent": "practice_generator"}
        else:
            response = f"## 📝 Practice Questions: {result['topic']}\n\n"
            yield {"type": "token", "content": response, "agent": "practice_generator"}
            
            for i, q in enumerate(result.get('questions', []), 1):
                chunk = f"**Question {i}** ({q['type'].upper()})\n{q['question']}\n\n"
                if q['type'] == 'mcq' and 'options' in q:
                    for idx, opt in enumerate(q['options'], 1):
                        chunk += f"{idx}. {opt}\n"
                    chunk += "\n"
                yield {"type": "token", "content": chunk, "agent": "practice_generator"}
            
            footer = f"\n✨ Generated {len(result.get('questions', []))} questions\n"
            footer += f"📚 Sources: {', '.join(result.get('sources', ['General knowledge']))}\n"
            yield {"type": "token", "content": footer, "agent": "practice_generator"}
        
        yield {"type": "done", "agent": "practice_generator"}
        
    except Exception as e:
        logger.error(f"Practice generator streaming error: {e}")
        yield {"type": "token", "content": f"Error: {str(e)}", "agent": "practice_generator"}
        yield {"type": "done", "agent": "practice_generator"}
