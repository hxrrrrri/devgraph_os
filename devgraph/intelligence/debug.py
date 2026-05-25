"""Debug context engine."""

from __future__ import annotations

import re
from typing import cast

from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Node
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest
from devgraph.update.diff_parser import nodes_for_changed_lines

STACK_PATH_RE = re.compile(r"(?P<path>[\w./\\-]+\.(?:py|ts|tsx|js|jsx|go|rs|java))(?::(?P<line>\d+))?")
PY_FRAME_RE = re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<function>[^\s]+)')
NODE_FRAME_RE = re.compile(r"\s*at\s+(?:(?P<function>[^\s(]+)\s+\()?((?P<path>[\w./\\:-]+\.(?:js|ts|tsx|jsx)):(?P<line>\d+):(?P<col>\d+)\)?)")
JAVA_FRAME_RE = re.compile(r"\s*at\s+(?P<function>[\w.$<>]+)\((?P<file>[^:()]+)(?::(?P<line>\d+))?\)")
GO_RUST_FRAME_RE = re.compile(r"^\s*(?P<path>[\w./\\-]+\.(?:go|rs)):(?P<line>\d+)(?::\d+)?", re.MULTILINE)
ERROR_RE = re.compile(r"^(?P<type>[A-Za-z_.$][\w.$]*(?:Error|Exception|Panic|panic)?):\s*(?P<message>.+)$", re.MULTILINE)


class DebugEngine:
    def __init__(self, store: GraphStore) -> None:
        self.store = store
        self.packer = ContextPacker(store)

    def debug(self, issue: str, budget: str = "normal") -> str:
        analysis = self.analyze(issue, budget=budget)
        stack_frames = cast(list[dict[str, object]], analysis["stack_frames"])
        suspected_nodes = cast(list[dict[str, object]], analysis["suspected_nodes"])
        recommended_order = cast(list[str], analysis["recommended_debugging_order"])
        seed_files = [str(frame["file_path"]) for frame in stack_frames if frame.get("file_path")]
        entry_points = [f"- `{path}`" for path in dict.fromkeys(seed_files)]
        if not entry_points:
            entry_points = ["- No stack-trace file paths were detected."]
        stack_frame_lines = [
            f"- `{frame.get('file_path')}`:{frame.get('line') or '?'} in `{frame.get('function') or 'unknown'}`"
            for frame in stack_frames[:20]
        ] or ["- No stack frames parsed."]
        suspected_node_lines = [
            f"- `{node['qualified_name']}` ({node['type']}, lines {node.get('line_start')}-{node.get('line_end')})"
            for node in suspected_nodes[:20]
        ] or ["- No stack frames mapped to graph nodes."]
        return "\n".join(
            [
                "# DevGraph Debug Context",
                "",
                f"Error type: `{analysis['error_type'] or 'unknown'}`",
                f"Message: {analysis['error_message'] or 'No explicit error message parsed.'}",
                "",
                "## Parsed stack frames",
                *stack_frame_lines,
                "",
                "## Suspected entry points",
                *entry_points,
                "",
                "## Suspected graph nodes",
                *suspected_node_lines,
                "",
                "## Recommended debugging order",
                *[f"{index + 1}. {item}" for index, item in enumerate(recommended_order)],
                "",
                str(analysis["context_pack"]),
            ]
        )

    def analyze(self, issue: str, budget: str = "normal") -> dict[str, object]:
        frames = parse_stack_trace(issue)
        seed_files = [str(frame["file_path"]) for frame in frames if frame.get("file_path")]
        suspected_nodes: dict[str, Node] = {}
        for frame in frames:
            path = frame.get("file_path")
            line = frame.get("line")
            if isinstance(path, str) and isinstance(line, int):
                for node in nodes_for_changed_lines(self.store, path, [line]):
                    suspected_nodes[node.id] = node
        pack = self.packer.pack(
            ContextRequest(
                task_type="debug",
                query=issue,
                seed_files=list(dict.fromkeys(seed_files)),
                seed_nodes=list(suspected_nodes),
                token_budget=budget,
                include_source=True,
            )
        )
        error = ERROR_RE.search(issue)
        related_tests = self.store.tests_for_nodes(list(suspected_nodes), limit=20)
        related_configs = self._related_configs(seed_files)
        return {
            "error_type": error.group("type") if error else None,
            "error_message": error.group("message") if error else None,
            "stack_frames": frames,
            "suspected_entry_points": list(dict.fromkeys(seed_files)),
            "suspected_nodes": [node.model_dump() for node in suspected_nodes.values()],
            "related_files": sorted(set(seed_files)),
            "related_callers_or_callees": self._related_graph_paths(list(suspected_nodes)),
            "related_configs": related_configs,
            "related_tests": [node.model_dump() for node in related_tests],
            "recent_related_changes": self.store.recent_changes(limit=10),
            "recommended_debugging_order": self._debug_order(frames, list(suspected_nodes.values()), related_configs),
            "context_pack": pack,
        }

    def _related_graph_paths(self, node_ids: list[str]) -> list[str]:
        neighborhood = self.store.get_neighborhood(node_ids, depth=1, limit=40) if node_ids else {"nodes": [], "edges": []}
        by_id = {node["id"]: node for node in neighborhood["nodes"]}
        paths: list[str] = []
        for edge in neighborhood["edges"][:20]:
            source = by_id.get(edge["source_id"])
            target = by_id.get(edge["target_id"])
            if source and target:
                paths.append(f"{source['qualified_name']} --{edge['type']}--> {target['qualified_name']}")
        return paths

    def _related_configs(self, seed_files: list[str]) -> list[str]:
        if not seed_files:
            return []
        rows = self.store.connection.execute(
            """
            SELECT path FROM files
            WHERE category IN ('config', 'infra') AND is_deleted = 0
            ORDER BY path
            LIMIT 25
            """
        ).fetchall()
        return [row["path"] for row in rows]

    @staticmethod
    def _debug_order(frames: list[dict[str, object]], nodes: list[Node], configs: list[str]) -> list[str]:
        order = []
        if frames:
            first = frames[0]
            order.append(f"Open {first.get('file_path')} at line {first.get('line')}.")
        if nodes:
            order.append(f"Inspect mapped graph node {nodes[0].qualified_name}.")
        order.append("Walk callers and callees from the graph paths before broad searching.")
        if configs:
            order.append("Check related config files for environment or routing changes.")
        order.append("Run or add the nearest tests around the suspected node.")
        return order


def parse_stack_trace(issue: str) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for match in PY_FRAME_RE.finditer(issue):
        frames.append(_frame(match.group("path"), int(match.group("line")), match.group("function"), "python"))
    for match in NODE_FRAME_RE.finditer(issue):
        frames.append(_frame(match.group("path"), int(match.group("line")), match.group("function"), "node"))
    for match in JAVA_FRAME_RE.finditer(issue):
        file_name = match.group("file")
        frames.append(
            {
                "file_path": file_name,
                "line": int(match.group("line")) if match.group("line") else None,
                "function": match.group("function"),
                "language": "java",
                "raw": match.group(0).strip(),
            }
        )
    for match in GO_RUST_FRAME_RE.finditer(issue):
        language = "go" if match.group("path").endswith(".go") else "rust"
        frames.append(_frame(match.group("path"), int(match.group("line")), None, language))
    if not frames:
        for match in STACK_PATH_RE.finditer(issue):
            frames.append(
                _frame(
                    match.group("path"),
                    int(match.group("line")) if match.group("line") else None,
                    None,
                    "unknown",
                )
            )
    deduped: list[dict[str, object]] = []
    seen: set[tuple[object, object, object]] = set()
    for frame in frames:
        key = (frame.get("file_path"), frame.get("line"), frame.get("function"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(frame)
    return deduped


def _frame(path: str, line: int | None, function: str | None, language: str) -> dict[str, object]:
    return {
        "file_path": path.replace("\\", "/").lstrip("./"),
        "line": line,
        "function": function,
        "language": language,
    }
