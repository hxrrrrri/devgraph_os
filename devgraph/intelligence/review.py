"""Risk-scored review engine."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Node, ReviewResult
from devgraph.intelligence.compat import diff_public_api, diff_routes, load_snapshot
from devgraph.intelligence.migration_risk import detect_migration_warnings
from devgraph.intelligence.risk import risk_level, score_risk
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest
from devgraph.update.diff_parser import DiffHunk, hunks_for_files, map_hunks_to_nodes
from devgraph.update.git import changed_files, diff_patch, run_git


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
        previous_snapshot: Path | None = None,
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
        hunks = hunks_for_files(self.root, files_to_review, base=base_ref, staged=staged) if files_to_review else []
        hunk_mapping = map_hunks_to_nodes(self.store, hunks)
        changed_symbols = self._changed_symbols(hunk_mapping, files_to_review)
        changed_nodes = self.store.nodes_for_files(files_to_review)
        impact_seed_nodes = changed_symbols or changed_nodes
        impacted_nodes = self.store.impacted_nodes([node.id for node in impact_seed_nodes], depth=self.config.review.max_depth)
        related_tests = self.store.tests_for_nodes([node.id for node in impact_seed_nodes])
        impacted_files = sorted({node.file_path for node in impacted_nodes if node.file_path})
        affected_tests = sorted(
            {
                node.file_path or node.qualified_name
                for node in [*changed_nodes, *impacted_nodes, *related_tests]
                if node.type == "test"
            }
        )
        missing_tests = [] if affected_tests else ["No directly related tests found in the graph."]
        changed_line_count = sum(len(set(hunk.changed_lines)) for hunk in hunks)
        recent_churn = self._recent_churn(files_to_review)
        score, reasons = score_risk(
            files_to_review,
            changed_symbols or changed_nodes,
            impacted_nodes,
            changed_line_count=changed_line_count,
            affected_tests=affected_tests,
            recent_churn=recent_churn,
        )
        changed_snippets = {
            path: self._changed_snippet(path, base=base_ref, staged=staged)
            for path in files_to_review[:20]
        }
        diff_summary = self._diff_summary(files_to_review, changed_snippets)
        public_api_changes = self._public_api_changes(files_to_review, changed_symbols)
        config_or_infra_changes = self._config_or_infra_changes(files_to_review)
        database_or_schema_changes = self._database_or_schema_changes(files_to_review, changed_symbols)
        security_sensitive_changes = self._security_sensitive_changes(files_to_review, changed_symbols)
        migration_warnings = detect_migration_warnings(files_to_review, changed_snippets)
        snapshot_payload = (
            load_snapshot(previous_snapshot) if previous_snapshot is not None else None
        )
        if snapshot_payload is not None:
            all_current_nodes = self.store.all_nodes()
            api_signature_changes = diff_public_api(snapshot_payload, all_current_nodes)
            route_contract_changes = diff_routes(snapshot_payload, all_current_nodes)
        else:
            api_signature_changes = []
            route_contract_changes = []
        fan_out_entries = self._fan_out(changed_symbols, impacted_nodes)
        infra_blast_radius = self._infra_blast_radius(files_to_review)
        severity_by_file, severity_by_symbol = _severity_maps(
            migration_warnings,
            api_signature_changes,
            route_contract_changes,
            fan_out_entries,
        )
        packer = ContextPacker(self.store)
        context = packer.pack(
            ContextRequest(
                task_type="review",
                query=" ".join(files_to_review[:5]),
                seed_files=files_to_review,
                seed_nodes=[node.id for node in changed_symbols],
                token_budget=self.config.review.token_budget,
                include_source=True,
                base_branch=base_ref,
                diff_snippets=changed_snippets,
            )
        )
        result = ReviewResult(
            changed_files=files_to_review,
            changed_hunks=[_hunk_payload(hunk) for hunk in hunks],
            changed_symbols=changed_symbols,
            changed_nodes=changed_nodes,
            impacted_nodes=impacted_nodes,
            impacted_files=impacted_files,
            impacted_flows=self._impacted_flows(impact_seed_nodes),
            affected_tests=affected_tests,
            missing_tests=missing_tests,
            public_api_changes=public_api_changes,
            config_or_infra_changes=config_or_infra_changes,
            database_or_schema_changes=database_or_schema_changes,
            security_sensitive_changes=security_sensitive_changes,
            migration_warnings=migration_warnings,
            api_signature_changes=api_signature_changes,
            route_contract_changes=route_contract_changes,
            fan_out=fan_out_entries,
            infra_blast_radius=infra_blast_radius,
            severity_by_file=severity_by_file,
            severity_by_symbol=severity_by_symbol,
            diff_summary=diff_summary,
            changed_snippets=changed_snippets,
            risk_score=score,
            risk_level=risk_level(score),
            risk_explanation=reasons,
            prioritized_review_items=self._prioritized_items(
                public_api_changes,
                config_or_infra_changes,
                database_or_schema_changes,
                security_sensitive_changes,
                impacted_files,
                missing_tests,
                migration_warnings,
            ),
            review_checklist=self._checklist(files_to_review, changed_symbols or changed_nodes),
            context_pack=context,
            suggested_commands=self._suggested_commands(affected_tests, files_to_review),
            warnings=self._warnings(files_to_review, selected_changes),
        )
        self._write_reports(result, base_ref, staged)
        return result

    @staticmethod
    def _changed_symbols(hunk_mapping: dict[str, list[Node]], files: list[str]) -> list[Node]:
        symbols: dict[str, Node] = {}
        for nodes in hunk_mapping.values():
            for node in nodes:
                if node.type in {"module", "file"}:
                    continue
                symbols[node.id] = node
        return sorted(
            symbols.values(),
            key=lambda node: (files.index(node.file_path) if node.file_path in files else 10_000, node.line_start or 0),
        )

    def _recent_churn(self, files: list[str]) -> int:
        churn = 0
        for path in files[:20]:
            output = run_git(self.root, ["log", "--since=90 days ago", "--format=%H", "--", path])
            churn += len([line for line in output.splitlines() if line.strip()])
        return churn

    @staticmethod
    def _public_api_changes(files: list[str], symbols: Sequence[Node]) -> list[str]:
        public_paths = [
            path for path in files if any(part in path.lower() for part in ("api", "route", "server", "controller"))
        ]
        public_symbols = [
            node.qualified_name
            for node in symbols
            if node.type in {"api_endpoint", "class", "function", "type"} and not node.name.startswith("_")
        ]
        return sorted({*public_paths, *public_symbols})

    @staticmethod
    def _config_or_infra_changes(files: list[str]) -> list[str]:
        suffixes = (".yml", ".yaml", ".toml", ".json", ".env", ".tf", ".tfvars", "Dockerfile")
        hints = ("docker", "kubernetes", ".github", "workflow", "terraform")
        return sorted(
            path
            for path in files
            if path.endswith(suffixes) or any(hint in path.lower() for hint in hints)
        )

    @staticmethod
    def _database_or_schema_changes(files: list[str], symbols: Sequence[Node]) -> list[str]:
        path_hits = [
            path
            for path in files
            if any(hint in path.lower() for hint in ("schema", "migration", "database", "sql", "prisma", "alembic"))
        ]
        symbol_hits = [
            node.qualified_name for node in symbols if node.type in {"database_table", "schema"}
        ]
        return sorted({*path_hits, *symbol_hits})

    @staticmethod
    def _security_sensitive_changes(files: list[str], symbols: Sequence[Node]) -> list[str]:
        hints = ("auth", "token", "secret", "password", "permission", "crypto", "session", "jwt")
        path_hits = [path for path in files if any(hint in path.lower() for hint in hints)]
        symbol_hits = [
            node.qualified_name
            for node in symbols
            if any(hint in node.qualified_name.lower() for hint in hints)
        ]
        return sorted({*path_hits, *symbol_hits})

    def _fan_out(
        self,
        changed_symbols: Sequence[Node],
        impacted_nodes: Sequence[Node],
    ) -> list[dict[str, Any]]:
        if not changed_symbols:
            return []
        impacted_ids = {node.id for node in impacted_nodes}
        entries: list[dict[str, Any]] = []
        for symbol in changed_symbols:
            neighborhood = self.store.get_neighborhood([symbol.id], depth=2, limit=200)
            dependent_ids = {
                edge["source_id"]
                for edge in neighborhood["edges"]
                if edge["target_id"] == symbol.id
            }
            fan_in = len(dependent_ids)
            fan_out_count = len(
                {
                    edge["target_id"]
                    for edge in neighborhood["edges"]
                    if edge["source_id"] == symbol.id
                }
            )
            total_impacted = len(impacted_ids)
            ratio = (
                round(total_impacted / max(1, len(changed_symbols)), 3)
                if total_impacted
                else 0.0
            )
            entries.append(
                {
                    "qualified_name": symbol.qualified_name,
                    "file_path": symbol.file_path,
                    "fan_in": fan_in,
                    "fan_out": fan_out_count,
                    "impact_ratio": ratio,
                }
            )
        entries.sort(key=lambda item: (item["fan_in"] + item["fan_out"]), reverse=True)
        return entries[:10]

    def _infra_blast_radius(self, files: list[str]) -> list[dict[str, Any]]:
        infra_files = self._config_or_infra_changes(files)
        if not infra_files:
            return []
        entries: list[dict[str, Any]] = []
        for path in infra_files:
            path_lower = path.lower()
            if path_lower.endswith(".env") or path_lower.endswith("/.env") or path_lower == ".env":
                touched = self._env_dependents(path)
                category = "env"
            elif "dockerfile" in path_lower:
                touched = self._docker_dependents(path)
                category = "docker"
            elif path_lower.endswith((".tf", ".tfvars")):
                touched = self._terraform_dependents(path)
                category = "terraform"
            elif ".github" in path_lower and (path_lower.endswith(".yml") or path_lower.endswith(".yaml")):
                touched = self._workflow_dependents(path)
                category = "ci"
            elif any(hint in path_lower for hint in ("helm", "k8s", "kubernetes", "manifests")):
                touched = self._k8s_dependents(path)
                category = "k8s"
            else:
                touched = []
                category = "other"
            entries.append(
                {
                    "file_path": path,
                    "category": category,
                    "touched": touched,
                }
            )
        return entries

    def _env_dependents(self, path: str) -> list[str]:
        nodes = self.store.nodes_for_files([path])
        touched: set[str] = set()
        for node in nodes:
            for key in (node.metadata or {}).get("keys", []) or []:
                touched.add(f"env:{key}")
        return sorted(touched)

    def _docker_dependents(self, path: str) -> list[str]:
        services = [
            node.qualified_name
            for node in self.store.nodes_for_files([path])
            if node.type == "service"
        ]
        return sorted(set(services))

    def _terraform_dependents(self, path: str) -> list[str]:
        resources = [
            node.qualified_name
            for node in self.store.nodes_for_files([path])
            if node.type in {"resource", "service"}
        ]
        return sorted(set(resources))

    def _workflow_dependents(self, path: str) -> list[str]:
        pipelines = [
            node.qualified_name
            for node in self.store.nodes_for_files([path])
            if node.type in {"pipeline", "step"}
        ]
        return sorted(set(pipelines))

    def _k8s_dependents(self, path: str) -> list[str]:
        resources = [
            node.qualified_name
            for node in self.store.nodes_for_files([path])
            if node.type in {"resource", "service"}
        ]
        return sorted(set(resources))

    def _impacted_flows(self, nodes: Sequence[Node]) -> list[dict[str, object]]:
        flows: list[dict[str, object]] = []
        for node in nodes[:5]:
            neighborhood = self.store.get_neighborhood([node.id], depth=1, limit=20)
            if neighborhood["edges"]:
                flows.append(
                    {
                        "entry": node.qualified_name,
                        "node_count": len(neighborhood["nodes"]),
                        "edge_count": len(neighborhood["edges"]),
                    }
                )
        return flows

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
    def _prioritized_items(
        public_api_changes: list[str],
        config_or_infra_changes: list[str],
        database_or_schema_changes: list[str],
        security_sensitive_changes: list[str],
        impacted_files: list[str],
        missing_tests: list[str],
        migration_warnings: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        items: list[str] = []
        if migration_warnings and any(w.get("severity") == "high" for w in migration_warnings):
            high = [w["code"] for w in migration_warnings if w.get("severity") == "high"]
            items.append(
                f"High-risk migration ops detected ({', '.join(sorted(set(high)))}). Stage, backfill, and verify rollback before merging."
            )
        if security_sensitive_changes:
            items.append("Review authentication, authorization, secret handling, and audit logging first.")
        if public_api_changes:
            items.append("Check public API compatibility, request/response contracts, and callers.")
        if database_or_schema_changes:
            items.append("Validate migrations, rollback behavior, and data-access callers.")
        if config_or_infra_changes:
            items.append("Validate environment, CI, deployment, and local developer defaults.")
        if impacted_files:
            items.append("Inspect impacted files with graph dependents before approving.")
        if missing_tests:
            items.append("Add or update tests around changed symbols and impacted behavior.")
        return items or ["Review changed symbols, run related tests, and verify context-pack uncertainty."]

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
    def _suggested_commands(affected_tests: list[str], files: list[str]) -> list[str]:
        commands = ["devgraph explain <changed-file-or-symbol>", "devgraph handoff"]
        if files:
            commands.insert(0, f"devgraph explain {files[0]}")
        if affected_tests:
            commands.insert(0, "Run related tests listed in the review output.")
        return commands


SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _severity_maps(
    migration_warnings: Sequence[dict[str, Any]],
    api_signature_changes: Sequence[dict[str, Any]],
    route_contract_changes: Sequence[dict[str, Any]],
    fan_out_entries: Sequence[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    by_file: dict[str, int] = {}
    by_symbol: dict[str, int] = {}

    def _record_file(path: str | None, severity: str | None) -> None:
        if not path or not severity:
            return
        rank = SEVERITY_RANK.get(severity.lower(), 0)
        if not rank:
            return
        if rank > by_file.get(path, 0):
            by_file[path] = rank

    def _record_symbol(qn: str | None, severity: str | None) -> None:
        if not qn or not severity:
            return
        rank = SEVERITY_RANK.get(severity.lower(), 0)
        if not rank:
            return
        if rank > by_symbol.get(qn, 0):
            by_symbol[qn] = rank

    for warning in migration_warnings:
        _record_file(warning.get("file_path"), warning.get("severity"))
    for warning in api_signature_changes:
        _record_file(warning.get("file_path"), warning.get("severity"))
        _record_symbol(warning.get("qualified_name"), warning.get("severity"))
    for warning in route_contract_changes:
        _record_file(warning.get("file_path"), warning.get("severity"))
    for entry in fan_out_entries:
        impact = float(entry.get("impact_ratio") or 0.0)
        fan_in = int(entry.get("fan_in") or 0)
        if fan_in >= 10 or impact >= 5:
            severity_value = "high"
        elif fan_in >= 3 or impact >= 2:
            severity_value = "medium"
        else:
            continue
        _record_file(entry.get("file_path"), severity_value)
        _record_symbol(entry.get("qualified_name"), severity_value)

    def _label(rank: int) -> str:
        for name, value in SEVERITY_RANK.items():
            if value == rank:
                return name
        return "low"

    return (
        {path: _label(rank) for path, rank in by_file.items()},
        {qn: _label(rank) for qn, rank in by_symbol.items()},
    )


def format_review_markdown(result: ReviewResult) -> str:
    changed_files = [f"- `{path}`" for path in result.changed_files] or ["- No changed files detected."]
    changed_symbols = [
        f"- `{node.qualified_name}` ({node.type}, lines {node.line_start}-{node.line_end})"
        for node in result.changed_symbols
    ] or ["- No changed symbols mapped from diff hunks."]
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
        "## Changed symbols",
        *changed_symbols,
        "",
        "## Diff summary",
        *diff_summary,
        "",
        "## Prioritized review items",
        *[f"- {item}" for item in result.prioritized_review_items],
        "",
        "## Sensitive areas",
        *[f"- Public/API: `{item}`" for item in result.public_api_changes[:10]],
        *[f"- Config/infra: `{item}`" for item in result.config_or_infra_changes[:10]],
        *[f"- Database/schema: `{item}`" for item in result.database_or_schema_changes[:10]],
        *[f"- Security: `{item}`" for item in result.security_sensitive_changes[:10]],
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


def _hunk_payload(hunk: DiffHunk) -> dict[str, object]:
    return {
        "file_path": hunk.file_path,
        "old_start": hunk.old_start,
        "old_count": hunk.old_count,
        "new_start": hunk.new_start,
        "new_count": hunk.new_count,
        "changed_lines": hunk.changed_lines,
        "text": _trim_patch(hunk.text, max_lines=80),
    }


def _trim_patch(patch: str, max_lines: int = 160) -> str:
    lines = patch.splitlines()
    if len(lines) <= max_lines:
        return patch
    return "\n".join([*lines[:max_lines], f"... truncated {len(lines) - max_lines} diff lines ..."])
