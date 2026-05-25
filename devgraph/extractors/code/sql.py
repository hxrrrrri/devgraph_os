"""SQL extraction helpers."""

from __future__ import annotations

import re

SQL_TABLE_RE = re.compile(
    r"\b(?P<action>FROM|JOIN|UPDATE|INTO|TABLE)\s+[`\"[]?(?P<table>[A-Za-z_][\w.$-]*)",
    re.IGNORECASE,
)
SQL_CREATE_TABLE_RE = re.compile(
    r"\bCREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"[]?(?P<table>[A-Za-z_][\w.$-]*)",
    re.IGNORECASE,
)


def extract_table_references(text: str) -> list[tuple[str, str, int]]:
    references: list[tuple[str, str, int]] = []
    line_offsets = _line_offsets(text)
    for match in SQL_CREATE_TABLE_RE.finditer(text):
        references.append(("writes_to", match.group("table").strip("`\"[]"), _line_for_offset(line_offsets, match.start())))
    for match in SQL_TABLE_RE.finditer(text):
        action = match.group("action").upper()
        table = match.group("table").strip("`\"[]")
        edge = "writes_to" if action in {"UPDATE", "INTO", "TABLE"} else "reads_from"
        references.append((edge, table, _line_for_offset(line_offsets, match.start())))
    deduped: dict[tuple[str, str, int], tuple[str, str, int]] = {}
    for item in references:
        deduped[item] = item
    return list(deduped.values())


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
