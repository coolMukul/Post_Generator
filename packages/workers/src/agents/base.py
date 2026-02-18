"""Base agent class with step-level logging, timing, and resource tracking.

All agents inherit from AgentBase, which provides:
  - Automatic execution timing (start → end → duration)
  - Step-level logging using [Agent:<name>][step:<tool>] convention
  - Agent step accumulation for audit trail
  - Resource limit enforcement (time, LLM calls)
"""
import logging
import time
from typing import Any, Dict, List

from ..models.agent_schemas import AgentManifest, AgentResourceLimits

logger = logging.getLogger(__name__)


class AgentBase:
    """Base class for all LangGraph-powered agents."""

    manifest: AgentManifest

    def __init__(self):
        self._steps: List[str] = []
        self._start_time: float = 0.0
        self._llm_call_count: int = 0

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def limits(self) -> AgentResourceLimits:
        return self.manifest.resource_limits

    def log_step(self, step_name: str, detail: str = "") -> None:
        """Log an agent step and append to the step trail."""
        entry = f"[Agent:{self.name}][step:{step_name}] {detail}".strip()
        self._steps.append(entry)
        logger.info(entry)

    def start_timer(self) -> None:
        """Mark the beginning of agent execution."""
        self._start_time = time.time()
        self._llm_call_count = 0
        self._steps = []
        logger.info("[Agent:%s] Execution START", self.name)

    def elapsed_ms(self) -> int:
        """Return milliseconds since start_timer()."""
        return int((time.time() - self._start_time) * 1000)

    def check_time_limit(self) -> None:
        """Raise if the agent has exceeded its time limit."""
        elapsed = time.time() - self._start_time
        if elapsed > self.limits.max_time_seconds:
            raise TimeoutError(
                f"Agent {self.name} exceeded time limit: "
                f"{elapsed:.1f}s > {self.limits.max_time_seconds}s"
            )

    def track_llm_call(self) -> None:
        """Increment LLM call counter and check limit."""
        self._llm_call_count += 1
        if self._llm_call_count > self.limits.max_llm_calls:
            raise RuntimeError(
                f"Agent {self.name} exceeded LLM call limit: "
                f"{self._llm_call_count} > {self.limits.max_llm_calls}"
            )

    def get_steps(self) -> List[str]:
        """Return the accumulated step trail."""
        return list(self._steps)

    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent. Subclasses must implement _execute()."""
        self.start_timer()
        self.log_step("init", f"Starting {self.name} v{self.manifest.version}")
        result = self._execute(request)
        logger.info(
            "[Agent:%s] Execution END  duration=%dms  steps=%d  llm_calls=%d",
            self.name, self.elapsed_ms(), len(self._steps), self._llm_call_count,
        )
        return result

    def _execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to implement agent logic."""
        raise NotImplementedError
