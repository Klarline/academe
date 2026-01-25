"""
Concept Explainer Agent - Explains concepts at multiple levels.

This is the CORE INNOVATION of Academe - inspired by the viral "granny mode"
prompting technique. The agent provides TWO levels of explanation:

1. INTUITIVE (Granny Mode): Simple analogies, no jargon, pure intuition
2. TECHNICAL: Full mathematical rigor with formulas and terminology

This adaptive approach helps learners at any level understand complex concepts.
"""

from typing import Literal
from academe.config import get_llm
from langchain.prompts import ChatPromptTemplate


# Explanation level instructions
EXPLANATION_LEVELS = {
    "intuitive": """
Explain using simple, everyday language that a 70-year-old with no technical 
background could understand. Use relatable analogies and real-world examples.
NO jargon, NO math notation, NO technical terms. Focus purely on intuition.
Make it feel like explaining to a curious grandparent over tea.
""",
    
    "technical": """
Provide a rigorous, graduate-level explanation with proper mathematical notation.
Include formulas, algorithms, and precise technical terminology.
Assume the reader has a strong mathematics and computer science background.
Be thorough and academically complete.
"""
}


def create_concept_explainer():
    """
    Creates the Concept Explainer agent with multi-level prompting.
    
    This agent is the heart of Academe's innovation. It generates explanations
    at two different levels, allowing learners to choose their preferred depth.
    
    Returns:
        LangChain chain configured for multi-level explanations
    """
    
    llm = get_llm(temperature=0.7)
    
    # Multi-level explanation prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert educator with a gift for adaptive teaching.

Your specialty is explaining complex machine learning concepts at multiple levels,
making them accessible to learners with different backgrounds.

You will provide TWO versions of your explanation:

1. **INTUITIVE VERSION (Granny Mode)**:
{intuitive_instruction}

2. **TECHNICAL VERSION**:
{technical_instruction}

Format your response EXACTLY as follows:

## Intuitive Explanation 🎈

[Your intuitive explanation here - simple, relatable, no jargon]

## Technical Explanation 🔬

[Your technical explanation here - rigorous, mathematical, complete]

## Key Takeaway 💡

[One sentence that captures the core insight - the "aha!" moment]

## Why This Matters 🎯

[2-3 sentences explaining why this concept is important]

Remember:
- The intuitive version should make a complete beginner say "Oh, I get it!"
- The technical version should satisfy a graduate student's need for rigor
- Both versions should be accurate - just different in presentation
- Use analogies freely in intuitive, formulas freely in technical
"""),
        ("human", "Explain this concept: {question}")
    ])
    
    chain = prompt | llm
    return chain


def explain_concept(
    question: str, 
    level: Literal["both", "intuitive", "technical"] = "both"
) -> str:
    """
    Explains an concept at the specified level(s).
    
    This is the main function that users and other agents will call.
    
    Args:
        question: The concept to explain (e.g., "What is gradient descent?")
        level: Which explanation level(s) to provide:
            - "both": Both intuitive and technical (default)
            - "intuitive": Only the simple, granny-mode explanation
            - "technical": Only the rigorous mathematical explanation
    
    Returns:
        Formatted explanation at the requested level(s)
    
    Examples:
        >>> explain_concept("What is PCA?", level="both")
        # Returns both intuitive and technical explanations
        
        >>> explain_concept("Explain eigenvalues", level="intuitive")
        # Returns only simple, intuitive explanation
    """
    
    explainer = create_concept_explainer()
    
    # Get full response with both levels
    response = explainer.invoke({
        "question": question,
        "intuitive_instruction": EXPLANATION_LEVELS["intuitive"],
        "technical_instruction": EXPLANATION_LEVELS["technical"]
    })
    
    content = response.content
    
    # If user wants both, return everything
    if level == "both":
        return content
    
    # Extract only requested level
    if level == "intuitive":
        # Extract content between "## Intuitive" and "## Technical"
        try:
            start = content.find("## Intuitive Explanation")
            end = content.find("## Technical Explanation")
            if start != -1 and end != -1:
                return content[start:end].strip()
        except:
            pass
    
    elif level == "technical":
        # Extract content from "## Technical" onwards
        try:
            start = content.find("## Technical Explanation")
            if start != -1:
                return content[start:].strip()
        except:
            pass
    
    # Fallback: return full response if extraction fails
    return content


def explain_concept_interactive(question: str) -> dict:
    """
    Interactive version that returns structured data for UI display.
    
    This version is useful when building a web interface where you want
    to display each section separately.
    
    Args:
        question: The concept to explain
    
    Returns:
        Dictionary with structured explanation sections:
        {
            "intuitive": str,
            "technical": str,
            "key_takeaway": str,
            "why_matters": str,
            "full_response": str
        }
    """
    
    full_response = explain_concept(question, level="both")
    
    # Parse sections (basic parsing - can be improved)
    result = {
        "full_response": full_response,
        "intuitive": "",
        "technical": "",
        "key_takeaway": "",
        "why_matters": ""
    }
    
    # Simple section extraction
    sections = full_response.split("##")
    for section in sections:
        section = section.strip()
        if section.startswith("Intuitive"):
            result["intuitive"] = section
        elif section.startswith("Technical"):
            result["technical"] = section
        elif section.startswith("Key Takeaway"):
            result["key_takeaway"] = section
        elif section.startswith("Why This Matters"):
            result["why_matters"] = section
    
    return result


# Export main functions
__all__ = [
    "explain_concept",
    "explain_concept_interactive",
    "create_concept_explainer"
]