# Academe RAG Architecture

## System Overview

Academe uses Retrieval-Augmented Generation (RAG) to answer student questions
about their uploaded course materials. The system retrieves relevant document
chunks and uses them as context for LLM-generated explanations.

```
                    ┌─────────────┐
                    │  User Query │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Query     │  LLM rewrites ambiguous queries;
                    │  Rewriter   │  optional HyDE hypothesis embedding
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Adaptive   │  Classifies query type
                    │  Retriever  │  (definition/comparison/code/general)
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │    Hybrid Search        │
              │  ┌──────┐  ┌────────┐  │
              │  │ BM25 │  │ Vector │  │  Weighted score fusion
              │  │ (10%) │  │ (90%) │  │  (0.1 * BM25 + 0.9 * Vector)
              │  └──────┘  └────────┘  │
              │  (contextual embeddings)│
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │Cross-Encoder│  BAAI/bge-reranker-base
                    │  Reranker   │  Reranks top-20 → top-5
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Context    │  Sliding window: ±1 neighbor chunks
                    │  Builder    │  Parent-child: expand to parent text
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Knowledge  │  Multi-hop traversal from query entities
                    │  Graph      │  Adds related facts to context
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    LLM      │  Generates answer with context + KG
                    │  (Gemini)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Response   │  Answer + source attribution
                    └─────────────┘
```

## Components

### 1. Document Ingestion Pipeline

```
Upload → Detect Type → Adaptive Chunk → Enrich → Embed → Index (Pinecone)
                              ↓                              ↓
                     Extract Propositions          Extract KG Triples
                       (atomic facts)            (entity → rel → entity)
                              ↓                              ↓
                     Store (MongoDB)              Store (MongoDB)
```

- **DocumentManager** (`core/documents/manager.py`): Orchestrates upload, type detection, chunking
  - `use_adaptive_chunking=True`: Auto-selects chunk params per document type
  - `use_parent_child=False`: Toggle two-level parent/child chunking
- **DocTypeDetector** (`core/documents/doc_type_detector.py`): Classifies content as textbook, paper, notes, code, or general from structural signals + filename hints
- **DocumentChunker** (`core/documents/chunker.py`): Multiple chunking strategies
  - `adaptive_chunk()`: Per-type profiles (textbook 1200/300, paper 800/200, notes 600/100, code 1000/150)
  - `chunk_with_parents()`: Large parent windows split into small retrieval children; children store parent content in metadata
  - Recursive, semantic, and character-level splitters
- **EmbeddingService** (`core/vectors/embeddings.py`): OpenAI text-embedding-3-small (1536 dims; falls back to sentence-transformers or mock)
- **Contextual Embedding Enrichment** (`core/vectors/search.py`): Prepends `Document: {title} | Section: {section}` to chunk text before embedding, so vectors capture document-level context
- **PineconeManager** (`core/vectors/pinecone_client.py`): Vector index with user namespaces

**Document deletion:** When a document is deleted, `DocumentManager.delete_document()` removes Pinecone vectors, propositions, KG triples, MongoDB chunks, and the file. 

### 2. Retrieval Stack

Six layers of retrieval for best precision:

| Layer | Component | Purpose |
|-------|-----------|---------|
| 1 | **SemanticResponseCache** | Skip retrieval entirely for similar past queries |
| 2 | **QueryDecomposer** | Split complex questions into atomic sub-queries |
| 3 | **Multi-query generation** | 3 phrasings per query for broader recall |
| 4 | **AdaptiveRetriever** | Query-type-aware BM25/vector weight tuning |
| 5 | **CrossEncoder Reranker** | Rerank candidates for precision |
| 6 | **SelfRAGController** | Verify context sufficiency, reformulate + retry |
| 7 | **KnowledgeGraphTraverser** | Multi-hop graph traversal adds related entity-relationship facts |

### 3. Search Flow Detail

1. **Response cache check** — If a semantically similar query was answered recently, return cached result
2. **Query rewriting** — LLM resolves pronouns and expands abbreviations using conversation history
3. **Query decomposition** — Complex multi-part questions split into atomic sub-queries
4. **Multi-query expansion** — Generate 3 alternative phrasings, retrieve for each, merge results
5. **Adaptive retrieval** — `AdaptiveRetriever` adjusts BM25/vector weights by query type
6. **Hybrid search** — BM25 handles exact terms ("PCA", "eigenvalue"), vectors handle semantics
7. **Score fusion** — Normalize + weighted combination (0.1 BM25 / 0.9 vector)
8. **Cross-encoder reranking** — Score query-document pairs for final ranking
9. **Self-RAG verification** — LLM judges if context is sufficient; reformulates + retries if not
10. **Context expansion** — Sliding window (±1 adjacent chunks) or parent-child (expand child→parent)
11. **Knowledge graph augmentation** — Multi-hop traversal from query entities through extracted triples adds related facts
12. **LLM generation** — Answer grounded in expanded context + KG relationships
13. **Cache result** — Store answer for future similar queries (reuses query embedding from step 1 to avoid double embedding)

### 3.1 HyDE (Hypothetical Document Embeddings)

When enabled (e.g. in the `deep` retrieval profile), HyDE improves semantic retrieval by:

1. **Hypothesis generation** — LLM generates a short hypothetical answer passage for the query
2. **Three-way retrieval** — Vector search with query embedding, vector search with hypothesis embedding, and BM25 keyword search (when HybridSearchService is used)
3. **Reciprocal Rank Fusion (RRF)** — Merge all three rank lists via RRF (k=60) for semantic coverage and keyword precision (e.g. exact "dropout" matches)
4. **Reranking** — Cross-encoder reranks the fused list using the original query
5. **Adaptive composition** — CODE queries: filter for `has_code` chunks (with fallback if too few); COMPARISON queries: diversify across documents/sections

HyDE bypasses AdaptiveRetriever's BM25 weight tuning (replaced by three-way RRF) but composes with CODE filter and COMPARISON diversification. The query embedding from the response cache lookup is reused for cache put to avoid redundant embedding calls.

### 4. BM25 Index Lifecycle

- **Build**: Lazily on first search per user (from MongoDB chunks)
- **Cache**: In-memory dictionary keyed by user_id
- **Invalidate**: On document upload or deletion
- **Rebuild**: Automatically on next search after invalidation

### 5. Evaluation Infrastructure

| Level | Tool | Metrics | When |
|-------|------|---------|------|
| L1 | `RetrievalEvaluator` | P@k, R@k, MRR | After retrieval changes |
| L2 | `RAGASEvaluator` | Faithfulness, relevancy | Pre-release |
| Tracking | `MetricsTracker` | Trends over time | Continuous |

### 6. Data Flow

```
MongoDB "documents"          →  Document metadata, status
MongoDB "chunks"             →  Chunk text, page numbers, content flags
Pinecone index               →  Embeddings with chunk metadata
MongoDB "rag_metrics"        →  Performance metrics over time
MongoDB "retrieval_feedback" →  User thumbs up/down on RAG answers
MongoDB "rag_responses"      →  Query/answer/sources per message (feedback linkage)
MongoDB "propositions"       →  Atomic facts with source chunk back-references
MongoDB "knowledge_graph"    →  Entity-relationship triples for multi-hop reasoning
In-memory cache              →  Semantic response cache (query embedding → answer)
```

## Agent Workflow Graph (LangGraph)

The LangGraph workflow wraps the RAG pipeline with a cyclic, self-correcting
graph.  Instead of a simple `router → agent → END` path, the enhanced workflow
adds a response quality gate with refinement loops and failure-driven
re-routing.

```
check_documents → router → confidence_gate
    ├── confidence < 0.4  → clarify_query → END
    └── confidence >= 0.4 → agent_executor → response_grader
                                 ↑                 │
                                 │   ┌─────────────┤
                                 │   │  PASS → END
                                 │   │  REFINE (max 2) → agent_executor (with feedback)
                                 │   │  WRONG_AGENT (max 1) → re_router → agent_executor
```

### Nodes

| Node | File | Role |
|------|------|------|
| `check_documents` | `graph/nodes.py` | Sets `has_documents`, `document_count` |
| `router` | `graph/nodes.py` | LLM-based intent classification with confidence score |
| `clarify_query` | `graph/nodes.py` | Generates clarification question for ambiguous queries |
| `agent_executor` | `graph/nodes.py` | Dispatcher — reads `state["route"]` and calls the right agent |
| `response_grader` | `graph/nodes.py` | LLM (gpt-4o-mini) evaluates response quality |
| `re_router` | `graph/nodes.py` | Picks a different agent after wrong-agent verdict |

### How agent_executor calls into RAG

`agent_executor` dispatches to one of four agents. Each agent internally calls
`RAGPipeline.query_with_context()`, which runs the full 13-step retrieval
pipeline (cache → rewrite → decompose → multi-query → hybrid search → rerank →
self-RAG → context expansion → KG → generate → cache).

The grader evaluates the final response *after* the full RAG pipeline has run.
If the grader triggers a refinement, the agent is re-invoked with the grader's
feedback appended to the question, causing a fresh RAG retrieval cycle.

### Loop Limits

- **Refinement loop**: max 2 iterations (tracked by `refinement_count`)
- **Re-routing**: max 1 re-route (tracked by `reroute_count`)
- **Worst-case path**: router → agent → grader → REFINE → agent → grader → REFINE → agent → grader → PASS (5 LLM calls for grading)

---

## Key Files

```
backend/core/
├── rag/
│   ├── pipeline.py              # RAGPipeline: cache → decompose → multi-query → adaptive → self-rag → generate
│   ├── adaptive_retrieval.py    # AdaptiveRetriever: query-type routing (wired into pipeline)
│   ├── query_rewriter.py        # QueryRewriter (LLM) + HyDE + multi-query generation
│   ├── response_cache.py        # SemanticResponseCache: cosine similarity lookup, TTL, eviction
│   ├── self_rag.py              # RetrievalVerifier + SelfRAGController: verify → reformulate → retry
│   ├── query_decomposer.py      # QueryDecomposer: split complex questions into sub-queries
│   ├── feedback.py              # RetrievalFeedback: thumbs up/down, weak doc detection, stats
│   ├── request_budget.py        # RequestBudget: per-query caps on LLM calls, retries, latency
│   ├── retrieval_profiles.py    # Named presets (fast/balanced/deep) + auto-selection heuristic
│   ├── fallback.py              # Deterministic fallback chain + FallbackStrategies defaults
│   ├── stage_metrics.py         # Per-stage value metrics (RequestMetrics + AggregateMetrics)
│   ├── proposition_indexer.py   # PropositionExtractor + PropositionRepository: atomic fact indexing
│   ├── knowledge_graph.py       # KGExtractor + KnowledgeGraphTraverser: entity-rel extraction + multi-hop
│   └── analytics.py             # RAGAnalytics: Pandas + MongoDB aggregation for quality insights
├── vectors/
│   ├── hybrid_search.py         # HybridSearchService: BM25+vector fusion
│   ├── search.py                # SemanticSearchService + cross-encoder reranking + contextual embeddings
│   ├── embeddings.py            # Gemini/sentence-transformer/OpenAI embeddings (auto-detect)
│   └── pinecone_client.py       # Vector DB client
├── documents/
│   ├── manager.py               # Upload + auto-detect type + adaptive/parent-child chunking
│   ├── chunker.py               # adaptive_chunk(), chunk_with_parents(), recursive/semantic
│   ├── doc_type_detector.py     # Classify textbook/paper/notes/code/general
│   └── storage.py               # Repos + get_adjacent_chunks() for sliding window
├── graph/
│   ├── state.py                 # WorkflowState with DecisionContext and budget
│   ├── decision_context.py      # Unified DecisionContext: routing + grading + loop signals
│   ├── nodes.py                 # All nodes: router, agent_executor, response_grader, clarify, re_router
│   └── workflow.py              # Cyclic LangGraph: confidence gate, refinement loop, re-routing
├── config/
│   └── llm_config.py            # LLM routing (Gemini user-facing, OpenAI infrastructure)
└── evaluation/
    ├── retrieval_evaluator.py   # Level 1: P@k, R@k, MRR
    ├── ragas_evaluator.py       # Level 2: RAGAS metrics
    ├── metrics_tracker.py       # Performance logging + trending
    └── test_data.py             # 20+ ML test questions with ground truth

backend/core/agents/
└── research_agent.py            # RAG-powered Q&A with arXiv fallback when no docs or RAG fails

backend/mcp_servers/
└── arxiv_server.py              # Standalone MCP tool server: search_papers, get_paper_details, search_by_author

backend/api/v1/endpoints/
├── chat.py                      # Chat + POST /feedback endpoint (links to rag_responses)
└── analytics.py                 # GET /report — RAG analytics via RAGAnalytics
```
