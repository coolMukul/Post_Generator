"""Research Query Agent — hybrid retrieval orchestrator.

LangGraph StateGraph workflow:
  search → rank → explain → format

Wraps Phase 3 hybrid retrieval via the search_papers tool, then uses the
LLM to generate relevance explanations for each result.

Manifest:
  name: research_query_agent
  version: 1.0.0
  job_type: research_query_agent
  tools: [search_papers, get_abstract]
"""
import logging
import operator
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict, Annotated

from langgraph.graph import StateGraph, START, END

from .base import AgentBase
from .registry import register_agent
from ..models.agent_schemas import (
    AgentManifest,
    AgentResourceLimits,
    ResearchQueryRequest,
    ResearchQueryResponse,
    ResearchQueryResultItem,
)
from ..tools.search_papers import search_papers
from ..tools.get_abstract import get_abstract
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------
class ResearchQueryState(TypedDict):
    query: str
    max_results: int
    min_score: float
    include_context: bool
    raw_results: List[Dict[str, Any]]
    ranked_results: List[Dict[str, Any]]
    steps: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@register_agent
class ResearchQueryAgent(AgentBase):
    """AI-powered research query agent using hybrid RAG."""

    manifest = AgentManifest(
        name="research_query_agent",
        version="1.0.0",
        description="Hybrid retrieval orchestrator: accepts user queries, calls search_papers, ranks and merges results, returns candidates with scores.",
        required_tools=["search_papers", "get_abstract"],
        job_type="research_query_agent",
        resource_limits=AgentResourceLimits(max_time_seconds=120, max_llm_calls=15),
    )

    def __init__(self):
        super().__init__()
        self._llm: Optional[LLMService] = None
        self._graph = self._build_graph()

    def _get_llm(self) -> LLMService:
        if self._llm is None:
            self._llm = LLMService()
        return self._llm

    # ------------------------------------------------------------------
    # LangGraph nodes
    # ------------------------------------------------------------------

    def _search_node(self, state: ResearchQueryState) -> dict:
        """Node: run hybrid retrieval via search_papers tool."""
        self.log_step("search", f"Searching for: {state['query']}")
        self.check_time_limit()

        results = search_papers(
            query=state["query"],
            limit=state["max_results"],
            min_score=state["min_score"],
            search_mode="hybrid",
        )
        return {
            "raw_results": results,
            "steps": [f"Hybrid search returned {len(results)} results"],
        }

    def _rank_node(self, state: ResearchQueryState) -> dict:
        """Node: re-rank results by score (already sorted by RRF, but filter applies here)."""
        self.log_step("rank", f"Ranking {len(state['raw_results'])} results")
        self.check_time_limit()

        ranked = sorted(state["raw_results"], key=lambda r: r.get("score", 0), reverse=True)
        ranked = ranked[:state["max_results"]]
        return {
            "ranked_results": ranked,
            "steps": [f"Ranked and limited to top {len(ranked)} results"],
        }

    def _explain_node(self, state: ResearchQueryState) -> dict:
        """Node: use LLM to generate relevance explanations for top results."""
        self.log_step("explain", "Generating relevance explanations")
        self.check_time_limit()

        results = state["ranked_results"]
        if not results:
            return {"ranked_results": results, "steps": ["No results to explain"]}

        top_results = results[:5]
        chunks_text = ""
        for i, r in enumerate(top_results):
            chunks_text += f"\n--- Result {i+1} (score={r.get('score', 0):.4f}) ---\n"
            chunks_text += r.get("content", "")[:300]
            chunks_text += "\n"

        system_prompt = (
            "You are a research relevance assessor. For each search result, provide a brief "
            "(1 sentence) explanation of why it is relevant to the user's query. "
            "Respond in JSON format as a list of strings, one per result. "
            "Example: [\"Discusses transformer architecture directly.\", \"Mentions attention mechanisms.\"]"
        )
        user_prompt = f"Query: {state['query']}\n\nResults:{chunks_text}"

        llm = self._get_llm()
        self.track_llm_call()
        reasons = llm.chat_json(system_prompt, user_prompt, model="lite")

        if isinstance(reasons, dict):
            reasons = list(reasons.values())
        if not isinstance(reasons, list):
            reasons = []

        for i, r in enumerate(results):
            if i < len(reasons):
                r["relevanceReason"] = str(reasons[i])

        return {
            "ranked_results": results,
            "steps": [f"Generated relevance explanations for {min(len(top_results), len(reasons))} results"],
        }

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(ResearchQueryState)
        builder.add_node("search", self._search_node)
        builder.add_node("rank", self._rank_node)
        builder.add_node("explain", self._explain_node)
        builder.add_edge(START, "search")
        builder.add_edge("search", "rank")
        builder.add_edge("rank", "explain")
        builder.add_edge("explain", END)
        return builder.compile()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = ResearchQueryRequest(**request)
        self.log_step("validate", f"query={req.query!r}  maxResults={req.maxResults}  minScore={req.minScore}")

        initial_state: ResearchQueryState = {
            "query": req.query,
            "max_results": req.maxResults,
            "min_score": req.minScore,
            "include_context": req.includeContext,
            "raw_results": [],
            "ranked_results": [],
            "steps": [],
        }

        final_state = self._graph.invoke(initial_state)

        result_items = [
            ResearchQueryResultItem(
                id=r.get("id", ""),
                documentId=r.get("documentId", ""),
                documentTitle=r.get("documentTitle"),
                chunkIndex=r.get("chunkIndex", 0),
                content=r.get("content", ""),
                contextSummary=r.get("contextSummary"),
                score=r.get("score", 0.0),
                rankSource=r.get("rankSource", "hybrid"),
                relevanceReason=r.get("relevanceReason"),
                metadata=r.get("metadata", {}),
            )
            for r in final_state.get("ranked_results", [])
        ]

        response = ResearchQueryResponse(
            query=req.query,
            resultsCount=len(result_items),
            results=result_items,
            executionTimeMs=self.elapsed_ms(),
            agentSteps=self.get_steps() + final_state.get("steps", []),
        )

        self.log_step("complete", f"Returning {response.resultsCount} results in {response.executionTimeMs}ms")
        return response.model_dump()
