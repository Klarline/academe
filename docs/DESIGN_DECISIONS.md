# RAG Design Decisions

Each decision documents: what, why, tradeoffs, and alternatives considered.

---

## 1. Hybrid Search (BM25 + Vector)

**Decision**: Combine BM25 (30%) and vector search (70%) with weighted score fusion.

**Reasoning**:
- Vector search alone misses exact keyword matches for technical terms like "PCA", "eigenvalue", "LSTM"
- BM25 excels at lexical matching; vectors excel at semantic similarity
- Weight ratio (0.3/0.7) balances exact match and semantic — tunable on validation set

**Trade-offs**:
- (+) Better precision for technical/keyword-heavy queries
- (+) Handles both typos (vector) and exact terms (BM25)
- (-) Requires BM25 index build and cache management
- (-) Adds ~50ms latency for BM25 scoring

**Alternatives Considered**:
- **Elasticsearch**: More features but significant operational overhead for a small project
- **Pure vector search**: Simpler but missed relevant docs for exact technical terms
- **Reciprocal Rank Fusion (RRF)**: Viable alternative to weighted fusion; chose weighted for interpretability and tunability

---

## 2. Cross-Encoder Reranking

**Decision**: Use lightweight cross-encoder (ms-marco-MiniLM-L-6-v2) to rerank top-20 candidates down to top-5.

**Reasoning**:
- Bi-encoder (used for initial retrieval) encodes query and document independently — fast but less accurate
- Cross-encoder encodes query-document pairs jointly — more accurate but too slow for all candidates
- Two-stage approach: fast bi-encoder for recall, cross-encoder for precision

**Trade-offs**:
- (+) Significant precision improvement on nuanced queries
- (+) Small model (66M params) keeps latency under 100ms for 20 candidates
- (-) Can't apply to full corpus (only reranking stage)
- (-) Adds dependency on sentence-transformers

**Implementation**:
1. Hybrid search retrieves top-20 (high recall)
2. Cross-encoder scores all 20 query-document pairs
3. Return re-ranked top-5 (high precision)
4. Graceful fallback to keyword-overlap reranking if model unavailable

---

## 3. Adaptive Chunking (1000 chars, 200 overlap)

**Decision**: Use 1000-char chunks with 200-char overlap for general text; semantic chunking for textbooks.

**Reasoning**:
- 1000 chars balances context completeness and retrieval precision
- 200-char overlap prevents breaking concept boundaries
- Semantic chunking (paragraph-aware) better preserves logical units in textbooks
- Tested 4 strategies: small (512), current (1000), large (1500), semantic

**Trade-offs**:
- Larger chunks: more context but lower precision (more noise)
- Smaller chunks: better precision but risk losing context
- Semantic: best retrieval quality, 2x processing time
- 200-char overlap is empirically chosen (tested 100/200/300)

**Decision Framework**:
| Document Type | Chunk Size | Overlap | Strategy | Why |
|---------------|-----------|---------|----------|-----|
| Textbook | 1200 | 300 | semantic | Preserves chapter/section structure |
| Paper | 800 | 200 | recursive | Dense, self-contained paragraphs |
| Notes | 600 | 100 | recursive | Short bullet-point items need smaller windows |
| Code | 1000 | 150 | recursive | Function/class boundary awareness |
| General | 1000 | 200 | recursive | Default balance for unclassified content |

---

## 4. BM25 Index Lifecycle

**Decision**: Lazy build on first search, in-memory cache, invalidate on document change.

**Reasoning**:
- Eager build on startup wastes resources for users who never search
- In-memory cache is fast for repeated searches in a session
- Invalidation on upload ensures fresh results without background jobs

**Trade-offs**:
- (+) No startup cost
- (+) Simple, no background workers needed
- (-) First search per user is slower (builds index)
- (-) Cache lost on server restart (acceptable for current scale)

**Future**: Add disk persistence if user base grows or for cold-start optimization.

---

## 5. Adaptive Retrieval

**Decision**: Classify queries into types (definition, comparison, code, procedural, general) and adjust retrieval parameters accordingly.

**Reasoning**:
- "What is PCA?" (definition) needs high-precision, exact-match-heavy results
- "PCA vs t-SNE" (comparison) needs diverse sources covering both topics
- "Write PCA from scratch" (code) should prefer code-containing chunks
- One-size-fits-all retrieval leaves performance on the table

**Implementation**:
| Query Type | BM25 Weight | top_k | Special Handling |
|------------|-------------|-------|------------------|
| Definition | 0.4 (boosted) | 3 | Fewer, higher quality |
| Comparison | 0.3 (default) | 2x | Diversity selection (MMR-style) |
| Code | 0.3 (default) | 5 | Filter `has_code=True`, fallback |
| Procedural | 0.3 (default) | 5 | Standard |
| General | 0.3 (default) | 5 | Standard |

**Trade-offs**:
- (+) Measurable improvement for definition and comparison queries
- (+) Regex-based classifier is fast and deterministic
- (-) Rule-based classification may misclassify edge cases
- (-) Adds complexity to the retrieval path

---

## 6. Two-Level Evaluation

**Decision**: Separate retrieval evaluation (Level 1) from end-to-end evaluation (Level 2).

**Reasoning**:
- Retrieval changes need fast feedback (P@5, MRR) without LLM calls
- End-to-end evaluation (RAGAS) is slower and tests the full generation pipeline
- Different cadences: L1 on every change, L2 pre-release

**Trade-offs**:
- (+) Fast iteration on retrieval improvements
- (+) Clear separation of retrieval vs generation issues
- (-) L1 evaluation uses content-overlap heuristic (not perfect relevance)
- (-) Full recall measurement requires explicit ground-truth chunk IDs

---

## 7. Embedding Model Choice (Gemini embedding-001)

**Decision**: Use Gemini embedding-001 (768 dimensions via Matryoshka truncation) for document and query embeddings. Falls back to sentence-transformers (all-MiniLM-L6-v2, 384 dims) when offline.

**Reasoning**:
- Highest quality on MTEB benchmarks (~68 overall score) among free-tier API models
- Google free tier covers development and moderate-scale usage at zero cost
- Matryoshka dimensionality allows flexible output (256, 768, 1536, 3072) — 768 balances quality and Pinecone storage
- Auto-detection: uses Gemini if `GOOGLE_API_KEY` is set, falls back to local sentence-transformers
- Consistent with LLM routing: Gemini API key is already required for the user-facing assistant

**Trade-offs**:
- (+) Significant quality improvement over all-MiniLM-L6-v2 (MTEB ~68 vs ~49)
- (+) Free tier — no additional cost for embedding generation
- (+) Flexible dimensions via Matryoshka truncation
- (-) Requires network access (mitigated by sentence-transformers fallback)
- (-) Rate-limited on free tier (5-15 RPM) — add delays for large batch uploads

**Alternatives Considered**:
- **all-MiniLM-L6-v2 (previous)**: Free, local, fast (~2ms), but significantly lower quality (384 dims)
- **OpenAI text-embedding-3-small**: Good quality but $0.02/1M tokens, not free
- **BGE-M3**: Strong open-source, free, but requires local GPU for good performance
- **Fine-tuned model**: Best for domain but requires training data and infrastructure

---

## 8. Adaptive Chunking with Document Type Detection

**Decision**: Auto-detect document type (textbook/paper/notes/code) and apply per-type chunk size, overlap, and splitting strategy.

**Reasoning**:
- Textbooks have long chapters with definitions/theorems — larger chunks (1200) preserve section coherence
- Papers are dense — smaller chunks (800) improve retrieval precision for specific claims
- Notes are informal and short — small chunks (600) match the bullet-point structure
- A single chunk size forces a compromise; adaptive chunking eliminates it

**Trade-offs**:
- (+) Each document type gets appropriately sized chunks
- (+) Detection is heuristic-only (no LLM call), <1ms overhead
- (-) Heuristics may misclassify edge cases (e.g., a very short textbook excerpt)
- (-) Different chunk sizes mean BM25 index must be rebuilt when mixing types

**Alternatives Considered**:
- **Fixed chunk size**: Simpler but suboptimal for varied content
- **LLM-based classification**: More accurate but adds latency and cost per upload
- **User-specified type**: Accurate but adds friction to the upload flow

---

## 9. Contextual Embedding Enrichment

**Decision**: Prepend `Document: {title} | Section: {section}` to each chunk before embedding, while storing raw content in Pinecone metadata.

**Reasoning**:
- Embeddings of isolated chunks lose document-level context (e.g., "Chapter 3" about ML vs biology)
- Prefixing title and section gives the embedding model disambiguation signals
- The raw content is still stored and displayed — enrichment only affects the vector

**Trade-offs**:
- (+) Significant retrieval improvement for ambiguous terms
- (+) Zero additional storage cost (enriched text is not persisted)
- (-) Slight mismatch between query embedding (no prefix) and document embedding (with prefix)
- (-) Re-indexing required to benefit existing documents

---

## 10. Sliding Window + Parent-Child Context Expansion

**Decision**: At context-building time, expand each retrieved chunk with ±1 adjacent neighbors (sliding window) or with the full parent chunk (parent-child mode).

**Reasoning**:
- Retrieved chunks often cut off mid-thought — the LLM needs surrounding context
- Sliding window is simple and effective: fetch neighbors from MongoDB by chunk_index
- Parent-child is more precise: small children for retrieval, large parents for generation
- Both approaches dedup overlapping windows to avoid redundant context

**Trade-offs**:
- (+) LLM sees 3x more context per retrieval hit without sacrificing retrieval precision
- (+) Parent-child gives the best of both worlds: precise retrieval + coherent context
- (-) Sliding window adds 1 MongoDB query per retrieved chunk
- (-) Parent-child stores parent_content in chunk metadata, increasing document size

**Alternatives Considered**:
- **No expansion**: Simpler but LLM frequently gets incomplete context
- **Fixed large chunks**: Larger chunks capture more context but hurt retrieval precision
- **Re-chunking at query time**: Flexible but expensive and complex

---

## 11. Self-RAG (Retrieval Verification + Retry)

**Decision**: After retrieval, use a fast LLM to judge whether retrieved context is sufficient. If not, reformulate the query and retry (max 2 retries).

**Reasoning**:
- Retrieval sometimes returns irrelevant chunks (wrong topic, wrong granularity)
- Without verification, the generation LLM hallucinates from bad context
- A cheap LLM call (gpt-4o-mini) to verify is far cheaper than a wrong answer
- Reformulation targets the specific gap identified by the verifier

**Trade-offs**:
- (+) Catches retrieval failures before they become hallucinations
- (+) Reformulated queries often find the right chunks on retry
- (-) Adds 1-2 LLM calls per query (~200ms latency)
- (-) Verifier itself can make mistakes (mitigated by defaulting to "sufficient")

---

## 12. Semantic Response Cache

**Decision**: Cache (user_id, query_embedding, answer, sources) in-memory, **scoped per user**. On new queries, compute cosine similarity against that user's cached entries; if > 0.95, return cached answer.

**Reasoning**:
- Students frequently ask similar questions about the same material
- LLM generation is the most expensive step (~500ms + API cost)
- Semantic matching (not exact match) handles paraphrases: "What is PCA?" ≈ "Explain PCA"
- Per-user scoping prevents cross-user data leakage (answers cite user-specific documents)
- `cache.invalidate(user_id)` clears only the affected user when documents are uploaded/deleted

**Trade-offs**:
- (+) Dramatic latency reduction for repeat/similar queries (~50ms vs ~1s)
- (+) Reduces LLM API costs proportional to cache hit rate
- (-) In-memory cache is lost on restart (acceptable for this scale)
- (-) 0.95 threshold may occasionally return stale answers for genuinely different queries

**Alternatives Considered**:
- **Redis cache**: Persistent but adds infrastructure complexity
- **Exact-match cache**: Misses paraphrases, much lower hit rate
- **No cache**: Simpler but wasteful for the common case

---

## 13. Query Decomposition for Multi-Part Questions

**Decision**: Use an LLM to detect complex/compound questions and split them into atomic sub-queries. Retrieve for each sub-query independently, then merge and deduplicate.

**Reasoning**:
- Questions like "Compare PCA and t-SNE, and when to use each?" need chunks about both topics
- Single retrieval often biases toward one topic
- Sub-query retrieval ensures coverage of all parts

**Trade-offs**:
- (+) Much better coverage for comparison and multi-hop questions
- (+) LLM returns "SIMPLE" for easy questions — zero overhead in the common case
- (-) 1 extra LLM call to classify complexity
- (-) Multiple retrievals increase latency for complex queries

---

## 14. Retrieval Feedback Loop

**Decision**: Record user thumbs-up/down on RAG answers in MongoDB. Use feedback to identify weak queries, weak documents, and track satisfaction trends.

**Reasoning**:
- Without feedback, retrieval quality degrades silently
- Negative feedback identifies documents that need re-chunking or better metadata
- Satisfaction rate is a key metric for RAG system health
- Data enables future fine-tuning of retrieval weights and embedding models

**Trade-offs**:
- (+) Closed-loop quality improvement
- (+) Identifies specific documents causing problems
- (-) Requires user engagement (thumbs up/down UI)
- (-) Feedback analysis is currently manual (future: automated retraining)

---

## 15. Proposition-Based Indexing

**Decision**: Decompose each document chunk into atomic factual statements (propositions) using an LLM, store them in MongoDB with source chunk back-references. Each proposition is independently embeddable for fine-grained retrieval.

**Reasoning**:
- Standard chunks (800-1200 chars) contain many facts — matching against a proposition is more precise
- Each proposition is self-contained and de-contextualized (pronouns resolved, context added)
- Back-reference to source chunk enables context expansion at generation time
- Based on "Dense X Retrieval" (Chen et al., 2023): proposition-level retrieval improves precision@5 by 10-20%

**Trade-offs**:
- (+) Significantly more precise retrieval for factual questions
- (+) Each proposition is independently verifiable
- (+) Sentence-level fallback when LLM is unavailable
- (-) 5-10x more vectors in the index (mitigated by storing only in MongoDB for now)
- (-) LLM cost for proposition extraction at upload time (~$0.01/document with gpt-4o-mini)

**Alternatives considered**:
- *Sentence-level splitting only*: Cheaper but loses de-contextualization (pronouns unresolved)
- *Embedding propositions directly in Pinecone*: Better for retrieval but increases vector count significantly

---

## 16. Knowledge Graph Extraction with Multi-Hop Traversal

**Decision**: Extract entity-relationship triples from chunks using an LLM, store in MongoDB, and build an in-memory graph for multi-hop reasoning. Graph context is appended to the LLM prompt alongside retrieved chunks.

**Reasoning**:
- RAG with flat retrieval cannot answer multi-hop questions ("What method does the technique that uses chain rule employ?")
- Knowledge graph captures structured relationships that span chunks and documents
- BFS traversal from query entities finds related facts not in the retrieved chunks
- Combining structured (graph) and unstructured (vector) retrieval is a strong differentiator

**Trade-offs**:
- (+) Enables multi-hop reasoning across documents
- (+) Graph traversal reveals implicit connections between concepts
- (+) Regex-based fallback when LLM is unavailable
- (+) In-memory graph keeps latency low for moderate-scale datasets
- (-) LLM cost for triple extraction at upload time
- (-) Graph quality depends on LLM extraction accuracy
- (-) In-memory traversal won't scale past ~100K triples (future: Neo4j migration)

**Alternatives considered**:
- *Neo4j graph database*: Better for large-scale graphs, but adds infrastructure complexity
- *Entity linking to external KBs (Wikidata)*: Richer semantics but requires entity disambiguation
- *LLM-only multi-hop*: Let the LLM reason in multiple turns — more expensive and less reliable

---

## 17. Enhanced Workflow with Response Grading and Refinement Loops

**Decision**: Replace the simple linear `router → agent → END` LangGraph workflow with a cyclic, self-correcting graph that adds three new patterns: (1) a response quality gate with refinement loop, (2) low-confidence clarification, and (3) failure-driven re-routing.

**Reasoning**:
- The original workflow had no quality control — hallucinated or incomplete responses went directly to the user
- Router misclassification had no recovery path; the wrong agent's output was final
- The router already computed a confidence score but never acted on it
- Self-RAG exists inside the RAG pipeline for *retrieval* verification, but there was no *response*-level verification
- Academic users need high-quality, grounded answers — a quality gate catches most failures before they become visible

**Implementation**:

The enhanced graph topology:
```
check_documents → router → confidence_gate
    ├── confidence < 0.4  → clarify_query → END
    └── confidence >= 0.4 → agent_executor → response_grader
                                 ↑                 │
                                 │   PASS → END
                                 │   REFINE (max 2) ──→ agent_executor
                                 │   WRONG_AGENT (max 1) → re_router → agent_executor
```

Three new nodes:
- **response_grader**: Uses gpt-4o-mini to evaluate (question, response, agent_used). Emits PASS, REFINE with feedback, or WRONG_AGENT with suggested route.
- **clarify_query**: Generates a disambiguation question when routing confidence is too low.
- **re_router**: Switches to a different agent, resetting transient state for a clean retry.

Plus one structural change:
- **agent_executor**: Dispatcher node that consolidates all 4 agents behind one graph node, enabling clean back-edges for the refinement loop.

**Trade-offs**:
- (+) Catches hallucinated and incomplete responses before they reach the user
- (+) Recovers from router misclassification via re-routing
- (+) Avoids guessing on ambiguous queries by asking for clarification
- (+) Refinement feedback is specific, not blind retry — grader explains what's wrong
- (+) All loops have hard limits (max 2 refine, max 1 reroute) preventing runaway cost
- (-) Adds 1 LLM call (gpt-4o-mini) per query for grading (~200ms, ~$0.001)
- (-) Worst case adds ~3x latency (2 refinements + 1 reroute + 3 grading calls)
- (-) Grader itself can make mistakes (mitigated by defaulting to PASS on uncertainty)

**Alternatives considered**:
- *No quality gate*: Simpler but no protection against hallucinations or misrouting
- *Rule-based grading* (length/keyword checks): Cheaper but misses semantic quality issues
- *User feedback only*: Reactive, not proactive — bad responses still reach the user
- *Multiple agents in parallel + pick best*: Better quality but 4x the LLM cost per query
- *Grading with primary LLM (Gemini)*: Higher quality judgment but more expensive and slower than gpt-4o-mini

---

## 18. Request Budget Layer

**Decision**: Introduce a `RequestBudget` dataclass that travels with every user query through `WorkflowState`, capping total auxiliary LLM calls, retries, and wall-clock latency.

**Reasoning**:
- The cyclic workflow (Decision #17) can trigger multiple LLM calls: router, grader, up to 2 refinement re-generations, and a possible re-route — on top of the RAG pipeline's own LLM calls (query rewriting, self-RAG verification, decomposition)
- Without a budget, a pathological query could trigger 10+ LLM calls and 30+ seconds of latency
- Codex review specifically flagged the need for "a request budget layer: cap per-query max_latency_ms, max_aux_llm_calls, and max_retries"
- Individual per-stage limits (MAX_REFINEMENTS, MAX_REROUTES, self-RAG max_retries) exist but don't coordinate — the budget provides a unified ceiling

**Implementation**:
- `core/rag/request_budget.py`: Mutable dataclass with `can_call_llm()`, `use_llm_call()`, `can_retry()`, `elapsed_ms` tracking
- Default limits: 8 LLM calls, 3 retries, 30 000 ms
- Stored in `WorkflowState["budget"]` and checked by `response_grader_node` and `clarify_query_node` before each LLM invocation — if exhausted, they gracefully skip (grader auto-passes, clarifier uses a static fallback)

**Trade-offs**:
- (+) Hard ceiling prevents cost/latency explosions regardless of loop topology
- (+) Observable via `budget.to_dict()` — easy to log and monitor
- (+) Default limits are generous enough for normal queries; only pathological cases hit the cap
- (-) Adds a coordination object that all LLM-calling stages must check
- (-) Static defaults may need per-deployment tuning (addressed by making fields configurable)

**Alternatives considered**:
- *Per-stage limits only*: Already exist (MAX_REFINEMENTS, etc.) but don't account for cross-stage accumulation
- *Global timeout with no call counting*: Misses the cost dimension — a fast query can still be expensive
- *Token-budget instead of call-budget*: More precise but harder to enforce without streaming token counters

---

## 19. Retrieval Profiles (fast / balanced / deep)

**Decision**: Define three named retrieval profiles that bundle RAGPipeline toggle settings into coherent presets, selectable by name or by automatic heuristic.

**Reasoning**:
- RAGPipeline has 10 boolean constructor flags; manually choosing the right combination is error-prone
- Different queries have fundamentally different cost/quality tradeoffs: "What is PCA?" doesn't need knowledge-graph traversal, but "Compare PCA, t-SNE, and UMAP step by step" does
- Codex review recommended "retrieval profiles: fast, balanced, deep with fixed parameter sets; choose profile by query complexity"

**Implementation**:
- `core/rag/retrieval_profiles.py`: `RetrievalProfile` frozen dataclass with a `to_pipeline_kwargs()` method, three pre-built instances (`FAST`, `BALANCED`, `DEEP`), and `select_profile_for_query()` heuristic
- `FAST`: hybrid search + adaptive retrieval + cache only (no LLM enrichment)
- `BALANCED`: adds query rewriting, multi-query, self-RAG (default for most queries)
- `DEEP`: everything enabled including HyDE, decomposition, propositions, knowledge graph

**Trade-offs**:
- (+) Callers pick one name instead of toggling 10 flags
- (+) Automatic selector keeps simple queries fast and complex queries thorough
- (+) Profiles are frozen dataclasses — immutable, testable, documented
- (-) Heuristic profile selection is keyword-based, not LLM-based (intentional: no LLM call overhead for profile selection)
- (-) Three profiles may not cover every edge case (mitigated: callers can still pass explicit RAGPipeline kwargs)

**Alternatives considered**:
- *LLM-based profile selection*: More accurate but adds latency and an LLM call — contradicts the purpose of "fast"
- *Continuous parameter tuning per query*: Optimal but unpredictable; discrete profiles are easier to reason about
- *Single default with overrides*: What we had before — works but hard to document and test as a coherent strategy

---

## 20. Deterministic Fallback Chain

**Decision**: Introduce a `fallback()` utility and `FallbackStrategies` class that provide ordered, predictable degradation when external services fail.

**Reasoning**:
- Every LLM-calling stage, the cross-encoder reranker, Pinecone, and Redis can fail independently (network timeout, rate limit, service outage)
- Without a strategy, each `try/except` block handles failure differently — some re-raise, some return `None`, some swallow silently
- The system should degrade predictably: if OpenAI is down, the grader auto-passes; if the reranker times out, unranked results are returned; if Pinecone is unreachable, an empty result set triggers the no-context answer path
- Each attempt and its outcome are logged, feeding directly into stage metrics

**Implementation**:
- `core/rag/fallback.py`: Generic `fallback(primary, fallbacks=[], default=..., label=...)` function that tries callables in order
- `@with_fallback(default=..., label=...)` decorator for simpler single-fallback cases
- `FallbackStrategies` class provides canonical default values per dependency (grader → auto-pass, rewriter → original query, reranker → unranked results, etc.)
- All attempts are timed and logged with the stage label

**Trade-offs**:
- (+) Every failure mode has an explicit, documented default — no more "what happens when X is down?"
- (+) Ordered fallback lists make degradation testable and deterministic
- (+) Logging every attempt enables alerting on elevated fallback rates
- (-) Adds a wrapping layer around external calls (small overhead, typically <1ms)

**Alternatives considered**:
- *Circuit-breaker pattern*: More sophisticated but adds state management; fallback chain is simpler and sufficient for our scale
- *Retry-with-backoff only*: Doesn't provide a graceful result when all retries fail
- *Let exceptions propagate*: Simplest but gives users error messages instead of degraded-but-useful responses

---

## 21. Per-Stage Value Metrics

**Decision**: Add a `RequestMetrics` collector that tracks, for each RAG pipeline stage, whether the stage actually changed the input or output.

**Reasoning**:
- The pipeline has 8+ optional stages, each adding latency and (sometimes) LLM cost
- Without metrics, we can't answer "did reranking help?" or "how often does self-RAG retry?"
- The Codex review specifically recommended per-stage value metrics to prune low-ROI stages
- Having these numbers also strengthens the portfolio story ("reranking reordered top-5 in 73% of queries")

**Implementation**:
- `core/rag/stage_metrics.py`: `RequestMetrics` (per-request collector) and `AggregateMetrics` (cross-request counters)
- Recording helpers: `record_query_rewrite()`, `record_reranking()`, `record_self_rag()`, `record_knowledge_graph()`, etc.
- Each event tracks: stage name, enabled, ran, changed_input, changed_output, elapsed_ms
- `to_dict()` produces a summary including `stages_that_changed_input` and `stages_that_changed_output` lists
- `AggregateMetrics.absorb()` folds request metrics into running counters (ready for Prometheus export)
- **Wired into `RAGPipeline.query_with_context()`**: A `RequestMetrics` instance is created per request, records cache hit/miss, query rewriting, decomposition, multi-query, self-RAG, and knowledge graph stages with timing, then logs a summary and absorbs into the global `AggregateMetrics` singleton

**Trade-offs**:
- (+) Zero external dependencies — pure Python counters and dataclasses
- (+) Pluggable: connect `AggregateMetrics.to_dict()` to Prometheus, structured logging, or a dashboard
- (+) Per-request `to_dict()` can be returned in API responses for debugging
- (-) In-process counters reset on restart (sufficient for monitoring; Prometheus scraping provides persistence)

**Alternatives considered**:
- *OpenTelemetry spans*: More standard but heavier setup; can be added later wrapping the same events
- *Prometheus histograms directly*: Tighter integration but creates a hard dependency on Prometheus client library
- *No metrics, rely on logs*: We already log per-stage, but structured counters enable aggregation and alerting

---

## 22. Redis-Backed Semantic Response Cache

**Decision**: Add `RedisResponseCache` as an optional persistent backend for the existing `SemanticResponseCache`, with automatic fallback to in-memory when Redis is unavailable.

**Reasoning**:
- The in-memory cache dies on restart and doesn't work across multiple backend instances
- In production (Docker Compose, multi-worker), each worker builds its own cold cache — wasting LLM calls
- Redis is already in the stack for Celery; reusing it for caching is zero new infrastructure
- The Codex review recommended "persist semantic cache in Redis (optional mode)"

**Implementation**:
- `RedisResponseCache` in `core/rag/response_cache.py`: same `get/put/invalidate/size` API as `SemanticResponseCache`
- Uses per-user Redis Hashes (`academe:cache:{user_id}:entries`, `academe:cache:{user_id}:embeddings`) for entry and embedding storage
- Similarity search loads all embeddings for the requesting user on lookup (fine up to ~1000 entries per user; beyond that, use a vector-DB cache index)
- If Redis is unreachable at init, transparently falls back to `SemanticResponseCache`
- `REDIS_URL` setting added to `core/config/settings.py`

**Trade-offs**:
- (+) Cache survives restarts and is shared across workers/instances
- (+) Graceful fallback — if Redis goes down, the system continues with in-memory cache
- (+) Same API — callers don't know which backend they're using
- (-) Similarity search is O(n) over all cached embeddings per user per lookup (acceptable for <1000 entries per user)
- (-) Serializing `DocumentSearchResult` objects for Redis requires conversion to dicts (handled in `put()`)

**Alternatives considered**:
- *Redis with vector search (RediSearch)*: True ANN search but adds module dependency and complexity
- *Pinecone as cache*: Leverages existing vector DB but conflates cache with document index
- *Memcached*: Faster for simple key-value but no TTL-per-key and no data structures

---

## 23. Unified DecisionContext Object

**Decision**: Replace the scattered decision-related fields in `WorkflowState` (`routing_confidence`, `routing_reasoning`, `grader_verdict`, `grader_feedback`, `refinement_count`, `reroute_count`, `previous_agents`) with a single `DecisionContext` dataclass that accumulates all signals in one place.

**Reasoning**:
- Conditional edge functions (`confidence_gate`, `grading_decision`) and nodes (`response_grader_node`, `re_router_node`) were reading and writing 7+ separate state fields to make routing decisions
- Understanding "why did the graph take this path?" required inspecting multiple disconnected fields
- Adding new signals (e.g., retrieval sufficiency) would mean adding yet another loose field
- Codex review recommended "unify confidence signals: router confidence, retrieval sufficiency, and grader verdict should feed one decision object"

**Implementation**:
- `core/graph/decision_context.py`: `DecisionContext` dataclass with recording helpers (`record_routing`, `record_grading`, `record_reroute`, `record_agent_used`) and query properties (`should_clarify`, `can_refine`, `can_reroute`, `loops_exhausted`, `next_action`)
- Stored in `WorkflowState["decision"]`; all nodes read/write through it
- `_sync_decision_to_state()` copies context fields back to legacy state fields after each node, preserving full backward compatibility with existing tests and the streaming path
- Conditional edges (`confidence_gate`, `grading_decision`) check the `DecisionContext` first, with fallback to legacy fields for states created without one
- Constants (`MAX_REFINEMENTS`, `MAX_REROUTES`, `CONFIDENCE_THRESHOLD`) moved to `decision_context.py` as the single source of truth

**Trade-offs**:
- (+) One object to inspect for "why did the graph do this?" — simplifies debugging and logging
- (+) `next_action` property replaces ad-hoc verdict parsing in the grading edge
- (+) Easy to add new signals (e.g., retrieval sufficiency) without touching `WorkflowState`
- (+) Full backward compatibility — legacy fields still work, existing tests unchanged
- (-) Adds a coordination object that nodes must use (mitigated: `_decision()` helper auto-creates from legacy fields)
- (-) `_sync_decision_to_state()` duplicates data between context and state (necessary for LangGraph serialization)

**Alternatives considered**:
- *Just rename fields*: Doesn't reduce the number of fields or provide query helpers
- *Nested TypedDict*: TypedDict can't have methods; wouldn't support `should_clarify` or `next_action`
- *Remove legacy fields entirely*: Would break all existing tests and any external consumers of `WorkflowState`


---

## 24. arXiv Fallback in Research Agent

**Decision**: When the research agent has no uploaded documents or when the RAG pipeline fails, fall back to searching arXiv papers via direct Python import from `mcp_servers/arxiv_server.py`. Synthesize an answer from paper abstracts using the LLM, with citations.

**Reasoning**:
- Previously, users with no documents got a dead-end "upload documents first" message
- Students often want to explore topics before uploading materials
- The arXiv API is free, no auth required, and returns structured metadata (title, authors, abstract)
- Direct import is correct because the agent and arXiv tools share the same Python codebase — MCP protocol overhead is unnecessary

**Degradation chain**:
1. User has documents → RAG pipeline (primary)
2. No documents → arXiv search + LLM synthesis with citations
3. RAG fails (e.g., Pinecone down) → arXiv fallback
4. Both fail → friendly error message

**Trade-offs**:
- (+) Users get useful answers even without uploaded documents
- (+) arXiv abstracts are high-quality, peer-reviewed content
- (+) Graceful degradation — RAG failure no longer means total failure
- (-) arXiv API has rate limits (~3 req/s) and ~1-2s latency
- (-) Abstracts are summaries, not full text — answers may lack depth
- (-) Network dependency (mitigated by fallback to error message)

**Alternatives considered**:
- *MCP client in agent*: Would add subprocess + JSON-RPC overhead to call a function importable in the same process
- *Google Scholar*: No official API; scraping is unreliable and against TOS
- *Always require documents*: Simpler but bad UX for new users

---

## 25. End-to-End Feedback Loop with Pandas Analytics

**Decision**: Build a complete feedback pipeline: frontend thumbs up/down → `POST /api/v1/chat/feedback` → `rag_responses` + `retrieval_feedback` in MongoDB → `RAGAnalytics` module using MongoDB aggregation pipelines + Pandas for trend detection and opportunity identification.

**Reasoning**:
- `RetrievalFeedback` class existed but had no way for users to submit feedback (no API, no UI)
- Without feedback data, retrieval quality degrades silently
- MongoDB aggregation pipelines handle server-side grouping/counting efficiently
- Pandas handles the analysis layer: rolling averages, trend detection, ranking
- This combination makes both "MongoDB aggregation" and "Pandas for analysis" genuine capabilities

**Implementation**:
- `rag_responses` collection: stores `(message_id, user_id, query, answer, sources)` at response time — single lookup for feedback, no fragile "find previous message" logic
- `POST /api/v1/chat/feedback`: accepts `{message_id, rating, comment}`, looks up `rag_responses`, calls `RetrievalFeedback.record()`
- `FeedbackButtons.tsx`: thumbs up/down on assistant messages, wired via RTK Query
- `RAGAnalytics`: `satisfaction_trends()`, `weak_documents()`, `query_type_performance()`, `cache_performance()`, `generate_report()` with actionable recommendations
- `GET /api/v1/analytics/report`: exposes analytics scoped to authenticated user; includes `cache_performance` section with hit rate, hits, misses, and low-hit-rate recommendations
- Prometheus counters: `academe_cache_hits_total`, `academe_cache_misses_total`, `academe_cache_entries` (labeled by `backend=memory|redis`) auto-exposed at `/metrics` for Grafana dashboards

**Trade-offs**:
- (+) Closed-loop quality improvement — weak documents and failing query types identified automatically
- (+) MongoDB aggregation does heavy lifting server-side; Pandas receives pre-grouped data
- (+) `rag_responses` indexed on `message_id` for O(1) lookup
- (-) Requires user engagement (thumbs up/down) to populate data
- (-) `rag_responses` adds ~500 bytes per assistant message to MongoDB storage

**Alternatives considered**:
- *Pull all data into Pandas*: Works at 100 records, breaks at 100K — aggregation pipelines scale better
- *Look up previous message for query*: Fragile (race conditions, system messages, deletions)
- *Skip analytics, log only*: Misses the "opportunity identification" capability

---

## 26. Reranker Upgrade: ms-marco-MiniLM → BAAI/bge-reranker-base

**Decision**: Replace ms-marco-MiniLM-L-6-v2 (66M params) with BAAI/bge-reranker-base (~278M params) for cross-encoder reranking.

**Reasoning**:
- Original reranker missed implicit relevance (e.g., "dk=dv=dmodel/h=64" implying 8 attention heads)
- bge-reranker-base consistently outperforms ms-marco-MiniLM on MTEB reranking benchmarks
- Context precision analysis showed relevant chunks at rank 4-5 instead of 1-2

**Trade-offs**:
- (+) Better at understanding implicit and nuanced relevance
- (+) Improved context_precision in RAGAS evaluation
- (-) Latency increase: ~80ms → ~150-200ms for 20 candidates
- (-) Larger model footprint in memory

**Alternatives considered**:
- *bge-reranker-large*: Higher quality but significantly slower
- *Cohere Rerank API*: Strong quality but adds external dependency and cost
- *No reranker*: Simpler but measurably worse precision


---

## 27. Celery Task Monitoring (Prometheus + MongoDB)

**Decision**: Add signal-based Celery monitoring that writes to both Prometheus counters (Level 2) and a MongoDB `task_failures` collection (Level 3). Signal handlers are connected once at worker startup — no changes to individual task functions.

**Reasoning**:
- Celery tasks (document indexing, memory updates, progress tracking) can fail silently after exhausting retries
- Without monitoring, the only signal is the user seeing "indexing failed" in the UI — no aggregation, no alerting
- Prometheus counters (`academe_celery_task_success_total`, `_failure_total`, `_retry_total`) enable Grafana dashboards and alerts (e.g. "failure rate > 5%")
- MongoDB records provide structured failure data for offline analysis: which tasks fail, how often, what exceptions, how many retries

**Implementation**:
- `core/celery_monitoring.py`: Prometheus counters with `try/except ImportError` fallback, signal handlers for `task_success`, `task_failure`, `task_retry`, MongoDB failure logger, `get_celery_metrics()` reader
- `core/celery_config.py`: calls `connect_signals()` after task autodiscovery
- `core/rag/analytics.py`: `task_failure_summary()` aggregates from MongoDB; `celery_task_metrics()` reads Prometheus counters; both wired into `generate_report()` with auto-recommendations

**Trade-offs**:
- (+) Zero changes to existing task functions — pure signal-based
- (+) Prometheus counters auto-exposed at `/metrics` via existing Instrumentator
- (+) MongoDB failures survive restarts and are queryable via analytics endpoint
- (+) Graceful no-op if `prometheus_client` is not installed
- (-) MongoDB write on every failure adds ~5ms latency to the failure path (acceptable)
- (-) In-process Prometheus counters reset on worker restart (Prometheus scraping provides persistence)

**Alternatives considered**:
- *Flower only*: Quick dashboard but no Grafana integration or structured failure storage
- *Sentry*: Full error tracking but adds external SaaS dependency
- *Log parsing*: Cheap but fragile and hard to aggregate


---

## 28. Terminal Failure Handling for Celery Tasks

**Decision**: Catch `MaxRetriesExceededError` in every Celery task. For document-related tasks, set `processing_status = FAILED` with the error message so the UI shows the correct state.

**Reasoning**:
- Previously, `index_document_task` wrote `processing_error` but never set `processing_status = FAILED` — documents were stuck in `PROCESSING` state after all retries
- `process_document_task` had no status update at all on failure
- `update_memory_task` and `update_progress_task` silently raised after retries, with no structured return value
- `delete_document_task` left orphaned data (Pinecone vectors, chunks, KG triples) with no log trail

**Implementation**:
- All 5 tasks now catch `MaxRetriesExceededError` explicitly after `self.retry()`
- `index_document_task` and `process_document_task`: set `processing_status = FAILED` and write a descriptive `processing_error` including retry count
- `update_memory_task` and `update_progress_task`: return `{"status": "permanently_failed"}` for structured logging
- `delete_document_task`: logs orphaned resources for manual cleanup
- All re-raise after handling so Celery still marks the task as failed (signals fire correctly)

**Trade-offs**:
- (+) Documents no longer stuck in limbo — users see "failed" instead of endless "processing"
- (+) Every permanent failure is explicitly logged with context
- (+) Celery signal handlers still fire (monitoring picks up the failure)
- (-) Minor code duplication across tasks (could use a base class, but explicit handling is clearer)

---

## 29. Queue Depth Protection

**Decision**: Add `check_queue_before_dispatch()` that reads the Redis list length and raises `QueueFullError` if it exceeds `MAX_QUEUE_DEPTH` (default 500, configurable via `CELERY_MAX_QUEUE_DEPTH` env var).

**Reasoning**:
- Celery queues are Redis lists with no built-in size limit
- Under load (e.g. 100 users uploading simultaneously), tasks pile up with no backpressure
- Eventually this exhausts Redis memory, causing cascading failures for all services sharing Redis (cache, sessions, Celery)

**Implementation**:
- `celery_monitoring.py`: `get_queue_depth()` reads `LLEN` on the Redis queue list; `check_queue_before_dispatch()` raises if over limit
- Fail-open: if Redis is unreachable, the check returns 0 and allows the dispatch (better to attempt than to block)
- `document_service.py`: calls `check_queue_before_dispatch("documents")` before `delete_document_task.delay()`; catches `QueueFullError` gracefully (delete still succeeds from the user's perspective, cleanup is deferred)

**Trade-offs**:
- (+) Prevents Redis memory exhaustion from unbounded queue growth
- (+) Configurable limit per deployment (`CELERY_MAX_QUEUE_DEPTH`)
- (+) Fail-open design: Redis downtime doesn't block task dispatch
- (-) Per-queue check, not per-user — a single busy queue affects all users
- (-) `LLEN` is O(1) but adds one Redis round-trip per dispatch

**Alternatives considered**:
- *Redis memory limit*: Blunt instrument that kills all Redis data, not just queues
- *Celery rate limiting per task*: Controls throughput, not queue depth
- *Worker auto-scaling*: Solves the consumer side but doesn't protect Redis memory
