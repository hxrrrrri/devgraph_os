"""Markdown wiki generation."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.graph_store import GraphStore


def generate_wiki(store: GraphStore) -> Path:
    root = store.storage_path / "wiki"
    for child in ["communities", "flows", "files"]:
        (root / child).mkdir(parents=True, exist_ok=True)
    file_rows = store.connection.execute(
        """
        SELECT f.path, f.language, COUNT(n.id) AS node_count
        FROM files f
        LEFT JOIN nodes n ON n.file_path = f.path
        WHERE f.is_deleted = 0
        GROUP BY f.path
        ORDER BY f.path
        """
    ).fetchall()
    index_lines = ["# DevGraph Wiki", "", "## Files"]
    for row in file_rows:
        filename = _safe_filename(row["path"])
        index_lines.append(f"- [{row['path']}](files/{filename}.md)")
        (root / "files" / f"{filename}.md").write_text(
            "\n".join(
                [
                    f"# {row['path']}",
                    "",
                    f"- Language: {row['language'] or 'unknown'}",
                    f"- Node count: {row['node_count']}",
                ]
            ),
            encoding="utf-8",
        )
    (root / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    return root / "index.md"


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)[:120]

