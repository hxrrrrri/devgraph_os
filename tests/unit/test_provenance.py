from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.update.incremental import build_graph


def test_provenance_recorded_for_nodes_and_chunks(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def main():\n    return True\n", encoding="utf-8")
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    node = store.find_nodes("main", limit=1)[0]
    assert store.provenance_for_entity(node.id)
    chunk_id = store.get_chunks_for_file("app.py")[0].id
    assert store.provenance_for_entity(chunk_id)
