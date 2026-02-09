"""User profile models for Academe."""

from bson import ObjectId
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from core.utils import get_current_time


class LearningLevel(str, Enum):
    """User's current learning level."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    def get_description(self) -> str:
        """Get human-readable description of learning level."""
        descriptions = {
            "beginner": "New to ML concepts, needs foundational explanations",
            "intermediate": "Familiar with basics, ready for deeper concepts",
            "advanced": "Strong understanding, can handle complex theory"
        }
        return descriptions.get(self.value, "")


class LearningGoal(str, Enum):
    """User's primary learning objective."""

    QUICK_REVIEW = "quick_review"
    DEEP_LEARNING = "deep_learning"
    EXAM_PREP = "exam_prep"
    RESEARCH = "research"

    def get_description(self) -> str:
        """Get human-readable description of learning goal."""
        descriptions = {
            "quick_review": "Quick refresh of concepts",
            "deep_learning": "Thorough understanding with practice",
            "exam_prep": "Focused preparation for exams",
            "research": "In-depth exploration for research"
        }
        return descriptions.get(self.value, "")


class ExplanationStyle(str, Enum):
    """User's preferred explanation style."""

    INTUITIVE = "intuitive"
    BALANCED = "balanced"
    TECHNICAL = "technical"

    def get_description(self) -> str:
        """Get human-readable description of explanation style."""
        descriptions = {
            "intuitive": "Simple analogies and everyday examples",
            "balanced": "Mix of intuition and technical details",
            "technical": "Rigorous mathematical explanations"
        }
        return descriptions.get(self.value, "")


class RAGFallbackPreference(str, Enum):
    """User preference for handling no-context scenarios."""
    
    ALWAYS_ASK = "always_ask"
    PREFER_GENERAL = "prefer_general"
    STRICT_DOCUMENTS = "strict_documents"
    
    def get_description(self) -> str:
        """Get human-readable description."""
        descriptions = {
            self.ALWAYS_ASK: "Ask me each time what to do",
            self.PREFER_GENERAL: "Use general knowledge automatically",
            self.STRICT_DOCUMENTS: "Only answer from my documents"
        }
        return descriptions[self]


class UserProfile(BaseModel):
    """User profile with authentication and personalization settings."""

    # MongoDB ID field
    id: Optional[str] = Field(
        default=None,
        alias="_id",
        description="Unique user identifier"
    )

    # Authentication fields
    email: EmailStr = Field(
        ...,
        description="User email address for authentication"
    )
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Display name (3-50 characters, alphanumeric with _ and -)"
    )
    
    password_hash: str = Field(
        ...,
        description="Bcrypt hashed password"
    )

    # Profile preferences
    learning_level: LearningLevel = Field(
        default=LearningLevel.INTERMEDIATE,
        description="User's current learning proficiency level for personalization"
    )
    
    learning_goal: LearningGoal = Field(
        default=LearningGoal.DEEP_LEARNING,
        description="Primary learning objective that guides content depth and focus"
    )
    
    explanation_style: ExplanationStyle = Field(
        default=ExplanationStyle.BALANCED,
        description="Preferred approach to explanations (intuitive vs technical)"
    )
    
    rag_fallback_preference: RAGFallbackPreference = Field(
        default=RAGFallbackPreference.ALWAYS_ASK,
        description="Behavior when documents don't contain answer to user's question"
    )

    # Additional preferences
    preferred_code_language: str = Field(
        default="python",
        description="Preferred programming language for code examples"
    )
    
    include_math_formulas: bool = Field(
        default=True,
        description="Include mathematical notation and formulas in explanations"
    )
    
    include_visualizations: bool = Field(
        default=True,
        description="Include ASCII diagrams and visual aids when helpful"
    )

    # System flags
    has_completed_onboarding: bool = Field(
        default=False,
        description="Whether user has completed initial onboarding flow"
    )
    
    has_seen_rag_explanation: bool = Field(
        default=False,
        description="Whether user has been educated about RAG feature during onboarding"
    )
    
    is_active: bool = Field(
        default=True,
        description="Account active status"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=get_current_time,
        description="Account creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=get_current_time,
        description="Last profile update timestamp"
    )
    
    last_login_at: Optional[datetime] = Field(
        default=None,
        description="Most recent login timestamp"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username must contain only letters, numbers, underscores, and hyphens")
        return v.lower()

    def to_mongo_dict(self) -> dict:
        """Convert to MongoDB-compatible dictionary."""
        data = self.model_dump(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = self.id
        return data

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "UserProfile":
        """
        Create UserProfile from MongoDB document.
        
        Args:
            data: MongoDB document dictionary
        
        Returns:
            UserProfile instance
        """
        if not data:
            return None
        
        # Convert ObjectId to string
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        
        # Convert datetime strings to datetime objects if needed
        for field in ["created_at", "updated_at", "last_login_at"]:
            if field in data and isinstance(data[field], str):
                from datetime import datetime
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert enum strings back to enums
        if "learning_level" in data and isinstance(data["learning_level"], str):
            data["learning_level"] = LearningLevel(data["learning_level"])
        if "learning_goal" in data and isinstance(data["learning_goal"], str):
            data["learning_goal"] = LearningGoal(data["learning_goal"])
        if "explanation_style" in data and isinstance(data["explanation_style"], str):
            data["explanation_style"] = ExplanationStyle(data["explanation_style"])
        if "rag_fallback_preference" in data and isinstance(data["rag_fallback_preference"], str):
            data["rag_fallback_preference"] = RAGFallbackPreference(data["rag_fallback_preference"])
        
        return cls(**data)

    def get_prompt_context(self) -> str:
        """Generate context string for LLM prompts based on user preferences."""
        context_parts = [
            f"User learning level: {self.learning_level.value}",
            f"Learning goal: {self.learning_goal.value}",
            f"Preferred explanation style: {self.explanation_style.value}",
        ]

        if self.learning_level == LearningLevel.BEGINNER:
            context_parts.append("Provide foundational explanations with simple examples")
        elif self.learning_level == LearningLevel.ADVANCED:
            context_parts.append("Include advanced concepts and technical depth")

        if self.explanation_style == ExplanationStyle.INTUITIVE:
            context_parts.append("Use analogies and avoid heavy mathematical notation")
        elif self.explanation_style == ExplanationStyle.TECHNICAL:
            context_parts.append("Include rigorous mathematical formulations")

        if self.learning_goal == LearningGoal.EXAM_PREP:
            context_parts.append("Focus on key concepts likely to appear in exams")
        elif self.learning_goal == LearningGoal.RESEARCH:
            context_parts.append("Provide comprehensive coverage with citations")

        return "\n".join(context_parts)

    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }