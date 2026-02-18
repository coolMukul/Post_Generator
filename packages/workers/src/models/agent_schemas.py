"""Pydantic models for agent inputs, outputs, and manifests.

Contracts are locked by the existing UI pages:
  - Research Query Agent: POST /agent/research-query
  - Insight Extraction Agent: POST /agent/insight-extraction
  - LinkedIn Post Agent: POST /agent/linkedin-post
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent manifest
# ---------------------------------------------------------------------------
class AgentResourceLimits(BaseModel):
    """Per-agent resource constraints."""
    max_time_seconds: int = Field(default=120)
    max_llm_calls: int = Field(default=10)
    max_concurrency: int = Field(default=1)


class AgentManifest(BaseModel):
    """Describes an agent's identity, capabilities, and constraints."""
    name: str
    version: str
    description: str
    required_tools: List[str] = Field(default_factory=list)
    job_type: str
    resource_limits: AgentResourceLimits = Field(default_factory=AgentResourceLimits)


# ---------------------------------------------------------------------------
# Research Query Agent
# ---------------------------------------------------------------------------
class ResearchQueryRequest(BaseModel):
    """Input for the Research Query Agent."""
    query: str = Field(..., min_length=1)
    maxResults: int = Field(default=10, ge=1, le=50)
    minScore: float = Field(default=0.0, ge=0.0, le=1.0)
    includeContext: bool = Field(default=True)


class ResearchQueryResultItem(BaseModel):
    """Single result from the Research Query Agent."""
    id: str
    documentId: str
    documentTitle: Optional[str] = None
    chunkIndex: int
    content: str
    contextSummary: Optional[str] = None
    score: float
    rankSource: str
    relevanceReason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchQueryResponse(BaseModel):
    """Output from the Research Query Agent."""
    query: str
    resultsCount: int
    results: List[ResearchQueryResultItem]
    executionTimeMs: int
    agentSteps: List[str]


# ---------------------------------------------------------------------------
# Citation Validator Agent
# ---------------------------------------------------------------------------
class CitationRequest(BaseModel):
    """Input for the Citation Validator Agent."""
    claim: str = Field(..., min_length=1)
    source_chunk_id: str
    document_id: str


class CitationResult(BaseModel):
    """Output from the Citation Validator Agent."""
    claim: str
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    source_excerpt: str
    document_title: Optional[str] = None
    formatted_citation: str


# ---------------------------------------------------------------------------
# Insight Extraction Agent
# ---------------------------------------------------------------------------
class InsightExtractionRequest(BaseModel):
    """Input for the Insight Extraction Agent."""
    query: str = Field(..., min_length=1)
    maxResults: int = Field(default=10, ge=1, le=50)
    minScore: float = Field(default=0.0, ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    """A single piece of evidence supporting an insight."""
    excerpt: str
    chunkIndex: int
    documentId: str
    score: float
    chunkId: str


class InsightItem(BaseModel):
    """A structured insight extracted from the corpus."""
    id: str
    claim: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)


class InsightExtractionResponse(BaseModel):
    """Output from the Insight Extraction Agent."""
    insights: List[InsightItem]
    query: str
    executionTimeMs: int
    agentSteps: List[str]


# ---------------------------------------------------------------------------
# LinkedIn Post Generator Agent
# ---------------------------------------------------------------------------
class InsightInput(BaseModel):
    """A single insight used as input for post generation."""
    claim: str


class LinkedInPostRequest(BaseModel):
    """Input for the LinkedIn Post Generator Agent."""
    title: str = Field(default="")
    insights: List[InsightInput] = Field(default_factory=list)
    tone: str = Field(default="professional")
    maxLength: int = Field(default=700, ge=100, le=2000)


class LinkedInPostResponse(BaseModel):
    """Output from the LinkedIn Post Generator Agent."""
    post: str
    hashtags: List[str] = Field(default_factory=list)
    length: int
    tone: str
    executionTimeMs: int
    agentSteps: List[str]


# ---------------------------------------------------------------------------
# Content Strategy Orchestrator
# ---------------------------------------------------------------------------
class ContentStrategyRequest(BaseModel):
    """Input for the Content Strategy Orchestrator."""
    query: str = Field(..., min_length=1)
    tone: str = Field(default="professional")
    maxLength: int = Field(default=700, ge=100, le=2000)
    maxResults: int = Field(default=10, ge=1, le=50)
    minScore: float = Field(default=0.0, ge=0.0, le=1.0)


class ContentStrategyResponse(BaseModel):
    """Output from the Content Strategy Orchestrator."""
    query: str
    insights: List[InsightItem]
    post: str
    hashtags: List[str] = Field(default_factory=list)
    executionTimeMs: int
    agentSteps: List[str]
