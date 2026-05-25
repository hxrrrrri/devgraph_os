"""GraphML export."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from devgraph.core.graph_store import GraphStore


def export_graphml(store: GraphStore, output: Path | None = None) -> Path:
    target = output or (store.storage_path / "exports" / "graph.graphml")
    target.parent.mkdir(parents=True, exist_ok=True)
    graph = nx.DiGraph()
    for row in store.connection.execute("SELECT * FROM nodes").fetchall():
        graph.add_node(row["id"], type=row["type"], name=row["name"], qualified_name=row["qualified_name"])
    for row in store.connection.execute("SELECT * FROM edges").fetchall():
        graph.add_edge(row["source_id"], row["target_id"], type=row["type"], id=row["id"])
    nx.write_graphml(graph, target)
    return target

