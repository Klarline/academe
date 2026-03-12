"""
RAG Analytics module.

Uses MongoDB aggregation pipelines for server-side grouping/counting,
then Pandas for trend detection, rolling averages, and report formatting.
Makes "Pandas for data analysis and opportunity identification" defensible.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database import get_database
from core.rag.adaptive_retrieval import classify_query

logger = logging.getLogger(__name__)

FEEDBACK_COLLECTION = "retrieval_feedback"
METRICS_COLLECTION = "rag_metrics"


class RAGAnalytics:
    """
    Analyze RAG performance from MongoDB data.

    Uses aggregation pipelines for heavy lifting, Pandas for analysis.
    """

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        if self._db is None:
            from core.database import get_database
            self._db = get_database()
        return self._db

    def _feedback_collection(self):
        return self.db.get_database()[FEEDBACK_COLLECTION]

    def _metrics_collection(self):
        return self.db.get_database()[METRICS_COLLECTION]

    def satisfaction_trends(
        self,
        days: int = 30,
        user_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Group feedback by day, compute satisfaction rate and rolling average.

        Uses MongoDB $group for aggregation, Pandas for trend detection.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        match = {"created_at": {"$gte": cutoff}}
        if user_id:
            match["user_id"] = user_id

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$toDate": {"$multiply": ["$created_at", 1000]}},
                        }
                    },
                    "positive": {"$sum": {"$cond": [{"$gt": ["$rating", 0]}, 1, 0]}},
                    "negative": {"$sum": {"$cond": [{"$lt": ["$rating", 0]}, 1, 0]}},
                    "total": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        try:
            cursor = self._feedback_collection().aggregate(pipeline)
            rows = list(cursor)
        except Exception as e:
            logger.error(f"Satisfaction trends aggregation failed: {e}")
            return pd.DataFrame(columns=["date", "positive", "negative", "total", "rate", "rolling_rate"])

        if not rows:
            return pd.DataFrame(columns=["date", "positive", "negative", "total", "rate", "rolling_rate"])

        df = pd.DataFrame([
            {
                "date": r["_id"],
                "positive": r["positive"],
                "negative": r["negative"],
                "total": r["total"],
                "rate": r["positive"] / r["total"] if r["total"] else 0,
            }
            for r in rows
        ])
        df["rolling_rate"] = df["rate"].rolling(window=7, min_periods=1).mean()
        return df

    def weak_documents(
        self,
        user_id: Optional[str] = None,
        min_negative: int = 2,
    ) -> pd.DataFrame:
        """
        Aggregate negative feedback by document, rank by failure frequency.
        """
        match: Dict[str, Any] = {"rating": -1}
        if user_id:
            match["user_id"] = user_id

        pipeline = [
            {"$match": match},
            {"$unwind": {"path": "$sources", "preserveNullAndEmptyArrays": False}},
            {
                "$group": {
                    "_id": {"$ifNull": ["$sources.document_id", "$sources.document"]},
                    "negative_count": {"$sum": 1},
                    "queries": {"$push": "$query"},
                }
            },
            {"$match": {"negative_count": {"$gte": min_negative}}},
            {"$sort": {"negative_count": -1}},
            {"$limit": 50},
        ]

        try:
            cursor = self._feedback_collection().aggregate(pipeline)
            rows = list(cursor)
        except Exception as e:
            logger.error(f"Weak documents aggregation failed: {e}")
            return pd.DataFrame(columns=["document_id", "negative_count", "sample_queries"])

        if not rows:
            return pd.DataFrame(columns=["document_id", "negative_count", "sample_queries"])

        return pd.DataFrame([
            {
                "document_id": r["_id"] or "unknown",
                "negative_count": r["negative_count"],
                "sample_queries": r["queries"][:3],
            }
            for r in rows
        ])

    def query_type_performance(
        self,
        user_id: Optional[str] = None,
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Cluster negative feedback by query type (definition/comparison/code/procedural).
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        match: Dict[str, Any] = {"created_at": {"$gte": cutoff}}
        if user_id:
            match["user_id"] = user_id

        try:
            cursor = self._feedback_collection().find(match, {"query": 1, "rating": 1})
            entries = list(cursor)
        except Exception as e:
            logger.error(f"Query type fetch failed: {e}")
            return pd.DataFrame()

        if not entries:
            return pd.DataFrame(columns=["query_type", "total", "positive", "negative", "sat_rate"])

        # Classify each query and aggregate in Python (query count is typically small)
        type_counts: Dict[str, Dict[str, int]] = {}
        for e in entries:
            qtype = classify_query(e.get("query", ""))
            if qtype not in type_counts:
                type_counts[qtype] = {"total": 0, "positive": 0, "negative": 0}
            type_counts[qtype]["total"] += 1
            if e.get("rating", 0) > 0:
                type_counts[qtype]["positive"] += 1
            elif e.get("rating", 0) < 0:
                type_counts[qtype]["negative"] += 1

        df = pd.DataFrame([
            {
                "query_type": k,
                "total": v["total"],
                "positive": v["positive"],
                "negative": v["negative"],
                "sat_rate": v["positive"] / v["total"] if v["total"] else 0,
            }
            for k, v in type_counts.items()
        ])
        if not df.empty:
            df = df.sort_values("total", ascending=False)
        return df

    def stage_value_summary(self) -> pd.DataFrame:
        """
        Pull from rag_metrics: stage-level enabled/ran/changed_input/changed_output.
        Returns empty DataFrame if no stage data exists (evaluation-only metrics).
        """
        try:
            cursor = self._metrics_collection().find(
                {"type": {"$ne": "evaluation_run"}},
                {"metadata": 1, "metrics": 1}
            ).limit(1000)
            records = list(cursor)
        except Exception as e:
            logger.error(f"Stage metrics fetch failed: {e}")
            return pd.DataFrame()

        if not records:
            return pd.DataFrame(columns=["stage", "enabled_pct", "ran_pct", "changed_input_pct", "changed_output_pct"])

        # Aggregate stage counters from metadata/metrics if present
        stage_totals: Dict[str, Dict[str, int]] = {}
        for r in records:
            meta = r.get("metadata", r.get("metrics", {}))
            if not isinstance(meta, dict):
                continue
            for key, val in meta.items():
                if "." in key and isinstance(val, (int, float)):
                    stage, metric = key.split(".", 1)
                    if stage not in stage_totals:
                        stage_totals[stage] = {"enabled": 0, "ran": 0, "changed_input": 0, "changed_output": 0}
                    if metric in stage_totals[stage]:
                        stage_totals[stage][metric] += int(val)

        if not stage_totals:
            return pd.DataFrame(columns=["stage", "enabled_pct", "ran_pct", "changed_input_pct", "changed_output_pct"])

        n = len(records)
        return pd.DataFrame([
            {
                "stage": k,
                "enabled_pct": v.get("enabled", 0) / n * 100 if n else 0,
                "ran_pct": v.get("ran", 0) / n * 100 if n else 0,
                "changed_input_pct": v.get("changed_input", 0) / n * 100 if n else 0,
                "changed_output_pct": v.get("changed_output", 0) / n * 100 if n else 0,
            }
            for k, v in stage_totals.items()
        ])

    def cache_performance(self) -> Dict[str, Any]:
        """
        Return process-global cache hit/miss metrics.

        Reads from Prometheus counters (shared across all pipeline instances).
        """
        from core.rag.response_cache import get_cache_metrics
        return get_cache_metrics()

    def celery_task_metrics(self) -> Dict[str, Any]:
        """
        Return process-global Celery task success/failure/retry counters.

        Reads from Prometheus counters via celery_monitoring module.
        """
        from core.celery_monitoring import get_celery_metrics
        return get_celery_metrics()

    def task_failure_summary(
        self,
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Aggregate task failures from MongoDB by task name.

        Returns DataFrame with task_name, failure_count, last_exception,
        and most recent failure timestamp.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {
                "$group": {
                    "_id": "$task_name",
                    "failure_count": {"$sum": 1},
                    "last_exception": {"$last": "$exception_message"},
                    "last_failure": {"$max": "$created_at"},
                    "avg_retries": {"$avg": "$retries"},
                }
            },
            {"$sort": {"failure_count": -1}},
            {"$limit": 20},
        ]

        try:
            collection = self.db.get_database()["task_failures"]
            rows = list(collection.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Task failure aggregation failed: {e}")
            return pd.DataFrame(columns=["task_name", "failure_count", "last_exception", "avg_retries"])

        if not rows:
            return pd.DataFrame(columns=["task_name", "failure_count", "last_exception", "avg_retries"])

        return pd.DataFrame([
            {
                "task_name": r["_id"] or "unknown",
                "failure_count": r["failure_count"],
                "last_exception": (r.get("last_exception") or "")[:200],
                "avg_retries": round(r.get("avg_retries", 0), 1),
            }
            for r in rows
        ])

    def generate_report(
        self,
        days: int = 30,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Produce structured report dict for dashboard or CLI.
        """
        satisfaction_df = self.satisfaction_trends(days=days, user_id=user_id)
        weak_df = self.weak_documents(user_id=user_id)
        query_type_df = self.query_type_performance(user_id=user_id, days=days)
        stage_df = self.stage_value_summary()
        cache_stats = self.cache_performance()
        celery_stats = self.celery_task_metrics()
        task_failures_df = self.task_failure_summary(days=days)

        # Trend detection: declining if rolling rate drops > 5% over last 7 days
        declining = False
        if len(satisfaction_df) >= 7:
            recent = satisfaction_df["rolling_rate"].tail(7)
            if recent.iloc[0] - recent.iloc[-1] > 0.05:
                declining = True

        recommendations: List[str] = []
        if declining:
            recommendations.append("Satisfaction trend is declining; review recent retrieval changes.")
        if not weak_df.empty:
            top_weak = weak_df.iloc[0]
            recommendations.append(
                f"Re-chunk or improve document '{top_weak['document_id']}' "
                f"({int(top_weak['negative_count'])} negative feedbacks)."
            )
        if not query_type_df.empty:
            worst = query_type_df.loc[query_type_df["sat_rate"].idxmin()]
            recommendations.append(
                f"Query type '{worst['query_type']}' underperforms "
                f"(sat_rate={worst['sat_rate']:.2f}); consider retrieval tuning."
            )
        if cache_stats["total_lookups"] >= 20 and cache_stats["hit_rate"] < 0.10:
            recommendations.append(
                f"Cache hit rate is low ({cache_stats['hit_rate']:.1%} over "
                f"{cache_stats['total_lookups']} lookups); users may be asking "
                f"diverse questions or cache TTL may be too short."
            )
        if not task_failures_df.empty:
            top_fail = task_failures_df.iloc[0]
            recommendations.append(
                f"Celery task '{top_fail['task_name']}' has failed "
                f"{int(top_fail['failure_count'])} times in the last {days} days; "
                f"last error: {top_fail['last_exception'][:100]}"
            )
        if celery_stats["total_failure"] > 0 and celery_stats["total_success"] > 0:
            fail_rate = celery_stats["total_failure"] / (
                celery_stats["total_success"] + celery_stats["total_failure"]
            )
            if fail_rate > 0.05:
                recommendations.append(
                    f"Celery task failure rate is {fail_rate:.1%}; "
                    f"investigate worker health and external dependencies."
                )

        return {
            "period_days": days,
            "user_id": user_id,
            "satisfaction_trends": satisfaction_df.to_dict(orient="records") if not satisfaction_df.empty else [],
            "weak_documents": weak_df.to_dict(orient="records") if not weak_df.empty else [],
            "query_type_performance": query_type_df.to_dict(orient="records") if not query_type_df.empty else [],
            "stage_value_summary": stage_df.to_dict(orient="records") if not stage_df.empty else [],
            "cache_performance": cache_stats,
            "celery_task_metrics": celery_stats,
            "task_failures": task_failures_df.to_dict(orient="records") if not task_failures_df.empty else [],
            "satisfaction_declining": declining,
            "recommendations": recommendations,
        }
