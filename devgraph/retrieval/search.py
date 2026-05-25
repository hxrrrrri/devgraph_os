"""Hybrid search facade."""

from __future__ import annotations

from typing import Any

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.retrieval.embeddings import semantic_search


def search_graph(
    store: GraphStore,
    query: str,
    limit: int = 20,
    config: DevGraphConfig | None = None,
) -> dict[str, Any]:
    payload = store.search(query, limit=limit)
    payload["semantic"] = semantic_search(store, query, limit=limit, config=config)
    return payload
