# Planning Document: Research Insight

**Tagline:** AI-Powered LinkedIn Content Generation

**Purpose:**
- Personal learning project to master multi-agent RAG architecture
- Portfolio piece for public showcase
- Built from scratch with original code
- Demonstrates enterprise-grade architectural skills in a different domain

**High-Level Concept:**
User interacts with a separate UI project that connects to a backend API. The system ingests multiple public documents (URL or file upload) and stores them in pgvector. A test UI screen validates each agent and phase during development. The final UI provides a textbox where users enter text, the application recommends matching ingested documents, users select documents, the application asks targeted questions, and then generates a copy-paste-ready LinkedIn post.

---

## Architecture Overview

### Conceptual Patterns

| Component | Learning Objective |
|-----------|-------------------|
| Per-topic knowledge bases | Multi-tenant vector store isolation |
| Research paper ingestion | Document processing pipeline |
| Research bundles | Knowledge base construction |
| Insight Extraction Agent | Multi-stage StateGraph workflows |
| LinkedIn Post Generator Agent | Content generation with validation |
| Citation Validator Agent | Quality assurance agents |
| Research Query Agent | ReAct pattern with tools |
| Content Strategy Orchestrator | Meta-agent coordination |
| Hybrid search (vector + BM25) | Advanced retrieval |
| Contextual embeddings | Chunk enhancement |

### Domain Differences from Company Project

| Aspect | Company Project | Personal Project |
|--------|----------------|-----------------|
| Domain | Government planning compliance | Academic research → social media |
| Users | Planners, councils, applicants | Researchers, content creators |
| Input | Planning schemes, policies | Research papers (PDFs, arXiv) |
| Output | Compliance reports, RFI letters | LinkedIn posts, threads, summaries |
| Validation | Regulatory citation checking | Academic citation checking |
| Tone | Formal, regulatory | Casual to professional (variable) |
| Scale | Multi-council (B2G) | Personal/small team (B2C) |
| Auth | Enterprise SSO | Simple auth or none initially |

---

## Database Schema Benefits

- ✅ Reusable `documents` table for any future project
- ✅ Project isolation via `project_documents` junction table
- ✅ Flexible metadata at document, project, and chunk levels
- ✅ Easy to add new projects without schema changes
- ✅ Documents can be shared across projects
- ✅ Status tracking for async processing
- ✅ Deduplication via checksum

---

## Phase-by-Phase Plan

### Phase 1: Foundation ✅
**Goal:** Set up monorepo and basic infrastructure

**Completed:**
- [x] Folder structure (research-api, research-workers, research-ui)
- [x] Python configs for all packages
- [x] package.json files with dependencies
- [x] Basic BullMQ worker setup with job stubs
- [x] Fastify API server with monitoring endpoints
- [x] Swagger documentation for API
- [x] Worker and API integration tests
- [x] Environment configuration (.env files)

**Learning focus:** Monorepo management, BullMQ patterns, Fastify API design, clean architecture separation

**Estimated Time:** 10-15 hours

---

### Phase 2: Document Ingestion Pipeline
**Goal:** Build paper processing pipeline in Python

---

#### Pipeline Overview

```
Download → Parse → Chunk → Context Summary → Embed & Store
   │         │        │           │              │
   ▼         ▼        ▼           ▼              ▼
file_path  markdown  chunks[]   chunks[]      vectors[]
checksum   metadata  + tokens   + context     in pgvector
```

**Progress Tracking:** Each step reports progress (10%, 25%, 40%, 55%, 70%, 85%, 100%)

**Deduplication:** SHA-256 checksum calculated after download; skip if already ingested

---

#### Component 1: Paper Downloader Service

**Purpose:** Download PDF from URL or decode from base64 upload

| Input | Output |
|-------|--------|
| URL or base64 file | Local file path + SHA-256 checksum |

**Behavior:**
- Support arXiv URLs (convert abstract URL to PDF URL)
- Decode base64 uploads to temp file
- Download with retry logic (3 attempts, exponential backoff)
- Calculate checksum before returning

**Python approach:** Use `httpx` for async HTTP, `hashlib` for checksum

---

#### Component 2: Document Parser Service

**Purpose:** Parse PDF to markdown using LlamaParse (best for academic papers with tables/figures)

| Input | Output |
|-------|--------|
| File path | Markdown text + metadata (title, authors, abstract, page_count) |

**Metadata Extraction:**
- Title: First `# heading` in markdown
- Abstract: Content under `## Abstract` section (first 500 chars)
- Authors: Heuristic - comma-separated names near title (first 20 lines)

**Validation:** Check PDF magic number (`%PDF` in first 4 bytes)

**Python approach:** Use `llama-parse` library with `result_type="markdown"`

---

#### Component 3: Document Chunker Service

**Purpose:** Split document into chunks with token counting

| Input | Output |
|-------|--------|
| Full document text | List of chunks with index, content, token_count, start/end positions |

**Configuration:**
- Chunk size: 1000 characters (configurable)
- Chunk overlap: 200 characters (configurable)
- Separators in order: `\n\n`, `\n`, `. `, ` `, ``

**Statistics to track:** Total chunks, total tokens, avg/min/max tokens per chunk

**Python approach:** Use `langchain-text-splitters.RecursiveCharacterTextSplitter`, `tiktoken` for token counting (fallback: chars/4)

---

#### Component 4: Contextual Summary Service

**Purpose:** Generate 1-2 sentence contextual summary for each chunk to improve retrieval (30-40% accuracy improvement)

| Input | Output |
|-------|--------|
| Chunks + document context (title/abstract) | Chunks with context_summary field added |

**Prompt focus:**
- What topic/section the chunk belongs to
- Key concepts or entities mentioned
- How it relates to document's main theme

**Processing:**
- Batch size: 5 chunks (avoid rate limits)
- Parallel processing within batch
- On failure: fallback to document context as summary

**Python approach:** Use `langchain-openai.ChatOpenAI` with gpt-4o-mini, temperature=0

---

#### Component 5: Embedding Service

**Purpose:** Generate embeddings for chunks (context + content combined) with multi-provider support

| Input | Output |
|-------|--------|
| Chunks with context | Embedding vectors (1536 dimensions) |

**Embedding strategy:** Combine context and content before embedding: `{context_summary}\n\n{content}`

**Multi-Provider Support:**
- **OpenAI**: `text-embedding-3-small` (default)
- **Google Gemini**: `gemini-embedding-001` (via `google.genai` SDK v1.0.0+)
- Automatic cross-provider mismatch detection
- Unified 1536-dimension output for compatibility

**Additional methods:**
- `embed_query()` for search queries (used by Research Query Agent)
- `validate_dimension()` to check database schema compatibility
- Provider-agnostic interface via environment variables

**Python approach:** Use `google.genai.Client` for Gemini or `langchain-openai.OpenAIEmbeddings` for OpenAI based on `EMBEDDING_PROVIDER` setting

---

#### Component 6: Paper Ingestion Orchestrator

**Purpose:** Orchestrate complete pipeline with progress tracking and error handling

| Input | Output |
|-------|--------|
| URL, optional title, optional project_id, optional base64 file | document_id, title, chunk_count, processing_time_ms |

**Orchestration steps:**

| Step | Progress | Action | On Error |
|------|----------|--------|----------|
| 1 | 10% | Download/decode PDF | Fail job |
| 2 | 25% | Check deduplication (return existing if found) | - |
| 3 | 40% | Parse PDF with LlamaParse | Fail job |
| 4 | 55% | Chunk document | Fail job |
| 5 | 70% | Generate contextual summaries | Continue with fallback |
| 6 | 85% | Generate embeddings | Fail job |
| 7 | 100% | Store in database | Fail job |

**Cleanup:** Delete temp file after successful ingestion

**Logging:** Log each step with timing, document title, chunk counts

---

#### Database Schema (pgvector)

**documents table:**
- id (UUID, primary key)
- url (TEXT)
- title (TEXT)
- checksum (TEXT, unique index for deduplication)
- metadata (JSONB - authors, abstract, chunk_stats)
- created_at (TIMESTAMP)

**vectors table:**
- id (UUID, primary key)
- document_id (UUID, foreign key)
- chunk_index (INT)
- content (TEXT)
- context_summary (TEXT)
- embedding (VECTOR(1536), IVFFlat index)
- token_count (INT)
- created_at (TIMESTAMP)

---

#### Python Project Structure

```
src/
├── services/           # Downloader, Parser, Chunker, Summarizer, Embedder
├── orchestrators/      # PaperIngestionOrchestrator
├── repositories/       # DocumentRepository, VectorRepository
├── models/             # Pydantic models for chunks, embeddings, jobs
├── config/             # Pydantic Settings for env vars
└── workers/            # Celery or ARQ worker for background jobs
```

---

#### Key Dependencies

| Purpose | Library |
|---------|---------|
| PDF Parsing | llama-parse |
| Text Splitting | langchain-text-splitters |
| Token Counting | tiktoken |
| LLM & Embeddings | langchain-openai, openai, google-genai |
| Database | asyncpg, sqlalchemy, pgvector |
| HTTP Client | httpx |
| Validation | pydantic |
| Background Jobs | celery or arq |

---

#### Configuration (Environment Variables)

| Variable | Purpose |
|----------|---------|
| LLAMA_CLOUD_API_KEY | LlamaParse API access |
| EMBEDDING_PROVIDER | Provider choice: `openai` or `gemini` (default: gemini) |
| OPENAI_API_KEY | OpenAI embeddings and context generation (if provider=openai) |
| GEMINI_API_KEY | Google Gemini embeddings (if provider=gemini) |
| EMBEDDING_MODEL | Model name (default: gemini-embedding-001 or text-embedding-3-small) |
| EMBEDDING_DIMENSION | Vector size (default: 1536) |
| CHUNK_SIZE | Target chunk size (default: 1000) |
| CHUNK_OVERLAP | Overlap between chunks (default: 200) |
| DATABASE_URL | PostgreSQL connection string |
| REDIS_URL | Redis for job queue |

**Estimated Time:** 20-25 hours

---

### Phase 3: Hardened Hybrid Retrieval & Indexing ✅
**Goal:** Production-quality retrieval layer with multi-provider embedding support

**Completed:**
- [x] Validated schema with pgvector embedding and index
- [x] Consistent embedding serialization on insert and query
- [x] Automated index maintenance and reindex scripts
- [x] End-to-end tests for vector and keyword search
- [x] Job renaming to `hybrid_retrieval`, updated producers/workers
- [x] **Multi-provider embedding support:**
  - [x] Migrated from deprecated `google.generativeai` to `google.genai` SDK (v1.0.0+)
  - [x] Updated default model from `text-embedding-004` (deprecated Jan 2026) to `gemini-embedding-001`
  - [x] Added cross-provider mismatch detection (auto-ignores OpenAI model names when using Gemini)
  - [x] Unified dimension to 1536 for cross-provider compatibility
  - [x] Added startup diagnostics in `config.py` to display active provider/model/key status
  - [x] Updated `requirements.txt` with `google-genai>=1.0.0`
  - [x] Supports both OpenAI (`text-embedding-3-small`) and Google Gemini (`gemini-embedding-001`)

**Learning focus:** Production readiness for vector stores, index tuning for ivfflat, reliable embedding serialization, multi-provider LLM/embedding architecture

**Estimated Time:** 8-12 hours

---

### Phase 4: Agent Framework & Core Tools
**Goal:** Lightweight, reusable agent framework with foundational tools

**Framework Infrastructure:**
- [ ] Integrate LangGraph or lightweight StateGraph runner
- [ ] Agent registry and manifest format (config, versioning)
- [ ] Agent contracts (Zod schemas) for input/output guarantees
- [ ] Developer CLI for local agent runs and step log inspection
- [ ] Mock LLM/embeddings provider for testing and CI
- [ ] Per-agent resource limits (time, tokens, concurrency)
- [ ] Step-level logging conventions (`[Agent:<name>][step:<tool>]`)
- [ ] Agent sandboxing, timeouts, and graceful aborts
- [ ] Basic metrics/tracing hooks (duration, tool calls, errors)

**Core Tools:**
- [ ] `search_papers` - Hybrid retrieval tool
- [ ] `get_abstract` - Fetch document abstracts
- [ ] `summarize_chunk` - Summarize document chunks
- [ ] `cite_source` - Citation formatting and verification

**Utility Agents (implement here):**
- [ ] **Research Query Agent** - Hybrid retrieval orchestrator accepting user queries, calling `search_papers`, ranking/merging results, returning candidates with scores
- [ ] **Citation Validator Agent** - Verifies claim provenance, formats citations, checks source correctness

**API Integration:**
- [ ] `POST /agent/run` endpoint
- [ ] Agent job enqueueing via BullMQ (`agent_run` job type)
- [ ] UI page for submitting runs and displaying progressive logs

**Learning focus:** Tool design patterns, safe tool invocation, agent orchestration

**Estimated Time:** 15-20 hours

---

### Phase 5: Multi-Stage Content Agents
**Goal:** Build orchestration agents as multi-node workflows

**Content Generation Agents:**
- [ ] **Insight Extraction Agent** - Extracts structured insights (key findings, claims, relevance) from documents using `summarize_chunk` and `get_abstract`
- [ ] **LinkedIn Post Generator Agent** - Composes short-form content from insights; supports tone variants and A/B headline candidates
- [ ] **Content Strategy Orchestrator** - Meta-agent composing query → insight → draft → publish decision; applies filters and schedules downstream jobs

**Supporting Agents:**
- [ ] **Topic Discovery Agent** - Scans ingested papers to propose topics, clusters, and research areas
- [ ] **Source Validator Agent** - Runs heuristics on sources (credibility, recency, domain); flags low-quality evidence

**Workflow Nodes:**
- [ ] Retrieval node (hybrid search, returns candidate chunks)
- [ ] Insight node (structured extraction and claim tagging)
- [ ] Headline node (A/B hook candidates)
- [ ] Draft node (thread/draft variants with citation placeholders)
- [ ] Citation node (verify and attach provenance metadata)
- [ ] HITL review node (optional editorial checkpoint)

**Infrastructure:**
- [ ] Node APIs and state checkpoint schema for resumable runs
- [ ] Human-in-the-loop hooks between insight extraction and drafting
- [ ] A/B testing support with metrics collection
- [ ] Provenance model with citation metadata and scoring
- [ ] Export/publish connector (demo LinkedIn simulation)
- [ ] Evaluation harness (citation presence, length, toxic-content filters)
- [ ] End-to-end demo script with full audit trail

**Agent Manifest Standard:**
Each agent includes:
- Manifest (name, version, required tools, resource limits)
- Zod input/output contract
- API producer pattern and BullMQ job type
- Worker handler with step-level logging

**Learning focus:** Composing RAG into content flows, resumable workflow state design

**Estimated Time:** 25-35 hours

---

### Phase 6: Security & Deployment
**Goal:** Harden for safe public demo

**What to build:**
- [ ] Secrets management (no hard-coded keys)
- [ ] Minimal auth (API key or simple OAuth)
- [ ] Docker Compose for local development
- [ ] Helm manifests for cloud deployment (optional)
- [ ] Schema migration runbook for pgvector
- [ ] Backup and restore procedures

**Learning focus:** Secure credentials, deployment hygiene, vector DB migrations

**Estimated Time:** 12-18 hours

---

### Phase 7: Advanced Features
**Goal:** Polish and differentiate

**What to build:**
- [ ] Cohere reranking integration
- [ ] Multi-draft generation with comparison
- [ ] User preferences and history tracking
- [ ] Cost tracking per generation
- [ ] Rate limiting and usage quotas

**Learning focus:** Advanced RAG techniques, agent coordination, user experience, analytics

**Estimated Time:** 15-20 hours

---

### Phase 8: Portfolio & Documentation
**Goal:** Make it showcase-ready

**What to build:**
- [ ] Clean public repo with README and architecture diagrams
- [ ] Quickstart guide for local setup
- [ ] Demo script: ingest paper → generate post → show provenance
- [ ] Blog post describing architecture patterns learned
- [ ] Video walkthrough (5-8 minutes, optional)
- [ ] Deploy demo instance
- [ ] LinkedIn posts about the project (using the tool itself!)

**Learning focus:** Technical writing, documentation best practices, DevOps, marketing your work

**Estimated Time:** 15-20 hours

---

## Technology Stack

### Chosen Stack (Same Tech, Original Code)
- **Frontend:** Next.js 15 (App Router, SSR)
- **Backend:** Fastify with Swagger/OpenAPI
- **Database:** PostgreSQL with pgvector
- **Queue:** Redis + BullMQ
- **AI:** LangChain, LangGraph
- **Embeddings:** Multi-provider (OpenAI, Voyage, Cohere)

Ubuntu is installed on a Win 11 machine. User has sudo permissions. Ubuntu has Redis,  postgresql v14 and postgresql v16 installed with pgvector. Project uses postgresql v16.
pg4Admin is also installed on win11 macine and remotely connected to Ubuntus' postgresql v16 server for any DB and table troubleshooting.


### Alternative Options for Future Learning
- Frontend: SvelteKit, Remix
- Backend: Express, Hono
- Queue: Inngest, Temporal
- Different LLM providers

---

## Key Differentiators (Proving Original Work)

| Aspect | Company Project | Personal Project |
|--------|----------------|-----------------|
| Naming | `councilId`, `applicationId` | `topicId`, `paperId` |
| Structure | `agents/topic-assessment-no-gemini/` | `agents/content-generator/` |
| Schema | Planning-specific tables | Research/content-specific tables |
| UI | Professional dashboard | Custom design |
| Prompts | Planning assessment | Content generation |
| Documentation | Internal | Public with build process |

---

## Success Metrics

### Technical
- [ ] Full working system deployed
- [ ] 95%+ test coverage
- [ ] Sub-second search response times
- [ ] Supports 100+ page papers
- [ ] Generates 3+ post variations

### Portfolio
- [ ] Public GitHub repo with stars
- [ ] Blog post with architecture diagrams
- [ ] Demo video or live site
- [ ] Used to create own LinkedIn content
- [ ] Added to resume as key project

### Learning
- [ ] Can explain every architectural decision
- [ ] Comfortable with all parts of the stack
- [ ] Can extend with new features independently
- [ ] Ready to discuss in interviews

---
