"""JSON config extraction."""

from __future__ import annotations

import json
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


class JsonExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "config", "json", text)
        file_node = make_file_node(record)
        metadata: dict[str, object] = {}
        try:
            parsed = json.loads(text)
            metadata = {"top_level_keys": list(parsed.keys()) if isinstance(parsed, dict) else []}
        except json.JSONDecodeError as exc:
            metadata = {"parse_error": str(exc)}
        config = Node(
            id=node_id("config", record.path),
            type="config",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="json",
            content_hash=record.content_hash,
            metadata=metadata,
            confidence=0.9 if "parse_error" in metadata else 1.0,
            confidence_tier="ambiguous" if "parse_error" in metadata else "extracted",
        )
        return ExtractionResult(
            file=record,
            nodes=[file_node, config],
            edges=[contains_edge(file_node, config, "json")],
            chunks=[make_chunk(record.path, text, "config", config)],
        )
