"""JSON graph export."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.graph_store import GraphStore


def export_json(store: GraphStore, output: Path | None = None) -> Path:
    target = output or (store.storage_path / "exports" / "graph.json")
    store.write_json_export(target)
    return target

