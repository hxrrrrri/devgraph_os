"""Architecture-layer derivation. Mirrors the dashboard `graphAdapter.ts` rules
so MCP clients and the dashboard see the same partition without re-implementing
the heuristics on each side."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Node

LAYER_DEFS: tuple[dict[str, str], ...] = (
    {"id": "entry", "name": "Entry Points / API", "description": "Endpoints, routers, CLIs, controllers.", "color": "#FFB59D"},
    {"id": "ui", "name": "UI / Frontend", "description": "Components, views, pages, client widgets.", "color": "#D4BBFF"},
    {"id": "app", "name": "Application / Services", "description": "Service objects, orchestrators, use-cases.", "color": "#7CD7C4"},
    {"id": "domain", "name": "Domain / Business Logic", "description": "Core entities, pure functions, models.", "color": "#9EF9E5"},
    {"id": "data", "name": "Data / Persistence", "description": "Tables, schemas, queries, migrations.", "color": "#E8A55A"},
    {"id": "infra", "name": "Config / Infrastructure", "description": "Config, terraform, k8s, CI, deploys.", "color": "#FFD3B6"},
    {"id": "tests", "name": "Tests", "description": "Test suites and fixtures.", "color": "#5DB872"},
    {"id": "docs", "name": "Documentation", "description": "Markdown, RST, knowledge.", "color": "#D4BBFF"},
    {"id": "memory", "name": "Memory / Decisions", "description": "Decisions, sessions, handoffs.", "color": "#B388FF"},
)

ENTRY_TYPES = {"api_endpoint", "service", "pipeline", "resource", "schema"}
DATA_TYPES = {"database_table", "schema"}
DOC_TYPES = {"document", "section", "article", "claim", "entity"}
MEMORY_TYPES = {"decision", "session"}
TEST_TYPES = {"test"}
CONFIG_TYPES = {"config"}

UI_PATH_RE = re.compile(r"(^|[\\/])(ui|components?|views?|pages?|frontend|web|client|webview)(?=[\\/]|$)", re.I)
APP_PATH_RE = re.compile(r"(^|[\\/])(services?|app|orchestrat|use[-_]?case|workflow|handlers?|controllers?)(?=[\\/]|$)", re.I)
ENTRY_PATH_RE = re.compile(r"(^|[\\/])(api|routes?|endpoints?|gateway|cli|server|http)(?=[\\/]|$)", re.I)
DATA_PATH_RE = re.compile(r"(^|[\\/])(db|database|persistence|repository|repositories|models?|migrations?|sql|prisma)(?=[\\/]|$)", re.I)
INFRA_PATH_RE = re.compile(r"(^|[\\/])(infra|terraform|k8s|kubernetes|helm|deploy|ops|\.github|ci)(?=[\\/]|$)", re.I)
TEST_PATH_RE = re.compile(r"(^|[\\/])(tests?|__tests__|spec|specs|e2e)(?=[\\/]|$)", re.I)
DOCS_PATH_RE = re.compile(r"(^|[\\/])(docs?|documentation|wiki)(?=[\\/]|$)|\.(md|mdx|rst|txt)$", re.I)
CONFIG_PATH_RE = re.compile(r"\.(ya?ml|toml|ini|cfg|json5?|env)$|(^|[\\/])(config|configs|settings)(?=[\\/]|$)", re.I)
DOMAIN_PATH_RE = re.compile(r"(^|[\\/])(domain|core|entities|business|logic|models?)(?=[\\/]|$)", re.I)

FRAMEWORK_ROUTE_KEYS = {"route", "routes", "framework", "framework_route", "route_kind", "is_route"}


def classify_node(node: Node) -> str:
    if node.type in TEST_TYPES:
        return "tests"
    if node.type in MEMORY_TYPES:
        return "memory"
    if node.type in DOC_TYPES:
        return "docs"
    if node.type in DATA_TYPES:
        return "data"
    if node.type in CONFIG_TYPES:
        return "infra"

    metadata = node.metadata or {}
    for key in metadata:
        if key in FRAMEWORK_ROUTE_KEYS and metadata.get(key):
            return "entry"
    if node.type in ENTRY_TYPES:
        return "entry"

    path = (node.file_path or "").replace("\\", "/")
    if path:
        if TEST_PATH_RE.search(path):
            return "tests"
        if DOCS_PATH_RE.search(path):
            return "docs"
        if CONFIG_PATH_RE.search(path):
            return "infra"
        if DATA_PATH_RE.search(path):
            return "data"
        if INFRA_PATH_RE.search(path):
            return "infra"
        if ENTRY_PATH_RE.search(path):
            return "entry"
        if UI_PATH_RE.search(path):
            return "ui"
        if APP_PATH_RE.search(path):
            return "app"
        if DOMAIN_PATH_RE.search(path):
            return "domain"

    if node.language:
        lower = node.language.lower()
        if lower in {"tsx", "jsx", "vue", "svelte"}:
            return "ui"
        if lower == "sql":
            return "data"

    if node.type in {"class", "function", "module", "type"}:
        return "app"
    return "app"


def derive_architecture(store: GraphStore) -> dict[str, Any]:
    """Return the full layer partition along with per-layer summary stats."""
    nodes = store.all_nodes()
    buckets: dict[str, list[Node]] = defaultdict(list)
    for node in nodes:
        buckets[classify_node(node)].append(node)

    layers: list[dict[str, Any]] = []
    for defn in LAYER_DEFS:
        items = buckets.get(defn["id"], [])
        if not items:
            continue
        files = sum(1 for n in items if n.type == "file")
        symbols = sum(1 for n in items if n.type in {"function", "class", "module", "type"})
        tests = sum(1 for n in items if n.type == "test")
        docs = sum(1 for n in items if n.type in DOC_TYPES)
        layers.append(
            {
                **defn,
                "node_ids": [n.id for n in items],
                "stats": {
                    "files": files,
                    "symbols": symbols,
                    "tests": tests,
                    "docs": docs,
                    "total": len(items),
                },
            }
        )

    return {
        "total_nodes": len(nodes),
        "layer_count": len(layers),
        "layers": layers,
    }


def layer_detail(store: GraphStore, layer_id: str) -> dict[str, Any] | None:
    """Return the nodes + intra-layer edges for a given layer id."""
    arch = derive_architecture(store)
    target = next((layer for layer in arch["layers"] if layer["id"] == layer_id), None)
    if target is None:
        return None
    ids = set(target["node_ids"])
    if not ids:
        return {"layer": target, "nodes": [], "edges": []}
    placeholders = ",".join("?" for _ in ids)
    node_rows = store.connection.execute(
        f"SELECT * FROM nodes WHERE id IN ({placeholders})", list(ids)
    ).fetchall()
    edge_rows = store.connection.execute(
        f"SELECT * FROM edges WHERE source_id IN ({placeholders}) "
        f"OR target_id IN ({placeholders})",
        list(ids) + list(ids),
    ).fetchall()
    nodes = [GraphStore._row_to_node(row).model_dump() for row in node_rows]
    edges = [GraphStore._row_to_edge(row).model_dump() for row in edge_rows]
    return {"layer": target, "nodes": nodes, "edges": edges}
