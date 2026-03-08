"""
BM25/Vector Weight Tuning for OpenAI Embeddings.

Uses the centralized academe_eval.json dataset (same as run_academe_eval.py)
to test different BM25/vector fusion weights. Measures keyword hit rate
in retrieved chunks — no LLM calls, runs in seconds.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from core.database import init_database
from core.documents import DocumentManager
from core.vectors import HybridSearchService, SemanticSearchService

WEIGHT_CONFIGS = [
    (0.0, 1.0),  # Pure vector
    (0.1, 0.9),
    (0.2, 0.8),
    (0.3, 0.7),  # Original default
    (0.4, 0.6),
    (0.5, 0.5),
    (0.6, 0.4),
    (0.7, 0.3),  # Heavy BM25
]


def load_questions(dataset_path: Path, expected_docs: list = None, limit: int = None) -> list:
    """Load questions from academe_eval.json, optionally filtering."""
    with open(dataset_path) as f:
        data = json.load(f)
    questions = data["questions"]
    if expected_docs:
        questions = [
            q for q in questions
            if not q.get("expected_documents")
            or any(d in expected_docs for d in q["expected_documents"])
        ]
    if limit:
        questions = questions[:limit]
    return questions


def extract_keywords(ground_truth: str) -> List[str]:
    """Extract key terms from ground truth for hit-rate scoring.
    Pulls numbers, technical terms, and distinctive phrases."""
    keywords = []
    # Extract numbers (e.g. "28.4", "512", "0.1", "6")
    numbers = re.findall(r"\b\d+\.?\d*\b", ground_truth)
    keywords.extend(numbers)
    # Extract technical terms (capitalized or specific patterns)
    tech = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*\b", ground_truth)
    keywords.extend(t.lower() for t in tech if len(t) > 2)
    # Add distinctive lowercase words (>5 chars, not common)
    stopwords = {"which", "about", "their", "there", "these", "those",
                 "would", "could", "should", "being", "between", "through"}
    for word in ground_truth.lower().split():
        clean = re.sub(r"[^a-z0-9]", "", word)
        if len(clean) > 5 and clean not in stopwords:
            keywords.append(clean)
    return list(dict.fromkeys(keywords))[:8]  # Dedupe, cap at 8


def keyword_hit_rate(chunks: list, keywords: list) -> float:
    """What fraction of ground-truth keywords appear in any retrieved chunk?"""
    if not keywords:
        return 0.0
    combined = " ".join(c.chunk.content.lower() for c in chunks)
    hits = sum(1 for kw in keywords if kw.lower() in combined)
    return hits / len(keywords)


def best_chunk_rank(chunks: list, keywords: list) -> int:
    """Rank (1-indexed) of the chunk with highest keyword coverage. -1 if none."""
    best_score = 0.0
    best_rank = -1
    for i, c in enumerate(chunks):
        text = c.chunk.content.lower()
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_rank = i + 1
    return best_rank


def run_search(svc, query, user_id, top_k, use_reranking):
    """Dispatch search to the right method."""
    if isinstance(svc, HybridSearchService):
        if use_reranking:
            return svc.hybrid_search_with_reranking(
                query=query, user_id=user_id, top_k=top_k)
        return svc.hybrid_search(query=query, user_id=user_id, top_k=top_k)
    else:
        if use_reranking:
            return svc.search_with_reranking(
                query=query, user_id=user_id,
                top_k=top_k * 4, rerank_top_k=top_k)
        return svc.search(query=query, user_id=user_id, top_k=top_k)


def evaluate_config(label, svc, user_id, questions, top_k, use_reranking):
    """Evaluate a single config against all questions."""
    total_hr = 0.0
    best_at_1 = 0
    best_in_3 = 0
    latencies = []
    per_query = []

    for q in questions:
        keywords = extract_keywords(q["ground_truth"])
        t0 = time.time()
        results = run_search(svc, q["question"], user_id, top_k, use_reranking)
        lat = time.time() - t0

        hr = keyword_hit_rate(results, keywords)
        br = best_chunk_rank(results, keywords)

        total_hr += hr
        if br == 1: best_at_1 += 1
        if 1 <= br <= 3: best_in_3 += 1
        latencies.append(lat)
        per_query.append({
            "id": q.get("id", ""),
            "question": q["question"][:50],
            "type": q.get("query_type", ""),
            "hit_rate": hr,
            "best_rank": br,
            "keywords": keywords[:5],
            "n_results": len(results),
        })

    n = len(questions)
    return {
        "label": label,
        "avg_hit_rate": total_hr / n if n else 0,
        "best_at_rank1": best_at_1,
        "best_in_top3": best_in_3,
        "avg_latency_ms": (sum(latencies) / n * 1000) if n else 0,
        "n": n,
        "per_query": per_query,
    }


def print_table(all_results, n_questions):
    """Print comparison table."""
    print()
    print("=" * 95)
    print("WEIGHT TUNING RESULTS")
    print("=" * 95)
    hdr = f"{'Config':<22} {'AvgHitRate':>10} {'@Rank1':>8} {'InTop3':>8} {'Latency':>10}"
    print(hdr)
    print("-" * 95)

    best_hr = -1
    best_label = ""
    for r in all_results:
        row = (
            f"{r['label']:<22} "
            f"{r['avg_hit_rate']:>10.3f} "
            f"{r['best_at_rank1']:>6}/{n_questions} "
            f"{r['best_in_top3']:>6}/{n_questions} "
            f"{r['avg_latency_ms']:>8.0f}ms"
        )
        print(row)
        if r["avg_hit_rate"] > best_hr:
            best_hr = r["avg_hit_rate"]
            best_label = r["label"]

    print("-" * 95)
    print(f"Best: {best_label} (hit_rate={best_hr:.3f})")

    # Per-query-type breakdown for best config
    best = next(r for r in all_results if r["label"] == best_label)
    by_type = {}
    for pq in best["per_query"]:
        t = pq["type"]
        by_type.setdefault(t, []).append(pq["hit_rate"])
    print()
    print("Per query type (best config):")
    for t, hrs in sorted(by_type.items()):
        avg = sum(hrs) / len(hrs)
        print(f"  {t:<20s}: avg_hit_rate={avg:.3f} (n={len(hrs)})")

    # Per-query detail for worst performing questions
    worst = sorted(best["per_query"], key=lambda x: x["hit_rate"])[:5]
    print()
    print("Worst 5 questions (best config):")
    print(f"  {'ID':<6} {'Type':<14} {'HitRate':>8} {'BestRk':>7}  Question")
    print("  " + "-" * 80)
    for pq in worst:
        print(
            f"  {pq['id']:<6} {pq['type']:<14} "
            f"{pq['hit_rate']:>8.2f} "
            f"{'N/A' if pq['best_rank'] < 0 else str(pq['best_rank']):>7}  "
            f"{pq['question']}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(description="Tune BM25/vector weights")
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rerank", action="store_true",
                        help="Enable reranking (default: off to isolate weight effect)")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--expected-docs", nargs="+", default=None)
    args = parser.parse_args()

    init_database()
    doc_manager = DocumentManager()

    # Resolve user
    user_id = args.user_id
    if not user_id:
        users = doc_manager.get_users_with_documents()
        if users:
            user_id, count = users[0]
            print(f"Auto-selected user {user_id} ({count} docs)")
        else:
            print("No user with documents found.")
            sys.exit(1)

    # Auto-infer expected docs from corpus
    expected_docs = args.expected_docs
    if expected_docs is None:
        inferred = doc_manager.infer_expected_documents(user_id)
        if inferred:
            expected_docs = list(inferred)
            print(f"Corpus filter: {expected_docs}")

    # Load questions
    dataset_path = Path(__file__).parent.parent / "evaluation" / "datasets" / "academe_eval.json"
    questions = load_questions(dataset_path, expected_docs, args.limit)
    n_q = len(questions)

    mode = "WITH reranking" if args.rerank else "WITHOUT reranking (isolating weight effect)"
    print(f"\n{n_q} questions, top_k={args.top_k}, {mode}\n")

    all_results = []

    # Vector-only baseline
    print("Running: vector-only ...")
    svc = SemanticSearchService()
    r = evaluate_config("vector-only", svc, user_id, questions, args.top_k, args.rerank)
    print(f"  hit_rate={r['avg_hit_rate']:.3f}")
    all_results.append(r)

    # Each weight config
    for bm25_w, vec_w in WEIGHT_CONFIGS:
        label = f"BM25={bm25_w:.1f}/Vec={vec_w:.1f}"
        print(f"Running: {label} ...")
        svc = HybridSearchService(weight_bm25=bm25_w, weight_vector=vec_w)
        r = evaluate_config(label, svc, user_id, questions, args.top_k, args.rerank)
        print(f"  hit_rate={r['avg_hit_rate']:.3f}")
        all_results.append(r)

    print_table(all_results, n_q)


if __name__ == "__main__":
    main()
