"""Hybrid retrieval worker.

Processes jobs from the Redis main_queue.  Each job runs the
hybrid_retrieve pipeline: embed query -> vector search -> keyword search
-> fuse results with Reciprocal Rank Fusion (RRF) -> return ranked list.

Guidelines followed:
  - All business logic lives here, not in the API layer.
  - Console logs trace every step (start, scores, completion).
  - On exception the job is marked FAILED with the error message.
"""
import logging
import signal
import sys
from typing import Dict, Any, List, Optional

from .config import get_database_url
from .models.schemas import SearchMode, SearchRequest, SearchResult, SearchResponse
from .repositories.vector_repository import VectorRepository
from .repositories.document_repository import DocumentRepository
from .services.embedding_service import EmbeddingService
from .services.job_store import JobStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

RRF_K = 60  # Reciprocal Rank Fusion constant


class HybridWorker:
    """Executes hybrid_retrieval jobs."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or get_database_url()
        self.vector_repo = VectorRepository(self.db_url)
        self.doc_repo = DocumentRepository(self.db_url)
        self.embedding_service = EmbeddingService()
        self.job_store = JobStore()

    def hybrid_retrieve(self, request: SearchRequest) -> SearchResponse:
        """Run full hybrid retrieval pipeline and return a SearchResponse."""
        logger.info(
            "hybrid_retrieve START  query=%r  mode=%s  limit=%d  min_score=%.2f",
            request.query,
            request.search_mode.value,
            request.limit,
            request.min_score,
        )

        vector_rows: List[Dict[str, Any]] = []
        keyword_rows: List[Dict[str, Any]] = []

        # --- Vector search ---
        if request.search_mode in (SearchMode.VECTOR, SearchMode.HYBRID):
            logger.info("Step 1/3: Generating query embedding via OpenAI")
            query_embedding = self.embedding_service.embed_query(request.query)

            logger.info("Step 2/3: Running vector similarity search")
            vector_rows = self.vector_repo.similarity_search(
                query_embedding=query_embedding,
                limit=request.limit * 2,  # over-fetch for fusion
                project_document_id=request.document_id,
            )
            logger.info("Vector search returned %d rows", len(vector_rows))

        # --- Keyword search ---
        if request.search_mode in (SearchMode.KEYWORD, SearchMode.HYBRID):
            logger.info("Step 2/3: Running keyword (full-text) search")
            keyword_rows = self.vector_repo.keyword_search(
                query_text=request.query,
                limit=request.limit * 2,
                project_document_id=request.document_id,
            )
            logger.info("Keyword search returned %d rows", len(keyword_rows))

        # --- Fuse ---
        if request.search_mode == SearchMode.HYBRID:
            logger.info(
                "Step 3/3: Fusing results with RRF (vector_weight=%.2f, keyword_weight=%.2f)",
                request.vector_weight,
                request.keyword_weight,
            )
            merged = self._rrf_fuse(
                vector_rows,
                keyword_rows,
                vector_weight=request.vector_weight,
                keyword_weight=request.keyword_weight,
            )
        elif request.search_mode == SearchMode.VECTOR:
            merged = self._tag_rows(vector_rows, "vector", score_key="similarity")
        else:
            merged = self._tag_rows(keyword_rows, "keyword", score_key="rank")

        # --- Filter and limit ---
        filtered = [r for r in merged if r.score >= request.min_score]
        filtered = filtered[: request.limit]

        for r in filtered:
            logger.info(
                "  result chunk=%d  score=%.4f  source=%s  doc=%s",
                r.chunkIndex,
                r.score,
                r.rankSource,
                r.documentTitle or "unknown",
            )

        response = SearchResponse(
            success=True,
            query=request.query,
            searchMode=request.search_mode.value,
            resultsCount=len(filtered),
            results=filtered,
        )
        logger.info("hybrid_retrieve END  results=%d", len(filtered))
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tag_rows(
        rows: List[Dict[str, Any]],
        source: str,
        score_key: str,
    ) -> List[SearchResult]:
        """Convert raw DB rows to SearchResult with a uniform score."""
        results: List[SearchResult] = []
        for row in rows:
            raw_score = float(row.get(score_key, 0))
            results.append(
                SearchResult(
                    id=str(row["id"]),
                    documentId=str(row.get("document_id", "")),
                    documentTitle=row.get("document_title"),
                    chunkIndex=row.get("chunk_index", 0),
                    content=row.get("content", ""),
                    contextSummary=row.get("context_summary"),
                    score=max(0.0, min(1.0, raw_score)),
                    rankSource=source,
                    metadata=row.get("metadata") or {},
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    @staticmethod
    def _rrf_fuse(
        vector_rows: List[Dict[str, Any]],
        keyword_rows: List[Dict[str, Any]],
        vector_weight: float,
        keyword_weight: float,
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion of vector and keyword result lists."""
        score_map: Dict[str, float] = {}
        row_map: Dict[str, Dict[str, Any]] = {}
        source_map: Dict[str, str] = {}

        for rank, row in enumerate(vector_rows, start=1):
            rid = str(row["id"])
            rrf_score = vector_weight / (RRF_K + rank)
            score_map[rid] = score_map.get(rid, 0.0) + rrf_score
            row_map[rid] = row
            source_map[rid] = "vector"

        for rank, row in enumerate(keyword_rows, start=1):
            rid = str(row["id"])
            rrf_score = keyword_weight / (RRF_K + rank)
            score_map[rid] = score_map.get(rid, 0.0) + rrf_score
            row_map[rid] = row
            if rid in source_map and source_map[rid] == "vector":
                source_map[rid] = "hybrid"
            else:
                source_map[rid] = "keyword"

        if not score_map:
            return []

        max_score = max(score_map.values())
        results: List[SearchResult] = []
        for rid, rrf_score in score_map.items():
            row = row_map[rid]
            normalised = rrf_score / max_score if max_score > 0 else 0.0
            results.append(
                SearchResult(
                    id=rid,
                    documentId=str(row.get("document_id", "")),
                    documentTitle=row.get("document_title"),
                    chunkIndex=row.get("chunk_index", 0),
                    content=row.get("content", ""),
                    contextSummary=row.get("context_summary"),
                    score=round(normalised, 6),
                    rankSource=source_map[rid],
                    metadata=row.get("metadata") or {},
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results


# ------------------------------------------------------------------
# Worker loop – listens on Redis main_queue
# ------------------------------------------------------------------

_RUNNING = True


def _shutdown(signum, frame):
    global _RUNNING
    logger.info("Received signal %s, shutting down gracefully", signum)
    _RUNNING = False


def run_worker_loop():
    """Blocking loop: dequeue jobs and process them."""
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    worker = HybridWorker()
    logger.info("Worker loop started – listening on main_queue")

    while _RUNNING:
        job_id = worker.job_store.dequeue(timeout=5)
        if job_id is None:
            continue

        job = worker.job_store.get_job(job_id)
        if job is None:
            logger.warning("Job %s not found in store, skipping", job_id)
            continue

        job_type = job["job_type"]
        logger.info("Job START  id=%s  type=%s", job_id, job_type)

        try:
            if job_type == "hybrid_retrieval":
                request = SearchRequest(**job["data"])
                response = worker.hybrid_retrieve(request)
                worker.job_store.mark_success(job_id, response.model_dump())
            else:
                worker.job_store.mark_failed(job_id, f"Unknown job type: {job_type}")

        except Exception as exc:
            logger.exception("Job FAILED  id=%s  error=%s", job_id, exc)
            worker.job_store.mark_failed(job_id, str(exc))

    logger.info("Worker loop stopped")


if __name__ == "__main__":
    run_worker_loop()
