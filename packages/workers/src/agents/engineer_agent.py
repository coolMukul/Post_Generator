"""EngineerAgent – maps tasks to code-level steps.

Takes a task description and produces a structured plan of files
to create/modify, unit test files, and identifies blockers.
Outputs follow the EngineerAgent JSON contract.

Console log format: [Agent:EngineerAgent][step:<step>] message
"""
import logging
from typing import Any, Dict, List

from ..models.agent_schemas import ManifestSchema
from .base_agent import BaseAgent
from .tools.search_papers import search_papers
from .tools.cite_source import cite_sources_from_results

logger = logging.getLogger(__name__)


class EngineerAgent(BaseAgent):
    """Concrete engineer agent that decomposes tasks into code-level steps."""

    def __init__(self, manifest: ManifestSchema):
        super().__init__(manifest)
        self.register_tool("search_papers", search_papers)

    def execute(self, run_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decompose a task into actionable code steps.

        Input:
            task_id: str (required)
            title: str (required)
            description: str (required)
            acceptance_criteria: list[str]
            required_files: list[str]
            query: str (optional — if provided, searches for context first)

        Output (EngineerAgent contract):
            task_id, steps[], unit_test_files[], shell_snippets[],
            blocked: bool, blocks[]
        """
        task_id = input_data.get("task_id", run_id)
        title = input_data.get("title", "Untitled task")
        description = input_data.get("description", "")
        acceptance_criteria = input_data.get("acceptance_criteria", [])
        required_files = input_data.get("required_files", [])
        query = input_data.get("query", "")

        self.log("start", f"task_id={task_id} title={title!r}")

        search_context: List[Dict[str, Any]] = []
        if query:
            self.log("research", f"Searching for context: {query!r}")
            search_result = self.call_tool("search_papers", {"query": query, "limit": 5})
            if search_result.output and not search_result.error:
                search_context = search_result.output.get("results", [])
                self.log("research", f"Found {len(search_context)} context results")

        steps = self._plan_steps(title, description, required_files, acceptance_criteria)
        unit_test_files = self._plan_tests(title, required_files)
        shell_snippets = self._plan_shell(required_files)
        blocked, blocks = self._check_blockers(description, required_files)

        self.log("complete", f"steps={len(steps)} blocked={blocked}")

        return {
            "task_id": task_id,
            "steps": steps,
            "unit_test_files": unit_test_files,
            "shell_snippets": shell_snippets,
            "blocked": blocked,
            "blocks": blocks,
            "search_context_count": len(search_context),
        }

    def _plan_steps(
        self,
        title: str,
        description: str,
        required_files: List[str],
        acceptance_criteria: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate code-level steps from the task description."""
        steps: List[Dict[str, Any]] = []

        for filepath in required_files:
            action = "create"
            if any(kw in filepath for kw in ["__init__", "main.py", "worker.py", "page.tsx"]):
                action = "modify"
            steps.append({
                "step_name": f"{'Create' if action == 'create' else 'Modify'} {filepath.split('/')[-1]}",
                "action": action,
                "file_path": filepath,
                "description": f"Implement {filepath.split('/')[-1]} for: {title}",
            })

        for criterion in acceptance_criteria:
            steps.append({
                "step_name": f"Verify: {criterion[:60]}",
                "action": "verify",
                "file_path": "",
                "description": criterion,
            })

        return steps

    def _plan_tests(self, title: str, required_files: List[str]) -> List[str]:
        """Determine which test files are needed."""
        test_files = []
        for filepath in required_files:
            if filepath.startswith("unit-test/"):
                test_files.append(filepath)
        if not test_files:
            safe_name = title.lower().replace(" ", "_")[:30]
            test_files.append(f"unit-test/Phase4-{safe_name}_test.py")
        return test_files

    def _plan_shell(self, required_files: List[str]) -> List[str]:
        """Generate shell commands for directory creation if needed."""
        dirs_needed: set = set()
        for filepath in required_files:
            parts = filepath.rsplit("/", 1)
            if len(parts) == 2:
                dirs_needed.add(parts[0])
        return [f"mkdir -p {d}" for d in sorted(dirs_needed)]

    def _check_blockers(self, description: str, required_files: List[str]) -> tuple:
        """Check for known blockers."""
        blocks: List[str] = []

        secret_keywords = ["api_key", "secret", "credential", "token"]
        desc_lower = description.lower()
        for kw in secret_keywords:
            if kw in desc_lower:
                blocks.append(f"Requires secret provisioning: {kw} referenced in description")

        return (len(blocks) > 0, blocks)
