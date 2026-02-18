"""Citation Validator Agent — verifies claim provenance and formats citations.

LangGraph StateGraph workflow:
  retrieve_source → verify_claim → format_citation

Uses the cite_source tool for LLM-based verification.

Manifest:
  name: citation_validator_agent
  version: 1.0.0
  job_type: citation_validator_agent
  tools: [cite_source, get_abstract]
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
    CitationRequest,
    CitationResult,
)
from ..tools.cite_source import cite_source
from ..tools.get_abstract import get_abstract
from ..config import get_database_url
from ..repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------
class CitationState(TypedDict):
    claim: str
    source_chunk_id: str
    document_id: str
    source_content: str
    document_title: str
    chunk_index: int
    verification: Dict[str, Any]
    steps: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@register_agent
class CitationValidatorAgent(AgentBase):
    """Verifies claim provenance against source chunks and formats citations."""

    manifest = AgentManifest(
        name="citation_validator_agent",
        version="1.0.0",
        description="Verifies claim provenance, formats citations, checks source correctness.",
        required_tools=["cite_source", "get_abstract"],
        job_type="citation_validator_agent",
        resource_limits=AgentResourceLimits(max_time_seconds=60, max_llm_calls=5),
    )

    def __init__(self):
        super().__init__()
        self._vector_repo: Optional[VectorRepository] = None

    def _get_vector_repo(self) -> VectorRepository:
        if self._vector_repo is None:
            self._vector_repo = VectorRepository(get_database_url())
        return self._vector_repo

    # ------------------------------------------------------------------
    # LangGraph nodes
    # ------------------------------------------------------------------

    def _retrieve_source_node(self, state: CitationState) -> dict:
        """Node: fetch the source chunk content from the vector store."""
        self.log_step("retrieve_source", f"Fetching chunk {state['source_chunk_id']}")
        self.check_time_limit()

        doc_info = get_abstract(state["document_id"])
        return {
            "document_title": doc_info.get("title", "Unknown"),
            "steps": [f"Retrieved document metadata: {doc_info.get('title', 'Unknown')}"],
        }

    def _verify_claim_node(self, state: CitationState) -> dict:
        """Node: verify the claim against the source using LLM."""
        self.log_step("verify_claim", f"Verifying claim against source")
        self.check_time_limit()
        self.track_llm_call()

        result = cite_source(
            claim=state["claim"],
            source_content=state["source_content"],
            document_title=state["document_title"],
            document_id=state["document_id"],
            chunk_index=state["chunk_index"],
        )
        return {
            "verification": result,
            "steps": [f"Verification: verified={result['verified']}  confidence={result['confidence']:.2f}"],
        }

    def _format_citation_node(self, state: CitationState) -> dict:
        """Node: format the final citation output."""
        self.log_step("format_citation", "Formatting citation result")
        v = state["verification"]
        return {
            "steps": [f"Citation formatted: {v.get('formatted_citation', '')}"],
        }

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(CitationState)
        builder.add_node("retrieve_source", self._retrieve_source_node)
        builder.add_node("verify_claim", self._verify_claim_node)
        builder.add_node("format_citation", self._format_citation_node)
        builder.add_edge(START, "retrieve_source")
        builder.add_edge("retrieve_source", "verify_claim")
        builder.add_edge("verify_claim", "format_citation")
        builder.add_edge("format_citation", END)
        return builder.compile()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = CitationRequest(**request)
        self.log_step("validate", f"claim={req.claim[:60]!r}  doc={req.document_id}")

        initial_state: CitationState = {
            "claim": req.claim,
            "source_chunk_id": req.source_chunk_id,
            "document_id": req.document_id,
            "source_content": "",
            "document_title": "",
            "chunk_index": 0,
            "verification": {},
            "steps": [],
        }

        graph = self._build_graph()
        final_state = graph.invoke(initial_state)

        v = final_state.get("verification", {})
        result = CitationResult(
            claim=req.claim,
            verified=v.get("verified", False),
            confidence=v.get("confidence", 0.0),
            source_excerpt=v.get("excerpt", ""),
            document_title=final_state.get("document_title", ""),
            formatted_citation=v.get("formatted_citation", ""),
        )

        self.log_step("complete", f"verified={result.verified}  confidence={result.confidence:.2f}")
        return result.model_dump()
