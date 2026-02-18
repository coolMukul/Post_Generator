"""Draft generation workflow node (Phase 5).

Takes insights from the WorkflowState and generates a structured
content draft (e.g. LinkedIn post, article section).

Console log format: [Agent:DraftGeneration][step:<step>] message
"""
import logging
from typing import Any, Dict, List

from ...config import settings
from ...models.agent_schemas import WorkflowState

logger = logging.getLogger(__name__)


def _log(step: str, message: str) -> None:
    logger.info("[Agent:DraftGeneration][step:%s] %s", step, message)


def generate_draft(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: generate a content draft from insights.

    Reads state["insights"], produces state["draft"].
    """
    insights = state.get("insights", [])
    query = state.get("query", "")

    _log("start", f"Generating draft from {len(insights)} insights for query={query!r}")

    if not insights:
        _log("no_insights", "No insights available — skipping draft generation")
        state["draft"] = ""
        state["current_step"] = "draft_generation"
        state["steps_log"] = state.get("steps_log", []) + ["draft_generation: no insights"]
        return state

    use_gemini = (
        settings.gemini_api_key
        and (settings.embedding_provider == "gemini" or not settings.openai_api_key)
    )
    use_openai = settings.openai_api_key and not use_gemini

    if use_openai:
        draft = _generate_with_openai(query, insights)
    elif use_gemini:
        draft = _generate_with_gemini(query, insights)
    else:
        _log("template", "No LLM key — using template-based draft")
        draft = _generate_template(query, insights)

    _log("complete", f"Draft generated: {len(draft)} chars")
    state["draft"] = draft
    state["current_step"] = "draft_generation"
    state["steps_log"] = state.get("steps_log", []) + [
        f"draft_generation: {len(draft)} chars"
    ]
    return state


def _generate_template(query: str, insights: List[str]) -> str:
    """Template-based draft when no LLM is available."""
    lines = [f"# Research Insights: {query}", ""]
    for i, insight in enumerate(insights, start=1):
        lines.append(f"{i}. {insight}")
    lines.append("")
    lines.append("---")
    lines.append(f"Based on analysis of {len(insights)} key findings from ingested documents.")
    return "\n".join(lines)


def _build_draft_prompt(query: str, insights: List[str]) -> str:
    """Build the LLM prompt for draft generation."""
    insight_block = "\n".join(f"- {ins}" for ins in insights)
    return (
        f"You are a professional content writer. Based on the following research insights "
        f"about '{query}', write a well-structured, engaging LinkedIn post.\n\n"
        f"Key Insights:\n{insight_block}\n\n"
        "Requirements:\n"
        "- Start with an attention-grabbing hook\n"
        "- Include 3-5 key points backed by the insights\n"
        "- End with a call-to-action or thought-provoking question\n"
        "- Keep it under 1300 characters (LinkedIn limit)\n"
        "- Use a professional but approachable tone\n"
        "- Include relevant hashtags at the end"
    )


def _generate_with_openai(query: str, insights: List[str]) -> str:
    """Generate draft using OpenAI."""
    _log("openai_start", "Calling OpenAI for draft generation")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _build_draft_prompt(query, insights)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert content writer specializing in LinkedIn posts."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
        temperature=0.7,
    )
    draft = response.choices[0].message.content.strip()
    _log("openai_complete", f"draft_length={len(draft)}")
    return draft


def _generate_with_gemini(query: str, insights: List[str]) -> str:
    """Generate draft using Google Gemini."""
    _log("gemini_start", "Calling Gemini for draft generation")
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = _build_draft_prompt(query, insights)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"You are an expert content writer specializing in LinkedIn posts.\n\n{prompt}",
    )
    draft = response.text.strip()
    _log("gemini_complete", f"draft_length={len(draft)}")
    return draft
