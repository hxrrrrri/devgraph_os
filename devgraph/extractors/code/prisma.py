"""Prisma schema extractor (`*.prisma`).

Emits a `schema` node per model, plus `database_table` synonym nodes for query
ergonomics. Fields and relations are stored as metadata.
"""

from __future__ import annotations

from pathlib import Path

from devgraph.core.ids import edge_id, node_id
from devgraph.core.schema import Edge, ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    make_file_node,
    make_file_record,
    read_text,
)
from devgraph.extractors.code.frameworks import parse_prisma_models
from devgraph.retrieval.chunking import chunk_code


class PrismaExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = read_text(path)
        record = make_file_record(root, path, "code", "prisma", text)
        file_node = make_file_node(record)
        nodes: list[Node] = []
        edges: list[Edge] = []

        for name, fields, line in parse_prisma_models(text):
            qn = f"{record.path}::{name}"
            field_payload = [
                {"name": field, "type": ftype, "attributes": attrs}
                for field, ftype, attrs in fields
            ]
            model_node = Node(
                id=node_id("schema", qn),
                type="schema",
                name=name,
                qualified_name=qn,
                file_path=record.path,
                line_start=line,
                line_end=line,
                language="prisma",
                content_hash=record.content_hash,
                metadata={
                    "framework": "prisma",
                    "kind": "model",
                    "fields": field_payload,
                    "parser": "prisma-patterns",
                },
            )
            nodes.append(model_node)
            edges.append(
                Edge(
                    id=edge_id(file_node.id, model_node.id, "contains", "prisma-patterns"),
                    source_id=file_node.id,
                    target_id=model_node.id,
                    type="contains",
                    provenance_source="prisma-patterns",
                    file_path=record.path,
                    line=line,
                )
            )
            table_node = Node(
                id=node_id("database_table", f"prisma::{name}"),
                type="database_table",
                name=name,
                qualified_name=f"prisma::{name}",
                file_path=record.path,
                line_start=line,
                line_end=line,
                language="prisma",
                content_hash=record.content_hash,
                metadata={"framework": "prisma", "parser": "prisma-patterns"},
            )
            nodes.append(table_node)
            edges.append(
                Edge(
                    id=edge_id(model_node.id, table_node.id, "writes_to", f"prisma:{name}"),
                    source_id=model_node.id,
                    target_id=table_node.id,
                    type="writes_to",
                    provenance_source="prisma-patterns",
                    file_path=record.path,
                    line=line,
                )
            )

        all_nodes = [file_node, *nodes]
        all_edges = [contains_edge(file_node, node, "prisma-patterns") for node in nodes if node.type == "schema"]
        all_edges.extend(edges)
        return ExtractionResult(
            file=record,
            nodes=all_nodes,
            edges=all_edges,
            chunks=chunk_code(record.path, text, all_nodes),
            warnings=[],
        )
