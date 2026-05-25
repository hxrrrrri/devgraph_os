import json
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.extractors.registry import ExtractorRegistry
from devgraph.intelligence.review import ReviewEngine
from devgraph.update.incremental import build_graph


def test_graph_records_provenance_snapshots_memories_and_test_links(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    (tmp_path / "tests" / "test_auth.py").write_text(
        "from src.auth import login\n\n"
        "def test_login():\n"
        "    assert login()\n",
        encoding="utf-8",
    )
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")

    stats = build_graph(tmp_path, config, store, force=True)
    assert stats.indexed == 2
    assert (tmp_path / ".devgraph" / "snapshots" / "latest.json").exists()
    assert store.connection.execute("SELECT COUNT(*) FROM provenance").fetchone()[0] > 0

    memory_id = store.remember("decision", "API_TOKEN=do-not-store")
    memories = store.list_memories()
    assert memory_id == memories[0]["id"]
    assert "do-not-store" not in memories[0]["content"]

    login_nodes = store.find_nodes("login")
    tests = store.tests_for_nodes([node.id for node in login_nodes])
    assert any(test.name == "test_login" for test in tests)


def test_review_engine_can_scope_files_without_git_diff(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, config, store, force=True)

    result = ReviewEngine(tmp_path, config, store).review(files=["src/auth.py"])

    assert result.changed_files == ["src/auth.py"]
    assert result.diff_summary
    assert "Current file excerpt" in result.changed_snippets["src/auth.py"]
    assert result.warnings


def test_static_language_extractors_find_symbols_and_imports(tmp_path: Path) -> None:
    samples = {
        "main.go": 'package main\nimport "fmt"\nfunc Login() bool { return true }\n',
        "lib.rs": "use std::io;\npub fn login() -> bool { true }\nstruct Session {}\n",
        "Auth.java": "import java.util.List;\npublic class Auth { public boolean login() { return true; } }\n",
    }
    registry = ExtractorRegistry(DevGraphConfig())
    for filename, text in samples.items():
        path = tmp_path / filename
        path.write_text(text, encoding="utf-8")
        result = registry.extract(tmp_path, path)
        assert any(node.type in {"function", "class", "type"} for node in result.nodes), filename
        assert any(edge.type == "imports" for edge in result.edges), filename


def test_cli_doctor_memories_and_review_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    (tmp_path / "src" / "service.py").write_text("def health():\n    return 'ok'\n", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["build"]).exit_code == 0

    remember = runner.invoke(
        app,
        ["remember", "--kind", "decision", "We use SQLite as the local graph store."],
    )
    assert remember.exit_code == 0, remember.output
    memory_id = remember.output.strip()

    memories = runner.invoke(app, ["memories", "--json"])
    assert memories.exit_code == 0, memories.output
    assert json.loads(memories.output)[0]["id"] == memory_id

    doctor = runner.invoke(app, ["doctor", "--json"])
    assert doctor.exit_code == 0, doctor.output
    assert json.loads(doctor.output)["issues"] == []

    review = runner.invoke(app, ["review", "--json", "--files", "src/auth.py", "src/service.py"])
    assert review.exit_code == 0, review.output
    assert json.loads(review.output)["changed_files"] == ["src/auth.py", "src/service.py"]

    forget = runner.invoke(app, ["forget", memory_id])
    assert forget.exit_code == 0, forget.output
