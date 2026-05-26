"""Integration test: mixed_docs_config_repo fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "repos" / "mixed_docs_config_repo"


def _copy_fixture(dest: Path) -> Path:
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def test_mixed_repo_non_code_extractors_produce_nodes(tmp_path: Path) -> None:
    registry = ExtractorRegistry(DevGraphConfig())
    repo = _copy_fixture(tmp_path / "site")

    md = registry.extract(repo, repo / "docs" / "overview.md")
    assert any(node.type == "section" for node in md.nodes)

    rst = registry.extract(repo, repo / "docs" / "contributing.rst")
    assert rst.nodes  # at least a file node

    yaml = registry.extract(repo, repo / "config" / "app.yaml")
    assert yaml.nodes

    toml = registry.extract(repo, repo / "config" / "pyproject.toml")
    assert toml.nodes

    env = registry.extract(repo, repo / ".env")
    assert env.nodes

    dockerfile = registry.extract(repo, repo / "Dockerfile")
    assert dockerfile.nodes


def test_mixed_repo_cli_build(tmp_path: Path, monkeypatch) -> None:
    repo = _copy_fixture(tmp_path / "site")
    monkeypatch.chdir(repo)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["build"]).exit_code == 0
