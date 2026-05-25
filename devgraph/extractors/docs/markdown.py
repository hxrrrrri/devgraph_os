"""Markdown extraction."""

from __future__ import annotations

import re
from pathlib import Path

from devgraph.core.ids import edge_id, node_id
from devgraph.core.schema import Edge, ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    make_chunk,
    make_file_node,
    make_file_record,
    read_text,
    redact_secrets,
    section_slug,
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "document", "markdown", text)
        file_node = make_file_node(record)
        document = Node(
            id=node_id("document", record.path),
            type="document",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="markdown",
            content_hash=record.content_hash,
        )
        nodes = [file_node, document]
        edges: list[Edge] = [contains_edge(file_node, document, "markdown")]
        for match in HEADING_RE.finditer(text):
            title = match.group(2).strip()
            line = text[: match.start()].count("\n") + 1
            section = Node(
                id=node_id("section", f"{record.path}#{section_slug(title)}"),
                type="section",
                name=title,
                qualified_name=f"{record.path}#{title}",
                file_path=record.path,
                line_start=line,
                line_end=line,
                language="markdown",
                content_hash=record.content_hash,
                metadata={"level": len(match.group(1))},
            )
            nodes.append(section)
            edges.append(
                Edge(
                    id=edge_id(document.id, section.id, "contains", "markdown"),
                    source_id=document.id,
                    target_id=section.id,
                    type="contains",
                    provenance_source="markdown",
                    file_path=record.path,
                    line=line,
                )
            )
        return ExtractionResult(
            file=record,
            nodes=nodes,
            edges=edges,
            chunks=[make_chunk(record.path, text, "document", document)],
        )

