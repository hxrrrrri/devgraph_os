from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_python_parser_extracts_symbols(tmp_path: Path) -> None:
    path = tmp_path / "auth.py"
    path.write_text(
        "class AuthService:\n"
        "    def login(self):\n"
        "        return validate_user()\n\n"
        "def validate_user():\n"
        "    return True\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    names = {node.name for node in result.nodes}
    assert "AuthService" in names
    assert "login" in names
    assert any(edge.type == "calls" for edge in result.edges)


def test_typescript_parser_extracts_route(tmp_path: Path) -> None:
    path = tmp_path / "server.ts"
    path.write_text(
        "import express from 'express';\n"
        "function login() { return true; }\n"
        "router.get('/login', login);\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert any(node.type == "api_endpoint" and node.name == "GET /login" for node in result.nodes)
    assert any(edge.type == "imports" for edge in result.edges)


def test_markdown_parser_extracts_sections(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("# Title\n\n## Auth\nDetails\n", encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert any(node.type == "section" and node.name == "Auth" for node in result.nodes)


def test_env_parser_redacts_values(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("API_KEY=secret-value\nDEBUG=true\n", encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert "secret-value" not in result.chunks[0].content
    assert "API_KEY=<redacted>" in result.chunks[0].content

