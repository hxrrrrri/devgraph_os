"""Safe .env extraction."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.ids import node_id
from devgraph.core.schema import ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    make_file_node,
    make_file_record,
    read_text,
)
from devgraph.retrieval.chunking import chunk_config


class EnvExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        raw = read_text(path)
        keys: list[str] = []
        safe_lines: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            keys.append(key)
            safe_lines.append(f"{key}=<redacted>")
        safe_text = "\n".join(safe_lines)
        record = make_file_record(root, path, "config", "env", safe_text)
        file_node = make_file_node(record)
        config = Node(
            id=node_id("config", record.path),
            type="config",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, raw.count("\n") + 1),
            language="env",
            content_hash=record.content_hash,
            metadata={"variable_names": keys, "values_stored": False},
        )
        return ExtractionResult(
            file=record,
            nodes=[file_node, config],
            edges=[contains_edge(file_node, config, "env")],
            chunks=chunk_config(record.path, safe_text, config),
        )
