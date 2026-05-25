"""Integration test: build graph from the react_next_app fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "repos" / "react_next_app"


def _copy_fixture(dest: Path) -> Path:
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def test_nextjs_app_and_pages_routes_extracted_from_fixture(tmp_path: Path) -> None:
    registry = ExtractorRegistry(DevGraphConfig())
    repo = _copy_fixture(tmp_path / "site")

    home = registry.extract(repo, repo / "app" / "page.tsx")
    assert any(
        node.type == "api_endpoint"
        and node.metadata.get("framework") == "nextjs"
        and node.metadata.get("path") == "/"
        for node in home.nodes
    )

    user = registry.extract(repo, repo / "app" / "users" / "[id]" / "page.tsx")
    user_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in user.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/users/[id]", "nextjs") in user_endpoints

    health = registry.extract(repo, repo / "app" / "api" / "health" / "route.ts")
    health_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in health.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/api/health", "nextjs") in health_endpoints
    assert ("POST", "/api/health", "nextjs") in health_endpoints

    legacy_index = registry.extract(repo, repo / "pages" / "index.tsx")
    legacy_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in legacy_index.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/", "nextjs") in legacy_endpoints

    version = registry.extract(repo, repo / "pages" / "api" / "version.ts")
    version_endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in version.nodes
        if node.type == "api_endpoint"
    }
    assert ("ANY", "/api/version", "nextjs") in version_endpoints

    app_shell = registry.extract(repo, repo / "pages" / "_app.tsx")
    assert not any(node.type == "api_endpoint" for node in app_shell.nodes)


def test_nextjs_fixture_cli_build(tmp_path: Path, monkeypatch) -> None:
    repo = _copy_fixture(tmp_path / "site")
    monkeypatch.chdir(repo)
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    build = runner.invoke(app, ["build"])
    assert build.exit_code == 0, build.output

    status = runner.invoke(app, ["status", "--json"])
    assert status.exit_code == 0, status.output
    assert '"total_files"' in status.output
