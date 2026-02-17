"""summarize_chunk tool – summarizes a document chunk using the configured LLM.

Uses the LLM (OpenAI or Gemini, depending on env config) to produce a
concise summary of the provided text chunk.

Console log format: [Agent:Tool:summarize_chunk][step:<step>] message
"""
import logging
from typing import Any, Dict, Optional

from ...config import settings

logger = logging.getLogger(__name__)

MAX_SUMMARY_CHARS = 500


def _log(step: str, message: str) -> None:
    logger.info("[Agent:Tool:summarize_chunk][step:%s] %s", step, message)


def summarize_chunk(
    content: str,
    context_summary: Optional[str] = None,
    max_length: int = MAX_SUMMARY_CHARS,
) -> Dict[str, Any]:
    """Summarize a document chunk.

    If a pre-computed context_summary exists (from ingestion), it is
    returned directly.  Otherwise uses the configured LLM provider.

    Args:
        content: The chunk text to summarize.
        context_summary: Optional existing context summary (from ingestion).
        max_length: Target max characters for the summary.

    Returns:
        Dict with 'summary' and 'method' keys.
    """
    _log("start", f"content_length={len(content)} max_length={max_length}")

    if context_summary:
        _log("use_existing", "Using pre-computed context_summary from ingestion")
        return {
            "summary": context_summary[:max_length],
            "method": "context_summary",
            "original_length": len(content),
        }

    if settings.openai_api_key:
        return _summarize_openai(content, max_length)

    if settings.gemini_api_key:
        return _summarize_gemini(content, max_length)

    _log("no_llm_key", "No LLM API key configured — required for summarization")
    raise RuntimeError(
        "No LLM API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY to enable summarization."
    )


def _summarize_openai(content: str, max_length: int) -> Dict[str, Any]:
    """Summarize using OpenAI chat completion."""
    _log("openai_start", "Calling OpenAI for summarization")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Summarize the following text in {max_length} characters or fewer. "
                "Be concise and capture the key points.",
            },
            {"role": "user", "content": content},
        ],
        max_tokens=200,
        temperature=0.3,
    )
    summary = response.choices[0].message.content.strip()
    _log("openai_complete", f"summary_length={len(summary)}")
    return {
        "summary": summary[:max_length],
        "method": "openai",
        "original_length": len(content),
    }


def _summarize_gemini(content: str, max_length: int) -> Dict[str, Any]:
    """Summarize using Google Gemini."""
    _log("gemini_start", "Calling Gemini for summarization")
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Summarize the following text in {max_length} characters or fewer. "
        f"Be concise and capture the key points.\n\n{content}",
    )
    summary = response.text.strip()
    _log("gemini_complete", f"summary_length={len(summary)}")
    return {
        "summary": summary[:max_length],
        "method": "gemini",
        "original_length": len(content),
    }
