"""Document storage and retrieval for Academe."""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from bson import ObjectId

from core.database import get_database
from core.models.document import Document, DocumentChunk, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


class DocumentStorage:
    """Handle document file storage and database operations."""

    def __init__(self, storage_path: str = "../document_storage"):
        """
        Initialize document storage.

        Args:
            storage_path: Base path for document storage (relative to backend/)
                         Default: ../document_storage (root directory)
        """
        # Ensure we're using the root-level document_storage directory
        # Convert relative path to absolute to avoid confusion
        if storage_path.startswith("../"):
            # Get backend directory
            backend_dir = Path(__file__).parent.parent.parent
            self.storage_path = (backend_dir / storage_path).resolve()
            logger.info(f"Resolved storage path from {storage_path} via __file__: {self.storage_path}")
        else:
            self.storage_path = Path(storage_path)
            logger.info(f"Using direct storage path: {self.storage_path}")
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Document storage initialized at: {self.storage_path}")

        # Get database
        self.db = get_database()

    def save_document_file(
        self,
        source_path: str,
        user_id: str,
        document_id: str
    ) -> str:
        """
        Save document file to storage.

        Args:
            source_path: Path to source file
            user_id: User ID
            document_id: Document ID

        Returns:
            Path to stored file
        """
        # Create user directory
        user_dir = self.storage_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Get file extension
        source = Path(source_path)
        extension = source.suffix

        # Create destination path
        dest_filename = f"{document_id}{extension}"
        dest_path = user_dir / dest_filename

        # Copy file
        shutil.copy2(source_path, dest_path)

        logger.info(f"Saved document file to {dest_path}")
        return str(dest_path)

    def delete_document_file(self, file_path: str) -> bool:
        """
        Delete document file from storage.

        Args:
            file_path: Path to file

        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted document file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def get_document_path(self, user_id: str, document_id: str) -> Optional[str]:
        """
        Get path to stored document.

        Args:
            user_id: User ID
            document_id: Document ID

        Returns:
            Path to file or None if not found
        """
        user_dir = self.storage_path / user_id

        # Check for different extensions
        for ext in ['.pdf', '.txt', '.md']:
            file_path = user_dir / f"{document_id}{ext}"
            if file_path.exists():
                return str(file_path)

        return None


class DocumentRepository:
    """Repository for document database operations."""

    def __init__(self):
        """Initialize document repository."""
        self.db = get_database()

    def create_document(self, document: Document) -> str:
        """
        Create a new document record.

        Args:
            document: Document object

        Returns:
            Document ID
        """
        try:
            collection = self.db.get_database()["documents"]
            doc_dict = document.to_mongo_dict()

            # Remove id if None
            if '_id' in doc_dict and doc_dict['_id'] is None:
                del doc_dict['_id']

            result = collection.insert_one(doc_dict)
            logger.info(f"Created document with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise

    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document object or None
        """
        try:
            collection = self.db.get_database()["documents"]
            doc_dict = collection.find_one({"_id": ObjectId(document_id)})

            if doc_dict:
                return Document.from_mongo_dict(doc_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

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
        try:
            collection = self.db.get_database()["documents"]

            query = {"user_id": user_id}
            if not include_deleted:
                query["processing_status"] = {"$ne": "deleted"}  # String value, not enum

            cursor = collection.find(query).sort("uploaded_at", -1)

            documents = []
            for doc_dict in cursor:
                documents.append(Document.from_mongo_dict(doc_dict))

            return documents

        except Exception as e:
            logger.error(f"Failed to get user documents: {e}")
            return []

    def update_document(
        self,
        document_id: str,
        updates: dict
    ) -> bool:
        """
        Update document information.

        Args:
            document_id: Document ID
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        try:
            collection = self.db.get_database()["documents"]

            # Remove _id from updates
            updates.pop("_id", None)
            updates.pop("id", None)

            result = collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": updates}
            )

            if result.modified_count > 0:
                logger.info(f"Updated document {document_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """
        Mark document as deleted.

        Args:
            document_id: Document ID

        Returns:
            True if marked as deleted
        """
        return self.update_document(
            document_id,
            {
                "processing_status": "deleted",  # String value for MongoDB
                "is_active": False
            }
        )

    def find_document_by_hash(
        self,
        user_id: str,
        file_hash: str
    ) -> Optional[Document]:
        """
        Find document by file hash for deduplication.

        Args:
            user_id: User ID
            file_hash: SHA256 hash of file

        Returns:
            Document if found
        """
        try:
            collection = self.db.get_database()["documents"]
            doc_dict = collection.find_one({
                "user_id": user_id,
                "file_hash": file_hash,
                "processing_status": {"$ne": DocumentStatus.DELETED}
            })

            if doc_dict:
                return Document.from_mongo_dict(doc_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to find document by hash: {e}")
            return None


class ChunkRepository:
    """Repository for document chunk operations."""

    def __init__(self):
        """Initialize chunk repository."""
        self.db = get_database()

    def create_chunks(self, chunks: List[DocumentChunk]) -> List[str]:
        """
        Create multiple chunks in batch.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            List of chunk IDs
        """
        try:
            collection = self.db.get_database()["chunks"]

            # Convert to dicts
            chunk_dicts = [chunk.to_mongo_dict() for chunk in chunks]

            # Remove None ids
            for chunk_dict in chunk_dicts:
                if '_id' in chunk_dict and chunk_dict['_id'] is None:
                    del chunk_dict['_id']

            # Batch insert
            result = collection.insert_many(chunk_dicts)

            chunk_ids = [str(id) for id in result.inserted_ids]
            logger.info(f"Created {len(chunk_ids)} chunks")

            return chunk_ids

        except Exception as e:
            logger.error(f"Failed to create chunks: {e}")
            raise

    def get_document_chunks(
        self,
        document_id: str
    ) -> List[DocumentChunk]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            List of chunks ordered by index
        """
        try:
            collection = self.db.get_database()["chunks"]
            cursor = collection.find(
                {"document_id": document_id}
            ).sort("chunk_index", 1)

            chunks = []
            for chunk_dict in cursor:
                chunks.append(DocumentChunk.from_mongo_dict(chunk_dict))

            return chunks

        except Exception as e:
            logger.error(f"Failed to get document chunks: {e}")
            return []

    def get_user_chunks(
        self,
        user_id: str,
        include_deleted_docs: bool = False
    ) -> List[DocumentChunk]:
        """
        Get all chunks for a user (for BM25 index building).

        Args:
            user_id: User ID
            include_deleted_docs: If False, exclude chunks from deleted documents

        Returns:
            List of chunks from all user documents, ordered by document then index
        """
        try:
            collection = self.db.get_database()["chunks"]
            query = {"user_id": user_id}

            if not include_deleted_docs:
                # Exclude chunks from deleted documents
                docs_collection = self.db.get_database()["documents"]
                deleted_doc_ids = [
                    str(doc["_id"])
                    for doc in docs_collection.find(
                        {"user_id": user_id, "processing_status": "deleted"},
                        {"_id": 1}
                    )
                ]
                if deleted_doc_ids:
                    query["document_id"] = {"$nin": deleted_doc_ids}

            cursor = collection.find(query).sort(
                [("document_id", 1), ("chunk_index", 1)]
            )

            return [DocumentChunk.from_mongo_dict(c) for c in cursor]

        except Exception as e:
            logger.error(f"Failed to get user chunks: {e}")
            return []

    def get_adjacent_chunks(
        self,
        document_id: str,
        chunk_index: int,
        window: int = 1,
    ) -> List[DocumentChunk]:
        """
        Fetch a chunk and its neighbors within ±window of chunk_index.

        Used by the sliding-window context builder to expand retrieved
        chunks with surrounding text from the same document.

        Args:
            document_id: Document ID
            chunk_index: Center chunk index
            window: How many neighbors on each side

        Returns:
            Ordered list of chunks covering [chunk_index-window, chunk_index+window]
        """
        try:
            collection = self.db.get_database()["chunks"]
            lo = max(0, chunk_index - window)
            hi = chunk_index + window
            cursor = collection.find(
                {
                    "document_id": document_id,
                    "chunk_index": {"$gte": lo, "$lte": hi},
                }
            ).sort("chunk_index", 1)
            return [DocumentChunk.from_mongo_dict(c) for c in cursor]
        except Exception as e:
            logger.error(f"Failed to get adjacent chunks: {e}")
            return []

    def delete_document_chunks(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of chunks deleted
        """
        try:
            collection = self.db.get_database()["chunks"]
            result = collection.delete_many({"document_id": document_id})

            logger.info(f"Deleted {result.deleted_count} chunks for document {document_id}")
            return result.deleted_count

        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            return 0

    def search_chunks(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[DocumentChunk]:
        """
        Simple text search in chunks (before vector search is available).

        Args:
            user_id: User ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching chunks
        """
        try:
            collection = self.db.get_database()["chunks"]

            # Simple regex search (will be replaced by vector search)
            cursor = collection.find({
                "user_id": user_id,
                "content": {"$regex": query, "$options": "i"}
            }).limit(limit)

            chunks = []
            for chunk_dict in cursor:
                chunks.append(DocumentChunk.from_mongo_dict(chunk_dict))

            return chunks

        except Exception as e:
            logger.error(f"Failed to search chunks: {e}")
            return []

    def update_chunk_vectors(
        self,
        chunk_id: str,
        vector_id: str,
        embedding_model: str
    ) -> bool:
        """
        Update chunk with vector information.

        Args:
            chunk_id: Chunk ID
            vector_id: Pinecone vector ID
            embedding_model: Model used for embedding

        Returns:
            True if updated
        """
        try:
            collection = self.db.get_database()["chunks"]

            result = collection.update_one(
                {"_id": ObjectId(chunk_id)},
                {
                    "$set": {
                        "vector_id": vector_id,
                        "embedding_model": embedding_model
                    }
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Failed to update chunk vectors: {e}")
            return False