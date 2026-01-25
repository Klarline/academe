"""
Code Helper Agent - Generates educational code with detailed explanations.

This agent creates clean, well-commented Python implementations of algorithms
and concepts. Focus is on educational clarity, not production optimization.
"""

from academe.config import get_llm
from langchain.prompts import ChatPromptTemplate


def create_code_helper():
    """
    Creates the Code Helper agent for generating educational code.
    
    Returns:
        LangChain chain configured for code generation
    """
    
    llm = get_llm(temperature=0.3)  # Lower temperature for more consistent code
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert coding instructor who writes clean, educational Python code.

Your specialty is creating code that teaches concepts clearly. You write code that:
- Is correct and executable
- Follows Python best practices
- Uses clear variable names
- Has detailed comments explaining WHAT and WHY
- Includes docstrings
- Uses NumPy for mathematical operations
- Keeps it simple and educational (not production-optimized)

Format your response EXACTLY as follows:

## Overview 📋

[2-3 sentences: What this code does and what concept it demonstrates]

## Implementation 💻
```python
[Your complete, working code here with detailed comments]
```

## Usage Example 🚀
```python
[Simple example showing how to use the code with sample data]
```

## How It Works 🔍

[Step-by-step explanation of the key parts:
- What each major section does
- Why certain design choices were made
- Any important concepts being applied]

## Key Concepts 💡

[Bullet points of the main ML/programming concepts demonstrated:
- Concept 1
- Concept 2
- etc.]

Remember:
- Every function needs a docstring
- Complex lines need inline comments
- Show the complete, runnable code
- Make it beginner-friendly but not dumbed down
"""),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    return chain


def generate_code(question: str) -> str:
    """
    Generates code with detailed explanations.
    
    This is the main function for code generation. It creates complete,
    educational implementations of algorithms and concepts.
    
    Args:
        question: What to implement (e.g., "Implement gradient descent in NumPy")
    
    Returns:
        Formatted code with explanations and examples
    
    Examples:
        >>> code = generate_code("Implement linear regression from scratch")
        >>> print(code)
        # Returns complete implementation with explanations
        
        >>> code = generate_code("Show me how to compute PCA with NumPy")
        >>> print(code)
        # Returns PCA implementation with usage example
    """
    
    code_helper = create_code_helper()
    
    response = code_helper.invoke({
        "question": question
    })
    
    return response.content


def generate_code_with_explanation(concept: str, detail_level: str = "standard") -> str:
    """
    Generates code with adjustable explanation detail.
    
    Args:
        concept: The concept to implement
        detail_level: How detailed the explanations should be:
            - "minimal": Just code with basic comments
            - "standard": Code with good explanations (default)
            - "detailed": Extensive step-by-step explanations
    
    Returns:
        Generated code with appropriate level of explanation
    """
    
    if detail_level == "minimal":
        question = f"Write clean Python code for {concept}. Include basic comments but keep explanations brief."
    elif detail_level == "detailed":
        question = f"Write Python code for {concept} with very detailed, line-by-line explanations for a beginner."
    else:  # standard
        question = f"Implement {concept} in Python with clear explanations."
    
    return generate_code(question)


def generate_code_snippet(question: str) -> dict:
    """
    Generates code and returns structured output for UI display.
    
    Useful for web interfaces where you want to display sections separately.
    
    Args:
        question: What to implement
    
    Returns:
        Dictionary with structured sections:
        {
            "overview": str,
            "code": str,
            "example": str,
            "explanation": str,
            "concepts": str,
            "full_response": str
        }
    """
    
    full_response = generate_code(question)
    
    result = {
        "full_response": full_response,
        "overview": "",
        "code": "",
        "example": "",
        "explanation": "",
        "concepts": ""
    }
    
    # Parse sections (basic parsing)
    sections = full_response.split("##")
    for section in sections:
        section = section.strip()
        if section.startswith("Overview"):
            result["overview"] = section
        elif section.startswith("Implementation"):
            result["code"] = section
        elif section.startswith("Usage Example"):
            result["example"] = section
        elif section.startswith("How It Works"):
            result["explanation"] = section
        elif section.startswith("Key Concepts"):
            result["concepts"] = section
    
    return result


# Export main functions
__all__ = [
    "generate_code",
    "generate_code_with_explanation",
    "generate_code_snippet",
    "create_code_helper"
]