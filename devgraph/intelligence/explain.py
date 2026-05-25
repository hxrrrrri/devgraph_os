"""Explain and ask workflows."""

from __future__ import annotations

from devgraph.core.graph_store import GraphStore
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest


class ExplainEngine:
    def __init__(self, store: GraphStore) -> None:
        self.store = store
        self.packer = ContextPacker(store)

    def explain(self, target: str, budget: str = "normal") -> str:
        seed_files = [target] if self._looks_like_file(target) else []
        return self.packer.pack(
            ContextRequest(
                task_type="explain",
                query=target,
                seed_files=seed_files,
                token_budget=budget,
                include_source=True,
            )
        )

    def ask(self, question: str, budget: str = "normal") -> str:
        return self.packer.pack(
            ContextRequest(
                task_type="ask",
                query=question,
                token_budget=budget,
                include_source=True,
            )
        )

    @staticmethod
    def _looks_like_file(value: str) -> bool:
        return "/" in value or "\\" in value or "." in value.rsplit("/", 1)[-1]

