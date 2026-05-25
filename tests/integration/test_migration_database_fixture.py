"""Integration test: migration_database_repo fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app
from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "repos" / "migration_database_repo"


def _copy_fixture(dest: Path) -> Path:
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def test_alembic_prisma_and_sql_extracted(tmp_path: Path) -> None:
    registry = ExtractorRegistry(DevGraphConfig())
    repo = _copy_fixture(tmp_path / "db")

    alembic_init = registry.extract(repo, repo / "migrations" / "alembic" / "20240101_init.py")
    ops = {
        (node.metadata.get("operation"), node.metadata.get("target"), node.metadata.get("framework"))
        for node in alembic_init.nodes
        if node.type == "schema" and node.metadata.get("framework") == "alembic"
    }
    assert ("create_table", "users", "alembic") in ops
    assert ("create_table", "posts", "alembic") in ops
    assert ("create_index", "ix_posts_user_id", "alembic") in ops

    add_role = registry.extract(repo, repo / "migrations" / "alembic" / "20240202_add_role.py")
    role_ops = {
        (node.metadata.get("operation"), node.metadata.get("target"))
        for node in add_role.nodes
        if node.type == "schema" and node.metadata.get("framework") == "alembic"
    }
    assert ("add_column", "users") in role_ops
    assert ("alter_column", "users") in role_ops

    sql_result = registry.extract(repo, repo / "migrations" / "sql" / "0003_audit_log.sql")
    tables = {node.name for node in sql_result.nodes if node.type == "database_table"}
    assert "audit_log" in tables

    prisma = registry.extract(repo, repo / "prisma" / "schema.prisma")
    prisma_models = {
        node.name for node in prisma.nodes if node.type == "schema" and node.metadata.get("framework") == "prisma"
    }
    assert {"User", "Post"}.issubset(prisma_models)


def test_migration_repo_cli_build(tmp_path: Path, monkeypatch) -> None:
    repo = _copy_fixture(tmp_path / "db")
    monkeypatch.chdir(repo)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["build"]).exit_code == 0
