"""Insight Extraction Agent — extracts structured insights from the corpus.

LangGraph StateGraph workflow:
  retrieve → extract → structure → validate

Uses search_papers for retrieval, LLM for insight extraction,
and cite_source for evidence validation.

Manifest:
  name: insight_extraction_agent
  version: 1.0.0
  job_type: insight_extraction_agent
  tools: [search_papers, summarize_chunk, cite_source]
"""
import logging
import operator
import uuid
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict, Annotated

from langgraph.graph import StateGraph, START, END

from .base import AgentBase
from .registry import register_agent
from ..models.agent_schemas import (
    AgentManifest,
    AgentResourceLimits,
    InsightExtractionRequest,
    InsightExtractionResponse,
    InsightItem,
    EvidenceItem,
)
from ..tools.search_papers import search_papers
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------
class InsightState(TypedDict):
    query: str
    max_results: int
    min_score: float
    search_results: List[Dict[str, Any]]
    raw_insights: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    steps: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@register_agent
class InsightExtractionAgent(AgentBase):
    """Extracts structured insights from the research corpus."""

    manifest = AgentManifest(
        name="insight_extraction_agent",
        version="1.0.0",
        description="Extracts structured insights (key findings, claims, relevance) from documents using hybrid retrieval and LLM analysis.",
        required_tools=["search_papers", "summarize_chunk", "cite_source"],
        job_type="insight_extraction_agent",
        resource_limits=AgentResourceLimits(max_time_seconds=180, max_llm_calls=20),
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

    def _retrieve_node(self, state: InsightState) -> dict:
        """Node: retrieve relevant chunks from the corpus."""
        self.log_step("retrieve", f"Searching corpus for: {state['query']}")
        self.check_time_limit()

        results = search_papers(
            query=state["query"],
            limit=state["max_results"],
            min_score=state["min_score"],
            search_mode="hybrid",
        )
        return {
            "search_results": results,
            "steps": [f"Retrieved {len(results)} chunks from corpus"],
        }

    def _extract_node(self, state: InsightState) -> dict:
        """Node: use LLM to extract structured insights from retrieved chunks."""
        self.log_step("extract", f"Extracting insights from {len(state['search_results'])} chunks")
        self.check_time_limit()

        results = state["search_results"]
        if not results:
            return {"raw_insights": [], "steps": ["No chunks to extract insights from"]}

        chunks_text = ""
        for i, r in enumerate(results[:10]):
            chunks_text += f"\n--- Chunk {i+1} (doc: {r.get('documentTitle', 'unknown')}, score: {r.get('score', 0):.3f}) ---\n"
            chunks_text += r.get("content", "")[:500]
            if r.get("contextSummary"):
                chunks_text += f"\n[Context: {r['contextSummary']}]"
            chunks_text += "\n"

        system_prompt = (
            "You are an insight extraction assistant. Analyze the provided research chunks and extract "
            "key insights. For each insight, provide:\n"
            "- claim: A concise statement of the finding or claim\n"
            "- summary: A 1-2 sentence explanation\n"
            "- confidence: How well-supported the insight is (0.0 to 1.0)\n"
            "- tags: 2-4 topic tags\n"
            "- source_chunks: List of chunk numbers (1-indexed) that support this insight\n\n"
            "Return a JSON object: {\"insights\": [{\"claim\": \"...\", \"summary\": \"...\", "
            "\"confidence\": 0.85, \"tags\": [\"tag1\", \"tag2\"], \"source_chunks\": [1, 3]}]}\n"
            "Extract 3-7 distinct insights. Focus on the most significant findings."
        )
        user_prompt = f"Research query: {state['query']}\n\nChunks:{chunks_text}"

        llm = self._get_llm()
        self.track_llm_call()
        extracted = llm.chat_json(system_prompt, user_prompt)

        raw_insights = extracted.get("insights", [])
        if not isinstance(raw_insights, list):
            raw_insights = []

        return {
            "raw_insights": raw_insights,
            "steps": [f"Extracted {len(raw_insights)} raw insights via LLM"],
        }

    def _structure_node(self, state: InsightState) -> dict:
        """Node: structure raw insights with evidence links from search results."""
        self.log_step("structure", f"Structuring {len(state['raw_insights'])} insights with evidence")
        self.check_time_limit()

        search_results = state["search_results"]
        structured = []

        for raw in state["raw_insights"]:
            source_indices = raw.get("source_chunks", [])

            evidence = []
            for idx in source_indices:
                chunk_idx = int(idx) - 1
                if 0 <= chunk_idx < len(search_results):
                    sr = search_results[chunk_idx]
                    evidence.append({
                        "excerpt": (sr.get("content", ""))[:200],
                        "chunkIndex": sr.get("chunkIndex", 0),
                        "documentId": sr.get("documentId", ""),
                        "score": sr.get("score", 0.0),
                        "chunkId": sr.get("id", ""),
                    })

            structured.append({
                "id": str(uuid.uuid4()),
                "claim": raw.get("claim", ""),
                "summary": raw.get("summary", ""),
                "confidence": max(0.0, min(1.0, float(raw.get("confidence", 0.5)))),
                "tags": raw.get("tags", []),
                "evidence": evidence,
            })

        return {
            "insights": structured,
            "steps": [f"Structured {len(structured)} insights with evidence links"],
        }

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(InsightState)
        builder.add_node("retrieve", self._retrieve_node)
        builder.add_node("extract", self._extract_node)
        builder.add_node("structure", self._structure_node)
        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "extract")
        builder.add_edge("extract", "structure")
        builder.add_edge("structure", END)
        return builder.compile()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = InsightExtractionRequest(**request)
        self.log_step("validate", f"query={req.query!r}  maxResults={req.maxResults}")

        initial_state: InsightState = {
            "query": req.query,
            "max_results": req.maxResults,
            "min_score": req.minScore,
            "search_results": [],
            "raw_insights": [],
            "insights": [],
            "steps": [],
        }

        final_state = self._graph.invoke(initial_state)

        insight_items = [
            InsightItem(
                id=ins.get("id", str(uuid.uuid4())),
                claim=ins.get("claim", ""),
                summary=ins.get("summary", ""),
                confidence=ins.get("confidence", 0.5),
                tags=ins.get("tags", []),
                evidence=[
                    EvidenceItem(
                        excerpt=ev.get("excerpt", ""),
                        chunkIndex=ev.get("chunkIndex", 0),
                        documentId=ev.get("documentId", ""),
                        score=ev.get("score", 0.0),
                        chunkId=ev.get("chunkId", ""),
                    )
                    for ev in ins.get("evidence", [])
                ],
            )
            for ins in final_state.get("insights", [])
        ]

        response = InsightExtractionResponse(
            insights=insight_items,
            query=req.query,
            executionTimeMs=self.elapsed_ms(),
            agentSteps=self.get_steps() + final_state.get("steps", []),
        )

        self.log_step("complete", f"Returning {len(insight_items)} insights in {response.executionTimeMs}ms")
        return response.model_dump()
