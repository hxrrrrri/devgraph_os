"""GitHub Actions extraction."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.ids import node_id
from devgraph.core.schema import ExtractionResult, Node
from devgraph.extractors.base import contains_edge
from devgraph.extractors.config.yaml_parser import YamlExtractor


class GitHubActionsExtractor(YamlExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        result = super().extract(root, path)
        pipeline = Node(
            id=node_id("pipeline", result.file.path),
            type="pipeline",
            name=Path(result.file.path).name,
            qualified_name=result.file.path,
            file_path=result.file.path,
            line_start=1,
            line_end=None,
            language="github-actions",
            content_hash=result.file.content_hash,
            metadata={"provider": "github-actions"},
        )
        result.nodes.append(pipeline)
        result.edges.append(contains_edge(result.nodes[0], pipeline, "github-actions"))
        result.file.category = "infra"
        result.file.language = "github-actions"
        return result

