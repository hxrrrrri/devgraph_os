"""Focused chunking for retrieval and context packs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from devgraph.constants import SECRET_KEY_HINTS
from devgraph.core.ids import chunk_id, content_hash
from devgraph.core.schema import Chunk, Node
from devgraph.retrieval.token_budget import estimate_tokens


@dataclass(frozen=True)
class LineWindow:
    kind: str
    line_start: int
    line_end: int
    node_id: str | None = None
    metadata: dict[str, object] | None = None


def chunk_code(file_path: str, text: str, nodes: list[Node]) -> list[Chunk]:
    """Create chunks around extracted code symbols with generic fallbacks."""
    lines = text.splitlines()
    windows: list[LineWindow] = []
    for node in nodes:
        if node.file_path != file_path:
            continue
        if node.type not in {"class", "function", "test", "type", "api_endpoint", "module"}:
            continue
        if not node.line_start:
            continue
        start = max(1, node.line_start)
        end = max(start, node.line_end or start)
        if node.type == "api_endpoint" and start == end:
            end = min(len(lines), start + 8)
        windows.append(
            LineWindow(
                kind=f"code:{node.type}",
                line_start=start,
                line_end=end,
                node_id=node.id,
                metadata={
                    "qualified_name": node.qualified_name,
                    "node_type": node.type,
                    "provenance": node.metadata.get("parser", node.confidence_tier),
                    "confidence_tier": node.confidence_tier,
                },
            )
        )
    if not windows:
        windows = _line_windows(len(lines), kind="code:window", max_lines=80)
    return _materialize(file_path, lines, windows)


def chunk_markdown(file_path: str, text: str, section_nodes: list[Node]) -> list[Chunk]:
    lines = text.splitlines()
    sections = sorted(
        [
            node
            for node in section_nodes
            if node.file_path == file_path and node.type in {"document", "section"} and node.line_start
        ],
        key=lambda node: node.line_start or 1,
    )
    windows: list[LineWindow] = []
    headings = [node for node in sections if node.type == "section"]
    if headings:
        for index, node in enumerate(headings):
            start = node.line_start or 1
            next_start = headings[index + 1].line_start if index + 1 < len(headings) else None
            end = (next_start - 1) if next_start else len(lines)
            windows.append(
                LineWindow(
                    kind="document:section",
                    line_start=start,
                    line_end=max(start, end),
                    node_id=node.id,
                    metadata={
                        "heading": node.name,
                        "level": node.metadata.get("level"),
                        "provenance": "markdown-heading",
                    },
                )
            )
    else:
        windows = _line_windows(len(lines), kind="document:window", max_lines=80)
    return _materialize(file_path, lines, windows)


def chunk_config(file_path: str, text: str, node: Node | None = None) -> list[Chunk]:
    lines = text.splitlines()
    windows = _top_level_key_windows(lines)
    if not windows:
        windows = _line_windows(len(lines), kind="config:window", max_lines=80)
    enriched = [
        LineWindow(
            kind=window.kind,
            line_start=window.line_start,
            line_end=window.line_end,
            node_id=node.id if node else None,
            metadata={**(window.metadata or {}), "provenance": "config-keys"},
        )
        for window in windows
    ]
    return _materialize(file_path, lines, enriched)


def chunk_sql(file_path: str, text: str, node: Node | None = None) -> list[Chunk]:
    lines = text.splitlines()
    windows: list[LineWindow] = []
    start = 1
    for index, line in enumerate(lines, start=1):
        if ";" in line:
            windows.append(
                LineWindow(
                    kind="sql:statement",
                    line_start=start,
                    line_end=index,
                    node_id=node.id if node else None,
                    metadata={"provenance": "sql-statement"},
                )
            )
            start = index + 1
    if start <= len(lines):
        windows.append(
            LineWindow(
                kind="sql:statement",
                line_start=start,
                line_end=len(lines),
                node_id=node.id if node else None,
                metadata={"provenance": "sql-statement"},
            )
        )
    return _materialize(file_path, lines, windows or _line_windows(len(lines), "sql:window", 80))


def chunk_text(file_path: str, text: str, node: Node | None = None, kind: str = "text") -> list[Chunk]:
    lines = text.splitlines()
    return _materialize(
        file_path,
        lines,
        [
            LineWindow(
                kind=f"{kind}:window",
                line_start=window.line_start,
                line_end=window.line_end,
                node_id=node.id if node else None,
                metadata={"provenance": "line-window"},
            )
            for window in _line_windows(len(lines), f"{kind}:window", 80)
        ],
    )


def _line_windows(line_count: int, kind: str, max_lines: int) -> list[LineWindow]:
    count = max(1, line_count)
    windows: list[LineWindow] = []
    start = 1
    while start <= count:
        end = min(count, start + max_lines - 1)
        windows.append(LineWindow(kind=kind, line_start=start, line_end=end))
        start = end + 1
    return windows


def _top_level_key_windows(lines: list[str]) -> list[LineWindow]:
    key_lines: list[tuple[int, str]] = []
    key_re = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*[:=]")
    for index, line in enumerate(lines, start=1):
        if line.startswith((" ", "\t", "#")):
            continue
        match = key_re.match(line)
        if match:
            key_lines.append((index, match.group(1)))
    windows: list[LineWindow] = []
    for idx, (start, key) in enumerate(key_lines):
        next_start = key_lines[idx + 1][0] if idx + 1 < len(key_lines) else len(lines) + 1
        windows.append(
            LineWindow(
                kind="config:key",
                line_start=start,
                line_end=max(start, next_start - 1),
                metadata={"key": key},
            )
        )
    return windows


def _materialize(file_path: str, lines: list[str], windows: list[LineWindow]) -> list[Chunk]:
    chunks: list[Chunk] = []
    line_count = max(1, len(lines))
    for window in windows:
        start = max(1, min(window.line_start, line_count))
        end = max(start, min(window.line_end, line_count))
        content = _redact_secret_like("\n".join(lines[start - 1 : end]))
        if not content.strip():
            continue
        chunks.append(
            Chunk(
                id=chunk_id(file_path, start, end, content),
                file_path=file_path,
                node_id=window.node_id,
                kind=window.kind,
                content=content,
                line_start=start,
                line_end=end,
                token_estimate=estimate_tokens(content),
                content_hash=content_hash(content),
                metadata=window.metadata or {},
            )
        )
    return chunks


def _redact_secret_like(text: str) -> str:
    safe_lines: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if any(hint in lower for hint in SECRET_KEY_HINTS):
            if "=" in line:
                safe_lines.append(f"{line.split('=', 1)[0].strip()}=<redacted>")
            elif ":" in line:
                safe_lines.append(f"{line.split(':', 1)[0].strip()}: <redacted>")
            else:
                safe_lines.append("<redacted secret-like line>")
        else:
            safe_lines.append(line)
    return "\n".join(safe_lines)
