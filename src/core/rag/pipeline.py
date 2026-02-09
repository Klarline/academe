"""RAG (Retrieval-Augmented Generation) pipeline for Academe."""

import logging
from typing import List, Dict, Optional, Any, Tuple

from core.vectors import SemanticSearchService
from core.documents import DocumentManager
from core.models import UserProfile, Document, DocumentSearchResult
from core.config import get_llm

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Pipeline for RAG-based question answering."""

    def __init__(
        self,
        search_service: Optional[SemanticSearchService] = None,
        document_manager: Optional[DocumentManager] = None
    ):
        """
        Initialize RAG pipeline.

        Args:
            search_service: Semantic search service
            document_manager: Document manager
        """
        self.search_service = search_service or SemanticSearchService()
        self.document_manager = document_manager or DocumentManager()

    def process_document_upload(
        self,
        file_path: str,
        user_id: str,
        title: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str, Optional[Document]]:
        """
        Upload and index a document for RAG.

        Args:
            file_path: Path to document
            user_id: User ID
            title: Document title
            **kwargs: Additional document metadata

        Returns:
            Tuple of (success, message, document)
        """
        # Upload and process document
        success, message, document = self.document_manager.upload_document(
            file_path=file_path,
            user_id=user_id,
            title=title,
            **kwargs
        )

        if not success or not document:
            return success, message, document

        # Get chunks
        chunks = self.document_manager.get_document_chunks(
            document.id,
            user_id
        )

        if not chunks:
            return False, "No chunks created for document", document

        # Index for semantic search
        index_success, index_message = self.search_service.index_document(
            document,
            chunks
        )

        if not index_success:
            return False, f"Document processed but indexing failed: {index_message}", document

        return True, f"Document uploaded and indexed: {len(chunks)} chunks", document

    def query_with_context(
        self,
        query: str,
        user: UserProfile,
        top_k: int = 5,
        use_reranking: bool = True,
        **search_kwargs
    ) -> Tuple[str, List[DocumentSearchResult]]:
        """
        Answer a query using RAG.

        Args:
            query: User's question
            user: User profile
            top_k: Number of context chunks to retrieve
            use_reranking: Whether to use reranking
            **search_kwargs: Additional search parameters

        Returns:
            Tuple of (answer, source_chunks)
        """
        # Search for relevant chunks
        if use_reranking:
            search_results = self.search_service.search_with_reranking(
                query=query,
                user_id=user.id,
                top_k=top_k * 2,
                rerank_top_k=top_k,
                **search_kwargs
            )
        else:
            search_results = self.search_service.search(
                query=query,
                user_id=user.id,
                top_k=top_k,
                **search_kwargs
            )

        if not search_results:
            return self._generate_no_context_answer(query, user), []

        # Build context from search results
        context = self._build_context(search_results)

        # Generate answer with context
        answer = self._generate_answer(query, context, user)

        return answer, search_results

    def _build_context(self, search_results: List[DocumentSearchResult]) -> str:
        """
        Build context string from search results.

        Args:
            search_results: List of search results

        Returns:
            Formatted context string
        """
        context_parts = []

        for result in search_results:
            # Format each chunk with source information
            source_info = f"[Source: {result.document.title or result.document.original_filename}"
            if result.chunk.page_number:
                source_info += f", Page {result.chunk.page_number}"
            if result.chunk.section_title:
                source_info += f", Section: {result.chunk.section_title}"
            source_info += "]"

            context_parts.append(f"{source_info}\n{result.chunk.content}\n")

        return "\n---\n".join(context_parts)

    def _generate_answer(
        self,
        query: str,
        context: str,
        user: UserProfile
    ) -> str:
        """
        Generate answer using LLM with context.

        Args:
            query: User's question
            context: Retrieved context
            user: User profile

        Returns:
            Generated answer
        """
        # Get user's learning preferences
        user_context = user.get_prompt_context() if user else ""

        # Build prompt
        prompt = f"""You are an expert academic assistant helping a student understand their course materials.

User Profile:
{user_context}

Context from the user's documents:
{context}

Question: {query}

Instructions:
1. Answer based primarily on the provided context from the user's documents
2. Cite specific sources when referencing information
3. Adapt your explanation to the user's learning level and style
4. If the context doesn't fully answer the question, acknowledge this
5. Provide a clear, well-structured response

Answer:"""

        try:
            # Get LLM and generate response
            llm = get_llm(temperature=0.7)
            response = llm.invoke(prompt)

            # Extract content from response
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return f"I encountered an error generating the answer: {str(e)}"

    def _generate_no_context_answer(
        self,
        query: str,
        user: UserProfile
    ) -> str:
        """
        Generate answer when no relevant context is found.

        Args:
            query: User's question
            user: User profile

        Returns:
            Generated answer
        """
        return (
            "I couldn't find relevant information in your uploaded documents to answer this question. "
            "Please make sure you've uploaded documents related to your query, or try rephrasing your question. "
            "You can also ask me general questions, and I'll do my best to help based on my knowledge."
        )

    def explain_with_sources(
        self,
        query: str,
        user: UserProfile,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Answer query with detailed source attribution.

        Args:
            query: User's question
            user: User profile
            top_k: Number of sources to use

        Returns:
            Dictionary with answer and source details
        """
        answer, sources = self.query_with_context(query, user, top_k)

        # Format sources for display
        source_list = []
        for i, source in enumerate(sources, 1):
            source_info = {
                "rank": i,
                "document": source.document.title or source.document.original_filename,
                "page": source.chunk.page_number,
                "section": source.chunk.section_title,
                "relevance_score": round(source.score, 3),
                "excerpt": source.chunk.content[:200] + "..." if len(source.chunk.content) > 200 else source.chunk.content
            }
            source_list.append(source_info)

        return {
            "answer": answer,
            "sources": source_list,
            "sources_used": len(sources),
            "query": query
        }

    def generate_summary(
        self,
        document_id: str,
        user_id: str,
        user: Optional[UserProfile] = None
    ) -> str:
        """
        Generate a summary of a document.

        Args:
            document_id: Document ID
            user_id: User ID
            user: User profile

        Returns:
            Document summary
        """
        # Get document
        document = self.document_manager.doc_repo.get_document(document_id)
        if not document or document.user_id != user_id:
            return "Document not found or access denied."

        # Get chunks
        chunks = self.document_manager.get_document_chunks(document_id, user_id)
        if not chunks:
            return "No content found for this document."

        # Take first few and last few chunks for summary
        sample_chunks = chunks[:3] + chunks[-2:] if len(chunks) > 5 else chunks

        # Build content for summary
        content = "\n\n".join([chunk.content for chunk in sample_chunks])

        # Generate summary
        prompt = f"""Provide a concise summary of this document.

Document: {document.title or document.original_filename}
Content Sample:
{content[:3000]}  # Limit content length

Provide a 3-5 paragraph summary covering:
1. Main topic and purpose
2. Key concepts or findings
3. Important conclusions or takeaways

Summary:"""

        try:
            llm = get_llm(temperature=0.5)
            response = llm.invoke(prompt)

            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "Failed to generate summary."

    def find_related_content(
        self,
        query: str,
        user_id: str,
        current_document_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find related content across user's documents.

        Args:
            query: Search query or topic
            user_id: User ID
            current_document_id: Exclude this document from results
            top_k: Number of results

        Returns:
            List of related content
        """
        # Search across all documents
        results = self.search_service.search(
            query=query,
            user_id=user_id,
            top_k=top_k * 2  # Get more to filter
        )

        # Filter out current document if specified
        if current_document_id:
            results = [
                r for r in results
                if r.document.id != current_document_id
            ]

        # Group by document
        doc_results = {}
        for result in results[:top_k]:
            doc_id = result.document.id
            if doc_id not in doc_results:
                doc_results[doc_id] = {
                    "document": result.document.title or result.document.original_filename,
                    "document_id": doc_id,
                    "chunks": []
                }

            doc_results[doc_id]["chunks"].append({
                "content": result.chunk.content[:200] + "...",
                "page": result.chunk.page_number,
                "score": round(result.score, 3)
            })

        return list(doc_results.values())