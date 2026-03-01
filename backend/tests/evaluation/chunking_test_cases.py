"""
Chunking evaluation test cases for Academe RAG.

Use with RetrievalEvaluator when you have a test document with known structure.
Format: query, ground_truth, and optionally relevant_chunk_ids (document_id + chunk_index)
for computing recall.

When relevant_chunk_ids is absent, RetrievalEvaluator uses content overlap with
ground_truth to judge relevance (precision@k, MRR only).
"""

from typing import List, Dict, Any

# Test cases for ML concept retrieval
# Add relevant_chunk_ids when you have a seeded test document
CHUNKING_TEST_CASES: List[Dict[str, Any]] = [
    {
        "query": "What is PCA?",
        "ground_truth": "Principal Component Analysis is a dimensionality reduction technique that finds the axes of maximum variance in the data. It uses eigenvectors of the covariance matrix.",
        "topic": "linear_algebra",
        "document_id": "ml_textbook_001",
        # "relevant_chunk_ids": [{"document_id": "ml_textbook_001", "chunk_index": 0}, ...],
    },
    {
        "query": "What are eigenvectors and why are they important in PCA?",
        "ground_truth": "Eigenvectors are vectors that don't change direction when a linear transformation is applied. In PCA, eigenvectors of the covariance matrix represent the principal components.",
        "topic": "linear_algebra",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "Explain the bias-variance tradeoff",
        "ground_truth": "The bias-variance tradeoff describes the balance between bias (underfitting) and variance (overfitting). Simple models have high bias, complex models have high variance.",
        "topic": "ml_fundamentals",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "What is cross-validation?",
        "ground_truth": "Cross-validation partitions data into folds, training on k-1 and validating on the remaining fold. It provides better estimates of generalization.",
        "topic": "ml_fundamentals",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "Explain backpropagation in neural networks",
        "ground_truth": "Backpropagation computes gradients using the chain rule, propagating error backwards from output to input to update weights.",
        "topic": "neural_networks",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "Compare SGD, Momentum, and Adam optimizers",
        "ground_truth": "SGD uses current gradient. Momentum adds fraction of previous update. Adam combines momentum with adaptive learning rates per parameter.",
        "topic": "optimization",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "L1 vs L2 regularization",
        "ground_truth": "L1 (Lasso) promotes sparsity. L2 (Ridge) shrinks weights uniformly. Elastic Net combines both.",
        "topic": "regularization",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "How does k-means clustering work?",
        "ground_truth": "K-means initializes k centroids, assigns points to nearest centroid, updates centroids as mean of assigned points, repeats until convergence.",
        "topic": "clustering",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "PCA vs t-SNE for dimensionality reduction",
        "ground_truth": "PCA is linear and preserves global structure. t-SNE is non-linear and preserves local neighborhoods, good for visualization.",
        "topic": "dimensionality_reduction",
        "document_id": "ml_textbook_001",
    },
    {
        "query": "What is feature scaling and why is it important?",
        "ground_truth": "Feature scaling normalizes features to similar ranges. Important for distance-based algorithms and gradient descent convergence.",
        "topic": "feature_engineering",
        "document_id": "ml_textbook_001",
    },
]
