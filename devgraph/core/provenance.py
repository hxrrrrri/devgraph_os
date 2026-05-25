"""Provenance utilities."""

from __future__ import annotations

from devgraph.core.schema import ConfidenceTier


def tier_description(tier: ConfidenceTier) -> str:
    descriptions = {
        "extracted": "deterministic parser result",
        "inferred": "deterministic but indirect inference",
        "llm": "model-generated semantic enrichment",
        "ambiguous": "uncertain result needing user review",
        "user": "user-approved or manually added knowledge",
    }
    return descriptions[tier]

