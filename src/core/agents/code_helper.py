"""
Code Helper Agent - Personalized code generation with RAG support.

Searches user's documents for code examples before generating.
"""

from typing import Optional, Dict, Any
from core.config import get_llm
from core.models import UserProfile, LearningLevel, LearningGoal
from core.models.agent_responses import CodeGenerationResponse


def get_code_instructions(user: Optional[UserProfile] = None) -> str:
    """
    Generate personalized code generation instructions based on user profile.
    
    Args:
        user: User profile with preferences
    
    Returns:
        Complete system prompt for code generation
    """
    if not user:
        return """You are an expert coding instructor who writes clean, educational code.

Write code that is correct, well-commented, and uses clear variable names."""
    
    # Base prompt
    system_prompt = f"""You are an expert coding instructor who adapts to each student's level.

USER PROFILE:
- Learning Level: {user.learning_level.value} ({user.learning_level.get_description()})
- Learning Goal: {user.learning_goal.value} ({user.learning_goal.get_description()})
- Preferred Language: {user.preferred_code_language}

CODE STYLE INSTRUCTIONS:
"""
    
    # Complexity based on learning level
    if user.learning_level == LearningLevel.BEGINNER:
        system_prompt += """
- Write SIMPLE, beginner-friendly code
- Use very descriptive variable names
- Add comments for every important line
- Break complex operations into multiple steps
- Avoid advanced features (comprehensions, lambdas, etc.)
- Include type hints for clarity"""
        
    elif user.learning_level == LearningLevel.INTERMEDIATE:
        system_prompt += """
- Write clear, well-structured code
- Use good variable names
- Add comments for important logic
- Can use list comprehensions and common patterns
- Include docstrings and type hints
- Balance clarity with efficiency"""
        
    else:  # ADVANCED
        system_prompt += """
- Write sophisticated, efficient code
- Can use advanced language features
- Include comprehensive type hints
- Add comments for complex algorithms only
- Can use functional programming patterns
- Include performance considerations"""
    
    # Adjust for learning goal
    if user.learning_goal == LearningGoal.QUICK_REVIEW:
        system_prompt += "\n- Focus on core implementation, minimal extras"
    elif user.learning_goal == LearningGoal.EXAM_PREP:
        system_prompt += "\n- Include time/space complexity comments"
    elif user.learning_goal == LearningGoal.RESEARCH:
        system_prompt += "\n- Provide extensible, modular design"
    else:  # DEEP_LEARNING
        system_prompt += "\n- Include comprehensive explanations and error handling"
    
    return system_prompt


def create_personalized_code_helper(
    user: Optional[UserProfile] = None,
    use_rag: bool = True
):
    """
    Creates a personalized Code Helper using structured output.
    
    Args:
        user: User profile with preferences
        use_rag: Whether to use RAG for document context
    
    Returns:
        LLM configured for structured code generation
    """
    llm = get_llm(temperature=0.3)  # Lower temp for consistent code
    system_prompt = get_code_instructions(user)
    
    language = user.preferred_code_language if user else "python"
    
    # Add RAG instruction if enabled
    rag_instruction = ""
    if use_rag:
        rag_instruction = """

CODE EXAMPLES FROM USER'S DOCUMENTS:
{document_context}

IMPORTANT: If code examples are provided above:
- Use similar coding style and patterns
- Reference algorithms or approaches from their materials
- Adapt examples to the current request
- Cite which document the approach came from if relevant
"""
    
    full_prompt = system_prompt + rag_instruction + f"""

FORMAT YOUR RESPONSE:
- overview: Brief description of what the code does (2-3 sentences)
- code: Complete, working {language} code with comments
- usage_example: Example showing how to use the code
- explanation: Clear explanation of how the code works
- key_concepts: List of main concepts demonstrated (3-5 items)
- time_complexity: Time complexity analysis (e.g., "O(n log n)")
- space_complexity: Space complexity analysis (e.g., "O(n)")

User request: {{question}}"""
    
    # Use structured output
    structured_llm = llm.with_structured_output(CodeGenerationResponse)
    
    return structured_llm, full_prompt


def generate_code_with_context(
    question: str,
    user_profile: Optional[UserProfile] = None,
    context: Optional[Dict[str, Any]] = None,
    memory_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate code with RAG enhancement and memory context.
    
    v0.3: Now searches user's documents for code examples.
    v0.4: Also uses memory context from previous conversations.
    
    Args:
        question: What to implement
        user_profile: User profile for personalization
        context: RAG context (legacy parameter)
        memory_context: Memory context from previous conversations (v0.4 NEW!)
    
    Returns:
        Formatted code response text
    """
    # Try to get code examples via RAG
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
                # Search specifically for code examples
                rag = RAGPipeline()
                
                # First try: search for code chunks
                from core.vectors import SemanticSearchService
                search_service = SemanticSearchService()
                
                code_results = search_service.search(
                    query=question,
                    user_id=user_profile.id,
                    top_k=3,
                    filter_has_code=True  # Only chunks with code
                )
                
                if code_results:
                    # Build context from code examples
                    context_parts = []
                    for result in code_results[:3]:
                        source_text = f"[Code from: {result.document.title or result.document.original_filename}"
                        if result.chunk.page_number:
                            source_text += f", p. {result.chunk.page_number}"
                        source_text += f"]\n{result.chunk.content[:400]}..."
                        context_parts.append(source_text)
                    
                    document_context = "\n\n".join(context_parts)
                    has_rag_context = True
                else:
                    # Fallback: general search
                    answer, sources = rag.query_with_context(
                        query=question + " code implementation",
                        user=user_profile,
                        top_k=2
                    )
                    if sources:
                        document_context = f"[Context from documents]\n{answer[:500]}..."
                        has_rag_context = True
                        
        except Exception as e:
            # RAG failed, continue without it
            import logging
            logging.warning(f"RAG lookup failed: {e}")
    
    # Build memory context string (v0.4 NEW!)
    memory_context_str = ""
    if memory_context:
        memory_parts = []
        
        # Add relevant concepts for code context
        if memory_context.get("relevant_concepts"):
            memory_parts.append(f"User familiar with: {', '.join(memory_context['relevant_concepts'])}")
        
        # Add weak areas to avoid in code
        if memory_context.get("weak_areas"):
            memory_parts.append(f"Needs simpler approach for: {', '.join(memory_context['weak_areas'])}")
        
        if memory_parts:
            memory_context_str = "\n\nCODING CONTEXT:\n" + "\n".join(f"- {part}" for part in memory_parts)
            memory_context_str += "\n\nADAPT YOUR CODE:\n"
            memory_context_str += "- Use concepts they're already comfortable with\n"
            memory_context_str += "- Simplify areas they're struggling with\n"
            memory_context_str += "- Add extra comments for weak areas\n"
    
    # Create code helper
    structured_llm, prompt_template = create_personalized_code_helper(
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
            "\n\nCODE EXAMPLES FROM USER'S DOCUMENTS:\n{document_context}\n\nIMPORTANT: If code examples are provided above:\n- Use similar coding style and patterns\n- Reference algorithms or approaches from their materials\n- Adapt examples to the current request\n- Cite which document the approach came from if relevant",
            ""
        ).format(question=question)
    
    # Add memory context to the prompt
    if memory_context_str:
        formatted_prompt += memory_context_str
    
    # Get structured response
    response = structured_llm.invoke(formatted_prompt)
    
    # Format for display
    language = user_profile.preferred_code_language if user_profile else "python"
    
    output = []
    
    output.append("## Overview\n")
    output.append(response.overview)
    output.append("\n\n")
    
    output.append("## Implementation\n")
    output.append(f"```{language}\n")
    output.append(response.code)
    output.append("\n```\n\n")
    
    output.append("## Usage Example\n")
    output.append(f"```{language}\n")
    output.append(response.usage_example)
    output.append("\n```\n\n")
    
    output.append("## How It Works\n")
    output.append(response.explanation)
    output.append("\n\n")
    
    if response.time_complexity or response.space_complexity:
        output.append("## Complexity Analysis\n")
        if response.time_complexity:
            output.append(f"- Time: {response.time_complexity}\n")
        if response.space_complexity:
            output.append(f"- Space: {response.space_complexity}\n")
        output.append("\n")
    
    output.append("## Key Concepts\n")
    for concept in response.key_concepts:
        output.append(f"- {concept}\n")
    
    # Add note if using document context
    if has_rag_context:
        output.append("\n💡 *This code was informed by examples from your documents.*")
    
    return "".join(output)


def generate_code(
    question: str,
    user: Optional[UserProfile] = None
) -> CodeGenerationResponse:
    """
    Generates code with personalized complexity (structured output).
    
    Args:
        question: What to implement
        user: User profile for personalization
    
    Returns:
        Structured CodeGenerationResponse
    """
    structured_llm, prompt_template = create_personalized_code_helper(user, use_rag=False)
    
    # Invoke with structured output
    response = structured_llm.invoke(
        prompt_template.format(question=question)
    )
    
    return response


def generate_code_as_text(
    question: str,
    user: Optional[UserProfile] = None
) -> str:
    """
    Get code generation as formatted text for display.
    
    Args:
        question: What to implement
        user: User profile for personalization
    
    Returns:
        Formatted text response
    """
    # Use the RAG-enhanced version
    return generate_code_with_context(question, user, context=None)


__all__ = [
    "generate_code",
    "generate_code_as_text",
    "generate_code_with_context",
    "create_personalized_code_helper",
    "get_code_instructions"
]