"""Import parsing helpers for regex-backed languages."""

from __future__ import annotations

import re

IMPORT_RE = re.compile(
    r"^\s*(?:import\s+(?:.+?\s+from\s+)?[\"']([^\"']+)[\"']|"
    r"import\s+[\"']([^\"']+)[\"']|"
    r"const\s+\w+\s*=\s*require\([\"']([^\"']+)[\"']\))",
    re.MULTILINE,
)


def parse_js_ts_imports(text: str) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    line_offsets = _line_offsets(text)
    for match in IMPORT_RE.finditer(text):
        module = next(group for group in match.groups() if group)
        imports.append((module, _line_for_offset(line_offsets, match.start())))
    return imports


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _line_for_offset(offsets: list[int], offset: int) -> int:
    line = 1
    for item in offsets:
        if item <= offset:
            line += 1
        else:
            break
    return max(1, line - 1)

