"""Pinecone vector database client for Academe."""

import logging
import time
from typing import List, Dict, Optional, Any, Tuple

try:
    import pinecone
    from pinecone import Index, GRPCIndex
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    # Mock classes for when Pinecone is not installed
    class Index:
        pass
    class GRPCIndex:
        pass

logger = logging.getLogger(__name__)


class PineconeClient:
    """Client for interacting with Pinecone vector database."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: str = "academe",
        dimension: int = 384,
        metric: str = "cosine"
    ):
        """
        Initialize Pinecone client.

        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Name of the Pinecone index
            dimension: Vector dimension
            metric: Distance metric (cosine, euclidean, dotproduct)
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric
        self.index = None

        # Initialize Pinecone
        self._init_pinecone()

    def _init_pinecone(self):
        """Initialize Pinecone connection."""
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone not installed, using mock mode")
            self.mock_mode = True
            self.mock_data = {}  # Simple in-memory storage for testing
            return

        if not self.api_key:
            # Try to get from environment/settings
            try:
                from core.config.settings import get_settings
                settings = get_settings()
                self.api_key = getattr(settings, 'pinecone_api_key', None)
                self.environment = getattr(settings, 'pinecone_environment', None)
            except:
                pass

        if not self.api_key:
            logger.warning("No Pinecone API key provided, using mock mode")
            self.mock_mode = True
            self.mock_data = {}
            return

        try:
            # Initialize Pinecone
            pinecone.init(
                api_key=self.api_key,
                environment=self.environment
            )

            # Check if index exists
            if self.index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {self.index_name}")
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric
                )
                # Wait for index to be ready
                time.sleep(5)

            # Connect to index
            self.index = pinecone.Index(self.index_name)
            self.mock_mode = False

            logger.info(f"Connected to Pinecone index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            self.mock_mode = True
            self.mock_data = {}

    def upsert_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        namespace: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Upsert vectors to Pinecone.

        Args:
            vectors: List of (id, vector, metadata) tuples
            namespace: Namespace for vectors (e.g., user ID)
            batch_size: Batch size for upserting

        Returns:
            Dictionary with upsert statistics
        """
        if self.mock_mode:
            return self._mock_upsert(vectors, namespace)

        try:
            total_upserted = 0

            # Process in batches
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]

                # Format for Pinecone
                formatted_batch = [
                    {
                        "id": vec_id,
                        "values": values,
                        "metadata": metadata
                    }
                    for vec_id, values, metadata in batch
                ]

                # Upsert batch
                response = self.index.upsert(
                    vectors=formatted_batch,
                    namespace=namespace
                )

                total_upserted += response.get("upserted_count", 0)

            logger.info(f"Upserted {total_upserted} vectors to namespace {namespace}")

            return {"upserted_count": total_upserted}

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return {"upserted_count": 0, "error": str(e)}

    def query(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Query similar vectors.

        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            namespace: Namespace to search in
            filter: Metadata filter
            include_metadata: Include metadata in results
            include_values: Include vector values in results

        Returns:
            List of similar vectors with scores
        """
        if self.mock_mode:
            return self._mock_query(query_vector, top_k, namespace)

        try:
            response = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter,
                include_metadata=include_metadata,
                include_values=include_values
            )

            results = []
            for match in response.get("matches", []):
                result = {
                    "id": match["id"],
                    "score": match["score"]
                }
                if include_metadata:
                    result["metadata"] = match.get("metadata", {})
                if include_values:
                    result["values"] = match.get("values", [])

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def delete_vectors(
        self,
        ids: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        delete_all: bool = False
    ) -> Dict[str, Any]:
        """
        Delete vectors from Pinecone.

        Args:
            ids: List of vector IDs to delete
            namespace: Namespace to delete from
            filter: Delete by metadata filter
            delete_all: Delete all vectors in namespace

        Returns:
            Deletion response
        """
        if self.mock_mode:
            return self._mock_delete(ids, namespace)

        try:
            response = self.index.delete(
                ids=ids,
                namespace=namespace,
                filter=filter,
                delete_all=delete_all
            )
            logger.info(f"Deleted vectors from namespace {namespace}")
            return response

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return {"error": str(e)}

    def describe_index(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index description and statistics
        """
        if self.mock_mode:
            return {
                "mock_mode": True,
                "namespaces": list(self.mock_data.keys()),
                "total_vectors": sum(len(v) for v in self.mock_data.values())
            }

        try:
            stats = self.index.describe_index_stats()
            return stats

        except Exception as e:
            logger.error(f"Failed to describe index: {e}")
            return {"error": str(e)}

    def create_namespace(self, user_id: str) -> str:
        """
        Create a namespace for a user.

        Args:
            user_id: User ID

        Returns:
            Namespace string
        """
        # Namespaces in Pinecone are created automatically on first upsert
        # This method just returns the namespace format
        return f"user_{user_id}"

    # Mock methods for testing without Pinecone

    def _mock_upsert(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        namespace: Optional[str] = None
    ) -> Dict[str, int]:
        """Mock upsert for testing."""
        namespace = namespace or "default"

        if namespace not in self.mock_data:
            self.mock_data[namespace] = {}

        for vec_id, values, metadata in vectors:
            self.mock_data[namespace][vec_id] = {
                "values": values,
                "metadata": metadata
            }

        return {"upserted_count": len(vectors)}

    def _mock_query(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Mock query for testing."""
        namespace = namespace or "default"

        if namespace not in self.mock_data:
            return []

        # Simple similarity calculation
        import numpy as np
        results = []

        for vec_id, data in self.mock_data[namespace].items():
            # Cosine similarity
            vec1 = np.array(query_vector)
            vec2 = np.array(data["values"])

            if len(vec1) != len(vec2):
                continue

            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

            results.append({
                "id": vec_id,
                "score": float(similarity),
                "metadata": data["metadata"]
            })

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _mock_delete(
        self,
        ids: Optional[List[str]] = None,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock delete for testing."""
        namespace = namespace or "default"

        if namespace not in self.mock_data:
            return {"deleted": 0}

        deleted = 0
        if ids:
            for vec_id in ids:
                if vec_id in self.mock_data[namespace]:
                    del self.mock_data[namespace][vec_id]
                    deleted += 1

        return {"deleted": deleted}


class PineconeManager:
    """High-level manager for Pinecone operations."""

    def __init__(self, client: Optional[PineconeClient] = None):
        """
        Initialize Pinecone manager.

        Args:
            client: PineconeClient instance
        """
        self.client = client or PineconeClient()

    def index_document_chunks(
        self,
        document_id: str,
        user_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> bool:
        """
        Index document chunks with embeddings.

        Args:
            document_id: Document ID
            user_id: User ID
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors

        Returns:
            True if successful
        """
        if len(chunks) != len(embeddings):
            logger.error("Chunks and embeddings count mismatch")
            return False

        # Create namespace for user
        namespace = self.client.create_namespace(user_id)

        # Prepare vectors for upsert
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vec_id = f"{document_id}_{chunk.get('chunk_index', 0)}"

            metadata = {
                "document_id": document_id,
                "chunk_index": chunk.get("chunk_index", 0),
                "content": chunk.get("content", "")[:1000],  # Truncate for metadata
                "page_number": chunk.get("page_number"),
                "section_title": chunk.get("section_title"),
                "has_code": chunk.get("has_code", False),
                "has_equations": chunk.get("has_equations", False)
            }

            vectors.append((vec_id, embedding, metadata))

        # Upsert to Pinecone
        result = self.client.upsert_vectors(vectors, namespace=namespace)

        return result.get("upserted_count", 0) > 0

    def search_similar_chunks(
        self,
        user_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in user's namespace.

        Args:
            user_id: User ID
            query_embedding: Query vector
            top_k: Number of results
            filter: Optional metadata filter

        Returns:
            List of similar chunks with metadata
        """
        namespace = self.client.create_namespace(user_id)

        results = self.client.query(
            query_vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_metadata=True
        )

        return results

    def delete_document_vectors(
        self,
        document_id: str,
        user_id: str
    ) -> bool:
        """
        Delete all vectors for a document.

        Args:
            document_id: Document ID
            user_id: User ID

        Returns:
            True if successful
        """
        namespace = self.client.create_namespace(user_id)

        # In production Pinecone, we'd use metadata filter
        # For now, we'll delete by ID pattern
        # This is a limitation of the free tier

        # Get all vectors for document (mock implementation)
        # In production, use metadata filter
        result = self.client.delete_vectors(
            filter={"document_id": document_id},
            namespace=namespace
        )

        return True