"""Integration test: build graph from the ts_nestjs_app fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "repos" / "ts_nestjs_app"


def _copy_fixture(dest: Path) -> Path:
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def test_nestjs_routes_extracted_from_fixture(tmp_path: Path) -> None:
    registry = ExtractorRegistry(DevGraphConfig())
    repo = _copy_fixture(tmp_path / "svc")

    users_result = registry.extract(repo, repo / "src" / "users" / "users.controller.ts")
    users_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in users_result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/users", "nestjs") in users_endpoints
    assert ("GET", "/users/:id", "nestjs") in users_endpoints
    assert ("POST", "/users", "nestjs") in users_endpoints
    assert ("PATCH", "/users/:id", "nestjs") in users_endpoints
    assert ("DELETE", "/users/:id", "nestjs") in users_endpoints

    auth_result = registry.extract(repo, repo / "src" / "auth" / "auth.controller.ts")
    auth_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in auth_result.nodes
        if node.type == "api_endpoint"
    }
    assert ("POST", "/auth/login", "nestjs") in auth_endpoints
    assert ("POST", "/auth/logout", "nestjs") in auth_endpoints


def test_nestjs_fixture_cli_build_and_status(tmp_path: Path, monkeypatch) -> None:
    repo = _copy_fixture(tmp_path / "svc")
    monkeypatch.chdir(repo)
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    build = runner.invoke(app, ["build"])
    assert build.exit_code == 0, build.output

    status = runner.invoke(app, ["status", "--json"])
    assert status.exit_code == 0, status.output
    assert '"total_files"' in status.output
    assert '"typescript"' in status.output
