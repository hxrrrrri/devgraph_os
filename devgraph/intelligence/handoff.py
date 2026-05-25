"""Session handoff generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.review import ReviewEngine
from devgraph.update.git import changed_files, current_branch, recent_commits


class HandoffEngine:
    def __init__(self, root: Path, config: DevGraphConfig, store: GraphStore) -> None:
        self.root = root
        self.config = config
        self.store = store

    def generate(self) -> tuple[Path, Path]:
        status = self.store.get_status(self.config.project.name)
        changes = changed_files(self.root)
        changed_paths = [change.path for change in changes]
        changed_symbols = self.store.nodes_for_files(changed_paths) if changed_paths else []
        latest_debug = self._latest_report("debug.json")
        todo_items = self._todo_scan()
        memories = self.store.list_memories(limit=50)
        accepted_decisions = [
            memory["content"]
            for memory in memories
            if memory["kind"] in {"decision", "accepted_solution"}
        ]
        rejected_attempts = [
            memory["content"]
            for memory in memories
            if memory["kind"] == "rejected_attempt"
        ]
        open_tasks = [memory["content"] for memory in memories if memory["kind"] == "task"]
        review_summary = self._review_summary(changed_paths)
        payload: dict[str, Any] = {
            "project_status": status.model_dump(),
            "current_branch": current_branch(self.root),
            "changed_files": changed_paths,
            "changed_symbols": [
                {
                    "qualified_name": node.qualified_name,
                    "type": node.type,
                    "file_path": node.file_path,
                    "line_start": node.line_start,
                    "line_end": node.line_end,
                    "confidence_tier": node.confidence_tier,
                }
                for node in changed_symbols
                if node.type not in {"file", "module"}
            ],
            "impacted_files": review_summary.get("impacted_files", []),
            "recent_commits": recent_commits(self.root),
            "graph_freshness": status.last_indexed_at,
            "recent_devgraph_sessions": self.store.recent_sessions(),
            "recent_changes": self.store.recent_changes(),
            "latest_review_summary": review_summary,
            "latest_debug_summary": latest_debug,
            "project_memories": memories,
            "open_tasks": open_tasks,
            "accepted_decisions": accepted_decisions,
            "rejected_attempts": rejected_attempts,
            "known_failing_tests": [],
            "todo_fixme_scan": todo_items,
            "recommended_next_step": "Run `devgraph status --json`, then `devgraph review --json` before editing.",
            "relevant_files_to_inspect_first": [change.path for change in changes[:10]],
            "continue_prompt": CONTINUE_PROMPT,
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
            "## Changed symbols",
            *(
                _lines_or_empty(
                    [
                        f"- `{item['qualified_name']}` ({item['type']}, `{item['file_path']}`:{item['line_start']})"
                        for item in payload["changed_symbols"][:30]
                    ],
                    "No changed symbols detected.",
                )
            ),
            "",
            "## Impacted files",
            *(
                _lines_or_empty(
                    [f"- `{path}`" for path in payload["impacted_files"][:30]],
                    "No impacted files detected.",
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
            "## Accepted decisions",
            *_lines_or_empty([f"- {item}" for item in accepted_decisions], "No accepted decisions recorded."),
            "",
            "## Rejected attempts",
            *_lines_or_empty([f"- {item}" for item in rejected_attempts], "No rejected attempts recorded."),
            "",
            "## Open tasks",
            *_lines_or_empty([f"- {item}" for item in open_tasks], "No open tasks recorded."),
            "",
            "## TODO/FIXME scan",
            *_lines_or_empty(
                [f"- `{item['file_path']}`:{item['line']} {item['text']}" for item in todo_items[:25]],
                "No TODO/FIXME items found.",
            ),
            "",
            "## Graph status",
            f"- Files: {status.total_files}",
            f"- Nodes: {status.total_nodes}",
            f"- Edges: {status.total_edges}",
            "",
            "## Recommended next step",
            payload["recommended_next_step"],
            "",
            "## Continue from here",
            CONTINUE_SECTION,
            "",
            "## Continuation prompt",
            "```",
            CONTINUE_PROMPT,
            "```",
        ]
        sessions = self.store.storage_path / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        markdown_path = sessions / "handoff.md"
        json_path = sessions / "handoff.json"
        markdown_path.write_text("\n".join(lines), encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.store.record_session("handoff", "Session handoff", "Generated handoff context.", payload)
        return markdown_path, json_path

    def _review_summary(self, changed_paths: list[str]) -> dict[str, Any]:
        report = self._latest_report("review.json")
        if report:
            return report
        if not changed_paths:
            return {"risk_level": "low", "risk_score": 0, "impacted_files": []}
        try:
            result = ReviewEngine(self.root, self.config, self.store).review(files=changed_paths)
        except Exception:
            return {"risk_level": "unknown", "risk_score": 0, "impacted_files": []}
        return {
            "risk_level": result.risk_level,
            "risk_score": result.risk_score,
            "impacted_files": result.impacted_files,
            "changed_symbols": [node.qualified_name for node in result.changed_symbols],
            "missing_tests": result.missing_tests,
        }

    def _latest_report(self, name: str) -> dict[str, Any] | None:
        path = self.store.storage_path / "reports" / name
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _todo_scan(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        ignored_parts = {".git", ".devgraph", "node_modules", ".venv", "__pycache__", "dist", "build"}
        for path in self.root.rglob("*"):
            if len(items) >= 100:
                break
            if path.is_dir() or any(part in ignored_parts for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper:
                    items.append(
                        {
                            "file_path": path.relative_to(self.root).as_posix(),
                            "line": line_number,
                            "text": line.strip()[:240],
                        }
                    )
                    if len(items) >= 100:
                        break
        return items


def _lines_or_empty(lines: list[str], empty: str) -> list[str]:
    return lines or [f"- {empty}"]


CONTINUE_SECTION = """You are continuing work on this repository. Do not read files blindly.

Call DevGraph tools in this order:

1. get_project_status
2. review_changes
3. get_context
4. explain on the top changed file
5. search only if graph context is insufficient"""


CONTINUE_PROMPT = """You are continuing work on this repository. Start with DevGraph context instead of broad file reading.

Call DevGraph tools in this order: get_project_status, review_changes, get_context, explain on the top changed file, then search only if graph context is insufficient. Preserve user changes, inspect changed symbols first, and update tests/docs for any code changes."""
