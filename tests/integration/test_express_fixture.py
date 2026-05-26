"""Integration test: ts_express_app fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "repos" / "ts_express_app"


def _copy_fixture(dest: Path) -> Path:
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def test_express_routes_and_sql_extracted(tmp_path: Path) -> None:
    registry = ExtractorRegistry(DevGraphConfig())
    repo = _copy_fixture(tmp_path / "svc")

    app_result = registry.extract(repo, repo / "src" / "app.ts")
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in app_result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/health", "express") in endpoints
    assert ("GET", "/users", "express") in endpoints
    assert ("POST", "/users", "express") in endpoints

    sql_result = registry.extract(repo, repo / "sql" / "0001_users.sql")
    tables = {node.name for node in sql_result.nodes if node.type == "database_table"}
    assert "users" in tables


def test_express_fixture_cli_build_status(tmp_path: Path, monkeypatch) -> None:
    repo = _copy_fixture(tmp_path / "svc")
    monkeypatch.chdir(repo)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["build"]).exit_code == 0
    status = runner.invoke(app, ["status", "--json"])
    assert status.exit_code == 0
    assert '"typescript"' in status.output
    assert '"sql"' in status.output
