"""
Concept Explainer Agent - Personalized explanations with RAG support.

This is the CORE INNOVATION of Academe - inspired by the viral "granny mode"
prompting technique, enhanced with user personalization and document context.
It also searches user's documents for relevant context before explaining.
"""

from typing import Optional, Dict, Any
from core.config import get_llm
from core.models import UserProfile, LearningLevel, ExplanationStyle, LearningGoal
from core.models.agent_responses import ConceptExplanationResponse


def get_personalized_instructions(user: Optional[UserProfile] = None) -> str:
    """
    Generate personalized system prompt based on user profile.
    
    Args:
        user: User profile with preferences
    
    Returns:
        Complete system prompt with user context
    """
    if not user:
        return """You are an expert educator with a gift for adaptive teaching.
        
Provide clear explanations that are easy to understand."""
    
    # Build system context
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


def create_personalized_explainer(
    user: Optional[UserProfile] = None,
    use_rag: bool = True
):
    """
    Creates a personalized Concept Explainer using structured output.
    
    Args:
        user: User profile with preferences
        use_rag: Whether to use RAG for document context
    
    Returns:
        LLM configured for structured concept explanations
    """
    llm = get_llm(temperature=0.7)
    system_prompt = get_personalized_instructions(user)
    
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
    
    # Use structured output
    structured_llm = llm.with_structured_output(ConceptExplanationResponse)
    
    return structured_llm, full_prompt


def explain_concept_with_context(
    question: str,
    user_profile: Optional[UserProfile] = None,
    context: Optional[Dict[str, Any]] = None,
    memory_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Explains a concept with RAG enhancement and memory context.
    
    v0.3: Now searches user's documents for relevant context.
    v0.4: Also uses memory context from previous conversations.
    
    Args:
        question: The concept to explain
        user_profile: User profile for personalization
        context: RAG context (legacy parameter, kept for compatibility)
        memory_context: Memory context from previous conversations (v0.4 NEW!)
    
    Returns:
        Formatted explanation text
    """
    # Try to get document context via RAG
    document_context = ""
    has_rag_context = False
    
    if user_profile:
        try:
            from core.rag import RAGPipeline
            from core.documents import DocumentManager
            
            # Check if user has documents
            doc_manager = DocumentManager()
            user_docs = doc_manager.get_user_documents(user_profile.id)
            
            if user_docs:
                # Search user's documents for relevant context
                rag = RAGPipeline()
                answer, sources = rag.query_with_context(
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
            # RAG failed, continue without it
            import logging
            logging.warning(f"RAG lookup failed: {e}")
    
    # Build memory context string (v0.4 NEW!)
    memory_context_str = ""
    if memory_context:
        memory_parts = []
        
        # Add relevant concepts
        if memory_context.get("relevant_concepts"):
            memory_parts.append(f"Recently studied concepts: {', '.join(memory_context['relevant_concepts'])}")
        
        # Add weak areas
        if memory_context.get("weak_areas"):
            memory_parts.append(f"Struggling with: {', '.join(memory_context['weak_areas'])}")
        
        # Add current topic
        if memory_context.get("memory", {}).get("current_topic"):
            memory_parts.append(f"Currently focusing on: {memory_context['memory']['current_topic']}")
        
        # Add follow-up indicator
        if memory_context.get("is_followup"):
            memory_parts.append("This is a follow-up question to previous topics")
        
        if memory_parts:
            memory_context_str = "\n\nLEARNING CONTEXT:\n" + "\n".join(f"- {part}" for part in memory_parts)
            memory_context_str += "\n\nADAPT YOUR EXPLANATION:\n"
            memory_context_str += "- Build on concepts they've already studied\n"
            memory_context_str += "- Simplify or avoid their weak areas\n"
            memory_context_str += "- Connect to their current focus topic if relevant\n"
            if memory_context.get("is_followup"):
                memory_context_str += "- Reference your previous explanations naturally\n"
    
    # Create explainer
    structured_llm, prompt_template = create_personalized_explainer(
        user=user_profile,
        use_rag=has_rag_context
    )
    
    # Format prompt with RAG context, memory context, or both
    if has_rag_context:
        formatted_prompt = prompt_template.format(
            question=question,
            document_context=document_context
        )
    else:
        # Remove the {document_context} placeholder if no RAG
        formatted_prompt = prompt_template.replace(
            "\n\nDOCUMENT CONTEXT:\n{document_context}\n\nIMPORTANT: If document context is provided above, use it to enhance your explanation:\n- Reference specific examples from the user's materials\n- Use terminology consistent with their documents\n- Cite page numbers or sections when relevant\n- If context conflicts with general knowledge, prioritize the user's materials",
            ""
        ).format(question=question)
    
    # Add memory context to the prompt
    if memory_context_str:
        formatted_prompt += memory_context_str
    
    # Get structured response
    response = structured_llm.invoke(formatted_prompt)
    
    # Format for display
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
    
    # Add note if using document context
    if has_rag_context:
        output.append("\n\n💡 *This explanation was enhanced using content from your documents.*")
    
    return "".join(output)


def explain_concept(
    question: str,
    user: Optional[UserProfile] = None
) -> ConceptExplanationResponse:
    """
    Explains a concept with personalization (structured output).
    
    Args:
        question: The concept to explain
        user: User profile for personalization
    
    Returns:
        Structured ConceptExplanationResponse
    """
    structured_llm, prompt_template = create_personalized_explainer(user, use_rag=False)
    
    # Invoke with structured output
    response = structured_llm.invoke(
        prompt_template.format(question=question)
    )
    
    return response


def explain_concept_as_text(
    question: str,
    user: Optional[UserProfile] = None
) -> str:
    """
    Get explanation as formatted text for display.
    
    Args:
        question: The concept to explain
        user: User profile for personalization
    
    Returns:
        Formatted text response
    """
    # Use the RAG-enhanced version
    return explain_concept_with_context(question, user, context=None)


__all__ = [
    "explain_concept",
    "explain_concept_as_text",
    "explain_concept_with_context",
    "create_personalized_explainer",
    "get_personalized_instructions"
]