from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import classify_file
from devgraph.update.ignore import IgnoreMatcher
from devgraph.update.incremental import scan_files


def test_classify_file() -> None:
    assert classify_file(Path("src/auth.py")) == ("code", "python")
    assert classify_file(Path("docs/README.md")) == ("document", "markdown")
    assert classify_file(Path(".env")) == ("config", "env")


def test_ignore_rules_skip_node_modules(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src" / "app.py").write_text("def main(): pass", encoding="utf-8")
    (tmp_path / "node_modules" / "pkg.js").write_text("export {}", encoding="utf-8")
    files = [path.relative_to(tmp_path).as_posix() for path in scan_files(tmp_path, DevGraphConfig())]
    assert "src/app.py" in files
    assert "node_modules/pkg.js" not in files
    assert IgnoreMatcher(tmp_path).ignored(tmp_path / "node_modules" / "pkg.js")

