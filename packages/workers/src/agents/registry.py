"""Agent registry – loads manifests, registers agents, provides lookup.

The registry is the single source of truth for which agents are available
and how to instantiate them. It loads manifest JSON files from the
mukDocs/agent-manifests/ directory and maintains a mapping from agent
name to (manifest, agent_class) pairs.

Console logging follows the pattern:
  [Agent:AgentRegistry][step:<step>] message
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type

from ..models.agent_schemas import ManifestSchema
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

MANIFESTS_DIR = Path(__file__).resolve().parents[4] / "mukDocs" / "agent-manifests"


class AgentRegistry:
    """Central registry for all agents."""

    def __init__(self):
        self._manifests: Dict[str, ManifestSchema] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}

    @staticmethod
    def _log(step: str, message: str) -> None:
        logger.info("[Agent:AgentRegistry][step:%s] %s", step, message)

    def load_manifests(self, manifests_dir: Optional[Path] = None) -> int:
        """Load all .manifest.json files from the manifests directory.

        Returns the number of manifests loaded.
        """
        directory = manifests_dir or MANIFESTS_DIR
        self._log("load_manifests", f"Scanning {directory}")

        if not directory.exists():
            self._log("load_manifests", f"Directory not found: {directory}")
            return 0

        count = 0
        for manifest_file in sorted(directory.glob("*.manifest.json")):
            try:
                with open(manifest_file, "r") as f:
                    raw = json.load(f)
                manifest = ManifestSchema(**raw)
                self._manifests[manifest.name] = manifest
                self._log("load_manifests", f"Loaded manifest: {manifest.name} v{manifest.version}")
                count += 1
            except Exception as exc:
                self._log("load_manifests", f"Failed to load {manifest_file.name}: {exc}")

        self._log("load_manifests", f"Loaded {count} manifests")
        return count

    def register_agent(self, agent_name: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class against a loaded manifest name."""
        if agent_name not in self._manifests:
            self._log("register_agent", f"No manifest found for {agent_name}")
            raise ValueError(f"No manifest loaded for agent: {agent_name}")

        self._agent_classes[agent_name] = agent_class
        self._log("register_agent", f"Registered: {agent_name} -> {agent_class.__name__}")

    def get_manifest(self, agent_name: str) -> Optional[ManifestSchema]:
        """Retrieve a loaded manifest by agent name."""
        return self._manifests.get(agent_name)

    def list_agents(self) -> list:
        """Return a list of all registered agents with metadata."""
        agents = []
        for name, manifest in self._manifests.items():
            agents.append({
                "name": name,
                "version": manifest.version,
                "description": manifest.description,
                "tools": manifest.tools,
                "registered": name in self._agent_classes,
            })
        return agents

    def create_agent(self, agent_name: str) -> BaseAgent:
        """Instantiate a registered agent by name."""
        if agent_name not in self._agent_classes:
            self._log("create_agent", f"Agent not registered: {agent_name}")
            raise ValueError(f"Agent not registered: {agent_name}")

        manifest = self._manifests[agent_name]
        agent_class = self._agent_classes[agent_name]
        instance = agent_class(manifest)
        self._log("create_agent", f"Created instance: {agent_name}")
        return instance

    def has_agent(self, agent_name: str) -> bool:
        """Check if an agent is registered (manifest loaded + class registered)."""
        return agent_name in self._agent_classes

    def manifest_count(self) -> int:
        """Return the number of loaded manifests."""
        return len(self._manifests)

    def registered_count(self) -> int:
        """Return the number of fully registered agents (manifest + class)."""
        return len(self._agent_classes)
