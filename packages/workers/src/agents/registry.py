"""Agent registry — central lookup for all registered agents.

Each agent registers itself via register_agent(). The worker loop
uses get_agent() to resolve a job_type to the correct agent instance.
"""
import logging
from typing import Dict, Optional, Type

from .base import AgentBase

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, Type[AgentBase]] = {}


def register_agent(agent_cls: Type[AgentBase]) -> Type[AgentBase]:
    """Decorator/function to register an agent class by its manifest job_type."""
    manifest = agent_cls.manifest
    job_type = manifest.job_type
    if job_type in _REGISTRY:
        logger.warning(
            "Agent job_type %r already registered — overwriting with %s",
            job_type, agent_cls.__name__,
        )
    _REGISTRY[job_type] = agent_cls
    logger.info(
        "Registered agent: %s v%s  job_type=%s  tools=%s",
        manifest.name, manifest.version, job_type, manifest.required_tools,
    )
    return agent_cls


def get_agent(job_type: str) -> Optional[AgentBase]:
    """Look up an agent by job_type and return a fresh instance, or None."""
    cls = _REGISTRY.get(job_type)
    if cls is None:
        return None
    return cls()


def list_agents() -> list:
    """Return manifests of all registered agents."""
    return [cls.manifest.model_dump() for cls in _REGISTRY.values()]
