from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest
from devgraph.update.incremental import build_graph


def test_context_pack_uses_readable_graph_paths_and_line_ranges(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def a():\n    return b()\n\ndef b():\n    return True\n", encoding="utf-8")
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    pack = ContextPacker(store).pack(ContextRequest(task_type="explain", query="a", token_budget="deep"))
    graph_section = pack.split("## Graph paths", 1)[1].split("## Changed code snippets", 1)[0]
    assert "function:" not in graph_section
    assert "app.a" in pack or "app.py::a" in pack
    assert "lines" in pack
