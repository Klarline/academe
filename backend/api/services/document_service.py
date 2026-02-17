"""
Document service that wraps Academe document processing for API use.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.documents import DocumentManager
from core.rag import RAGPipeline
from core.vectors import SemanticSearchService

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for handling document operations.
    """

    def __init__(self):
        """Initialize document service."""
        self.doc_manager = DocumentManager()
        self.rag_pipeline = RAGPipeline()
        self.search_service = SemanticSearchService()

    async def process_uploaded_document(
        self,
        user_id: str,
        file_path: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process an uploaded document using DocumentManager.

        Args:
            user_id: User ID
            file_path: Path to uploaded file
            filename: Original filename

        Returns:
            Processing result
        """
        try:
            # Use DocumentManager's upload_document method
            success, message, document = self.doc_manager.upload_document(
                file_path=file_path,
                user_id=user_id,
                title=filename
            )

            # If document already exists, return existing document info
            if not success and document:
                return {
                    "document_id": document.id,
                    "filename": document.filename,
                    "chunk_count": document.chunk_count,
                    "status": document.processing_status.value if hasattr(document.processing_status, 'value') else str(document.processing_status),
                    "message": message,
                    "already_exists": True
                }
            
            # If failed without document, raise error
            if not success:
                raise Exception(message)

            return {
                "document_id": document.id,
                "filename": filename,
                "chunk_count": document.chunk_count,
                "status": document.processing_status.value if hasattr(document.processing_status, 'value') else str(document.processing_status)
            }

        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise

    async def get_user_documents(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all documents for a user.

        Args:
            user_id: User ID

        Returns:
            List of document dictionaries
        """
        documents = self.doc_manager.get_user_documents(user_id)
        
        # Convert Document objects to dicts
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.document_type.value if hasattr(doc.document_type, 'value') else str(doc.document_type),
                "size_bytes": doc.file_size,
                "chunk_count": doc.chunk_count,
                "status": doc.processing_status.value if hasattr(doc.processing_status, 'value') else str(doc.processing_status),
                "created_at": doc.uploaded_at,  # Document uses uploaded_at, not created_at
                "processed_at": doc.processed_at
            }
            for doc in documents
        ]

    async def delete_document(
        self,
        user_id: str,
        document_id: str
    ) -> bool:
        """
        Delete a document.

        Args:
            user_id: User ID
            document_id: Document ID

        Returns:
            Success status
        """
        success, message = self.doc_manager.delete_document(
            document_id=document_id,
            user_id=user_id,
            delete_file=True
        )
        return success

    async def search_documents(
        self,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search user's documents using semantic search.

        Args:
            user_id: User ID
            query: Search query
            top_k: Number of results

        Returns:
            Search results as dictionaries
        """
        results = self.search_service.search(
            query=query,
            user_id=user_id,
            top_k=top_k
        )
        
        # Convert DocumentSearchResult objects to dicts
        return [
            {
                "document_id": r.document.id,
                "filename": r.document.filename or r.document.original_filename,
                "page_number": r.chunk.page_number,
                "chunk_text": r.chunk.content,
                "similarity_score": r.score  # Frontend expects similarity_score
            }
            for r in results
        ]
