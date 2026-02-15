"""
User management endpoints.

Handles user profile operations, settings, and statistics.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.models import UserProfile, LearningLevel, LearningGoal, ExplanationStyle
from core.database.repositories import UserRepository, ConversationRepository
from core.database.progress_repository import ProgressRepository
from core.documents import DocumentManager
from api.v1.deps import get_current_user_id, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize repositories
user_repo = UserRepository()
conv_repo = ConversationRepository()
progress_repo = ProgressRepository()
doc_manager = DocumentManager()


# Request/Response models
class UserUpdateRequest(BaseModel):
    """User profile update request."""
    learning_level: Optional[LearningLevel] = None
    learning_goal: Optional[LearningGoal] = None
    explanation_style: Optional[ExplanationStyle] = None
    rag_fallback_preference: Optional[str] = None
    preferred_code_language: Optional[str] = None
    include_math_formulas: Optional[bool] = None
    include_visualizations: Optional[bool] = None


class UserStatsResponse(BaseModel):
    """User statistics response."""
    total_conversations: int
    total_messages: int
    documents_uploaded: int
    concepts_studied: int
    study_streak_days: int
    total_study_time_hours: float


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: UserProfile = Depends(get_current_user)
) -> Any:
    """
    Get current user profile.
    
    Returns the complete profile of the authenticated user including
    learning preferences and settings.
    
    Args:
        current_user: Authenticated user profile
        
    Returns:
        User profile
    """
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_current_user(
    data: UserUpdateRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Update current user profile.
    
    Allows users to update their learning preferences including
    learning level, goals, and explanation style.
    
    Args:
        data: Profile update data
        current_user_id: ID of authenticated user
        
    Returns:
        Updated user profile
        
    Raises:
        HTTPException: If update fails
    """
    # Build update dictionary
    update_data = {}
    if data.learning_level is not None:
        update_data["learning_level"] = data.learning_level
    if data.learning_goal is not None:
        update_data["learning_goal"] = data.learning_goal
    if data.explanation_style is not None:
        update_data["explanation_style"] = data.explanation_style
    if data.rag_fallback_preference is not None:
        update_data["rag_fallback_preference"] = data.rag_fallback_preference
    if data.preferred_code_language is not None:
        update_data["preferred_code_language"] = data.preferred_code_language
    if data.include_math_formulas is not None:
        update_data["include_math_formulas"] = data.include_math_formulas
    if data.include_visualizations is not None:
        update_data["include_visualizations"] = data.include_visualizations
    
    if not update_data:
        # No updates provided
        user = user_repo.get_user_by_id(current_user_id)
        return user
    
    # Update user
    success = user_repo.update_user(current_user_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )
    
    # Return updated user
    user = user_repo.get_user_by_id(current_user_id)
    
    logger.info(f"User profile updated: {current_user_id}")
    
    return user


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get user statistics.
    
    Returns comprehensive statistics about the user's activity including
    conversations, messages, documents, study time, and progress.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        User statistics
    """
    # Get conversation count
    conversations = conv_repo.get_user_conversations(current_user_id)
    total_conversations = len(conversations)
    
    # Count total messages across all conversations
    total_messages = 0
    for conv in conversations:
        messages = conv_repo.get_conversation_messages(conv.id)
        total_messages += len(messages)
    
    # Get document count using DocumentManager
    user_documents = doc_manager.get_user_documents(current_user_id)
    documents_uploaded = len(user_documents)
    
    # Get progress stats
    try:
        progress_data = progress_repo.get_user_progress_summary(current_user_id)
        concepts_studied = progress_data.get("total_concepts", 0)
        study_streak_days = progress_data.get("streak_days", 0)
        total_study_time_hours = progress_data.get("total_hours", 0.0)
    except:
        concepts_studied = 0
        study_streak_days = 0
        total_study_time_hours = 0.0
    
    return UserStatsResponse(
        total_conversations=total_conversations,
        total_messages=total_messages,
        documents_uploaded=documents_uploaded,
        concepts_studied=concepts_studied,
        study_streak_days=study_streak_days,
        total_study_time_hours=total_study_time_hours
    )


@router.post("/me/complete-onboarding")
async def complete_onboarding(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Mark onboarding as complete.
    
    Updates the user's onboarding status to indicate they have
    completed the initial setup process.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If update fails
    """
    success = user_repo.update_user(
        current_user_id,
        {"has_completed_onboarding": True}
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update onboarding status"
        )
    
    logger.info(f"Onboarding completed for user: {current_user_id}")
    
    return {"message": "Onboarding completed successfully"}
