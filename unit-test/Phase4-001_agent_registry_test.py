"""Phase 4 – Unit tests for AgentRegistry.

Tests:
  - Manifest loading from disk
  - Agent registration and lookup
  - Agent instantiation
  - Error handling for missing manifests/agents
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure workers package is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "workers"))

from src.agents.registry import AgentRegistry
from src.agents.base_agent import BaseAgent
from src.models.agent_schemas import ManifestSchema


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------
@pytest.fixture
def sample_manifest_dir(tmp_path):
    """Create a temp directory with sample manifest files."""
    manifest = {
        "name": "TestAgent",
        "version": "1.0.0",
        "description": "A test agent for unit testing",
        "tools": ["search_papers"],
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        "time_budget": {"default_seconds": 60, "max_seconds": 120},
        "queue_job_type": "agent_run",
    }
    path = tmp_path / "TestAgent.manifest.json"
    path.write_text(json.dumps(manifest))

    manifest2 = {
        "name": "AnotherAgent",
        "version": "2.0.0",
        "description": "Another test agent",
        "tools": [],
        "input_schema": {},
        "output_schema": {},
        "time_budget": {"default_seconds": 30},
        "queue_job_type": "agent_run",
    }
    path2 = tmp_path / "AnotherAgent.manifest.json"
    path2.write_text(json.dumps(manifest2))

    return tmp_path


class ConcreteTestAgent(BaseAgent):
    """Minimal concrete agent for testing."""

    def execute(self, run_id, input_data):
        return {"echo": input_data.get("query", "none")}


# ---------------------------------------------------------------
# Tests
# ---------------------------------------------------------------
class TestAgentRegistry:
    def test_load_manifests(self, sample_manifest_dir):
        registry = AgentRegistry()
        count = registry.load_manifests(sample_manifest_dir)
        assert count == 2
        assert registry.manifest_count() == 2

    def test_load_manifests_nonexistent_dir(self, tmp_path):
        registry = AgentRegistry()
        count = registry.load_manifests(tmp_path / "nonexistent")
        assert count == 0

    def test_get_manifest(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        manifest = registry.get_manifest("TestAgent")
        assert manifest is not None
        assert manifest.name == "TestAgent"
        assert manifest.version == "1.0.0"
        assert "search_papers" in manifest.tools

    def test_get_manifest_missing(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        assert registry.get_manifest("NonexistentAgent") is None

    def test_register_agent(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        registry.register_agent("TestAgent", ConcreteTestAgent)
        assert registry.has_agent("TestAgent")
        assert registry.registered_count() == 1

    def test_register_agent_no_manifest(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        with pytest.raises(ValueError, match="No manifest loaded"):
            registry.register_agent("UnknownAgent", ConcreteTestAgent)

    def test_create_agent(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        registry.register_agent("TestAgent", ConcreteTestAgent)
        agent = registry.create_agent("TestAgent")
        assert isinstance(agent, ConcreteTestAgent)
        assert agent.name == "TestAgent"

    def test_create_agent_not_registered(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        with pytest.raises(ValueError, match="Agent not registered"):
            registry.create_agent("AnotherAgent")

    def test_list_agents(self, sample_manifest_dir):
        registry = AgentRegistry()
        registry.load_manifests(sample_manifest_dir)
        registry.register_agent("TestAgent", ConcreteTestAgent)
        agents = registry.list_agents()
        assert len(agents) == 2
        test_agent = next(a for a in agents if a["name"] == "TestAgent")
        assert test_agent["registered"] is True
        another = next(a for a in agents if a["name"] == "AnotherAgent")
        assert another["registered"] is False

    def test_load_real_manifests(self):
        """Test loading the actual project manifests from mukDocs/agent-manifests/."""
        manifests_dir = ROOT / "mukDocs" / "agent-manifests"
        if not manifests_dir.exists():
            pytest.skip("mukDocs/agent-manifests/ not found")
        registry = AgentRegistry()
        count = registry.load_manifests(manifests_dir)
        assert count >= 4
        assert registry.get_manifest("ResearchAgent") is not None
        assert registry.get_manifest("EngineerAgent") is not None
        assert registry.get_manifest("UIAgent") is not None
        assert registry.get_manifest("TODOManagerAgent") is not None
