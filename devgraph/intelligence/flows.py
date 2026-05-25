"""Flow tracing helpers."""

from __future__ import annotations

from devgraph.core.graph_store import GraphStore


def trace_flow(store: GraphStore, query: str) -> dict[str, object]:
    seeds = store.find_nodes(query, limit=3)
    if not seeds:
        return {"nodes": [], "edges": []}
    return store.get_neighborhood([node.id for node in seeds], depth=2, limit=100)

