"""LinkedIn Post Generator Agent — composes short-form content from insights.

LangGraph StateGraph workflow:
  plan → headline → draft → format

Supports tone variants and generates hashtags.

Manifest:
  name: linkedin_post_agent
  version: 1.0.0
  job_type: linkedin_post_agent
  tools: [summarize_chunk]
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
    LinkedInPostRequest,
    LinkedInPostResponse,
)
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------
class PostState(TypedDict):
    title: str
    insights: List[Dict[str, Any]]
    tone: str
    max_length: int
    headline_candidates: List[str]
    draft: str
    final_post: str
    hashtags: List[str]
    steps: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@register_agent
class LinkedInPostAgent(AgentBase):
    """Composes LinkedIn posts from insights with tone control."""

    manifest = AgentManifest(
        name="linkedin_post_agent",
        version="1.0.0",
        description="Composes short-form LinkedIn content from insights; supports tone variants and A/B headline candidates.",
        required_tools=["summarize_chunk"],
        job_type="linkedin_post_agent",
        resource_limits=AgentResourceLimits(max_time_seconds=120, max_llm_calls=10),
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

    def _headline_node(self, state: PostState) -> dict:
        """Node: generate A/B headline candidates."""
        self.log_step("headline", "Generating headline candidates")
        self.check_time_limit()

        insights_text = "\n".join(
            f"- {ins.get('claim', '')}" for ins in state["insights"]
        )

        system_prompt = (
            "You are a LinkedIn content strategist. Generate 3 compelling headline/hook options "
            "for a LinkedIn post based on the provided insights. "
            "Each headline should be attention-grabbing, under 100 characters, and suited for the given tone.\n\n"
            "Respond in JSON format: {\"headlines\": [\"headline1\", \"headline2\", \"headline3\"]}"
        )
        user_prompt = (
            f"Topic: {state['title']}\n"
            f"Tone: {state['tone']}\n"
            f"Key insights:\n{insights_text}"
        )

        llm = self._get_llm()
        self.track_llm_call()
        result = llm.chat_json(system_prompt, user_prompt)

        headlines = result.get("headlines", [])
        if not isinstance(headlines, list):
            headlines = [str(headlines)]

        return {
            "headline_candidates": headlines,
            "steps": [f"Generated {len(headlines)} headline candidates"],
        }

    def _draft_node(self, state: PostState) -> dict:
        """Node: write the full LinkedIn post draft."""
        self.log_step("draft", "Writing post draft")
        self.check_time_limit()

        insights_text = "\n".join(
            f"- {ins.get('claim', '')}" for ins in state["insights"]
        )
        headline = state["headline_candidates"][0] if state["headline_candidates"] else state["title"]

        system_prompt = (
            "You are a LinkedIn content writer. Write a complete LinkedIn post based on the provided "
            "headline, insights, and tone. The post should:\n"
            "- Start with the headline/hook\n"
            "- Expand on 2-3 key insights with brief explanations\n"
            "- Include a call to action or thought-provoking question at the end\n"
            "- Be formatted for LinkedIn (short paragraphs, line breaks)\n"
            f"- Be under {state['max_length']} characters\n"
            f"- Tone: {state['tone']}\n\n"
            "Respond in JSON: {\"post\": \"the full post text\", \"hashtags\": [\"#tag1\", \"#tag2\"]}"
        )
        user_prompt = (
            f"Headline: {headline}\n"
            f"Topic: {state['title']}\n"
            f"Insights:\n{insights_text}"
        )

        llm = self._get_llm()
        self.track_llm_call()
        result = llm.chat_json(system_prompt, user_prompt)

        draft = result.get("post", "")
        hashtags = result.get("hashtags", [])
        if not isinstance(hashtags, list):
            hashtags = []

        return {
            "draft": draft,
            "hashtags": hashtags,
            "steps": [f"Draft written: {len(draft)} chars, {len(hashtags)} hashtags"],
        }

    def _format_node(self, state: PostState) -> dict:
        """Node: finalize the post (trim to max_length, clean formatting)."""
        self.log_step("format", "Finalizing post")

        post = state["draft"]
        if len(post) > state["max_length"]:
            post = post[:state["max_length"] - 3] + "..."

        return {
            "final_post": post,
            "steps": [f"Finalized post: {len(post)} chars"],
        }

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(PostState)
        builder.add_node("headline", self._headline_node)
        builder.add_node("draft", self._draft_node)
        builder.add_node("format", self._format_node)
        builder.add_edge(START, "headline")
        builder.add_edge("headline", "draft")
        builder.add_edge("draft", "format")
        builder.add_edge("format", END)
        return builder.compile()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = LinkedInPostRequest(**request)
        self.log_step("validate", f"title={req.title!r}  tone={req.tone}  insights={len(req.insights)}")

        initial_state: PostState = {
            "title": req.title,
            "insights": [ins.model_dump() for ins in req.insights],
            "tone": req.tone,
            "max_length": req.maxLength,
            "headline_candidates": [],
            "draft": "",
            "final_post": "",
            "hashtags": [],
            "steps": [],
        }

        final_state = self._graph.invoke(initial_state)

        post_text = final_state.get("final_post", "")
        response = LinkedInPostResponse(
            post=post_text,
            hashtags=final_state.get("hashtags", []),
            length=len(post_text),
            tone=req.tone,
            executionTimeMs=self.elapsed_ms(),
            agentSteps=self.get_steps() + final_state.get("steps", []),
        )

        self.log_step("complete", f"Post generated: {response.length} chars in {response.executionTimeMs}ms")
        return response.model_dump()
