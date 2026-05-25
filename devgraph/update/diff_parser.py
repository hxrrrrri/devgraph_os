"""Unified diff parsing and changed-symbol mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from devgraph.core.schema import Node
from devgraph.update.git import diff_patch, run_git

if TYPE_CHECKING:  # pragma: no cover
    from devgraph.core.graph_store import GraphStore


@dataclass(frozen=True)
class DiffHunk:
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    changed_lines: list[int]
    text: str


HUNK_RE = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+"
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)


def git_diff(root: Path, base: str | None = None, staged: bool = False, files: list[str] | None = None) -> str:
    args = ["diff"]
    if staged:
        args.append("--staged")
    elif base:
        args.append(base)
    if files:
        args.append("--")
        args.extend(files)
    return run_git(root, args)


def parse_unified_diff(patch: str) -> list[DiffHunk]:
    hunks: list[DiffHunk] = []
    current_file = ""
    hunk_header: re.Match[str] | None = None
    hunk_lines: list[str] = []
    old_line = 0
    new_line = 0
    changed_lines: list[int] = []

    def flush() -> None:
        nonlocal hunk_header, hunk_lines, changed_lines
        if hunk_header is None:
            return
        hunks.append(
            DiffHunk(
                file_path=current_file,
                old_start=int(hunk_header.group("old_start")),
                old_count=int(hunk_header.group("old_count") or "1"),
                new_start=int(hunk_header.group("new_start")),
                new_count=int(hunk_header.group("new_count") or "1"),
                changed_lines=changed_lines.copy(),
                text="\n".join(hunk_lines),
            )
        )
        hunk_header = None
        hunk_lines = []
        changed_lines = []

    for line in patch.splitlines():
        if line.startswith("+++ "):
            value = line[4:].strip()
            current_file = value[2:] if value.startswith("b/") else value
            if current_file == "/dev/null":
                current_file = ""
            continue
        match = HUNK_RE.match(line)
        if match:
            flush()
            hunk_header = match
            hunk_lines = [line]
            old_line = int(match.group("old_start"))
            new_line = int(match.group("new_start"))
            changed_lines = []
            continue
        if hunk_header is None:
            continue
        hunk_lines.append(line)
        if line.startswith("+") and not line.startswith("+++"):
            changed_lines.append(new_line)
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            if new_line > 0:
                changed_lines.append(new_line)
            old_line += 1
        else:
            old_line += 1
            new_line += 1
    flush()
    return hunks


def hunks_for_files(root: Path, files: list[str], base: str | None = None, staged: bool = False) -> list[DiffHunk]:
    patch = git_diff(root, base=base, staged=staged, files=files)
    if not patch:
        hunks: list[DiffHunk] = []
        for file_path in files:
            file_patch = diff_patch(root, file_path, base=base, staged=staged)
            hunks.extend(parse_unified_diff(file_patch))
        return hunks
    return parse_unified_diff(patch)


def map_hunks_to_nodes(store: GraphStore, hunks: list[DiffHunk]) -> dict[str, list[Node]]:
    mapped: dict[str, list[Node]] = {}
    for hunk in hunks:
        if not hunk.file_path:
            continue
        nodes = nodes_for_changed_lines(store, hunk.file_path, hunk.changed_lines)
        mapped[f"{hunk.file_path}:{hunk.new_start}"] = nodes
    return mapped


def nodes_for_changed_lines(store: GraphStore, file_path: str, lines: list[int]) -> list[Node]:
    if not lines:
        return []
    rows = store.connection.execute(
        """
        SELECT * FROM nodes
        WHERE file_path = ?
          AND line_start IS NOT NULL
          AND line_end IS NOT NULL
        ORDER BY line_start DESC
        """,
        (file_path,),
    ).fetchall()
    matched: dict[str, Node] = {}
    for row in rows:
        node = store._row_to_node(row)
        if node.type == "file":
            continue
        start = node.line_start or 0
        end = node.line_end or start
        if any(start <= line <= end for line in lines):
            matched[node.id] = node
    return sorted(matched.values(), key=lambda node: (node.file_path or "", node.line_start or 0))
