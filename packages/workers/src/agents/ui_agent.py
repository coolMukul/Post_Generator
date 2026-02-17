"""UIAgent – designs UI specs and acceptance criteria.

Takes a task describing a UI page/component and produces a structured
spec with components, API calls, test specs, and acceptance criteria.
Outputs follow the UIAgent JSON contract.

Console log format: [Agent:UIAgent][step:<step>] message
"""
import logging
from typing import Any, Dict, List

from ..models.agent_schemas import ManifestSchema
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class UIAgent(BaseAgent):
    """Concrete UI agent that produces UI component specs and test plans."""

    def __init__(self, manifest: ManifestSchema):
        super().__init__(manifest)

    def execute(self, run_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a UI spec and test plan for the requested page/component.

        Input:
            task_id: str (required)
            page_spec: { route, components[], api_calls[] }
            title: str
            description: str

        Output (UIAgent contract):
            task_id, ui_spec[], test_spec[], acceptance_criteria[],
            estimated_hours
        """
        task_id = input_data.get("task_id", run_id)
        title = input_data.get("title", "Untitled UI task")
        description = input_data.get("description", "")
        page_spec = input_data.get("page_spec", {})

        self.log("start", f"task_id={task_id} title={title!r}")

        route = page_spec.get("route", "/unknown")
        components = page_spec.get("components", [title])
        api_calls = page_spec.get("api_calls", [])

        ui_spec = self._build_ui_spec(route, components, api_calls)
        test_spec = self._build_test_spec(task_id, route, components)
        acceptance = self._build_acceptance_criteria(route, components, api_calls)
        hours = self._estimate_hours(components, api_calls)

        self.log("complete", f"components={len(ui_spec)} tests={len(test_spec)}")

        return {
            "task_id": task_id,
            "ui_spec": ui_spec,
            "test_spec": test_spec,
            "acceptance_criteria": acceptance,
            "estimated_hours": hours,
        }

    def _build_ui_spec(
        self,
        route: str,
        components: List[str],
        api_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build UI component specifications."""
        specs = []
        for comp_name in components:
            safe_name = comp_name.replace(" ", "")
            specs.append({
                "component": safe_name,
                "path": f"packages/ui/app{route}/page.tsx",
                "props": f"{safe_name}Props",
                "api_calls": api_calls,
                "mock_data_allowed": False,
            })
        return specs

    def _build_test_spec(
        self,
        task_id: str,
        route: str,
        components: List[str],
    ) -> List[Dict[str, Any]]:
        """Build test specifications for the UI page."""
        specs = []
        route_name = route.strip("/").replace("/", "-") or "home"

        specs.append({
            "case_id": f"{task_id}-render",
            "type": "component",
            "description": f"Page at {route} renders without errors",
            "test_files": [f"unit-test/Phase4-UI-{route_name}-render.tsx"],
        })

        specs.append({
            "case_id": f"{task_id}-polling",
            "type": "integration",
            "description": f"Polling updates state correctly on {route}",
            "test_files": [f"unit-test/Phase4-UI-{route_name}-polling.tsx"],
        })

        specs.append({
            "case_id": f"{task_id}-manual",
            "type": "manual",
            "description": f"Manual acceptance check: navigate to {route}, verify layout and interactions",
            "test_files": [],
        })

        return specs

    def _build_acceptance_criteria(
        self,
        route: str,
        components: List[str],
        api_calls: List[Dict[str, Any]],
    ) -> List[str]:
        """Build acceptance criteria list."""
        criteria = [
            f"Page at {route} renders without errors",
            "Responsive design works at mobile and desktop breakpoints",
            "Accessible: keyboard navigation works, ARIA labels present",
        ]
        if api_calls:
            criteria.append(f"API calls ({len(api_calls)}) complete and results display correctly")
            criteria.append("Polling interval is 5s and updates state on completion")
        criteria.append("No console errors in browser dev tools")
        return criteria

    def _estimate_hours(
        self,
        components: List[str],
        api_calls: List[Dict[str, Any]],
    ) -> float:
        """Estimate implementation hours based on complexity."""
        base = 2.0
        base += len(components) * 1.5
        base += len(api_calls) * 1.0
        return round(base, 1)
