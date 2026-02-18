# TODO Tracker

## Upcoming Changes

- Phase 2: Document ingestion pipeline end-to-end test via UI ingest page
- Add unit tests for Phase 4-5 agents (Phase4-agent tests, Phase5-content tests)
- Add unit tests for hybrid_retrieve (Phase3-hybrid-retrieve tests)
- Add tsvector GIN index on document_vectors.content for faster keyword search
- Phase 6: Security & Deployment (secrets management, Docker Compose, auth)

---

## Completed Changes

### Phase 4 & 5 – Agent Framework, Core Tools & Multi-Stage Content Agents (2026-02-18) ✅

**Agent Framework (`packages/workers/src/agents/`)**

- Created `agents/base.py` – AgentBase class with step-level logging (`[Agent:<name>][step:<tool>]`), execution timing (start/end/duration), LLM call counting, resource limit enforcement (time + LLM calls), step trail accumulation for audit
- Created `agents/registry.py` – Agent registry with `@register_agent` decorator, `get_agent(job_type)` lookup, `list_agents()` for manifest enumeration
- All agents use LangGraph StateGraph with typed state, `START` → nodes → `END` edges
- Each agent includes: manifest (name, version, tools, resource limits), Pydantic input/output contract, step-level console logging, job_type for worker dispatch

**Core Tools (`packages/workers/src/tools/`)**

- Created `tools/search_papers.py` – wraps `HybridWorker.hybrid_retrieve()` for agent use, does NOT rebuild retrieval logic
- Created `tools/get_abstract.py` – fetches document metadata/abstract from `DocumentRepository`
- Created `tools/summarize_chunk.py` – LLM-based chunk summarization via `LLMService`
- Created `tools/cite_source.py` – LLM-based citation verification and formatting

**LLM Service (`packages/workers/src/services/llm_service.py`)**

- Multi-provider LLM service mirroring EmbeddingService pattern
- Supports Gemini (default: `gemini-2.0-flash`) and OpenAI (`gpt-4o-mini`)
- `LLM_PROVIDER` and `LLM_MODEL` env vars for configuration
- `chat()` for plain text responses, `chat_json()` for structured JSON responses
- Lazy client initialization, provider diagnostics on startup

**Phase 4 Agents:**

- ✅ **Research Query Agent** (`research_query_agent.py`) – LangGraph StateGraph: search → rank → explain. Wraps Phase 3 hybrid retrieval via `search_papers` tool, uses LLM to generate relevance explanations for top results. Returns results with `relevanceReason`, `agentSteps`, `executionTimeMs`
- ✅ **Citation Validator Agent** (`citation_validator_agent.py`) – LangGraph StateGraph: retrieve_source → verify_claim → format_citation. Verifies claim provenance against source chunks, outputs verified/confidence/formatted_citation

**Phase 5 Agents:**

- ✅ **Insight Extraction Agent** (`insight_extraction_agent.py`) – LangGraph StateGraph: retrieve → extract → structure. Retrieves corpus chunks, uses LLM to extract structured insights (claim, summary, confidence, tags), links evidence to source chunks
- ✅ **LinkedIn Post Generator Agent** (`linkedin_post_agent.py`) – LangGraph StateGraph: headline → draft → format. Generates A/B headline candidates, writes full post with tone control, produces hashtags. Enforces max length
- ✅ **Content Strategy Orchestrator** (`content_strategy_agent.py`) – Meta-agent LangGraph StateGraph: research → insights → post → review. Chains retrieval, insight extraction, and post generation into a single end-to-end pipeline. Includes HITL-ready review checkpoint

**Agent Pydantic Schemas (`packages/workers/src/models/agent_schemas.py`)**

- `AgentManifest`, `AgentResourceLimits` – agent identity and constraints
- `ResearchQueryRequest/Response`, `ResearchQueryResultItem` – research query I/O
- `CitationRequest/Result` – citation validator I/O
- `InsightExtractionRequest/Response`, `InsightItem`, `EvidenceItem` – insight extraction I/O
- `LinkedInPostRequest/Response`, `InsightInput` – LinkedIn post I/O
- `ContentStrategyRequest/Response` – content strategy orchestrator I/O

**Config Updates (`packages/workers/src/config.py`)**

- Added `LLM_PROVIDER` (default: `gemini`) and `LLM_MODEL` settings
- Startup diagnostics now display LLM provider alongside embedding provider

**Worker Loop (`packages/workers/src/worker.py`)**

- Extended `run_worker_loop()` to dispatch agent jobs via `get_agent(job_type)` from the registry
- `hybrid_retrieval` jobs still handled directly by `HybridWorker`
- All other job types resolved via agent registry: `research_query_agent`, `insight_extraction_agent`, `linkedin_post_agent`, `citation_validator_agent`, `content_strategy_agent`
- Unknown job types marked FAILED with error message

**API Endpoints (`packages/api/app/main.py`)**

- Added `POST /agent/research-query` – submits `research_query_agent` job, returns `{ success, jobId }`
- Added `POST /agent/insight-extraction` – submits `insight_extraction_agent` job, returns `{ success, jobId }`
- Added `POST /agent/linkedin-post` – submits `linkedin_post_agent` job, returns `{ success, jobId }`
- All agent endpoints use existing `GET /queue/jobs/{job_id}` for polling
- API version bumped to 0.4.0

**Dependencies (`packages/workers/requirements.txt`)**

- Updated `langgraph>=0.2.0` (from `>=0.0.20`) for modern StateGraph API

**Documentation (`mukDocs/`)**

- Created `ARC-comms.md` – ARC team communication log with session start, task assignments, architecture decisions
- Updated `TODO.md` with Phase 4-5 completion details

**Architecture alignment with CodingGuidelines.md:**

- All business logic in workers (agents, tools, services) — API is thin job submission layer
- Single `main_queue` for all job types (hybrid retrieval + all agents)
- Console logs trace every agent step with `[Agent:<name>][step:<tool>]` convention
- Job status model preserved: InProgress → Success/Failed
- Real LLM API calls (Gemini/OpenAI) — no mocks in production code
- No fallback code, no TODO comments in code
- Pydantic validation on all agent inputs/outputs

---

### Phase 3 – Hybrid Retrieval Rewrite + Gemini Embedding Migration (2026-02-17) ✅

**Worker layer (`packages/workers/src/`)**

- Created `models/schemas.py` – Pydantic models: JobStatus, SearchMode, SearchRequest, SearchResult, SearchResponse, JobRecord
- Rewrote `repositories/vector_repository.py` – corrected table from `vectors` to `document_vectors`, changed IDs from integer to UUID (`project_document_id`), added `keyword_search()` using PostgreSQL full-text search (`ts_rank_cd` + `plainto_tsquery`)
- Rewrote `repositories/document_repository.py` – UUID-based, added `count_documents()`, `link_document_to_project()`, `get_project_by_key()`
- **Updated `services/embedding_service.py`** – **Multi-provider embedding support:**
  - ✅ Migrated from deprecated `google.generativeai` (<=0.7.x) to `google.genai` SDK (v1.0.0+)
  - ✅ Updated default model from `text-embedding-004` (deprecated Jan 2026) to `gemini-embedding-001`
  - ✅ Added `EMBEDDING_PROVIDER` config: supports `gemini` (default) or `openai`
  - ✅ Unified dimension to 1536 for cross-provider compatibility with existing DB vectors
  - ✅ Added cross-provider mismatch detection (auto-ignores OpenAI model names when using Gemini)
  - ✅ `embed_query()` and `embed_texts()` methods work with both providers
  - ✅ Graceful fallback error messages for missing API keys
- **Updated `config.py`** – Added startup diagnostics to display active provider, model, and API key status
- Created `services/job_store.py` – Redis-backed job lifecycle: `create_job()` (pushes to `main_queue`), `get_job()`, `mark_success()`, `mark_failed()`, `dequeue()` (BLPOP)
- Rewrote `worker.py` – full `HybridWorker.hybrid_retrieve()` pipeline: embed query via configured provider (Gemini or OpenAI), vector similarity search (pgvector cosine), keyword search (PostgreSQL FTS), Reciprocal Rank Fusion (RRF) for hybrid mode, min_score filtering. Added `run_worker_loop()` that listens on Redis `main_queue` and processes `hybrid_retrieval` jobs with console logging at each step
- Removed `jobs/pdf_processor.py` placeholder

**Dependencies (`requirements.txt`)**

- ✅ Replaced `google-generativeai>=0.7.0` with `google-genai>=1.0.0`
- ✅ Added `psycopg`, `redis`, `pydantic`, `pydantic-settings`

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

**Documentation (`mukDocs/`)**

- ✅ Updated `planning-doc-refined.md` to reflect Gemini embedding support in Phase 3
- ✅ Updated `phase1-setup-guide.md` with new environment variables (`EMBEDDING_PROVIDER`, `GEMINI_API_KEY`)
- ✅ Updated `TODO.md` to mark Phase 3 as complete with Gemini migration details

**Architecture alignment with CodingGuidelines.md:**

- Worker processes jobs from Redis queue (not called directly by API)
- API is a thin layer – no business logic, only job submission and status polling
- No fallback code
- No mock data
- Console logs trace job lifecycle (start, steps, scores, completion/failure)
- Job status model: InProgress (start_time), Success (result + start/end time), Failed (error + start/end time)
- Multi-provider support allows easy switching between embedding providers

**Migration Notes:**

- **Existing documents** in the DB were embedded with OpenAI. For optimal search quality, consider re-embedding with Gemini.
- **New documents** ingested will use the configured provider (Gemini by default)
- Both ingestion and retrieval use the same `EmbeddingService`, ensuring consistency

### Phase 1 – Foundation (completed earlier)

- Monorepo setup, package configs, basic infrastructure
