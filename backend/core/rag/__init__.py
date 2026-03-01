"""RAG (Retrieval-Augmented Generation) module for Academe."""

from .pipeline import RAGPipeline
from .adaptive_retrieval import AdaptiveRetriever, classify_query, QueryType
from .query_rewriter import QueryRewriter, HyDE
from .response_cache import SemanticResponseCache
from .self_rag import SelfRAGController, RetrievalVerifier
from .query_decomposer import QueryDecomposer
from .feedback import RetrievalFeedback

__all__ = [
    "RAGPipeline",
    "AdaptiveRetriever",
    "classify_query",
    "QueryType",
    "QueryRewriter",
    "HyDE",
    "SemanticResponseCache",
    "SelfRAGController",
    "RetrievalVerifier",
    "QueryDecomposer",
    "RetrievalFeedback",
]