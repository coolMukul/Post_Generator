"""summarize_chunk tool — LLM-based chunk summarization."""
import logging
from typing import Optional

from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)

_llm: Optional[LLMService] = None


def _get_llm() -> LLMService:
    """Lazy-initialise a shared LLMService instance."""
    global _llm
    if _llm is None:
        _llm = LLMService()
    return _llm


def summarize_chunk(
    content: str,
    document_title: str = "",
    context_summary: str = "",
) -> str:
    """Produce a concise summary of a document chunk.

    Uses the LLM to create a 2-3 sentence summary that captures the key
    information in the chunk, considering the broader document context.
    """
    logger.info(
        "[Tool:summarize_chunk] content_len=%d  doc=%r",
        len(content), document_title,
    )

    system_prompt = (
        "You are a research summarization assistant. "
        "Given a chunk of text from a research document, produce a concise 2-3 sentence summary "
        "that captures the key findings, claims, or information. "
        "Be precise and factual. Do not add information not present in the text."
    )

    context_parts = []
    if document_title:
        context_parts.append(f"Document: {document_title}")
    if context_summary:
        context_parts.append(f"Context: {context_summary}")
    context_prefix = "\n".join(context_parts)

    user_prompt = f"{context_prefix}\n\nChunk text:\n{content}" if context_prefix else content

    llm = _get_llm()
    summary = llm.chat(system_prompt, user_prompt, model="lite")
    logger.info("[Tool:summarize_chunk] summary_len=%d", len(summary))
    return summary
