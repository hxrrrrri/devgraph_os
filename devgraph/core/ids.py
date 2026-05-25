"""Stable ID helpers for graph entities."""

from __future__ import annotations

import hashlib
from pathlib import Path


def normalize_path(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def stable_hash(*parts: object, length: int = 16) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def content_hash(content: bytes | str) -> str:
    data = content.encode("utf-8", errors="replace") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


def node_id(node_type: str, qualified_name: str) -> str:
    return f"{node_type}:{stable_hash(node_type, qualified_name, length=24)}"


def file_node_id(path: str | Path) -> str:
    normalized = normalize_path(path)
    return node_id("file", normalized)


def edge_id(source_id: str, target_id: str, edge_type: str, provenance: str = "") -> str:
    return f"edge:{stable_hash(source_id, target_id, edge_type, provenance, length=24)}"


def chunk_id(file_path: str, line_start: int | None, line_end: int | None, content: str) -> str:
    return f"chunk:{stable_hash(file_path, line_start, line_end, content_hash(content), length=24)}"

