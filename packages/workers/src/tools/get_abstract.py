"""get_abstract tool — fetches document metadata and abstract from the repository."""
import logging
from typing import Any, Dict, Optional

from ..config import get_database_url
from ..repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

_repo: Optional[DocumentRepository] = None


def _get_repo() -> DocumentRepository:
    """Lazy-initialise a shared DocumentRepository instance."""
    global _repo
    if _repo is None:
        _repo = DocumentRepository(get_database_url())
    return _repo


def get_abstract(document_id: str) -> Dict[str, Any]:
    """Fetch a document's title, URL, and metadata (including abstract if available).

    Returns a dict with keys: id, title, source_url, metadata, abstract.
    """
    logger.info("[Tool:get_abstract] document_id=%s", document_id)

    repo = _get_repo()
    doc = repo.get_document(document_id)
    if doc is None:
        logger.warning("[Tool:get_abstract] document not found: %s", document_id)
        return {"id": document_id, "title": "Unknown", "source_url": "", "metadata": {}, "abstract": ""}

    metadata = doc.get("metadata") or {}
    abstract = metadata.get("abstract", "")

    result = {
        "id": str(doc["id"]),
        "title": doc.get("title", "Untitled"),
        "source_url": doc.get("source_url", ""),
        "metadata": metadata,
        "abstract": abstract,
    }
    logger.info("[Tool:get_abstract] found: title=%r  abstract_len=%d", result["title"], len(abstract))
    return result
