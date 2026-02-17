"""Content pipeline – LangGraph StateGraph orchestrator (Phase 5).

Orchestrates the multi-stage content generation workflow:
  1. retrieval (via search_papers tool / hybrid_retrieve)
  2. insight_extraction
  3. draft_generation
  4. citation_validation

The pipeline takes a query, runs hybrid_retrieve to get search results,
then passes them through the workflow nodes.

Console log format: [Agent:ContentPipeline][step:<step>] message
"""
import logging
import uuid
from typing import Any, Dict, TypedDict

from langgraph.graph import StateGraph, END

from ..tools.search_papers import search_papers
from .insight_extraction import extract_insights
from .draft_generation import generate_draft
from .citation_validation import validate_citations

logger = logging.getLogger(__name__)


def _log(step: str, message: str) -> None:
    logger.info("[Agent:ContentPipeline][step:%s] %s", step, message)


class PipelineState(TypedDict, total=False):
    """State passed through the content pipeline graph."""
    run_id: str
    query: str
    search_mode: str
    limit: int
    min_score: float
    search_results: list
    insights: list
    draft: str
    citations: list
    validation_errors: list
    current_step: str
    steps_log: list
    metadata: dict


def retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 1: Run hybrid retrieval via search_papers tool."""
    query = state.get("query", "")
    search_mode = state.get("search_mode", "hybrid")
    limit = state.get("limit", 10)
    min_score = state.get("min_score", 0.0)

    _log("retrieval_start", f"query={query!r} mode={search_mode} limit={limit}")

    result = search_papers(
        query=query,
        search_mode=search_mode,
        limit=limit,
        min_score=min_score,
    )

    if "error" in result and result["error"]:
        _log("retrieval_error", f"Error: {result['error']}")
        state["search_results"] = []
        state["validation_errors"] = state.get("validation_errors", []) + [
            f"Retrieval failed: {result['error']}"
        ]
    else:
        results = result.get("results", [])
        _log("retrieval_complete", f"Got {len(results)} results")
        state["search_results"] = results

    state["current_step"] = "retrieval"
    state["steps_log"] = state.get("steps_log", []) + [
        f"retrieval: {len(state.get('search_results', []))} results"
    ]
    return state


def should_continue(state: Dict[str, Any]) -> str:
    """Conditional edge: skip remaining nodes if no search results."""
    if not state.get("search_results"):
        _log("should_continue", "No search results — ending pipeline")
        return "end"
    return "insight_extraction"


def build_content_pipeline() -> StateGraph:
    """Build and return the LangGraph content pipeline.

    Returns a compiled StateGraph that can be invoked with:
        result = pipeline.invoke({"query": "...", ...})
    """
    _log("build", "Building content pipeline StateGraph")

    graph = StateGraph(PipelineState)

    graph.add_node("retrieval", retrieval_node)
    graph.add_node("insight_extraction", extract_insights)
    graph.add_node("draft_generation", generate_draft)
    graph.add_node("citation_validation", validate_citations)

    graph.set_entry_point("retrieval")

    graph.add_conditional_edges(
        "retrieval",
        should_continue,
        {
            "insight_extraction": "insight_extraction",
            "end": END,
        },
    )
    graph.add_edge("insight_extraction", "draft_generation")
    graph.add_edge("draft_generation", "citation_validation")
    graph.add_edge("citation_validation", END)

    _log("build", "Content pipeline built successfully")
    return graph.compile()


def run_content_pipeline(
    query: str,
    search_mode: str = "hybrid",
    limit: int = 10,
    min_score: float = 0.0,
    run_id: str = "",
) -> Dict[str, Any]:
    """Execute the full content pipeline and return the final state.

    This is the main entry point called by the worker when processing
    an agent_run job of type 'content_pipeline'.
    """
    run_id = run_id or str(uuid.uuid4())
    _log("run_start", f"run_id={run_id} query={query!r}")

    pipeline = build_content_pipeline()

    initial_state: PipelineState = {
        "run_id": run_id,
        "query": query,
        "search_mode": search_mode,
        "limit": limit,
        "min_score": min_score,
        "search_results": [],
        "insights": [],
        "draft": "",
        "citations": [],
        "validation_errors": [],
        "current_step": "init",
        "steps_log": [],
        "metadata": {},
    }

    final_state = pipeline.invoke(initial_state)
    _log("run_complete", f"run_id={run_id} steps={final_state.get('steps_log', [])}")

    return dict(final_state)
