"""cite_source tool – formats citation metadata for a document/chunk.

Produces a structured citation object from the search result metadata.
Used by the citation_validation workflow node and by agents that need
to attach references to generated content.

Console log format: [Agent:Tool:cite_source][step:<step>] message
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _log(step: str, message: str) -> None:
    logger.info("[Agent:Tool:cite_source][step:%s] %s", step, message)


def cite_source(
    document_id: str,
    document_title: Optional[str] = None,
    chunk_index: int = 0,
    content_snippet: str = "",
    score: float = 0.0,
    rank_source: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format a structured citation from search result metadata.

    Args:
        document_id: UUID of the source document.
        document_title: Title of the source document.
        chunk_index: Index of the cited chunk.
        content_snippet: Short excerpt from the cited content.
        score: Relevance score from the search.
        rank_source: How the result was ranked (vector/keyword/hybrid).
        metadata: Additional metadata from the document.

    Returns:
        Dict with citation fields.
    """
    _log("start", f"document_id={document_id} chunk={chunk_index} score={score:.4f}")

    meta = metadata or {}
    url = meta.get("url", "")
    author = meta.get("author", "")
    published_date = meta.get("published_date", "")

    snippet_preview = content_snippet[:150].rstrip()
    if len(content_snippet) > 150:
        snippet_preview += "..."

    citation = {
        "document_id": document_id,
        "document_title": document_title or "Untitled",
        "chunk_index": chunk_index,
        "snippet": snippet_preview,
        "relevance_score": round(score, 4),
        "rank_source": rank_source,
        "url": url,
        "author": author,
        "published_date": published_date,
    }

    _log("complete", f"citation for '{citation['document_title']}' chunk {chunk_index}")
    return citation


def cite_sources_from_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build citation list from a list of search results.

    Convenience wrapper that calls cite_source for each result dict.
    """
    _log("batch_start", f"Citing {len(results)} results")
    citations = []
    for result in results:
        citation = cite_source(
            document_id=result.get("documentId", result.get("document_id", "")),
            document_title=result.get("documentTitle", result.get("document_title")),
            chunk_index=result.get("chunkIndex", result.get("chunk_index", 0)),
            content_snippet=result.get("content", ""),
            score=result.get("score", 0.0),
            rank_source=result.get("rankSource", result.get("rank_source", "unknown")),
            metadata=result.get("metadata", {}),
        )
        citations.append(citation)

    _log("batch_complete", f"Generated {len(citations)} citations")
    return citations
