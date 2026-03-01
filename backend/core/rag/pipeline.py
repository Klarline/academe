"""RAG (Retrieval-Augmented Generation) pipeline for Academe."""

import logging
import re
from typing import List, Dict, Optional, Any, Tuple

from core.vectors import SemanticSearchService, HybridSearchService
from core.documents import DocumentManager
from core.documents.storage import ChunkRepository
from core.models import UserProfile, Document, DocumentSearchResult
from core.config import get_llm
from core.rag.query_rewriter import QueryRewriter, HyDE
from core.rag.adaptive_retrieval import AdaptiveRetriever
from core.rag.response_cache import SemanticResponseCache
from core.rag.self_rag import SelfRAGController
from core.rag.query_decomposer import QueryDecomposer, retrieve_with_decomposition
from core.rag.feedback import RetrievalFeedback
from core.rag.proposition_indexer import (
    PropositionExtractor, PropositionRepository, Proposition,
)
from core.rag.knowledge_graph import (
    KGExtractor, KnowledgeGraphRepository, KnowledgeGraphTraverser,
)

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Pipeline for RAG-based question answering."""

    def __init__(
        self,
        search_service: Optional[SemanticSearchService] = None,
        document_manager: Optional[DocumentManager] = None,
        use_hybrid_search: bool = True,
        use_query_rewriting: bool = True,
        use_hyde: bool = False,
        use_adaptive_retrieval: bool = True,
        use_multi_query: bool = True,
        use_self_rag: bool = True,
        use_query_decomposition: bool = True,
        use_response_cache: bool = True,
        use_propositions: bool = True,
        use_knowledge_graph: bool = True,
    ):
        """
        Initialize RAG pipeline.

        Args:
            search_service: Semantic search service (or HybridSearchService)
            document_manager: Document manager
            use_hybrid_search: Use hybrid BM25+vector search (default True)
            use_query_rewriting: Use LLM-based query rewriting (default True)
            use_hyde: Use HyDE for retrieval (default False — enable per-query)
            use_adaptive_retrieval: Use AdaptiveRetriever for query-type strategies
            use_multi_query: Generate multiple query variants for broader recall
            use_self_rag: Verify retrieval quality and retry if insufficient
            use_query_decomposition: Split complex questions into sub-queries
            use_response_cache: Cache answers by semantic similarity
            use_propositions: Extract and index atomic propositions from chunks
            use_knowledge_graph: Extract entity-relationship triples for multi-hop
        """
        base_search = search_service or SemanticSearchService()
        if use_hybrid_search and not isinstance(base_search, HybridSearchService):
            self.search_service = HybridSearchService(vector_search=base_search)
        else:
            self.search_service = base_search

        # Adaptive retriever wraps hybrid search with query-type strategies
        if use_adaptive_retrieval and isinstance(self.search_service, HybridSearchService):
            self.adaptive_retriever = AdaptiveRetriever(
                hybrid_search=self.search_service
            )
        else:
            self.adaptive_retriever = None

        self.document_manager = document_manager or DocumentManager()
        self.query_rewriter = QueryRewriter() if use_query_rewriting else None
        self.use_multi_query = use_multi_query
        self.hyde = HyDE() if use_hyde else None
        self.self_rag = SelfRAGController() if use_self_rag else None
        self.decomposer = QueryDecomposer() if use_query_decomposition else None
        self.response_cache = SemanticResponseCache() if use_response_cache else None
        self.feedback = RetrievalFeedback()
        self.chunk_repo = ChunkRepository()
        self.context_window = 1  # adjacent chunks to include on each side

        # Proposition-based indexing
        self.proposition_extractor = PropositionExtractor() if use_propositions else None
        self.proposition_repo = PropositionRepository() if use_propositions else None

        # Knowledge graph
        self.kg_extractor = KGExtractor() if use_knowledge_graph else None
        self.kg_repo = KnowledgeGraphRepository() if use_knowledge_graph else None

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

        # Extract propositions for fine-grained retrieval
        prop_count = 0
        if self.proposition_extractor and self.proposition_repo:
            try:
                propositions = self.proposition_extractor.extract_from_chunks(
                    chunks, document.id, user_id
                )
                prop_count = self.proposition_repo.store_propositions(propositions)
            except Exception as e:
                logger.warning(f"Proposition extraction failed (non-fatal): {e}")

        # Extract knowledge graph triples
        kg_count = 0
        if self.kg_extractor and self.kg_repo:
            try:
                triples = self.kg_extractor.extract_from_chunks(chunks, document.id)
                kg_count = self.kg_repo.store_triples(triples)
            except Exception as e:
                logger.warning(f"KG extraction failed (non-fatal): {e}")

        extras = []
        if prop_count:
            extras.append(f"{prop_count} propositions")
        if kg_count:
            extras.append(f"{kg_count} KG triples")
        extra_msg = f", {', '.join(extras)}" if extras else ""

        return True, f"Document uploaded and indexed: {len(chunks)} chunks{extra_msg}", document

    def record_feedback(
        self,
        user_id: str,
        query: str,
        answer: str,
        sources: List[Dict[str, Any]],
        rating: int,
        comment: Optional[str] = None,
    ) -> str:
        """
        Record user feedback (thumbs up/down) on a RAG response.

        Args:
            user_id: User ID.
            query: The original query.
            answer: The generated answer.
            sources: Source info list.
            rating: 1 (positive) or -1 (negative).
            comment: Optional user comment.

        Returns:
            Feedback entry ID.
        """
        return self.feedback.record(
            user_id=user_id,
            query=query,
            answer=answer,
            sources=sources,
            rating=rating,
            comment=comment,
        )

    def query_with_context(
        self,
        query: str,
        user: UserProfile,
        top_k: int = 5,
        use_reranking: bool = True,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_hyde: Optional[bool] = None,
        **search_kwargs
    ) -> Tuple[str, List[DocumentSearchResult]]:
        """
        Answer a query using the full RAG pipeline.

        Flow:
        1. Check semantic response cache
        2. Query rewriting (pronoun resolution, term expansion)
        3. Query decomposition (split complex questions)
        4. Multi-query generation (alternative phrasings)
        5. Adaptive retrieval (query-type-aware strategy)
        6. Self-RAG verification (check sufficiency, retry if needed)
        7. Context building (sliding window / parent-child expansion)
        8. LLM generation
        9. Cache the result

        Args:
            query: User's question
            user: User profile
            top_k: Number of context chunks to retrieve
            use_reranking: Whether to use reranking
            conversation_history: Recent messages for query rewriting
            use_hyde: Use HyDE for this query (None = use pipeline default)
            **search_kwargs: Additional search parameters

        Returns:
            Tuple of (answer, source_chunks)
        """
        # Step 0: Check response cache
        if self.response_cache:
            try:
                embedding_service = self._get_embedding_service()
                if embedding_service:
                    q_embedding = embedding_service.generate_embedding(query)
                    cached = self.response_cache.get(query, q_embedding)
                    if cached:
                        return cached  # (answer, sources)
            except Exception as e:
                logger.debug(f"Cache lookup failed: {e}")

        # Step 1: Query rewriting (resolve pronouns, expand terms)
        search_query = query
        if self.query_rewriter and conversation_history:
            search_query = self.query_rewriter.rewrite(query, conversation_history)

        # Step 2: Retrieve (with decomposition, multi-query, adaptive, self-rag)
        search_results = self._full_search(
            query=search_query,
            user_id=user.id,
            top_k=top_k,
            use_reranking=use_reranking,
            use_hyde=use_hyde if use_hyde is not None else (self.hyde is not None),
            **search_kwargs,
        )

        if not search_results:
            return self._generate_no_context_answer(query, user), []

        # Build context from search results
        context = self._build_context(search_results)

        # Augment with knowledge graph context for multi-hop reasoning
        kg_context = self._get_kg_context(query, search_results)
        if kg_context:
            context = context + "\n\n" + kg_context

        # Generate answer with original query (not rewritten) for natural response
        answer = self._generate_answer(query, context, user)

        # Cache the result
        if self.response_cache:
            try:
                embedding_service = self._get_embedding_service()
                if embedding_service:
                    q_embedding = embedding_service.generate_embedding(query)
                    self.response_cache.put(query, q_embedding, answer, search_results)
            except Exception as e:
                logger.debug(f"Cache put failed: {e}")

        return answer, search_results

    def _get_embedding_service(self):
        """Get the embedding service from the search stack."""
        if isinstance(self.search_service, HybridSearchService):
            return self.search_service.vector_search.embedding_service
        return getattr(self.search_service, "embedding_service", None)

    def _get_kg_context(
        self, query: str, search_results: List[DocumentSearchResult]
    ) -> str:
        """
        Build knowledge graph context for multi-hop reasoning.

        Loads triples from documents referenced in search results, then
        traverses the graph from entities mentioned in the query to find
        related facts that may not appear in the retrieved chunks.
        """
        if not self.kg_repo:
            return ""

        try:
            # Collect triples from all documents in the search results
            doc_ids = {r.chunk.document_id for r in search_results}
            all_triples = []
            for doc_id in doc_ids:
                all_triples.extend(self.kg_repo.get_document_triples(doc_id))

            if not all_triples:
                return ""

            traverser = KnowledgeGraphTraverser(all_triples)

            # Extract key terms from query for graph traversal
            query_terms = self._extract_query_entities(query)
            all_paths = []
            for term in query_terms:
                paths = traverser.multi_hop(term, max_hops=2, max_results=10)
                all_paths.extend(paths)

            return traverser.format_context(all_paths, max_triples=10)
        except Exception as e:
            logger.debug(f"KG context generation failed: {e}")
            return ""

    @staticmethod
    def _extract_query_entities(query: str) -> List[str]:
        """Extract potential entity mentions from a query for graph lookup."""
        stop_words = {
            "what", "how", "why", "when", "where", "which", "who", "is", "are",
            "was", "were", "do", "does", "did", "the", "a", "an", "in", "on",
            "at", "to", "for", "of", "with", "by", "from", "and", "or", "not",
            "can", "could", "would", "should", "will", "this", "that", "it",
            "its", "be", "been", "being", "have", "has", "had", "about", "into",
            "used", "using", "between", "explain", "describe", "tell", "me",
        }
        words = re.findall(r"\b[a-zA-Z]{2,}\b", query.lower())
        entities = [w for w in words if w not in stop_words]
        # Also try bigrams
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)
                    if words[i] not in stop_words and words[i+1] not in stop_words]
        return bigrams + entities

    def _full_search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_hyde: bool = False,
        **search_kwargs,
    ) -> List[DocumentSearchResult]:
        """
        Full search pipeline: decompose → multi-query → adaptive → self-rag.

        Layers applied in order:
        1. Query decomposition (if complex question)
        2. Multi-query expansion (alternative phrasings)
        3. AdaptiveRetriever or standard _search
        4. Self-RAG verification + retry
        """
        base_kwargs = dict(
            user_id=user_id,
            top_k=top_k,
            use_reranking=use_reranking,
            use_hyde=use_hyde,
            **search_kwargs,
        )

        # Layer 1: Query decomposition
        if self.decomposer:
            try:
                results = retrieve_with_decomposition(
                    query=query,
                    search_fn=lambda **kw: self._adaptive_or_base_search(**kw),
                    decomposer=self.decomposer,
                    **base_kwargs,
                )
                if results:
                    return self._maybe_verify(query, results, base_kwargs)
            except Exception as e:
                logger.warning(f"Decomposition failed, falling back: {e}")

        # Layer 2: Multi-query expansion
        if self.use_multi_query and self.query_rewriter:
            try:
                results = self._search_multi_query(query=query, **base_kwargs)
                if results:
                    return self._maybe_verify(query, results, base_kwargs)
            except Exception as e:
                logger.warning(f"Multi-query failed, falling back: {e}")

        # Layer 3: Standard adaptive/base search
        results = self._adaptive_or_base_search(query=query, **base_kwargs)

        # Layer 4: Self-RAG verification
        return self._maybe_verify(query, results, base_kwargs)

    def _adaptive_or_base_search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        use_reranking: bool = True,
        **kwargs,
    ) -> List[DocumentSearchResult]:
        """Use AdaptiveRetriever if available, else fall back to _search."""
        kwargs.pop("use_hyde", None)
        if self.adaptive_retriever:
            return self.adaptive_retriever.retrieve(
                query=query,
                user_id=user_id,
                top_k=top_k,
                use_reranking=use_reranking,
            )
        return self._search(
            query=query,
            user_id=user_id,
            top_k=top_k,
            use_reranking=use_reranking,
        )

    def _search_multi_query(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        use_reranking: bool = True,
        **kwargs,
    ) -> List[DocumentSearchResult]:
        """
        Generate multiple query variants and merge results.

        Retrieves for each variant and deduplicates by (doc_id, chunk_index),
        keeping the highest score for each chunk.
        """
        variants = self.query_rewriter.generate_multi_query(query, num_queries=3)

        all_results: Dict[str, DocumentSearchResult] = {}
        per_variant_k = max(3, top_k)

        for variant in variants:
            results = self._adaptive_or_base_search(
                query=variant,
                user_id=user_id,
                top_k=per_variant_k,
                use_reranking=use_reranking,
            )
            for r in results:
                key = f"{r.chunk.document_id}_{r.chunk.chunk_index}"
                if key not in all_results or r.score > all_results[key].score:
                    all_results[key] = r

        merged = sorted(all_results.values(), key=lambda r: r.score, reverse=True)
        for i, r in enumerate(merged):
            r.rank = i + 1
        return merged[:top_k]

    def _maybe_verify(
        self,
        query: str,
        results: List[DocumentSearchResult],
        search_kwargs: Dict[str, Any],
    ) -> List[DocumentSearchResult]:
        """Apply Self-RAG verification if enabled."""
        if not self.self_rag or not results:
            return results

        try:
            return self.self_rag.search_with_verification(
                query=query,
                search_fn=lambda **kw: self._adaptive_or_base_search(**kw),
                user_id=search_kwargs["user_id"],
                top_k=search_kwargs.get("top_k", 5),
                use_reranking=search_kwargs.get("use_reranking", True),
            )
        except Exception as e:
            logger.warning(f"Self-RAG verification failed: {e}")
            return results

    def _search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_hyde: bool = False,
        **search_kwargs,
    ) -> List[DocumentSearchResult]:
        """
        Internal search dispatcher: hybrid, HyDE, or plain vector.

        When use_hyde=True, generates a hypothetical answer, embeds it,
        and uses that embedding for vector search (then reranks normally).
        """
        # HyDE path: use hypothetical answer embedding for vector search
        if use_hyde and self.hyde:
            try:
                return self._search_with_hyde(
                    query, user_id, top_k, use_reranking, **search_kwargs
                )
            except Exception as e:
                logger.warning(f"HyDE search failed, falling back to standard: {e}")

        # Standard path: hybrid or vector
        if isinstance(self.search_service, HybridSearchService):
            if use_reranking:
                return self.search_service.hybrid_search_with_reranking(
                    query=query, user_id=user_id, top_k=top_k, **search_kwargs
                )
            return self.search_service.hybrid_search(
                query=query, user_id=user_id, top_k=top_k, **search_kwargs
            )
        elif use_reranking:
            return self.search_service.search_with_reranking(
                query=query, user_id=user_id, top_k=top_k * 2,
                rerank_top_k=top_k, **search_kwargs
            )
        return self.search_service.search(
            query=query, user_id=user_id, top_k=top_k, **search_kwargs
        )

    def _search_with_hyde(
        self,
        query: str,
        user_id: str,
        top_k: int,
        use_reranking: bool,
        **search_kwargs,
    ) -> List[DocumentSearchResult]:
        """Search using HyDE embedding + BM25 fusion + reranking."""
        from core.models.document import DocumentChunk

        # Get HyDE embedding
        hyde_embedding = self.hyde.get_hypothesis_embedding(query)

        # Get the underlying vector search components
        if isinstance(self.search_service, HybridSearchService):
            vs = self.search_service.vector_search
        else:
            vs = self.search_service

        # Vector search with HyDE embedding
        pinecone_results = vs.pinecone_manager.search_similar_chunks(
            user_id=user_id,
            query_embedding=hyde_embedding,
            top_k=top_k * 4,
        )

        # Convert to DocumentSearchResult objects (same as SemanticSearchService.search)
        search_results = []
        for i, result in enumerate(pinecone_results):
            if result.get("score", 0) < 0.2:
                continue
            vec_id = result["id"]
            parts = vec_id.split("_")
            if len(parts) < 2:
                continue
            document_id = "_".join(parts[:-1])
            chunk_index = int(parts[-1])
            document = vs.doc_repo.get_document(document_id)
            if not document:
                continue
            chunk = DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                chunk_index=chunk_index,
                content=result["metadata"].get("content", ""),
                page_number=result["metadata"].get("page_number"),
                section_title=result["metadata"].get("section_title"),
                char_count=len(result["metadata"].get("content", "")),
                word_count=len(result["metadata"].get("content", "").split()),
                has_code=result["metadata"].get("has_code", False),
                has_equations=result["metadata"].get("has_equations", False),
            )
            search_results.append(
                DocumentSearchResult(chunk=chunk, document=document, score=result["score"], rank=i + 1)
            )

        # Rerank with cross-encoder using the ORIGINAL query (not hypothesis)
        if use_reranking and search_results:
            search_results = vs.rerank_results(query, search_results, top_k=top_k)

        return search_results[:top_k]

    def _build_context(self, search_results: List[DocumentSearchResult]) -> str:
        """
        Build context string from search results with sliding-window expansion.

        For each retrieved chunk, fetches ±context_window adjacent chunks from
        the same document so the LLM sees surrounding text.  If parent-child
        metadata is present, the parent content is used instead.

        Deduplicates so overlapping windows don't repeat text.

        Args:
            search_results: List of search results

        Returns:
            Formatted context string
        """
        context_parts = []
        seen_chunks: set = set()  # (document_id, chunk_index)

        for result in search_results:
            doc_id = result.chunk.document_id
            source_info = f"[Source: {result.document.title or result.document.original_filename}"
            if result.chunk.page_number:
                source_info += f", Page {result.chunk.page_number}"
            if result.chunk.section_title:
                source_info += f", Section: {result.chunk.section_title}"
            source_info += "]"

            # Parent-child: if chunk has parent_content in metadata, use it
            parent_content = (result.chunk.metadata or {}).get("parent_content")
            if parent_content:
                parent_idx = result.chunk.metadata.get("parent_chunk_index")
                key = (doc_id, f"parent_{parent_idx}")
                if key not in seen_chunks:
                    seen_chunks.add(key)
                    context_parts.append(f"{source_info}\n{parent_content}\n")
                continue

            # Sliding window: expand with adjacent chunks
            if self.context_window > 0:
                try:
                    neighbors = self.chunk_repo.get_adjacent_chunks(
                        doc_id, result.chunk.chunk_index, window=self.context_window
                    )
                    if neighbors:
                        merged_parts = []
                        for nb in neighbors:
                            key = (doc_id, nb.chunk_index)
                            if key not in seen_chunks:
                                seen_chunks.add(key)
                                merged_parts.append(nb.content)
                        if merged_parts:
                            context_parts.append(
                                f"{source_info}\n" + "\n".join(merged_parts) + "\n"
                            )
                        continue
                except Exception as e:
                    logger.debug(f"Sliding window fallback: {e}")

            # Fallback: just use the retrieved chunk
            key = (doc_id, result.chunk.chunk_index)
            if key not in seen_chunks:
                seen_chunks.add(key)
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
        if isinstance(self.search_service, HybridSearchService):
            results = self.search_service.hybrid_search(
                query=query,
                user_id=user_id,
                top_k=top_k * 2,
            )
        else:
            results = self.search_service.search(
                query=query,
                user_id=user_id,
                top_k=top_k * 2,
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