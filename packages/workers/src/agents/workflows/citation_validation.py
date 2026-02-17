"""Citation validation workflow node (Phase 5).

Verifies that the draft references are backed by actual search results
and formats them into structured citations.

Console log format: [Agent:CitationValidation][step:<step>] message
"""
import logging
from typing import Any, Dict, List

from ..tools.cite_source import cite_sources_from_results

logger = logging.getLogger(__name__)


def _log(step: str, message: str) -> None:
    logger.info("[Agent:CitationValidation][step:%s] %s", step, message)


def validate_citations(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: validate and format citations from search results.

    Reads state["search_results"] and state["draft"],
    produces state["citations"] and state["validation_errors"].
    """
    search_results = state.get("search_results", [])
    draft = state.get("draft", "")

    _log("start", f"Validating citations: {len(search_results)} results, draft={len(draft)} chars")

    if not search_results:
        _log("no_results", "No search results — no citations to validate")
        state["citations"] = []
        state["validation_errors"] = ["No search results available for citation"]
        state["current_step"] = "citation_validation"
        state["steps_log"] = state.get("steps_log", []) + ["citation_validation: no results"]
        return state

    citations = cite_sources_from_results(search_results)
    validation_errors = _validate(citations, draft)

    _log("complete", f"citations={len(citations)} errors={len(validation_errors)}")

    state["citations"] = citations
    state["validation_errors"] = validation_errors
    state["current_step"] = "citation_validation"
    state["steps_log"] = state.get("steps_log", []) + [
        f"citation_validation: {len(citations)} citations, {len(validation_errors)} errors"
    ]
    return state


def _validate(citations: List[Dict[str, Any]], draft: str) -> List[str]:
    """Run validation checks on citations against the draft."""
    errors = []

    if not citations:
        errors.append("No citations generated from search results")
        return errors

    low_relevance = [c for c in citations if c.get("relevance_score", 0) < 0.1]
    if low_relevance:
        errors.append(
            f"{len(low_relevance)} citation(s) have very low relevance scores (<0.1)"
        )

    missing_title = [c for c in citations if c.get("document_title") == "Untitled"]
    if missing_title:
        errors.append(
            f"{len(missing_title)} citation(s) have missing document titles"
        )

    missing_snippet = [c for c in citations if not c.get("snippet")]
    if missing_snippet:
        errors.append(
            f"{len(missing_snippet)} citation(s) have empty content snippets"
        )

    if draft:
        cited_docs = {c["document_title"] for c in citations if c.get("document_title")}
        draft_lower = draft.lower()
        unreferenced = [
            title for title in cited_docs
            if title != "Untitled" and title.lower() not in draft_lower
        ]
        if unreferenced and len(unreferenced) == len(cited_docs):
            errors.append(
                "Draft does not explicitly reference any cited document titles — "
                "consider adding source attributions"
            )

    return errors
