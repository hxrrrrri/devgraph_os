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

    def review(
        self,
        base: str | None = None,
        staged: bool = False,
        files: Sequence[str] | None = None,
    ) -> ReviewResult:
        base_ref = base
        changes = changed_files(self.root, base=base_ref, staged=staged)
        selected_files = [_normalize_review_path(path) for path in files or []]
        if selected_files:
            change_by_path = {change.path: change for change in changes}
            selected_changes = [
                change_by_path.get(path) for path in selected_files if path in change_by_path
            ]
            files_to_review = selected_files
        else:
            selected_changes = list(changes)
            files_to_review = [change.path for change in changes]
        changed_nodes = self.store.nodes_for_files(files_to_review)
        impacted_nodes = self.store.impacted_nodes([node.id for node in changed_nodes], depth=self.config.review.max_depth)
        related_tests = self.store.tests_for_nodes([node.id for node in changed_nodes])
        impacted_files = sorted({node.file_path for node in impacted_nodes if node.file_path})
        affected_tests = sorted(
            {
                node.file_path or node.qualified_name
                for node in [*changed_nodes, *impacted_nodes, *related_tests]
                if node.type == "test"
            }
        )
        missing_tests = [] if affected_tests else ["No directly related tests found in the graph."]
        score, reasons = score_risk(files_to_review, changed_nodes, impacted_nodes)
        changed_snippets = {
            path: self._changed_snippet(path, base=base_ref, staged=staged)
            for path in files_to_review[:20]
        }
        diff_summary = self._diff_summary(files_to_review, changed_snippets)
        packer = ContextPacker(self.store)
        context = packer.pack(
            ContextRequest(
                task_type="review",
                query=" ".join(files_to_review[:5]),
                seed_files=files_to_review,
                token_budget=self.config.review.token_budget,
                include_source=True,
                base_branch=base_ref,
                diff_snippets=changed_snippets,
            )
        )
        result = ReviewResult(
            changed_files=files_to_review,
            changed_nodes=changed_nodes,
            impacted_nodes=impacted_nodes,
            impacted_files=impacted_files,
            affected_tests=affected_tests,
            missing_tests=missing_tests,
            diff_summary=diff_summary,
            changed_snippets=changed_snippets,
            risk_score=score,
            risk_level=risk_level(score),
            risk_explanation=reasons,
            review_checklist=self._checklist(files_to_review, changed_nodes),
            context_pack=context,
            suggested_commands=self._suggested_commands(affected_tests),
            warnings=self._warnings(files_to_review, selected_changes),
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

    def _changed_snippet(self, path: str, base: str | None, staged: bool) -> str:
        patch = diff_patch(self.root, path, base=base, staged=staged)
        if patch:
            return _trim_patch(patch)
        file_path = self.root / path
        if file_path.exists() and file_path.is_file():
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                return "No readable diff or source excerpt available."
            excerpt = "\n".join(f"{index + 1}: {line}" for index, line in enumerate(lines[:80]))
            return f"No git diff available. Current file excerpt:\n{excerpt}"
        return "No readable diff or source excerpt available."

    @staticmethod
    def _diff_summary(files: list[str], snippets: dict[str, str]) -> list[str]:
        summary: list[str] = []
        for path in files:
            snippet = snippets.get(path, "")
            added = sum(1 for line in snippet.splitlines() if line.startswith("+") and not line.startswith("+++"))
            removed = sum(1 for line in snippet.splitlines() if line.startswith("-") and not line.startswith("---"))
            if added or removed:
                summary.append(f"{path}: +{added}/-{removed} lines in available diff.")
            else:
                summary.append(f"{path}: no git diff available; using graph/source context.")
        return summary

    @staticmethod
    def _warnings(files: list[str], selected_changes: Sequence[object | None]) -> list[str]:
        warnings: list[str] = []
        if files and not selected_changes:
            warnings.append("Review was scoped with --files; git change metadata was not available for those paths.")
        if not files:
            warnings.append("No changed files were detected. Use --files to review specific paths.")
        return warnings

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
    diff_summary = [f"- {item}" for item in result.diff_summary] or ["- No diff summary available."]
    warnings = [f"- {item}" for item in result.warnings]
    lines = [
        "# DevGraph Review",
        "",
        f"Risk: **{result.risk_level}** ({result.risk_score}/100)",
        "",
        *([] if not warnings else ["## Warnings", *warnings, ""]),
        "## Changed files",
        *changed_files,
        "",
        "## Diff summary",
        *diff_summary,
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


def _normalize_review_path(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def _trim_patch(patch: str, max_lines: int = 160) -> str:
    lines = patch.splitlines()
    if len(lines) <= max_lines:
        return patch
    return "\n".join([*lines[:max_lines], f"... truncated {len(lines) - max_lines} diff lines ..."])
