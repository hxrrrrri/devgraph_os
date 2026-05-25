from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_typescript_parser_extracts_symbols_imports_and_express_route(tmp_path: Path) -> None:
    path = tmp_path / "server.ts"
    path.write_text(
        "import express from 'express';\nexport class Auth {}\nexport function login() { return true; }\nrouter.post('/login', login);\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert any(node.name == "Auth" and node.type == "class" for node in result.nodes)
    assert any(node.name == "login" for node in result.nodes)
    assert any(node.name == "POST /login" and node.type == "api_endpoint" for node in result.nodes)
    assert any(edge.type == "imports" for edge in result.edges)


def test_tsx_component_is_chunked(tmp_path: Path) -> None:
    path = tmp_path / "Button.tsx"
    path.write_text("export const Button = () => <button>Save</button>;\n", encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert any(node.name == "Button" for node in result.nodes)
    assert result.chunks
