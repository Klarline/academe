"""
Helper utilities for integrating Celery tasks into the application.

Provides convenient wrappers for calling background tasks.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def queue_memory_update(
    user_id: str,
    conversation_id: str,
    interaction: Dict[str, Any],
    async_mode: bool = True
) -> Optional[str]:
    """
    Queue a memory update task.
    
    Args:
        user_id: User ID
        conversation_id: Conversation ID
        interaction: Interaction data
        async_mode: Whether to run async (True) or sync (False)
    
    Returns:
        Task ID if async, None if sync
    """
    try:
        if async_mode:
            # Import here to avoid circular dependency
            from academe.tasks import update_memory_task
            
            # Queue task asynchronously
            result = update_memory_task.delay(
                user_id=user_id,
                conversation_id=conversation_id,
                interaction=interaction
            )
            
            logger.info(f"Queued memory update task: {result.id}")
            return result.id
        else:
            # Run synchronously (for testing/development)
            from academe.memory.context_manager import ContextManager
            
            context_manager = ContextManager()
            context_manager.update_context(user_id, conversation_id, interaction)
            logger.info("Memory updated synchronously")
            return None
            
    except Exception as e:
        logger.error(f"Failed to queue memory update: {e}")
        # Fallback to sync if Celery unavailable
        try:
            from academe.memory.context_manager import ContextManager
            context_manager = ContextManager()
            context_manager.update_context(user_id, conversation_id, interaction)
            logger.info("Memory updated synchronously (fallback)")
        except Exception as e2:
            logger.error(f"Sync fallback also failed: {e2}")
        return None


def queue_progress_update(
    user_id: str,
    concept: str,
    correct: bool,
    time_spent: float = 0.0,
    async_mode: bool = True
) -> Optional[str]:
    """
    Queue a progress update task.
    
    Args:
        user_id: User ID
        concept: Concept name
        correct: Whether answer was correct
        time_spent: Time spent (minutes)
        async_mode: Whether to run async
    
    Returns:
        Task ID if async, None if sync
    """
    try:
        if async_mode:
            from academe.tasks import update_progress_task
            
            result = update_progress_task.delay(
                user_id=user_id,
                concept=concept,
                correct=correct,
                time_spent=time_spent
            )
            
            logger.info(f"Queued progress update task: {result.id}")
            return result.id
        else:
            from academe.database.progress_repository import ProgressRepository
            
            progress_repo = ProgressRepository()
            progress_repo.track_concept_interaction(
                user_id=user_id,
                concept=concept,
                interaction_type="practice",
                details={"correct": correct, "time_spent": time_spent}
            )
            logger.info("Progress updated synchronously")
            return None
            
    except Exception as e:
        logger.error(f"Failed to queue progress update: {e}")
        return None


def extract_concepts_from_query(query: str) -> list:
    """
    Simple keyword extraction for concepts.
    
    Args:
        query: User query
    
    Returns:
        List of potential concepts
    """
    # Simple keyword-based extraction
    # In production, use NLP or LLM for better extraction
    
    ml_keywords = [
        "pca", "eigenvalue", "eigenvector", "gradient", "descent",
        "neural", "network", "backprop", "loss", "function",
        "matrix", "vector", "tensor", "derivative", "optimization",
        "regression", "classification", "clustering", "supervised",
        "unsupervised", "learning", "algorithm", "model", "training"
    ]
    
    query_lower = query.lower()
    concepts = []
    
    for keyword in ml_keywords:
        if keyword in query_lower:
            concepts.append(keyword)
    
    return concepts[:5]  # Limit to 5 concepts


# Check if Celery is available
def is_celery_available() -> bool:
    """Check if Celery worker is running."""
    try:
        from academe.celery_config import celery_app
        
        # Try to ping a worker
        inspect = celery_app.control.inspect(timeout=1.0)
        stats = inspect.stats()
        
        return stats is not None and len(stats) > 0
    except Exception:
        return False


__all__ = [
    'queue_memory_update',
    'queue_progress_update',
    'extract_concepts_from_query',
    'is_celery_available'
]
