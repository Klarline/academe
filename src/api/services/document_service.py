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
            # Use your existing DocumentManager
            result = self.doc_manager.add_document(
                user_id=user_id,
                file_path=file_path,
                filename=filename
            )

            return {
                "document_id": result.get("document_id"),
                "filename": filename,
                "chunk_count": result.get("chunk_count", 0),
                "status": "processed"
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
            List of documents
        """
        return self.doc_manager.get_user_documents(user_id)

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
        return self.doc_manager.delete_document(user_id, document_id)

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
            Search results
        """
        return self.search_service.search(
            query=query,
            user_id=user_id,
            top_k=top_k
        )
