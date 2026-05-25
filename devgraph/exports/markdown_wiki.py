"""Markdown wiki generation."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.graph_store import GraphStore


def generate_wiki(store: GraphStore) -> Path:
    root = store.storage_path / "wiki"
    for child in ["communities", "flows", "files", "symbols", "docs"]:
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
    index_lines = [
        "# DevGraph Wiki",
        "",
        "- [[architecture]]",
        "- [[flows]]",
        "- [[decisions]]",
        "- [[review]]",
        "",
        "## Files",
    ]
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
    symbol_rows = store.connection.execute(
        """
        SELECT qualified_name, type, file_path, line_start, line_end
        FROM nodes
        WHERE type IN ('module', 'class', 'function', 'test', 'api_endpoint', 'database_table', 'config')
        ORDER BY qualified_name
        LIMIT 500
        """
    ).fetchall()
    architecture_lines = ["# Architecture", "", "## Key Symbols"]
    for row in symbol_rows:
        filename = _safe_filename(row["qualified_name"])
        architecture_lines.append(f"- [[symbols/{filename}|{row['qualified_name']}]]")
        (root / "symbols" / f"{filename}.md").write_text(
            "\n".join(
                [
                    f"# {row['qualified_name']}",
                    "",
                    f"- Type: {row['type']}",
                    f"- File: [[files/{_safe_filename(row['file_path'] or 'external')}|{row['file_path'] or 'external'}]]",
                    f"- Lines: {row['line_start']}-{row['line_end']}",
                    "",
                    "## Backlinks",
                    "- [[architecture]]",
                ]
            ),
            encoding="utf-8",
        )
    flow_rows = store.connection.execute(
        """
        SELECT e.type, source.qualified_name AS source, target.qualified_name AS target
        FROM edges e
        JOIN nodes source ON source.id = e.source_id
        JOIN nodes target ON target.id = e.target_id
        WHERE e.type IN ('calls', 'routes_to', 'reads_from', 'writes_to', 'depends_on')
        LIMIT 300
        """
    ).fetchall()
    flow_lines = ["# Flows", ""]
    for row in flow_rows:
        flow_lines.append(f"- `{row['source']}` --{row['type']}--> `{row['target']}`")
    memory_rows = store.list_memories(limit=100)
    decision_lines = ["# Decisions", ""]
    for memory in memory_rows:
        if memory["kind"] in {"decision", "accepted_solution", "rejected_attempt", "task"}:
            decision_lines.append(f"- **{memory['kind']}**: {memory['content']}")
    review_path = store.storage_path / "reports" / "review.md"
    (root / "architecture.md").write_text("\n".join(architecture_lines), encoding="utf-8")
    (root / "flows.md").write_text("\n".join(flow_lines), encoding="utf-8")
    (root / "decisions.md").write_text("\n".join(decision_lines), encoding="utf-8")
    (root / "review.md").write_text(
        review_path.read_text(encoding="utf-8") if review_path.exists() else "# Review\n\nNo review artifact generated yet.",
        encoding="utf-8",
    )
    (root / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    return root / "index.md"


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)[:120]
