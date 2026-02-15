"""
Router Agent - Routes queries to appropriate agents including research.

Uses modern LangChain with structured output for reliable routing decisions.
"""

import logging
from typing import Literal
from pydantic import BaseModel, Field

from core.config import get_llm

logger = logging.getLogger(__name__)


class RouterDecision(BaseModel):
    """Structured router decision with reasoning."""
    
    route: Literal["concept", "code", "research", "practice"] = Field(
        description="Which agent should handle this query"
    )
    reasoning: str = Field(
        description="Why this routing decision was made"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in routing decision (0.0 to 1.0)"
    )


def route_query_structured(
    question: str,
    has_documents: bool = False
) -> RouterDecision:
    """
    Route query using LLM with structured output.
    
    Args:
        question: User's question
        has_documents: Whether user has uploaded documents
    
    Returns:
        RouterDecision with route, reasoning, and confidence
    """
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(RouterDecision)
    
    prompt = f"""Determine which agent should handle this query.

PRIORITY ORDER (check in this exact order):

1. PRACTICE - If query contains ANY of: "quiz", "test me", "practice", "exercise", "problem", "questions"
   Examples: "quiz me on X", "test me", "give me practice problems"
   
2. CODE - If asking for code implementation
   Examples: "show me code", "implement in Python"
   
3. RESEARCH - ONLY if explicitly asking about uploaded documents
   Examples: "find in my notes", "according to my PDF"
   {"(User has documents)" if has_documents else "(User has NO documents - do not use research)"}
   
4. CONCEPT - Default for explanations
   Examples: "explain X", "what is X"

Query: "{question}"

Respond with route ("practice", "code", "research", or "concept"), reasoning, and confidence."""

    try:
        response = structured_llm.invoke(prompt)
        if not has_documents and response.route == "research":
            response.route = "concept"
        logger.info(f"Routed to {response.route.upper()} (confidence: {response.confidence:.2f})")
        return response
    except Exception as e:
        logger.error(f"LLM routing failed: {e}, using keyword fallback")
        route = route_query_keyword(question, has_documents)
        return RouterDecision(route=route, reasoning="Keyword fallback", confidence=0.8)


def route_query(
    question: str,
    has_documents: bool = False
) -> Literal["concept", "code", "research", "practice"]:
    """
    Simple routing function for backward compatibility.
    
    Args:
        question: User's question
        has_documents: Whether user has uploaded documents
    
    Returns:
        "concept", "code", "research", or "practice"
    """
    decision = route_query_structured(question, has_documents)
    return decision.route


def route_query_keyword(
    question: str,
    has_documents: bool = False
) -> Literal["concept", "code", "research", "practice"]:
    """
    Fallback keyword-based routing (fast but less accurate).
    
    Use this if LLM routing fails or for testing.
    
    Args:
        question: User's question
        has_documents: Whether user has uploaded documents
    
    Returns:
        "concept", "code", "research", or "practice"
    """
    question_lower = question.lower()
    
    # Practice generator keywords
    practice_keywords = [
        "quiz me", "test me", "practice", "exercise",
        "problem", "give me questions", "generate questions",
        "can i practice", "want to practice", "help me practice",
        "create practice", "practice problems", "quiz me on",
        "test my knowledge", "give me 5 questions", "give me problems"
    ]
    
    # Check practice FIRST with simple substring match
    if any(keyword in question_lower for keyword in practice_keywords):
        logger.info(f"Keyword routing to PRACTICE")
        return "practice"
    
    # Research agent keywords (only if user has documents)
    if has_documents:
        research_keywords = [
            "my document", "my notes", "my pdf", "my file",
            "uploaded", "from the text", "in the reading",
            "according to", "based on the", "cite", "source",
            "find in", "search for", "look up",
            "what does the author", "what does the paper",
            "summarize the", "summary of"
        ]
        
        for keyword in research_keywords:
            if keyword in question_lower:
                logger.info(f"Keyword routing to RESEARCH: {keyword}")
                return "research"
    
    # Code keywords
    code_keywords = [
        "code", "implement", "python", "java", "javascript",
        "function", "class", "algorithm", "program",
        "syntax", "debug", "error", "script",
        "write", "create", "build", "develop",
        "example code", "show me how to code",
        "programming", "coding"
    ]
    
    for keyword in code_keywords:
        if keyword in question_lower:
            logger.info("Keyword routing to CODE")
            return "code"
    
    # Default to concept for general questions
    logger.info("Keyword routing to CONCEPT (default)")
    return "concept"


def route_query_with_context(
    question: str,
    has_documents: bool = False
) -> Literal["concept", "code", "research", "practice"]:
    """
    Route query with additional context (alias for route_query).
    
    Args:
        question: User's question
        has_documents: Whether user has uploaded documents
    
    Returns:
        Route to take
    """
    return route_query(question, has_documents)


def get_agent_description(route: str) -> str:
    """
    Get description of what the agent does.
    
    Args:
        route: Agent route
    
    Returns:
        Description string
    """
    descriptions = {
        "concept": "Explaining concepts with personalized multi-level explanations",
        "code": "Generating code examples and implementations",
        "research": "Searching your documents and providing cited answers",
        "practice": "Generating practice questions and exercises"
    }
    
    return descriptions.get(route, "Processing your request")


# Export functions
__all__ = [
    "route_query",
    "route_query_structured",
    "route_query_keyword",
    "route_query_with_context",
    "get_agent_description",
    "RouterDecision"
]


def route_query(
    question: str,
    has_documents: bool = False
) -> Literal["concept", "code", "research", "practice"]:
    """Simple routing function for backward compatibility."""
    decision = route_query_structured(question, has_documents)
    return decision.route
