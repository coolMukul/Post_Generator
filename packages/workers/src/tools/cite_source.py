"""cite_source tool — citation formatting and verification."""
import logging
from typing import Any, Dict, Optional

from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)

_llm: Optional[LLMService] = None


def _get_llm() -> LLMService:
    """Lazy-initialise a shared LLMService instance."""
    global _llm
    if _llm is None:
        _llm = LLMService()
    return _llm


def cite_source(
    claim: str,
    source_content: str,
    document_title: str = "",
    document_id: str = "",
    chunk_index: int = 0,
) -> Dict[str, Any]:
    """Verify a claim against source content and produce a formatted citation.

    Returns a dict with:
      - verified: bool — whether the source supports the claim
      - confidence: float — 0.0 to 1.0
      - formatted_citation: str — human-readable citation string
      - excerpt: str — the relevant excerpt from the source
    """
    logger.info(
        "[Tool:cite_source] claim=%r  doc=%r  chunk=%d",
        claim[:80], document_title, chunk_index,
    )

    system_prompt = (
        "You are a citation verification assistant. Given a claim and a source text, determine:\n"
        "1. Whether the source text supports the claim (verified: true/false)\n"
        "2. Your confidence level (0.0 to 1.0)\n"
        "3. The specific excerpt from the source that supports or contradicts the claim\n"
        "4. A formatted citation string\n\n"
        "Respond in JSON format:\n"
        '{"verified": true, "confidence": 0.85, "excerpt": "...", "formatted_citation": "..."}'
    )

    user_prompt = (
        f"Claim: {claim}\n\n"
        f"Source document: {document_title}\n"
        f"Source text (chunk {chunk_index}):\n{source_content}"
    )

    llm = _get_llm()
    result = llm.chat_json(system_prompt, user_prompt)

    citation = {
        "verified": bool(result.get("verified", False)),
        "confidence": float(result.get("confidence", 0.0)),
        "excerpt": str(result.get("excerpt", "")),
        "formatted_citation": str(result.get("formatted_citation", f"[{document_title}]")),
        "document_id": document_id,
        "chunk_index": chunk_index,
    }

    logger.info(
        "[Tool:cite_source] verified=%s  confidence=%.2f",
        citation["verified"], citation["confidence"],
    )
    return citation
