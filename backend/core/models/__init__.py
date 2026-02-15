"""Database models for Academe."""

from .conversation import Conversation, ConversationSummary, Message
from .user import ExplanationStyle, LearningGoal, LearningLevel, UserProfile, RAGFallbackPreference
from .document import Document, DocumentChunk, DocumentStatus, DocumentType, DocumentSearchResult
from .progress import ConceptMastery, LearningProgress, StudySession, MemoryContext
from .practice import PracticeSession, PracticeQuestionResult, PracticeSessionCreate, PracticeStats
from .agent_responses import (
    ConceptExplanationResponse,
    CodeGenerationResponse,
    RouterDecision,
    ResearchResponse,
    PracticeQuestion,
    PracticeSetResponse,
)

__all__ = [
    # User models
    "UserProfile",
    "LearningLevel",
    "LearningGoal",
    "ExplanationStyle",
    "RAGFallbackPreference",
    # Conversation models
    "Conversation",
    "ConversationSummary",
    "Message",
    # Document models
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "DocumentType",
    "DocumentSearchResult",
    # Progress models
    "ConceptMastery",
    "LearningProgress",
    "StudySession",
    "MemoryContext",
    # Practice models
    "PracticeSession",
    "PracticeQuestionResult",
    "PracticeSessionCreate",
    "PracticeStats",
    # Agent response models
    "ConceptExplanationResponse",
    "CodeGenerationResponse",
    "RouterDecision",
    "ResearchResponse",
    "PracticeQuestion",
    "PracticeSetResponse",
]