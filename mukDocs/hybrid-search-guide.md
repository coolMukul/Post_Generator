# Hybrid Retrieval Implementation Guide

## Overview

This Phase implements **Hybrid Retrieval** - an advanced search system combining:
1. **Vector Similarity Search** (semantic understanding)
2. **BM25 Keyword Search** (lexical matching)
3. **Reciprocal Rank Fusion (RRF)** (intelligent result merging)

This approach delivers better search results than using either method alone.

## Architecture

### Components

```
┌─────────────┐
│     API     │ (TypeScript)
│   Port 3201 │
└──────┬──────┘
       │
      │ POST /hybrid-retrieval
       │
       v
┌─────────────────────────────────────────┐
│   HybridRetrievalRepository (Python)       │
│                                          │
│   ┌─────────────┐   ┌────────────────┐ │
│   │   Vector    │   │    Keyword     │ │
│   │   Search    │   │    Search      │ │
│   │ (pgvector)  │   │   (BM25)       │ │
│   └──────┬──────┘   └────────┬───────┘ │
│          │                    │         │
│          └────────┬───────────┘         │
│                   v                     │
│            ┌──────────────┐             │
│            │     RRF      │             │
│            │    Merger    │             │
│            └──────────────┘             │
└──────────────────┬──────────────────────┘
                   │
                   v
           ┌──────────────┐
           │  PostgreSQL  │
           │  + pgvector  │
           └──────────────┘
```

### How It Works

1. **Vector Search**
   - Converts query to embedding using OpenAI
   - Performs cosine similarity search in `document_vectors` table
   - Returns top-k most semantically similar chunks

2. **Keyword Search**
   - Tokenizes query for PostgreSQL full-text search
   - Uses BM25 ranking algorithm (via `ts_rank_cd`)
   - Returns top-k lexically matching chunks

3. **RRF Merging**
   - Combines rankings from both searches
   - Formula: `score = Σ(weight / (k + rank))`
   - Normalizes final scores to 0-1 range

## Python Implementation

### HybridRetrievalRepository

Location: `packages/workers/src/repositories/hybrid_retrieval_repository.py`

```python
from repositories import HybridRetrievalRepository, HybridRetrievalConfig

# Initialize
config = HybridRetrievalConfig(
    default_limit=20,
    default_min_score=0.3,
    default_vector_weight=0.7,
    default_keyword_weight=0.3,
    rrf_k=60
)

repo = HybridRetrievalRepository(
    connection_string=DATABASE_URL,
    config=config
)

# Perform search
results = repo.hybrid_retrieval(
    query="machine learning applications",
    query_embedding=embedding_vector,  # from OpenAI
    project_key='researchpaper',
    limit=10,
    min_score=0.4
)

# Results are sorted by hybrid score
for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Source: {result.rank_source}")  # 'vector', 'keyword', or 'hybrid'
    print(f"Content: {result.content[:100]}...")
```

### Key Features

#### 1. Configurable Weights

```python
# Emphasize semantic understanding
repo.hybrid_retrieval(
    query="...",
    query_embedding=...,
    vector_weight=0.8,    # 80% weight on semantic
    keyword_weight=0.2    # 20% weight on keywords
)

# Emphasize exact keyword matching
repo.hybrid_retrieval(
    query="...",
    query_embedding=...,
    vector_weight=0.3,    # 30% weight on semantic
    keyword_weight=0.7    # 70% weight on keywords
)
```

#### 2. Query Expansion

The keyword search includes intelligent query expansion:

```python
# Original query: "neural networks deep learning"

# Without expansion (AND):
# → requires ALL words present (more precise, fewer results)

# With expansion (OR):
# → matches ANY word (more flexible, more results)
```

#### 3. Score Normalization

All scores are normalized to 0-1 range:
- **1.0**: Perfect match (top result)
- **0.7-0.9**: Excellent match
- **0.4-0.6**: Good match
- **< 0.4**: Weak match (filtered by default)

#### 4. Rank Source Tracking

Results include `rank_source` to understand how they were found:
- `'vector'`: Found only by semantic search
- `'keyword'`: Found only by keyword search
- `'hybrid'`: Found by both methods (highest confidence!)

## API Endpoint

### Request

```http
POST http://localhost:3201/hybrid-retrieval
Content-Type: application/json

{
  "query": "machine learning in healthcare",
  "project_key": "researchpaper",
  "limit": 20,
  "min_score": 0.3,
  "vector_weight": 0.7,
  "keyword_weight": 0.3,
  "rrf_k": 60
}
```

### Response

```json
{
  "results": [
    {
      "id": "uuid-here",
      "document_id": "doc-uuid",
      "chunk_index": 5,
      "content": "Machine learning has revolutionized healthcare...",
      "context_summary": "Discussion of ML applications in medical diagnosis",
      "score": 0.892,
      "rank_source": "hybrid",
      "document_title": "AI in Healthcare: A Review",
      "metadata": {}
    }
  ],
  "query": "machine learning in healthcare",
  "project_key": "researchpaper",
  "total": 15,
  "config": {
    "vector_weight": 0.7,
    "keyword_weight": 0.3,
    "rrf_k": 60
  }
}
```

### PowerShell Example

```powershell
$body = @{
    query = "transformer architecture attention mechanism"
    project_key = "researchpaper"
    limit = 10
    min_score = 0.4
    vector_weight = 0.7
    keyword_weight = 0.3
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3201/hybrid-retrieval" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### cURL Example

```bash
curl -X POST http://localhost:3201/hybrid-retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "query": "reinforcement learning robotics",
    "project_key": "researchpaper",
    "limit": 15,
    "min_score": 0.35
  }'
```

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | *required* | Search query text |
| `project_key` | string | `'researchpaper'` | Project to search within |
| `limit` | number | `20` | Maximum results to return |
| `min_score` | number | `0.3` | Minimum score threshold (0-1) |
| `vector_weight` | number | `0.7` | Weight for vector search (0-1) |
| `keyword_weight` | number | `0.3` | Weight for keyword search (0-1) |
| `rrf_k` | number | `60` | RRF constant (higher = more conservative) |

### Tuning RRF_K

The `rrf_k` parameter controls how aggressively rankings are merged:

- **Low (20-40)**: Aggressive merging, favors top results from each search
- **Medium (60-80)**: Balanced merging (recommended)
- **High (100+)**: Conservative merging, considers more results equally

## Advantages Over TypeScript Version

### 1. **Better Performance**
- Direct PostgreSQL connection (no ORM overhead)
- Efficient rank-only fetching before full detail retrieval
- Single query for result details using `ANY(%s)`

### 2. **Enhanced Query Processing**
- Smart query expansion for better keyword matching
- Better handling of special characters
- Configurable AND/OR logic

### 3. **Improved Architecture**
- Clean separation of concerns (search/rank/merge)
- Configurable through dataclass
- Type-safe with dataclasses
- Better error handling

### 4. **More Flexible**
- Easy to add new ranking algorithms
- Simple to modify weights per-query
- Extensible for custom scoring functions

## Database Requirements

### Required Tables

```sql
-- Ensure these exist (from init_db.sql)
- documents
- projects
- project_documents
- document_vectors
```

### Required Indexes

```sql
-- Vector similarity index
CREATE INDEX idx_document_vectors_embedding ON document_vectors
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search (automatic with to_tsvector)
-- PostgreSQL creates GIN index automatically for text search
```

## Testing

### Unit Test Example

```python
import pytest
from repositories import HybridRetrievalRepository

@pytest.fixture
def repo():
    return HybridRetrievalRepository(
        connection_string=TEST_DB_URL
    )

def test_hybrid_retrieval(repo):
    # Mock embedding
    embedding = [0.1] * 1536

    results = repo.hybrid_retrieval(
        query="test query",
        query_embedding=embedding,
        limit=5
    )

    assert len(results) <= 5
    assert all(r.score >= 0 and r.score <= 1 for r in results)
    assert results[0].score >= results[-1].score  # Sorted desc
```

### Integration Test (Manual)

```powershell
# 1. Ingest a document
Invoke-RestMethod -Uri "http://localhost:3201/pdf/process" `
    -Method Post -ContentType "application/json" `
    -Body '{"url":"https://arxiv.org/pdf/2301.00001.pdf","title":"Test Paper"}'

# 2. Wait for processing to complete
# Check job status...

# 3. Test hybrid search
Invoke-RestMethod -Uri "http://localhost:3201/hybrid-retrieval" `
    -Method Post -ContentType "application/json" `
    -Body '{"query":"neural networks","limit":5}'

# 4. Verify results
# - Check scores are normalized (0-1)
# - Check rank_source values
# - Verify content relevance
```

## Troubleshooting

### No Results Returned

**Cause**: `min_score` threshold too high or no matching documents

**Solution**:
```json
{
  "query": "your query",
  "min_score": 0.1,  // Lower threshold
  "limit": 50        // Increase limit
}
```

### All Results from Vector Search Only

**Cause**: Keyword search not finding matches

**Solution**:
- Check query has meaningful keywords
- Try simpler query terms
- Increase `keyword_weight`
- Enable query expansion in config

### Scores Not Normalized

**Cause**: No results from either search

**Solution**:
- Verify documents are ingested
- Check `project_key` is correct
- Ensure embeddings are generated

## Next Steps

1. **Implement in Python Worker** - See `mukDocs/schema-migration-guide.md`
2. **Add Embedding Generation** - Integrate OpenAI embedding service
3. **Create Handler** - Connect API to Python hybrid search
4. **Add to UI** - Create hybrid search page
5. **Optimize Performance** - Add caching, query result caching

## References

- [Reciprocal Rank Fusion Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
