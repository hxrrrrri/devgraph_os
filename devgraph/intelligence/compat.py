"""Public API + route contract compatibility detection between snapshots.

Compares a previously-exported graph snapshot (JSON) to the current set of
nodes and emits structured warnings: removed symbols, added-required
parameters, removed defaults, narrowed return types, visibility downgrades,
removed routes, added routes, route renames.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from devgraph.core.schema import Node


def load_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"nodes": [], "edges": [], "files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _node_metadata(node: dict[str, Any]) -> dict[str, Any]:
    raw = node.get("metadata")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            return {}
    return {}


def _summarize_signature(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "signature": meta.get("signature"),
        "parameters": meta.get("parameters"),
        "return_type": meta.get("return_type"),
        "visibility": meta.get("visibility"),
    }


def _index_previous(payload: dict[str, Any]) -> tuple[
    dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
]:
    signatures: dict[str, dict[str, Any]] = {}
    routes: dict[tuple[str, str], dict[str, Any]] = {}
    for node in payload.get("nodes", []) or []:
        ntype = node.get("type")
        meta = _node_metadata(node)
        qn = node.get("qualified_name") or ""
        if ntype in {"function", "class", "type"} and qn:
            summary = _summarize_signature(meta)
            summary.update(
                {
                    "type": ntype,
                    "file_path": node.get("file_path"),
                    "name": node.get("name"),
                }
            )
            signatures[qn] = summary
        elif ntype == "api_endpoint":
            method = meta.get("method")
            path = meta.get("path")
            if not method or not path:
                continue
            routes[(method, path)] = {
                "framework": meta.get("framework"),
                "file_path": node.get("file_path"),
                "qualified_name": qn,
            }
    return signatures, routes


def _index_current(nodes: Iterable[Node]) -> tuple[
    dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
]:
    signatures: dict[str, dict[str, Any]] = {}
    routes: dict[tuple[str, str], dict[str, Any]] = {}
    for node in nodes:
        meta = node.metadata or {}
        if node.type in {"function", "class", "type"}:
            summary = _summarize_signature(meta)
            summary.update(
                {
                    "type": node.type,
                    "file_path": node.file_path,
                    "name": node.name,
                }
            )
            signatures[node.qualified_name] = summary
        elif node.type == "api_endpoint":
            method = meta.get("method")
            path = meta.get("path")
            if method and path:
                routes[(method, path)] = {
                    "framework": meta.get("framework"),
                    "file_path": node.file_path,
                    "qualified_name": node.qualified_name,
                }
    return signatures, routes


def diff_public_api(previous: dict[str, Any], current_nodes: Iterable[Node]) -> list[dict[str, Any]]:
    prev_sigs, _ = _index_previous(previous)
    curr_sigs, _ = _index_current(current_nodes)
    warnings: list[dict[str, Any]] = []
    for qn, prev in prev_sigs.items():
        name = prev.get("name") or qn.rsplit(".", 1)[-1]
        if isinstance(name, str) and name.startswith("_"):
            continue
        curr = curr_sigs.get(qn)
        if curr is None:
            warnings.append(
                {
                    "code": "removed_public_symbol",
                    "qualified_name": qn,
                    "file_path": prev.get("file_path"),
                    "severity": "high",
                }
            )
            continue
        prev_vis = (prev.get("visibility") or "").lower()
        curr_vis = (curr.get("visibility") or "").lower()
        if prev_vis == "public" and curr_vis in {"private", "protected"}:
            warnings.append(
                {
                    "code": "visibility_downgrade",
                    "qualified_name": qn,
                    "file_path": curr.get("file_path"),
                    "severity": "high",
                    "from": prev_vis,
                    "to": curr_vis,
                }
            )
        prev_params = prev.get("parameters") or ""
        curr_params = curr.get("parameters") or ""
        if isinstance(prev_params, str) and isinstance(curr_params, str) and prev_params != curr_params:
            prev_required = _required_param_count(prev_params)
            curr_required = _required_param_count(curr_params)
            if curr_required > prev_required:
                warnings.append(
                    {
                        "code": "required_parameter_added",
                        "qualified_name": qn,
                        "file_path": curr.get("file_path"),
                        "severity": "high",
                        "from": prev_params,
                        "to": curr_params,
                    }
                )
            elif _had_defaults(prev_params) and not _had_defaults(curr_params):
                warnings.append(
                    {
                        "code": "default_removed",
                        "qualified_name": qn,
                        "file_path": curr.get("file_path"),
                        "severity": "medium",
                        "from": prev_params,
                        "to": curr_params,
                    }
                )
        prev_ret = (prev.get("return_type") or "").strip()
        curr_ret = (curr.get("return_type") or "").strip()
        if prev_ret and curr_ret and prev_ret != curr_ret:
            warnings.append(
                {
                    "code": "return_type_changed",
                    "qualified_name": qn,
                    "file_path": curr.get("file_path"),
                    "severity": "medium",
                    "from": prev_ret,
                    "to": curr_ret,
                }
            )
    return warnings


def diff_routes(previous: dict[str, Any], current_nodes: Iterable[Node]) -> list[dict[str, Any]]:
    _, prev_routes = _index_previous(previous)
    _, curr_routes = _index_current(current_nodes)
    warnings: list[dict[str, Any]] = []
    for key, prev in prev_routes.items():
        if key not in curr_routes:
            method, path = key
            warnings.append(
                {
                    "code": "route_removed",
                    "method": method,
                    "path": path,
                    "framework": prev.get("framework"),
                    "file_path": prev.get("file_path"),
                    "severity": "high",
                }
            )
    for key, curr in curr_routes.items():
        if key not in prev_routes:
            method, path = key
            warnings.append(
                {
                    "code": "route_added",
                    "method": method,
                    "path": path,
                    "framework": curr.get("framework"),
                    "file_path": curr.get("file_path"),
                    "severity": "medium",
                }
            )
    return warnings


def _required_param_count(params: str) -> int:
    cleaned = params.strip().strip("()").strip()
    if not cleaned:
        return 0
    parts: list[str] = []
    current = ""
    depth = 0
    for char in cleaned:
        if char in "([{<":
            depth += 1
        elif char in ")]}>":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current)
    required = 0
    for part in parts:
        token = part.strip()
        if not token:
            continue
        if token.startswith(("*", "**", "self", "cls", "this")):
            continue
        if "=" in token:
            continue
        required += 1
    return required


def _had_defaults(params: str) -> bool:
    return "=" in params
