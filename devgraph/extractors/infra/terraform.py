"""Terraform extraction."""

from __future__ import annotations

import re
from pathlib import Path

from devgraph.core.ids import edge_id, node_id
from devgraph.core.schema import Edge, ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    make_file_node,
    make_file_record,
    read_text,
    redact_secrets,
)
from devgraph.retrieval.chunking import chunk_text

BLOCK_RE = re.compile(r'^\s*(resource|data|module|variable|output)\s+"([^"]+)"(?:\s+"([^"]+)")?', re.MULTILINE)


class TerraformExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "infra", "terraform", text)
        file_node = make_file_node(record)
        root_resource = Node(
            id=node_id("resource", record.path),
            type="resource",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="terraform",
            content_hash=record.content_hash,
            metadata={"kind": "terraform-file"},
        )
        nodes = [file_node, root_resource]
        edges: list[Edge] = [contains_edge(file_node, root_resource, "terraform")]
        for match in BLOCK_RE.finditer(text):
            block_kind = match.group(1)
            name = ".".join(part for part in match.groups()[1:] if part)
            line = text[: match.start()].count("\n") + 1
            resource = Node(
                id=node_id("resource", f"{record.path}::{block_kind}.{name}"),
                type="resource",
                name=f"{block_kind}.{name}",
                qualified_name=f"{record.path}::{block_kind}.{name}",
                file_path=record.path,
                line_start=line,
                line_end=line,
                language="terraform",
                content_hash=record.content_hash,
                metadata={"kind": block_kind, "parser": "terraform-patterns"},
            )
            nodes.append(resource)
            edges.append(
                Edge(
                    id=edge_id(root_resource.id, resource.id, "contains", "terraform"),
                    source_id=root_resource.id,
                    target_id=resource.id,
                    type="contains",
                    provenance_source="terraform",
                    file_path=record.path,
                    line=line,
                )
            )
        return ExtractionResult(
            file=record,
            nodes=nodes,
            edges=edges,
            chunks=chunk_text(record.path, text, root_resource, "infra"),
        )
