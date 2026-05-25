"""Risk-scored review engine."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Node, ReviewResult
from devgraph.intelligence.risk import risk_level, score_risk
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest
from devgraph.update.git import changed_files, diff_patch


class ReviewEngine:
    def __init__(self, root: Path, config: DevGraphConfig, store: GraphStore) -> None:
        self.root = root
        self.config = config
        self.store = store

    def review(self, base: str | None = None, staged: bool = False) -> ReviewResult:
        base_ref = base
        changes = changed_files(self.root, base=base_ref, staged=staged)
        files = [change.path for change in changes]
        changed_nodes = self.store.nodes_for_files(files)
        impacted_nodes = self.store.impacted_nodes([node.id for node in changed_nodes], depth=self.config.review.max_depth)
        impacted_files = sorted({node.file_path for node in impacted_nodes if node.file_path})
        affected_tests = sorted(
            {
                node.file_path or node.qualified_name
                for node in [*changed_nodes, *impacted_nodes]
                if node.type == "test"
            }
        )
        missing_tests = [] if affected_tests else ["No directly related tests found in the graph."]
        score, reasons = score_risk(files, changed_nodes, impacted_nodes)
        packer = ContextPacker(self.store)
        context = packer.pack(
            ContextRequest(
                task_type="review",
                query=" ".join(files[:5]),
                seed_files=files,
                token_budget=self.config.review.token_budget,
                include_source=True,
                base_branch=base_ref,
            )
        )
        result = ReviewResult(
            changed_files=files,
            changed_nodes=changed_nodes,
            impacted_nodes=impacted_nodes,
            impacted_files=impacted_files,
            affected_tests=affected_tests,
            missing_tests=missing_tests,
            risk_score=score,
            risk_level=risk_level(score),
            risk_explanation=reasons,
            review_checklist=self._checklist(files, changed_nodes),
            context_pack=context,
            suggested_commands=self._suggested_commands(affected_tests),
        )
        self._write_reports(result, base_ref, staged)
        return result

    def _write_reports(self, result: ReviewResult, base: str | None, staged: bool) -> None:
        reports = self.store.storage_path / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "review.md").write_text(format_review_markdown(result), encoding="utf-8")
        payload = result.model_dump(mode="json")
        payload["base"] = base
        payload["staged"] = staged
        payload["patches"] = {
            path: diff_patch(self.root, path, base=base, staged=staged)
            for path in result.changed_files[:20]
        }
        (reports / "review.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _checklist(files: list[str], changed_nodes: Sequence[Node]) -> list[str]:
        checklist = [
            "Verify changed behavior against related tests.",
            "Inspect graph impacted files for unintended blast radius.",
            "Check confidence tiers before treating inferred facts as certain.",
        ]
        if any(path.endswith((".yml", ".yaml", ".toml", ".json", ".env")) for path in files):
            checklist.append("Validate config and infrastructure changes in a clean environment.")
        if any("auth" in path.lower() or "token" in path.lower() for path in files):
            checklist.append("Review authentication, authorization, and secret-handling paths.")
        if not any(getattr(node, "type", None) == "test" for node in changed_nodes):
            checklist.append("Add or update tests for the changed behavior.")
        return checklist

    @staticmethod
    def _suggested_commands(affected_tests: list[str]) -> list[str]:
        commands = ["devgraph explain <changed-file-or-symbol>", "devgraph handoff"]
        if affected_tests:
            commands.insert(0, "Run related tests listed in the review output.")
        return commands


def format_review_markdown(result: ReviewResult) -> str:
    changed_files = [f"- `{path}`" for path in result.changed_files] or ["- No changed files detected."]
    impacted_files = [f"- `{path}`" for path in result.impacted_files] or [
        "- No impacted files detected."
    ]
    affected_tests = [f"- `{test}`" for test in result.affected_tests] or [
        "- No directly affected tests found."
    ]
    missing_tests = [f"- {item}" for item in result.missing_tests] or [
        "- No missing-test signal found."
    ]
    lines = [
        "# DevGraph Review",
        "",
        f"Risk: **{result.risk_level}** ({result.risk_score}/100)",
        "",
        "## Changed files",
        *changed_files,
        "",
        "## Impacted files",
        *impacted_files,
        "",
        "## Risk explanation",
        *[f"- {reason}" for reason in result.risk_explanation],
        "",
        "## Affected tests",
        *affected_tests,
        "",
        "## Missing tests",
        *missing_tests,
        "",
        "## Review checklist",
        *[f"- [ ] {item}" for item in result.review_checklist],
        "",
        "## Suggested commands",
        *[f"- `{command}`" for command in result.suggested_commands],
        "",
        result.context_pack,
    ]
    return "\n".join(lines)
