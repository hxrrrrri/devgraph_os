"""SQLite migrations for the local graph store."""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            absolute_path TEXT NOT NULL,
            language TEXT,
            category TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            content_hash TEXT NOT NULL,
            last_indexed_at TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            is_generated INTEGER NOT NULL DEFAULT 0,
            is_test INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            qualified_name TEXT NOT NULL,
            file_path TEXT,
            line_start INTEGER,
            line_end INTEGER,
            language TEXT,
            summary TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 1.0,
            confidence_tier TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            content_hash TEXT,
            metadata TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
        CREATE INDEX IF NOT EXISTS idx_nodes_file_path ON nodes(file_path);
        CREATE INDEX IF NOT EXISTS idx_nodes_qualified_name ON nodes(qualified_name);

        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            type TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            confidence_tier TEXT NOT NULL,
            provenance_source TEXT NOT NULL,
            file_path TEXT,
            line INTEGER,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
        CREATE INDEX IF NOT EXISTS idx_edges_file_path ON edges(file_path);

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            node_id TEXT,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            line_start INTEGER,
            line_end INTEGER,
            token_estimate INTEGER NOT NULL DEFAULT 0,
            metadata TEXT NOT NULL DEFAULT '{}',
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
        CREATE INDEX IF NOT EXISTS idx_chunks_node_id ON chunks(node_id);

        CREATE TABLE IF NOT EXISTS communities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            summary TEXT,
            node_count INTEGER NOT NULL DEFAULT 0,
            metadata TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            summary TEXT,
            entry_node_id TEXT,
            metadata TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flow_memberships (
            flow_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (flow_id, node_id)
        );

        CREATE TABLE IF NOT EXISTS changes (
            id TEXT PRIMARY KEY,
            base_ref TEXT,
            staged INTEGER NOT NULL DEFAULT 0,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL,
            patch TEXT,
            changed_at TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            title TEXT,
            summary TEXT,
            metadata TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence_tier TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS provenance (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            source TEXT NOT NULL,
            source_path TEXT,
            line_start INTEGER,
            line_end INTEGER,
            confidence_tier TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            id UNINDEXED,
            name,
            qualified_name,
            summary,
            content
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            id UNINDEXED,
            file_path,
            content
        );
        """,
    ),
    (
        2,
        """
        CREATE INDEX IF NOT EXISTS idx_changes_file_path ON changes(file_path);
        CREATE INDEX IF NOT EXISTS idx_changes_changed_at ON changes(changed_at);
        CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
        CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
        CREATE INDEX IF NOT EXISTS idx_provenance_entity ON provenance(entity_id, entity_type);
        CREATE INDEX IF NOT EXISTS idx_provenance_source_path ON provenance(source_path);
        """,
    ),
]


def run_migrations(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        connection.executescript(sql)
        connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
    connection.commit()
