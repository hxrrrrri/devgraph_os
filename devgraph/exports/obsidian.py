"""Obsidian export."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.graph_store import GraphStore


def export_obsidian(store: GraphStore, output: Path | None = None) -> Path:
    target = output or (store.storage_path / "exports" / "obsidian")
    target.mkdir(parents=True, exist_ok=True)
    rows = store.connection.execute(
        "SELECT qualified_name, type, file_path, summary FROM nodes ORDER BY qualified_name LIMIT 500"
    ).fetchall()
    for row in rows:
        safe_name = _safe_filename(row["qualified_name"])
        content = [
            f"# {row['qualified_name']}",
            "",
            f"- Type: {row['type']}",
            f"- File: {row['file_path'] or 'external'}",
            "",
            row["summary"] or "No summary stored.",
        ]
        (target / f"{safe_name}.md").write_text("\n".join(content), encoding="utf-8")
    return target


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)[:120]

