"""RAG (Retrieval-Augmented Generation) module for Academe."""

from .pipeline import RAGPipeline
from .adaptive_retrieval import AdaptiveRetriever, classify_query, QueryType
from .query_rewriter import QueryRewriter, HyDE
from .response_cache import SemanticResponseCache, RedisResponseCache
from .self_rag import SelfRAGController, RetrievalVerifier
from .query_decomposer import QueryDecomposer
from .feedback import RetrievalFeedback
from .request_budget import RequestBudget
from .fallback import fallback, with_fallback, FallbackStrategies, FallbackExhausted
from .stage_metrics import RequestMetrics, AggregateMetrics, get_aggregate_metrics
from .retrieval_profiles import (
    RetrievalProfile,
    ProfileName,
    get_profile,
    select_profile_for_query,
    FAST,
    BALANCED,
    DEEP,
)
from .proposition_indexer import PropositionExtractor, PropositionRepository, Proposition
from .knowledge_graph import (
    KGExtractor, KnowledgeGraphRepository, KnowledgeGraphTraverser, KGTriple,
)

__all__ = [
    "RAGPipeline",
    "AdaptiveRetriever",
    "classify_query",
    "QueryType",
    "QueryRewriter",
    "HyDE",
    "SemanticResponseCache",
    "RedisResponseCache",
    "SelfRAGController",
    "RetrievalVerifier",
    "QueryDecomposer",
    "RetrievalFeedback",
    "RequestBudget",
    "PropositionExtractor",
    "PropositionRepository",
    "Proposition",
    "KGExtractor",
    "KnowledgeGraphRepository",
    "KnowledgeGraphTraverser",
    "KGTriple",
    "RequestBudget",
    "fallback",
    "with_fallback",
    "FallbackStrategies",
    "FallbackExhausted",
    "RequestMetrics",
    "AggregateMetrics",
    "get_aggregate_metrics",
    "RetrievalProfile",
    "ProfileName",
    "get_profile",
    "select_profile_for_query",
    "FAST",
    "BALANCED",
    "DEEP",
]