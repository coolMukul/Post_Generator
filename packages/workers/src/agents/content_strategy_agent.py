"""Content Strategy Orchestrator — meta-agent composing the full pipeline.

LangGraph StateGraph workflow:
  research → extract_insights → generate_post → review

Chains the Research Query Agent, Insight Extraction Agent, and LinkedIn Post
Agent into a single end-to-end workflow. This is the top-level orchestrator
for the content generation pipeline.

Manifest:
  name: content_strategy_agent
  version: 1.0.0
  job_type: content_strategy_agent
  tools: [search_papers, summarize_chunk, cite_source]
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
    ContentStrategyRequest,
    ContentStrategyResponse,
    InsightItem,
    EvidenceItem,
)
from ..tools.search_papers import search_papers
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------
class StrategyState(TypedDict):
    query: str
    tone: str
    max_length: int
    max_results: int
    min_score: float
    search_results: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    post: str
    hashtags: List[str]
    steps: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@register_agent
class ContentStrategyAgent(AgentBase):
    """Meta-agent: query → retrieval → insight extraction → post generation."""

    manifest = AgentManifest(
        name="content_strategy_agent",
        version="1.0.0",
        description="Meta-agent composing query, insight extraction, and draft generation into one workflow with editorial filters.",
        required_tools=["search_papers", "summarize_chunk", "cite_source"],
        job_type="content_strategy_agent",
        resource_limits=AgentResourceLimits(max_time_seconds=300, max_llm_calls=30),
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

    def _research_node(self, state: StrategyState) -> dict:
        """Node: retrieve relevant research chunks."""
        self.log_step("research", f"Searching corpus for: {state['query']}")
        self.check_time_limit()

        results = search_papers(
            query=state["query"],
            limit=state["max_results"],
            min_score=state["min_score"],
            search_mode="hybrid",
        )
        return {
            "search_results": results,
            "steps": [f"Research: retrieved {len(results)} chunks"],
        }

    def _insight_node(self, state: StrategyState) -> dict:
        """Node: extract structured insights from search results."""
        self.log_step("insights", f"Extracting insights from {len(state['search_results'])} chunks")
        self.check_time_limit()

        results = state["search_results"]
        if not results:
            return {"insights": [], "steps": ["No chunks available for insight extraction"]}

        chunks_text = ""
        for i, r in enumerate(results[:10]):
            chunks_text += f"\n--- Chunk {i+1} ({r.get('documentTitle', 'unknown')}) ---\n"
            chunks_text += r.get("content", "")[:500]
            chunks_text += "\n"

        system_prompt = (
            "You are a research insight extractor. From the provided chunks, extract 3-5 key insights.\n"
            "For each insight provide:\n"
            "- claim: concise statement\n"
            "- summary: 1-2 sentence explanation\n"
            "- confidence: 0.0 to 1.0\n"
            "- tags: 2-3 topic tags\n"
            "- source_chunks: chunk numbers (1-indexed)\n\n"
            "Return JSON: {\"insights\": [...]}"
        )
        user_prompt = f"Query: {state['query']}\n\nChunks:{chunks_text}"

        llm = self._get_llm()
        self.track_llm_call()
        extracted = llm.chat_json(system_prompt, user_prompt)
        raw_insights = extracted.get("insights", [])

        import uuid
        structured = []
        for raw in raw_insights:
            evidence = []
            for idx in raw.get("source_chunks", []):
                ci = int(idx) - 1
                if 0 <= ci < len(results):
                    sr = results[ci]
                    evidence.append({
                        "excerpt": sr.get("content", "")[:200],
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
            "steps": [f"Extracted {len(structured)} insights"],
        }

    def _post_node(self, state: StrategyState) -> dict:
        """Node: generate LinkedIn post from insights."""
        self.log_step("post", f"Generating post from {len(state['insights'])} insights")
        self.check_time_limit()

        insights = state["insights"]
        if not insights:
            return {"post": "", "hashtags": [], "steps": ["No insights to generate post from"]}

        insights_text = "\n".join(f"- {ins.get('claim', '')}" for ins in insights)

        system_prompt = (
            "You are a LinkedIn content writer. Write a compelling LinkedIn post.\n"
            "- Start with an attention-grabbing hook\n"
            "- Cover 2-3 key insights with brief explanations\n"
            "- End with a question or call to action\n"
            "- Use short paragraphs and line breaks\n"
            f"- Tone: {state['tone']}\n"
            f"- Max length: {state['max_length']} characters\n\n"
            "Respond in JSON: {\"post\": \"...\", \"hashtags\": [\"#tag1\"]}"
        )
        user_prompt = f"Topic: {state['query']}\n\nInsights:\n{insights_text}"

        llm = self._get_llm()
        self.track_llm_call()
        result = llm.chat_json(system_prompt, user_prompt)

        post = result.get("post", "")
        hashtags = result.get("hashtags", [])
        if len(post) > state["max_length"]:
            post = post[:state["max_length"] - 3] + "..."

        return {
            "post": post,
            "hashtags": hashtags if isinstance(hashtags, list) else [],
            "steps": [f"Generated post: {len(post)} chars"],
        }

    def _review_node(self, state: StrategyState) -> dict:
        """Node: editorial review checkpoint (HITL-ready)."""
        self.log_step("review", "Editorial review checkpoint")
        post_len = len(state.get("post", ""))
        insight_count = len(state.get("insights", []))
        return {
            "steps": [f"Review: {insight_count} insights, {post_len}-char post ready for review"],
        }

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(StrategyState)
        builder.add_node("research", self._research_node)
        builder.add_node("insights", self._insight_node)
        builder.add_node("post", self._post_node)
        builder.add_node("review", self._review_node)
        builder.add_edge(START, "research")
        builder.add_edge("research", "insights")
        builder.add_edge("insights", "post")
        builder.add_edge("post", "review")
        builder.add_edge("review", END)
        return builder.compile()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = ContentStrategyRequest(**request)
        self.log_step("validate", f"query={req.query!r}  tone={req.tone}")

        initial_state: StrategyState = {
            "query": req.query,
            "tone": req.tone,
            "max_length": req.maxLength,
            "max_results": req.maxResults,
            "min_score": req.minScore,
            "search_results": [],
            "insights": [],
            "post": "",
            "hashtags": [],
            "steps": [],
        }

        final_state = self._graph.invoke(initial_state)

        insight_items = [
            InsightItem(
                id=ins.get("id", ""),
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

        response = ContentStrategyResponse(
            query=req.query,
            insights=insight_items,
            post=final_state.get("post", ""),
            hashtags=final_state.get("hashtags", []),
            executionTimeMs=self.elapsed_ms(),
            agentSteps=self.get_steps() + final_state.get("steps", []),
        )

        self.log_step("complete", f"Pipeline complete in {response.executionTimeMs}ms")
        return response.model_dump()
