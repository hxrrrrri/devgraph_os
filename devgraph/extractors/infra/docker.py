"""Dockerfile extraction."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.ids import node_id
from devgraph.core.schema import ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    make_chunk,
    make_file_node,
    make_file_record,
    read_text,
    redact_secrets,
)


class DockerExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "infra", "dockerfile", text)
        file_node = make_file_node(record)
        resource = Node(
            id=node_id("resource", record.path),
            type="resource",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="dockerfile",
            content_hash=record.content_hash,
            metadata={"kind": "container-build"},
        )
        return ExtractionResult(
            file=record,
            nodes=[file_node, resource],
            edges=[contains_edge(file_node, resource, "dockerfile")],
            chunks=[make_chunk(record.path, text, "infra", resource)],
        )

