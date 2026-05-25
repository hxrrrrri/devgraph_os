"""Graph-grounded context packer."""

from __future__ import annotations

from dataclasses import dataclass, field

from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Node
from devgraph.retrieval.ranking import rank_nodes
from devgraph.retrieval.token_budget import budget_tokens, trim_to_budget


@dataclass
class ContextRequest:
    task_type: str
    query: str = ""
    seed_files: list[str] = field(default_factory=list)
    seed_nodes: list[str] = field(default_factory=list)
    token_budget: str = "normal"
    include_source: bool = True
    base_branch: str | None = None
    diff_snippets: dict[str, str] = field(default_factory=dict)


class ContextPacker:
    def __init__(self, store: GraphStore) -> None:
        self.store = store

    def pack(self, request: ContextRequest) -> str:
        seeds = self._seed_nodes(request)
        neighborhood = self.store.get_neighborhood([node.id for node in seeds], depth=1, limit=80)
        related_nodes = [Node(**node) for node in neighborhood["nodes"]]
        deduped_nodes = {node.id: node for node in [*seeds, *related_nodes]}
        ranked_nodes = rank_nodes(list(deduped_nodes.values()), request.query)
        relevant_files = sorted({node.file_path for node in ranked_nodes if node.file_path})
        chunks = []
        if request.include_source:
            for file_path in relevant_files[:8]:
                chunks.extend(self.store.get_chunks_for_file(file_path, limit=1))
        memories = self.store.relevant_memories(request.query, limit=6)
        lines = [
            "# DevGraph Context Pack",
            "",
            "## Task",
            request.task_type,
            "",
            "## Summary",
            self._summary(request, ranked_nodes, relevant_files),
            "",
            "## High-confidence facts",
            *self._facts(ranked_nodes),
            "",
            "## Relevant files",
            *[f"- `{path}`" for path in relevant_files[:20]],
            "",
            "## Relevant symbols",
            *[
                f"- `{node.qualified_name}` ({node.type}, {node.confidence_tier})"
                for node in ranked_nodes[:30]
            ],
            "",
            "## Graph paths",
            *self._graph_edges(neighborhood["edges"]),
            "",
            "## Changed code snippets",
            *self._diff_snippets(request.diff_snippets),
            "",
            "## Tests",
            *self._tests(ranked_nodes),
            "",
            "## Project memories",
            *self._memories(memories),
            "",
            "## Docs/configs",
            *[
                f"- `{node.qualified_name}` ({node.type})"
                for node in ranked_nodes
                if node.type in {"document", "section", "config"}
            ][:20],
            "",
            "## Risks / uncertainty",
            *self._uncertainty(ranked_nodes),
            "",
            "## Suggested next actions",
            *self._actions(request),
        ]
        if chunks:
            lines.extend(["", "## Source excerpts"])
            for chunk in chunks[:8]:
                line_range = f"{chunk.line_start or 1}-{chunk.line_end or '?'}"
                lines.extend(
                    [
                        f"### `{chunk.file_path}` lines {line_range}",
                        "```",
                        chunk.content[:2500],
                        "```",
                    ]
                )
        return trim_to_budget("\n".join(lines), budget_tokens(request.token_budget))

    def _seed_nodes(self, request: ContextRequest) -> list[Node]:
        nodes: list[Node] = []
        for node_id in request.seed_nodes:
            node = self.store.get_node(node_id)
            if node:
                nodes.append(node)
        if request.seed_files:
            nodes.extend(self.store.nodes_for_files(request.seed_files))
        if request.query:
            nodes.extend(self.store.find_nodes(request.query, limit=12))
        deduped: dict[str, Node] = {node.id: node for node in nodes}
        return list(deduped.values())

    @staticmethod
    def _summary(request: ContextRequest, nodes: list[Node], files: list[str]) -> str:
        if not nodes:
            return f"No graph nodes matched `{request.query}`. Try `devgraph build` or a more specific query."
        return (
            f"Found {len(nodes)} relevant graph nodes across {len(files)} files for "
            f"`{request.query or request.task_type}`."
        )

    @staticmethod
    def _facts(nodes: list[Node]) -> list[str]:
        facts = [
            f"- `{node.qualified_name}` is a `{node.type}` from `{node.file_path}`."
            for node in nodes
            if node.confidence_tier == "extracted" and node.file_path
        ]
        return facts[:20] or ["- No high-confidence parser facts matched the request."]

    @staticmethod
    def _graph_edges(edges: list[dict[str, object]]) -> list[str]:
        lines = [
            f"- `{edge['source_id']}` --{edge['type']}--> `{edge['target_id']}` "
            f"(source: `{edge.get('provenance_source', 'unknown')}`)"
            for edge in edges[:20]
        ]
        return lines or ["- No graph paths found for the current seed nodes."]

    @staticmethod
    def _diff_snippets(snippets: dict[str, str]) -> list[str]:
        if not snippets:
            return ["No diff snippets were provided to this context pack."]
        lines: list[str] = []
        for path, snippet in list(snippets.items())[:8]:
            lines.extend([f"### `{path}`", "```diff", snippet[:3000], "```"])
        return lines

    @staticmethod
    def _memories(memories: list[dict[str, object]]) -> list[str]:
        if not memories:
            return ["- No user-approved project memories matched this request."]
        lines = []
        for memory in memories:
            lines.append(
                f"- `{memory['id']}` ({memory['kind']}): {str(memory['content'])[:240]}"
            )
        return lines

    @staticmethod
    def _tests(nodes: list[Node]) -> list[str]:
        tests = [f"- `{node.qualified_name}`" for node in nodes if node.type == "test"]
        return tests[:20] or ["- No directly related tests were found."]

    @staticmethod
    def _uncertainty(nodes: list[Node]) -> list[str]:
        uncertain = [
            f"- `{node.qualified_name}` has confidence tier `{node.confidence_tier}`."
            for node in nodes
            if node.confidence_tier != "extracted"
        ]
        return uncertain[:20] or ["- No non-extracted facts are required for this context pack."]

    @staticmethod
    def _actions(request: ContextRequest) -> list[str]:
        if request.task_type == "review":
            return ["- Run the related tests listed above.", "- Inspect changed public APIs and configs."]
        if request.task_type == "debug":
            return ["- Start from suspected entry points.", "- Check callers, configs, and recent changes."]
        if request.task_type == "onboard":
            return ["- Read the listed files first.", "- Ask DevGraph follow-up questions by subsystem."]
        return ["- Use `devgraph explain <symbol-or-file>` for a narrower context pack."]
