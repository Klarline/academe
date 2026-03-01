"""
Evaluation module for Academe.

- Level 1: RetrievalEvaluator - P@k, R@k, MRR (fast, no LLM)
- Level 2: RAGASEvaluator - Full system with RAGAS metrics
- MetricsTracker - Log and trend performance over time
"""

from .ragas_evaluator import RAGASEvaluator
from .retrieval_evaluator import RetrievalEvaluator
from .metrics_tracker import MetricsTracker
from .test_data import TEST_QUESTIONS, create_test_dataset, get_test_statistics

__all__ = [
    "RAGASEvaluator",
    "RetrievalEvaluator",
    "MetricsTracker",
    "TEST_QUESTIONS",
    "create_test_dataset",
    "get_test_statistics",
]