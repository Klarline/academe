"""
Practice endpoints for generating quizzes and exercises.
"""

import logging
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.agents.practice_generator import PracticeGenerator
from core.database import UserRepository
from api.v1.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

practice_generator = PracticeGenerator()
user_repo = UserRepository()


class PracticeRequest(BaseModel):
    """Generate practice set request."""
    topic: str = Field(..., min_length=1)
    num_questions: int = Field(default=5, ge=1, le=20)
    question_types: Optional[List[str]] = Field(default=None)


class QuizRequest(BaseModel):
    """Generate quiz from document request."""
    document_id: str
    quiz_length: int = Field(default=10, ge=1, le=30)


@router.post("/generate")
async def generate_practice(
    request: PracticeRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Generate practice questions on a topic."""
    try:
        user = user_repo.get_user_by_id(current_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = practice_generator.generate_practice_set(
            topic=request.topic,
            user=user,
            num_questions=request.num_questions,
            question_types=request.question_types
        )
        
        return result
    except Exception as e:
        logger.error(f"Error generating practice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quiz")
async def generate_quiz(
    request: QuizRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Generate quiz from document."""
    try:
        user = user_repo.get_user_by_id(current_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = practice_generator.generate_quiz(
            document_id=request.document_id,
            user=user,
            quiz_length=request.quiz_length
        )
        
        return result
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW ENDPOINTS FOR SESSION HISTORY
# ============================================================================

from datetime import datetime
from core.database.practice_repository import PracticeRepository
from core.database.progress_repository import ProgressRepository
from core.database.connection import get_database

# Don't initialize at module load - lazy load instead
def get_practice_repo():
    """Get practice repository instance."""
    return PracticeRepository(get_database())

def get_progress_repo():
    """Get progress repository instance."""
    return ProgressRepository(get_database())


class PracticeSessionSave(BaseModel):
    """Save practice session request."""
    topic: str
    difficulty: str = "intermediate"
    questions: List[dict]
    score: int
    total_questions: int
    percentage: float
    started_at: datetime
    completed_at: datetime
    duration_minutes: int
    question_types: List[str]


@router.post("/sessions")
async def save_practice_session(
    session: PracticeSessionSave,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Save completed practice session."""
    try:
        practice_repo = get_practice_repo()
        saved_session = practice_repo.save_session(
            user_id=current_user_id,
            session_data=session.dict()
        )
        
        # ALSO log study session for dashboard
        try:
            progress_repo = get_progress_repo()
            progress_repo.log_study_session(
                user_id=current_user_id,
                session_start=session.started_at,
                duration_minutes=session.duration_minutes,
                activity_type="practice",
                concepts_covered=[session.topic],
                metadata={"practice_session_id": saved_session.get("id")}
            )
        except Exception as e:
            logger.warning(f"Failed to log study session: {e}")
        
        return saved_session
    except Exception as e:
        logger.error(f"Error saving practice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_practice_sessions(
    skip: int = 0,
    limit: int = 20,
    topic: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get user's practice session history."""
    try:
        practice_repo = get_practice_repo()
        sessions = practice_repo.get_user_sessions(user_id=current_user_id, skip=skip, limit=limit, topic=topic)
        return sessions
    except Exception as e:
        logger.error(f"Error getting practice sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_practice_session(session_id: str, current_user_id: str = Depends(get_current_user_id)) -> Any:
    """Get specific practice session details."""
    try:
        practice_repo = get_practice_repo()
        session = practice_repo.get_session_by_id(session_id, current_user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting practice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_practice_session(session_id: str, current_user_id: str = Depends(get_current_user_id)) -> Any:
    """Delete a practice session."""
    try:
        practice_repo = get_practice_repo()
        success = practice_repo.delete_session(session_id, current_user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting practice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_practice_stats(current_user_id: str = Depends(get_current_user_id)) -> Any:
    """Get practice statistics."""
    try:
        practice_repo = get_practice_repo()
        stats = practice_repo.get_practice_stats(current_user_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting practice stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
