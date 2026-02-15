"""
Concept Explainer Agent - Personalized explanations with RAG support.

This is the CORE INNOVATION of Academe - inspired by the viral "granny mode"
prompting technique, enhanced with user personalization and document context.
"""

import logging
from typing import Optional, Dict, Any, AsyncGenerator
from core.config import get_llm
from core.models import UserProfile, LearningLevel, ExplanationStyle, LearningGoal
from core.models.agent_responses import ConceptExplanationResponse

logger = logging.getLogger(__name__)


class ConceptExplainer:
    """Agent that provides personalized concept explanations with RAG support."""
    
    def __init__(
        self,
        rag_pipeline=None,
        document_manager=None
    ):
        """
        Initialize concept explainer.
        
        Args:
            rag_pipeline: RAG pipeline for document context
            document_manager: Document manager
        """
        from core.rag import RAGPipeline
        from core.documents import DocumentManager
        
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.document_manager = document_manager or DocumentManager()
    
    def explain(
        self,
        question: str,
        user_profile: Optional[UserProfile] = None,
        memory_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Explain a concept with RAG enhancement and memory context.
        
        Args:
            question: The concept to explain
            user_profile: User profile for personalization
            memory_context: Memory context from previous conversations
        
        Returns:
            Formatted explanation text
        """
        try:
            # Get document context via RAG
            document_context, has_rag_context = self._get_document_context(question, user_profile)
            
            # Build memory context string
            memory_context_str = self._build_memory_context(memory_context)
            
            # Create personalized explainer
            structured_llm, prompt_template = self._create_personalized_explainer(
                user_profile, has_rag_context
            )
            
            # Format final prompt
            formatted_prompt = self._format_prompt(
                prompt_template, question, document_context,
                memory_context_str, has_rag_context
            )
            
            # Get structured response
            response = structured_llm.invoke(formatted_prompt)
            
            # Format for display
            return self._format_response(response, has_rag_context)
        
        except Exception as e:
            logger.error(f"Failed to explain '{question}': {e}", exc_info=True)
            return (
                "I encountered an error generating the explanation. "
                "This might be due to API issues or rate limits. "
                "Please try rephrasing your question or try again in a moment."
            )
    
    def _get_document_context(
        self,
        question: str,
        user_profile: Optional[UserProfile]
    ) -> tuple[str, bool]:
        """Get relevant document context via RAG."""
        document_context = ""
        has_rag_context = False
        
        if user_profile:
            try:
                # Check if user has documents
                user_docs = self.document_manager.get_user_documents(user_profile.id)
                
                if user_docs:
                    # Search user's documents for relevant context
                    answer, sources = self.rag_pipeline.query_with_context(
                        query=question,
                        user=user_profile,
                        top_k=3,
                        use_reranking=True
                    )
                    
                    if sources:
                        # Build context from sources
                        context_parts = []
                        for source in sources[:3]:
                            source_text = f"[From: {source.document.title or source.document.original_filename}"
                            if source.chunk.page_number:
                                source_text += f", p. {source.chunk.page_number}"
                            source_text += f"]\n{source.chunk.content[:300]}..."
                            context_parts.append(source_text)
                        
                        document_context = "\n\n".join(context_parts)
                        has_rag_context = True
            except Exception as e:
                logger.warning(f"RAG lookup failed: {e}")
        
        return document_context, has_rag_context
    
    def _build_memory_context(self, memory_context: Optional[Dict[str, Any]]) -> str:
        """Build memory context string from memory dict."""
        if not memory_context:
            return ""
        
        memory_parts = []
        
        if memory_context.get("relevant_concepts"):
            memory_parts.append(f"Recently studied: {', '.join(memory_context['relevant_concepts'])}")
        
        if memory_context.get("weak_areas"):
            memory_parts.append(f"Struggling with: {', '.join(memory_context['weak_areas'])}")
        
        if memory_context.get("memory", {}).get("current_topic"):
            memory_parts.append(f"Current focus: {memory_context['memory']['current_topic']}")
        
        if memory_context.get("is_followup"):
            memory_parts.append("This is a follow-up question")
        
        if not memory_parts:
            return ""
        
        memory_str = "\n\nLEARNING CONTEXT:\n" + "\n".join(f"- {part}" for part in memory_parts)
        memory_str += "\n\nADAPT YOUR EXPLANATION:\n"
        memory_str += "- Build on concepts they've studied\n"
        memory_str += "- Simplify their weak areas\n"
        memory_str += "- Connect to their current focus\n"
        if memory_context.get("is_followup"):
            memory_str += "- Reference previous explanations\n"
        
        return memory_str
    
    def _create_personalized_explainer(
        self,
        user: Optional[UserProfile] = None,
        use_rag: bool = True
    ):
        """
        Create personalized LLM with structured output.
        
        Args:
            user: User profile with preferences
            use_rag: Whether to include RAG instructions
        
        Returns:
            Tuple of (structured_llm, prompt_template)
        """
        llm = get_llm(temperature=0.7)
        system_prompt = self._get_personalized_instructions(user)
        
        # Determine which fields to populate based on style
        if user and user.explanation_style == ExplanationStyle.INTUITIVE:
            additional_instruction = "\nProvide only intuitive_explanation (leave technical_explanation as None)."
        elif user and user.explanation_style == ExplanationStyle.TECHNICAL:
            additional_instruction = "\nProvide only technical_explanation (leave intuitive_explanation as None)."
        else:
            additional_instruction = "\nProvide both intuitive_explanation AND technical_explanation."
        
        # Add RAG instruction if enabled
        rag_instruction = ""
        if use_rag:
            rag_instruction = """

DOCUMENT CONTEXT:
{document_context}

IMPORTANT: If document context is provided above, use it to enhance your explanation:
- Reference specific examples from the user's materials
- Use terminology consistent with their documents
- Cite page numbers or sections when relevant
- If context conflicts with general knowledge, prioritize the user's materials
"""
        
        full_prompt = system_prompt + additional_instruction + rag_instruction + """

FORMAT YOUR RESPONSE:
- intuitive_explanation: Simple, intuitive explanation using analogies
- technical_explanation: Rigorous technical explanation with formulas
- key_takeaway: One sentence capturing the core insight
- why_matters: 2-3 sentences explaining importance
- concepts_covered: List of key concepts (3-5 items)

User question: {question}"""
        
        structured_llm = llm.with_structured_output(ConceptExplanationResponse)
        return structured_llm, full_prompt
    
    def _get_personalized_instructions(self, user: Optional[UserProfile] = None) -> str:
        """Generate personalized system prompt based on user profile."""
        if not user:
            return """You are an expert educator with a gift for adaptive teaching.
        
Provide clear explanations that are easy to understand."""
        
        system_prompt = f"""You are an expert educator with a gift for adaptive teaching.

USER PROFILE:
- Learning Level: {user.learning_level.value} ({user.learning_level.get_description()})
- Learning Goal: {user.learning_goal.value} ({user.learning_goal.get_description()})
- Explanation Style: {user.explanation_style.value} ({user.explanation_style.get_description()})
- Include Math: {'Yes' if user.include_math_formulas else 'No - avoid mathematical notation'}
- Include Visuals: {'Yes - use ASCII diagrams when helpful' if user.include_visualizations else 'No'}

INSTRUCTIONS FOR THIS USER:
"""
        
        # Customize based on learning level
        if user.learning_level == LearningLevel.BEGINNER:
            system_prompt += """
- Use very simple, everyday language
- Use familiar analogies from daily life
- Avoid technical jargon or define it clearly
- Break down complex ideas into small steps
- Provide concrete examples"""
            
        elif user.learning_level == LearningLevel.INTERMEDIATE:
            system_prompt += """
- Use clear language with some technical terms
- Introduce concepts with context
- Balance accessibility with depth
- Include relevant examples
- Connect to foundational knowledge"""
            
        else:  # ADVANCED
            system_prompt += """
- Use rigorous, graduate-level explanations
- Include advanced mathematical formulations
- Connect to cutting-edge research
- Discuss nuances and edge cases
- Reference papers or advanced resources"""
        
        # Adjust for learning goal
        if user.learning_goal == LearningGoal.QUICK_REVIEW:
            system_prompt += "\n- Focus on key points only, be concise"
        elif user.learning_goal == LearningGoal.EXAM_PREP:
            system_prompt += "\n- Emphasize testable concepts and common questions"
        elif user.learning_goal == LearningGoal.RESEARCH:
            system_prompt += "\n- Include depth, nuances, and research context"
        else:  # DEEP_LEARNING
            system_prompt += "\n- Provide comprehensive coverage with multiple examples"
        
        # Explanation style
        if user.explanation_style == ExplanationStyle.INTUITIVE:
            system_prompt += "\n- Prioritize intuitive understanding over technical rigor"
        elif user.explanation_style == ExplanationStyle.TECHNICAL:
            system_prompt += "\n- Prioritize technical accuracy and mathematical precision"
        else:  # BALANCED
            system_prompt += "\n- Balance intuitive understanding with technical details"
        
        return system_prompt
    
    def _format_prompt(
        self,
        prompt_template: str,
        question: str,
        document_context: str,
        memory_context_str: str,
        has_rag_context: bool
    ) -> str:
        """Format the final prompt with all context."""
        if has_rag_context:
            formatted_prompt = prompt_template.format(
                question=question,
                document_context=document_context
            )
        else:
            # Remove RAG placeholder if not used
            formatted_prompt = prompt_template.replace(
                "\n\nDOCUMENT CONTEXT:\n{document_context}\n\nIMPORTANT: If document context is provided above, use it to enhance your explanation:\n- Reference specific examples from the user's materials\n- Use terminology consistent with their documents\n- Cite page numbers or sections when relevant\n- If context conflicts with general knowledge, prioritize the user's materials",
                ""
            ).format(question=question)
        
        if memory_context_str:
            formatted_prompt += memory_context_str
        
        return formatted_prompt
    
    def _format_response(
        self,
        response: ConceptExplanationResponse,
        has_rag_context: bool
    ) -> str:
        """Format structured response into readable text."""
        output = []
        
        if response.intuitive_explanation:
            output.append("## Intuitive Explanation\n")
            output.append(response.intuitive_explanation)
            output.append("\n\n")
        
        if response.technical_explanation:
            output.append("## Technical Explanation\n")
            output.append(response.technical_explanation)
            output.append("\n\n")
        
        output.append("## Key Takeaway\n")
        output.append(response.key_takeaway)
        output.append("\n\n")
        
        output.append("## Why This Matters\n")
        output.append(response.why_matters)
        
        if has_rag_context:
            output.append("\n\n💡 *Enhanced using your documents.*")
        
        return "".join(output)


async def explain_concept_streaming(
    question: str,
    user_profile: Optional[UserProfile] = None,
    memory_context: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """
    Stream concept explanation token by token.
    Used by workflow streaming nodes.
    """
    llm = get_llm(temperature=0.7)
    
    # Use class method to get instructions
    explainer = ConceptExplainer()
    system_prompt = explainer._get_personalized_instructions(user_profile)
    
    prompt = system_prompt + f"""

Explain the following concept clearly and thoroughly:

{question}

Provide a comprehensive explanation that matches the user's learning level and style preferences."""

    # Add memory context if available
    if memory_context:
        memory_parts = []
        if memory_context.get("relevant_concepts"):
            memory_parts.append(f"Recently studied: {', '.join(memory_context['relevant_concepts'])}")
        if memory_context.get("weak_areas"):
            memory_parts.append(f"Needs help with: {', '.join(memory_context['weak_areas'])}")
        
        if memory_parts:
            prompt += "\n\nLEARNING CONTEXT:\n" + "\n".join(f"- {part}" for part in memory_parts)

    try:
        async for chunk in llm.astream(prompt):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"\n\n[Error: API quota exceeded or connection issue. Please try again later.]"


__all__ = [
    "ConceptExplainer",
    "explain_concept_streaming",
]
