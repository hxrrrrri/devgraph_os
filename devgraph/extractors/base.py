"""Base extractor helpers."""

from __future__ import annotations

import re
from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.constants import SECRET_KEY_HINTS
from devgraph.core.ids import chunk_id, content_hash, edge_id, file_node_id, node_id, normalize_path
from devgraph.core.schema import Chunk, Edge, ExtractionResult, FileRecord, Node, utc_now
from devgraph.update.fingerprints import is_probably_generated, is_probably_test


class BaseExtractor:
    def __init__(self, config: DevGraphConfig) -> None:
        self.config = config

    def extract(self, root: Path, path: Path) -> ExtractionResult:
        raise NotImplementedError


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def make_file_record(root: Path, path: Path, category: str, language: str | None, text: str) -> FileRecord:
    rel = normalize_path(path.relative_to(root))
    return FileRecord(
        path=rel,
        absolute_path=str(path.resolve()),
        language=language,
        category=category,
        size_bytes=path.stat().st_size,
        content_hash=content_hash(text),
        last_indexed_at=utc_now(),
        is_generated=is_probably_generated(path, text),
        is_test=is_probably_test(path),
    )


def make_file_node(record: FileRecord) -> Node:
    return Node(
        id=file_node_id(record.path),
        type="file",
        name=Path(record.path).name,
        qualified_name=record.path,
        file_path=record.path,
        language=record.language,
        content_hash=record.content_hash,
        tags=[record.category],
        metadata={
            "category": record.category,
            "is_test": record.is_test,
            "is_generated": record.is_generated,
        },
    )


def contains_edge(parent: Node, child: Node, source: str) -> Edge:
    return Edge(
        id=edge_id(parent.id, child.id, "contains", source),
        source_id=parent.id,
        target_id=child.id,
        type="contains",
        provenance_source=source,
        file_path=child.file_path,
        line=child.line_start,
    )


def make_chunk(file_path: str, text: str, kind: str = "source", node: Node | None = None) -> Chunk:
    safe_text = redact_secrets(text)
    line_count = text.count("\n") + 1 if text else 1
    return Chunk(
        id=chunk_id(file_path, 1, line_count, safe_text),
        file_path=file_path,
        node_id=node.id if node else None,
        kind=kind,
        content=safe_text,
        line_start=1,
        line_end=line_count,
        token_estimate=max(1, len(safe_text) // 4),
        content_hash=content_hash(safe_text),
    )


def external_module_node(name: str, language: str | None = None) -> Node:
    return Node(
        id=node_id("module", f"external::{name}"),
        type="module",
        name=name,
        qualified_name=f"external::{name}",
        language=language,
        confidence_tier="inferred",
        confidence=0.8,
        metadata={"external": True},
    )


def redact_secrets(text: str) -> str:
    redacted_lines: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if any(hint in lower for hint in SECRET_KEY_HINTS):
            if "=" in line:
                key = line.split("=", 1)[0].strip()
                redacted_lines.append(f"{key}=<redacted>")
            elif ":" in line:
                key = line.split(":", 1)[0].strip()
                redacted_lines.append(f"{key}: <redacted>")
            else:
                redacted_lines.append("<redacted secret-like line>")
        else:
            redacted_lines.append(line)
    return "\n".join(redacted_lines)


def section_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"
