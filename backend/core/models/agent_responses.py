"""
Pydantic models for agent responses.

These models define the structured output format for each agent,
enabling type-safe responses and modern LangChain patterns.
"""

from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class ConceptExplanationResponse(BaseModel):
    """Response model for Concept Explainer agent."""
    
    intuitive_explanation: Optional[str] = Field(
        None,
        description="Simple, intuitive explanation using analogies"
    )
    
    technical_explanation: Optional[str] = Field(
        None,
        description="Rigorous, technical explanation with formulas"
    )
    
    key_takeaway: str = Field(
        ...,
        description="One sentence capturing the core insight"
    )
    
    why_matters: str = Field(
        ...,
        description="2-3 sentences explaining importance"
    )
    
    concepts_covered: list[str] = Field(
        default_factory=list,
        description="List of key concepts covered"
    )


class CodeGenerationResponse(BaseModel):
    """Response model for Code Helper agent."""
    
    overview: str = Field(
        ...,
        description="Brief description of what the code does"
    )
    
    code: str = Field(
        ...,
        description="Complete, working code implementation"
    )
    
    usage_example: str = Field(
        ...,
        description="Example showing how to use the code"
    )
    
    explanation: str = Field(
        ...,
        description="Explanation of how the code works"
    )
    
    key_concepts: list[str] = Field(
        default_factory=list,
        description="Main programming concepts demonstrated"
    )
    
    time_complexity: Optional[str] = Field(
        None,
        description="Time complexity analysis (e.g., 'O(n log n)')"
    )
    
    space_complexity: Optional[str] = Field(
        None,
        description="Space complexity analysis (e.g., 'O(n)')"
    )


class RouterDecision(BaseModel):
    """Response model for Router agent."""
    
    route: Literal["concept", "code"] = Field(
        ...,
        description="Which agent should handle this query"
    )
    
    reasoning: str = Field(
        ...,
        description="Brief explanation of routing decision"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )


class ResearchResponse(BaseModel):
    """Response model for Research agent."""
    
    summary: str = Field(
        ...,
        description="Comprehensive summary of research findings"
    )
    
    key_findings: list[str] = Field(
        default_factory=list,
        description="List of main findings"
    )
    
    sources_used: list[str] = Field(
        default_factory=list,
        description="List of source documents referenced"
    )
    
    related_concepts: list[str] = Field(
        default_factory=list,
        description="Related concepts to explore"
    )
    
    citations: Optional[list[str]] = Field(
        None,
        description="Formatted citations if available"
    )


class PracticeQuestion(BaseModel):
    """Single practice question model."""
    
    question_text: str = Field(description="The actual question text")
    question_type: Literal["mcq", "short", "code", "explain"] = Field(description="Type of question")
    options: Optional[List[str]] = Field(default=None, description="4 options for mcq type (list of strings)")
    correct_answer: str = Field(description="The correct answer")
    explanation: str = Field(description="Explanation of the answer")
    difficulty: Optional[str] = Field(default=None, description="Difficulty level")


class PracticeSetResponse(BaseModel):
    """Response model for Practice Generator agent."""
    
    questions: List[PracticeQuestion] = Field(
        ...,
        description="List of generated practice questions"
    )
    
    topic: str = Field(
        ...,
        description="Topic of the practice set"
    )
    
    difficulty_level: str = Field(
        ...,
        description="Overall difficulty level"
    )


# Export all response models
__all__ = [
    "ConceptExplanationResponse",
    "CodeGenerationResponse",
    "RouterDecision",
    "ResearchResponse",
    "PracticeQuestion",
    "PracticeSetResponse",
]