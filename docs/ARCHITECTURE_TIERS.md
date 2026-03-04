# Architecture Tiers

Academe's features are organized into three tiers of increasing sophistication.
Each tier is fully functional on its own; higher tiers layer additional quality
or research capabilities on top.

This document serves two purposes:

1. **For reviewers** — quickly see what's "table stakes" versus
  what goes beyond typical RAG demos.
2. **For contributors** — know which tier a feature belongs to so you can
  reason about dependencies and optional-ness.

---

## Tier 1 — Baseline Robust System

Core functionality that every production RAG application needs.  The system is
usable and reliable with **only** Tier 1 enabled (corresponds to the `fast`
retrieval profile).


| Component                      | Description                                                                                          | Key Files                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- | -------------------------------- |
| **Multi-agent routing**        | LLM-based router dispatches to Concept Explainer, Code Helper, Research Agent, or Practice Generator | `core/agents/router.py`          |
| **Hybrid search**              | Weighted fusion of BM25 (keyword) and Pinecone vector search with contextual embeddings              | `core/vectors/hybrid_search.py`  |
| **Cross-encoder reranking**    | `ms-marco-MiniLM-L-6-v2` reranks top candidates for precision                                        | `core/vectors/hybrid_search.py`  |
| **Adaptive retrieval**         | Query-type classification (definition / comparison / code / procedural) adjusts search parameters    | `core/rag/adaptive_retrieval.py` |
| **Adaptive chunking**          | PDF / code / markdown-aware chunk boundaries with sliding-window context expansion                   | `core/documents/chunker.py`      |
| **Semantic response cache**    | Embedding-based cache (in-memory or Redis-backed) avoids redundant LLM calls for similar queries     | `core/rag/response_cache.py`     |
| **Request budget**             | Per-query caps on LLM calls, retries, and wall-clock latency to prevent cost/latency explosions      | `core/rag/request_budget.py`     |
| **Retrieval profiles**         | Named presets (`fast` / `balanced` / `deep`) so callers don't have to toggle 10 flags manually       | `core/rag/retrieval_profiles.py` |
| **Deterministic fallback**     | Ordered degradation chain for every external dependency (LLM, reranker, Pinecone, Redis)             | `core/rag/fallback.py`           |
| **Per-stage value metrics**    | Tracks whether each pipeline stage changed the input/output, feeds aggregate counters                | `core/rag/stage_metrics.py`      |
| **Memory & progress tracking** | Spaced-repetition scheduler, concept mastery, weak-area identification                               | `core/memory/`                   |
| **Auth & multi-tenancy**       | JWT auth, per-user document isolation, profile management                                            | `core/auth/`, `core/database/`   |


---

## Tier 2 — Quality Enhancements

Features that measurably improve answer quality or user experience.  Enabled by
default in the `balanced` retrieval profile.


| Component                        | Description                                                                                                         | Key Files                                       |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Cyclic LangGraph workflow**    | Response grader → refinement loop → re-routing: the agent can self-correct instead of returning a poor first answer | `core/graph/workflow.py`, `core/graph/nodes.py` |
| **Low-confidence clarification** | When routing confidence is below threshold, asks the user to disambiguate instead of guessing                       | `core/graph/nodes.py` (`clarify_query_node`)    |
| **Query rewriting**              | LLM resolves pronouns and expands abbreviations using conversation history                                          | `core/rag/query_rewriter.py`                    |
| **Multi-query expansion**        | Generates alternative phrasings of the same query for broader recall                                                | `core/rag/query_rewriter.py`                    |
| **Self-RAG (corrective RAG)**    | LLM judge verifies whether retrieved context is sufficient; reformulates and retries if not                         | `core/rag/self_rag.py`                          |
| **Retrieval feedback loop**      | Implicit signal from user interactions used to re-weight future results                                             | `core/rag/feedback.py`                          |
| **Streaming responses**          | Token-by-token SSE streaming with per-agent progress events                                                         | `core/graph/workflow.py`, `backend/api/routes/` |


---

## Tier 3 — Research / Advanced Features

Experimental or computationally expensive features that go beyond typical
industry RAG systems.  Enabled in the `deep` retrieval profile.


| Component                                   | Description                                                                                                 | Key Files                             |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Query decomposition**                     | Splits multi-part questions into atomic sub-queries, retrieves independently, then merges results           | `core/rag/query_decomposer.py`        |
| **HyDE (Hypothetical Document Embeddings)** | Generates a hypothetical answer, retrieves with both query and hypothesis embeddings, fuses via RRF for better semantic alignment | `core/rag/query_rewriter.py` (`HyDE`), `pipeline.py` (`_search_with_hyde`) |
| **Proposition-based indexing**              | Decomposes chunks into atomic factual statements; indexes propositions alongside raw chunks                 | `core/rag/proposition_indexer.py`     |
| **Knowledge graph**                         | Extracts entity-relationship triples, stores in graph repo, performs multi-hop traversal for richer context | `core/rag/knowledge_graph.py`         |


---

## Tier × Profile Mapping


| Profile    | Tier 1 | Tier 2 | Tier 3 | Typical use-case                               |
| ---------- | ------ | ------ | ------ | ---------------------------------------------- |
| `fast`     | ✅      | —      | —      | Simple factoid look-ups, high-throughput batch |
| `balanced` | ✅      | ✅      | —      | Day-to-day student Q&A (default)               |
| `deep`     | ✅      | ✅      | ✅      | Complex multi-hop or comparison questions      |


The `select_profile_for_query()` heuristic in `retrieval_profiles.py` picks a
profile automatically based on query surface features (word count, comparison
markers, decomposition cues).  Callers can also pass an explicit profile name.

---

## Design Principles Across Tiers

1. **Graceful degradation** — Disabling any higher-tier feature never breaks
   lower tiers.  Each optional component has a `use_*` toggle and a safe
   no-op fallback.  The `fallback()` utility ensures every external call has
   an ordered degradation chain.
2. **Budget-aware** — The `RequestBudget` object travels with every query.
   Higher-tier stages check the budget before making LLM calls, so even the
   `deep` profile obeys cost/latency caps.
3. **Observable** — `RequestMetrics` tracks per-stage value (did it change
   the input? the output?) and `AggregateMetrics` accumulates counters across
   requests for dashboards and alerting.
4. **Cache-resilient** — `RedisResponseCache` persists across restarts and
   multi-instance deployments; falls back to in-memory if Redis is unavailable.

