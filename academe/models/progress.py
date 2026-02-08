"""
Learning Progress Models for Academe

Track user's learning progress, concept mastery, and study sessions.
Part of the Memory Module enhancement.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum

from academe.utils import get_current_time

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for testing without pydantic
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    def Field(default=None, default_factory=None, alias=None):
        if default_factory:
            return default_factory()
        return default


class ConceptMastery(str, Enum):
    """Levels of concept mastery."""
    NOVICE = "novice"          # 0-20% understanding
    LEARNING = "learning"       # 20-40% understanding
    COMPETENT = "competent"     # 40-60% understanding
    PROFICIENT = "proficient"   # 60-80% understanding
    EXPERT = "expert"           # 80-100% understanding


class LearningProgress(BaseModel):
    """
    Track user's progress on specific topics/concepts.
    Part of the enhanced Memory Module.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    concept: str  # e.g., "eigenvalues", "gradient_descent", "bayes_theorem"

    # Mastery tracking
    mastery_level: ConceptMastery = Field(default=ConceptMastery.NOVICE)
    mastery_score: float = Field(default=0.0)  # 0.0 to 1.0

    # Interaction tracking
    questions_attempted: int = Field(default=0)
    questions_correct: int = Field(default=0)
    accuracy_rate: float = Field(default=0.0)

    # Time tracking
    total_study_time_minutes: float = Field(default=0.0)
    last_studied: datetime = Field(default_factory=get_current_time)
    first_seen: datetime = Field(default_factory=get_current_time)

    # Document context
    related_documents: List[str] = Field(default_factory=list)  # Document IDs
    related_chunks: List[str] = Field(default_factory=list)     # Chunk IDs that mention this concept

    # Learning history
    practice_history: List[Dict[str, Any]] = Field(default_factory=list)
    explanation_views: int = Field(default=0)  # Times user asked about this
    code_examples_requested: int = Field(default=0)

    # Spaced repetition data
    review_count: int = Field(default=0)
    next_review_date: Optional[datetime] = None
    retention_strength: float = Field(default=0.0)  # 0.0 to 1.0

    def calculate_mastery_level(self) -> ConceptMastery:
        """Calculate mastery level based on score."""
        if self.mastery_score >= 0.8:
            return ConceptMastery.EXPERT
        elif self.mastery_score >= 0.6:
            return ConceptMastery.PROFICIENT
        elif self.mastery_score >= 0.4:
            return ConceptMastery.COMPETENT
        elif self.mastery_score >= 0.2:
            return ConceptMastery.LEARNING
        else:
            return ConceptMastery.NOVICE

    def update_from_practice(self, correct: bool, time_spent: float = 0):
        """Update progress from a practice attempt."""
        self.questions_attempted += 1
        if correct:
            self.questions_correct += 1

        # Update accuracy
        if self.questions_attempted > 0:
            self.accuracy_rate = self.questions_correct / self.questions_attempted

        # Update mastery score (weighted average of accuracy and other factors)
        self.mastery_score = min(1.0, (
            self.accuracy_rate * 0.5 +  # 50% weight on accuracy
            min(1.0, self.explanation_views / 10) * 0.2 +  # 20% weight on engagement
            min(1.0, self.total_study_time_minutes / 60) * 0.2 +  # 20% weight on time
            min(1.0, self.review_count / 5) * 0.1  # 10% weight on reviews
        ))

        # Update mastery level
        self.mastery_level = self.calculate_mastery_level()

        # Update time
        self.total_study_time_minutes += time_spent
        self.last_studied = get_current_time()

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "LearningProgress":
        """Create LearningProgress from MongoDB document."""
        if not data:
            return None
        
        # Make a copy to avoid modifying original
        data = dict(data)
        
        # Convert ObjectId to string and use the alias
        if "_id" in data:
            data["_id"] = str(data["_id"])
        
        # Convert datetime strings if needed
        for field in ["last_studied", "first_seen", "next_review_date"]:
            if field in data and isinstance(data[field], str):
                from datetime import datetime
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)


class StudySession(BaseModel):
    """
    Track individual study sessions for learning analytics.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    session_start: datetime = Field(default_factory=get_current_time)
    session_end: Optional[datetime] = None
    duration_minutes: float = Field(default=0.0)

    # Session activity
    concepts_studied: List[str] = Field(default_factory=list)
    documents_accessed: List[str] = Field(default_factory=list)
    questions_asked: int = Field(default=0)
    practice_problems_solved: int = Field(default=0)
    practice_problems_correct: int = Field(default=0)

    # Performance metrics
    average_accuracy: float = Field(default=0.0)
    concepts_mastered: List[str] = Field(default_factory=list)  # Concepts that leveled up
    weak_areas_identified: List[str] = Field(default_factory=list)

    # Session type
    session_type: str = Field(default="general")  # general, practice, research, review
    focus_concept: Optional[str] = None  # Main concept if focused session

    def end_session(self):
        """End the study session and calculate metrics."""
        self.session_end = get_current_time()

        # Calculate duration
        if self.session_start and self.session_end:
            delta = self.session_end - self.session_start
            self.duration_minutes = delta.total_seconds() / 60

        # Calculate accuracy
        if self.practice_problems_solved > 0:
            self.average_accuracy = self.practice_problems_correct / self.practice_problems_solved

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "StudySession":
        """Create StudySession from MongoDB document."""
        if not data:
            return None
        
        # Make a copy to avoid modifying original
        data = dict(data)
        
        # Convert ObjectId to string and use the alias
        if "_id" in data:
            data["_id"] = str(data["_id"])
        
        # Convert datetime strings if needed
        for field in ["session_start", "session_end"]:
            if field in data and isinstance(data[field], str):
                from datetime import datetime
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)

class ConceptRelationship(BaseModel):
    """
    Track relationships between concepts for learning path generation.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    concept_from: str
    concept_to: str
    relationship_type: str  # "prerequisite", "related", "application", "builds_on"
    strength: float = Field(default=1.0)  # How strong the relationship is

    # Context
    source_document: Optional[str] = None
    extracted_from: str = Field(default="user_interaction")  # or "document_analysis"


class LearningPath(BaseModel):
    """
    Personalized learning path for a user.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    goal_concept: str  # Target concept to master

    # Path details
    path_concepts: List[str] = Field(default_factory=list)  # Ordered list
    current_position: int = Field(default=0)

    # Progress
    completed_concepts: List[str] = Field(default_factory=list)
    estimated_hours_remaining: float = Field(default=0.0)
    completion_percentage: float = Field(default=0.0)

    # Metadata
    created_at: datetime = Field(default_factory=get_current_time)
    last_updated: datetime = Field(default_factory=get_current_time)
    path_strategy: str = Field(default="shortest")  # shortest, comprehensive, prerequisite_first

    def get_next_concept(self) -> Optional[str]:
        """Get the next concept to study."""
        if self.current_position < len(self.path_concepts):
            return self.path_concepts[self.current_position]
        return None

    def mark_concept_complete(self, concept: str):
        """Mark a concept as completed."""
        if concept not in self.completed_concepts:
            self.completed_concepts.append(concept)

        # Update position if this was the current concept
        if (self.current_position < len(self.path_concepts) and
            self.path_concepts[self.current_position] == concept):
            self.current_position += 1

        # Update completion percentage
        if len(self.path_concepts) > 0:
            self.completion_percentage = len(self.completed_concepts) / len(self.path_concepts)

        self.last_updated = get_current_time()


class MemoryContext(BaseModel):
    """
    Enhanced memory context from previous messages.
    Provides context awareness across conversations.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    conversation_id: str

    # Recent context
    recent_concepts: List[str] = Field(default_factory=list)  # Last 10 concepts discussed
    recent_documents: List[str] = Field(default_factory=list)  # Last 5 documents accessed
    recent_mistakes: List[Dict[str, Any]] = Field(default_factory=list)  # Recent errors to avoid

    # Current focus
    current_topic: Optional[str] = None
    current_goal: Optional[str] = None
    learning_path_active: bool = Field(default=False)

    # Conversation flow
    question_sequence: List[str] = Field(default_factory=list)  # Track question progression
    requires_followup: bool = Field(default=False)
    pending_clarifications: List[str] = Field(default_factory=list)

    # User preferences learned
    preferred_explanation_depth: str = Field(default="balanced")
    prefers_examples: bool = Field(default=True)
    prefers_math_notation: bool = Field(default=False)

    # Timestamp
    last_updated: datetime = Field(default_factory=get_current_time)

    def add_concept(self, concept: str):
        """Add a concept to recent concepts."""
        if concept not in self.recent_concepts:
            self.recent_concepts.insert(0, concept)
            # Keep only last 10
            self.recent_concepts = self.recent_concepts[:10]
        self.last_updated = get_current_time()

    def add_document(self, doc_id: str):
        """Add a document to recent documents."""
        if doc_id not in self.recent_documents:
            self.recent_documents.insert(0, doc_id)
            # Keep only last 5
            self.recent_documents = self.recent_documents[:5]
        self.last_updated = get_current_time()

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "MemoryContext":
        """Create MemoryContext from MongoDB document."""
        if not data:
            return None
        
        # Make a copy to avoid modifying original
        data = dict(data)
        
        # Convert ObjectId to string and use the alias
        if "_id" in data:
            data["_id"] = str(data["_id"])
        
        # Convert datetime strings if needed
        if "last_updated" in data and isinstance(data["last_updated"], str):
            from datetime import datetime
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        
        return cls(**data)


# Export all models
__all__ = [
    "ConceptMastery",
    "LearningProgress",
    "StudySession",
    "ConceptRelationship",
    "LearningPath",
    "MemoryContext"
]