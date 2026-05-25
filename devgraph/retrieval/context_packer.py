"""Graph-grounded context packer."""

from __future__ import annotations

from dataclasses import dataclass, field

from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Chunk, Node
from devgraph.retrieval.embeddings import semantic_search
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
        semantic_matches = semantic_search(self.store, request.query, limit=8)
        relevant_files = sorted({node.file_path for node in ranked_nodes if node.file_path})
        relevant_files = sorted(
            {
                *relevant_files,
                *(
                    str(match["file_path"])
                    for match in semantic_matches
                    if match.get("file_path")
                ),
            }
        )
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
            "## Intent",
            self._intent(request),
            "",
            "## Direct answer basis",
            self._summary(request, ranked_nodes, relevant_files),
            "",
            "## High-confidence parser facts",
            *self._facts(ranked_nodes),
            "",
            "## Changed files and symbols",
            *self._changed_area(request, ranked_nodes),
            "",
            "## Impacted graph area",
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
            "## Relevant source excerpts",
            *self._source_excerpts(chunks[:8]),
            "",
            "## Relevant tests",
            *self._tests(ranked_nodes),
            "",
            "## Relevant docs/config/infra",
            *[
                f"- `{node.qualified_name}` ({node.type}, {node.confidence_tier})"
                for node in ranked_nodes
                if node.type in {"document", "section", "config", "resource", "pipeline"}
            ][:20],
            "",
            "## Memories / decisions",
            *self._memories(memories),
            "",
            "## Semantic matches",
            *self._semantic_matches(semantic_matches),
            "",
            "## Risks / uncertainty",
            *self._uncertainty(ranked_nodes),
            "",
            "## Recommended next actions",
            *self._actions(request),
        ]
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
            semantic_nodes = semantic_search(
                self.store, request.query, limit=8, entity_types=["node"]
            )
            for match in semantic_nodes:
                node = self.store.get_node(str(match["entity_id"]))
                if node:
                    nodes.append(node)
        deduped: dict[str, Node] = {node.id: node for node in nodes}
        return list(deduped.values())

    @staticmethod
    def _intent(request: ContextRequest) -> str:
        intents = {
            "review": "Assess changed files, impacted symbols, risk signals, and test coverage gaps.",
            "debug": "Map symptoms or stack frames to likely entry points, callers, callees, tests, and configs.",
            "explain": "Explain the requested file, symbol, or subsystem from parser facts and graph context.",
            "ask": "Answer a project question using graph facts, chunks, docs, configs, and memories.",
            "onboard": "Prioritize read-first files, major symbols, architecture layers, and glossary terms.",
            "refactor": "Identify dependent symbols, callers, tests, and risk before changing structure.",
            "handoff": "Preserve current project status, decisions, changed areas, and next-agent instructions.",
        }
        return intents.get(request.task_type, "Provide graph-grounded context for the requested task.")

    @staticmethod
    def _summary(request: ContextRequest, nodes: list[Node], files: list[str]) -> str:
        if not nodes:
            return f"No graph nodes matched `{request.query}`. Try `devgraph build` or a more specific query."
        return (
            f"Found {len(nodes)} relevant graph nodes across {len(files)} files for "
            f"`{request.query or request.task_type}`."
        )

    @staticmethod
    def _changed_area(request: ContextRequest, nodes: list[Node]) -> list[str]:
        lines = [f"- File: `{path}`" for path in request.seed_files[:20]]
        if request.seed_nodes:
            seeded = [node for node in nodes if node.id in set(request.seed_nodes)]
            lines.extend(
                f"- Symbol: `{node.qualified_name}` ({node.type}, lines {node.line_start}-{node.line_end})"
                for node in seeded[:20]
            )
        return lines or ["- No changed files or explicit seed symbols were provided."]

    @staticmethod
    def _facts(nodes: list[Node]) -> list[str]:
        facts = [
            f"- `{node.qualified_name}` is a `{node.type}` from `{node.file_path}`."
            for node in nodes
            if node.confidence_tier == "extracted" and node.file_path
        ]
        return facts[:20] or ["- No high-confidence parser facts matched the request."]

    def _graph_edges(self, edges: list[dict[str, object]]) -> list[str]:
        lines = []
        for edge in edges[:20]:
            source = self.store.get_node(str(edge["source_id"]))
            target = self.store.get_node(str(edge["target_id"]))
            if source is None or target is None:
                continue
            lines.append(
                f"- `{_display_node(source)}` --{edge['type']}--> `{_display_node(target)}` "
                f"(source: `{edge.get('provenance_source', 'unknown')}`)"
            )
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
    def _source_excerpts(chunks: list[Chunk]) -> list[str]:
        if not chunks:
            return ["- No focused source chunks were selected."]
        lines: list[str] = []
        for chunk in chunks:
            line_range = f"{chunk.line_start or 1}-{chunk.line_end or '?'}"
            lines.extend(
                [
                    f"### `{chunk.file_path}` lines {line_range} ({chunk.kind})",
                    "```",
                    chunk.content[:2500],
                    "```",
                ]
            )
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
    def _semantic_matches(matches: list[dict[str, object]]) -> list[str]:
        if not matches:
            return ["- No local embedding matches were available."]
        lines = []
        for match in matches:
            score = float(str(match["score"]))
            file_path = match.get("file_path") or "graph"
            lines.append(
                f"- `{match['entity_id']}` ({match['entity_type']}, {score:.2f}) from `{file_path}`"
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
        if request.task_type == "handoff":
            return ["- Start with `devgraph status --json`.", "- Run `devgraph review --json` before editing."]
        return ["- Use `devgraph explain <symbol-or-file>` for a narrower context pack."]


def _display_node(node: Node) -> str:
    if node.file_path and node.line_start:
        return f"{node.qualified_name}"
    return node.qualified_name
