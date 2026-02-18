"""search_papers tool — wraps Phase 3 HybridWorker.hybrid_retrieve().

TOOL does NOT rebuild retrieval. It delegates entirely to the existing
HybridWorker pipeline (embed → vector search → keyword search → RRF fuse).
"""
import logging
from typing import Any, Dict, List, Optional

from ..models.schemas import SearchMode, SearchRequest
from ..worker import HybridWorker

logger = logging.getLogger(__name__)

_worker: Optional[HybridWorker] = None


def _get_worker() -> HybridWorker:
    """Lazy-initialise a shared HybridWorker instance."""
    global _worker
    if _worker is None:
        _worker = HybridWorker()
    return _worker


def search_papers(
    query: str,
    limit: int = 10,
    min_score: float = 0.0,
    search_mode: str = "hybrid",
    document_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Run hybrid retrieval and return results as list of dicts.

    This is the primary retrieval tool used by agents. It wraps the existing
    Phase 3 pipeline without modification.
    """
    logger.info(
        "[Tool:search_papers] query=%r  limit=%d  min_score=%.2f  mode=%s",
        query, limit, min_score, search_mode,
    )

    mode = SearchMode(search_mode)
    request = SearchRequest(
        query=query,
        search_mode=mode,
        limit=limit,
        min_score=min_score,
        document_id=document_id,
    )

    worker = _get_worker()
    response = worker.hybrid_retrieve(request)

    results = [r.model_dump() for r in response.results]
    logger.info("[Tool:search_papers] returned %d results", len(results))
    return results
