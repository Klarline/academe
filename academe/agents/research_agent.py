"""
Research Agent - RAG-powered document question answering for Academe.

This agent uses the RAG pipeline to answer questions based on the user's
uploaded documents, providing citations and personalized explanations.
"""

from typing import Optional, Dict, List, Any
from academe.config import get_llm
from academe.models import UserProfile
from academe.rag import RAGPipeline
from academe.vectors import SemanticSearchService
from academe.documents import DocumentManager


class ResearchAgent:
    """Agent that answers questions using user's documents."""

    def __init__(
        self,
        rag_pipeline: Optional[RAGPipeline] = None,
        search_service: Optional[SemanticSearchService] = None,
        document_manager: Optional[DocumentManager] = None
    ):
        """
        Initialize research agent.

        Args:
            rag_pipeline: RAG pipeline for Q&A
            search_service: Semantic search service
            document_manager: Document manager
        """
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.search_service = search_service or SemanticSearchService()
        self.document_manager = document_manager or DocumentManager()

    def answer_question(
        self,
        question: str,
        user: UserProfile,
        use_citations: bool = True,
        top_k: int = 5
    ) -> str:
        """
        Answer a question using the user's documents.

        Args:
            question: User's question
            user: User profile
            use_citations: Whether to include source citations
            top_k: Number of context chunks to use

        Returns:
            Answer with optional citations
        """
        # Check if user has documents
        documents = self.document_manager.get_user_documents(user.id)
        if not documents:
            return self._no_documents_response(question, user)

        # Use RAG pipeline to get answer
        answer, sources = self.rag_pipeline.query_with_context(
            query=question,
            user=user,
            top_k=top_k,
            use_reranking=True
        )

        # Format response with citations if requested
        if use_citations and sources:
            answer = self._add_citations(answer, sources)

        return answer

    def research_topic(
        self,
        topic: str,
        user: UserProfile,
        depth: str = "standard"
    ) -> str:
        """
        Research a topic comprehensively across user's documents.

        Args:
            topic: Topic to research
            user: User profile
            depth: Research depth (quick/standard/deep)

        Returns:
            Comprehensive research summary
        """
        # Determine number of sources based on depth
        depth_config = {
            "quick": {"top_k": 3, "sections": 2},
            "standard": {"top_k": 5, "sections": 3},
            "deep": {"top_k": 10, "sections": 5}
        }
        config = depth_config.get(depth, depth_config["standard"])

        # Get relevant information
        answer, sources = self.rag_pipeline.query_with_context(
            query=f"Provide comprehensive information about {topic}",
            user=user,
            top_k=config["top_k"]
        )

        # Find related topics
        related = self.rag_pipeline.find_related_content(
            query=topic,
            user_id=user.id,
            top_k=3
        )

        # Build comprehensive response
        response = self._format_research_response(
            topic=topic,
            main_content=answer,
            sources=sources,
            related_topics=related,
            user=user
        )

        return response

    def summarize_document(
        self,
        document_id: str,
        user: UserProfile
    ) -> str:
        """
        Generate a summary of a specific document.

        Args:
            document_id: Document to summarize
            user: User profile

        Returns:
            Document summary
        """
        return self.rag_pipeline.generate_summary(
            document_id=document_id,
            user_id=user.id,
            user=user
        )

    def compare_concepts(
        self,
        concept1: str,
        concept2: str,
        user: UserProfile
    ) -> str:
        """
        Compare and contrast two concepts from documents.

        Args:
            concept1: First concept
            concept2: Second concept
            user: User profile

        Returns:
            Comparison analysis
        """
        # Get information about both concepts
        info1, sources1 = self.rag_pipeline.query_with_context(
            query=f"Explain {concept1}",
            user=user,
            top_k=3
        )

        info2, sources2 = self.rag_pipeline.query_with_context(
            query=f"Explain {concept2}",
            user=user,
            top_k=3
        )

        # Generate comparison
        comparison_prompt = f"""Compare and contrast {concept1} and {concept2}.

Information about {concept1}:
{info1[:500]}

Information about {concept2}:
{info2[:500]}

Provide a comparison covering:
1. Key similarities
2. Main differences
3. When to use each
4. Practical implications

Adapt the explanation to the user's learning level: {user.learning_level.value}"""

        try:
            llm = get_llm(temperature=0.7)
            response = llm.invoke(comparison_prompt)

            comparison = response.content if hasattr(response, 'content') else str(response)

            # Add sources
            all_sources = sources1 + sources2
            if all_sources:
                comparison = self._add_citations(comparison, all_sources[:5])

            return comparison

        except Exception as e:
            return f"Unable to compare concepts: {str(e)}"

    def find_examples(
        self,
        concept: str,
        user: UserProfile,
        num_examples: int = 3
    ) -> str:
        """
        Find examples of a concept from the user's documents.

        Args:
            concept: Concept to find examples for
            user: User profile
            num_examples: Number of examples to find

        Returns:
            Examples with context
        """
        # Search for examples
        results = self.search_service.search(
            query=f"{concept} example implementation code",
            user_id=user.id,
            top_k=num_examples * 2,
            filter_has_code=True
        )

        if not results:
            results = self.search_service.search(
                query=f"{concept} example",
                user_id=user.id,
                top_k=num_examples * 2
            )

        if not results:
            return f"No examples of {concept} found in your documents."

        # Format examples
        examples = []
        for i, result in enumerate(results[:num_examples], 1):
            example = f"""Example {i} - From: {result.document.title or result.document.original_filename}
{result.chunk.get_context_string()}"""
            examples.append(example)

        response = f"Found {len(examples)} examples of {concept}:\n\n"
        response += "\n\n---\n\n".join(examples)

        return response

    def check_understanding(
        self,
        concept: str,
        user_answer: str,
        user: UserProfile
    ) -> str:
        """
        Check user's understanding of a concept against documents.

        Args:
            concept: Concept being tested
            user_answer: User's explanation
            user: User profile

        Returns:
            Feedback on understanding
        """
        # Get correct information from documents
        correct_info, sources = self.rag_pipeline.query_with_context(
            query=f"Explain {concept} accurately and completely",
            user=user,
            top_k=3
        )

        # Compare user's answer with correct information
        feedback_prompt = f"""Evaluate the user's understanding of {concept}.

Correct information from documents:
{correct_info[:800]}

User's explanation:
{user_answer}

Provide feedback that:
1. Identifies what the user understood correctly
2. Points out any misconceptions or gaps
3. Suggests areas for improvement
4. Provides encouragement

User's learning level: {user.learning_level.value}
Be {user.explanation_style.value} in your feedback."""

        try:
            llm = get_llm(temperature=0.7)
            response = llm.invoke(feedback_prompt)

            feedback = response.content if hasattr(response, 'content') else str(response)

            return feedback

        except Exception as e:
            return f"Unable to evaluate understanding: {str(e)}"

    def _no_documents_response(self, question: str, user: UserProfile) -> str:
        """Generate response when user has no documents."""
        return (
            "📚 You haven't uploaded any documents yet!\n\n"
            "To use the research features, please upload your study materials "
            "(PDFs, notes, textbooks) first. Once uploaded, I can:\n"
            "• Answer questions from your documents\n"
            "• Provide summaries and explanations\n"
            "• Find examples and related concepts\n"
            "• Generate practice problems\n\n"
            "Use the 'Upload Document' option from the main menu to get started."
        )

    def _add_citations(self, answer: str, sources: List[Any]) -> str:
        """Add citations to answer."""
        if not sources:
            return answer

        citations = "\n\n📚 Sources:\n"
        seen_docs = set()

        for source in sources:
            doc_title = source.document.title or source.document.original_filename
            if doc_title not in seen_docs:
                seen_docs.add(doc_title)
                citation = f"• {doc_title}"
                if source.chunk.page_number:
                    citation += f" (p. {source.chunk.page_number})"
                citations += citation + "\n"

        return answer + citations

    def _format_research_response(
        self,
        topic: str,
        main_content: str,
        sources: List[Any],
        related_topics: List[Dict],
        user: UserProfile
    ) -> str:
        """Format comprehensive research response."""
        response = f"# Research Summary: {topic}\n\n"

        # Add main content
        response += "## Overview\n\n"
        response += main_content + "\n\n"

        # Add related topics if found
        if related_topics:
            response += "## Related Topics in Your Documents\n\n"
            for related in related_topics:
                response += f"• **{related['document']}**: "
                if related.get('chunks'):
                    response += f"{len(related['chunks'])} relevant sections found\n"

        # Add sources
        if sources:
            response += "\n" + self._add_citations("", sources)

        return response


def create_research_agent() -> ResearchAgent:
    """
    Create a research agent instance.

    Returns:
        Configured research agent
    """
    return ResearchAgent()


# Export main components
__all__ = [
    "ResearchAgent",
    "create_research_agent"
]