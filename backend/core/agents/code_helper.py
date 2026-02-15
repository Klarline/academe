"""
Code Helper Agent - Personalized code generation with RAG support.

Searches user's documents for code examples before generating.
"""

import logging
from typing import Optional, Dict, Any, AsyncGenerator
from core.config import get_llm
from core.models import UserProfile, LearningLevel, LearningGoal
from core.models.agent_responses import CodeGenerationResponse

logger = logging.getLogger(__name__)


class CodeHelper:
    """Agent that generates code with RAG support for code examples."""
    
    def __init__(
        self,
        rag_pipeline=None,
        document_manager=None
    ):
        """
        Initialize code helper.
        
        Args:
            rag_pipeline: RAG pipeline for code examples
            document_manager: Document manager
        """
        from core.rag import RAGPipeline
        from core.documents import DocumentManager
        
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.document_manager = document_manager or DocumentManager()
    
    def generate_code(
        self,
        question: str,
        user_profile: Optional[UserProfile] = None,
        memory_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate code with RAG enhancement and memory context.
        
        Args:
            question: What to implement
            user_profile: User profile for personalization
            memory_context: Memory context from previous conversations
        
        Returns:
            Formatted code response text
        """
        try:
            # Get code examples via RAG
            document_context, has_rag_context = self._get_code_examples(question, user_profile)
            
            # Build memory context string
            memory_context_str = self._build_memory_context(memory_context)
            
            # Create personalized code generator
            structured_llm, prompt_template = self._create_personalized_code_helper(
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
            return self._format_response(response, user_profile, has_rag_context)
        
        except Exception as e:
            logger.error(f"Failed to generate code for '{question}': {e}", exc_info=True)
            return (
                "I encountered an error generating the code. "
                "This might be due to API issues or rate limits. "
                "Please try rephrasing your request or try again in a moment."
            )
    
    def _get_code_examples(
        self,
        question: str,
        user_profile: Optional[UserProfile]
    ) -> tuple[str, bool]:
        """Get relevant code examples via RAG."""
        document_context = ""
        has_rag_context = False
        
        if user_profile:
            try:
                # Check if user has documents
                user_docs = self.document_manager.get_user_documents(user_profile.id)
                
                if user_docs:
                    # Search specifically for code examples
                    from core.vectors import SemanticSearchService
                    search_service = SemanticSearchService()
                    
                    code_results = search_service.search(
                        query=question,
                        user_id=user_profile.id,
                        top_k=3,
                        filter_has_code=True
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
                        answer, sources = self.rag_pipeline.query_with_context(
                            query=question + " code implementation",
                            user=user_profile,
                            top_k=2
                        )
                        if sources:
                            document_context = f"[Context from documents]\n{answer[:500]}..."
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
            memory_parts.append(f"User familiar with: {', '.join(memory_context['relevant_concepts'])}")
        
        if memory_context.get("weak_areas"):
            memory_parts.append(f"Needs simpler approach for: {', '.join(memory_context['weak_areas'])}")
        
        if not memory_parts:
            return ""
        
        memory_str = "\n\nCONTEXT:\n" + "\n".join(f"- {part}" for part in memory_parts)
        return memory_str
    
    def _create_personalized_code_helper(
        self,
        user: Optional[UserProfile] = None,
        use_rag: bool = True
    ):
        """
        Create personalized code generator with structured output.
        
        Args:
            user: User profile with preferences
            use_rag: Whether to include RAG instructions
        
        Returns:
            Tuple of (structured_llm, prompt_template)
        """
        llm = get_llm(temperature=0.3)
        system_prompt = self._get_code_instructions(user)
        
        # Add RAG instruction if enabled
        rag_instruction = ""
        if use_rag:
            rag_instruction = """

CODE EXAMPLES FROM YOUR DOCUMENTS:
{document_context}

IMPORTANT: If code examples are provided above:
- Study the patterns and style
- Follow similar naming conventions
- Use similar error handling approaches
- Adapt the structure to fit the current task
"""
        
        full_prompt = system_prompt + rag_instruction + """

Generate code for the following request:

{question}

FORMAT YOUR RESPONSE:
- code: Complete, working code
- explanation: How the code works
- usage_example: Example of using the code
- time_complexity: Big O time complexity
- space_complexity: Big O space complexity
- key_concepts: List of concepts used (3-5 items)
"""
        
        structured_llm = llm.with_structured_output(CodeGenerationResponse)
        return structured_llm, full_prompt
    
    def _get_code_instructions(self, user: Optional[UserProfile] = None) -> str:
        """Generate personalized code generation instructions."""
        if not user:
            return "You are an expert programmer. Generate clean, working code."
        
        language = user.preferred_code_language or "python"
        
        system_prompt = f"""You are an expert {language.title()} programmer.

USER PROFILE:
- Language: {language}
- Level: {user.learning_level.value}
- Goal: {user.learning_goal.value}

INSTRUCTIONS:
"""
        
        if user.learning_level == LearningLevel.BEGINNER:
            system_prompt += """
- Use simple, clear code
- Add extensive comments explaining each step
- Avoid advanced language features
- Include clear variable names
- Provide complete examples"""
        elif user.learning_level == LearningLevel.INTERMEDIATE:
            system_prompt += """
- Use idiomatic code patterns
- Add helpful comments for complex parts
- Balance readability with efficiency
- Use appropriate data structures
- Include edge case handling"""
        else:  # ADVANCED
            system_prompt += """
- Use advanced language features appropriately
- Optimize for performance where relevant
- Include algorithmic complexity analysis
- Handle edge cases elegantly
- Follow industry best practices"""
        
        # Adjust for learning goal
        if user.learning_goal == LearningGoal.QUICK_REVIEW:
            system_prompt += "\n- Provide concise, straightforward implementations"
        elif user.learning_goal == LearningGoal.EXAM_PREP:
            system_prompt += "\n- Focus on commonly tested patterns and algorithms"
        else:
            system_prompt += "\n- Provide comprehensive, production-quality code"
        
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
                "\n\nCODE EXAMPLES FROM YOUR DOCUMENTS:\n{document_context}\n\nIMPORTANT: If code examples are provided above:\n- Study the patterns and style\n- Follow similar naming conventions\n- Use similar error handling approaches\n- Adapt the structure to fit the current task",
                ""
            ).format(question=question)
        
        if memory_context_str:
            formatted_prompt += memory_context_str
        
        return formatted_prompt
    
    def _format_response(
        self,
        response: CodeGenerationResponse,
        user_profile: Optional[UserProfile],
        has_rag_context: bool
    ) -> str:
        """Format structured response into readable text."""
        output = []
        language = user_profile.preferred_code_language if user_profile else "python"
        
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
        
        if has_rag_context:
            output.append("\n💡 *Informed by examples from your documents.*")
        
        return "".join(output)


async def generate_code_streaming(
    question: str,
    user_profile: Optional[UserProfile] = None,
    memory_context: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """
    Stream code generation token by token.
    Used by workflow streaming nodes.
    """
    llm = get_llm(temperature=0.3)
    
    # Use class method to get instructions
    helper = CodeHelper()
    system_prompt = helper._get_code_instructions(user_profile)
    
    language = user_profile.preferred_code_language if user_profile else "python"
    
    prompt = system_prompt + f"""

Generate {language} code for the following request:

{question}

Provide clean, working code with clear explanations."""

    if memory_context and memory_context.get("relevant_concepts"):
        prompt += f"\n\nUser is familiar with: {', '.join(memory_context['relevant_concepts'])}"

    async for chunk in llm.astream(prompt):
        if hasattr(chunk, 'content') and chunk.content:
            yield chunk.content


__all__ = [
    "CodeHelper",
    "generate_code_streaming",
]
