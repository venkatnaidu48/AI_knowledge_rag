# RAG Pipeline Module

Complete Retrieval-Augmented Generation (RAG) pipeline with modular, maintainable components.

## Overview

The RAG pipeline orchestrates 5 main steps:

```
1. RETRIEVAL → 2. RANKING → 3. CONTEXT BUILDING → 4. LLM GENERATION → 5. VALIDATION
```

## Module Structure

### `retrieval.py` - Document Retrieval
Retrieves relevant documents from FAISS vector store.

**Key Classes:**
- `DocumentRetriever` - Searches FAISS index for similar documents
- `RetrievedDocument` - Represents a retrieved document chunk

**Features:**
- FAISS vector search
- Embedding query processing
- Similarity score calculation
- Configurable top-K retrieval

**Usage:**
```python
from rag_pipeline.retrieval import DocumentRetriever

retriever = DocumentRetriever(
    index_path="./data/vector_index/faiss.index",
    metadata_path="./data/vector_index/faiss_metadata.pkl",
    top_k=5,
    min_similarity=0.3,
)

results = retriever.retrieve("What is the company strategy?")
```

### `ranking.py` - Result Ranking & Filtering
Ranks and filters retrieved documents based on relevance and quality.

**Key Classes:**
- `ResultRanker` - Ranks documents by multiple factors
- `RankedResult` - Ranked document with score

**Ranking Factors:**
- Similarity Score (70%) - How relevant to query
- Source Diversity (20%) - Avoid duplicates
- Text Quality (10%) - Document quality heuristics

**Usage:**
```python
from rag_pipeline.ranking import ResultRanker

ranker = ResultRanker(
    similarity_weight=0.7,
    diversity_weight=0.2,
    quality_weight=0.1,
)

ranked = ranker.rank(retrieved_documents)
```

### `context_builder.py` - Context Construction
Builds formatted context from ranked documents for LLM input.

**Key Classes:**
- `ContextBuilder` - Builds readable context from documents
- `BuiltContext` - Formatted context with metadata

**Features:**
- Multiple format styles (default, structured, minimal)
- Source attribution
- Length management
- Context truncation strategies

**Usage:**
```python
from rag_pipeline.context_builder import ContextBuilder

builder = ContextBuilder(
    max_context_length=2000,
    context_format="default",
    include_source=True,
)

context = builder.build(ranked_results)
```

### `pipeline.py` - Main Orchestrator
Coordinates all pipeline components.

**Key Classes:**
- `RAGPipeline` - Main orchestrator
- `PipelineResponse` - Complete pipeline response

**Features:**
- Orchestrates retrieval → ranking → context building
- Timing and logging
- Status monitoring
- Error handling

**Usage:**
```python
from rag_pipeline import RAGPipeline

pipeline = RAGPipeline(
    top_k=5,
    max_context_length=2000,
)

result = pipeline.process_query("What is the company strategy?")
print(result['context'])
```

### `__init__.py` - Module Exports
Exports main classes for easy importing.

**Usage:**
```python
from rag_pipeline import (
    RAGPipeline,
    DocumentRetriever,
    ResultRanker,
    ContextBuilder,
)
```

## Data Flow

### Input
```
User Query
  ↓
"What is the company strategy?"
```

### Step 1: Retrieval
```
Query → Embed → FAISS Search → Retrieved Documents
                               (top_k=5)
```

### Step 2: Ranking
```
Retrieved Documents
  ↓
Score by: similarity, diversity, quality
  ↓
Ranked Results (sorted by rank_score)
```

### Step 3: Context Building
```
Ranked Results
  ↓
Format + Truncate
  ↓
Formatted Context String
```

### Output
```
Context
Sources
Metadata
```

## Configuration

### Key Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `top_k` | 5 | Number of documents to retrieve |
| `min_similarity` | 0.3 | Minimum similarity threshold |
| `max_context_length` | 2000 | Maximum context length |
| `similarity_weight` | 0.7 | Weight for similarity score |
| `diversity_weight` | 0.2 | Weight for source diversity |
| `quality_weight` | 0.1 | Weight for text quality |

### Tuning

**For Better Quality (slower):**
```python
pipeline = RAGPipeline(
    top_k=10,  # More documents
    min_similarity=0.5,  # Stricter filtering
)
```

**For Speed (lower quality):**
```python
pipeline = RAGPipeline(
    top_k=3,  # Fewer documents
    min_similarity=0.2,  # Loose filtering
    max_context_length=1000,  # Shorter context
)
```

## Integration with LLM & Validation

### Full Pipeline (with Generation & Validation)

```python
from rag_pipeline import RAGPipeline
from llm_generation import LLMGenerator
from response_validators import ResponseValidators

# Initialize components
pipeline = RAGPipeline()
generator = LLMGenerator()
validator = ResponseValidators()

# Process query
rag_result = pipeline.process_query(query)

# Generate answer
answer = generator.generate_answer(
    context=rag_result['context'],
    question=query,
)

# Validate response
validation = validator.validate_response(
    question=query,
    answer=answer,
    context=rag_result['context'],
)

print(f"Answer: {answer}")
print(f"Quality Score: {validation.overall_score:.2%}")
```

## Performance Tuning

### Retrieval Speed
- Reduce `top_k` for faster retrieval
- Use smaller embedding model
- Enable Redis caching for embeddings

### Ranking Speed
- Disable `enforce_diversity` if not needed
- Reduce number of results to rank

### Context Building Speed
- Reduce `max_context_length`
- Use "minimal" format instead of "structured"

### Memory Usage
- Use streaming for large indexes
- Enable disk-based FAISS index

## Debugging

### Enable Verbose Logging
```python
pipeline = RAGPipeline(verbose=True)
result = pipeline.process_query(query)
```

### Check Statistics
```python
status = pipeline.get_status()
print(status['retriever'])
```

### Analyze Results
```python
result = pipeline.process_query(query)
print(f"Retrieved: {result['retrieved_documents']} documents")
print(f"Ranked: {result['ranked_results']} results")
print(f"Context: {len(result['context'])} characters")
print(f"Processing time: {result['processing_time_ms']:.2f}ms")
```

## Testing

```python
import pytest
from rag_pipeline import RAGPipeline

def test_retrieval():
    pipeline = RAGPipeline()
    result = pipeline.process_query("test query")
    assert result['retrieved_documents'] > 0

def test_ranking():
    pipeline = RAGPipeline()
    result = pipeline.process_query("test query")
    assert result['ranked_results'] <= result['retrieved_documents']

def test_context_length():
    pipeline = RAGPipeline(max_context_length=1000)
    result = pipeline.process_query("test query")
    assert len(result['context']) <= 1000
```

## Best Practices

1. **Start Simple** - Use default parameters first
2. **Monitor Performance** - Track retrieval time and quality
3. **Test Thresholds** - Experiment with similarity and quality scores
4. **Use Caching** - Cache embeddings in Redis for repeated queries
5. **Backup Index** - Regularly backup FAISS indexes
6. **Log Everything** - Enable logging for debugging

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No results retrieved | Lower `min_similarity` threshold |
| Too many irrelevant results | Increase `min_similarity` or enable diversity |
| Slow retrieval | Reduce `top_k` or cache embeddings |
| Low quality context | Increase `top_k` or improve query |
| Out of memory | Reduce batch size or use smaller model |

## Related Modules

- `src/embedding/` - Embedding models and caching
- `src/generation/` - LLM generation
- `src/validation/` - Response validation
- `src/query_pipeline/` - Query processing
- `src/vector_db/` - Vector database integration
