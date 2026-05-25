"""Language metadata."""

from __future__ import annotations

from pathlib import Path

from devgraph.constants import SUPPORTED_CODE_EXTENSIONS


def language_for_path(path: Path) -> str | None:
    return SUPPORTED_CODE_EXTENSIONS.get(path.suffix.lower())


TREE_SITTER_LANGUAGE_NAMES = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "csharp": "csharp",
    "ruby": "ruby",
    "php": "php",
    "kotlin": "kotlin",
    "swift": "swift",
    "scala": "scala",
    "dart": "dart",
    "lua": "lua",
    "bash": "bash",
}
