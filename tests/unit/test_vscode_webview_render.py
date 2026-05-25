"""Render-only sanity test for the VS Code review preview HTML.

We don't run TypeScript here — but we can exercise the data contract by
asserting the review.json structure includes the fields the webviews depend
on. Catches breakage in the schema -> webview pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

from devgraph.core.schema import ReviewResult


def test_review_result_payload_contains_v12_fields(tmp_path: Path) -> None:
    result = ReviewResult(
        changed_files=["a.py"],
        risk_score=10,
        risk_level="low",
        risk_explanation=["test"],
        review_checklist=[],
        context_pack="",
        suggested_commands=[],
    )
    payload = result.model_dump(mode="json")
    for key in (
        "migration_warnings",
        "api_signature_changes",
        "route_contract_changes",
        "fan_out",
        "infra_blast_radius",
        "severity_by_file",
        "severity_by_symbol",
    ):
        assert key in payload, f"missing field {key}"
    # JSON round-trip safe
    json.dumps(payload)


def test_review_preview_html_snippet_renders_severity_classes() -> None:
    """Smoke-check the severity class scheme used in reviewPreviewPanel."""

    # This test does NOT execute the TS panel — it only locks in the contract
    # that webviews depend on by asserting the classes/keys exist in the panel
    # source file.
    panel = Path("apps/vscode-extension/src/panels/reviewPreviewPanel.ts").read_text(
        encoding="utf-8"
    )
    assert "sev-high" in panel
    assert "sev-medium" in panel or "sev-med" in panel
    assert "severity_by_file" in panel
