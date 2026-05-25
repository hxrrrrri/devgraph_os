"""Refactor intelligence placeholder."""

from __future__ import annotations

from devgraph.core.graph_store import GraphStore


def refactor_context(store: GraphStore, query: str) -> str:
    nodes = store.find_nodes(query, limit=10)
    return "\n".join(f"- {node.qualified_name}" for node in nodes)
