"""
WebSocket endpoints for real-time bidirectional communication.

Provides WebSocket support for features that require two-way communication:
- Real-time chat with ability to cancel
- Typing indicators
- Push notifications
- Real-time progress updates
"""

import logging
import json
import asyncio
from typing import Dict
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from bson import ObjectId

from core.auth.service import AuthService
from core.models import Message
from core.database.repositories import ConversationRepository
from core.utils.datetime_utils import get_current_time
from api.services import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
auth_service = AuthService()
chat_service = ChatService()
conv_repo = ConversationRepository()


class ConnectionManager:
    """
    Manages WebSocket connections for multiple users.
    
    Tracks active connections and provides methods for sending messages
    and broadcasting to all connected clients.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            user_id: User ID
            websocket: WebSocket instance
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            user_id: User ID to disconnect
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_message(self, user_id: str, message: dict):
        """
        Send a message to a specific user.
        
        Args:
            user_id: Target user ID
            message: Message dictionary to send
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, message: dict, exclude: str = None):
        """
        Broadcast a message to all connected users.
        
        Args:
            message: Message to broadcast
            exclude: Optional user ID to exclude from broadcast
        """
        disconnected = []
        for user_id, websocket in self.active_connections.items():
            if user_id == exclude:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected:
            self.disconnect(user_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    
    Provides bidirectional communication for:
    - Streaming AI responses
    - Canceling generation mid-stream
    - Real-time typing indicators
    - Push notifications
    
    Protocol:
    1. Client connects
    2. Client sends auth message: {"type": "auth", "token": "jwt_token"}
    3. Server validates token and accepts connection
    4. Client can send: {"type": "message", "content": "...", "conversation_id": "..."}
    5. Server streams: {"type": "token", "content": "word"}
    6. Client can send: {"type": "cancel"} to stop generation
    7. Server sends: {"type": "done"} when complete
    """
    user_id = None
    current_stream_task = None

    try:
        # Accept connection first
        await websocket.accept()

        # Wait for authentication message
        auth_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10.0
        )

        if auth_data.get("type") != "auth":
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required as first message"
            })
            await websocket.close()
            return

        # Verify JWT token
        token = auth_data.get("token")
        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "Token required"
            })
            await websocket.close()
            return

        # Validate token using AuthService
        payload = auth_service.verify_jwt_token(token)
        if not payload:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid or expired token"
            })
            await websocket.close()
            return

        user_id = payload.get("sub")
        if not user_id:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid token payload"
            })
            await websocket.close()
            return

        # Register connection
        await manager.connect(user_id, websocket)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "Connected to Academe chat"
        })

        # Message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")

            # Handle different message types
            if message_type == "message":
                # Process chat message with streaming
                content = data.get("content", "")
                conversation_id = data.get("conversation_id")
                client_message_id = data.get("message_id", str(ObjectId()))

                if not content:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue

                # Create or get conversation
                if not conversation_id:
                    conversation_id = "temp_" + str(ObjectId())

                # Send streaming start event
                await websocket.send_json({
                    "type": "start_streaming",
                    "message_id": client_message_id
                })

                # Stream response using real LangGraph streaming
                try:
                    async def stream_to_websocket():
                        async for event in chat_service.stream_message(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=content,
                            use_memory=True
                        ):
                            await websocket.send_json({
                                "type": "stream_chunk",
                                "message_id": client_message_id,
                                "chunk": event.get("chunk", ""),
                                "is_final": event.get("is_final", False),
                                "metadata": event.get("metadata")
                            })
                        
                        # Send completion
                        await websocket.send_json({
                            "type": "end_streaming",
                            "message_id": client_message_id
                        })

                    # Create task for streaming (so it can be cancelled)
                    current_stream_task = asyncio.create_task(stream_to_websocket())
                    await current_stream_task
                    current_stream_task = None

                except asyncio.CancelledError:
                    await websocket.send_json({
                        "type": "cancelled",
                        "message_id": client_message_id,
                        "message": "Generation cancelled by user"
                    })
                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Streaming error: {str(e)}"
                    })

            elif message_type == "cancel":
                # Cancel current streaming
                if current_stream_task and not current_stream_task.done():
                    current_stream_task.cancel()
                    await websocket.send_json({
                        "type": "cancelled",
                        "message": "Generation cancelled"
                    })
                else:
                    await websocket.send_json({
                        "type": "info",
                        "message": "Nothing to cancel"
                    })

            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": get_current_time().isoformat()
                })

            elif message_type == "typing":
                # Typing indicator (future feature)
                await websocket.send_json({
                    "type": "typing_acknowledged",
                    "message": "Typing indicator received"
                })

            else:
                # Unknown message type
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected (WebSocketDisconnect)")
        if user_id:
            manager.disconnect(user_id)
    
    except asyncio.TimeoutError:
        logger.warning("WebSocket authentication timeout")
        if user_id:
            manager.disconnect(user_id)
        try:
            await websocket.close()
        except:
            pass
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if user_id:
            manager.disconnect(user_id)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error"
            })
            await websocket.close()
        except:
            pass


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.
    
    Allows server to push notifications to clients:
    - Progress updates
    - New documents processed
    - Study reminders
    - Achievement unlocked
    
    Protocol:
    1. Client connects
    2. Client sends: {"type": "auth", "token": "jwt_token"}
    3. Server validates and keeps connection open
    4. Server sends notifications as they occur
    5. Client receives real-time updates
    """
    user_id = None

    try:
        # Accept connection
        await websocket.accept()

        # Wait for authentication
        auth_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10.0
        )

        if auth_data.get("type") != "auth":
            await websocket.close()
            return

        # Verify token
        token = auth_data.get("token")
        payload = auth_service.verify_jwt_token(token)
        
        if not payload:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid token"
            })
            await websocket.close()
            return

        user_id = payload.get("sub")

        # Connection established
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notifications"
        })

        # Keep connection alive with heartbeat
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": get_current_time().isoformat()
            })

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from notifications")
    
    except asyncio.TimeoutError:
        logger.warning("Notification WebSocket authentication timeout")
        try:
            await websocket.close()
        except:
            pass
    
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
