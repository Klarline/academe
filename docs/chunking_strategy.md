# Chunking Strategy Decision

## Current Configuration

Adaptive chunking is enabled by default. The system auto-detects document type and applies per-type profiles:

| Document Type | Chunk Size | Overlap | Strategy | Rationale |
|---------------|-----------|---------|----------|-----------|
| Textbook | 1200 chars | 300 | semantic | Preserves chapter/section structure |
| Paper | 800 chars | 200 | recursive | Dense, self-contained paragraphs |
| Notes | 600 chars | 100 | recursive | Short bullet-point structure |
| Code | 1000 chars | 150 | recursive | Function/class boundaries |
| General (fallback) | 1000 chars | 200 | recursive | Balance between context and precision |

## Experiments to Run

Test different strategies on evaluation queries:

| Strategy | Chunk Size | Overlap | Use Case |
|----------|-----------|---------|----------|
| Small | 512 | 100 | Higher precision, risk of fragmented context |
| Current | 1000 | 200 | Default balance |
| Large | 1500 | 300 | More context, lower precision |
| Semantic | Variable | Smart | Best for textbooks, 2x processing time |

## Decision Framework

1. **Run chunking comparison** using `tests/evaluation/chunking_test_cases.py` and `RetrievalEvaluator`
2. **Measure** Precision@5 and Recall@10 for each strategy
3. **Automatic selection** based on document type — handled by `doc_type_detector.py`:
   - **Textbooks**: Semantic chunking (3% better, 2x cost)
   - **Papers**: 800 chars, 200 overlap (dense paragraphs)
   - **Notes**: 600 chars, 100 overlap (short bullet points)
   - **Code**: 1000 chars, 150 overlap (function boundaries)
   - **General**: 1000 chars, 200 overlap (default balance)

## Trade-offs

- **Larger chunks**: Better context, worse precision (more noise)
- **Smaller chunks**: Better precision, risk of losing context
- **Semantic**: Best retrieval, higher processing cost
- **200 char overlap**: Empirically prevents breaking concept boundaries (test 100/200/300)

## Additional Features

- **Parent-child chunking**: Small chunks for retrieval, expand to parent chunk for LLM context (`DocumentChunker.chunk_with_parents()`)
- **Contextual embeddings**: Document title + section prepended before embedding (`SemanticSearchService._enrich_text_for_embedding()`)
- **Sliding window**: Adjacent chunks from the same document included for broader LLM context
- **Document type detection**: Heuristic classifier in `core/documents/doc_type_detector.py` (keyword analysis, filename hints)

## Next Steps

1. ~~Create seeded test document~~ ✅ Done
2. ~~Add `relevant_chunk_ids` to `CHUNKING_TEST_CASES`~~ ✅ Done
3. Run `experiments/chunking_comparison.py` to compare adaptive profiles against fixed defaults
4. Document results in `docs/EVALUATION_RESULTS.md`
