"""Phase 4 – Unit tests for agent schema models.

Tests:
  - AgentRunRequest validation
  - AgentRunResult creation
  - WorkflowState structure
  - ManifestSchema parsing
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "workers"))

from src.models.agent_schemas import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    ManifestSchema,
    ToolCallRecord,
    WorkflowState,
)


class TestAgentRunRequest:
    def test_minimal_request(self):
        req = AgentRunRequest(agent_name="ResearchAgent")
        assert req.agent_name == "ResearchAgent"
        assert req.input == {}
        assert req.config == {}

    def test_full_request(self):
        req = AgentRunRequest(
            agent_name="ResearchAgent",
            input={"query": "test", "limit": 5},
            config={"timeout": 60},
        )
        assert req.input["query"] == "test"
        assert req.config["timeout"] == 60


class TestAgentRunResult:
    def test_success_result(self):
        result = AgentRunResult(
            run_id="run-1",
            agent_name="TestAgent",
            status=AgentRunStatus.SUCCESS,
            output={"data": "value"},
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        assert result.status == AgentRunStatus.SUCCESS
        assert result.error is None

    def test_failed_result(self):
        result = AgentRunResult(
            run_id="run-2",
            agent_name="TestAgent",
            status=AgentRunStatus.FAILED,
            error="Something broke",
            start_time=datetime.now(timezone.utc),
        )
        assert result.status == AgentRunStatus.FAILED
        assert result.output is None


class TestManifestSchema:
    def test_parse_manifest(self):
        manifest = ManifestSchema(
            name="TestAgent",
            version="1.0.0",
            description="Test",
            tools=["search_papers", "summarize_chunk"],
            time_budget={"default_seconds": 60},
        )
        assert manifest.name == "TestAgent"
        assert len(manifest.tools) == 2

    def test_default_values(self):
        manifest = ManifestSchema(
            name="Min",
            version="0.1.0",
            description="Minimal",
        )
        assert manifest.tools == []
        assert manifest.queue_job_type == "agent_run"
        assert manifest.reuses == []


class TestWorkflowState:
    def test_initial_state(self):
        state = WorkflowState(
            run_id="run-123",
            query="test query",
        )
        assert state.run_id == "run-123"
        assert state.query == "test query"
        assert state.search_results == []
        assert state.insights == []
        assert state.draft is None
        assert state.current_step == "init"

    def test_populated_state(self):
        state = WorkflowState(
            run_id="run-456",
            query="AI research",
            search_results=[{"id": "1", "score": 0.9}],
            insights=["Key finding 1"],
            draft="Generated draft text",
            citations=[{"document_id": "doc-1"}],
            current_step="citation_validation",
            steps_log=["retrieval", "insight_extraction", "draft_generation"],
        )
        assert len(state.search_results) == 1
        assert len(state.insights) == 1
        assert state.draft is not None


class TestToolCallRecord:
    def test_success_record(self):
        record = ToolCallRecord(
            tool_name="search_papers",
            input={"query": "test"},
            output={"results": []},
            duration_ms=150,
        )
        assert record.error is None
        assert record.duration_ms == 150

    def test_error_record(self):
        record = ToolCallRecord(
            tool_name="search_papers",
            input={"query": "test"},
            error="Connection refused",
        )
        assert record.output is None
        assert "Connection refused" in record.error
