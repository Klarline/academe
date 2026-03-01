"""
Chunking Strategy Comparison Experiment.

Compare different chunking configurations and measure retrieval
quality with RetrievalEvaluator.

Usage:
    cd backend
    python experiments/chunking_comparison.py --user-id <USER_ID>

Requires:
    - MongoDB running with user documents
    - Pinecone configured (or mock mode)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.documents.chunker import DocumentChunker
from core.evaluation.retrieval_evaluator import RetrievalEvaluator
from core.evaluation.test_data import create_test_dataset
from core.vectors import SemanticSearchService, HybridSearchService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


STRATEGIES = [
    {"name": "small", "size": 512, "overlap": 100, "strategy": "recursive"},
    {"name": "current", "size": 1000, "overlap": 200, "strategy": "recursive"},
    {"name": "large", "size": 1500, "overlap": 300, "strategy": "recursive"},
    {"name": "semantic", "size": 1000, "overlap": 200, "strategy": "semantic"},
]


def analyze_chunking(text: str, strategy: Dict) -> Dict[str, Any]:
    """Chunk text with given strategy and return statistics."""
    chunker = DocumentChunker(
        chunk_size=strategy["size"],
        chunk_overlap=strategy["overlap"],
        strategy=strategy["strategy"],
    )
    chunks = chunker.chunk_document(
        text=text,
        document_id="experiment",
        user_id="experiment",
    )
    sizes = [c.char_count for c in chunks]
    return {
        "num_chunks": len(chunks),
        "avg_size": round(sum(sizes) / len(sizes), 1) if sizes else 0,
        "min_size": min(sizes) if sizes else 0,
        "max_size": max(sizes) if sizes else 0,
    }


def run_retrieval_evaluation(
    user_id: str,
    limit: int = 10,
    k_values: List[int] = [5, 10],
) -> Dict[str, Any]:
    """Run retrieval evaluation with current config."""
    search = HybridSearchService()
    evaluator = RetrievalEvaluator(search_service=search)
    return evaluator.evaluate(
        user_id=user_id,
        limit=limit,
        k_values=k_values,
    )


def run_experiment(
    sample_text: str = None,
    user_id: str = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Run chunking comparison.

    If sample_text is provided: analyzes chunk statistics only.
    If user_id is provided: also runs retrieval evaluation.
    """
    results = {}

    if sample_text is None:
        sample_text = _default_sample_text()

    for strategy in STRATEGIES:
        logger.info(f"Testing strategy: {strategy['name']}")
        stats = analyze_chunking(sample_text, strategy)
        results[strategy["name"]] = {
            "config": strategy,
            "chunking_stats": stats,
        }

    if user_id:
        logger.info("Running retrieval evaluation with current index...")
        eval_result = run_retrieval_evaluation(user_id, limit=limit)
        results["retrieval_evaluation"] = eval_result.get("metrics", {})

    return results


def format_results(results: Dict) -> str:
    """Format experiment results as a table."""
    lines = [
        "=" * 70,
        "CHUNKING STRATEGY COMPARISON",
        "=" * 70,
        "",
        f"{'Strategy':<12} {'Size':>6} {'Overlap':>8} {'Chunks':>7} {'Avg':>6} {'Min':>5} {'Max':>5}",
        "-" * 70,
    ]
    for name in ["small", "current", "large", "semantic"]:
        if name not in results:
            continue
        cfg = results[name]["config"]
        stats = results[name]["chunking_stats"]
        lines.append(
            f"{name:<12} {cfg['size']:>6} {cfg['overlap']:>8} "
            f"{stats['num_chunks']:>7} {stats['avg_size']:>6.0f} "
            f"{stats['min_size']:>5} {stats['max_size']:>5}"
        )

    if "retrieval_evaluation" in results:
        metrics = results["retrieval_evaluation"]
        lines.extend([
            "",
            "--- Retrieval Metrics (current index) ---",
        ])
        for k, v in metrics.items():
            if v is not None:
                lines.append(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return "\n".join(lines)


def _default_sample_text() -> str:
    """Sample ML text for chunking analysis when no user data."""
    return """
Principal Component Analysis (PCA) is a dimensionality reduction technique.
It finds the directions of maximum variance in high-dimensional data and
projects it onto a lower-dimensional subspace.

The key steps in PCA are:
1. Center the data by subtracting the mean
2. Compute the covariance matrix
3. Find eigenvectors and eigenvalues of the covariance matrix
4. Sort eigenvectors by eigenvalues in decreasing order
5. Select top k eigenvectors as principal components
6. Transform the data

Eigenvectors represent the directions of maximum variance. The corresponding
eigenvalues indicate the amount of variance explained by each component.

The bias-variance tradeoff is a fundamental concept in machine learning.
Bias refers to errors from wrong assumptions in the model (underfitting).
Variance refers to sensitivity to small fluctuations in training data (overfitting).

Total error = Bias^2 + Variance + Irreducible noise.

Simple models (linear regression) have high bias but low variance.
Complex models (deep networks) have low bias but high variance.
The goal is to find the model complexity that minimizes total error.

Cross-validation is used to estimate model generalization performance.
In k-fold cross-validation, data is split into k subsets. The model is
trained k times, each time using k-1 folds for training and 1 for validation.

Backpropagation computes gradients of the loss function with respect to
network weights using the chain rule. It propagates errors backwards from
the output layer to update weights efficiently.

Gradient descent optimizers:
- SGD: uses current gradient only
- Momentum: adds fraction of previous update
- Adam: combines momentum with adaptive per-parameter learning rates

L1 regularization (Lasso) adds |w| penalty and promotes sparsity.
L2 regularization (Ridge) adds w^2 penalty and shrinks weights uniformly.
Elastic Net combines both L1 and L2 penalties.
""".strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunking strategy comparison")
    parser.add_argument("--user-id", help="User ID for retrieval evaluation")
    parser.add_argument("--limit", type=int, default=10, help="Number of test queries")
    args = parser.parse_args()

    results = run_experiment(user_id=args.user_id, limit=args.limit)
    print(format_results(results))
    print()

    out_path = Path(__file__).parent / "chunking_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Raw results saved to {out_path}")
