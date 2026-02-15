"""
Practice Repository for session history tracking.
"""

import logging
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)


class PracticeRepository:
    """Repository for practice session operations."""
    
    def __init__(self, database=None):
        """Initialize practice repository."""
        from core.database.connection import get_database
        
        self.db = database or get_database()
        mongo_db = self.db.get_database() if hasattr(self.db, 'get_database') else self.db
        self.sessions_collection = mongo_db["practice_sessions"]
        
        # Create indexes for performance
        try:
            self.sessions_collection.create_index([("user_id", 1), ("completed_at", -1)])
            self.sessions_collection.create_index([("user_id", 1), ("topic", 1)])
        except Exception as e:
            # Indexes might already exist - log but don't fail
            logger.debug(f"Index creation info: {e}")

    def save_session(self, user_id: str, session_data: dict) -> dict:
        """Save a practice session."""
        try:
            session_doc = {
                "_id": ObjectId(),
                "user_id": user_id,
                "topic": session_data.get("topic"),
                "difficulty": session_data.get("difficulty", "intermediate"),
                "questions": session_data.get("questions", []),
                "score": session_data.get("score", 0),
                "total_questions": session_data.get("total_questions", 0),
                "percentage": session_data.get("percentage", 0.0),
                "started_at": session_data.get("started_at"),
                "completed_at": session_data.get("completed_at"),
                "duration_minutes": session_data.get("duration_minutes", 0),
                "question_types": session_data.get("question_types", [])
            }
            
            result = self.sessions_collection.insert_one(session_doc)
            session_doc["id"] = str(session_doc.pop("_id"))
            
            logger.info(f"Practice session saved: {session_doc['id']}")
            return session_doc
            
        except Exception as e:
            logger.error(f"Error saving practice session: {e}")
            raise
    
    def get_user_sessions(self, user_id: str, skip: int = 0, limit: int = 20, topic: Optional[str] = None) -> List[dict]:
        """Get user's practice sessions."""
        try:
            query = {"user_id": user_id}
            if topic:
                query["topic"] = topic
            
            cursor = self.sessions_collection.find(query).sort("completed_at", -1).skip(skip).limit(limit)
            
            sessions = []
            for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                sessions.append(doc)
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting practice sessions: {e}")
            return []
    
    def get_session_by_id(self, session_id: str, user_id: str) -> Optional[dict]:
        """Get specific practice session."""
        try:
            doc = self.sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user_id})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
            return None
        except Exception as e:
            logger.error(f"Error getting practice session: {e}")
            return None
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a practice session."""
        try:
            result = self.sessions_collection.delete_one({"_id": ObjectId(session_id), "user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting practice session: {e}")
            return False
    
    def get_practice_stats(self, user_id: str) -> dict:
        """Get practice statistics for user."""
        try:
            sessions = self.get_user_sessions(user_id, limit=100)
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "total_questions_answered": 0,
                    "average_score": 0.0,
                    "sessions_by_topic": {},
                    "recent_sessions": [],
                    "improvement_trend": []
                }
            
            total_questions = sum(s.get("total_questions", 0) for s in sessions)
            average_score = sum(s.get("percentage", 0) for s in sessions) / len(sessions)
            
            sessions_by_topic = {}
            for session in sessions:
                topic = session.get("topic", "Unknown")
                sessions_by_topic[topic] = sessions_by_topic.get(topic, 0) + 1
            
            improvement_trend = [s.get("percentage", 0) for s in sessions[:10]]
            improvement_trend.reverse()
            
            recent_sessions = []
            for s in sessions[:5]:
                recent_sessions.append({
                    "id": s["id"],
                    "topic": s.get("topic"),
                    "score": s.get("score"),
                    "percentage": s.get("percentage"),
                    "completed_at": s.get("completed_at").isoformat() if isinstance(s.get("completed_at"), datetime) else str(s.get("completed_at"))
                })
            
            return {
                "total_sessions": len(sessions),
                "total_questions_answered": total_questions,
                "average_score": round(average_score, 1),
                "sessions_by_topic": sessions_by_topic,
                "recent_sessions": recent_sessions,
                "improvement_trend": improvement_trend
            }
        except Exception as e:
            logger.error(f"Error getting practice stats: {e}")
            return {
                "total_sessions": 0,
                "total_questions_answered": 0,
                "average_score": 0.0,
                "sessions_by_topic": {},
                "recent_sessions": [],
                "improvement_trend": []
            }


__all__ = ["PracticeRepository"]
