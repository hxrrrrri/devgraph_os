"""Call parsing helpers."""

from __future__ import annotations

import re

CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\s*\(")
IGNORED_CALLS = {"if", "for", "while", "switch", "catch", "function", "return"}


def parse_js_ts_calls(text: str) -> list[tuple[str, int]]:
    offsets = _line_offsets(text)
    calls: list[tuple[str, int]] = []
    for match in CALL_RE.finditer(text):
        name = match.group(1)
        if name in IGNORED_CALLS:
            continue
        calls.append((name, _line_for_offset(offsets, match.start())))
    return calls


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

