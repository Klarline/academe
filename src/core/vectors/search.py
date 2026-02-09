"""Semantic search service for Academe."""

import logging
from typing import List, Dict, Optional, Any, Tuple

from core.vectors.embeddings import EmbeddingService, create_embedding_service
from core.vectors.pinecone_client import PineconeClient, PineconeManager
from core.models.document import DocumentChunk, Document, DocumentSearchResult
from core.documents.storage import ChunkRepository, DocumentRepository

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Service for semantic search over documents."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        pinecone_client: Optional[PineconeClient] = None
    ):
        """
        Initialize semantic search service.

        Args:
            embedding_service: Service for generating embeddings
            pinecone_client: Client for vector database
        """
        self.embedding_service = embedding_service or create_embedding_service()
        self.pinecone_client = pinecone_client or PineconeClient()
        self.pinecone_manager = PineconeManager(self.pinecone_client)
        self.chunk_repo = ChunkRepository()
        self.doc_repo = DocumentRepository()

    def index_document(
        self,
        document: Document,
        chunks: List[DocumentChunk]
    ) -> Tuple[bool, str]:
        """
        Index a document's chunks for semantic search.

        Args:
            document: Document object
            chunks: List of document chunks

        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info(f"Indexing document {document.id} with {len(chunks)} chunks")

            # Extract text from chunks
            texts = [chunk.content for chunk in chunks]

            # Generate embeddings
            logger.info("Generating embeddings...")
            embeddings = self.embedding_service.generate_embeddings_batch(texts)

            if len(embeddings) != len(chunks):
                return False, "Failed to generate embeddings for all chunks"

            # Prepare chunk data for indexing
            chunk_data = []
            for i, chunk in enumerate(chunks):
                chunk_data.append({
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "has_code": chunk.has_code,
                    "has_equations": chunk.has_equations
                })

            # Index in Pinecone
            logger.info("Indexing in vector database...")
            success = self.pinecone_manager.index_document_chunks(
                document_id=document.id,
                user_id=document.user_id,
                chunks=chunk_data,
                embeddings=embeddings
            )

            if success:
                # Update chunks with vector information
                for i, chunk in enumerate(chunks):
                    vec_id = f"{document.id}_{chunk.chunk_index}"
                    self.chunk_repo.update_chunk_vectors(
                        chunk_id=chunk.id,
                        vector_id=vec_id,
                        embedding_model=self.embedding_service.model_name
                    )

                # Update document status
                self.doc_repo.update_document(
                    document.id,
                    {
                        "vector_namespace": f"user_{document.user_id}",
                        "embedding_model": self.embedding_service.model_name
                    }
                )

                return True, f"Successfully indexed {len(chunks)} chunks"
            else:
                return False, "Failed to index vectors"

        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False, f"Indexing failed: {str(e)}"

    def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filter_document_id: Optional[str] = None,
        filter_has_code: Optional[bool] = None,
        filter_has_equations: Optional[bool] = None,
        score_threshold: float = 0.5
    ) -> List[DocumentSearchResult]:
        """
        Perform semantic search over user's documents.

        Args:
            query: Search query
            user_id: User ID
            top_k: Number of results to return
            filter_document_id: Filter to specific document
            filter_has_code: Filter chunks with code
            filter_has_equations: Filter chunks with equations
            score_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)

            # Build metadata filter
            metadata_filter = {}
            if filter_document_id:
                metadata_filter["document_id"] = filter_document_id
            if filter_has_code is not None:
                metadata_filter["has_code"] = filter_has_code
            if filter_has_equations is not None:
                metadata_filter["has_equations"] = filter_has_equations

            # Search in Pinecone
            pinecone_results = self.pinecone_manager.search_similar_chunks(
                user_id=user_id,
                query_embedding=query_embedding,
                top_k=top_k,
                filter=metadata_filter if metadata_filter else None
            )

            # Convert to DocumentSearchResult objects
            search_results = []
            for i, result in enumerate(pinecone_results):
                if result["score"] < score_threshold:
                    continue

                # Parse chunk ID to get document and chunk index
                vec_id = result["id"]
                parts = vec_id.split("_")
                if len(parts) >= 2:
                    document_id = "_".join(parts[:-1])
                    chunk_index = int(parts[-1])
                else:
                    continue

                # Get document
                document = self.doc_repo.get_document(document_id)
                if not document:
                    continue

                # Create chunk from metadata
                chunk = DocumentChunk(
                    document_id=document_id,
                    user_id=user_id,
                    chunk_index=chunk_index,
                    content=result["metadata"].get("content", ""),
                    page_number=result["metadata"].get("page_number"),
                    section_title=result["metadata"].get("section_title"),
                    char_count=len(result["metadata"].get("content", "")),
                    word_count=len(result["metadata"].get("content", "").split()),
                    has_code=result["metadata"].get("has_code", False),
                    has_equations=result["metadata"].get("has_equations", False)
                )

                search_result = DocumentSearchResult(
                    chunk=chunk,
                    document=document,
                    score=result["score"],
                    rank=i + 1
                )

                search_results.append(search_result)

            logger.info(f"Found {len(search_results)} results for query: '{query}'")
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def search_with_reranking(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        rerank_top_k: int = 5,
        **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Search with reranking for better relevance.

        Args:
            query: Search query
            user_id: User ID
            top_k: Initial number of results
            rerank_top_k: Number of results after reranking
            **kwargs: Additional search parameters

        Returns:
            Reranked search results
        """
        # Get initial results
        initial_results = self.search(
            query=query,
            user_id=user_id,
            top_k=top_k,
            **kwargs
        )

        if len(initial_results) <= rerank_top_k:
            return initial_results

        # Simple reranking based on content overlap
        # In production, use a cross-encoder model
        reranked = self._rerank_results(query, initial_results)

        return reranked[:rerank_top_k]

    def _rerank_results(
        self,
        query: str,
        results: List[DocumentSearchResult]
    ) -> List[DocumentSearchResult]:
        """
        Rerank results based on additional criteria.

        Args:
            query: Original query
            results: Initial search results

        Returns:
            Reranked results
        """
        # Simple reranking based on keyword overlap
        query_terms = set(query.lower().split())

        for result in results:
            chunk_terms = set(result.chunk.content.lower().split())
            overlap = len(query_terms & chunk_terms)

            # Boost score based on overlap
            boost = overlap * 0.05
            result.score = min(1.0, result.score + boost)

            # Boost if section title matches
            if result.chunk.section_title:
                title_terms = set(result.chunk.section_title.lower().split())
                if query_terms & title_terms:
                    result.score = min(1.0, result.score + 0.1)

        # Re-sort by new scores
        results.sort(key=lambda x: x.score, reverse=True)

        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def find_similar_chunks(
        self,
        chunk: DocumentChunk,
        user_id: str,
        top_k: int = 5
    ) -> List[DocumentSearchResult]:
        """
        Find chunks similar to a given chunk.

        Args:
            chunk: Reference chunk
            user_id: User ID
            top_k: Number of similar chunks

        Returns:
            List of similar chunks
        """
        # Generate embedding for chunk
        chunk_embedding = self.embedding_service.generate_embedding(chunk.content)

        # Search for similar
        results = self.search(
            query="",  # Empty query since we're using chunk embedding
            user_id=user_id,
            top_k=top_k + 1  # Get extra since original chunk might be included
        )

        # Filter out the original chunk
        filtered_results = [
            r for r in results
            if r.chunk.document_id != chunk.document_id or
            r.chunk.chunk_index != chunk.chunk_index
        ]

        return filtered_results[:top_k]

    def delete_document_index(
        self,
        document_id: str,
        user_id: str
    ) -> bool:
        """
        Delete document from vector index.

        Args:
            document_id: Document ID
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            success = self.pinecone_manager.delete_document_vectors(
                document_id=document_id,
                user_id=user_id
            )

            if success:
                logger.info(f"Deleted vectors for document {document_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete document index: {e}")
            return False

    def get_index_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about user's vector index.

        Args:
            user_id: User ID

        Returns:
            Index statistics
        """
        namespace = f"user_{user_id}"
        stats = self.pinecone_client.describe_index()

        # Extract namespace-specific stats if available
        if "namespaces" in stats:
            user_stats = stats.get("namespaces", {}).get(namespace, {})
        else:
            user_stats = stats

        return {
            "namespace": namespace,
            "vector_count": user_stats.get("vector_count", 0),
            "embedding_model": self.embedding_service.model_name,
            "embedding_dimension": self.embedding_service.embedding_dim,
            **user_stats
        }