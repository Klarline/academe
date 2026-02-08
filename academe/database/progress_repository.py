"""
Progress Repository for Learning Analytics

Handles all database operations for learning progress tracking,
study sessions, and memory context.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from academe.models.progress import (
    LearningProgress,
    StudySession,
    ConceptRelationship,
    LearningPath,
    MemoryContext,
    ConceptMastery
)

logger = logging.getLogger(__name__)


class ProgressRepository:
    """
    Repository for learning progress and memory operations.
    Part of the enhanced Memory Module for v0.4.
    """

    def __init__(self, database=None):
        """Initialize progress repository."""
        self.db = database
        if self.db:
            # Get the MongoDB database
            mongo_db = self.db.get_database() if hasattr(self.db, 'get_database') else self.db
            
            self.progress_collection = mongo_db["learning_progress"]
            self.sessions_collection = mongo_db["study_sessions"]
            self.relationships_collection = mongo_db["concept_relationships"]
            self.paths_collection = mongo_db["learning_paths"]
            self.context_collection = mongo_db["memory_context"]

    # === Learning Progress Operations ===

    def track_concept_interaction(
        self,
        user_id: str,
        concept: str,
        interaction_type: str,
        details: Optional[Dict] = None
    ) -> bool:
        """
        Track when a user interacts with a concept.

        Args:
            user_id: User ID
            concept: Concept name (e.g., "eigenvalues")
            interaction_type: Type of interaction (view, practice, code_request)
            details: Additional details about the interaction

        Returns:
            Success status
        """
        try:
            # Get or create progress record
            progress = self.get_concept_progress(user_id, concept)

            if not progress:
                # Create new progress record
                progress = LearningProgress(
                    user_id=user_id,
                    concept=concept,
                    first_seen=datetime.utcnow()
                )

            # Update based on interaction type
            if interaction_type == "view" or interaction_type == "explanation":
                progress.explanation_views += 1
            elif interaction_type == "practice":
                if details and "correct" in details:
                    progress.update_from_practice(
                        correct=details["correct"],
                        time_spent=details.get("time_spent", 0)
                    )
            elif interaction_type == "code_request":
                progress.code_examples_requested += 1

            # Add to practice history if relevant
            if interaction_type == "practice" and details:
                progress.practice_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": interaction_type,
                    "details": details
                })

            # Update last studied
            progress.last_studied = datetime.utcnow()

            # Save to database
            if self.db:
                self.progress_collection.update_one(
                    {"user_id": user_id, "concept": concept},
                    {"$set": progress.dict()},
                    upsert=True
                )

            logger.info(f"Tracked {interaction_type} for concept '{concept}' by user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error tracking concept interaction: {e}")
            return False

    def update_mastery_level(
        self,
        user_id: str,
        concept: str,
        performance: Dict[str, Any]
    ) -> Optional[ConceptMastery]:
        """
        Update mastery level based on performance.

        Args:
            user_id: User ID
            concept: Concept name
            performance: Performance data (correct, total, time_spent)

        Returns:
            New mastery level or None
        """
        try:
            progress = self.get_concept_progress(user_id, concept)

            if not progress:
                progress = LearningProgress(
                    user_id=user_id,
                    concept=concept
                )

            # Update with performance data
            if "correct" in performance and "total" in performance:
                for _ in range(performance["total"]):
                    is_correct = _ < performance["correct"]
                    progress.update_from_practice(
                        correct=is_correct,
                        time_spent=performance.get("time_spent", 0) / performance["total"]
                    )

            # Save to database
            if self.db:
                self.progress_collection.update_one(
                    {"user_id": user_id, "concept": concept},
                    {"$set": progress.dict()},
                    upsert=True
                )

            return progress.mastery_level

        except Exception as e:
            logger.error(f"Error updating mastery level: {e}")
            return None

    def get_user_progress(
        self,
        user_id: str,
        min_interactions: int = 0
    ) -> List[LearningProgress]:
        """
        Get all learning progress for a user.

        Args:
            user_id: User ID
            min_interactions: Minimum number of interactions to include

        Returns:
            List of learning progress records
        """
        try:
            if self.db:
                query = {"user_id": user_id}
                if min_interactions > 0:
                    query["questions_attempted"] = {"$gte": min_interactions}

                results = self.progress_collection.find(query)
                return [LearningProgress.from_mongo_dict(doc) for doc in results]
            else:
                # Mock data for testing
                return [
                    LearningProgress(
                        user_id=user_id,
                        concept="eigenvalues",
                        mastery_level=ConceptMastery.LEARNING,
                        questions_attempted=5,
                        questions_correct=3
                    )
                ]

        except Exception as e:
            logger.error(f"Error getting user progress: {e}")
            return []

    def get_concept_progress(
        self,
        user_id: str,
        concept: str
    ) -> Optional[LearningProgress]:
        """
        Get progress for a specific concept.

        Args:
            user_id: User ID
            concept: Concept name

        Returns:
            Learning progress or None
        """
        try:
            if self.db:
                doc = self.progress_collection.find_one({
                    "user_id": user_id,
                    "concept": concept
                })
                return LearningProgress.from_mongo_dict(doc) if doc else None
            else:
                # Return mock data for testing
                return None

        except Exception as e:
            logger.error(f"Error getting concept progress: {e}")
            return None

    def get_weak_areas(
        self,
        user_id: str,
        threshold: float = 0.6
    ) -> List[str]:
        """
        Identify weak areas based on accuracy threshold.

        Args:
            user_id: User ID
            threshold: Accuracy threshold (concepts below this are weak)

        Returns:
            List of weak concept names
        """
        try:
            progress_list = self.get_user_progress(user_id, min_interactions=3)

            weak_areas = [
                p.concept
                for p in progress_list
                if p.accuracy_rate < threshold and p.questions_attempted >= 3
            ]

            return weak_areas

        except Exception as e:
            logger.error(f"Error identifying weak areas: {e}")
            return []

    def get_study_recommendations(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get personalized study recommendations.

        Args:
            user_id: User ID
            limit: Maximum number of recommendations

        Returns:
            List of recommendations with concept and reason
        """
        try:
            recommendations = []

            # Get all progress
            progress_list = self.get_user_progress(user_id)

            # Sort by priority (weak areas first, then least recent)
            progress_list.sort(
                key=lambda p: (
                    p.mastery_score,  # Lower mastery first
                    -p.last_studied.timestamp() if p.last_studied else 0  # Older first
                )
            )

            for progress in progress_list[:limit]:
                reason = ""

                if progress.mastery_score < 0.4:
                    reason = f"Weak area (mastery: {progress.mastery_score:.0%})"
                elif (datetime.utcnow() - progress.last_studied).days > 7:
                    reason = "Haven't reviewed in over a week"
                elif progress.questions_attempted < 5:
                    reason = "Need more practice"
                else:
                    reason = "Ready for advanced practice"

                recommendations.append({
                    "concept": progress.concept,
                    "mastery_level": progress.mastery_level,
                    "reason": reason,
                    "last_studied": progress.last_studied.isoformat(),
                    "accuracy": progress.accuracy_rate
                })

            return recommendations

        except Exception as e:
            logger.error(f"Error getting study recommendations: {e}")
            return []

    # === Study Session Operations ===

    def start_study_session(
        self,
        user_id: str,
        session_type: str = "general"
    ) -> Optional[str]:
        """
        Start a new study session.

        Args:
            user_id: User ID
            session_type: Type of session (general, practice, research, review)

        Returns:
            Session ID or None
        """
        try:
            session = StudySession(
                user_id=user_id,
                session_type=session_type,
                session_start=datetime.utcnow()
            )

            if self.db:
                result = self.sessions_collection.insert_one(session.dict())
                return str(result.inserted_id)
            else:
                return f"session_{user_id}_{datetime.utcnow().timestamp()}"

        except Exception as e:
            logger.error(f"Error starting study session: {e}")
            return None

    def end_study_session(
        self,
        session_id: str,
        metrics: Optional[Dict] = None
    ) -> bool:
        """
        End a study session and save metrics.

        Args:
            session_id: Session ID
            metrics: Session metrics to save

        Returns:
            Success status
        """
        try:
            if self.db:
                update_data = {
                    "session_end": datetime.utcnow(),
                    "duration_minutes": 0  # Will be calculated
                }

                if metrics:
                    update_data.update(metrics)

                self.sessions_collection.update_one(
                    {"_id": session_id},
                    {"$set": update_data}
                )

            return True

        except Exception as e:
            logger.error(f"Error ending study session: {e}")
            return False

    def get_study_sessions(
        self,
        user_id: str,
        days_back: int = 30
    ) -> List[StudySession]:
        """
        Get recent study sessions for a user.

        Args:
            user_id: User ID
            days_back: Number of days to look back

        Returns:
            List of study sessions
        """
        try:
            if self.db:
                cutoff = datetime.utcnow() - timedelta(days=days_back)
                results = self.sessions_collection.find({
                    "user_id": user_id,
                    "session_start": {"$gte": cutoff}
                }).sort("session_start", -1)

                return [StudySession.from_mongo_dict(doc) for doc in results]
            else:
                return []

        except Exception as e:
            logger.error(f"Error getting study sessions: {e}")
            return []

    # === Memory Context Operations ===

    def get_memory_context(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Optional[MemoryContext]:
        """
        Get memory context for a user/conversation.

        Args:
            user_id: User ID
            conversation_id: Optional conversation ID

        Returns:
            Memory context or None
        """
        try:
            if self.db:
                query = {"user_id": user_id}
                if conversation_id:
                    query["conversation_id"] = conversation_id

                doc = self.context_collection.find_one(
                    query,
                    sort=[("last_updated", -1)]  # Get most recent
                )
                return MemoryContext.from_mongo_dict(doc) if doc else None
            else:
                # Return mock context for testing
                return MemoryContext(
                    user_id=user_id,
                    conversation_id=conversation_id or "default",
                    recent_concepts=["eigenvalues", "PCA"],
                    current_topic="linear_algebra"
                )

        except Exception as e:
            logger.error(f"Error getting memory context: {e}")
            return None

    def update_memory_context(
        self,
        user_id: str,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update memory context with new information.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            updates: Updates to apply

        Returns:
            Success status
        """
        try:
            context = self.get_memory_context(user_id, conversation_id)

            if not context:
                context = MemoryContext(
                    user_id=user_id,
                    conversation_id=conversation_id
                )

            # Apply updates
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)

            context.last_updated = datetime.utcnow()

            if self.db:
                self.context_collection.update_one(
                    {"user_id": user_id, "conversation_id": conversation_id},
                    {"$set": context.dict()},
                    upsert=True
                )

            return True

        except Exception as e:
            logger.error(f"Error updating memory context: {e}")
            return False

    def get_relevant_context(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context from past interactions.

        Args:
            user_id: User ID
            query: Current query
            limit: Maximum number of relevant items

        Returns:
            List of relevant context items
        """
        try:
            # Get recent memory contexts
            if self.db:
                contexts = self.context_collection.find(
                    {"user_id": user_id}
                ).sort("last_updated", -1).limit(10)

                relevant_items = []
                for ctx_doc in contexts:
                    ctx = MemoryContext(**ctx_doc)

                    # Check if recent concepts are relevant to query
                    query_lower = query.lower()
                    for concept in ctx.recent_concepts:
                        if concept.lower() in query_lower:
                            relevant_items.append({
                                "type": "concept",
                                "value": concept,
                                "from_conversation": ctx.conversation_id,
                                "timestamp": ctx.last_updated
                            })

                    if len(relevant_items) >= limit:
                        break

                return relevant_items[:limit]
            else:
                return []

        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return []


# Export repository
__all__ = ["ProgressRepository"]