"""search_papers tool – reuses Phase 3 hybrid_retrieve.

Submits a hybrid_retrieval job via the job store (same queue the worker
already listens on) and waits for the result.  This keeps the tool
decoupled from the HybridWorker class and exercises the same code path
the API uses (POST /search/submit equivalent).

Console log format: [Agent:Tool:search_papers][step:<step>] message
"""
import logging
import time
from typing import Any, Dict, Optional

from ...services.job_store import JobStore

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 1
MAX_POLL_SECONDS = 120


def _log(step: str, message: str) -> None:
    logger.info("[Agent:Tool:search_papers][step:%s] %s", step, message)


def search_papers(
    query: str,
    search_mode: str = "hybrid",
    limit: int = 10,
    min_score: float = 0.0,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Search ingested papers using Phase 3 hybrid_retrieve via the job queue.

    Returns a dict with job_id and results list on success,
    or job_id and error on failure.
    """
    _log("submit", f"query={query!r} mode={search_mode} limit={limit}")

    job_store = JobStore()
    job_data = {
        "query": query,
        "search_mode": search_mode,
        "limit": limit,
        "min_score": min_score,
        "vector_weight": vector_weight,
        "keyword_weight": keyword_weight,
        "document_id": document_id,
    }

    job_id = job_store.create_job("hybrid_retrieval", job_data)
    _log("submitted", f"job_id={job_id}")

    elapsed = 0.0
    while elapsed < MAX_POLL_SECONDS:
        job = job_store.get_job(job_id)
        if job is None:
            _log("poll", f"job_id={job_id} not found")
            return {"job_id": job_id, "error": "Job not found in store"}

        status = job["status"]
        if status == "success":
            result = job.get("result", {})
            results_count = result.get("resultsCount", 0)
            _log("complete", f"job_id={job_id} results={results_count}")
            return {
                "job_id": job_id,
                "results": result.get("results", []),
                "results_count": results_count,
                "query": query,
                "search_mode": search_mode,
            }
        elif status == "failed":
            error = job.get("error", "Unknown error")
            _log("failed", f"job_id={job_id} error={error}")
            return {"job_id": job_id, "error": error}

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    _log("timeout", f"job_id={job_id} exceeded {MAX_POLL_SECONDS}s")
    return {"job_id": job_id, "error": f"Timed out after {MAX_POLL_SECONDS}s"}
