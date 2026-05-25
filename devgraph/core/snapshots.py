"""Snapshot helpers for future graph snapshots."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.graph_store import GraphStore


def create_snapshot(store: GraphStore, name: str) -> Path:
    target = store.storage_path / "snapshots" / f"{name}.json"
    store.write_json_export(target)
    return target
