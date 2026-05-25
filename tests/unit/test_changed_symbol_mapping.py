from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.update.diff_parser import DiffHunk, map_hunks_to_nodes
from devgraph.update.incremental import build_graph


def test_changed_symbol_mapping_uses_line_ranges(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def login():\n    return True\n\ndef other():\n    return False\n", encoding="utf-8")
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    mapped = map_hunks_to_nodes(store, [DiffHunk("app.py", 1, 1, 2, 1, [2], "+    return False")])
    assert any(node.name == "login" for nodes in mapped.values() for node in nodes)
