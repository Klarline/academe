"""
Retrieval feedback loop.

Records user feedback (thumbs up/down) on RAG answers and uses it to:
1. Identify weak queries and documents
2. Track retrieval quality trends
3. Provide data for future retrieval tuning

Stores feedback in MongoDB for persistence.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RetrievalFeedback:
    """
    Record and analyze user feedback on RAG responses.

    Each feedback entry captures the query, retrieved chunks, answer,
    and the user's rating, enabling offline analysis of retrieval quality.
    """

    COLLECTION_NAME = "retrieval_feedback"

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        if self._db is None:
            from core.database import get_database
            self._db = get_database()
        return self._db

    def record(
        self,
        user_id: str,
        query: str,
        answer: str,
        sources: List[Dict[str, Any]],
        rating: int,
        comment: Optional[str] = None,
    ) -> str:
        """
        Record feedback on a RAG response.

        Args:
            user_id: User who provided feedback.
            query: The original query.
            answer: The generated answer.
            sources: List of source info dicts (document, page, score, excerpt).
            rating: 1 (thumbs up) or -1 (thumbs down).
            comment: Optional user comment.

        Returns:
            Feedback entry ID.
        """
        entry = {
            "user_id": user_id,
            "query": query,
            "answer_excerpt": answer[:500],
            "sources": sources[:5],
            "rating": rating,
            "comment": comment,
            "created_at": time.time(),
        }

        try:
            collection = self.db.get_database()[self.COLLECTION_NAME]
            result = collection.insert_one(entry)
            feedback_id = str(result.inserted_id)
            logger.info(
                f"Feedback recorded: {'👍' if rating > 0 else '👎'} "
                f"for query '{query[:40]}' (id={feedback_id})"
            )
            return feedback_id
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return ""

    def get_negative_feedback(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent negative feedback entries.

        Useful for identifying queries where retrieval failed.

        Args:
            user_id: Filter by user (optional).
            limit: Maximum entries.

        Returns:
            List of negative feedback entries.
        """
        try:
            collection = self.db.get_database()[self.COLLECTION_NAME]
            query_filter: Dict[str, Any] = {"rating": -1}
            if user_id:
                query_filter["user_id"] = user_id
            cursor = collection.find(query_filter).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get negative feedback: {e}")
            return []

    def get_feedback_stats(
        self,
        user_id: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Aggregate feedback statistics.

        Args:
            user_id: Filter by user (optional).
            days: Look-back window in days.

        Returns:
            Stats dict with counts, satisfaction rate, and weak queries.
        """
        try:
            collection = self.db.get_database()[self.COLLECTION_NAME]
            cutoff = time.time() - (days * 86400)
            query_filter: Dict[str, Any] = {"created_at": {"$gte": cutoff}}
            if user_id:
                query_filter["user_id"] = user_id

            entries = list(collection.find(query_filter))
            if not entries:
                return {"total": 0, "positive": 0, "negative": 0, "satisfaction_rate": None}

            positive = sum(1 for e in entries if e.get("rating", 0) > 0)
            negative = sum(1 for e in entries if e.get("rating", 0) < 0)
            total = len(entries)

            neg_queries = [
                e["query"] for e in entries
                if e.get("rating", 0) < 0 and "query" in e
            ]

            return {
                "total": total,
                "positive": positive,
                "negative": negative,
                "satisfaction_rate": round(positive / total, 3) if total else None,
                "recent_negative_queries": neg_queries[:10],
            }
        except Exception as e:
            logger.error(f"Failed to get feedback stats: {e}")
            return {"total": 0, "error": str(e)}

    def get_weak_documents(
        self,
        user_id: Optional[str] = None,
        min_negative: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Identify documents that frequently appear in negatively-rated responses.

        These may need re-chunking, better metadata, or removal.

        Args:
            user_id: Filter by user (optional).
            min_negative: Minimum negative ratings to flag.

        Returns:
            List of (document_id, title, negative_count) sorted by count.
        """
        try:
            negative_entries = self.get_negative_feedback(user_id=user_id, limit=200)
            doc_counts: Dict[str, Dict[str, Any]] = {}

            for entry in negative_entries:
                for source in entry.get("sources", []):
                    doc_id = source.get("document_id", source.get("document", ""))
                    if not doc_id:
                        continue
                    if doc_id not in doc_counts:
                        doc_counts[doc_id] = {
                            "document_id": doc_id,
                            "title": source.get("document", ""),
                            "negative_count": 0,
                        }
                    doc_counts[doc_id]["negative_count"] += 1

            flagged = [
                d for d in doc_counts.values()
                if d["negative_count"] >= min_negative
            ]
            return sorted(flagged, key=lambda d: d["negative_count"], reverse=True)
        except Exception as e:
            logger.error(f"Failed to get weak documents: {e}")
            return []
