"""Pydantic models for the agent framework (Phase 4+5).

Defines data contracts for agent runs, manifests, tool calls,
and workflow state used throughout the agent system.
"""
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRunStatus(str, Enum):
    """Agent run lifecycle states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class AgentRunRequest(BaseModel):
    """Incoming agent run request from the API."""
    agent_name: str = Field(..., min_length=1, description="Registered agent name")
    input: Dict[str, Any] = Field(default_factory=dict, description="Agent input payload")
    config: Dict[str, Any] = Field(default_factory=dict, description="Runtime config overrides")


class AgentRunResult(BaseModel):
    """Result of a completed agent run."""
    run_id: str
    agent_name: str
    status: AgentRunStatus
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps_completed: List[str] = Field(default_factory=list)
    start_time: datetime
    end_time: Optional[datetime] = None


class ToolCallRecord(BaseModel):
    """Record of a single tool invocation within an agent run."""
    tool_name: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ManifestSchema(BaseModel):
    """In-memory representation of an agent manifest JSON."""
    name: str
    version: str
    description: str
    tools: List[str] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    time_budget: Dict[str, Any] = Field(default_factory=dict)
    queue_job_type: str = "agent_run"
    reuses: List[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Shared state passed through LangGraph workflow nodes (Phase 5)."""
    run_id: str
    query: str
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    draft: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    current_step: str = "init"
    steps_log: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
