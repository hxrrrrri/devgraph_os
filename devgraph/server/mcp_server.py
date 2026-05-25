"""MCP server tool surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devgraph.config import load_config
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.debug import DebugEngine
from devgraph.intelligence.explain import ExplainEngine
from devgraph.intelligence.flows import trace_flow
from devgraph.intelligence.handoff import HandoffEngine
from devgraph.intelligence.onboard import OnboardingEngine
from devgraph.intelligence.review import ReviewEngine
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest
from devgraph.retrieval.search import search_graph
from devgraph.update.incremental import build_graph, update_graph


class DevGraphMcpTools:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()
        self.config = load_config(self.root)
        self.store = GraphStore(self.root, self.root / self.config.storage.path)

    def build_or_update_graph(self, incremental: bool = True) -> dict[str, Any]:
        """Build or incrementally update the local DevGraph graph."""
        stats = update_graph(self.root, self.config, self.store) if incremental else build_graph(
            self.root, self.config, self.store, force=True
        )
        return stats.__dict__

    def get_project_status(self) -> dict[str, Any]:
        """Return graph counts, freshness, languages, and warnings."""
        return self.store.get_status(self.config.project.name).model_dump()

    def doctor(self) -> dict[str, Any]:
        """Check local privacy/configuration readiness without external calls."""
        status = self.store.get_status(self.config.project.name)
        issues: list[str] = []
        if self.config.privacy.allow_llm_enrichment:
            issues.append("LLM enrichment is enabled. Confirm external model privacy settings before use.")
        if self.config.privacy.store_env_values:
            issues.append("store_env_values is enabled. This can persist secrets and is not recommended.")
        if status.total_nodes == 0:
            issues.append("Graph has no nodes. Run `devgraph build`.")
        embedding_count = self.store.connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        return {
            "project_root": str(self.root),
            "issues": issues,
            "status": status.model_dump(),
            "privacy": self.config.privacy.model_dump(),
            "retrieval": {
                **self.config.retrieval.model_dump(),
                "indexed_embeddings": embedding_count,
            },
        }

    def get_context(
        self,
        task_type: str,
        query: str = "",
        token_budget: str = "normal",  # nosec B107
        include_source: bool = True,
    ) -> dict[str, Any]:
        """Create a task-specific context pack for AI coding agents."""
        pack = ContextPacker(self.store).pack(
            ContextRequest(
                task_type=task_type,
                query=query,
                token_budget=token_budget,
                include_source=include_source,
            )
        )
        return {"context_pack": pack}

    def review_changes(
        self,
        base: str | None = None,
        staged: bool = False,
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Review current git changes with changed symbols, impact, risk, and context."""
        return ReviewEngine(self.root, self.config, self.store).review(
            base=base, staged=staged, files=files
        ).model_dump(mode="json")

    def debug_issue(self, issue: str) -> dict[str, Any]:
        """Parse an error/stack trace and return graph-grounded debug context."""
        engine = DebugEngine(self.store)
        analysis = engine.analyze(issue)
        analysis["markdown"] = engine.debug(issue)
        return analysis

    def explain(self, target: str) -> dict[str, Any]:
        """Explain a file, symbol, module, concept, or flow."""
        return {"context_pack": ExplainEngine(self.store).explain(target)}

    def query_graph(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Search graph nodes and chunks using local FTS and optional embeddings."""
        return search_graph(self.store, query, limit=limit, config=self.config)

    def find_path(self, source: str, target: str) -> dict[str, Any]:
        """Find a readable graph path between two node queries."""
        return {"path": [node.model_dump() for node in self.store.find_path(source, target)]}

    def trace_flow(self, query: str) -> dict[str, Any]:
        """Trace a local dependency/call neighborhood around a query."""
        return trace_flow(self.store, query)

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Search the graph with agent-friendly JSON output."""
        return search_graph(self.store, query, limit=limit, config=self.config)

    def generate_onboarding(self) -> dict[str, Any]:
        """Generate the local onboarding report and return its path."""
        path = OnboardingEngine(self.root, self.store).generate()
        return {"path": str(path)}

    def handoff_session(self) -> dict[str, Any]:
        """Generate cross-agent handoff markdown and JSON artifacts."""
        markdown, data = HandoffEngine(self.root, self.config, self.store).generate()
        return {"markdown": str(markdown), "json": str(data)}

    def remember(self, kind: str, content: str) -> dict[str, Any]:
        """Store a redacted user-approved memory."""
        memory_id = self.store.remember(kind=kind, content=content)
        return {"id": memory_id}

    def list_memories(self, kind: str | None = None, limit: int = 50) -> dict[str, Any]:
        """List project memories, optionally filtered by kind."""
        return {"memories": self.store.list_memories(kind=kind, limit=limit)}

    def forget_memory(self, memory_id: str) -> dict[str, Any]:
        """Delete a project memory by id."""
        return {"deleted": self.store.forget_memory(memory_id)}

    def get_node_detail(self, node_id: str) -> dict[str, Any]:
        """Return a graph node, provenance, chunks, and one-hop neighborhood."""
        node = self.store.get_node(node_id)
        if node is None:
            return {"error": f"Node not found: {node_id}"}
        chunks = self.store.get_chunks_for_file(node.file_path, limit=10) if node.file_path else []
        return {
            "node": node.model_dump(),
            "provenance": self.store.provenance_for_entity(node.id),
            "chunks": [chunk.model_dump() for chunk in chunks if chunk.node_id in {None, node.id}],
            "neighborhood": self.store.get_neighborhood([node.id], depth=1, limit=40),
        }

    def get_file_context(self, path: str) -> dict[str, Any]:
        """Return nodes and focused chunks for a project-relative file path."""
        safe_path = Path(path).as_posix().lstrip("./")
        nodes = self.store.nodes_for_files([safe_path])
        chunks = self.store.get_chunks_for_file(safe_path, limit=20)
        return {
            "file_path": safe_path,
            "nodes": [node.model_dump() for node in nodes],
            "chunks": [chunk.model_dump() for chunk in chunks],
        }

    def get_review_artifacts(self) -> dict[str, Any]:
        """Return the latest review markdown/JSON artifacts when available."""
        reports = self.store.storage_path / "reports"
        payload: dict[str, Any] = {}
        for name in ("review.md", "review.json"):
            path = reports / name
            if path.exists():
                payload[name] = path.read_text(encoding="utf-8")
        return payload

    def get_provenance(self, entity_id: str) -> dict[str, Any]:
        """Return provenance records for a node, edge, chunk, or memory id."""
        return {"provenance": self.store.provenance_for_entity(entity_id)}

    def list_snapshots(self, limit: int = 20) -> dict[str, Any]:
        """List local graph snapshots."""
        rows = self.store.connection.execute(
            "SELECT * FROM snapshots ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return {"snapshots": [dict(row) for row in rows]}


def run_mcp_server(root: Path | None = None) -> None:
    tools = DevGraphMcpTools(root)
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError("Install MCP support with `pip install devgraph-os[mcp]`.") from exc

    server = FastMCP("devgraph-os")
    server.tool()(tools.build_or_update_graph)
    server.tool()(tools.get_project_status)
    server.tool()(tools.doctor)
    server.tool()(tools.get_context)
    server.tool()(tools.review_changes)
    server.tool()(tools.debug_issue)
    server.tool()(tools.explain)
    server.tool()(tools.query_graph)
    server.tool()(tools.find_path)
    server.tool()(tools.trace_flow)
    server.tool()(tools.search)
    server.tool()(tools.generate_onboarding)
    server.tool()(tools.handoff_session)
    server.tool()(tools.remember)
    server.tool()(tools.list_memories)
    server.tool()(tools.forget_memory)
    server.tool()(tools.get_node_detail)
    server.tool()(tools.get_file_context)
    server.tool()(tools.get_review_artifacts)
    server.tool()(tools.get_provenance)
    server.tool()(tools.list_snapshots)
    server.run()
