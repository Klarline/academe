"""
Chat service that wraps Academe core functionality for API use.
"""

import logging
from typing import Dict, Any, AsyncGenerator, Optional
import asyncio
import uuid

from core.graph.workflow import (
    build_workflow,
    process_with_langgraph,
    process_with_langgraph_streaming
)
from core.memory.context_manager import ContextManager
from core.models import UserProfile
from core.database.connection import get_database
from core.database.repositories import UserRepository
from bson import ObjectId

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for handling chat interactions.
    
    Wraps Academe LangGraph workflow and memory system
    for use by FastAPI endpoints.
    """

    def __init__(self):
        """Initialize chat service."""
        self.workflow = build_workflow()
        self.context_manager = ContextManager()
        self.user_repo = UserRepository()
        self.db = get_database()

    async def process_message(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        use_memory: bool = True
    ) -> Dict[str, Any]:
        """
        Process a chat message using Academe agents.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            message: User message
            use_memory: Whether to use memory context

        Returns:
            Response dictionary with content and metadata
        """
        # Track session start for dashboard stats
        from datetime import datetime
        session_start = datetime.now()
        
        try:
            # Get user profile
            user_profile = await self._get_user_profile(user_id)

            # Build memory context if requested
            memory_context = None
            if use_memory:
                memory_context = self.context_manager.build_agent_context(
                    user=user_profile,
                    query=message,
                    conversation_id=conversation_id
                )

            # Process with LangGraph workflow
            result = process_with_langgraph(
                question=message,
                user_id=user_id,
                conversation_id=conversation_id,
                user_profile=user_profile.dict() if user_profile else None
            )
            
            # Calculate session duration and log for dashboard
            session_end = datetime.now()
            duration_minutes = (session_end - session_start).total_seconds() / 60.0
            
            try:
                from core.database.progress_repository import ProgressRepository
                from core.database.connection import get_database
                
                progress_repo = ProgressRepository(get_database())
                progress_repo.log_study_session(
                    user_id=user_id,
                    session_start=session_start,
                    duration_minutes=duration_minutes,
                    activity_type="chat",
                    concepts_covered=[],
                    metadata={"conversation_id": conversation_id}
                )
            except Exception as e:
                logger.warning(f"Failed to log study session: {e}")

            return {
                "content": result.get("response", ""),
                "agent_used": result.get("agent"),
                "route": result.get("route"),
                "metadata": {
                    "agent": result.get("agent"),
                    "route": result.get("route"),
                    "has_documents": result.get("has_documents", False),
                    "used_memory": use_memory
                }
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def stream_message(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        use_memory: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a chat response with token-by-token streaming.
        
        Uses LangGraph's astream_events to stream tokens as the LLM generates them.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            message: User message
            use_memory: Whether to use memory context

        Yields:
            Stream events:
            - {"type": "thinking", "agent": "router"}
            - {"type": "token", "content": "word", "agent": "concept_explainer"}
            - {"type": "done", "response": "...", "metadata": {...}}
        """
        # Track session start for dashboard stats
        from datetime import datetime
        session_start = datetime.now()
        
        message_id = str(uuid.uuid4())
        
        # Stream from LangGraph workflow
        async for event in process_with_langgraph_streaming(
            question=message,
            user_id=user_id,
            conversation_id=conversation_id,
            user_profile=None  # Will be fetched inside
        ):
            # Add message ID to events
            event["id"] = message_id
            
            # Convert to API format
            if event["type"] == "token":
                yield {
                    "id": message_id,
                    "chunk": event["content"],
                    "is_final": False,
                    "agent": event.get("agent")
                }
            
            elif event["type"] == "done":
                yield {
                    "id": message_id,
                    "chunk": "",
                    "is_final": True,
                    "metadata": event.get("metadata")
                }
                
                # Log study session for dashboard AFTER streaming completes
                session_end = datetime.now()
                duration_minutes = (session_end - session_start).total_seconds() / 60.0
                
                try:
                    from core.database.progress_repository import ProgressRepository
                    from core.database.connection import get_database
                    
                    progress_repo = ProgressRepository(get_database())
                    progress_repo.log_study_session(
                        user_id=user_id,
                        session_start=session_start,
                        duration_minutes=duration_minutes,
                        activity_type="chat",
                        concepts_covered=[],
                        metadata={"conversation_id": conversation_id}
                    )
                    logger.info(f"Study session logged: {duration_minutes:.2f} minutes")
                except Exception as e:
                    logger.warning(f"Failed to log study session: {e}")

    async def _get_user_profile(self, user_id: str) -> UserProfile:
        """
        Get user profile from UserRepository.

        Args:
            user_id: User ID

        Returns:
            UserProfile instance
        """
        # Use UserRepository
        user = self.user_repo.get_user_by_id(user_id)

        if not user:
            # Return default profile for new users
            return UserProfile(
                id=user_id,
                username="user",
                email="user@example.com",
                learning_level="intermediate",
                learning_goal="understand_deeply",
                explanation_style="balanced"
            )

        return user
