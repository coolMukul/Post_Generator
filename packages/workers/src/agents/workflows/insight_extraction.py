"""Insight extraction workflow node (Phase 5).

Takes search results from the WorkflowState and extracts key insights
using the configured LLM.  If no LLM is available, performs rule-based
extraction from high-scoring chunks.

Console log format: [Agent:InsightExtraction][step:<step>] message
"""
import logging
from typing import Any, Dict, List

from ...config import settings
from ...models.agent_schemas import WorkflowState

logger = logging.getLogger(__name__)


def _log(step: str, message: str) -> None:
    logger.info("[Agent:InsightExtraction][step:%s] %s", step, message)


def extract_insights(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: extract insights from search_results in state.

    Reads state["search_results"], produces state["insights"].
    """
    _log("start", f"Processing {len(state.get('search_results', []))} search results")

    search_results = state.get("search_results", [])
    if not search_results:
        _log("no_results", "No search results to extract insights from")
        state["insights"] = []
        state["current_step"] = "insight_extraction"
        state["steps_log"] = state.get("steps_log", []) + ["insight_extraction: no results"]
        return state

    if settings.openai_api_key:
        insights = _extract_with_openai(search_results)
    elif settings.gemini_api_key:
        insights = _extract_with_gemini(search_results)
    else:
        _log("rule_based", "No LLM key — using rule-based extraction")
        insights = _extract_rule_based(search_results)

    _log("complete", f"Extracted {len(insights)} insights")
    state["insights"] = insights
    state["current_step"] = "insight_extraction"
    state["steps_log"] = state.get("steps_log", []) + [
        f"insight_extraction: extracted {len(insights)} insights"
    ]
    return state


def _extract_rule_based(results: List[Dict[str, Any]]) -> List[str]:
    """Rule-based insight extraction from high-scoring results."""
    insights = []
    for r in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        score = r.get("score", 0)
        if score < 0.2:
            continue
        content = r.get("content", "")
        title = r.get("documentTitle", r.get("document_title", "Unknown"))
        snippet = content[:300].strip()
        if snippet:
            insights.append(f"From '{title}' (score {score:.2f}): {snippet}")
    return insights[:10]


def _build_extraction_prompt(results: List[Dict[str, Any]]) -> str:
    """Build the LLM prompt from search results."""
    chunks = []
    for i, r in enumerate(results[:10], start=1):
        title = r.get("documentTitle", r.get("document_title", "Unknown"))
        content = r.get("content", "")[:500]
        score = r.get("score", 0)
        chunks.append(f"[{i}] Title: {title} | Score: {score:.2f}\n{content}")

    joined = "\n\n".join(chunks)
    return (
        "Extract the key insights from the following document excerpts. "
        "Return each insight as a separate bullet point. "
        "Focus on unique, actionable, and noteworthy information.\n\n"
        f"{joined}"
    )


def _extract_with_openai(results: List[Dict[str, Any]]) -> List[str]:
    """Extract insights using OpenAI."""
    _log("openai_start", "Calling OpenAI for insight extraction")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _build_extraction_prompt(results)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert research analyst."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()
    insights = [line.lstrip("•-* ").strip() for line in raw.split("\n") if line.strip()]
    _log("openai_complete", f"Got {len(insights)} insights")
    return insights


def _extract_with_gemini(results: List[Dict[str, Any]]) -> List[str]:
    """Extract insights using Google Gemini."""
    _log("gemini_start", "Calling Gemini for insight extraction")
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = _build_extraction_prompt(results)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"You are an expert research analyst.\n\n{prompt}",
    )
    raw = response.text.strip()
    insights = [line.lstrip("•-* ").strip() for line in raw.split("\n") if line.strip()]
    _log("gemini_complete", f"Got {len(insights)} insights")
    return insights
