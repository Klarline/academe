"""
Query rewriting for better retrieval.

Two modes:
1. LLM-based rewrite: Resolves pronouns/references from conversation
   context and expands queries with relevant terms.
2. HyDE: Generates a hypothetical answer, embeds it, and uses that
   embedding for retrieval (closer to document embeddings than a short query).

Uses OpenAI (gpt-4o-mini) for speed and instruction-following quality.
Falls back to primary LLM if OpenAI key unavailable.
"""

import logging
from typing import List, Dict, Optional, Any

from core.config import get_openai_llm

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    Rewrite user queries for better retrieval.

    Handles:
    - Conversational dereference: "explain it" → "explain PCA"
    - Query expansion: adds relevant technical synonyms
    - Multi-query: generates alternative phrasings
    """

    def __init__(self, llm=None):
        self._llm = llm

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_openai_llm(model="gpt-4o-mini", temperature=0.0)
        return self._llm

    def rewrite(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Rewrite a query using conversation context.

        Resolves pronouns, references, and ambiguity. If the query is
        already self-contained, returns it unchanged.

        Args:
            query: Current user query
            conversation_history: Recent messages [{role, content}, ...]

        Returns:
            Rewritten query optimized for retrieval
        """
        if not conversation_history:
            return query

        history_text = self._format_history(conversation_history[-5:])

        prompt = f"""You are a search query optimizer. Rewrite the user's query to be
self-contained and effective for searching academic documents.

Rules:
- Resolve ALL pronouns and references using conversation history
- Keep the rewritten query concise (1-2 sentences max)
- Include specific technical terms mentioned in history
- If the query is already self-contained, return it unchanged
- Return ONLY the rewritten query, nothing else

Conversation history:
{history_text}

Current query: {query}

Rewritten query:"""

        try:
            response = self.llm.invoke(prompt)
            rewritten = response.content.strip().strip('"')
            if rewritten and len(rewritten) > 3:
                logger.info(f"Query rewritten: '{query}' -> '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")

        return query

    def generate_multi_query(
        self,
        query: str,
        num_queries: int = 3,
    ) -> List[str]:
        """
        Generate multiple phrasings of the same query.

        Different phrasings retrieve different relevant chunks.
        Useful for comparison or broad-topic queries.

        Args:
            query: Original query
            num_queries: Number of alternative queries to generate

        Returns:
            List of query variations (including original)
        """
        prompt = f"""Generate {num_queries} different phrasings of this search query.
Each should approach the topic from a different angle to find different relevant documents.

Original query: {query}

Return each query on a new line, numbered 1-{num_queries}. No other text."""

        try:
            response = self.llm.invoke(prompt)
            lines = response.content.strip().split("\n")
            queries = [query]  # Always include original
            for line in lines:
                cleaned = line.strip().lstrip("0123456789.-) ").strip()
                if cleaned and cleaned != query and len(cleaned) > 5:
                    queries.append(cleaned)
            return queries[:num_queries + 1]
        except Exception as e:
            logger.warning(f"Multi-query generation failed: {e}")
            return [query]

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        lines = []
        for msg in history:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


class HyDE:
    """
    Hypothetical Document Embeddings.

    Instead of embedding the short query, generate a hypothetical answer
    and embed that. The hypothesis embedding is closer in vector space
    to actual document chunks than the query embedding.

    Paper: https://arxiv.org/abs/2212.10496
    """

    def __init__(self, llm=None, embedding_service=None):
        self._llm = llm
        self._embedding_service = embedding_service

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_openai_llm(model="gpt-4o-mini", temperature=0.3)
        return self._llm

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from core.vectors.embeddings import create_embedding_service
            self._embedding_service = create_embedding_service()
        return self._embedding_service

    def generate_hypothesis(self, query: str) -> str:
        """
        Generate a hypothetical document passage that would answer the query.

        Args:
            query: User's question

        Returns:
            Hypothetical passage (1-2 paragraphs)
        """
        prompt = f"""Write a short academic textbook passage (1-2 paragraphs) that
directly answers this question. Write as if you are a textbook author.
Include specific technical terms and definitions.

Question: {query}

Passage:"""

        try:
            response = self.llm.invoke(prompt)
            hypothesis = response.content.strip()
            if hypothesis:
                logger.info(f"HyDE hypothesis generated ({len(hypothesis)} chars)")
                return hypothesis
        except Exception as e:
            logger.warning(f"HyDE hypothesis generation failed: {e}")

        return query  # Fall back to original query

    def get_hypothesis_embedding(self, query: str) -> List[float]:
        """
        Generate embedding from hypothetical answer.

        Args:
            query: User's question

        Returns:
            Embedding vector of the hypothetical answer
        """
        hypothesis = self.generate_hypothesis(query)
        return self.embedding_service.generate_embedding(hypothesis)

    def search_with_hyde(
        self,
        query: str,
        user_id: str,
        pinecone_manager,
        top_k: int = 10,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search using HyDE embedding instead of query embedding.

        Args:
            query: User's question
            user_id: User ID
            pinecone_manager: PineconeManager for vector search
            top_k: Number of results
            metadata_filter: Optional metadata filter

        Returns:
            Pinecone search results
        """
        hyde_embedding = self.get_hypothesis_embedding(query)

        return pinecone_manager.search_similar_chunks(
            user_id=user_id,
            query_embedding=hyde_embedding,
            top_k=top_k,
            filter=metadata_filter,
        )
