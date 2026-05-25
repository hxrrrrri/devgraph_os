"""Session handoff generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.update.git import changed_files, current_branch, recent_commits


class HandoffEngine:
    def __init__(self, root: Path, config: DevGraphConfig, store: GraphStore) -> None:
        self.root = root
        self.config = config
        self.store = store

    def generate(self) -> tuple[Path, Path]:
        status = self.store.get_status(self.config.project.name)
        changes = changed_files(self.root)
        payload: dict[str, Any] = {
            "project_status": status.model_dump(),
            "current_branch": current_branch(self.root),
            "changed_files": [change.path for change in changes],
            "recent_commits": recent_commits(self.root),
            "graph_freshness": status.last_indexed_at,
            "recent_devgraph_sessions": self.store.recent_sessions(),
            "recent_changes": self.store.recent_changes(),
            "project_memories": self.store.list_memories(limit=20),
            "open_tasks": [],
            "accepted_decisions": [
                memory["content"]
                for memory in self.store.list_memories(kind="decision", limit=20)
            ],
            "rejected_attempts": [],
            "known_failing_tests": [],
            "recommended_next_step": "Run `devgraph status`, then `devgraph review` if files changed.",
            "relevant_files_to_inspect_first": [change.path for change in changes[:10]],
        }
        lines = [
            "# DevGraph Handoff",
            "",
            f"Project: `{status.project}`",
            f"Branch: `{payload['current_branch']}`",
            f"Graph freshness: `{status.last_indexed_at}`",
            "",
            "## Changed files",
            *(
                _lines_or_empty(
                    [f"- `{path}`" for path in payload["changed_files"]],
                    "No changed files detected.",
                )
            ),
            "",
            "## Recent commits",
            *(
                _lines_or_empty(
                    [f"- {commit}" for commit in payload["recent_commits"]],
                    "No git commits detected.",
                )
            ),
            "",
            "## Project memories",
            *(
                _lines_or_empty(
                    [
                        f"- `{memory['id']}` [{memory['kind']}] {memory['content']}"
                        for memory in payload["project_memories"]
                    ],
                    "No project memories recorded.",
                )
            ),
            "",
            "## Graph status",
            f"- Files: {status.total_files}",
            f"- Nodes: {status.total_nodes}",
            f"- Edges: {status.total_edges}",
            "",
            "## Recommended next step",
            payload["recommended_next_step"],
        ]
        sessions = self.store.storage_path / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        markdown_path = sessions / "handoff.md"
        json_path = sessions / "handoff.json"
        markdown_path.write_text("\n".join(lines), encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.store.record_session("handoff", "Session handoff", "Generated handoff context.", payload)
        return markdown_path, json_path


def _lines_or_empty(lines: list[str], empty: str) -> list[str]:
    return lines or [f"- {empty}"]
