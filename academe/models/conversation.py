"""Conversation and message models for Academe."""

from bson import ObjectId
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from academe.utils import get_current_time


class Message(BaseModel):
    """Individual message in a conversation."""

    # MongoDB ID field
    id: Optional[str] = Field(default=None, alias="_id")

    # Relationship fields
    conversation_id: str
    user_id: str

    # Message content
    role: Literal["user", "assistant", "system"]
    content: str

    # Metadata
    agent_used: Optional[str] = None  # Which agent handled this query
    route: Optional[str] = None  # Route taken (concept/code)
    processing_time_ms: Optional[int] = None  # Response time
    token_count: Optional[int] = None  # Approximate token usage

    # Timestamps
    timestamp: datetime = Field(default_factory=get_current_time)

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not empty."""
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v

    def to_mongo_dict(self) -> dict:
        """Convert to MongoDB-compatible dictionary."""
        data = self.model_dump(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = self.id
        return data

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "Message":
        """Create Message from MongoDB document."""
        if not data:
            return None
        
        # Convert ObjectId to string
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        
        # Convert timestamp if needed
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(**data)

    def format_for_display(self, show_metadata: bool = False) -> str:
        """Format message for CLI display."""
        role_symbol = "User" if self.role == "user" else "Assistant"
        formatted = f"{role_symbol}: {self.content}"

        if show_metadata and self.role == "assistant":
            metadata_parts = []
            if self.agent_used:
                metadata_parts.append(f"Agent: {self.agent_used}")
            if self.route:
                metadata_parts.append(f"Route: {self.route}")
            if self.processing_time_ms:
                metadata_parts.append(f"Time: {self.processing_time_ms}ms")
            if metadata_parts:
                formatted += f"\n   [{', '.join(metadata_parts)}]"

        return formatted

    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }


class Conversation(BaseModel):
    """Conversation containing multiple messages."""

    # MongoDB ID field
    id: Optional[str] = Field(default=None, alias="_id")

    # Relationship
    user_id: str

    # Conversation metadata
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Statistics
    message_count: int = Field(default=0)
    total_tokens: int = Field(default=0)

    # Status
    is_active: bool = Field(default=True)
    is_archived: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: datetime = Field(default_factory=get_current_time)
    last_message_at: Optional[datetime] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Conversation title cannot be empty")
        return v.strip()

    def to_mongo_dict(self) -> dict:
        """Convert to MongoDB-compatible dictionary."""
        data = self.model_dump(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = self.id
        return data

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "Conversation":
        """Create instance from MongoDB document."""
        if not data:
            return None
            
        if '_id' in data:
            data['id'] = str(data['_id'])
            del data['_id']
        
        # Convert datetime fields
        for field in ["created_at", "updated_at", "last_message_at"]:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)

    def generate_title(self, first_message: str) -> str:
        """Generate a title from the first message if not provided."""
        # Take first 50 characters and add ellipsis if truncated
        if len(first_message) > 50:
            return first_message[:47] + "..."
        return first_message

    def add_tag(self, tag: str) -> None:
        """Add a tag to the conversation."""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = get_current_time()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the conversation."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = get_current_time()

    def archive(self) -> None:
        """Archive the conversation."""
        self.is_archived = True
        self.is_active = False
        self.updated_at = get_current_time()

    def unarchive(self) -> None:
        """Unarchive the conversation."""
        self.is_archived = False
        self.is_active = True
        self.updated_at = get_current_time()

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }


class ConversationSummary(BaseModel):
    """Lightweight conversation summary for listing."""

    id: str
    title: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    is_active: bool
    is_archived: bool
    tags: List[str] = Field(default_factory=list)

    @classmethod
    def from_conversation(cls, conv: Conversation) -> "ConversationSummary":
        """Create summary from full conversation object."""
        return cls(
            id=conv.id,
            title=conv.title,
            message_count=conv.message_count,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            is_active=conv.is_active,
            is_archived=conv.is_archived,
            tags=conv.tags
        )

    def format_for_list(self) -> str:
        """Format for CLI conversation list display."""
        status = "Archived" if self.is_archived else "Active"
        date_str = self.created_at.strftime("%Y-%m-%d")
        return f"{status} - {self.title} ({self.message_count} messages) - {date_str}"
    
    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }