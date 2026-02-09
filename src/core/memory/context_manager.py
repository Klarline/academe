"""
Context Manager for Enhanced Memory Module

Manages context from previous messages and provides
comprehensive user context for better agent responses.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from core.database.progress_repository import ProgressRepository
from core.database.repositories import ConversationRepository
from core.models.progress import MemoryContext, ConceptMastery
from core.models import UserProfile
from core.utils.datetime_utils import get_current_time

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages context across sessions and conversations.
    Core part of the enhanced Memory Module.
    """

    def __init__(
        self,
        progress_repo: Optional[ProgressRepository] = None,
        conversation_repo: Optional[ConversationRepository] = None
    ):
        """Initialize context manager."""
        self.progress_repo = progress_repo or ProgressRepository()
        self.conversation_repo = conversation_repo or ConversationRepository()

    def get_user_context(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """
        Build comprehensive user context for agents.

        This provides all relevant context from:
        - User profile and preferences
        - Recent conversation history
        - Learning progress
        - Current session context
        - Document context

        Args:
            user_id: User ID
            conversation_id: Current conversation ID
            include_history: Whether to include conversation history

        Returns:
            Comprehensive context dictionary
        """
        context = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "timestamp": get_current_time().isoformat()
        }

        # Get memory context
        memory_ctx = self.progress_repo.get_memory_context(user_id, conversation_id)
        if memory_ctx:
            context["memory"] = {
                "recent_concepts": memory_ctx.recent_concepts,
                "recent_documents": memory_ctx.recent_documents,
                "current_topic": memory_ctx.current_topic,
                "current_goal": memory_ctx.current_goal,
                "question_sequence": memory_ctx.question_sequence[-5:],  # Last 5 questions
                "requires_followup": memory_ctx.requires_followup,
                "pending_clarifications": memory_ctx.pending_clarifications
            }

        # Get learning progress
        progress_list = self.progress_repo.get_user_progress(user_id)
        if progress_list:
            # Summarize progress
            mastery_summary = {}
            for level in ConceptMastery:
                count = len([p for p in progress_list if p.mastery_level == level])
                if count > 0:
                    mastery_summary[level.value] = count

            context["learning_progress"] = {
                "total_concepts_studied": len(progress_list),
                "mastery_distribution": mastery_summary,
                "recent_concepts": [
                    {
                        "concept": p.concept,
                        "mastery": p.mastery_level,
                        "last_studied": p.last_studied.isoformat()
                    }
                    for p in sorted(
                        progress_list,
                        key=lambda x: x.last_studied,
                        reverse=True
                    )[:5]
                ]
            }

        # Get weak areas
        weak_areas = self.progress_repo.get_weak_areas(user_id)
        if weak_areas:
            context["weak_areas"] = weak_areas

        # Get study recommendations
        recommendations = self.progress_repo.get_study_recommendations(user_id, limit=3)
        if recommendations:
            context["recommendations"] = recommendations

        # Get conversation history if requested
        if include_history and conversation_id:
            recent_messages = self._get_recent_messages(conversation_id, limit=10)
            if recent_messages:
                context["recent_messages"] = recent_messages

        # Get relevant past context
        if conversation_id:
            relevant_context = self.progress_repo.get_relevant_context(
                user_id,
                context.get("current_query", ""),
                limit=3
            )
            if relevant_context:
                context["relevant_past_context"] = relevant_context

        return context

    def update_context(
        self,
        user_id: str,
        conversation_id: str,
        interaction: Dict[str, Any]
    ) -> bool:
        """
        Update context after each interaction.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            interaction: Interaction details (query, response, agent_used, etc.)

        Returns:
            Success status
        """
        try:
            # Get or create memory context
            memory_ctx = self.progress_repo.get_memory_context(user_id, conversation_id)
            if not memory_ctx:
                memory_ctx = MemoryContext(
                    user_id=user_id,
                    conversation_id=conversation_id
                )

            # Update based on interaction type
            if "query" in interaction:
                # Add to question sequence
                memory_ctx.question_sequence.append(interaction["query"])
                # Keep only last 20 questions
                memory_ctx.question_sequence = memory_ctx.question_sequence[-20:]

            if "concepts" in interaction:
                # Add new concepts
                for concept in interaction["concepts"]:
                    memory_ctx.add_concept(concept)

                    # Track in learning progress
                    self.progress_repo.track_concept_interaction(
                        user_id=user_id,
                        concept=concept,
                        interaction_type=interaction.get("type", "view"),
                        details=interaction.get("details")
                    )

            if "documents" in interaction:
                # Add accessed documents
                for doc_id in interaction["documents"]:
                    memory_ctx.add_document(doc_id)

            if "current_topic" in interaction:
                memory_ctx.current_topic = interaction["current_topic"]

            if "requires_followup" in interaction:
                memory_ctx.requires_followup = interaction["requires_followup"]

            # Save updated context
            return self.progress_repo.update_memory_context(
                user_id=user_id,
                conversation_id=conversation_id,
                updates=memory_ctx.dict()
            )

        except Exception as e:
            logger.error(f"Error updating context: {e}")
            return False

    def get_relevant_history(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant past interactions for current query.

        Args:
            user_id: User ID
            query: Current query
            limit: Maximum number of relevant items

        Returns:
            List of relevant historical interactions
        """
        try:
            # Get relevant context from repository
            relevant_items = self.progress_repo.get_relevant_context(
                user_id=user_id,
                query=query,
                limit=limit
            )

            # Enhance with additional details if needed
            enhanced_items = []
            for item in relevant_items:
                enhanced_item = item.copy()

                # Add concept progress if it's a concept
                if item["type"] == "concept":
                    progress = self.progress_repo.get_concept_progress(
                        user_id=user_id,
                        concept=item["value"]
                    )
                    if progress:
                        enhanced_item["mastery_level"] = progress.mastery_level
                        enhanced_item["accuracy"] = progress.accuracy_rate

                enhanced_items.append(enhanced_item)

            return enhanced_items

        except Exception as e:
            logger.error(f"Error getting relevant history: {e}")
            return []

    def build_agent_context(
        self,
        user: UserProfile,
        query: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Build context specifically for agent processing.

        Args:
            user: User profile
            query: Current query
            conversation_id: Conversation ID

        Returns:
            Context optimized for agent use
        """
        # Get comprehensive context
        context = self.get_user_context(
            user_id=user.id,
            conversation_id=conversation_id,
            include_history=True
        )

        # Add user profile information
        context["user_profile"] = {
            "learning_level": user.learning_level.value if hasattr(user.learning_level, 'value') else str(user.learning_level),
            "learning_goal": user.learning_goal.value if hasattr(user.learning_goal, 'value') else str(user.learning_goal),
            "explanation_style": user.explanation_style.value if hasattr(user.explanation_style, 'value') else str(user.explanation_style)
        }

        # Add current query
        context["current_query"] = query

        # Determine if this is a follow-up question
        if "memory" in context and context["memory"].get("question_sequence"):
            last_questions = context["memory"]["question_sequence"][-3:]
            # Simple heuristic: if query references previous concepts, it's a follow-up
            context["is_followup"] = any(
                self._is_related_query(query, prev_q)
                for prev_q in last_questions
            )
        else:
            context["is_followup"] = False

        # Add adaptive hints for agents
        if "weak_areas" in context and len(context["weak_areas"]) > 0:
            context["agent_hints"] = {
                "focus_on_basics": True,
                "provide_more_examples": True,
                "avoid_concepts": []  # Concepts that might be too advanced
            }
        
        # [NEW] Use LLM to filter relevant concepts
        if "learning_progress" in context and "recent_concepts" in context["learning_progress"]:
            all_concepts = [c["concept"] for c in context["learning_progress"]["recent_concepts"]]
            if all_concepts:
                relevant_concepts = self._filter_relevant_concepts(query, all_concepts)
                context["relevant_concepts"] = relevant_concepts

        return context

    def _get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get recent messages from conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages

        Returns:
            List of recent messages
        """
        try:
            if self.conversation_repo:
                messages = self.conversation_repo.get_conversation_messages(
                    conversation_id=conversation_id
                )
                # Return last N messages
                recent = messages[-limit:] if len(messages) > limit else messages
                return [
                    {
                        "role": msg.role,
                        "content": msg.content[:200],  # Truncate for context
                        "timestamp": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None
                    }
                    for msg in recent
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []

    def _is_related_query(self, query1: str, query2: str) -> bool:
        """
        Simple heuristic to check if two queries are related.

        Args:
            query1: First query
            query2: Second query

        Returns:
            True if queries seem related
        """
        # Convert to lowercase for comparison
        q1_lower = query1.lower()
        q2_lower = query2.lower()

        # Check for pronouns indicating follow-up
        followup_indicators = ["it", "this", "that", "those", "these", "the same"]
        for indicator in followup_indicators:
            if indicator in q1_lower:
                return True

        # Check for shared significant words (simple approach)
        q1_words = set(q1_lower.split())
        q2_words = set(q2_lower.split())

        # Remove common words
        common_words = {"the", "a", "an", "is", "are", "what", "how", "why", "when", "where"}
        q1_significant = q1_words - common_words
        q2_significant = q2_words - common_words

        # If they share significant words, likely related
        shared = q1_significant & q2_significant
        if len(shared) >= 2:  # At least 2 shared significant words
            return True

        return False

    def _filter_relevant_concepts(
        self,
        query: str,
        all_concepts: List[str]
    ) -> List[str]:
        """
        Use LLM to intelligently filter which concepts are relevant to the query.
        
        This is the "Option 2" LLM-enhanced approach - simple but effective.
        
        Args:
            query: Current user query
            all_concepts: List of all concepts user has studied
            
        Returns:
            List of relevant concepts
        """
        if not all_concepts:
            return []
        
        try:
            # Use lightweight Gemini 1.5 Flash for this task
            from core.config import get_llm
            
            memory_llm = get_llm(temperature=0)  # Use same model but deterministic
            
            # Simple, focused prompt
            prompt = f"""Given this question: "{query}"

Which of these concepts are RELEVANT to answering it?

Concepts: {', '.join(all_concepts[:20])}

Return ONLY the relevant concept names as a comma-separated list.
If none are relevant, return "none".

Relevant concepts:"""

            response = memory_llm.invoke(prompt)
            result = response.content.strip().lower()
            
            if result == "none" or not result:
                return []
            
            # Parse response
            relevant = [c.strip() for c in result.split(',')]
            
            # Filter to only concepts that were in the original list
            relevant = [c for c in relevant if c in [x.lower() for x in all_concepts]]
            
            return relevant
            
        except Exception as e:
            logger.error(f"Error filtering concepts with LLM: {e}")
            # Fallback: return all concepts
            return all_concepts[:5]  # Limit to 5 most recent

    def initialize_session_context(
        self,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Initialize context for a new session.

        Args:
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            Initial context
        """
        # Start a study session
        session_id = self.progress_repo.start_study_session(
            user_id=user_id,
            session_type="general"
        )

        # Create initial memory context
        memory_ctx = MemoryContext(
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Save it
        self.progress_repo.update_memory_context(
            user_id=user_id,
            conversation_id=conversation_id,
            updates=memory_ctx.dict()
        )

        return {
            "session_id": session_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "initialized_at": get_current_time().isoformat()
        }


# Export the context manager
__all__ = ["ContextManager"]