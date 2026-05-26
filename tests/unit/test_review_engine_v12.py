"""ReviewEngine v1.2 extensions: fan_out, severity maps, infra blast radius,
API compat + route contract diff vs snapshot.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.review import ReviewEngine
from devgraph.update.incremental import build_graph


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)


def test_review_emits_fan_out_and_severity_maps(tmp_path: Path) -> None:
    (tmp_path / "core.py").write_text(
        "def shared():\n    return 1\n"
        "def caller_a():\n    return shared() + 1\n"
        "def caller_b():\n    return shared() + 2\n",
        encoding="utf-8",
    )
    _init_git(tmp_path)
    (tmp_path / "core.py").write_text(
        "def shared(extra):\n    return 1 + extra\n"
        "def caller_a():\n    return shared(1) + 1\n"
        "def caller_b():\n    return shared(2) + 2\n",
        encoding="utf-8",
    )
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, config, store, force=True)
    engine = ReviewEngine(tmp_path, config, store)
    result = engine.review()
    assert isinstance(result.fan_out, list)
    assert isinstance(result.severity_by_file, dict)
    assert isinstance(result.severity_by_symbol, dict)


def test_review_infra_blast_radius_lists_changed_infra(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("API_TOKEN=value\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
    _init_git(tmp_path)
    (tmp_path / ".env").write_text("API_TOKEN=value2\nNEW_KEY=x\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\nRUN echo hi\n", encoding="utf-8")
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, config, store, force=True)
    engine = ReviewEngine(tmp_path, config, store)
    result = engine.review()
    categories = {entry["category"] for entry in result.infra_blast_radius}
    assert "env" in categories
    assert "docker" in categories


def test_review_uses_snapshot_for_api_and_route_diff(tmp_path: Path) -> None:
    (tmp_path / "api.py").write_text(
        "def fetch():\n    return 1\n",
        encoding="utf-8",
    )
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, config, store, force=True)
    snapshot_path = store.create_snapshot("baseline")
    _init_git(tmp_path)
    (tmp_path / "api.py").write_text(
        "def fetch(arg):\n    return arg\n",
        encoding="utf-8",
    )
    build_graph(tmp_path, config, store, force=True)
    engine = ReviewEngine(tmp_path, config, store)
    result = engine.review(previous_snapshot=snapshot_path)
    assert isinstance(result.api_signature_changes, list)
    assert isinstance(result.route_contract_changes, list)
