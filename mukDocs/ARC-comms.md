# ARC Team Communications Log

**Team:** ARC (Agent Runtime Collective)
**Project:** Research Insight — AI-Powered LinkedIn Content Generation
**Phases:** 4 (Agent Framework & Core Tools) + 5 (Multi-Stage Content Agents)
**Branch:** `claude/setup-arc-team-structure-n57IQ`

---

## [THREAD-001] 2026-02-18 | Claude (Tech Lead) → All | Session Start — Phase 4+5 Kickoff

**Status:** Phases 1-3 complete and tested. Beginning Phase 4+5 implementation.

**Codebase audit findings:**
- Phase 3 hybrid retrieval is production-ready: `HybridWorker.hybrid_retrieve()` with RRF fusion, multi-provider embeddings (Gemini/OpenAI)
- Redis job store (`JobStore`) handles full lifecycle: create → dequeue → success/fail
- Worker loop processes `hybrid_retrieval` jobs from `main_queue` via BLPOP
- API is thin FastAPI layer — no business logic, only job submission + polling
- UI pages for Research Query Agent, Insight Extraction Agent, and LinkedIn Post Agent already exist with defined API contracts

**API contracts locked by existing UI:**
- `POST /agent/research-query` → `{ query, maxResults, minScore, includeContext }` → returns `{ success, jobId }`
- `POST /agent/insight-extraction` → `{ query, maxResults, minScore }` → returns `{ success, jobId }`
- `POST /agent/linkedin-post` → `{ title, insights, tone, maxLength }` → returns `{ success, jobId }`
- All agents poll via existing `GET /queue/jobs/{job_id}`

**Architecture decisions:**
- TOOL wraps Phase 3 `HybridWorker` — does not rebuild retrieval
- LangGraph StateGraph for all agent workflows
- Multi-provider LLM service (Gemini default, OpenAI fallback) — mirrors embedding service pattern
- All agents run in worker process, dispatched by job type from `main_queue`
- No mocks, no fallbacks, no TODOs in code per CodingGuidelines.md

---

## [THREAD-002] 2026-02-18 | Claude → TOOL | Task Assignment — Core Tools

**Assigned:**
1. `search_papers` tool — wraps `HybridWorker.hybrid_retrieve()` for agent use
2. `get_abstract` tool — fetches document metadata/abstracts from `DocumentRepository`
3. `summarize_chunk` tool — LLM-based chunk summarization
4. `cite_source` tool — citation formatting and verification

**Constraint:** TOOL wraps existing Phase 3 code. No rebuilding retrieval logic.

---

## [THREAD-003] 2026-02-18 | Claude → CRAFT | Task Assignment — Content Agents

**Assigned:**
1. Research Query Agent — hybrid retrieval orchestrator (LangGraph StateGraph)
2. Citation Validator Agent — verifies claim provenance, formats citations
3. Insight Extraction Agent — structured insight extraction from corpus
4. LinkedIn Post Generator Agent — composes short-form content from insights
5. Content Strategy Orchestrator — meta-agent: query → insight → draft → review

**Pattern:** Each agent uses LangGraph StateGraph with step-level logging `[Agent:<name>][step:<tool>]`

---

## [THREAD-004] 2026-02-18 | Claude → FLOW | Task Assignment — Agent Framework

**Assigned:**
1. Agent base class with timing, step logging, error handling
2. Agent registry with manifest format (name, version, tools, resource limits)
3. LangGraph integration patterns
4. State checkpoint schema for resumable runs (single-session)

---

## [THREAD-005] 2026-02-18 | Claude → WIRE | Task Assignment — API & Worker Integration

**Assigned:**
1. Three new API endpoints: `/agent/research-query`, `/agent/insight-extraction`, `/agent/linkedin-post`
2. Worker loop extension for job types: `research_query_agent`, `insight_extraction_agent`, `linkedin_post_agent`
3. LLM provider config additions to `config.py`

---
