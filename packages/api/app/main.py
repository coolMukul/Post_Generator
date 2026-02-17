"""FastAPI application – thin API layer.

Responsibilities:
  - Accept requests from the UI.
  - Submit jobs to the Redis main_queue via JobStore.
  - Serve job status / results back to the UI via polling.
  - No business logic – all heavy lifting happens in the worker.

Endpoints (Phase 3):
  POST /search/submit         – hybrid_retrieval job
  GET  /queue/jobs/{job_id}   – poll any job status
  GET  /health                – DB + Redis health check
  GET  /documents/count       – total document count

Endpoints (Phase 4+5):
  POST /agent/run             – submit an agent_run job
  GET  /agent/runs/{run_id}   – poll agent run status (alias for /queue/jobs)
  GET  /agent/list            – list registered agents
  POST /content/pipeline      – submit a content_pipeline job (Phase 5)
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Make the workers package importable so we can reuse JobStore / repos / config.
# We add "packages/workers" (not "packages/workers/src") so that relative
# imports inside the `src` package continue to work.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
WORKERS_PKG = ROOT / "packages" / "workers"
sys.path.insert(0, str(WORKERS_PKG))

from src.services.job_store import JobStore  # noqa: E402
from src.repositories.document_repository import DocumentRepository  # noqa: E402
from src.config import get_database_url, get_redis_url  # noqa: E402
from src.agents.registry import AgentRegistry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & middleware
# ---------------------------------------------------------------------------
app = FastAPI(title="Post Generator API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances (created once at startup)
_job_store: Optional[JobStore] = None
_doc_repo: Optional[DocumentRepository] = None
_agent_registry: Optional[AgentRegistry] = None


@app.on_event("startup")
async def _startup():
    global _job_store, _doc_repo, _agent_registry
    _job_store = JobStore()
    _doc_repo = DocumentRepository(get_database_url())

    _agent_registry = AgentRegistry()
    _agent_registry.load_manifests()
    logger.info("Agent registry loaded: %d manifests", _agent_registry.manifest_count())

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "3201"))
    display_host = "localhost" if host == "0.0.0.0" else host
    logger.info("Swagger UI : http://%s:%d/docs", display_host, port)
    logger.info("ReDoc       : http://%s:%d/redoc", display_host, port)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class SearchSubmitRequest(BaseModel):
    query: str = Field(..., min_length=1)
    searchMode: str = Field(default="hybrid")
    limit: int = Field(default=10, ge=1, le=100)
    minScore: float = Field(default=0.0, ge=0.0, le=1.0)
    vectorWeight: float = Field(default=0.7, ge=0.0, le=1.0)
    keywordWeight: float = Field(default=0.3, ge=0.0, le=1.0)
    documentId: Optional[str] = None


class AgentRunSubmitRequest(BaseModel):
    agentName: str = Field(..., min_length=1)
    input: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)


class ContentPipelineSubmitRequest(BaseModel):
    query: str = Field(..., min_length=1)
    searchMode: str = Field(default="hybrid")
    limit: int = Field(default=10, ge=1, le=100)
    minScore: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Phase 3 Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check – verifies DB and Redis connectivity."""
    db_ok = False
    redis_ok = False

    try:
        import psycopg
        with psycopg.connect(get_database_url()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_ok = True
    except Exception as exc:
        logger.warning("Health check DB failed: %s", exc)

    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(get_redis_url())
        r.ping()
        redis_ok = True
    except Exception as exc:
        logger.warning("Health check Redis failed: %s", exc)

    status = "healthy" if (db_ok and redis_ok) else "unhealthy"
    return {
        "status": status,
        "services": {"database": db_ok, "redis": redis_ok},
    }


@app.get("/documents/count")
async def documents_count():
    """Return total document count."""
    count = _doc_repo.count_documents()
    return {"count": count}


@app.post("/search/submit")
async def search_submit(req: SearchSubmitRequest):
    """Submit a hybrid_retrieval job to the worker queue."""
    job_data = {
        "query": req.query,
        "search_mode": req.searchMode,
        "limit": req.limit,
        "min_score": req.minScore,
        "vector_weight": req.vectorWeight,
        "keyword_weight": req.keywordWeight,
        "document_id": req.documentId,
    }
    job_id = _job_store.create_job("hybrid_retrieval", job_data)
    logger.info("Search job submitted: id=%s  query=%r", job_id, req.query)
    return {"jobId": job_id}


@app.get("/queue/jobs/{job_id}")
async def job_status(job_id: str):
    """Poll for the status of a background job."""
    job = _job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job["status"]
    response = {
        "jobId": job["job_id"],
        "state": "completed" if status == "success" else ("failed" if status == "failed" else "active"),
        "status": status,
        "startTime": job.get("start_time"),
        "endTime": job.get("end_time"),
    }

    if status == "success":
        response["returnvalue"] = job.get("result")
    elif status == "failed":
        response["failedReason"] = job.get("error")

    return response


# ---------------------------------------------------------------------------
# Phase 4 Endpoints – Agent Framework
# ---------------------------------------------------------------------------
@app.post("/agent/run")
async def agent_run(req: AgentRunSubmitRequest):
    """Submit an agent_run job to the worker queue.

    The worker will instantiate the named agent via the AgentRegistry,
    execute it, and store the result. Poll via GET /queue/jobs/{jobId}.
    """
    if _agent_registry and not _agent_registry.get_manifest(req.agentName):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {req.agentName}. Use GET /agent/list to see available agents.",
        )

    job_data = {
        "agent_name": req.agentName,
        "input": req.input,
        "config": req.config,
    }
    job_id = _job_store.create_job("agent_run", job_data)
    logger.info("Agent run submitted: id=%s  agent=%s", job_id, req.agentName)
    return {"jobId": job_id, "agentName": req.agentName}


@app.get("/agent/runs/{run_id}")
async def agent_run_status(run_id: str):
    """Poll agent run status (delegates to /queue/jobs)."""
    return await job_status(run_id)


@app.get("/agent/list")
async def agent_list():
    """List all registered agents with metadata."""
    if _agent_registry is None:
        return {"agents": []}
    agents = _agent_registry.list_agents()
    return {"agents": agents}


# ---------------------------------------------------------------------------
# Phase 5 Endpoints – Content Pipeline
# ---------------------------------------------------------------------------
@app.post("/content/pipeline")
async def content_pipeline(req: ContentPipelineSubmitRequest):
    """Submit a content_pipeline job (Phase 5 multi-stage workflow).

    The worker will run: retrieval → insight extraction → draft generation
    → citation validation. Poll via GET /queue/jobs/{jobId}.
    """
    job_data = {
        "query": req.query,
        "search_mode": req.searchMode,
        "limit": req.limit,
        "min_score": req.minScore,
    }
    job_id = _job_store.create_job("content_pipeline", job_data)
    logger.info("Content pipeline submitted: id=%s  query=%r", job_id, req.query)
    return {"jobId": job_id}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "3201")),
        reload=True,
    )
