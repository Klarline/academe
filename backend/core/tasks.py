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

from core.celery_config import celery_app
from core.utils.datetime_utils import get_current_time

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
        from core.memory.context_manager import ContextManager
        
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
                "timestamp": get_current_time().isoformat()
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
        from core.database.progress_repository import ProgressRepository
        
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
        from core.documents import DocumentManager
        
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
            "timestamp": get_current_time().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error processing document: {exc}")
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(
    name='academe.index_document',
    bind=True,
    max_retries=2,
    soft_time_limit=300
)
def index_document_task(
    self,
    document_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Index document chunks in vector database (background task).
    
    Generates embeddings and stores in Pinecone.
    Can take 5-10 seconds for large documents.
    
    Args:
        self: Task instance
        document_id: Document ID
        user_id: User ID
    
    Returns:
        Indexing result
    """
    try:
        # Initialize database connection for this worker
        from core.database import init_database
        init_database()
        
        from core.documents import DocumentRepository, ChunkRepository
        from core.vectors import SemanticSearchService
        
        logger.info(f"Indexing document {document_id} for user {user_id}")
        
        # Get document and chunks
        doc_repo = DocumentRepository()
        chunk_repo = ChunkRepository()
        
        document = doc_repo.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        chunks = chunk_repo.get_document_chunks(document_id)
        if not chunks:
            raise ValueError(f"No chunks found for document {document_id}")
        
        # Index in vector database
        search_service = SemanticSearchService()
        success, message = search_service.index_document(document, chunks)
        
        if success:
            logger.info(f"Document {document_id} indexed successfully: {len(chunks)} chunks")
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_indexed": len(chunks),
                "message": message
            }
        else:
            raise Exception(f"Indexing failed: {message}")
        
    except Exception as exc:
        logger.error(f"Error indexing document: {exc}")
        
        # Update document status to failed
        try:
            from core.database import init_database
            from core.documents import DocumentRepository
            init_database()
            doc_repo = DocumentRepository()
            doc_repo.update_document(document_id, {
                "processing_error": f"Indexing failed: {str(exc)}"
            })
        except:
            pass
        
        raise self.retry(exc=exc, countdown=10)


# Export tasks
__all__ = [
    'update_memory_task',
    'update_progress_task',
    'process_document_task',
    'index_document_task'
]
