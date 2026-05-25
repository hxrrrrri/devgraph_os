from pathlib import Path

from devgraph.server.http_server import DevGraphHttpHandler


def test_http_path_traversal_protection(tmp_path: Path) -> None:
    handler = DevGraphHttpHandler.__new__(DevGraphHttpHandler)
    handler.root = tmp_path
    assert handler._safe_relative_path("../secret.txt") is None
    safe = tmp_path / "app.py"
    safe.write_text("", encoding="utf-8")
    assert handler._safe_relative_path("app.py") == "app.py"
