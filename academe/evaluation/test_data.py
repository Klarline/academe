"""
Test Dataset for RAGAS Evaluation -  Machine Learning

Contains test questions from common topics including:
- Linear Algebra & PCA
- Probability & Statistics
- Machine Learning Fundamentals
- Neural Networks
- Optimization
"""

from typing import List, Dict, Any


TEST_QUESTIONS = [
    # ========== Linear Algebra & PCA ==========
    {
        "question": "What are eigenvectors and why are they important in PCA?",
        "topic": "linear_algebra",
        "difficulty": "intermediate",
        "ground_truth": "Eigenvectors are vectors that don't change direction when a linear transformation is applied, only scaled by eigenvalues. In PCA, eigenvectors of the covariance matrix represent the principal components - the directions of maximum variance in the data. The eigenvector with the largest eigenvalue points in the direction of greatest variance.",
        "contexts": [
            "PCA finds the axes along which data varies most",
            "Eigenvectors of covariance matrix are principal components"
        ]
    },
    {
        "question": "Write Python code to compute PCA from scratch without using sklearn",
        "topic": "pca",
        "difficulty": "advanced",
        "ground_truth": """def pca(X, n_components):
    # Center the data
    X_centered = X - np.mean(X, axis=0)
    # Compute covariance matrix
    cov_matrix = np.cov(X_centered.T)
    # Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
    # Sort by eigenvalues
    idx = eigenvalues.argsort()[::-1]
    eigenvectors = eigenvectors[:, idx]
    # Select top n_components
    components = eigenvectors[:, :n_components]
    # Transform data
    X_pca = X_centered @ components
    return X_pca, components""",
        "contexts": []
    },
    {
        "question": "Explain the difference between eigendecomposition and SVD",
        "topic": "linear_algebra",
        "difficulty": "advanced",
        "ground_truth": "Eigendecomposition works only on square matrices and decomposes A = QΛQ^(-1). SVD works on any matrix and decomposes A = UΣV^T. SVD is more numerically stable and can handle rectangular matrices. For symmetric matrices, SVD and eigendecomposition are related: the singular values are the absolute values of eigenvalues.",
        "contexts": []
    },

    # ========== Probability & Statistics ==========
    {
        "question": "Explain Bayes' theorem with a medical diagnosis example",
        "topic": "probability",
        "difficulty": "beginner",
        "ground_truth": "Bayes' theorem: P(A|B) = P(B|A) * P(A) / P(B). Example: If a disease affects 1% of people (P(disease)), a test is 99% accurate for sick people (P(positive|disease)), and 95% accurate for healthy people, we can calculate P(disease|positive) = 0.99 * 0.01 / P(positive) ≈ 16.7%, showing most positive tests are false positives due to low base rate.",
        "contexts": []
    },
    {
        "question": "What is the difference between MLE and MAP estimation?",
        "topic": "probability",
        "difficulty": "intermediate",
        "ground_truth": "MLE (Maximum Likelihood Estimation) finds parameters that maximize P(data|parameters), treating parameters as fixed unknown values. MAP (Maximum A Posteriori) maximizes P(parameters|data) = P(data|parameters) * P(parameters) / P(data), incorporating prior beliefs about parameters. MAP includes a prior distribution and reduces to MLE with uniform prior.",
        "contexts": []
    },
    {
        "question": "Derive the variance of the sum of two random variables",
        "topic": "probability",
        "difficulty": "intermediate",
        "ground_truth": "Var(X + Y) = E[(X+Y)²] - E[X+Y]² = E[X²] + 2E[XY] + E[Y²] - (E[X] + E[Y])² = E[X²] - E[X]² + E[Y²] - E[Y]² + 2(E[XY] - E[X]E[Y]) = Var(X) + Var(Y) + 2Cov(X,Y). If X and Y are independent, Cov(X,Y) = 0, so Var(X+Y) = Var(X) + Var(Y).",
        "contexts": []
    },

    # ========== Machine Learning Fundamentals ==========
    {
        "question": "Explain the bias-variance tradeoff in machine learning",
        "topic": "ml_fundamentals",
        "difficulty": "intermediate",
        "ground_truth": "The bias-variance tradeoff describes the balance between two sources of error: Bias (error from wrong assumptions, causing underfitting) and Variance (error from sensitivity to training data, causing overfitting). Total error = Bias² + Variance + Irreducible noise. Simple models have high bias, low variance. Complex models have low bias, high variance. The goal is finding the sweet spot that minimizes total error.",
        "contexts": []
    },
    {
        "question": "What is cross-validation and why is it important?",
        "topic": "ml_fundamentals",
        "difficulty": "beginner",
        "ground_truth": "Cross-validation is a technique to assess model generalization by partitioning data into folds, training on k-1 folds and validating on the remaining fold, repeating k times. It provides better estimates of model performance than a single train-test split, helps detect overfitting, and uses data more efficiently for both training and validation.",
        "contexts": []
    },
    {
        "question": "Implement gradient descent for linear regression in Python",
        "topic": "optimization",
        "difficulty": "intermediate",
        "ground_truth": """def gradient_descent(X, y, learning_rate=0.01, epochs=1000):
    m, n = X.shape
    theta = np.zeros(n)

    for _ in range(epochs):
        predictions = X @ theta
        errors = predictions - y
        gradient = (1/m) * X.T @ errors
        theta = theta - learning_rate * gradient

    return theta""",
        "contexts": []
    },

    # ========== Neural Networks ==========
    {
        "question": "Explain backpropagation in neural networks",
        "topic": "neural_networks",
        "difficulty": "intermediate",
        "ground_truth": "Backpropagation computes gradients of the loss with respect to weights using the chain rule. It works backwards from output to input: 1) Forward pass computes activations, 2) Compute output error, 3) Propagate error backwards through layers using derivatives of activation functions, 4) Update weights using gradients. Key insight: reuse computed gradients for efficiency.",
        "contexts": []
    },
    {
        "question": "What is the vanishing gradient problem and how can it be addressed?",
        "topic": "neural_networks",
        "difficulty": "advanced",
        "ground_truth": "Vanishing gradient occurs when gradients become exponentially small in deep networks, preventing lower layers from learning. Caused by: sigmoid/tanh saturating, repeated multiplication of small values. Solutions: ReLU activation (non-saturating), batch normalization (stabilizes distributions), residual connections (skip connections), LSTM/GRU for RNNs, careful weight initialization (Xavier/He).",
        "contexts": []
    },

    # ========== Optimization ==========
    {
        "question": "Compare SGD, Momentum, and Adam optimizers",
        "topic": "optimization",
        "difficulty": "intermediate",
        "ground_truth": "SGD updates weights using current gradient only. Momentum adds fraction of previous update, accelerating convergence and dampening oscillations. Adam combines momentum with adaptive learning rates per parameter using running averages of gradients (momentum) and squared gradients (RMSprop). Adam often converges faster but SGD sometimes generalizes better.",
        "contexts": []
    },
    {
        "question": "Explain L1 vs L2 regularization and their effects",
        "topic": "regularization",
        "difficulty": "intermediate",
        "ground_truth": "L1 (Lasso) adds |w| penalty, promotes sparsity by driving weights to exactly zero, useful for feature selection. L2 (Ridge) adds w² penalty, shrinks weights uniformly but keeps them non-zero, handles correlated features better. L1 produces non-differentiable objective at zero, L2 has closed-form solution. Elastic Net combines both.",
        "contexts": []
    },

    # ========== Clustering ==========
    {
        "question": "How does k-means clustering work and what are its limitations?",
        "topic": "clustering",
        "difficulty": "beginner",
        "ground_truth": "K-means: 1) Initialize k centroids randomly, 2) Assign points to nearest centroid, 3) Update centroids as mean of assigned points, 4) Repeat until convergence. Limitations: Assumes spherical clusters, sensitive to initialization, requires specifying k, sensitive to outliers, struggles with varying densities/sizes, only finds linear boundaries.",
        "contexts": []
    },

    # ========== Dimensionality Reduction ==========
    {
        "question": "Compare PCA and t-SNE for dimensionality reduction",
        "topic": "dimensionality_reduction",
        "difficulty": "advanced",
        "ground_truth": "PCA is linear, preserves global structure, fast, deterministic, preserves distances/variance. t-SNE is non-linear, preserves local neighborhoods, slow, stochastic, good for visualization. PCA finds orthogonal axes of maximum variance. t-SNE minimizes KL divergence between high-D and low-D probability distributions. Use PCA for preprocessing, t-SNE for 2D/3D visualization.",
        "contexts": []
    },

    # ========== Practice Problems ==========
    {
        "question": "Generate a quiz question about gradient descent",
        "topic": "practice",
        "difficulty": "intermediate",
        "ground_truth": "Question: If the learning rate in gradient descent is too large, what problem might occur? A) Convergence will be very slow, B) The algorithm might overshoot the minimum and diverge, C) The gradient will vanish, D) The model will overfit. Answer: B - Large learning rates can cause overshooting and oscillation around or away from the minimum.",
        "contexts": []
    },
    {
        "question": "Create a practice problem for calculating entropy",
        "topic": "practice",
        "difficulty": "beginner",
        "ground_truth": "Problem: Calculate the entropy of a coin with P(heads) = 0.7. Solution: H = -[P(heads)×log₂(P(heads)) + P(tails)×log₂(P(tails))] = -[0.7×log₂(0.7) + 0.3×log₂(0.3)] = -[0.7×(-0.515) + 0.3×(-1.737)] = 0.361 + 0.521 = 0.882 bits",
        "contexts": []
    },

    # ========== Ensemble Methods ==========
    {
        "question": "Explain how Random Forests reduce overfitting compared to decision trees",
        "topic": "ensemble_methods",
        "difficulty": "intermediate",
        "ground_truth": "Random Forests reduce overfitting through: 1) Bagging - training trees on bootstrap samples reduces variance, 2) Feature randomness - considering random feature subsets at each split decorrelates trees, 3) Averaging - combining many trees smooths out individual tree errors. No pruning needed as ensemble averaging handles overfitting.",
        "contexts": []
    },

    # ========== Evaluation Metrics ==========
    {
        "question": "When should you use ROC-AUC vs precision-recall curves?",
        "topic": "evaluation",
        "difficulty": "intermediate",
        "ground_truth": "Use ROC-AUC for balanced datasets or when both classes are equally important. Use precision-recall for imbalanced datasets where positive class is rare and more important. ROC can be overly optimistic on imbalanced data as true negative rate is inflated. PR curves focus on positive class performance.",
        "contexts": []
    },

    # ========== Feature Engineering ==========
    {
        "question": "What is feature scaling and why is it important?",
        "topic": "feature_engineering",
        "difficulty": "beginner",
        "ground_truth": "Feature scaling normalizes features to similar ranges. Important because: algorithms using distance metrics (KNN, SVM, K-means) are sensitive to scale, gradient descent converges faster with scaled features, regularization affects features equally when scaled. Methods: StandardScaler (z-score), MinMaxScaler (0-1 range), RobustScaler (handles outliers).",
        "contexts": []
    }
]


def create_test_dataset(
    topics: List[str] = None,
    difficulties: List[str] = None,
    limit: int = None
) -> List[Dict[str, Any]]:
    """
    Create a filtered test dataset.

    Args:
        topics: List of topics to include (None = all)
        difficulties: List of difficulty levels (None = all)
        limit: Maximum number of questions (None = all)

    Returns:
        Filtered list of test questions
    """
    dataset = TEST_QUESTIONS.copy()

    # Filter by topics
    if topics:
        dataset = [q for q in dataset if q.get('topic') in topics]

    # Filter by difficulty
    if difficulties:
        dataset = [q for q in dataset if q.get('difficulty') in difficulties]

    # Apply limit
    if limit and limit < len(dataset):
        dataset = dataset[:limit]

    return dataset


def get_test_statistics() -> Dict[str, Any]:
    """Get statistics about the test dataset."""
    topics = {}
    difficulties = {}

    for question in TEST_QUESTIONS:
        # Count topics
        topic = question.get('topic', 'unknown')
        topics[topic] = topics.get(topic, 0) + 1

        # Count difficulties
        difficulty = question.get('difficulty', 'unknown')
        difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

    return {
        'total_questions': len(TEST_QUESTIONS),
        'topics': topics,
        'difficulties': difficulties,
        'has_ground_truth': sum(1 for q in TEST_QUESTIONS if q.get('ground_truth')),
        'has_contexts': sum(1 for q in TEST_QUESTIONS if q.get('contexts'))
    }


# Export test data
__all__ = [
    "TEST_QUESTIONS",
    "create_test_dataset",
    "get_test_statistics"
]