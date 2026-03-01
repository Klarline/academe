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
              │  │ (30%) │  │ (70%) │  │  (0.3 * BM25 + 0.7 * Vector)
              │  └──────┘  └────────┘  │
              │  (contextual embeddings)│
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │Cross-Encoder│  ms-marco-MiniLM-L-6-v2
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
- **EmbeddingService** (`core/vectors/embeddings.py`): Gemini embedding-001 (768 dims, free tier; falls back to sentence-transformers or mock)
- **Contextual Embedding Enrichment** (`core/vectors/search.py`): Prepends `Document: {title} | Section: {section}` to chunk text before embedding, so vectors capture document-level context
- **PineconeManager** (`core/vectors/pinecone_client.py`): Vector index with user namespaces

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
7. **Score fusion** — Normalize + weighted combination (0.3 BM25 / 0.7 vector)
8. **Cross-encoder reranking** — Score query-document pairs for final ranking
9. **Self-RAG verification** — LLM judges if context is sufficient; reformulates + retries if not
10. **Context expansion** — Sliding window (±1 adjacent chunks) or parent-child (expand child→parent)
11. **Knowledge graph augmentation** — Multi-hop traversal from query entities through extracted triples adds related facts
12. **LLM generation** — Answer grounded in expanded context + KG relationships
13. **Cache result** — Store answer for future similar queries

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
MongoDB "propositions"       →  Atomic facts with source chunk back-references
MongoDB "knowledge_graph"    →  Entity-relationship triples for multi-hop reasoning
In-memory cache              →  Semantic response cache (query embedding → answer)
```

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
│   ├── proposition_indexer.py   # PropositionExtractor + PropositionRepository: atomic fact indexing
│   └── knowledge_graph.py       # KGExtractor + KnowledgeGraphTraverser: entity-rel extraction + multi-hop
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
├── config/
│   └── llm_config.py            # LLM routing (Gemini user-facing, OpenAI infrastructure)
└── evaluation/
    ├── retrieval_evaluator.py   # Level 1: P@k, R@k, MRR
    ├── ragas_evaluator.py       # Level 2: RAGAS metrics
    ├── metrics_tracker.py       # Performance logging + trending
    └── test_data.py             # 20+ ML test questions with ground truth
```
