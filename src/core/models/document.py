"""Document models for RAG features."""

from bson import ObjectId
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator

from core.utils import get_current_time


class DocumentStatus(str, Enum):
    """Document processing status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    TXT = "txt"
    MARKDOWN = "md"
    DOCX = "docx"  # Future support


class Document(BaseModel):
    """Document metadata model."""

    # MongoDB ID
    id: Optional[str] = Field(default=None, alias="_id")

    # Ownership
    user_id: str

    # File information
    filename: str
    original_filename: str
    file_path: str  # Path to stored file
    file_size: int  # Size in bytes
    file_hash: str  # SHA256 hash for deduplication
    document_type: DocumentType

    # Document metadata
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

    # Processing information
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    chunk_count: int = 0
    processing_status: DocumentStatus = DocumentStatus.UPLOADED
    processing_error: Optional[str] = None
    processing_time_seconds: Optional[float] = None

    # Vector database information
    vector_namespace: Optional[str] = None  # Pinecone namespace
    vector_ids: List[str] = Field(default_factory=list)
    embedding_model: Optional[str] = None

    # Organization
    tags: List[str] = Field(default_factory=list)
    course: Optional[str] = None
    category: Optional[str] = None

    # Flags
    is_active: bool = True
    is_public: bool = False  # For future sharing features

    # Timestamps
    uploaded_at: datetime = Field(default_factory=get_current_time)
    processed_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None

    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size (max 50MB)."""
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f"File size exceeds maximum of 50MB")
        return v

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename has correct extension."""
        valid_extensions = ['.pdf', '.txt', '.md']
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(f"Unsupported file type. Supported: {valid_extensions}")
        return v

    def to_mongo_dict(self) -> dict:
        """Convert to MongoDB-compatible dictionary."""
        data = self.model_dump(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = self.id
        return data

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "Document":
        """Create instance from MongoDB document."""
        if not data:
            return None
            
        if '_id' in data:
            data['id'] = str(data['_id'])
            del data['_id']
        
        # Convert datetime fields
        for field in ["uploaded_at", "processed_at", "last_accessed_at"]:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert enums
        if "processing_status" in data and isinstance(data["processing_status"], str):
            data["processing_status"] = DocumentStatus(data["processing_status"])
        if "document_type" in data and isinstance(data["document_type"], str):
            data["document_type"] = DocumentType(data["document_type"])
        
        return cls(**data)

    def get_summary(self) -> str:
        """Get a summary of the document."""
        status_icon = {
            DocumentStatus.UPLOADED: "Uploaded",
            DocumentStatus.PROCESSING: "Processing",
            DocumentStatus.READY: "Ready",
            DocumentStatus.FAILED: "Failed",
            DocumentStatus.DELETED: "Deleted"
        }.get(self.processing_status, "Unknown")

        return (
            f"{status_icon} - {self.title or self.original_filename} "
            f"({self.page_count or '?'} pages, {self.chunk_count} chunks)"
        )

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }


class DocumentChunk(BaseModel):
    """Individual chunk of a document."""

    # MongoDB ID
    id: Optional[str] = Field(default=None, alias="_id")

    # Relationships
    document_id: str
    user_id: str

    # Chunk information
    chunk_index: int  # Order in document
    content: str  # The actual text

    # Location in document
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    paragraph_index: Optional[int] = None

    # Chunk metadata
    char_count: int
    word_count: int
    has_equations: bool = False
    has_code: bool = False
    has_tables: bool = False

    # Vector information
    vector_id: Optional[str] = None  # Pinecone vector ID
    embedding: Optional[List[float]] = None  # Optional local storage
    embedding_model: Optional[str] = None

    # Additional metadata for better retrieval
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=get_current_time)

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not empty."""
        if not v.strip():
            raise ValueError("Chunk content cannot be empty")
        return v

    def to_mongo_dict(self) -> dict:
        """Convert to MongoDB-compatible dictionary."""
        data = self.model_dump(by_alias=True, exclude={'id', 'embedding'})
        if self.id:
            data['_id'] = self.id
        return data

    @classmethod
    def from_mongo_dict(cls, data: dict) -> "DocumentChunk":
        """Create instance from MongoDB document."""
        if not data:
            return None
            
        if '_id' in data:
            data['id'] = str(data['_id'])
            del data['_id']
        
        # Convert datetime fields
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        return cls(**data)

    def get_context_string(self) -> str:
        """Get context string for RAG prompts."""
        context_parts = []

        if self.section_title:
            context_parts.append(f"Section: {self.section_title}")
        if self.page_number:
            context_parts.append(f"Page {self.page_number}")

        context = " | ".join(context_parts) if context_parts else ""

        return f"[{context}]\n{self.content}" if context else self.content

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }


class DocumentSearchResult(BaseModel):
    """Search result for document queries."""

    chunk: DocumentChunk
    document: Document
    score: float  # Similarity score
    rank: int  # Result ranking

    def format_for_context(self) -> str:
        """Format for inclusion in LLM context."""
        return (
            f"Source: {self.document.title or self.document.original_filename}\n"
            f"{self.chunk.get_context_string()}\n"
            f"---"
        )
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True