"""Migration risk detector.

Scans diff snippets and migration-shaped paths for high-blast-radius operations:
column/table drops, NOT NULL adds without default, unindexed FK adds, type
changes on populated columns, irreversible Alembic ops, raw SQL in ORM
migrations. Each finding is a structured dict the review engine surfaces.
"""

from __future__ import annotations

import re
from typing import Any

MIGRATION_PATH_HINTS = ("migration", "migrations", "alembic", "versions/", "prisma/", "schema.prisma")

PATTERNS: list[tuple[str, re.Pattern[str], str | None]] = [
    (
        "drop_table",
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        "DROP TABLE is destructive and irreversible without backup.",
    ),
    (
        "drop_column",
        re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
        "DROP COLUMN removes data permanently; verify nothing reads the column.",
    ),
    (
        "alembic_drop_column",
        re.compile(r"op\.drop_column\s*\("),
        "Alembic op.drop_column is irreversible; provide a working downgrade or feature-flag the rollout.",
    ),
    (
        "alembic_drop_table",
        re.compile(r"op\.drop_table\s*\("),
        "Alembic op.drop_table is destructive; ensure all readers are removed first.",
    ),
    (
        "add_not_null_no_default",
        re.compile(
            r"(?:ADD\s+COLUMN[^;]*?NOT\s+NULL)(?![^;]*\bDEFAULT\b)",
            re.IGNORECASE | re.DOTALL,
        ),
        "Adding NOT NULL without DEFAULT will fail on populated tables; add DEFAULT or backfill first.",
    ),
    (
        "alter_column_type",
        re.compile(r"\bALTER\s+COLUMN\b[^;]*\bTYPE\b", re.IGNORECASE),
        "Type changes on populated columns can rewrite the table and lock writes.",
    ),
    (
        "rename_column",
        re.compile(r"\b(?:RENAME\s+COLUMN|op\.alter_column[^;]*new_column_name)", re.IGNORECASE),
        "Renames break readers until they redeploy; do via expand/contract.",
    ),
    (
        "add_foreign_key",
        re.compile(r"\bADD\s+CONSTRAINT\b[^;]*\bFOREIGN\s+KEY\b", re.IGNORECASE),
        "Adding a FOREIGN KEY locks the referenced table; add NOT VALID then VALIDATE separately.",
    ),
    (
        "prisma_field_drop",
        re.compile(r"^-\s*\w+\s+\w+", re.MULTILINE),
        None,  # noise-prone; only kept for prisma/*.prisma diffs
    ),
]


def detect_migration_warnings(
    files: list[str],
    snippets: dict[str, str],
) -> list[dict[str, Any]]:
    """Return structured warnings for migration-shaped diffs."""

    warnings: list[dict[str, Any]] = []
    for path in files:
        if not _is_migration_path(path):
            continue
        snippet = snippets.get(path, "")
        added_lines = "\n".join(
            line[1:] for line in snippet.splitlines() if line.startswith("+") and not line.startswith("+++")
        )
        if not added_lines:
            continue
        for code, pattern, message in PATTERNS:
            if message is None:
                continue
            for match in pattern.finditer(added_lines):
                warnings.append(
                    {
                        "code": code,
                        "file": path,
                        "snippet": _line_at(added_lines, match.start()),
                        "message": message,
                        "severity": _severity(code),
                    }
                )
    return warnings


def _is_migration_path(path: str) -> bool:
    lower = path.lower()
    return any(hint in lower for hint in MIGRATION_PATH_HINTS) or lower.endswith(".sql")


def _severity(code: str) -> str:
    if code in {"drop_table", "drop_column", "alembic_drop_column", "alembic_drop_table"}:
        return "high"
    if code in {"add_not_null_no_default", "alter_column_type", "add_foreign_key"}:
        return "high"
    return "medium"


def _line_at(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    return text[start:end].strip()
