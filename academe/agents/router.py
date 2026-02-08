"""
Router Agent - Routes queries to appropriate agents including research.

Uses modern LangChain with structured output for reliable routing decisions.
"""

import logging
from typing import Literal
from pydantic import BaseModel, Field

from academe.config import get_llm

logger = logging.getLogger(__name__)


class RouterDecision(BaseModel):
    """Structured router decision with reasoning."""
    
    route: Literal["concept", "code", "research"] = Field(
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
    
    # Use structured output with Pydantic model
    structured_llm = llm.with_structured_output(RouterDecision)
    
    # Build routing rules based on document availability
    document_context = ""
    if has_documents:
        document_context = """
- Route to "research" if the user wants:
  * Information from THEIR uploaded documents
  * Queries about "my notes", "my textbook", "my PDF"
  * Document summaries or citations
  * Questions with "according to", "in the reading", "from my documents"
  * Practice problems from uploaded materials
  * "What does the author say...", "Find in my notes..."
"""
    else:
        document_context = """
NOTE: User has NO uploaded documents, so "research" route is NOT available.
Do NOT route to "research" - use "concept" instead for explanations.
"""
    
    prompt = f"""Analyze this user query and determine which agent should handle it.

ROUTING RULES:
- Route to "concept" if the user wants:
  * General explanation of concepts or theory
  * Understanding WHY or WHAT something is (without code)
  * Definitions, intuition, or learning
  * "What is...", "Why does...", "Explain the concept of..."
  * "How does X work?" (asking for conceptual understanding)
  * Multi-level explanations adapted to their learning level
  * Questions about theory, mathematics, or algorithms (without code)
  
- Route to "code" if the user wants:
  * Actual code implementation or examples
  * Programming syntax, functions, or algorithms IN CODE
  * "Show me code", "Implement in Python/Java/etc", "Write a function..."
  * "How to implement...", "Implementation of...", "Code for..."
  * Specific programming language mentioned (Python, Java, C++, etc)
  * Debugging or code explanations
  * Questions containing: "code", "implement", "program", "function", "script"

{document_context}

IMPORTANT DISAMBIGUATION:
- "What is the implementation?" → CODE (asking for actual code)
- "How does it work?" → CONCEPT (asking for explanation)
- "Explain the algorithm" → CONCEPT (theory)
- "Show me the algorithm in Python" → CODE (wants code)

User query: "{question}"

Provide:
1. route: "concept", "code", or "research" (only if user has documents)
2. reasoning: Clear explanation of why this routing decision
3. confidence: 0.0 to 1.0 (how certain are you?)"""

    try:
        response = structured_llm.invoke(prompt)
        
        # If user has no documents but LLM routed to research, override
        if not has_documents and response.route == "research":
            logger.warning("LLM routed to research but user has no documents, overriding to concept")
            response.route = "concept"
            response.reasoning = "No documents available, using general explanation instead"
            response.confidence = 0.7
        
        logger.info(f"Routed to {response.route.upper()} (confidence: {response.confidence:.2f})")
        return response
        
    except Exception as e:
        logger.error(f"Structured routing failed: {e}, falling back to keyword routing")
        # Fallback to keyword-based routing
        route = route_query_keyword(question, has_documents)
        return RouterDecision(
            route=route,
            reasoning="Fallback to keyword-based routing due to LLM error",
            confidence=0.6
        )


def route_query(
    question: str,
    has_documents: bool = False
) -> Literal["concept", "code", "research"]:
    """
    Simple routing function for backward compatibility.
    
    Args:
        question: User's question
        has_documents: Whether user has uploaded documents
    
    Returns:
        "concept", "code", or "research"
    """
    decision = route_query_structured(question, has_documents)
    return decision.route


def route_query_keyword(
    question: str,
    has_documents: bool = False
) -> Literal["concept", "code", "research"]:
    """
    Fallback keyword-based routing (fast but less accurate).
    
    Use this if LLM routing fails or for testing.
    
    Args:
        question: User's question
        has_documents: Whether user has uploaded documents
    
    Returns:
        "concept", "code", or "research"
    """
    question_lower = question.lower()
    
    # Research agent keywords (only if user has documents)
    if has_documents:
        research_keywords = [
            "my document", "my notes", "my pdf", "my file",
            "uploaded", "from the text", "in the reading",
            "according to", "based on the", "cite", "source",
            "find in", "search for", "look up",
            "what does the author", "what does the paper",
            "summarize the", "summary of",
            "quiz me", "test me", "practice",
            "flashcard", "example from"
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
) -> Literal["concept", "code", "research"]:
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
        "research": "Searching your documents and providing cited answers"
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