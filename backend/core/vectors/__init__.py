"""Vector database and embedding module for Academe."""

from .embeddings import EmbeddingService, HybridEmbeddingService, create_embedding_service
from .pinecone_client import PineconeClient, PineconeManager
from .search import SemanticSearchService
from .hybrid_search import HybridSearchService

__all__ = [
    "EmbeddingService",
    "HybridEmbeddingService",
    "create_embedding_service",
    "PineconeClient",
    "PineconeManager",
    "SemanticSearchService",
    "HybridSearchService",
]