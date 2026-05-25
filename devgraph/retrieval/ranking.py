"""Ranking helpers."""

from __future__ import annotations

from devgraph.core.schema import Node


def rank_nodes(nodes: list[Node], query: str = "") -> list[Node]:
    lowered = query.lower()

    def score(node: Node) -> tuple[int, int, str]:
        exact = 2 if lowered and lowered in node.qualified_name.lower() else 0
        high_confidence = 1 if node.confidence_tier == "extracted" else 0
        return (exact, high_confidence, node.qualified_name)

    return sorted(nodes, key=score, reverse=True)

