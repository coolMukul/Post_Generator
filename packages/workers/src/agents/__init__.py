"""LangGraph agents for multi-agent workflows.

Phase 4: Agent framework (base agent, registry, core tools).
Phase 5: Workflow nodes (insight extraction, draft generation, citation validation).
"""
from .base_agent import BaseAgent
from .registry import AgentRegistry

__all__ = ["BaseAgent", "AgentRegistry"]
