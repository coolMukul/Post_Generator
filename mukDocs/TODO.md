# TODO Tracker

## Upcoming Changes

- Phase 4: Agent Framework & Core Tools (Research Query Agent, Citation Validator)
- Phase 2: Document ingestion pipeline end-to-end test via UI ingest page
- Add unit tests for hybrid_retrieve (Phase3-hybrid-retrieve tests)
- Add tsvector GIN index on document_vectors.content for faster keyword search

---

## Completed Changes

### Phase 3 – Hybrid Retrieval Rewrite (2026-02-11)

**Worker layer (`packages/workers/src/`)**

- Created `models/schemas.py` – Pydantic models: JobStatus, SearchMode, SearchRequest, SearchResult, SearchResponse, JobRecord
- Rewrote `repositories/vector_repository.py` – corrected table from `vectors` to `document_vectors`, changed IDs from integer to UUID (`project_document_id`), added `keyword_search()` using PostgreSQL full-text search (`ts_rank_cd` + `plainto_tsquery`)
- Rewrote `repositories/document_repository.py` – UUID-based, added `count_documents()`, `link_document_to_project()`, `get_project_by_key()`
- Created `services/embedding_service.py` – OpenAI `text-embedding-3-small` (1536 dimensions), `embed_query()` and `embed_texts()` methods
- Created `services/job_store.py` – Redis-backed job lifecycle: `create_job()` (pushes to `main_queue`), `get_job()`, `mark_success()`, `mark_failed()`, `dequeue()` (BLPOP)
- Rewrote `worker.py` – full `HybridWorker.hybrid_retrieve()` pipeline: embed query via OpenAI, vector similarity search (pgvector cosine), keyword search (PostgreSQL FTS), Reciprocal Rank Fusion (RRF) for hybrid mode, min_score filtering. Added `run_worker_loop()` that listens on Redis `main_queue` and processes `hybrid_retrieval` jobs with console logging at each step
- Removed `jobs/pdf_processor.py` placeholder

**API layer (`packages/api/`)**

- Rewrote `app/main.py` – thin FastAPI layer with CORS middleware, no business logic:
  - `POST /search/submit` – submits `hybrid_retrieval` job to Redis queue, returns jobId
  - `GET /queue/jobs/{job_id}` – polls job status (in_progress / success / failed)
  - `GET /health` – verifies DB and Redis connectivity
  - `GET /documents/count` – returns document count
- Removed all dead TypeScript stub files: `src/routes/*.ts`, `src/handlers/*.ts`, `src/config/*.ts`, `src/server.ts`, `src/types/schemas.ts`
- Updated `requirements.txt` to include psycopg, redis, pydantic, pydantic-settings
- Changed default API port from 8000 to 3201 (matching .env.example)

**UI layer (`packages/ui/`)**

- Fixed default API port fallback from 3101 to 3201 in all pages (hybrid-search, research-query, research-query-agent, insight-extraction-agent, linkedin-post-agent)
- Reduced hybrid-search poll interval from 60s to 5s for faster feedback

**Architecture alignment with CodingGuidelines.md:**

- Worker processes jobs from Redis queue (not called directly by API)
- API is a thin layer – no business logic, only job submission and status polling
- No fallback code
- No mock data
- Console logs trace job lifecycle (start, steps, scores, completion/failure)
- Job status model: InProgress (start_time), Success (result + start/end time), Failed (error + start/end time)

### Phase 1 – Foundation (completed earlier)

- Monorepo setup, package configs, basic infrastructure
