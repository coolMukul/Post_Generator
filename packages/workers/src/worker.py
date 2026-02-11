"""Hybrid search worker skeleton.

This worker is intentionally minimal: it exposes a small HybridWorker
to perform similarity search operations using the existing
repositories (vector and document). PDF processing and BullMQ polling
were removed per Phase 3 scope.
"""
import logging
from typing import List, Dict, Any, Optional
from .repositories.vector_repository import VectorRepository
from .repositories.document_repository import DocumentRepository
from .config import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridWorker:
    """Worker that exposes hybrid search utilities used by the API."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or get_database_url()
        self.vector_repo = VectorRepository(self.db_url)
        self.doc_repo = DocumentRepository(self.db_url)

    def similarity_search(self, query_embedding: List[float], limit: int = 10, document_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Run similarity search using the vector repository."""
        logger.info(f"Running similarity search (limit={limit}, document_id={document_id})")
        results = self.vector_repo.similarity_search(query_embedding, limit=limit, document_id=document_id)
        return results


def main():
    # Minimal smoke test
    worker = HybridWorker()
    logger.info('HybridWorker ready — implement integration tests or API calls to use it.')


if __name__ == '__main__':
    main()
