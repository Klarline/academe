"""
Evaluation module for Academe 

Uses RAGAS framework for automated quality metrics.
"""

from .ragas_evaluator import RAGASEvaluator
from .test_data import TEST_QUESTIONS, create_test_dataset

__all__ = [
    "RAGASEvaluator",
    "CS6140_TEST_QUESTIONS",
    "create_test_dataset"
]