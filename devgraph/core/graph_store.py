"""SQLite-backed graph store."""

from __future__ import annotations

import json
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import Any

import networkx as nx

from devgraph.constants import SECRET_KEY_HINTS
from devgraph.core.ids import edge_id, stable_hash
from devgraph.core.migrations import run_migrations
from devgraph.core.schema import Chunk, Edge, FileRecord, GraphStatus, Node, utc_now


class GraphStore:
    """Persistent local graph storage backed by SQLite and FTS5."""

    def __init__(self, project_root: Path, storage_path: Path) -> None:
        self.project_root = project_root
        self.storage_path = storage_path
        self.db_path = storage_path / "graph.db"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        for child in ["cache", "snapshots", "reports", "wiki", "sessions", "exports", "imports"]:
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
        self.connection.execute("DELETE FROM provenance WHERE source_path = ?", (record.path,))
        self.connection.execute("DELETE FROM embeddings WHERE file_path = ?", (record.path,))
        self.upsert_file(record)
        for node in nodes:
            self.upsert_node(node)
            self.record_provenance(
                entity_id=node.id,
                entity_type="node",
                source="extractor",
                source_path=record.path,
                line_start=node.line_start,
                line_end=node.line_end,
                confidence_tier=node.confidence_tier,
                metadata={"node_type": node.type, "qualified_name": node.qualified_name},
                commit=False,
            )
        for edge in edges:
            self.upsert_edge(edge)
            self.record_provenance(
                entity_id=edge.id,
                entity_type="edge",
                source=edge.provenance_source,
                source_path=edge.file_path or record.path,
                line_start=edge.line,
                line_end=edge.line,
                confidence_tier=edge.confidence_tier,
                metadata={"edge_type": edge.type},
                commit=False,
            )
        for chunk in chunks:
            self.upsert_chunk(chunk)
            self.record_provenance(
                entity_id=chunk.id,
                entity_type="chunk",
                source="extractor",
                source_path=chunk.file_path,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                confidence_tier="extracted",
                metadata={"kind": chunk.kind, "node_id": chunk.node_id},
                commit=False,
            )
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
        self.connection.execute("DELETE FROM provenance WHERE source_path = ?", (path,))
        self.connection.execute("DELETE FROM embeddings WHERE file_path = ?", (path,))
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

    def all_nodes(self) -> list[Node]:
        rows = self.connection.execute("SELECT * FROM nodes").fetchall()
        return [self._row_to_node(row) for row in rows]

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

    def upsert_embedding(
        self,
        entity_id: str,
        entity_type: str,
        provider: str,
        model: str,
        vector: list[float],
        text: str,
        file_path: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO embeddings(
                entity_id, entity_type, provider, model, dimensions, vector, text,
                file_path, metadata, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, provider, model) DO UPDATE SET
                dimensions=excluded.dimensions,
                vector=excluded.vector,
                text=excluded.text,
                file_path=excluded.file_path,
                metadata=excluded.metadata,
                updated_at=excluded.updated_at
            """,
            (
                entity_id,
                entity_type,
                provider,
                model,
                len(vector),
                json.dumps(vector),
                text,
                file_path,
                json.dumps(metadata or {}, sort_keys=True),
                utc_now(),
            ),
        )

    def search_embeddings(
        self,
        query_vector: list[float],
        provider: str,
        model: str,
        limit: int = 10,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM embeddings
            WHERE provider = ? AND model = ?
            ORDER BY updated_at DESC
            """,
            (provider, model),
        ).fetchall()
        allowed = set(entity_types or [])
        scored: list[dict[str, Any]] = []
        for row in rows:
            if allowed and row["entity_type"] not in allowed:
                continue
            try:
                vector = json.loads(row["vector"])
            except json.JSONDecodeError:
                continue
            score = _cosine(query_vector, vector)
            if score <= 0:
                continue
            data = dict(row)
            data["metadata"] = json.loads(data.get("metadata") or "{}")
            data["score"] = score
            data.pop("vector", None)
            scored.append(data)
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]

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

    def tests_for_nodes(self, node_ids: list[str], limit: int = 100) -> list[Node]:
        if not node_ids:
            return []
        placeholders = ",".join("?" for _ in node_ids)
        rows = self.connection.execute(
            "SELECT DISTINCT n.* FROM edges e "
            "JOIN nodes n ON n.id = e.target_id "
            f"WHERE e.type = 'tested_by' AND e.source_id IN ({placeholders}) "
            "ORDER BY n.file_path, n.line_start LIMIT ?",
            [*node_ids, limit],
        ).fetchall()
        return [self._row_to_node(row) for row in rows]

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

    def record_change(
        self,
        file_path: str,
        status: str,
        patch: str = "",
        base_ref: str | None = None,
        staged: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        now = utc_now()
        change_id = f"change:{stable_hash(base_ref or '', staged, file_path, status, patch, now, length=24)}"
        self.connection.execute(
            """
            INSERT INTO changes(id, base_ref, staged, file_path, status, patch, changed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change_id,
                base_ref,
                int(staged),
                file_path,
                status,
                patch,
                now,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        self.connection.commit()
        return change_id

    def recent_changes(self, limit: int = 25) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM changes ORDER BY changed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def remember(
        self,
        kind: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> str:
        redacted, did_redact = _redact_secret_like(content)
        now = utc_now()
        memory_id = f"memory:{stable_hash(kind, redacted, now, length=24)}"
        memory_metadata = dict(metadata or {})
        memory_metadata["redacted_secret_like_content"] = did_redact
        self.connection.execute(
            """
            INSERT INTO memories(id, session_id, kind, content, confidence_tier, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                session_id,
                kind,
                redacted,
                "user",
                now,
                json.dumps(memory_metadata, sort_keys=True),
            ),
        )
        self.connection.commit()
        return memory_id

    def list_memories(self, kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if kind:
            rows = self.connection.execute(
                "SELECT * FROM memories WHERE kind = ? ORDER BY created_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_decode_json_metadata(row) for row in rows]

    def relevant_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return self.list_memories(limit=limit)
        terms = [term for term in query.lower().split() if len(term) > 2][:6]
        if not terms:
            return self.list_memories(limit=limit)
        clauses = " OR ".join(["lower(content) LIKE ? OR lower(kind) LIKE ?" for _ in terms])
        params: list[Any] = []
        for term in terms:
            like = f"%{term}%"
            params.extend([like, like])
        rows = self.connection.execute(
            f"SELECT * FROM memories WHERE {clauses} ORDER BY created_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [_decode_json_metadata(row) for row in rows]

    def forget_memory(self, memory_id: str) -> bool:
        cursor = self.connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.connection.commit()
        return cursor.rowcount > 0

    def recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def record_provenance(
        self,
        entity_id: str,
        entity_type: str,
        source: str,
        source_path: str | None,
        line_start: int | None = None,
        line_end: int | None = None,
        confidence_tier: str = "extracted",
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> str:
        provenance_id = f"provenance:{stable_hash(entity_id, source, source_path, line_start, line_end, length=24)}"
        self.connection.execute(
            """
            INSERT INTO provenance(
                id, entity_id, entity_type, source, source_path, line_start, line_end,
                confidence_tier, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                confidence_tier=excluded.confidence_tier,
                metadata=excluded.metadata
            """,
            (
                provenance_id,
                entity_id,
                entity_type,
                source,
                source_path,
                line_start,
                line_end,
                confidence_tier,
                json.dumps(metadata or {}, sort_keys=True),
                utc_now(),
            ),
        )
        if commit:
            self.connection.commit()
        return provenance_id

    def provenance_for_entity(self, entity_id: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM provenance WHERE entity_id = ? ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [_decode_json_metadata(row) for row in rows]

    def create_snapshot(self, name: str, metadata: dict[str, Any] | None = None) -> Path:
        safe_name = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in name)
        target = self.storage_path / "snapshots" / f"{safe_name}.json"
        self.write_json_export(target)
        snapshot_id = f"snapshot:{stable_hash(name, utc_now(), length=24)}"
        self.connection.execute(
            "INSERT INTO snapshots(id, name, created_at, metadata) VALUES (?, ?, ?, ?)",
            (snapshot_id, name, utc_now(), json.dumps(metadata or {}, sort_keys=True)),
        )
        self.connection.commit()
        return target

    def refresh_inferred_relationships(self) -> None:
        self.connection.execute(
            "DELETE FROM edges WHERE confidence_tier = 'inferred' AND type = 'tested_by'"
        )
        self.connection.execute(
            "DELETE FROM edges WHERE confidence_tier = 'inferred' AND provenance_source = 'local-import-resolver'"
        )
        tests = [
            self._row_to_node(row)
            for row in self.connection.execute("SELECT * FROM nodes WHERE type = 'test'").fetchall()
        ]
        subjects = [
            self._row_to_node(row)
            for row in self.connection.execute(
                "SELECT * FROM nodes WHERE type IN ('function', 'class', 'api_endpoint', 'module')"
            ).fetchall()
        ]
        for test in tests:
            normalized_test_name = _normalize_test_name(test.name)
            test_path = (test.file_path or "").lower()
            for subject in subjects:
                if subject.id == test.id or subject.type == "test":
                    continue
                subject_name = subject.name.lower()
                if not subject_name or len(subject_name) < 3:
                    continue
                subject_path = Path(subject.file_path) if subject.file_path else None
                test_path_obj = Path(test.file_path or "")
                same_area = bool(
                    subject_path
                    and (
                        subject_path.parts[:1] == test_path_obj.parts[:1]
                        or subject_path.stem.lower() in test_path
                    )
                )
                name_match = subject_name in normalized_test_name or subject_name in test_path
                if not (name_match and same_area):
                    continue
                edge = Edge(
                    id=f"edge:{stable_hash(subject.id, test.id, 'tested_by', 'test-convention', length=24)}",
                    source_id=subject.id,
                    target_id=test.id,
                    type="tested_by",
                    confidence=0.7,
                    confidence_tier="inferred",
                    provenance_source="test-convention",
                    file_path=test.file_path,
                    line=test.line_start,
                    metadata={"reason": "test name or path references subject name"},
                )
                self.upsert_edge(edge)
        self._refresh_local_import_edges()
        self.connection.commit()

    def _refresh_local_import_edges(self) -> None:
        modules = [
            self._row_to_node(row)
            for row in self.connection.execute("SELECT * FROM nodes WHERE type = 'module'").fetchall()
        ]
        by_qualified = {module.qualified_name: module for module in modules}
        imports = self.connection.execute(
            """
            SELECT e.*, source.file_path AS source_file, target.name AS imported_name
            FROM edges e
            JOIN nodes source ON source.id = e.source_id
            JOIN nodes target ON target.id = e.target_id
            WHERE e.type = 'imports'
            """
        ).fetchall()
        for row in imports:
            source = self.get_node(row["source_id"])
            if source is None:
                continue
            target = _resolve_local_module(
                imported=str(row["imported_name"]),
                source_file=row["source_file"],
                modules_by_qualified=by_qualified,
            )
            if target is None or target.id == row["target_id"] or target.id == source.id:
                continue
            self.upsert_edge(
                Edge(
                    id=edge_id(
                        source.id,
                        target.id,
                        "imports",
                        f"local-import-resolver:{row['imported_name']}",
                    ),
                    source_id=source.id,
                    target_id=target.id,
                    type="imports",
                    confidence=0.8,
                    confidence_tier="inferred",
                    provenance_source="local-import-resolver",
                    file_path=source.file_path,
                    line=row["line"],
                    metadata={"imported": row["imported_name"]},
                )
            )

    def write_json_export(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "files": [dict(row) for row in self.connection.execute("SELECT * FROM files").fetchall()],
            "nodes": [dict(row) for row in self.connection.execute("SELECT * FROM nodes").fetchall()],
            "edges": [dict(row) for row in self.connection.execute("SELECT * FROM edges").fetchall()],
            "chunks": [dict(row) for row in self.connection.execute("SELECT * FROM chunks").fetchall()],
            "memories": [dict(row) for row in self.connection.execute("SELECT * FROM memories").fetchall()],
            "changes": [dict(row) for row in self.connection.execute("SELECT * FROM changes").fetchall()],
            "sessions": [dict(row) for row in self.connection.execute("SELECT * FROM sessions").fetchall()],
            "embeddings": [
                dict(row)
                for row in self.connection.execute(
                    "SELECT entity_id, entity_type, provider, model, dimensions, file_path, metadata, updated_at FROM embeddings"
                ).fetchall()
            ],
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


def _decode_json_metadata(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = json.loads(data.get("metadata") or "{}")
    return data


def _redact_secret_like(content: str) -> tuple[str, bool]:
    redacted_lines: list[str] = []
    did_redact = False
    for line in content.splitlines() or [content]:
        lower = line.lower()
        if any(hint in lower for hint in SECRET_KEY_HINTS):
            did_redact = True
            if "=" in line:
                key = line.split("=", 1)[0].strip()
                redacted_lines.append(f"{key}=<redacted>")
            elif ":" in line:
                key = line.split(":", 1)[0].strip()
                redacted_lines.append(f"{key}: <redacted>")
            else:
                redacted_lines.append("<redacted secret-like memory>")
        else:
            redacted_lines.append(line)
    return "\n".join(redacted_lines), did_redact


def _normalize_test_name(name: str) -> str:
    lower = name.lower()
    for prefix in ("test_", "test", "should_"):
        if lower.startswith(prefix):
            lower = lower.removeprefix(prefix)
    for suffix in ("_test", "test", "_spec", "spec"):
        if lower.endswith(suffix):
            lower = lower.removesuffix(suffix)
    return lower.replace("_", "").replace("-", "")


def _resolve_local_module(
    imported: str,
    source_file: str | None,
    modules_by_qualified: dict[str, Node],
) -> Node | None:
    candidates = _module_candidates(imported, source_file)
    for candidate in candidates:
        if candidate in modules_by_qualified:
            return modules_by_qualified[candidate]
    return None


def _module_candidates(imported: str, source_file: str | None) -> list[str]:
    cleaned = imported.removeprefix("external::").strip()
    candidates: list[str] = []
    if cleaned:
        candidates.append(cleaned)
        candidates.append(cleaned.replace("/", ".").strip("."))
    if source_file and cleaned.startswith("."):
        source_parent = Path(source_file).parent.as_posix()
        resolved = (Path(source_parent) / cleaned).as_posix()
        normalized = resolved.replace("/", ".").strip(".")
        candidates.append(normalized)
        for suffix in ("py", "ts", "tsx", "js", "jsx", "go", "rs", "java"):
            candidates.append(f"{normalized}.{suffix}")
        for suffix in ("ts", "tsx", "js", "jsx"):
            candidates.append(f"{normalized}.index.{suffix}")
    return list(dict.fromkeys(candidates))


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
