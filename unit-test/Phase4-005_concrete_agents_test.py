"""Phase 4 – Unit tests for concrete agent implementations.

Tests:
  - EngineerAgent: task decomposition, step planning, blocker detection
  - UIAgent: UI spec generation, test spec, acceptance criteria
  - TODOManagerAgent: append, complete, update, list actions
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "workers"))

from src.agents.engineer_agent import EngineerAgent
from src.agents.ui_agent import UIAgent
from src.agents.todo_manager_agent import TODOManagerAgent
from src.models.agent_schemas import AgentRunResult, AgentRunStatus, ManifestSchema


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _manifest(name: str) -> ManifestSchema:
    return ManifestSchema(
        name=name,
        version="1.0.0",
        description=f"Test {name}",
        tools=[],
        input_schema={},
        output_schema={},
        time_budget={"default_seconds": 30},
    )


# ---------------------------------------------------------------
# EngineerAgent Tests
# ---------------------------------------------------------------
class TestEngineerAgent:
    def test_basic_task_decomposition(self):
        agent = EngineerAgent(_manifest("EngineerAgent"))
        result = agent.run(input_data={
            "task_id": "task-001",
            "title": "Create user service",
            "description": "Implement user registration and login.",
            "acceptance_criteria": ["Unit test passes", "Endpoint responds 200"],
            "required_files": ["src/services/user_service.py", "unit-test/Phase4-user-test.py"],
        })
        assert result.status == AgentRunStatus.SUCCESS
        output = result.output
        assert output["task_id"] == "task-001"
        assert len(output["steps"]) >= 2
        assert len(output["unit_test_files"]) >= 1
        assert output["blocked"] is False

    def test_blocker_detection(self):
        agent = EngineerAgent(_manifest("EngineerAgent"))
        result = agent.run(input_data={
            "task_id": "task-002",
            "title": "Add OAuth",
            "description": "Implement OAuth with api_key from external provider.",
            "required_files": [],
        })
        assert result.status == AgentRunStatus.SUCCESS
        assert result.output["blocked"] is True
        assert len(result.output["blocks"]) > 0
        assert any("api_key" in b for b in result.output["blocks"])

    def test_shell_snippets_for_directories(self):
        agent = EngineerAgent(_manifest("EngineerAgent"))
        result = agent.run(input_data={
            "task_id": "task-003",
            "title": "Add routes",
            "description": "Add new route files.",
            "required_files": ["src/routes/auth.py", "src/routes/users.py"],
        })
        assert result.status == AgentRunStatus.SUCCESS
        snippets = result.output["shell_snippets"]
        assert any("mkdir" in s for s in snippets)

    def test_default_test_file_generated(self):
        agent = EngineerAgent(_manifest("EngineerAgent"))
        result = agent.run(input_data={
            "task_id": "task-004",
            "title": "Build widget",
            "description": "Build a widget.",
            "required_files": ["src/widget.py"],
        })
        assert result.status == AgentRunStatus.SUCCESS
        assert len(result.output["unit_test_files"]) == 1
        assert result.output["unit_test_files"][0].startswith("unit-test/Phase4-")


# ---------------------------------------------------------------
# UIAgent Tests
# ---------------------------------------------------------------
class TestUIAgent:
    def test_basic_ui_spec(self):
        agent = UIAgent(_manifest("UIAgent"))
        result = agent.run(input_data={
            "task_id": "ui-001",
            "title": "Agent Dashboard",
            "page_spec": {
                "route": "/agent/dashboard",
                "components": ["AgentList", "RunHistory"],
                "api_calls": [
                    {"method": "GET", "path": "/agent/list"},
                    {"method": "POST", "path": "/agent/run"},
                ],
            },
        })
        assert result.status == AgentRunStatus.SUCCESS
        output = result.output
        assert output["task_id"] == "ui-001"
        assert len(output["ui_spec"]) == 2
        assert output["ui_spec"][0]["mock_data_allowed"] is False
        assert len(output["test_spec"]) == 3
        assert len(output["acceptance_criteria"]) >= 3
        assert output["estimated_hours"] > 0

    def test_no_api_calls(self):
        agent = UIAgent(_manifest("UIAgent"))
        result = agent.run(input_data={
            "task_id": "ui-002",
            "title": "Static Page",
            "page_spec": {"route": "/about", "components": ["AboutContent"]},
        })
        assert result.status == AgentRunStatus.SUCCESS
        assert result.output["estimated_hours"] >= 2.0

    def test_test_spec_types(self):
        agent = UIAgent(_manifest("UIAgent"))
        result = agent.run(input_data={
            "task_id": "ui-003",
            "title": "Search Page",
            "page_spec": {"route": "/search", "components": ["SearchForm"]},
        })
        assert result.status == AgentRunStatus.SUCCESS
        types = [t["type"] for t in result.output["test_spec"]]
        assert "component" in types
        assert "integration" in types
        assert "manual" in types


# ---------------------------------------------------------------
# TODOManagerAgent Tests
# ---------------------------------------------------------------
class TestTODOManagerAgent:
    def test_append_action(self):
        agent = TODOManagerAgent(_manifest("TODOManagerAgent"))
        result = agent.run(input_data={
            "action": "append",
            "entry": {
                "id": "todo-001",
                "details": "Add caching layer",
                "phase": "4",
                "priority": "high",
            },
            "publish": True,
        })
        assert result.status == AgentRunStatus.SUCCESS
        output = result.output
        assert output["id"] == "todo-001"
        assert output["action"] == "append"
        assert output["published"] is True
        assert "HIGH" in output["markdown_snippet"]
        assert "Phase 4" in output["markdown_snippet"]

    def test_complete_action(self):
        agent = TODOManagerAgent(_manifest("TODOManagerAgent"))
        result = agent.run(input_data={
            "action": "complete",
            "entry": {"id": "todo-001", "details": "Add caching layer", "phase": "4"},
        })
        assert result.status == AgentRunStatus.SUCCESS
        assert result.output["action"] == "complete"

    def test_update_action(self):
        agent = TODOManagerAgent(_manifest("TODOManagerAgent"))
        result = agent.run(input_data={
            "action": "update",
            "entry": {"id": "todo-001", "details": "Updated details", "phase": "5", "priority": "low"},
            "publish": True,
        })
        assert result.status == AgentRunStatus.SUCCESS
        assert result.output["action"] == "update"
        assert "LOW" in result.output["markdown_snippet"]

    def test_list_action(self):
        agent = TODOManagerAgent(_manifest("TODOManagerAgent"))
        result = agent.run(input_data={"action": "list"})
        assert result.status == AgentRunStatus.SUCCESS
        assert result.output["action"] == "list"
        assert result.output["phase"] == "all"

    def test_unknown_action(self):
        agent = TODOManagerAgent(_manifest("TODOManagerAgent"))
        result = agent.run(input_data={"action": "delete"})
        assert result.status == AgentRunStatus.FAILED
        assert "Unknown action" in result.error

    def test_publish_false_no_snippet(self):
        agent = TODOManagerAgent(_manifest("TODOManagerAgent"))
        result = agent.run(input_data={
            "action": "append",
            "entry": {"details": "Test entry", "phase": "4", "priority": "medium"},
            "publish": False,
        })
        assert result.status == AgentRunStatus.SUCCESS
        assert result.output["markdown_snippet"] == ""
        assert result.output["published"] is False


# ---------------------------------------------------------------
# All agents register in the registry correctly
# ---------------------------------------------------------------
class TestAllAgentsRegistry:
    def test_all_four_agents_register(self):
        from src.agents.registry import AgentRegistry
        from src.agents.research_agent import ResearchAgent

        manifests_dir = ROOT / "mukDocs" / "agent-manifests"
        if not manifests_dir.exists():
            pytest.skip("mukDocs/agent-manifests/ not found")

        registry = AgentRegistry()
        registry.load_manifests(manifests_dir)
        registry.register_agent("ResearchAgent", ResearchAgent)
        registry.register_agent("EngineerAgent", EngineerAgent)
        registry.register_agent("UIAgent", UIAgent)
        registry.register_agent("TODOManagerAgent", TODOManagerAgent)

        assert registry.registered_count() == 4
        assert registry.has_agent("ResearchAgent")
        assert registry.has_agent("EngineerAgent")
        assert registry.has_agent("UIAgent")
        assert registry.has_agent("TODOManagerAgent")

        for name in ["ResearchAgent", "EngineerAgent", "UIAgent", "TODOManagerAgent"]:
            agent = registry.create_agent(name)
            assert agent.name == name
