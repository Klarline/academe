"""
Progress tracking and learning analytics endpoints.

Handles learning progress dashboard, concept mastery, study sessions,
and practice question generation.
"""

import logging
from typing import Any, List, Optional
from datetime import datetime
from bson import ObjectId

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.models import (
    ConceptMastery,
    LearningProgress,
    StudySession,
    UserProfile
)
from core.database.progress_repository import ProgressRepository
from core.database.repositories import UserRepository
from core.agents.practice_generator import PracticeGenerator
from api.v1.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize repositories and agents
user_repo = UserRepository()
progress_repo = ProgressRepository()
practice_generator = PracticeGenerator()


# Request/Response models
class ProgressDashboardResponse(BaseModel):
    """Complete progress dashboard."""
    total_concepts_studied: int
    concepts_mastered: int
    study_streak_days: int
    total_study_time_hours: float
    weak_areas: List[str]
    recommendations: List[dict]
    mastery_distribution: dict
    recent_progress: List[dict]


class LearningProgressResponse(BaseModel):
    """Individual concept progress."""
    concept: str
    mastery_level: ConceptMastery
    mastery_score: float
    questions_attempted: int
    questions_correct: int
    accuracy_rate: float
    last_studied: datetime
    total_study_time_minutes: int = 0


class StudySessionResponse(BaseModel):
    """Study session information."""
    id: str
    session_start: datetime
    session_end: Optional[datetime]
    duration_minutes: int
    concepts_studied: List[str]
    questions_asked: int
    practice_problems_solved: int
    average_accuracy: float


class PracticeRequest(BaseModel):
    """Practice question generation request."""
    topic: Optional[str] = None
    difficulty: Optional[str] = Field(default="intermediate", pattern="^(easy|intermediate|hard)$")
    num_questions: int = Field(default=5, ge=1, le=20)
    focus_weak_areas: bool = True


class PracticeQuestion(BaseModel):
    """Practice question."""
    id: str
    question: str
    question_type: str
    difficulty: str
    topic: str
    hint: Optional[str] = None
    options: Optional[List[str]] = None  # For MCQ


@router.get("/dashboard", response_model=ProgressDashboardResponse)
async def get_progress_dashboard(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get comprehensive learning progress dashboard.
    
    Returns overview of all learning metrics including concepts studied,
    mastery levels, weak areas, and personalized recommendations.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        Complete progress dashboard
    """
    try:
        # Get progress summary from repository
        summary = progress_repo.get_user_progress_summary(current_user_id)
        
        # Get weak areas
        weak_areas = progress_repo.get_weak_areas(current_user_id)
        
        # Get recommendations
        recommendations = progress_repo.get_study_recommendations(current_user_id)
        
        # Get mastery distribution
        mastery_dist = summary.get("mastery_distribution", {
            "novice": 0,
            "learning": 0,
            "competent": 0,
            "proficient": 0,
            "expert": 0
        })
        
        # Get recent progress
        recent = progress_repo.get_recent_concepts(current_user_id, limit=5)
        recent_progress = [
            {
                "concept": prog.concept,
                "mastery_level": prog.mastery_level,
                "accuracy_rate": prog.accuracy_rate,
                "last_studied": prog.last_studied.isoformat()
            }
            for prog in recent
        ]
        
        return ProgressDashboardResponse(
            total_concepts_studied=summary.get("total_concepts", 0),
            concepts_mastered=summary.get("concepts_mastered", 0),
            study_streak_days=summary.get("streak_days", 0),
            total_study_time_hours=summary.get("total_hours", 0.0),
            weak_areas=weak_areas,
            recommendations=recommendations,
            mastery_distribution=mastery_dist,
            recent_progress=recent_progress
        )
        
    except Exception as e:
        logger.error(f"Error fetching progress dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch progress data"
        )


@router.get("/concepts", response_model=List[LearningProgressResponse])
async def get_concept_progress(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get detailed progress for all concepts.
    
    Returns learning metrics for every concept the user has studied.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        List of concept progress data
    """
    try:
        progress_list = progress_repo.get_user_progress(current_user_id)
        
        return [
            LearningProgressResponse(
                concept=prog.concept,
                mastery_level=prog.mastery_level,
                mastery_score=prog.mastery_score,
                questions_attempted=prog.questions_attempted,
                questions_correct=prog.questions_correct,
                accuracy_rate=prog.accuracy_rate,
                last_studied=prog.last_studied,
                total_study_time_minutes=prog.total_study_time_minutes
            )
            for prog in progress_list
        ]
        
    except Exception as e:
        logger.error(f"Error fetching concept progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch concept progress"
        )


@router.get("/sessions", response_model=List[StudySessionResponse])
async def get_study_sessions(
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 20
) -> Any:
    """
    Get recent study sessions.
    
    Returns chronological list of study sessions with metrics.
    
    Args:
        current_user_id: ID of authenticated user
        limit: Maximum number of sessions to return
        
    Returns:
        List of study sessions
    """
    try:
        sessions = progress_repo.get_study_sessions(current_user_id, days_back=30)
        
        # Apply limit
        sessions = sessions[:limit]
        
        return [
            StudySessionResponse(
                id=sess.id,
                session_start=sess.session_start,
                session_end=sess.session_end,
                duration_minutes=sess.duration_minutes,
                concepts_studied=sess.concepts_studied,
                questions_asked=sess.questions_asked,
                practice_problems_solved=sess.practice_problems_solved,
                average_accuracy=sess.average_accuracy
            )
            for sess in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error fetching study sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch study sessions"
        )


@router.post("/practice/generate", response_model=List[PracticeQuestion])
async def generate_practice_questions(
    request: PracticeRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Generate practice questions.
    
    Generates questions tailored to user's learning needs, optionally
    focusing on weak areas for targeted practice.
    
    Args:
        request: Practice generation parameters
        current_user_id: ID of authenticated user
        
    Returns:
        List of practice questions
    """
    try:
        # Get user profile for personalized question generation
        user = user_repo.get_user_by_id(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get weak areas if focusing on them
        weak_areas = []
        if request.focus_weak_areas:
            weak_areas = progress_repo.get_weak_areas(current_user_id)
        
        # Determine topic
        topic = request.topic
        if not topic and weak_areas:
            # Focus on weakest area
            topic = weak_areas[0]
        elif not topic:
            topic = "general"
        
        # Generate real questions using PracticeGenerator agent
        result = practice_generator.generate_practice_set(
            topic=topic,
            user=user,
            num_questions=request.num_questions,
            question_types=["mcq", "short", "explain"],
            memory_context={
                "weak_areas": weak_areas,
                "focus_weak_areas": request.focus_weak_areas
            }
        )
        
        # Convert to API response format
        questions = []
        for q in result.get("questions", []):
            questions.append(PracticeQuestion(
                id=q.get("id", str(ObjectId())),
                question=q.get("question", ""),
                question_type=q.get("type", "conceptual"),
                difficulty=q.get("difficulty", request.difficulty),
                topic=topic,
                hint=q.get("hint"),
                options=q.get("options")  # For MCQ
            ))
        
        logger.info(f"Generated {len(questions)} real practice questions for user {current_user_id}")
        
        return questions
        
    except Exception as e:
        logger.error(f"Error generating practice questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate practice questions"
        )


@router.get("/weak-areas")
async def get_weak_areas(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get user's weak areas.
    
    Identifies concepts where the user has low mastery scores.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        List of weak areas with recommendations
    """
    try:
        weak_areas = progress_repo.get_weak_areas(current_user_id)
        recommendations = progress_repo.get_study_recommendations(current_user_id)
        
        return {
            "weak_areas": weak_areas,
            "recommendations": recommendations,
            "count": len(weak_areas)
        }
        
    except Exception as e:
        logger.error(f"Error identifying weak areas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to identify weak areas"
        )
