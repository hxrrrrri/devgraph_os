"""Knowledge graph helpers."""

from __future__ import annotations

from devgraph.core.graph_store import GraphStore


def stale_docs(store: GraphStore) -> list[str]:
    rows = store.connection.execute(
        "SELECT path FROM files WHERE category = 'document' AND is_deleted = 0 ORDER BY path"
    ).fetchall()
    return [row["path"] for row in rows]

