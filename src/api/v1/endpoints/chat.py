"""
Chat and conversation endpoints.

Handles chat messaging, conversation management, and streaming responses.
"""

import logging
import json
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.models import Conversation, Message
from core.database.repositories import ConversationRepository
from core.utils.datetime_utils import get_current_time
from api.services import ChatService
from api.v1.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
chat_service = ChatService()
conv_repo = ConversationRepository()


# Request/Response models
class ChatRequest(BaseModel):
    """Chat message request."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None
    use_memory: bool = True


class ChatResponse(BaseModel):
    """Chat message response."""
    id: str
    content: str
    role: str
    agent_used: Optional[str] = None
    route: Optional[str] = None
    timestamp: datetime
    metadata: Optional[dict] = None


class ConversationResponse(BaseModel):
    """Conversation metadata response."""
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_archived: bool = False


class ConversationListResponse(BaseModel):
    """List of conversations with pagination."""
    conversations: List[ConversationResponse]
    total: int
    page: int
    limit: int


class ConversationCreateRequest(BaseModel):
    """Create new conversation request."""
    title: str = Field(..., min_length=1, max_length=200)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Send a chat message and receive response.
    
    Processes the message through Academe's multi-agent system and
    returns the response with metadata about which agent handled it.
    
    Args:
        request: Chat request with message and optional conversation ID
        current_user_id: ID of authenticated user
        
    Returns:
        Chat response with agent metadata
    """
    try:
        # Get or create conversation
        if request.conversation_id:
            conversation = conv_repo.get_conversation(request.conversation_id)
            if not conversation or conversation.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            conversation_id = request.conversation_id
        else:
            # Create new conversation with title from message
            title = request.message[:50] + "..." if len(request.message) > 50 else request.message
            conversation_id = conv_repo.create_conversation(
                user_id=current_user_id,
                title=title
            )
        
        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            user_id=current_user_id,
            role="user",
            content=request.message
        )
        conv_repo.add_message(user_message)
        
        # Process with chat service (uses your agents)
        response_data = await chat_service.process_message(
            user_id=current_user_id,
            conversation_id=conversation_id,
            message=request.message,
            use_memory=request.use_memory
        )
        
        # Save assistant message
        assistant_message = Message(
            conversation_id=conversation_id,
            user_id=current_user_id,
            role="assistant",
            content=response_data["content"]
        )
        message_id = conv_repo.add_message(assistant_message)
        
        # Update conversation timestamp
        conv_repo.update_conversation(conversation_id, {
            "updated_at": get_current_time()
        })
        
        logger.info(f"Message processed for user {current_user_id}, agent: {response_data.get('agent_used')}")
        
        return ChatResponse(
            id=message_id,
            content=response_data["content"],
            role="assistant",
            agent_used=response_data.get("agent_used"),
            route=response_data.get("route"),
            timestamp=get_current_time(),
            metadata=response_data.get("metadata")
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/message/stream")
async def stream_message(
    request: ChatRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> StreamingResponse:
    """
    Send a chat message and stream the response.
    
    Streams the response token by token using Server-Sent Events (SSE)
    for a real-time chat experience.
    
    Args:
        request: Chat request with message
        current_user_id: ID of authenticated user
        
    Returns:
        Streaming response with SSE events
    """
    async def generate():
        try:
            # Get or create conversation
            conversation_id = request.conversation_id or "temp"
            
            # Stream response from chat service
            async for chunk in chat_service.stream_message(
                user_id=current_user_id,
                conversation_id=conversation_id,
                message=request.message,
                use_memory=request.use_memory
            ):
                # Format as Server-Sent Event
                event_data = json.dumps({
                    "id": chunk.get("id"),
                    "chunk": chunk.get("chunk"),
                    "is_final": chunk.get("is_final", False),
                    "metadata": chunk.get("metadata")
                })
                yield f"data: {event_data}\n\n"
            
            # Send completion event
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    current_user_id: str = Depends(get_current_user_id),
    page: int = 1,
    limit: int = 20,
    include_archived: bool = False
) -> Any:
    """
    Get user's conversations with pagination.
    
    Returns a paginated list of conversations sorted by most recent activity.
    
    Args:
        current_user_id: ID of authenticated user
        page: Page number (1-indexed)
        limit: Items per page
        include_archived: Whether to include archived conversations
        
    Returns:
        Paginated conversation list
    """
    # Get all user conversations
    all_conversations = conv_repo.get_user_conversations(current_user_id)
    
    # Filter archived if needed
    if not include_archived:
        all_conversations = [c for c in all_conversations if not c.is_archived]
    
    # Sort by updated_at descending
    all_conversations.sort(key=lambda c: c.updated_at, reverse=True)
    
    # Paginate
    total = len(all_conversations)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_conversations = all_conversations[start_idx:end_idx]
    
    # Convert to response model
    conversation_responses = [
        ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv_repo.get_conversation_messages(conv.id)),
            is_archived=conv.is_archived
        )
        for conv in page_conversations
    ]
    
    return ConversationListResponse(
        conversations=conversation_responses,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 100,
    offset: int = 0
) -> Any:
    """
    Get messages in a conversation.
    
    Returns messages in chronological order with pagination support.
    
    Args:
        conversation_id: Conversation ID
        current_user_id: ID of authenticated user
        limit: Maximum messages to return
        offset: Number of messages to skip
        
    Returns:
        List of messages
        
    Raises:
        HTTPException: If conversation not found or doesn't belong to user
    """
    # Verify conversation belongs to user
    conversation = conv_repo.get_conversation(conversation_id)
    
    if not conversation or conversation.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages with pagination
    all_messages = conv_repo.get_conversation_messages(conversation_id)
    total = len(all_messages)
    
    # Apply pagination
    messages = all_messages[offset:offset + limit]
    
    return {
        "messages": messages,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreateRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Create a new conversation.
    
    Args:
        data: Conversation creation data
        current_user_id: ID of authenticated user
        
    Returns:
        Created conversation
    """
    conversation_id = conv_repo.create_conversation(
        user_id=current_user_id,
        title=data.title
    )
    
    # Get the created conversation to return
    conversation = conv_repo.get_conversation(conversation_id)
    
    logger.info(f"Conversation created: {conversation_id} by user {current_user_id}")
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
        is_archived=False
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Delete a conversation.
    
    Permanently deletes the conversation and all associated messages.
    
    Args:
        conversation_id: Conversation ID to delete
        current_user_id: ID of authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If conversation not found or doesn't belong to user
    """
    # Verify ownership
    conversation = conv_repo.get_conversation(conversation_id)
    
    if not conversation or conversation.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Delete conversation
    success = conv_repo.delete_conversation(conversation_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )
    
    logger.info(f"Conversation deleted: {conversation_id}")
    
    return {"message": "Conversation deleted successfully"}
