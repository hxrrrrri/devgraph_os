"""Integration test: build graph from the python_fastapi_service fixture.

Verifies the cross-product of P1 (tree-sitter Python), P2 (FastAPI route
extractor), and SQL table extraction against a realistic small repo.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "repos" / "python_fastapi_service"


def _copy_fixture(dest: Path) -> Path:
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def test_fastapi_routes_extracted_from_fixture(tmp_path: Path) -> None:
    registry = ExtractorRegistry(DevGraphConfig())
    repo = _copy_fixture(tmp_path / "svc")

    main_result = registry.extract(repo, repo / "app" / "main.py")
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"))
        for node in main_result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/health") in endpoints
    assert ("POST", "/login") in endpoints

    users_result = registry.extract(repo, repo / "app" / "users.py")
    users_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"))
        for node in users_result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/") in users_endpoints
    assert ("GET", "/{user_id}") in users_endpoints
    assert ("POST", "/") in users_endpoints

    sql_result = registry.extract(repo, repo / "migrations" / "0001_initial.sql")
    tables = {node.name for node in sql_result.nodes if node.type == "database_table"}
    assert "users" in tables


def test_fastapi_fixture_cli_build_and_status(tmp_path: Path, monkeypatch) -> None:
    repo = _copy_fixture(tmp_path / "svc")
    monkeypatch.chdir(repo)
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    build = runner.invoke(app, ["build"])
    assert build.exit_code == 0, build.output

    status = runner.invoke(app, ["status", "--json"])
    assert status.exit_code == 0, status.output
    assert '"total_files"' in status.output
    assert '"python"' in status.output

    explain = runner.invoke(app, ["explain", "app/main.py"])
    assert explain.exit_code == 0, explain.output
