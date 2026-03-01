"""
Metrics Tracker for Academe RAG.

Logs retrieval and RAG performance metrics to MongoDB for
trending, regression detection, and performance reports.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from statistics import mean, stdev

from core.database import get_database

logger = logging.getLogger(__name__)

COLLECTION_NAME = "rag_metrics"


class MetricsTracker:
    """
    Track RAG retrieval performance over time.

    Stores per-query metrics in MongoDB and provides aggregated
    reports for regression detection and performance dashboards.
    """

    def __init__(self):
        self.db = get_database()

    def _collection(self):
        return self.db.get_database()[COLLECTION_NAME]

    def log_retrieval(
        self,
        query: str,
        user_id: str,
        results: List[Dict[str, Any]],
        ground_truth: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        search_type: str = "hybrid",
        latency_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log a single retrieval event with metrics.

        Returns:
            Inserted document ID
        """
        doc = {
            "timestamp": datetime.utcnow(),
            "query": query,
            "user_id": user_id,
            "search_type": search_type,
            "num_results": len(results),
            "top_scores": [r.get("score", r.score if hasattr(r, "score") else 0) for r in results[:5]]
            if results else [],
            "latency_ms": latency_ms,
            "ground_truth": ground_truth,
            "metadata": metadata or {},
        }
        if metrics:
            doc["metrics"] = metrics

        try:
            result = self._collection().insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to log retrieval metrics: {e}")
            return ""

    def log_evaluation_run(
        self,
        run_name: str,
        aggregated_metrics: Dict[str, float],
        per_query_metrics: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log a full evaluation run (e.g. from RetrievalEvaluator)."""
        doc = {
            "timestamp": datetime.utcnow(),
            "type": "evaluation_run",
            "run_name": run_name,
            "aggregated": aggregated_metrics,
            "per_query": per_query_metrics,
            "config": config or {},
        }
        try:
            result = self._collection().insert_one(doc)
            logger.info(f"Logged evaluation run '{run_name}': {aggregated_metrics}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to log evaluation run: {e}")
            return ""

    def get_performance_report(self, days: int = 7) -> Dict[str, Any]:
        """
        Aggregate metrics over the last N days.

        Returns:
            Summary with averages, std devs, counts, and trend.
        """
        since = datetime.utcnow() - timedelta(days=days)
        try:
            cursor = self._collection().find({
                "timestamp": {"$gte": since},
                "metrics": {"$exists": True},
            }).sort("timestamp", 1)

            records = list(cursor)
            if not records:
                return {"num_queries": 0, "message": "No data in window"}

            def _safe_mean(key):
                vals = [r["metrics"][key] for r in records if key in r.get("metrics", {})]
                return round(mean(vals), 4) if vals else None

            def _safe_std(key):
                vals = [r["metrics"][key] for r in records if key in r.get("metrics", {})]
                return round(stdev(vals), 4) if len(vals) >= 2 else None

            latencies = [r["latency_ms"] for r in records if r.get("latency_ms") is not None]

            report = {
                "days": days,
                "num_queries": len(records),
                "precision@5": {"mean": _safe_mean("precision@5"), "std": _safe_std("precision@5")},
                "recall@10": {"mean": _safe_mean("recall@10"), "std": _safe_std("recall@10")},
                "mrr": {"mean": _safe_mean("mrr"), "std": _safe_std("mrr")},
                "latency_ms": {
                    "mean": round(mean(latencies), 1) if latencies else None,
                    "std": round(stdev(latencies), 1) if len(latencies) >= 2 else None,
                },
                "trend": self._calculate_trend(records),
            }
            return report

        except Exception as e:
            logger.error(f"Failed to get performance report: {e}")
            return {"error": str(e)}

    def get_evaluation_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent evaluation runs for comparison."""
        try:
            cursor = self._collection().find(
                {"type": "evaluation_run"},
            ).sort("timestamp", -1).limit(limit)
            return [
                {
                    "run_name": r.get("run_name"),
                    "timestamp": r.get("timestamp"),
                    "aggregated": r.get("aggregated"),
                }
                for r in cursor
            ]
        except Exception as e:
            logger.error(f"Failed to get evaluation runs: {e}")
            return []

    def _calculate_trend(self, records: List[Dict]) -> Dict[str, str]:
        """Compare first-half vs second-half of records to detect trend."""
        if len(records) < 4:
            return {"direction": "insufficient_data"}

        mid = len(records) // 2
        first_half = records[:mid]
        second_half = records[mid:]

        def _half_mean(half, key):
            vals = [r["metrics"][key] for r in half if key in r.get("metrics", {})]
            return mean(vals) if vals else 0

        p5_first = _half_mean(first_half, "precision@5")
        p5_second = _half_mean(second_half, "precision@5")

        if p5_second > p5_first + 0.02:
            direction = "improving"
        elif p5_second < p5_first - 0.02:
            direction = "degrading"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "precision@5_first_half": round(p5_first, 4),
            "precision@5_second_half": round(p5_second, 4),
        }

    def format_report(self, report: Dict[str, Any]) -> str:
        """Format report for display."""
        if report.get("num_queries", 0) == 0:
            return "No metrics data available."

        lines = [
            "=== RAG Performance Report ===",
            f"Period: last {report.get('days', 7)} days",
            f"Queries: {report['num_queries']}",
            "",
        ]

        for metric in ["precision@5", "recall@10", "mrr"]:
            data = report.get(metric, {})
            m = data.get("mean")
            s = data.get("std")
            if m is not None:
                line = f"  {metric}: {m:.4f}"
                if s is not None:
                    line += f" +/- {s:.4f}"
                lines.append(line)

        lat = report.get("latency_ms", {})
        if lat.get("mean") is not None:
            lines.append(f"  Latency: {lat['mean']:.0f}ms +/- {lat.get('std', 0):.0f}ms")

        trend = report.get("trend", {})
        lines.append(f"\n  Trend: {trend.get('direction', 'unknown')}")

        return "\n".join(lines)
