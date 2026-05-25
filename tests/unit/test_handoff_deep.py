from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.handoff import HandoffEngine
from devgraph.update.incremental import build_graph


def test_handoff_includes_continue_section_and_memories(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("# TODO inspect\ndef main():\n    return True\n", encoding="utf-8")
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    store.remember("decision", "Use local-only search")
    markdown, data = HandoffEngine(tmp_path, DevGraphConfig(), store).generate()
    text = markdown.read_text(encoding="utf-8")
    assert "Continue from here" in text
    assert "Use local-only search" in text
    assert data.exists()
