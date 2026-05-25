"""Canonical graph schema models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

NodeType = Literal[
    "repository",
    "file",
    "module",
    "function",
    "class",
    "type",
    "test",
    "api_endpoint",
    "database_table",
    "schema",
    "config",
    "service",
    "pipeline",
    "resource",
    "document",
    "section",
    "article",
    "claim",
    "entity",
    "domain",
    "flow",
    "step",
    "commit",
    "pull_request",
    "session",
    "decision",
]

EdgeType = Literal[
    "contains",
    "imports",
    "calls",
    "inherits",
    "implements",
    "tested_by",
    "depends_on",
    "reads_from",
    "writes_to",
    "routes_to",
    "configures",
    "deploys",
    "documents",
    "belongs_to",
    "cites",
    "contradicts",
    "builds_on",
    "affects",
    "changed_in",
    "discussed_in",
    "similar_to",
]

ConfidenceTier = Literal["extracted", "inferred", "llm", "ambiguous", "user"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FileRecord(BaseModel):
    path: str
    absolute_path: str
    language: str | None = None
    category: str
    size_bytes: int
    content_hash: str
    last_indexed_at: str | None = None
    is_deleted: bool = False
    is_generated: bool = False
    is_test: bool = False


class Node(BaseModel):
    id: str
    type: NodeType
    name: str
    qualified_name: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    language: str | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    confidence_tier: ConfidenceTier = "extracted"
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    id: str
    source_id: str
    target_id: str
    type: EdgeType
    confidence: float = 1.0
    confidence_tier: ConfidenceTier = "extracted"
    provenance_source: str
    file_path: str | None = None
    line: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class Chunk(BaseModel):
    id: str
    file_path: str
    node_id: str | None = None
    kind: str = "source"
    content: str
    line_start: int | None = None
    line_end: int | None = None
    token_estimate: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ExtractionResult(BaseModel):
    file: FileRecord
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GraphStatus(BaseModel):
    project: str
    storage_path: str
    total_files: int
    total_nodes: int
    total_edges: int
    total_chunks: int
    languages: dict[str, int]
    last_indexed_at: str | None
    warnings: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    changed_files: list[str]
    changed_hunks: list[dict[str, Any]] = Field(default_factory=list)
    changed_symbols: list[Node] = Field(default_factory=list)
    changed_nodes: list[Node] = Field(default_factory=list)
    impacted_nodes: list[Node] = Field(default_factory=list)
    impacted_files: list[str] = Field(default_factory=list)
    impacted_flows: list[dict[str, Any]] = Field(default_factory=list)
    affected_tests: list[str] = Field(default_factory=list)
    missing_tests: list[str] = Field(default_factory=list)
    public_api_changes: list[str] = Field(default_factory=list)
    config_or_infra_changes: list[str] = Field(default_factory=list)
    database_or_schema_changes: list[str] = Field(default_factory=list)
    security_sensitive_changes: list[str] = Field(default_factory=list)
    diff_summary: list[str] = Field(default_factory=list)
    changed_snippets: dict[str, str] = Field(default_factory=dict)
    risk_score: int
    risk_level: str
    risk_explanation: list[str]
    prioritized_review_items: list[str] = Field(default_factory=list)
    review_checklist: list[str]
    context_pack: str
    suggested_commands: list[str]
    warnings: list[str] = Field(default_factory=list)
