"""
Celery background tasks for Academe.

All async operations run through these tasks:
- Memory updates
- Progress tracking
- Document processing
"""

import logging
from typing import Dict, Any
from datetime import datetime

from academe.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name='academe.update_memory',
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def update_memory_task(
    self,
    user_id: str,
    conversation_id: str,
    interaction: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update user's memory context in background.
    
    Args:
        self: Task instance (for retry)
        user_id: User ID
        conversation_id: Conversation ID
        interaction: Interaction data (query, concepts, etc.)
    
    Returns:
        Result dictionary with status
    """
    try:
        from academe.memory.context_manager import ContextManager
        
        logger.info(f"Updating memory for user {user_id}")
        
        # Initialize context manager
        context_manager = ContextManager()
        
        # Update context
        success = context_manager.update_context(
            user_id=user_id,
            conversation_id=conversation_id,
            interaction=interaction
        )
        
        if success:
            logger.info(f"Memory updated successfully for user {user_id}")
            return {
                "status": "success",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            logger.error(f"Memory update failed for user {user_id}")
            return {
                "status": "failed",
                "user_id": user_id,
                "error": "Update returned False"
            }
            
    except Exception as exc:
        logger.error(f"Error updating memory: {exc}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(
    name='academe.update_progress',
    bind=True,
    max_retries=3
)
def update_progress_task(
    self,
    user_id: str,
    concept: str,
    correct: bool,
    time_spent: float = 0.0
) -> Dict[str, Any]:
    """
    Update learning progress after practice.
    
    Args:
        self: Task instance
        user_id: User ID
        concept: Concept name
        correct: Whether answer was correct
        time_spent: Time spent on question (minutes)
    
    Returns:
        Result dictionary
    """
    try:
        from academe.database.progress_repository import ProgressRepository
        
        logger.info(f"Updating progress for user {user_id}, concept {concept}")
        
        progress_repo = ProgressRepository()
        
        # Get or create progress
        progress = progress_repo.get_concept_progress(user_id, concept)
        
        if progress:
            # Update existing progress
            progress.update_from_practice(correct=correct, time_spent=time_spent)
            
            # Save to database
            progress_repo.update_concept_progress(
                user_id=user_id,
                concept=concept,
                updates={
                    "questions_attempted": progress.questions_attempted,
                    "questions_correct": progress.questions_correct,
                    "accuracy_rate": progress.accuracy_rate,
                    "mastery_level": progress.mastery_level.value,
                    "mastery_score": progress.mastery_score,
                    "total_study_time_minutes": progress.total_study_time_minutes,
                    "last_studied": progress.last_studied
                }
            )
        else:
            # Create new progress entry
            progress_repo.track_concept_interaction(
                user_id=user_id,
                concept=concept,
                interaction_type="practice",
                details={"correct": correct, "time_spent": time_spent}
            )
        
        return {
            "status": "success",
            "user_id": user_id,
            "concept": concept,
            "correct": correct
        }
        
    except Exception as exc:
        logger.error(f"Error updating progress: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(
    name='academe.process_document',
    bind=True,
    max_retries=2,
    soft_time_limit=180
)
def process_document_task(
    self,
    user_id: str,
    document_id: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Process uploaded document in background.
    
    Heavy task: PDF parsing, chunking, embedding generation.
    
    Args:
        self: Task instance
        user_id: User ID
        document_id: Document ID
        file_path: Path to uploaded file
    
    Returns:
        Processing result
    """
    try:
        from academe.documents import DocumentManager
        
        logger.info(f"Processing document {document_id} for user {user_id}")
        
        doc_manager = DocumentManager()
        
        # Process document (parse, chunk, embed)
        result = doc_manager.process_document(
            user_id=user_id,
            document_id=document_id,
            file_path=file_path
        )
        
        logger.info(f"Document {document_id} processed successfully")
        
        return {
            "status": "success",
            "document_id": document_id,
            "chunks": result.get("chunk_count", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error processing document: {exc}")
        raise self.retry(exc=exc, countdown=10)


# Export tasks
__all__ = [
    'update_memory_task',
    'update_progress_task',
    'process_document_task'
]
