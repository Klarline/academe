"""Semantic search service for Academe."""

import logging
from typing import List, Dict, Optional, Any, Tuple

from core.vectors.embeddings import EmbeddingService, create_embedding_service
from core.vectors.pinecone_client import PineconeClient, PineconeManager
from core.models.document import DocumentChunk, Document, DocumentSearchResult
from core.documents.storage import ChunkRepository, DocumentRepository

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None


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

        # Cross-encoder for reranking (optional)
        self._reranker = None
        if CROSS_ENCODER_AVAILABLE:
            try:
                self._reranker = CrossEncoder(
                    "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    max_length=512,
                )
                logger.info("Cross-encoder reranker loaded")
            except Exception as e:
                logger.warning(f"Reranker not available: {e}")

    @staticmethod
    def _enrich_text_for_embedding(
        content: str,
        document_title: Optional[str] = None,
        section_title: Optional[str] = None,
    ) -> str:
        """
        Build a contextual embedding string by prepending document metadata.

        The enriched text is used only for embedding generation — the raw
        content is still stored in Pinecone metadata for display.
        """
        parts = []
        if document_title:
            parts.append(f"Document: {document_title}")
        if section_title:
            parts.append(f"Section: {section_title}")
        if parts:
            return " | ".join(parts) + "\n" + content
        return content

    def index_document(
        self,
        document: Document,
        chunks: List[DocumentChunk]
    ) -> Tuple[bool, str]:
        """
        Index a document's chunks for semantic search.

        Uses contextual embedding enrichment: each chunk text is prefixed
        with the document title and section before being embedded, so the
        embedding captures document-level context.

        Args:
            document: Document object
            chunks: List of document chunks

        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info(f"Indexing document {document.id} with {len(chunks)} chunks")

            # Build enriched texts for embedding (raw content stored separately)
            texts = [
                self._enrich_text_for_embedding(
                    chunk.content,
                    document_title=document.title,
                    section_title=chunk.section_title,
                )
                for chunk in chunks
            ]

            # Generate embeddings from enriched text
            logger.info("Generating contextual embeddings...")
            embeddings = self.embedding_service.generate_embeddings_batch(texts)

            if len(embeddings) != len(chunks):
                return False, "Failed to generate embeddings for all chunks"

            # Prepare chunk data for indexing
            chunk_data = []
            for i, chunk in enumerate(chunks):
                # Build metadata, filtering out None values (Pinecone doesn't accept null)
                metadata = {
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "has_code": chunk.has_code,
                    "has_equations": chunk.has_equations
                }
                
                # Add optional fields only if they have values
                if chunk.page_number is not None:
                    metadata["page_number"] = chunk.page_number
                if chunk.section_title is not None:
                    metadata["section_title"] = chunk.section_title
                
                chunk_data.append(metadata)

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
        score_threshold: float = 0.2  # Lowered from 0.5 for better recall
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
            
            logger.info(f"Processing {len(pinecone_results)} Pinecone results")
            
            for i, result in enumerate(pinecone_results):
                logger.info(f"Result {i}: id={result.get('id')}, score={result.get('score')}")
                
                if result.get("score", 0) < score_threshold:
                    logger.debug(f"Skipping result {i}: score {result.get('score')} below threshold {score_threshold}")
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
        initial_multiplier: int = 2,
        **kwargs
    ) -> List[DocumentSearchResult]:
        """
        Search with cross-encoder reranking for better relevance.

        Retrieves more candidates initially, then reranks with cross-encoder
        for improved precision. Falls back to keyword-overlap if reranker
        unavailable.

        Args:
            query: Search query
            user_id: User ID
            top_k: Initial number of results to retrieve
            rerank_top_k: Number of results after reranking
            initial_multiplier: Retrieve top_k * multiplier for reranking
            **kwargs: Additional search parameters

        Returns:
            Reranked search results
        """
        # Get initial results (more than needed for reranking)
        initial_results = self.search(
            query=query,
            user_id=user_id,
            top_k=max(top_k * initial_multiplier, 20),
            **kwargs
        )

        if len(initial_results) <= rerank_top_k:
            return initial_results[:rerank_top_k]

        # Cross-encoder reranking when available
        if self._reranker:
            reranked = self._rerank_with_cross_encoder(query, initial_results)
        else:
            reranked = self._rerank_results(query, initial_results)

        return reranked[:rerank_top_k]

    def rerank_results(
        self,
        query: str,
        results: List[DocumentSearchResult],
        top_k: Optional[int] = None,
    ) -> List[DocumentSearchResult]:
        """
        Rerank existing results with cross-encoder (or keyword fallback).

        Useful when initial retrieval comes from hybrid search.
        """
        if not results:
            return []
        if top_k is not None and len(results) <= top_k:
            return results[:top_k]

        if self._reranker:
            reranked = self._rerank_with_cross_encoder(query, results)
        else:
            reranked = self._rerank_results(query, results)

        return reranked[:top_k] if top_k else reranked

    def _rerank_with_cross_encoder(
        self,
        query: str,
        results: List[DocumentSearchResult],
    ) -> List[DocumentSearchResult]:
        """Rerank using cross-encoder model."""
        pairs = [[query, r.chunk.content[:512]] for r in results]
        scores = self._reranker.predict(pairs)

        for result, score in zip(results, scores):
            result.score = float(score)

        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        return results

    def _rerank_results(
        self,
        query: str,
        results: List[DocumentSearchResult]
    ) -> List[DocumentSearchResult]:
        """
        Fallback reranking based on keyword overlap.
        """
        query_terms = set(query.lower().split())

        for result in results:
            chunk_terms = set(result.chunk.content.lower().split())
            overlap = len(query_terms & chunk_terms)
            boost = overlap * 0.05
            result.score = min(1.0, result.score + boost)

            if result.chunk.section_title:
                title_terms = set(result.chunk.section_title.lower().split())
                if query_terms & title_terms:
                    result.score = min(1.0, result.score + 0.1)

        results.sort(key=lambda x: x.score, reverse=True)
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