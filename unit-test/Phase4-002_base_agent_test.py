"""Phase 4 – Unit tests for BaseAgent.

Tests:
  - Agent lifecycle (run → execute → result)
  - Tool registration and invocation
  - Error handling in execute
  - Structured logging
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "workers"))

from src.agents.base_agent import BaseAgent
from src.models.agent_schemas import (
    AgentRunResult,
    AgentRunStatus,
    ManifestSchema,
    ToolCallRecord,
)


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------
def _make_manifest(name="TestAgent"):
    return ManifestSchema(
        name=name,
        version="1.0.0",
        description="Test agent",
        tools=["test_tool"],
        input_schema={},
        output_schema={},
        time_budget={"default_seconds": 30},
    )


class SuccessAgent(BaseAgent):
    def execute(self, run_id, input_data):
        self.log("work", "Doing work")
        return {"message": f"Hello from {run_id}", "input": input_data}


class FailingAgent(BaseAgent):
    def execute(self, run_id, input_data):
        raise RuntimeError("Something went wrong")


class ToolUsingAgent(BaseAgent):
    def execute(self, run_id, input_data):
        result = self.call_tool("adder", {"a": 1, "b": 2})
        return {"tool_result": result.output}


# ---------------------------------------------------------------
# Tests
# ---------------------------------------------------------------
class TestBaseAgent:
    def test_successful_run(self):
        agent = SuccessAgent(_make_manifest())
        result = agent.run(run_id="test-123", input_data={"query": "test"})
        assert isinstance(result, AgentRunResult)
        assert result.status == AgentRunStatus.SUCCESS
        assert result.run_id == "test-123"
        assert result.output["message"] == "Hello from test-123"
        assert result.error is None
        assert result.end_time is not None

    def test_failed_run(self):
        agent = FailingAgent(_make_manifest())
        result = agent.run(run_id="fail-456")
        assert result.status == AgentRunStatus.FAILED
        assert "Something went wrong" in result.error
        assert result.output is None

    def test_auto_generated_run_id(self):
        agent = SuccessAgent(_make_manifest())
        result = agent.run()
        assert result.run_id is not None
        assert len(result.run_id) > 0

    def test_agent_properties(self):
        manifest = _make_manifest("MyAgent")
        agent = SuccessAgent(manifest)
        assert agent.name == "MyAgent"
        assert agent.version == "1.0.0"
        assert "test_tool" in agent.tools

    def test_tool_registration(self):
        agent = ToolUsingAgent(_make_manifest())
        agent.register_tool("adder", lambda a, b: {"sum": a + b})
        assert "adder" in agent._tool_registry

    def test_tool_call_success(self):
        agent = ToolUsingAgent(_make_manifest())
        agent.register_tool("adder", lambda a, b: {"sum": a + b})
        record = agent.call_tool("adder", {"a": 3, "b": 4})
        assert isinstance(record, ToolCallRecord)
        assert record.error is None
        assert record.output == {"sum": 7}
        assert record.duration_ms is not None

    def test_tool_call_not_registered(self):
        agent = ToolUsingAgent(_make_manifest())
        record = agent.call_tool("nonexistent", {})
        assert record.error == "Tool not registered: nonexistent"
        assert record.output is None

    def test_tool_call_with_exception(self):
        def bad_tool(**kwargs):
            raise ValueError("tool broke")

        agent = ToolUsingAgent(_make_manifest())
        agent.register_tool("bad", bad_tool)
        record = agent.call_tool("bad", {})
        assert "tool broke" in record.error

    def test_run_timestamps(self):
        agent = SuccessAgent(_make_manifest())
        result = agent.run()
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.end_time >= result.start_time
