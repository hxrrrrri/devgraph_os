"""Hybrid search facade."""

from __future__ import annotations

from typing import Any

from devgraph.core.graph_store import GraphStore


def search_graph(store: GraphStore, query: str, limit: int = 20) -> dict[str, Any]:
    return store.search(query, limit=limit)
