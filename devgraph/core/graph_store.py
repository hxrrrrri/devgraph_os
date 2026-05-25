"""SQLite-backed graph store."""

from __future__ import annotations

import json
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import Any

import networkx as nx

from devgraph.core.ids import stable_hash
from devgraph.core.migrations import run_migrations
from devgraph.core.schema import Chunk, Edge, FileRecord, GraphStatus, Node, utc_now


class GraphStore:
    """Persistent local graph storage backed by SQLite and FTS5."""

    def __init__(self, project_root: Path, storage_path: Path) -> None:
        self.project_root = project_root
        self.storage_path = storage_path
        self.db_path = storage_path / "graph.db"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        for child in ["cache", "snapshots", "reports", "wiki", "sessions", "exports"]:
            (self.storage_path / child).mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        run_migrations(self.connection)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> GraphStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def __del__(self) -> None:
        with suppress(Exception):
            self.connection.close()

    def upsert_file(self, record: FileRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO files (
                path, absolute_path, language, category, size_bytes, content_hash,
                last_indexed_at, is_deleted, is_generated, is_test
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                absolute_path=excluded.absolute_path,
                language=excluded.language,
                category=excluded.category,
                size_bytes=excluded.size_bytes,
                content_hash=excluded.content_hash,
                last_indexed_at=excluded.last_indexed_at,
                is_deleted=excluded.is_deleted,
                is_generated=excluded.is_generated,
                is_test=excluded.is_test
            """,
            (
                record.path,
                record.absolute_path,
                record.language,
                record.category,
                record.size_bytes,
                record.content_hash,
                record.last_indexed_at,
                int(record.is_deleted),
                int(record.is_generated),
                int(record.is_test),
            ),
        )

    def upsert_node(self, node: Node) -> None:
        self.connection.execute(
            """
            INSERT INTO nodes (
                id, type, name, qualified_name, file_path, line_start, line_end,
                language, summary, tags, confidence, confidence_tier, created_at,
                updated_at, content_hash, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                type=excluded.type,
                name=excluded.name,
                qualified_name=excluded.qualified_name,
                file_path=excluded.file_path,
                line_start=excluded.line_start,
                line_end=excluded.line_end,
                language=excluded.language,
                summary=excluded.summary,
                tags=excluded.tags,
                confidence=excluded.confidence,
                confidence_tier=excluded.confidence_tier,
                updated_at=excluded.updated_at,
                content_hash=excluded.content_hash,
                metadata=excluded.metadata
            """,
            self._node_values(node),
        )
        self.connection.execute("DELETE FROM nodes_fts WHERE id = ?", (node.id,))
        self.connection.execute(
            "INSERT INTO nodes_fts(id, name, qualified_name, summary, content) VALUES (?, ?, ?, ?, ?)",
            (
                node.id,
                node.name,
                node.qualified_name,
                node.summary or "",
                json.dumps(node.metadata, sort_keys=True),
            ),
        )

    def upsert_edge(self, edge: Edge) -> None:
        self.connection.execute(
            """
            INSERT INTO edges (
                id, source_id, target_id, type, confidence, confidence_tier,
                provenance_source, file_path, line, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_id=excluded.source_id,
                target_id=excluded.target_id,
                type=excluded.type,
                confidence=excluded.confidence,
                confidence_tier=excluded.confidence_tier,
                provenance_source=excluded.provenance_source,
                file_path=excluded.file_path,
                line=excluded.line,
                metadata=excluded.metadata,
                updated_at=excluded.updated_at
            """,
            self._edge_values(edge),
        )

    def upsert_chunk(self, chunk: Chunk) -> None:
        self.connection.execute(
            """
            INSERT INTO chunks (
                id, file_path, node_id, kind, content, line_start, line_end,
                token_estimate, metadata, content_hash, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                file_path=excluded.file_path,
                node_id=excluded.node_id,
                kind=excluded.kind,
                content=excluded.content,
                line_start=excluded.line_start,
                line_end=excluded.line_end,
                token_estimate=excluded.token_estimate,
                metadata=excluded.metadata,
                content_hash=excluded.content_hash,
                updated_at=excluded.updated_at
            """,
            (
                chunk.id,
                chunk.file_path,
                chunk.node_id,
                chunk.kind,
                chunk.content,
                chunk.line_start,
                chunk.line_end,
                chunk.token_estimate,
                json.dumps(chunk.metadata, sort_keys=True),
                chunk.content_hash,
                chunk.created_at,
                chunk.updated_at,
            ),
        )
        self.connection.execute("DELETE FROM chunks_fts WHERE id = ?", (chunk.id,))
        self.connection.execute(
            "INSERT INTO chunks_fts(id, file_path, content) VALUES (?, ?, ?)",
            (chunk.id, chunk.file_path, chunk.content),
        )

    def replace_file_graph(
        self,
        record: FileRecord,
        nodes: list[Node],
        edges: list[Edge],
        chunks: list[Chunk],
    ) -> None:
        old_ids = [
            row["id"]
            for row in self.connection.execute(
                "SELECT id FROM nodes WHERE file_path = ?", (record.path,)
            ).fetchall()
        ]
        if old_ids:
            placeholders = ",".join("?" for _ in old_ids)
            self.connection.execute(
                f"DELETE FROM edges WHERE source_id IN ({placeholders})",
                old_ids,
            )
            self.connection.execute(
                f"DELETE FROM edges WHERE target_id IN ({placeholders})",
                old_ids,
            )
            self.connection.execute(
                f"DELETE FROM nodes_fts WHERE id IN ({placeholders})",
                old_ids,
            )
            self.connection.execute(
                f"DELETE FROM nodes WHERE id IN ({placeholders})",
                old_ids,
            )
        self.connection.execute(
            "DELETE FROM chunks_fts WHERE id IN (SELECT id FROM chunks WHERE file_path = ?)",
            (record.path,),
        )
        self.connection.execute("DELETE FROM chunks WHERE file_path = ?", (record.path,))
        self.connection.execute("DELETE FROM edges WHERE file_path = ?", (record.path,))
        self.upsert_file(record)
        for node in nodes:
            self.upsert_node(node)
        for edge in edges:
            self.upsert_edge(edge)
        for chunk in chunks:
            self.upsert_chunk(chunk)
        self.connection.commit()

    def mark_file_deleted(self, path: str) -> None:
        now = utc_now()
        old_ids = [
            row["id"]
            for row in self.connection.execute("SELECT id FROM nodes WHERE file_path = ?", (path,)).fetchall()
        ]
        if old_ids:
            placeholders = ",".join("?" for _ in old_ids)
            self.connection.execute(
                f"DELETE FROM edges WHERE source_id IN ({placeholders})",
                old_ids,
            )
            self.connection.execute(
                f"DELETE FROM edges WHERE target_id IN ({placeholders})",
                old_ids,
            )
            self.connection.execute(
                f"DELETE FROM nodes_fts WHERE id IN ({placeholders})",
                old_ids,
            )
            self.connection.execute(
                f"DELETE FROM nodes WHERE id IN ({placeholders})",
                old_ids,
            )
        self.connection.execute(
            "DELETE FROM chunks_fts WHERE id IN (SELECT id FROM chunks WHERE file_path = ?)",
            (path,),
        )
        self.connection.execute("DELETE FROM chunks WHERE file_path = ?", (path,))
        self.connection.execute(
            "UPDATE files SET is_deleted = 1, last_indexed_at = ? WHERE path = ?",
            (now, path),
        )
        self.connection.commit()

    def get_status(self, project_name: str) -> GraphStatus:
        counts = {
            name: self.connection.execute(
                f"SELECT COUNT(*) FROM {name}"
            ).fetchone()[0]
            for name in ["files", "nodes", "edges", "chunks"]
        }
        language_rows = self.connection.execute(
            """
            SELECT COALESCE(language, 'unknown') AS language, COUNT(*) AS count
            FROM files
            WHERE is_deleted = 0
            GROUP BY COALESCE(language, 'unknown')
            ORDER BY count DESC
            """
        ).fetchall()
        last_indexed = self.connection.execute(
            "SELECT MAX(last_indexed_at) FROM files WHERE is_deleted = 0"
        ).fetchone()[0]
        warnings: list[str] = []
        if counts["nodes"] == 0:
            warnings.append("Graph has no nodes. Run `devgraph build`.")
        return GraphStatus(
            project=project_name,
            storage_path=str(self.storage_path),
            total_files=counts["files"],
            total_nodes=counts["nodes"],
            total_edges=counts["edges"],
            total_chunks=counts["chunks"],
            languages={row["language"]: row["count"] for row in language_rows},
            last_indexed_at=last_indexed,
            warnings=warnings,
        )

    def find_nodes(self, query: str, limit: int = 20) -> list[Node]:
        exact_rows = self.connection.execute(
            """
            SELECT * FROM nodes
            WHERE qualified_name = ? OR name = ? OR file_path = ?
            LIMIT ?
            """,
            (query, query, query, limit),
        ).fetchall()
        rows = list(exact_rows)
        if len(rows) < limit:
            rows.extend(self._search_nodes_fts(query, limit - len(rows)))
        unique: dict[str, Node] = {}
        for row in rows:
            node = self._row_to_node(row)
            unique[node.id] = node
        return list(unique.values())[:limit]

    def get_node(self, node_id: str) -> Node | None:
        row = self.connection.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_node(row) if row else None

    def nodes_for_files(self, paths: list[str]) -> list[Node]:
        if not paths:
            return []
        placeholders = ",".join("?" for _ in paths)
        rows = self.connection.execute(
            f"SELECT * FROM nodes WHERE file_path IN ({placeholders}) "
            "ORDER BY file_path, line_start",
            paths,
        ).fetchall()
        return [self._row_to_node(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        nodes = [node.model_dump() for node in self.find_nodes(query, limit=limit)]
        chunk_rows = self._search_chunks_fts(query, limit)
        chunks = [dict(row) for row in chunk_rows]
        return {"nodes": nodes, "chunks": chunks}

    def get_chunks_for_file(self, file_path: str, limit: int = 5) -> list[Chunk]:
        rows = self.connection.execute(
            "SELECT * FROM chunks WHERE file_path = ? ORDER BY line_start LIMIT ?",
            (file_path, limit),
        ).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def get_neighborhood(self, node_ids: list[str], depth: int = 1, limit: int = 100) -> dict[str, Any]:
        seen_nodes: set[str] = set(node_ids)
        frontier: set[str] = set(node_ids)
        edge_rows: list[sqlite3.Row] = []
        for _ in range(depth):
            if not frontier:
                break
            placeholders = ",".join("?" for _ in frontier)
            query = (
                f"SELECT * FROM edges WHERE source_id IN ({placeholders}) "
                f"OR target_id IN ({placeholders}) LIMIT ?"
            )
            rows = self.connection.execute(
                query,
                [*frontier, *frontier, limit],
            ).fetchall()
            next_frontier: set[str] = set()
            for row in rows:
                edge_rows.append(row)
                for key in ["source_id", "target_id"]:
                    value = row[key]
                    if value not in seen_nodes:
                        seen_nodes.add(value)
                        next_frontier.add(value)
            frontier = next_frontier
            if len(seen_nodes) >= limit:
                break
        node_rows = []
        if seen_nodes:
            placeholders = ",".join("?" for _ in seen_nodes)
            node_rows = self.connection.execute(
                f"SELECT * FROM nodes WHERE id IN ({placeholders})",
                list(seen_nodes),
            ).fetchall()
        return {
            "nodes": [self._row_to_node(row).model_dump() for row in node_rows],
            "edges": [self._row_to_edge(row).model_dump() for row in edge_rows],
        }

    def impacted_nodes(self, node_ids: list[str], depth: int = 2, limit: int = 100) -> list[Node]:
        impacted: dict[str, Node] = {}
        frontier = set(node_ids)
        seen = set(node_ids)
        for _ in range(depth):
            if not frontier:
                break
            placeholders = ",".join("?" for _ in frontier)
            query = (
                "SELECT DISTINCT n.* FROM edges e "
                "JOIN nodes n ON n.id = e.source_id "
                f"WHERE e.target_id IN ({placeholders}) LIMIT ?"
            )
            rows = self.connection.execute(
                query,
                [*frontier, limit],
            ).fetchall()
            next_frontier: set[str] = set()
            for row in rows:
                node = self._row_to_node(row)
                if node.id not in seen:
                    impacted[node.id] = node
                    seen.add(node.id)
                    next_frontier.add(node.id)
            frontier = next_frontier
        return list(impacted.values())[:limit]

    def find_path(self, source_query: str, target_query: str, cutoff: int = 6) -> list[Node]:
        source = self.find_nodes(source_query, limit=1)
        target = self.find_nodes(target_query, limit=1)
        if not source or not target:
            return []
        graph = nx.Graph()
        rows = self.connection.execute("SELECT source_id, target_id FROM edges").fetchall()
        graph.add_edges_from((row["source_id"], row["target_id"]) for row in rows)
        try:
            ids = nx.shortest_path(graph, source[0].id, target[0].id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        if len(ids) > cutoff + 1:
            return []
        return [node for node_id in ids if (node := self.get_node(node_id))]

    def all_graph(self, limit: int = 500) -> dict[str, Any]:
        node_rows = self.connection.execute("SELECT * FROM nodes LIMIT ?", (limit,)).fetchall()
        edge_rows = self.connection.execute("SELECT * FROM edges LIMIT ?", (limit * 2,)).fetchall()
        return {
            "nodes": [self._row_to_node(row).model_dump() for row in node_rows],
            "edges": [self._row_to_edge(row).model_dump() for row in edge_rows],
        }

    def record_session(self, kind: str, title: str, summary: str, metadata: dict[str, Any]) -> str:
        session_id = f"session:{stable_hash(kind, title, utc_now(), length=24)}"
        now = utc_now()
        self.connection.execute(
            """
            INSERT INTO sessions(id, kind, created_at, updated_at, title, summary, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, kind, now, now, title, summary, json.dumps(metadata, sort_keys=True)),
        )
        self.connection.commit()
        return session_id

    def recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def write_json_export(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "files": [dict(row) for row in self.connection.execute("SELECT * FROM files").fetchall()],
            "nodes": [dict(row) for row in self.connection.execute("SELECT * FROM nodes").fetchall()],
            "edges": [dict(row) for row in self.connection.execute("SELECT * FROM edges").fetchall()],
            "chunks": [dict(row) for row in self.connection.execute("SELECT * FROM chunks").fetchall()],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _search_nodes_fts(self, query: str, limit: int) -> list[sqlite3.Row]:
        try:
            ids = [
                row["id"]
                for row in self.connection.execute(
                    "SELECT id FROM nodes_fts WHERE nodes_fts MATCH ? LIMIT ?",
                    (self._fts_query(query), limit),
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            ids = []
        if not ids:
            like = f"%{query}%"
            return self.connection.execute(
                """
                SELECT * FROM nodes
                WHERE name LIKE ? OR qualified_name LIKE ? OR summary LIKE ? OR file_path LIKE ?
                LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
        placeholders = ",".join("?" for _ in ids)
        return self.connection.execute(
            f"SELECT * FROM nodes WHERE id IN ({placeholders})",
            ids,
        ).fetchall()

    def _search_chunks_fts(self, query: str, limit: int) -> list[sqlite3.Row]:
        try:
            ids = [
                row["id"]
                for row in self.connection.execute(
                    "SELECT id FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?",
                    (self._fts_query(query), limit),
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            ids = []
        if not ids:
            like = f"%{query}%"
            return self.connection.execute(
                "SELECT * FROM chunks WHERE content LIKE ? OR file_path LIKE ? LIMIT ?",
                (like, like, limit),
            ).fetchall()
        placeholders = ",".join("?" for _ in ids)
        return self.connection.execute(
            f"SELECT * FROM chunks WHERE id IN ({placeholders})",
            ids,
        ).fetchall()

    @staticmethod
    def _fts_query(query: str) -> str:
        terms = [term.strip('"') for term in query.replace(":", " ").replace("/", " ").split()]
        return " OR ".join(f'"{term}"' for term in terms if term) or '""'

    @staticmethod
    def _node_values(node: Node) -> tuple[Any, ...]:
        return (
            node.id,
            node.type,
            node.name,
            node.qualified_name,
            node.file_path,
            node.line_start,
            node.line_end,
            node.language,
            node.summary,
            json.dumps(node.tags),
            node.confidence,
            node.confidence_tier,
            node.created_at,
            node.updated_at,
            node.content_hash,
            json.dumps(node.metadata, sort_keys=True),
        )

    @staticmethod
    def _edge_values(edge: Edge) -> tuple[Any, ...]:
        return (
            edge.id,
            edge.source_id,
            edge.target_id,
            edge.type,
            edge.confidence,
            edge.confidence_tier,
            edge.provenance_source,
            edge.file_path,
            edge.line,
            json.dumps(edge.metadata, sort_keys=True),
            edge.created_at,
            edge.updated_at,
        )

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Node:
        data = dict(row)
        data["tags"] = json.loads(data.get("tags") or "[]")
        data["metadata"] = json.loads(data.get("metadata") or "{}")
        return Node(**data)

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> Edge:
        data = dict(row)
        data["metadata"] = json.loads(data.get("metadata") or "{}")
        return Edge(**data)

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> Chunk:
        data = dict(row)
        data["metadata"] = json.loads(data.get("metadata") or "{}")
        return Chunk(**data)
