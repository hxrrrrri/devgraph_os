"""Kubernetes manifest extraction."""

from __future__ import annotations

from pathlib import Path

import yaml

from devgraph.core.ids import node_id
from devgraph.core.schema import ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    make_file_node,
    make_file_record,
    read_text,
    redact_secrets,
)
from devgraph.retrieval.chunking import chunk_config


class KubernetesExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = redact_secrets(read_text(path))
        record = make_file_record(root, path, "infra", "kubernetes", text)
        file_node = make_file_node(record)
        resources: list[dict[str, object]] = []
        warnings: list[str] = []
        try:
            documents = [doc for doc in yaml.safe_load_all(text) if isinstance(doc, dict)]
            for document in documents:
                metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
                resources.append(
                    {
                        "apiVersion": document.get("apiVersion"),
                        "kind": document.get("kind"),
                        "name": metadata.get("name") if isinstance(metadata, dict) else None,
                    }
                )
        except yaml.YAMLError as exc:
            warnings.append(f"Kubernetes YAML parse failed for {record.path}: {exc}")
        manifest = Node(
            id=node_id("resource", record.path),
            type="resource",
            name=Path(record.path).name,
            qualified_name=record.path,
            file_path=record.path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="kubernetes",
            content_hash=record.content_hash,
            metadata={"resources": resources, "kind": "kubernetes-manifest"},
            confidence=0.9 if warnings else 1.0,
            confidence_tier="ambiguous" if warnings else "extracted",
        )
        return ExtractionResult(
            file=record,
            nodes=[file_node, manifest],
            edges=[contains_edge(file_node, manifest, "kubernetes")],
            chunks=chunk_config(record.path, text, manifest),
            warnings=warnings,
        )
