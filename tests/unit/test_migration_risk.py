"""Migration risk detector tests."""

from __future__ import annotations

from devgraph.intelligence.migration_risk import detect_migration_warnings


def test_drop_column_flagged_high() -> None:
    snippets = {
        "migrations/0042_drop_email.sql": (
            "--- a/migrations/0042_drop_email.sql\n"
            "+++ b/migrations/0042_drop_email.sql\n"
            "@@\n"
            "+ALTER TABLE users DROP COLUMN email;\n"
        ),
    }
    warnings = detect_migration_warnings(list(snippets), snippets)
    assert any(w["code"] == "drop_column" and w["severity"] == "high" for w in warnings)


def test_add_not_null_without_default_flagged() -> None:
    snippets = {
        "alembic/versions/x_add_not_null.py": (
            "+++ b/alembic/versions/x_add_not_null.py\n"
            "+op.execute('ALTER TABLE users ADD COLUMN tier VARCHAR NOT NULL')\n"
        ),
    }
    warnings = detect_migration_warnings(list(snippets), snippets)
    codes = {w["code"] for w in warnings}
    assert "add_not_null_no_default" in codes


def test_add_not_null_with_default_not_flagged() -> None:
    snippets = {
        "migrations/safe.sql": (
            "+++ b/migrations/safe.sql\n"
            "+ALTER TABLE users ADD COLUMN tier VARCHAR NOT NULL DEFAULT 'free';\n"
        ),
    }
    warnings = detect_migration_warnings(list(snippets), snippets)
    assert all(w["code"] != "add_not_null_no_default" for w in warnings)


def test_alembic_drop_table_flagged() -> None:
    snippets = {
        "alembic/versions/y_drop.py": (
            "+++ b/alembic/versions/y_drop.py\n"
            "+op.drop_table('legacy_audit')\n"
        ),
    }
    warnings = detect_migration_warnings(list(snippets), snippets)
    assert any(w["code"] == "alembic_drop_table" for w in warnings)


def test_non_migration_path_ignored() -> None:
    snippets = {
        "src/app/db.py": (
            "+++ b/src/app/db.py\n"
            "+session.execute('DROP TABLE users')\n"
        ),
    }
    warnings = detect_migration_warnings(list(snippets), snippets)
    assert warnings == []


def test_foreign_key_flagged() -> None:
    snippets = {
        "migrations/fk.sql": (
            "+++ b/migrations/fk.sql\n"
            "+ALTER TABLE orders ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id);\n"
        ),
    }
    warnings = detect_migration_warnings(list(snippets), snippets)
    assert any(w["code"] == "add_foreign_key" for w in warnings)
