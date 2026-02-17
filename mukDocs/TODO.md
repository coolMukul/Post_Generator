# TODO Tracker

## Upcoming Changes

- Phase 6: Security & Deployment (secrets management, Docker Compose, Helm)
- Phase 2: Document ingestion pipeline end-to-end test via UI ingest page
- Add unit tests for hybrid_retrieve (Phase3-hybrid-retrieve tests)
- Add tsvector GIN index on document_vectors.content for faster keyword search
- OPENAI_API_KEY or GEMINI_API_KEY required for LLM-backed summarization and insight extraction
- Implement additional concrete agents (EngineerAgent, UIAgent, TODOManagerAgent) beyond ResearchAgent
- Add Cohere reranking integration (Phase 7)
- Content pipeline HITL (human-in-the-loop) review step

---

## Completed Changes

### Phase 4+5 – Agent Framework & Content Pipeline (2026-02-17)

**Agent Framework (Phase 4) – `packages/workers/src/agents/`**

- Created `models/agent_schemas.py` – Pydantic models: AgentRunStatus, AgentRunRequest, AgentRunResult, ToolCallRecord, ManifestSchema, WorkflowState
- Created `agents/base_agent.py` – Abstract BaseAgent class with run lifecycle, tool registration, structured logging (`[Agent:<name>][step:<step>]`)
- Created `agents/registry.py` – AgentRegistry class: load_manifests(), register_agent(), create_agent(), list_agents(), has_agent()
- Created `agents/research_agent.py` – Concrete ResearchAgent: searches via hybrid_retrieve, extracts findings, assesses confidence, identifies risks, recommends next steps
- Created agent manifest templates in `mukDocs/agent-manifests/`:
  - ResearchAgent.manifest.json
  - EngineerAgent.manifest.json
  - UIAgent.manifest.json
  - TODOManagerAgent.manifest.json

**Core Tools (Phase 4) – `packages/workers/src/agents/tools/`**

- Created `tools/search_papers.py` – Reuses Phase 3 hybrid_retrieve via job queue (submit + poll pattern)
- Created `tools/summarize_chunk.py` – Multi-provider summarization (OpenAI gpt-4o-mini, Gemini 2.0 Flash), context_summary passthrough
- Created `tools/cite_source.py` – Citation formatting from search result metadata, batch citation via cite_sources_from_results()

**Workflow Nodes (Phase 5) – `packages/workers/src/agents/workflows/`**

- Created `workflows/insight_extraction.py` – LangGraph node: extracts insights from search results (LLM-backed or rule-based)
- Created `workflows/draft_generation.py` – LangGraph node: generates LinkedIn post drafts (LLM-backed or template-based)
- Created `workflows/citation_validation.py` – LangGraph node: validates citations against draft, checks relevance scores, missing titles, unreferenced docs
- Created `workflows/content_pipeline.py` – LangGraph StateGraph orchestrator: retrieval -> insight_extraction -> draft_generation -> citation_validation, conditional edges for empty results

**Worker Updates**

- Updated `worker.py` – Added `agent_run` and `content_pipeline` job type dispatch alongside existing `hybrid_retrieval`
- Added `_init_agent_registry()` function to load manifests and register agents at worker startup
- Worker now supports 3 job types: `hybrid_retrieval`, `agent_run`, `content_pipeline`

**API layer (`packages/api/`)**

- Updated `app/main.py` (v0.3.0) – Added Phase 4+5 endpoints:
  - `POST /agent/run` – submits agent_run job (validates agent name against registry)
  - `GET /agent/runs/{run_id}` – polls agent run status
  - `GET /agent/list` – lists registered agents with metadata
  - `POST /content/pipeline` – submits content_pipeline job (Phase 5 multi-stage workflow)
- Added AgentRunSubmitRequest, ContentPipelineSubmitRequest Pydantic models
- API loads AgentRegistry at startup for agent name validation

**UI layer (`packages/ui/`)**

- Created `/agent-run` page – submit agent runs or content pipeline jobs, select agent, configure search parameters, poll results with 5s interval, display findings/insights/draft/citations with expandable JSON
- Created `/agent-logs` page – display team interaction log entries, filter by agent, expandable details with attachments and follow-up actions
- Updated homepage (`/`) – added Agent Run and Agent Logs navigation cards, updated implementation status and architecture stack

**Unit Tests (`unit-test/`)**

- Phase4-001_agent_registry_test.py – 10 tests: manifest loading, registration, instantiation, error handling, real manifests
- Phase4-002_base_agent_test.py – 9 tests: lifecycle, tool registration/invocation, error handling, timestamps
- Phase4-003_core_tools_test.py – 9 tests: cite_source formatting, batch citation, summarize_chunk passthrough
- Phase4-004_agent_schemas_test.py – 10 tests: schema validation for all agent models
- Phase5-001_workflow_nodes_test.py – 11 tests: insight extraction, draft generation, citation validation
- **All 49 tests passing**

**Documentation (`mukDocs/`)**

- Created `mukDocs/teamInteraction.md` – Coordinator kickoff log entry with ISO8601 UTC timestamps
- Created `mukDocs/agent-manifests/` – 4 agent manifest JSON files
- Updated `mukDocs/TODO.md` – Phase 4+5 completed items, updated upcoming changes
- Updated `mukDocs/UnitTestResult.md` – Phase 4+5 test summary

**Architecture alignment with CodingGuidelines.md:**

- All business logic in workers, API is thin (no logic, just job submission/polling)
- Single main_queue for all job types (hybrid_retrieval, agent_run, content_pipeline)
- Console logs with `[Agent:<name>][step:<step>]` pattern at every worker/agent step
- No fallback code, no mock data
- Phase 3 hybrid_retrieve reused via job queue (POST /search/submit equivalent)
- Unit tests in unit-test/ with Phase-prefixed filenames

### Phase 3 – Hybrid Retrieval Rewrite + Gemini Embedding Migration (2026-02-17)

**Worker layer (`packages/workers/src/`)**

- Created `models/schemas.py` – Pydantic models: JobStatus, SearchMode, SearchRequest, SearchResult, SearchResponse, JobRecord
- Rewrote `repositories/vector_repository.py` – corrected table from `vectors` to `document_vectors`, changed IDs from integer to UUID (`project_document_id`), added `keyword_search()` using PostgreSQL full-text search (`ts_rank_cd` + `plainto_tsquery`)
- Rewrote `repositories/document_repository.py` – UUID-based, added `count_documents()`, `link_document_to_project()`, `get_project_by_key()`
- **Updated `services/embedding_service.py`** – **Multi-provider embedding support:**
  - Migrated from deprecated `google.generativeai` (<=0.7.x) to `google.genai` SDK (v1.0.0+)
  - Updated default model from `text-embedding-004` (deprecated Jan 2026) to `gemini-embedding-001`
  - Added `EMBEDDING_PROVIDER` config: supports `gemini` (default) or `openai`
  - Unified dimension to 1536 for cross-provider compatibility with existing DB vectors
  - Added cross-provider mismatch detection (auto-ignores OpenAI model names when using Gemini)
  - `embed_query()` and `embed_texts()` methods work with both providers
  - Graceful fallback error messages for missing API keys
- **Updated `config.py`** – Added startup diagnostics to display active provider, model, and API key status
- Created `services/job_store.py` – Redis-backed job lifecycle: `create_job()` (pushes to `main_queue`), `get_job()`, `mark_success()`, `mark_failed()`, `dequeue()` (BLPOP)
- Rewrote `worker.py` – full `HybridWorker.hybrid_retrieve()` pipeline: embed query via configured provider (Gemini or OpenAI), vector similarity search (pgvector cosine), keyword search (PostgreSQL FTS), Reciprocal Rank Fusion (RRF) for hybrid mode, min_score filtering. Added `run_worker_loop()` that listens on Redis `main_queue` and processes `hybrid_retrieval` jobs with console logging at each step
- Removed `jobs/pdf_processor.py` placeholder

**Dependencies (`requirements.txt`)**

- Replaced `google-generativeai>=0.7.0` with `google-genai>=1.0.0`
- Added `psycopg`, `redis`, `pydantic`, `pydantic-settings`

**API layer (`packages/api/`)**

- Rewrote `app/main.py` – thin FastAPI layer with CORS middleware, no business logic:
  - `POST /search/submit` – submits `hybrid_retrieval` job to Redis queue, returns jobId
  - `GET /queue/jobs/{job_id}` – polls job status (in_progress / success / failed)
  - `GET /health` – verifies DB and Redis connectivity
  - `GET /documents/count` – returns document count
- Removed all dead TypeScript stub files
- Changed default API port from 8000 to 3201

**UI layer (`packages/ui/`)**

- Fixed default API port fallback from 3101 to 3201 in all pages
- Reduced hybrid-search poll interval from 60s to 5s for faster feedback

**Migration Notes:**

- **Existing documents** in the DB were embedded with OpenAI. For optimal search quality, consider re-embedding with Gemini.
- **New documents** ingested will use the configured provider (Gemini by default)

### Phase 1 – Foundation (completed earlier)

- Monorepo setup, package configs, basic infrastructure
