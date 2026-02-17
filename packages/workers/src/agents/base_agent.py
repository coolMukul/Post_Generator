"""Base agent class for all agents in the system.

Every concrete agent extends BaseAgent, implements `execute()`,
and registers itself with the AgentRegistry.

Console logging follows the pattern:
  [Agent:<name>][step:<step>] message
"""
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.agent_schemas import (
    AgentRunResult,
    AgentRunStatus,
    ManifestSchema,
    ToolCallRecord,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, manifest: ManifestSchema):
        self.manifest = manifest
        self.name = manifest.name
        self.version = manifest.version
        self.tools: List[str] = manifest.tools
        self._tool_registry: Dict[str, Any] = {}

    def log(self, step: str, message: str) -> None:
        """Emit a structured console log: [Agent:<name>][step:<step>] message."""
        logger.info("[Agent:%s][step:%s] %s", self.name, step, message)

    def register_tool(self, tool_name: str, tool_fn: Any) -> None:
        """Register a callable tool that this agent can invoke."""
        self._tool_registry[tool_name] = tool_fn
        self.log("register_tool", f"Registered tool: {tool_name}")

    def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> ToolCallRecord:
        """Invoke a registered tool and return a ToolCallRecord."""
        self.log("call_tool", f"Calling tool: {tool_name}")
        start = time.monotonic()
        record = ToolCallRecord(tool_name=tool_name, input=tool_input)

        if tool_name not in self._tool_registry:
            record.error = f"Tool not registered: {tool_name}"
            self.log("call_tool", f"Tool not found: {tool_name}")
            return record

        try:
            result = self._tool_registry[tool_name](**tool_input)
            record.output = result if isinstance(result, dict) else {"result": result}
        except Exception as exc:
            record.error = str(exc)
            self.log("call_tool", f"Tool error: {tool_name} -> {exc}")
        finally:
            record.duration_ms = int((time.monotonic() - start) * 1000)

        return record

    def run(self, run_id: Optional[str] = None, input_data: Optional[Dict[str, Any]] = None) -> AgentRunResult:
        """Execute the agent with lifecycle logging and error handling."""
        run_id = run_id or str(uuid.uuid4())
        input_data = input_data or {}
        start_time = datetime.now(timezone.utc)

        self.log("run_start", f"run_id={run_id}")

        result = AgentRunResult(
            run_id=run_id,
            agent_name=self.name,
            status=AgentRunStatus.IN_PROGRESS,
            input=input_data,
            start_time=start_time,
        )

        try:
            output = self.execute(run_id, input_data)
            result.status = AgentRunStatus.SUCCESS
            result.output = output
            self.log("run_end", f"run_id={run_id} status=SUCCESS")
        except Exception as exc:
            result.status = AgentRunStatus.FAILED
            result.error = str(exc)
            self.log("run_end", f"run_id={run_id} status=FAILED error={exc}")
            logger.exception("Agent %s run failed: %s", self.name, exc)
        finally:
            result.end_time = datetime.now(timezone.utc)

        return result

    @abstractmethod
    def execute(self, run_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Implement the agent's core logic. Returns the output dict.

        Subclasses must implement this method. It receives the run_id
        (for correlation) and input_data (validated against the manifest
        input_schema by the registry before reaching here).
        """
        ...
