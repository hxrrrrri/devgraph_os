from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_external_like_document_extraction_redacts_secrets(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# Notes\napi_key: secret\n", encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert "secret" not in result.chunks[0].content
    assert any(node.type == "document" for node in result.nodes)
