"""Neo4j CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

from devgraph.core.graph_store import GraphStore


def export_neo4j(store: GraphStore, output: Path | None = None) -> Path:
    target = output or (store.storage_path / "exports" / "neo4j")
    target.mkdir(parents=True, exist_ok=True)
    with (target / "nodes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id:ID", "type:LABEL", "name", "qualified_name", "file_path"])
        for row in store.connection.execute("SELECT id, type, name, qualified_name, file_path FROM nodes"):
            writer.writerow([row["id"], row["type"], row["name"], row["qualified_name"], row["file_path"]])
    with (target / "edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([":START_ID", ":END_ID", ":TYPE", "id"])
        for row in store.connection.execute("SELECT id, source_id, target_id, type FROM edges"):
            writer.writerow([row["source_id"], row["target_id"], row["type"], row["id"]])
    return target

