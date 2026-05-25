from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.review import ReviewEngine
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest
from devgraph.update.incremental import build_graph, update_graph


def test_build_and_context_pack(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    stats = build_graph(tmp_path, config, store, force=True)
    assert stats.indexed == 1
    pack = ContextPacker(store).pack(ContextRequest(task_type="explain", query="login"))
    assert "login" in pack


def test_incremental_update_skips_unchanged(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    file_path = tmp_path / "src" / "auth.py"
    file_path.write_text("def login():\n    return True\n", encoding="utf-8")
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, config, store, force=False)
    stats = build_graph(tmp_path, config, store, force=False)
    assert stats.skipped == 1
    file_path.write_text("def login():\n    return False\n", encoding="utf-8")
    stats = update_graph(tmp_path, config, store)
    assert stats.indexed >= 1


def test_review_engine_returns_machine_readable_result(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, config, store, force=True)
    result = ReviewEngine(tmp_path, config, store).review(base=None, staged=False)
    assert result.risk_score >= 0
    assert isinstance(result.changed_files, list)

