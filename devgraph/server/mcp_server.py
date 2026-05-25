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
from devgraph.update.incremental import build_graph, update_graph


class DevGraphMcpTools:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()
        self.config = load_config(self.root)
        self.store = GraphStore(self.root, self.root / self.config.storage.path)

    def build_or_update_graph(self, incremental: bool = True) -> dict[str, Any]:
        stats = update_graph(self.root, self.config, self.store) if incremental else build_graph(
            self.root, self.config, self.store, force=True
        )
        return stats.__dict__

    def get_project_status(self) -> dict[str, Any]:
        return self.store.get_status(self.config.project.name).model_dump()

    def get_context(
        self,
        task_type: str,
        query: str = "",
        token_budget: str = "normal",  # nosec B107
        include_source: bool = True,
    ) -> dict[str, Any]:
        pack = ContextPacker(self.store).pack(
            ContextRequest(
                task_type=task_type,
                query=query,
                token_budget=token_budget,
                include_source=include_source,
            )
        )
        return {"context_pack": pack}

    def review_changes(self, base: str | None = None, staged: bool = False) -> dict[str, Any]:
        return ReviewEngine(self.root, self.config, self.store).review(base=base, staged=staged).model_dump(mode="json")

    def debug_issue(self, issue: str) -> dict[str, Any]:
        return {"context_pack": DebugEngine(self.store).debug(issue)}

    def explain(self, target: str) -> dict[str, Any]:
        return {"context_pack": ExplainEngine(self.store).explain(target)}

    def query_graph(self, query: str, limit: int = 20) -> dict[str, Any]:
        return self.store.search(query, limit=limit)

    def find_path(self, source: str, target: str) -> dict[str, Any]:
        return {"path": [node.model_dump() for node in self.store.find_path(source, target)]}

    def trace_flow(self, query: str) -> dict[str, Any]:
        return trace_flow(self.store, query)

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        return self.store.search(query, limit=limit)

    def generate_onboarding(self) -> dict[str, Any]:
        path = OnboardingEngine(self.root, self.store).generate()
        return {"path": str(path)}

    def handoff_session(self) -> dict[str, Any]:
        markdown, data = HandoffEngine(self.root, self.config, self.store).generate()
        return {"markdown": str(markdown), "json": str(data)}


def run_mcp_server(root: Path | None = None) -> None:
    tools = DevGraphMcpTools(root)
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError("Install MCP support with `pip install devgraph-os[mcp]`.") from exc

    server = FastMCP("devgraph-os")
    server.tool()(tools.build_or_update_graph)
    server.tool()(tools.get_project_status)
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
    server.run()
