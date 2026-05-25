"""Plain text document extraction."""

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


class TextExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "document", "text", text)
        file_node = make_file_node(record)
        document = Node(
            id=node_id("document", record.path),
            type="document",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="text",
            content_hash=record.content_hash,
        )
        return ExtractionResult(
            file=record,
            nodes=[file_node, document],
            edges=[contains_edge(file_node, document, "text")],
            chunks=[make_chunk(record.path, text, "document", document)],
        )

