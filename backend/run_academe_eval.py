#!/usr/bin/env python3
"""
Unified RAGAS evaluation for Academe.

Loads the centralized evaluation dataset (evaluation/datasets/academe_eval.json),
runs the RAG pipeline for each question, computes RAGAS metrics, and saves
results to MongoDB.

Usage:
    python run_academe_eval.py [--user-id USER_ID] [--limit N] [--no-save]
"""
import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from core.database import init_database
from core.rag import RAGPipeline
from core.models import UserProfile, LearningLevel, LearningGoal, ExplanationStyle
from core.evaluation.metrics_tracker import MetricsTracker
from bson import ObjectId


def load_eval_dataset(dataset_path: Path) -> dict:
    """Load the academe evaluation dataset from JSON."""
    with open(dataset_path, "r") as f:
        return json.load(f)


def _print_per_chunk_verdicts(per_query: list[dict]) -> None:
    """
    Print per-chunk context precision verdicts for debugging.
    Shows which retrieved chunks RAGAS marks as useful (1) vs not (0).
    Uses same LLM as RAGAS (gpt-4o-mini via llm_factory) for consistency.
    """
    import asyncio
    from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC
    from ragas.llms import llm_factory

    async def _run():
        llm = llm_factory()
        prompt = ContextPrecisionPrompt()
        for i, sample in enumerate(per_query):
            question = sample["question"]
            contexts = sample.get("contexts", [])
            ground_truth = sample.get("ground_truth", "")
            qid = sample.get("id", f"Q{i+1}")
            print()
            print("=" * 70)
            print(f"[DEBUG] Per-chunk verdicts: {qid}")
            print("=" * 70)
            print(f"Q: {question[:80]}{'...' if len(question) > 80 else ''}")
            print()
            verdicts = []
            for j, ctx in enumerate(contexts):
                try:
                    result = await prompt.generate(
                        llm=llm,
                        data=QAC(question=question, context=ctx, answer=ground_truth),
                        callbacks=[],
                    )
                    v = result.verdict if hasattr(result, "verdict") else int(getattr(result, "verdict", 0))
                    verdicts.append(v)
                    symbol = "✓" if v else "✗"
                    preview = (ctx[:120] + "...") if len(ctx) > 120 else ctx
                    print(f"  Chunk {j+1}: [{symbol}] verdict={v}  {preview.replace(chr(10), ' ')}")
                except Exception as e:
                    verdicts.append(0)
                    print(f"  Chunk {j+1}: [✗] error: {e}")
            n_ok = sum(verdicts)
            print(f"  → {n_ok}/{len(contexts)} chunks useful for ground truth")
            print()

    try:
        asyncio.run(_run())
    except Exception as e:
        print(f"[DEBUG] Per-chunk verdicts failed: {e}")


if TYPE_CHECKING:
    from core.documents import DocumentManager


def _resolve_eval_user(
    user_id_arg: str | None,
    doc_manager: "DocumentManager",
) -> str:
    """
    Resolve which user_id to use for evaluation.

    Priority: 1) EVAL_USER_ID env, 2) --user-id arg, 3) auto-detect user with documents.
    Fails with clear error if no user has documents.
    """
    import os
    from core.config.settings import get_settings

    # 1. EVAL_USER_ID from .env (set once, persists)
    settings = get_settings()
    env_user = getattr(settings, "eval_user_id", None) or os.environ.get("EVAL_USER_ID")
    if env_user:
        stats = doc_manager.get_document_stats(env_user)
        if stats.get("ready_documents", 0) > 0:
            return env_user
        # Env user has no docs; fall through to auto-detect

    # 2. Explicit --user-id
    if user_id_arg:
        stats = doc_manager.get_document_stats(user_id_arg)
        if stats.get("ready_documents", 0) > 0:
            return user_id_arg
        print(f"⚠️  User {user_id_arg} has no ready documents.")

    # 3. Auto-detect: first user with documents
    users_with_docs = doc_manager.get_users_with_documents()
    if users_with_docs:
        user_id, count = users_with_docs[0]
        if not user_id_arg:
            print(f"Auto-selected user {user_id} ({count} documents). Set EVAL_USER_ID in .env to override.")
        return user_id

    # No one has documents
    print()
    print("❌ No user has indexed documents. Cannot run evaluation.")
    print()
    print("  1. Upload documents via the web UI or CLI.")
    print("  2. Set EVAL_USER_ID in .env to the user who has documents.")
    print("  3. Or pass --user-id <USER_ID> with the correct account.")
    print()
    sys.exit(1)


def run_evaluation(
    user_id: str,
    limit: int | None = None,
    save_to_mongo: bool = True,
    use_reranking: bool = True,
    top_k: int = 5,
    debug: bool = False,
    expected_docs_filter: list[str] | None = None,
    use_self_rag: bool = True,
    use_decomposition: bool = True,
) -> dict:
    """
    Run full RAGAS evaluation.

    Returns:
        Dict with ragas_scores, per_question results, and metadata.
    """
    dataset_path = Path(__file__).parent / "evaluation" / "datasets" / "academe_eval.json"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    data = load_eval_dataset(dataset_path)
    questions = data["questions"]

    # Filter by expected_documents if specified (e.g. --expected-docs transformer)
    # Only keep questions whose expected_documents intersects with the filter
    if expected_docs_filter:
        filtered = [
            q for q in questions
            if not q.get("expected_documents")  # out-of-scope questions, keep for hallucination test
            or any(d in expected_docs_filter for d in q["expected_documents"])
        ]
        questions = filtered
        print(f"Filtered to {len(questions)} questions matching expected_documents: {expected_docs_filter}")

    if limit:
        questions = questions[:limit]

    print("=" * 70)
    print("ACADEME RAG EVALUATION")
    print("=" * 70)
    print(f"Dataset: {dataset_path.name} (v{data.get('version', '?')})")
    print(f"Questions: {len(questions)}")
    print(f"User ID: {user_id}")
    print()

    init_database()

    # Pre-flight: verify user has indexed documents
    from core.documents import DocumentManager
    doc_manager = DocumentManager()
    stats = doc_manager.get_document_stats(user_id)
    num_docs = stats.get("total_documents", 0)
    num_ready = stats.get("ready_documents", 0)
    if num_docs == 0 or num_ready == 0:
        print("⚠️  WARNING: User has no documents indexed!")
        print(f"   Documents: {num_docs}, Ready: {num_ready}")
        print("   Upload documents to this user first, or use --user-id <ID> for the account that has documents.")
        print("   List users: python -c \"from core.database import init_database, get_database; init_database(); [print(u['_id'], u.get('email','')) for u in get_database().get_database()['users'].find({}, {'_id':1,'email':1})]\"")
        print()

    user = UserProfile(
        id=user_id,
        email="eval@example.com",
        username="evaluator",
        password_hash="",
        learning_level=LearningLevel.INTERMEDIATE,
        learning_goal=LearningGoal.DEEP_LEARNING,
        explanation_style=ExplanationStyle.BALANCED,
    )

    rag = RAGPipeline(
        use_hybrid_search=True,
        use_response_cache=False,  # Disable cache for fair evaluation
        use_self_rag=use_self_rag,
        use_query_decomposition=use_decomposition,
    )

    # Run RAG for each question
    samples_data = []
    for i, q in enumerate(questions, 1):
        question = q["question"]
        print(f"[{i}/{len(questions)}] {question[:60]}...")

        try:
            answer, sources = rag.query_with_context(
                query=question,
                user=user,
                top_k=top_k,
                use_reranking=use_reranking,
            )
            contexts = [s.chunk.content for s in sources] if sources else ["No context retrieved"]
        except Exception as e:
            print(f"    ❌ Error: {e}")
            answer = f"Error: {e}"
            contexts = ["Error"]

        samples_data.append({
            "id": q.get("id", f"Q{i:03d}"),
            "question": question,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": q.get("ground_truth", ""),
            "query_type": q.get("query_type", "unknown"),
            "difficulty": q.get("difficulty", "unknown"),
            "hard_case": q.get("hard_case", "none"),
        })
        print(f"    ✓ {len(answer)} chars, {len(contexts)} chunks")

        # Debug: print first factual question's answer and context for inspection
        if debug and i == 1 and q.get("query_type") == "factual":
            print()
            print("    [DEBUG] Sample answer (first 300 chars):")
            print(f"    {answer[:300]}...")
            print("    [DEBUG] First context chunk (first 200 chars):")
            print(f"    {contexts[0][:200] if contexts else 'None'}...")
            print()

    # Run RAGAS
    print()
    print("Running RAGAS metrics...")

    try:
        from ragas import evaluate, EvaluationDataset, SingleTurnSample
        from ragas.metrics import Faithfulness, ResponseRelevancy, ContextPrecision, ContextRecall

        samples = [
            SingleTurnSample(
                user_input=s["question"],
                response=s["answer"],
                retrieved_contexts=s["contexts"],
                reference=s["ground_truth"],
            )
            for s in samples_data
        ]
        dataset = EvaluationDataset(samples=samples)
        metrics = [Faithfulness(), ResponseRelevancy(), ContextPrecision(), ContextRecall()]

        results = evaluate(dataset=dataset, metrics=metrics)
        df = results.to_pandas()

        # Extract metric columns (exclude content columns)
        content_cols = {"user_input", "response", "retrieved_contexts", "reference"}
        metric_cols = [c for c in df.columns if c not in content_cols]
        aggregated = {col: float(df[col].mean()) for col in metric_cols}

        # Build per-question results
        per_query = []
        for i, row in df.iterrows():
            rec = samples_data[i].copy()
            rec["ragas_scores"] = {col: float(row[col]) for col in metric_cols}
            per_query.append(rec)

        # Debug: per-chunk context precision verdicts (which chunks are useful vs not)
        if debug and per_query:
            _print_per_chunk_verdicts(per_query[:3])

        result = {
            "ragas_scores": aggregated,
            "per_query": per_query,
            "metadata": {
                "dataset_version": data.get("version"),
                "num_questions": len(questions),
                "user_id": user_id,
                "top_k": top_k,
                "use_reranking": use_reranking,
            },
        }

        # Save to MongoDB
        if save_to_mongo:
            tracker = MetricsTracker()
            run_name = f"ragas_academe_eval_{len(questions)}q"
            tracker.log_evaluation_run(
                run_name=run_name,
                aggregated_metrics=aggregated,
                per_query_metrics=per_query,
                config={
                    "evaluation_type": "ragas",
                    "dataset": "academe_eval",
                    "dataset_version": data.get("version"),
                    "num_questions": len(questions),
                    "top_k": top_k,
                    "use_reranking": use_reranking,
                },
            )
            print(f"\n✅ Results saved to MongoDB (run: {run_name})")

        return result

    except ImportError as e:
        print(f"❌ RAGAS not available: {e}")
        print("Install with: pip install 'ragas>=0.2.0,<0.3' datasets pyarrow")
        return {
            "ragas_scores": {},
            "per_query": samples_data,
            "metadata": {"error": str(e)},
        }
    except Exception as e:
        print(f"❌ RAGAS evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "ragas_scores": {},
            "per_query": samples_data,
            "metadata": {"error": str(e)},
        }


def print_results(result: dict) -> None:
    """Print RAGAS results to console."""
    scores = result.get("ragas_scores", {})
    if not scores:
        return

    print()
    print("=" * 70)
    print("📊 RAGAS RESULTS")
    print("=" * 70)
    print()

    for metric, score in scores.items():
        pct = score * 100
        if score >= 0.8:
            rating = "🟢 Excellent"
        elif score >= 0.6:
            rating = "🟡 Good"
        else:
            rating = "🔴 Needs Improvement"
        print(f"  {metric:25s}: {score:.3f} ({pct:.1f}%)  {rating}")

    # Per-query-type breakdown (faithfulness + context_recall for retrieval diagnosis)
    per_query = result.get("per_query", [])
    if per_query and "ragas_scores" in per_query[0]:
        by_type = {}
        for pq in per_query:
            qt = pq.get("query_type", "unknown")
            if qt not in by_type:
                by_type[qt] = {"faithfulness": [], "context_recall": []}
            scores = pq.get("ragas_scores", {})
            by_type[qt]["faithfulness"].append(scores.get("faithfulness", 0))
            by_type[qt]["context_recall"].append(scores.get("context_recall", 0))
        print()
        print("By query type (faithfulness | context_recall):")
        print("  Low context_recall may indicate: ground truth expects info not in docs, or chunk boundaries split key passages.")
        for qt in sorted(by_type.items(), key=lambda x: x[0]):
            qt_name, data = qt
            n = len(data["faithfulness"])
            f_avg = sum(data["faithfulness"]) / n if n else 0
            cr_avg = sum(data["context_recall"]) / n if n else 0
            print(f"  {qt_name:20s}: faithfulness={f_avg:.3f}  context_recall={cr_avg:.3f}  (n={n})")


def main():
    parser = argparse.ArgumentParser(description="Run Academe RAGAS evaluation")
    parser.add_argument(
        "--user-id",
        default=None,
        help="User ID with indexed documents. Auto-detected if unset (or use EVAL_USER_ID in .env).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions (default: all)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save results to MongoDB",
    )
    parser.add_argument(
        "--no-reranking",
        action="store_true",
        help="Disable reranking (faster, lower quality)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of context chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print sample answer and context for first factual question",
    )
    parser.add_argument(
        "--expected-docs",
        nargs="+",
        default=None,
        metavar="DOC",
        help="Only run questions that expect these docs (e.g. --expected-docs transformer). Auto-inferred from corpus if unset.",
    )
    parser.add_argument(
        "--no-self-rag",
        action="store_true",
        help="Disable Self-RAG verification/retry",
    )
    parser.add_argument(
        "--no-decomposition",
        action="store_true",
        help="Disable query decomposition",
    )
    args = parser.parse_args()

    init_database()
    from core.documents import DocumentManager
    doc_manager = DocumentManager()

    user_id = _resolve_eval_user(args.user_id, doc_manager)

    # Auto-infer expected_docs from corpus when not provided
    expected_docs_filter = args.expected_docs
    if expected_docs_filter is None:
        inferred = doc_manager.infer_expected_documents(user_id)
        if inferred:
            expected_docs_filter = list(inferred)
            print(f"Auto-filtering to questions matching corpus: {expected_docs_filter}")
        else:
            print("Could not infer expected_documents from corpus; running all questions.")

    result = run_evaluation(
        user_id=user_id,
        limit=args.limit,
        save_to_mongo=not args.no_save,
        use_reranking=not args.no_reranking,
        top_k=args.top_k,
        debug=args.debug,
        expected_docs_filter=expected_docs_filter,
        use_self_rag=not args.no_self_rag,
        use_decomposition=not args.no_decomposition,
    )

    print_results(result)


if __name__ == "__main__":
    main()
