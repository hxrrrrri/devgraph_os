"""Snapshot helpers for future graph snapshots."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.graph_store import GraphStore


def create_snapshot(store: GraphStore, name: str) -> Path:
    return store.create_snapshot(name)
