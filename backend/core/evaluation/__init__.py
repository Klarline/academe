"""
Evaluation module for Academe 

Uses RAGAS framework for automated quality metrics.
"""

from .ragas_evaluator import RAGASEvaluator
from .test_data import TEST_QUESTIONS, create_test_dataset, get_test_statistics

__all__ = [
    "RAGASEvaluator",
    "TEST_QUESTIONS",
    "create_test_dataset",
    "get_test_statistics"
]