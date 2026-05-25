from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_secret_values_do_not_leak_from_code_chunks(tmp_path: Path) -> None:
    path = tmp_path / "app.py"
    path.write_text('API_KEY = "secret-value"\ndef main():\n    return API_KEY\n', encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert all("secret-value" not in chunk.content for chunk in result.chunks)
