"""Ignore matching for project scanning."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from devgraph.constants import DEFAULT_EXCLUDES, DEFAULT_IGNORE_FILE


class IgnoreMatcher:
    def __init__(self, root: Path, patterns: list[str] | None = None, respect_gitignore: bool = True) -> None:
        self.root = root.resolve()
        self.patterns = list(DEFAULT_EXCLUDES)
        self.patterns.extend(patterns or [])
        self.patterns.extend(self._read_ignore_file(root / DEFAULT_IGNORE_FILE))
        if respect_gitignore:
            self.patterns.extend(self._read_ignore_file(root / ".gitignore"))

    def ignored(self, path: Path) -> bool:
        rel = path.resolve().relative_to(self.root).as_posix()
        if rel == ".":
            return False
        for pattern in self.patterns:
            normalized = pattern.strip()
            if not normalized or normalized.startswith("#"):
                continue
            if normalized.endswith("/"):
                normalized = f"{normalized}**"
            if fnmatch.fnmatch(rel, normalized) or fnmatch.fnmatch(path.name, normalized):
                return True
            if "/" not in normalized and any(fnmatch.fnmatch(part, normalized) for part in rel.split("/")):
                return True
        return False

    @staticmethod
    def _read_ignore_file(path: Path) -> list[str]:
        if not path.exists():
            return []
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

