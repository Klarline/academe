# Academe RAG Evaluation

Centralized evaluation framework for the Academe RAG pipeline.

## Dataset

**`datasets/academe_eval.json`** — 27 hand-curated questions across 5 query types:

| Query Type     | Count | Description                                                              |
|----------------|-------|--------------------------------------------------------------------------|
| factual        | 7     | Direct factual questions with specific answers                          |
| conceptual     | 6     | Explain concepts, mechanisms, or why something works                    |
| comparison     | 6     | Compare two or more concepts or architectures                           |
| cross_document | 3     | Requires information from multiple documents                             |
| procedural     | 4     | Step-by-step algorithm/pipeline explanation (answerable from papers)    |

Ambiguous and code-implementation questions were removed: RAGAS measures retrieval+generation quality for clear queries; clarification and code generation are tested separately.

### Hard Cases

- **multi_chunk**: Questions requiring information from multiple chunks
- **out_of_scope**: Questions where the answer is not in the documents (tests hallucination resistance)

### Expected Documents

The benchmark assumes 3–4 documents:

1. **Transformer paper** (Attention Is All You Need) — included
2. **ML textbook chapter** — backprop, optimization, etc.
3. **Lecture notes** — ML/DL concepts
4. **Second research paper** — e.g., BERT, GPT, or related

Upload additional documents to improve coverage. Questions tagged with `expected_documents: []` (e.g., Q027) test out-of-scope handling.

## Running Evaluation

```bash
cd backend
python run_academe_eval.py
```

### Options

| Flag           | Default | Description                              |
|----------------|---------|------------------------------------------|
| `--user-id`    | (Transformer user) | User ID with indexed documents   |
| `--limit N`    | all     | Limit to first N questions               |
| `--no-save`    | false   | Skip saving results to MongoDB            |
| `--no-reranking` | false | Disable reranking (faster)              |
| `--top-k`      | 5       | Number of context chunks to retrieve      |

### Examples

```bash
# Full evaluation (all 27 questions)
python run_academe_eval.py

# Quick test with 5 questions, no MongoDB save
python run_academe_eval.py --limit 5 --no-save

# Use a different user's documents
python run_academe_eval.py --user-id YOUR_USER_ID
```

## Output

- **Console**: RAGAS scores (faithfulness, answer_relevancy, context_precision, context_recall) with ratings
- **MongoDB**: Results logged to `rag_metrics` collection for trending and comparison

## Prerequisites

- MongoDB running with indexed documents
- `OPENAI_API_KEY` in `.env` (RAGAS uses OpenAI as judge)
- `pip install "ragas>=0.2.0,<0.3" datasets pyarrow`
