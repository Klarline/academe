"""
Router Agent - Routes queries to appropriate specialized agent.

The router analyzes user queries and decides whether to send them to:
- Concept Explainer: for explanations, definitions, theory
- Code Helper: for implementations, code examples, programming
"""

from typing import Literal
from academe.config import get_llm


def route_query(question: str) -> Literal["concept", "code"]:
    """
    Routes user question to appropriate agent using keyword matching.
    
    This is v0.1 implementation using simple keywords.
    For v1.0, we'll upgrade to LLM-based routing for better accuracy.
    
    Args:
        question: User's question or request
    
    Returns:
        "concept" - Route to Concept Explainer
        "code" - Route to Code Helper
    
    Examples:
        >>> route_query("What is gradient descent?")
        'concept'
        >>> route_query("Show me gradient descent code")
        'code'
    """
    
    question_lower = question.lower()
    
    # Keywords that indicate code request
    code_keywords = [
        "code", "implement", "implementation", "python", "numpy",
        "show me", "write", "program", "function", "script",
        "example code", "how to code", "syntax", "programming",
        "build", "create a function", "write a program"
    ]
    
    # Check for code keywords
    for keyword in code_keywords:
        if keyword in question_lower:
            return "code"
    
    # Default to concept explanation
    return "concept"


def route_query_llm(question: str) -> Literal["concept", "code"]:
    """
    Advanced LLM-based routing for more accurate classification.
    
    This is more expensive (uses LLM call) but more accurate than keyword matching.
    Use this in v1.0 or when keyword routing isn't accurate enough.
    
    Args:
        question: User's question or request
    
    Returns:
        "concept" - Route to Concept Explainer
        "code" - Route to Code Helper
    """
    
    llm = get_llm(temperature=0)  # Use low temperature for consistent routing
    
    prompt = f"""You are a routing agent for an learning assistant.

Analyze this user query and decide which agent should handle it:

- Return "concept" if the user wants:
  * Explanation of concepts
  * Definitions or theory
  * Understanding how something works
  * Intuition behind algorithms
  
- Return "code" if the user wants:
  * Code implementation
  * Programming examples
  * Syntax or functions
  * "Show me how to code X"

User query: "{question}"

Respond with ONLY one word: concept or code"""

    response = llm.invoke(prompt)
    result = response.content.strip().lower()
    
    # Validate response
    if result not in ["concept", "code"]:
        # Fallback to keyword routing if LLM gives unexpected response
        print(f"Warning: LLM returned unexpected value '{result}', using keyword routing")
        return route_query(question)
    
    return result  # type: ignore


# Export the function we'll use
# For v0.1, we use keyword routing
# For v1.0, switch to route_query_llm for better accuracy
__all__ = ["route_query", "route_query_llm"]