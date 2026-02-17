"""Document management orchestrator for Academe."""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.documents import (
    ChunkRepository,
    DocumentChunker,
    DocumentProcessorFactory,
    DocumentRepository,
    DocumentStorage,
)
from core.models.document import Document, DocumentChunk, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


class DocumentManager:
    """Orchestrate document processing, chunking, and storage."""

    def __init__(
        self,
        storage_path: str = "./document_storage",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize document manager.

        Args:
            storage_path: Base path for document storage
            chunk_size: Default chunk size
            chunk_overlap: Default chunk overlap
        """
        self.storage = DocumentStorage(storage_path)
        self.doc_repo = DocumentRepository()
        self.chunk_repo = ChunkRepository()
        self.processor_factory = DocumentProcessorFactory()
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)

    def upload_document(
        self,
        file_path: str,
        user_id: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        course: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Document]]:
        """
        Upload and process a document.

        Args:
            file_path: Path to document file
            user_id: User ID
            title: Optional document title
            tags: Optional tags
            course: Optional course name

        Returns:
            Tuple of (success, message, document)
        """
        start_time = time.time()

        try:
            # Validate file exists
            path = Path(file_path)
            if not path.exists():
                return False, f"File not found: {file_path}", None

            # Check file size
            file_size = path.stat().st_size
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                return False, f"File too large: {file_size / 1024 / 1024:.1f}MB (max 50MB)", None

            # Calculate file hash for deduplication
            processor = self.processor_factory.get_processor(file_path)
            file_hash = processor.calculate_file_hash(file_path) if hasattr(processor, 'calculate_file_hash') else ""

            # Check for duplicate
            if file_hash:
                existing = self.doc_repo.find_document_by_hash(user_id, file_hash)
                if existing:
                    return False, f"Document already exists: {existing.title or existing.original_filename}", existing

            # Determine document type
            extension = path.suffix.lower()
            doc_type_map = {
                '.pdf': DocumentType.PDF,
                '.txt': DocumentType.TXT,
                '.md': DocumentType.MARKDOWN,
                '.markdown': DocumentType.MARKDOWN,
            }
            doc_type = doc_type_map.get(extension, DocumentType.TXT)

            # Create document record
            document = Document(
                user_id=user_id,
                filename=path.name,
                original_filename=path.name,
                file_path="",  # Will be updated after saving
                file_size=file_size,
                file_hash=file_hash,
                document_type=doc_type,
                title=title or path.stem,
                tags=tags or [],
                course=course,
                processing_status=DocumentStatus.UPLOADED
            )

            # Save document record
            doc_id = self.doc_repo.create_document(document)
            document.id = doc_id

            # Save file to storage
            stored_path = self.storage.save_document_file(file_path, user_id, doc_id)
            self.doc_repo.update_document(doc_id, {"file_path": stored_path})
            document.file_path = stored_path

            # Process document
            success, message = self._process_document(document)

            processing_time = time.time() - start_time
            logger.info(f"Document upload completed in {processing_time:.2f}s: {message}")

            return success, message, document

        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return False, f"Upload failed: {str(e)}", None

    def _process_document(self, document: Document) -> Tuple[bool, str]:
        """
        Process document (extract text and create chunks).

        Args:
            document: Document object

        Returns:
            Tuple of (success, message)
        """
        try:
            # Update status to processing
            self.doc_repo.update_document(
                document.id,
                {"processing_status": DocumentStatus.PROCESSING}
            )

            # Extract text and metadata
            processor = self.processor_factory.get_processor(document.file_path)

            if document.document_type == DocumentType.PDF:
                text, metadata = processor.process_pdf(document.file_path)
            else:
                text, metadata = processor.process_text_file(document.file_path)

            # Update document with metadata
            updates = {
                "page_count": metadata.get("page_count"),
                "word_count": metadata.get("word_count"),
            }

            # Update title if extracted
            if metadata.get("title") and not document.title:
                updates["title"] = metadata["title"]

            if metadata.get("author"):
                updates["author"] = metadata["author"]

            if metadata.get("subject"):
                updates["subject"] = metadata["subject"]

            self.doc_repo.update_document(document.id, updates)

            # Chunk the document
            chunks = self.chunker.chunk_document(
                text,
                document.id,
                document.user_id,
                metadata={"document_title": document.title}
            )

            # Save chunks
            chunk_ids = self.chunk_repo.create_chunks(chunks)

            # Update document status to ready
            self.doc_repo.update_document(
                document.id,
                {
                    "processing_status": DocumentStatus.READY,
                    "chunk_count": len(chunks),
                    "processed_at": time.time()
                }
            )
            
            # Queue vector indexing as background task
            try:
                from core.tasks import index_document_task
                index_document_task.delay(document.id, document.user_id)
                logger.info(f"Queued indexing task for document {document.id}")
            except Exception as e:
                logger.warning(f"Failed to queue indexing task: {e}. Document processed but not indexed.")

            return True, f"Successfully processed: {len(chunks)} chunks created"

        except Exception as e:
            logger.error(f"Failed to process document {document.id}: {e}")

            # Update status to failed
            self.doc_repo.update_document(
                document.id,
                {
                    "processing_status": DocumentStatus.FAILED,
                    "processing_error": str(e)
                }
            )

            return False, f"Processing failed: {str(e)}"

    def delete_document(
        self,
        document_id: str,
        user_id: str,
        delete_file: bool = True
    ) -> Tuple[bool, str]:
        """
        Delete a document and its chunks.

        Args:
            document_id: Document ID
            user_id: User ID (for verification)
            delete_file: Whether to delete the physical file

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get document
            document = self.doc_repo.get_document(document_id)

            if not document:
                return False, "Document not found"

            if document.user_id != user_id:
                return False, "Unauthorized"

            # Delete chunks
            deleted_chunks = self.chunk_repo.delete_document_chunks(document_id)

            # Delete file if requested
            if delete_file and document.file_path:
                self.storage.delete_document_file(document.file_path)

            # Mark document as deleted
            self.doc_repo.delete_document(document_id)

            return True, f"Deleted document and {deleted_chunks} chunks"

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False, f"Deletion failed: {str(e)}"

    def get_user_documents(
        self,
        user_id: str,
        include_deleted: bool = False
    ) -> List[Document]:
        """
        Get all documents for a user.

        Args:
            user_id: User ID
            include_deleted: Include deleted documents

        Returns:
            List of documents
        """
        return self.doc_repo.get_user_documents(user_id, include_deleted)

    def get_document_chunks(
        self,
        document_id: str,
        user_id: str
    ) -> List[DocumentChunk]:
        """
        Get chunks for a document.

        Args:
            document_id: Document ID
            user_id: User ID (for verification)

        Returns:
            List of chunks
        """
        # Verify ownership
        document = self.doc_repo.get_document(document_id)
        if not document or document.user_id != user_id:
            return []

        return self.chunk_repo.get_document_chunks(document_id)

    def search_documents(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Document]:
        """
        Search user's documents by title or tags.

        Args:
            user_id: User ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching documents
        """
        # Get all user documents
        documents = self.get_user_documents(user_id)

        # Simple search (will be enhanced with vector search)
        query_lower = query.lower()
        matches = []

        for doc in documents:
            if doc.processing_status != DocumentStatus.READY:
                continue

            # Check title
            if doc.title and query_lower in doc.title.lower():
                matches.append(doc)
                continue

            # Check tags
            if any(query_lower in tag.lower() for tag in doc.tags):
                matches.append(doc)
                continue

            # Check filename
            if query_lower in doc.original_filename.lower():
                matches.append(doc)

        return matches[:limit]

    def get_document_stats(self, user_id: str) -> Dict:
        """
        Get statistics about user's documents.

        Args:
            user_id: User ID

        Returns:
            Dictionary of statistics
        """
        documents = self.get_user_documents(user_id)

        stats = {
            "total_documents": len(documents),
            "ready_documents": sum(1 for d in documents if d.processing_status == DocumentStatus.READY),
            "failed_documents": sum(1 for d in documents if d.processing_status == DocumentStatus.FAILED),
            "total_chunks": sum(d.chunk_count for d in documents),
            "total_pages": sum(d.page_count or 0 for d in documents),
            "total_size_mb": sum(d.file_size for d in documents) / (1024 * 1024),
        }

        return stats