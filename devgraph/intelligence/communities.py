"""Community detection placeholder."""

from __future__ import annotations

from devgraph.core.graph_store import GraphStore


def top_communities(store: GraphStore, limit: int = 10) -> list[dict[str, object]]:
    rows = store.connection.execute(
        """
        SELECT COALESCE(file_path, type) AS name, COUNT(*) AS node_count
        FROM nodes
        GROUP BY COALESCE(file_path, type)
        ORDER BY node_count DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]

