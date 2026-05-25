"""reStructuredText extraction."""

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
    section_slug,
)
from devgraph.retrieval.chunking import chunk_text

RST_HEADING_RE = re.compile(r"^(?P<title>.+)\n(?P<underline>[=\-~`^#*]{3,})$", re.MULTILINE)


class RstExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "document", "rst", text)
        file_node = make_file_node(record)
        document = Node(
            id=node_id("document", record.path),
            type="document",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="rst",
            content_hash=record.content_hash,
        )
        nodes = [file_node, document]
        edges: list[Edge] = [contains_edge(file_node, document, "rst")]
        for match in RST_HEADING_RE.finditer(text):
            title = match.group("title").strip()
            line = text[: match.start()].count("\n") + 1
            section = Node(
                id=node_id("section", f"{record.path}#{section_slug(title)}"),
                type="section",
                name=title,
                qualified_name=f"{record.path}#{title}",
                file_path=record.path,
                line_start=line,
                line_end=line + 1,
                language="rst",
                content_hash=record.content_hash,
                metadata={"underline": match.group("underline")[0]},
            )
            nodes.append(section)
            edges.append(
                Edge(
                    id=edge_id(document.id, section.id, "contains", "rst"),
                    source_id=document.id,
                    target_id=section.id,
                    type="contains",
                    provenance_source="rst",
                    file_path=record.path,
                    line=line,
                )
            )
        return ExtractionResult(
            file=record,
            nodes=nodes,
            edges=edges,
            chunks=chunk_text(record.path, text, document, "document"),
        )
