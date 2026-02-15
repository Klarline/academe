"""
Pydantic models for practice sessions.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from bson import ObjectId


class PracticeQuestionResult(BaseModel):
    """Single question result in a practice session."""
    question: str
    type: str  # mcq, short, code, explain
    options: Optional[List[str]] = None
    correct_answer: str
    user_answer: str
    is_correct: bool
    time_spent_seconds: int = 0
    explanation: str


class PracticeSession(BaseModel):
    """Complete practice session."""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    topic: str
    difficulty: str
    questions: List[dict]  # Simplified for JSON compatibility
    score: int
    total_questions: int
    percentage: float
    started_at: datetime
    completed_at: datetime
    duration_minutes: int
    question_types: List[str]
    
    model_config = ConfigDict()


class PracticeSessionCreate(BaseModel):
    """Request to create practice session."""
    topic: str
    difficulty: str
    questions: List[dict]
    score: int
    total_questions: int
    percentage: float
    started_at: datetime
    completed_at: datetime
    duration_minutes: int
    question_types: List[str]


class PracticeStats(BaseModel):
    """Practice statistics over time."""
    total_sessions: int
    total_questions_answered: int
    average_score: float
    sessions_by_topic: dict
    recent_sessions: List[dict]
    improvement_trend: List[float]


__all__ = [
    "PracticeQuestionResult",
    "PracticeSession", 
    "PracticeSessionCreate",
    "PracticeStats"
]
