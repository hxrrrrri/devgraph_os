from pathlib import Path

from devgraph.core.graph_store import GraphStore


def test_migrations_create_required_tables(tmp_path: Path) -> None:
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    tables = {
        row["name"]
        for row in store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')"
        ).fetchall()
    }
    assert "files" in tables
    assert "nodes" in tables
    assert "edges" in tables
    assert "chunks" in tables
    assert "nodes_fts" in tables
    store.close()

