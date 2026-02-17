"""TODOManagerAgent – manages mukDocs/TODO.md entries.

Appends, completes, and lists TODO items. Produces markdown snippets
when publish=true. Outputs follow the TODOManagerAgent JSON contract.

Console log format: [Agent:TODOManagerAgent][step:<step>] message
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..models.agent_schemas import ManifestSchema
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TODOManagerAgent(BaseAgent):
    """Concrete TODO manager agent that tracks project tasks."""

    def __init__(self, manifest: ManifestSchema):
        super().__init__(manifest)

    def execute(self, run_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manage TODO entries.

        Input:
            action: "append" | "complete" | "update" | "list"
            entry: { id, details, phase, priority }
            publish: bool (default false)

        Output (TODOManagerAgent contract):
            id, details, created_at, phase, priority,
            markdown_snippet (if publish=true), published
        """
        action = input_data.get("action", "list")
        entry = input_data.get("entry", {})
        publish = input_data.get("publish", False)

        self.log("start", f"action={action} publish={publish}")

        if action == "append":
            return self._append(entry, publish)
        elif action == "complete":
            return self._complete(entry, publish)
        elif action == "update":
            return self._update(entry, publish)
        elif action == "list":
            return self._list(publish)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _append(self, entry: Dict[str, Any], publish: bool) -> Dict[str, Any]:
        """Append a new TODO entry."""
        entry_id = entry.get("id", str(uuid.uuid4())[:8])
        details = entry.get("details", "No details provided")
        phase = entry.get("phase", "unknown")
        priority = entry.get("priority", "medium")
        created_at = datetime.now(timezone.utc).isoformat()

        self.log("append", f"id={entry_id} phase={phase} priority={priority}")

        snippet = ""
        if publish:
            snippet = f"- [{priority.upper()}] Phase {phase}: {details} (id: {entry_id})\n"

        return {
            "id": entry_id,
            "details": details,
            "created_at": created_at,
            "phase": phase,
            "priority": priority,
            "markdown_snippet": snippet,
            "published": publish,
            "action": "append",
        }

    def _complete(self, entry: Dict[str, Any], publish: bool) -> Dict[str, Any]:
        """Mark a TODO entry as complete."""
        entry_id = entry.get("id", "unknown")
        details = entry.get("details", "Completed")
        phase = entry.get("phase", "unknown")
        priority = entry.get("priority", "medium")
        completed_at = datetime.now(timezone.utc).isoformat()

        self.log("complete", f"Marking complete: id={entry_id}")

        snippet = ""
        if publish:
            snippet = f"- [DONE] Phase {phase}: {details} (id: {entry_id}, completed: {completed_at})\n"

        return {
            "id": entry_id,
            "details": details,
            "created_at": completed_at,
            "phase": phase,
            "priority": priority,
            "markdown_snippet": snippet,
            "published": publish,
            "action": "complete",
        }

    def _update(self, entry: Dict[str, Any], publish: bool) -> Dict[str, Any]:
        """Update an existing TODO entry."""
        entry_id = entry.get("id", "unknown")
        details = entry.get("details", "Updated")
        phase = entry.get("phase", "unknown")
        priority = entry.get("priority", "medium")
        updated_at = datetime.now(timezone.utc).isoformat()

        self.log("update", f"Updating: id={entry_id}")

        snippet = ""
        if publish:
            snippet = f"- [{priority.upper()}] Phase {phase}: {details} (id: {entry_id}, updated)\n"

        return {
            "id": entry_id,
            "details": details,
            "created_at": updated_at,
            "phase": phase,
            "priority": priority,
            "markdown_snippet": snippet,
            "published": publish,
            "action": "update",
        }

    def _list(self, publish: bool) -> Dict[str, Any]:
        """List current TODO status."""
        self.log("list", "Listing TODO status")

        return {
            "id": "list",
            "details": "Use mukDocs/TODO.md for the full TODO tracker",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "phase": "all",
            "priority": "info",
            "markdown_snippet": "See mukDocs/TODO.md for current items.\n" if publish else "",
            "published": publish,
            "action": "list",
        }
