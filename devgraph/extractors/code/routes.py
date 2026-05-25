"""Route extraction helpers."""

from __future__ import annotations

import re

ROUTE_RE = re.compile(
    r"\b(?:app|router|server)\.(get|post|put|patch|delete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


def parse_js_ts_routes(text: str) -> list[tuple[str, str, int]]:
    offsets = _line_offsets(text)
    routes: list[tuple[str, str, int]] = []
    for match in ROUTE_RE.finditer(text):
        routes.append((match.group(1).upper(), match.group(2), _line_for_offset(offsets, match.start())))
    return routes


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

