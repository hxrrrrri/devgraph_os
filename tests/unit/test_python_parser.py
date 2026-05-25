from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_python_parser_extracts_import_call_class_and_test(tmp_path: Path) -> None:
    path = tmp_path / "test_auth.py"
    path.write_text(
        "import os\n\nclass AuthService:\n    def login(self):\n        return helper()\n\ndef helper():\n    return True\n\ndef test_login():\n    assert helper()\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    names = {node.name for node in result.nodes}
    assert {"AuthService", "login", "helper", "test_login"} <= names
    assert any(edge.type == "imports" for edge in result.edges)
    assert any(edge.type == "calls" for edge in result.edges)
    assert any(node.type == "test" for node in result.nodes)
