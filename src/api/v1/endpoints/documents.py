"""
Document management endpoints.

Handles document upload, processing, search, and deletion.
"""

import logging
import os
from typing import Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    status
)
from pydantic import BaseModel, Field

from core.documents import DocumentManager
from core.utils.datetime_utils import get_current_time
from api.services import DocumentService
from api.v1.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
doc_service = DocumentService()
doc_manager = DocumentManager()

# Configuration
UPLOAD_DIR = Path("/tmp/academe_uploads")  # Configure for production
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


# Request/Response models
class DocumentUploadResponse(BaseModel):
    """Document upload response."""
    document_id: str
    filename: str
    status: str
    chunk_count: int
    message: str


class DocumentInfo(BaseModel):
    """Document information."""
    id: str
    user_id: str
    filename: str
    file_type: str
    size_bytes: int
    chunk_count: int
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """List of documents."""
    documents: List[DocumentInfo]
    total: int
    total_size_bytes: int


class DocumentSearchRequest(BaseModel):
    """Document search request."""
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class DocumentSearchResult(BaseModel):
    """Document search result."""
    document_id: str
    filename: str
    page_number: Optional[int] = None
    chunk_text: str
    relevance_score: float


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Upload and process a document.
    
    Accepts PDF, TXT, or MD files, extracts content, generates embeddings,
    and stores in vector database for semantic search.
    
    Args:
        file: Uploaded file
        current_user_id: ID of authenticated user
        
    Returns:
        Upload response with processing status
        
    Raises:
        HTTPException: If file type invalid or upload fails
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Save file temporarily
        user_upload_dir = UPLOAD_DIR / current_user_id
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_upload_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File uploaded: {file.filename} by user {current_user_id}")
        
        # Process document using document service
        result = await doc_service.process_uploaded_document(
            user_id=current_user_id,
            file_path=str(file_path),
            filename=file.filename
        )
        
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=file.filename,
            status=result["status"],
            chunk_count=result.get("chunk_count", 0),
            message="Document uploaded and processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.get("/", response_model=DocumentListResponse)
async def get_documents(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get user's documents.
    
    Returns list of all documents uploaded by the user with metadata.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        List of documents with statistics
    """
    try:
        # Get documents from document service
        documents_data = await doc_service.get_user_documents(current_user_id)
        
        # Convert to response model
        documents = []
        total_size = 0
        
        for doc in documents_data:
            documents.append(DocumentInfo(
                id=doc.get("id", ""),
                user_id=current_user_id,
                filename=doc.get("filename", ""),
                file_type=doc.get("file_type", "unknown"),
                size_bytes=doc.get("size_bytes", 0),
                chunk_count=doc.get("chunk_count", 0),
                status=doc.get("status", "unknown"),
                created_at=doc.get("created_at", get_current_time()),
                processed_at=doc.get("processed_at")
            ))
            total_size += doc.get("size_bytes", 0)
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            total_size_bytes=total_size
        )
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch documents"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Delete a document.
    
    Removes the document from storage and vector database.
    
    Args:
        document_id: Document ID to delete
        current_user_id: ID of authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        success = await doc_service.delete_document(
            user_id=current_user_id,
            document_id=document_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        logger.info(f"Document deleted: {document_id} by user {current_user_id}")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.post("/search", response_model=List[DocumentSearchResult])
async def search_documents(
    request: DocumentSearchRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Search within user's documents.
    
    Uses semantic search to find relevant passages across all user documents.
    
    Args:
        request: Search query and parameters
        current_user_id: ID of authenticated user
        
    Returns:
        List of search results with relevance scores
    """
    try:
        results = await doc_service.search_documents(
            user_id=current_user_id,
            query=request.query,
            top_k=request.top_k
        )
        
        # Convert to response model
        search_results = [
            DocumentSearchResult(
                document_id=r.get("document_id", ""),
                filename=r.get("filename", ""),
                page_number=r.get("page_number"),
                chunk_text=r.get("text", ""),
                relevance_score=r.get("score", 0.0)
            )
            for r in results
        ]
        
        return search_results
        
    except Exception as e:
        logger.error(f"Document search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )
