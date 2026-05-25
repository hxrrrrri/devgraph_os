"""Code extraction.

The module is structured around a Tree-sitter adapter boundary, but the initial
implementation uses reliable standard-library parsing for Python and conservative
regex extraction for JS/TS-family files when Tree-sitter grammars are unavailable.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Literal, cast

from devgraph.core.ids import edge_id, node_id, normalize_path
from devgraph.core.schema import Edge, EdgeType, ExtractionResult, Node, NodeType
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    external_module_node,
    make_file_node,
    make_file_record,
    read_text,
)
from devgraph.extractors.code.calls import parse_js_ts_calls
from devgraph.extractors.code.imports import parse_js_ts_imports
from devgraph.extractors.code.languages import language_for_path
from devgraph.extractors.code.routes import parse_js_ts_routes
from devgraph.extractors.code.sql import extract_table_references
from devgraph.extractors.code.tests import is_test_symbol
from devgraph.extractors.code.tree_sitter_adapter import TreeSitterSemanticAnalyzer
from devgraph.retrieval.chunking import chunk_code, chunk_sql


class CodeExtractor(BaseExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        text = read_text(path)
        language = language_for_path(path)
        record = make_file_record(root, path, "code", language, text)
        file_node = make_file_node(record)
        if language == "python":
            nodes, edges, warnings = self._extract_python(record.path, text, file_node)
        elif language in {"javascript", "typescript"}:
            nodes, edges, warnings = self._extract_js_ts(record.path, text, file_node, language)
        elif language == "sql":
            nodes, edges, warnings = self._extract_sql(record.path, text, file_node)
        elif language in {
            "go",
            "rust",
            "java",
            "c",
            "cpp",
            "csharp",
            "ruby",
            "php",
            "kotlin",
            "swift",
            "scala",
            "dart",
            "lua",
            "bash",
        }:
            nodes, edges, warnings = self._extract_static_language(
                record.path, text, file_node, language
            )
        elif language in {"vue", "svelte"}:
            nodes, edges, warnings = self._extract_component_file(
                record.path, text, file_node, language
            )
        else:
            nodes, edges, warnings = self._extract_generic_code(record.path, text, file_node, language)
        all_nodes = [file_node, *nodes]
        all_edges = [contains_edge(file_node, node, "code-extractor") for node in nodes if node.file_path]
        all_edges.extend(edges)
        return ExtractionResult(
            file=record,
            nodes=all_nodes,
            edges=all_edges,
            chunks=chunk_sql(record.path, text, file_node) if language == "sql" else chunk_code(record.path, text, all_nodes),
            warnings=warnings,
        )

    def _extract_python(
        self, file_path: str, text: str, file_node: Node
    ) -> tuple[list[Node], list[Edge], list[str]]:
        warnings: list[str] = []
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            return [], [], [f"Python parse failed for {file_path}: {exc}"]
        nodes: list[Node] = []
        edges: list[Edge] = []
        module_name = normalize_path(file_path).replace("/", ".").removesuffix(".py")
        module_node = Node(
            id=node_id("module", module_name),
            type="module",
            name=Path(file_path).stem,
            qualified_name=module_name,
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="python",
            content_hash=file_node.content_hash,
        )
        nodes.append(module_node)
        edges.append(
            Edge(
                id=edge_id(file_node.id, module_node.id, "contains", "python-ast"),
                source_id=file_node.id,
                target_id=module_node.id,
                type="contains",
                provenance_source="python-ast",
                file_path=file_path,
                line=1,
            )
        )

        symbol_by_simple_name: dict[str, Node] = {}
        parent_stack: list[str] = []

        for item in ast.walk(tree):
            if isinstance(item, ast.ClassDef):
                qn = f"{module_name}.{item.name}"
                class_node = Node(
                    id=node_id("class", qn),
                    type="class",
                    name=item.name,
                    qualified_name=qn,
                    file_path=file_path,
                    line_start=item.lineno,
                    line_end=getattr(item, "end_lineno", item.lineno),
                    language="python",
                    content_hash=file_node.content_hash,
                )
                nodes.append(class_node)
                symbol_by_simple_name[item.name] = class_node
                for base in item.bases:
                    base_name = _python_name(base)
                    if base_name:
                        target = external_module_node(base_name, "python")
                        nodes.append(target)
                        edges.append(
                            Edge(
                                id=edge_id(class_node.id, target.id, "inherits", "python-ast"),
                                source_id=class_node.id,
                                target_id=target.id,
                                type="inherits",
                                provenance_source="python-ast",
                                file_path=file_path,
                                line=item.lineno,
                            )
                        )
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner = _enclosing_class(tree, item)
                parent_stack.append(owner or "")
                qn = f"{module_name}.{owner + '.' if owner else ''}{item.name}"
                node_type: Literal["test", "function"] = (
                    "test" if is_test_symbol(item.name) else "function"
                )
                function_node = Node(
                    id=node_id(node_type, qn),
                    type=node_type,
                    name=item.name,
                    qualified_name=qn,
                    file_path=file_path,
                    line_start=item.lineno,
                    line_end=getattr(item, "end_lineno", item.lineno),
                    language="python",
                    content_hash=file_node.content_hash,
                    tags=["async"] if isinstance(item, ast.AsyncFunctionDef) else [],
                )
                nodes.append(function_node)
                symbol_by_simple_name[item.name] = function_node
                parent_stack.pop()

        for item in ast.walk(tree):
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                source = module_node
                module_names = _python_import_names(item)
                for imported in module_names:
                    target = external_module_node(imported, "python")
                    nodes.append(target)
                    edges.append(
                        Edge(
                            id=edge_id(source.id, target.id, "imports", f"python-ast:{imported}"),
                            source_id=source.id,
                            target_id=target.id,
                            type="imports",
                            provenance_source="python-ast",
                            file_path=file_path,
                            line=item.lineno,
                        )
                    )
            elif isinstance(item, ast.Call):
                call_name = _python_name(item.func)
                if not call_name:
                    continue
                caller = _containing_function_node(module_name, tree, item, symbol_by_simple_name)
                callee = symbol_by_simple_name.get(call_name.split(".")[-1])
                if caller and callee and caller.id != callee.id:
                    edges.append(
                        Edge(
                            id=edge_id(caller.id, callee.id, "calls", f"python-ast:{item.lineno}:{call_name}"),
                            source_id=caller.id,
                            target_id=callee.id,
                            type="calls",
                            provenance_source="python-ast",
                            file_path=file_path,
                            line=item.lineno,
                            metadata={"call": call_name},
                        )
                    )
        return _dedupe_nodes(nodes), _dedupe_edges(edges), warnings

    def _extract_js_ts(
        self,
        file_path: str,
        text: str,
        file_node: Node,
        language: str | None,
    ) -> tuple[list[Node], list[Edge], list[str]]:
        semantic = TreeSitterSemanticAnalyzer().analyze(
            file_path, text, file_node, language, Path(file_path)
        )
        if semantic.available and any(node.type != "module" for node in semantic.nodes):
            return _with_js_ts_routes(
                file_path,
                text,
                file_node,
                language,
                semantic.nodes,
                semantic.edges,
                semantic.warnings,
                provenance="tree-sitter",
            )

        module_name = normalize_path(file_path).replace("/", ".")
        module_node = Node(
            id=node_id("module", module_name),
            type="module",
            name=Path(file_path).stem,
            qualified_name=module_name,
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language=language,
            content_hash=file_node.content_hash,
        )
        nodes: list[Node] = [module_node]
        edges: list[Edge] = [
            Edge(
                id=edge_id(file_node.id, module_node.id, "contains", "js-ts-parser"),
                source_id=file_node.id,
                target_id=module_node.id,
                type="contains",
                provenance_source="js-ts-parser",
                file_path=file_path,
                line=1,
            )
        ]
        symbol_by_name: dict[str, Node] = {}
        for name, kind, line in _js_ts_symbols(text):
            node_type: Literal["class", "test", "function"] = (
                "class" if kind == "class" else ("test" if is_test_symbol(name) else "function")
            )
            qn = f"{module_name}::{name}"
            node = Node(
                id=node_id(node_type, qn),
                type=node_type,
                name=name,
                qualified_name=qn,
                file_path=file_path,
                line_start=line,
                line_end=_symbol_end_line(text, line),
                language=language,
                content_hash=file_node.content_hash,
            )
            nodes.append(node)
            symbol_by_name[name] = node
        for module, line in parse_js_ts_imports(text):
            target = external_module_node(module, language)
            nodes.append(target)
            edges.append(
                Edge(
                    id=edge_id(module_node.id, target.id, "imports", f"js-ts-parser:{module}"),
                    source_id=module_node.id,
                    target_id=target.id,
                    type="imports",
                    provenance_source="js-ts-parser",
                    file_path=file_path,
                    line=line,
                )
            )
        for call_name, line in parse_js_ts_calls(text):
            callee = symbol_by_name.get(call_name.split(".")[-1])
            caller = _nearest_symbol(symbol_by_name.values(), line) or module_node
            if callee and caller.id != callee.id:
                edges.append(
                    Edge(
                        id=edge_id(caller.id, callee.id, "calls", f"js-ts-parser:{line}:{call_name}"),
                        source_id=caller.id,
                        target_id=callee.id,
                        type="calls",
                        provenance_source="js-ts-parser",
                        file_path=file_path,
                        line=line,
                        metadata={"call": call_name},
                    )
                )
        return _with_js_ts_routes(
            file_path,
            text,
            file_node,
            language,
            nodes,
            edges,
            [],
            provenance="js-ts-parser",
        )

    def _extract_static_language(
        self,
        file_path: str,
        text: str,
        file_node: Node,
        language: str,
    ) -> tuple[list[Node], list[Edge], list[str]]:
        semantic = TreeSitterSemanticAnalyzer().analyze(
            file_path, text, file_node, language, Path(file_path)
        )
        if semantic.available and any(node.type != "module" for node in semantic.nodes):
            return semantic.nodes, semantic.edges, semantic.warnings

        module_name = normalize_path(file_path).replace("/", ".")
        module_node = Node(
            id=node_id("module", module_name),
            type="module",
            name=Path(file_path).stem,
            qualified_name=module_name,
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language=language,
            content_hash=file_node.content_hash,
        )
        nodes: list[Node] = [module_node]
        edges: list[Edge] = [
            Edge(
                id=edge_id(file_node.id, module_node.id, "contains", f"{language}-parser"),
                source_id=file_node.id,
                target_id=module_node.id,
                type="contains",
                provenance_source=f"{language}-parser",
                file_path=file_path,
                line=1,
            )
        ]
        symbol_by_name: dict[str, Node] = {}
        for name, kind, line in _language_symbols(text, language):
            node_type = "class" if kind == "class" else ("test" if is_test_symbol(name) else "function")
            if kind == "type":
                node_type = "type"
            qn = f"{module_name}::{name}"
            node = Node(
                id=node_id(node_type, qn),
                type=cast(NodeType, node_type),
                name=name,
                qualified_name=qn,
                file_path=file_path,
                line_start=line,
                line_end=_symbol_end_line(text, line),
                language=language,
                content_hash=file_node.content_hash,
                metadata={"parser": f"{language}-patterns", "kind": kind},
            )
            nodes.append(node)
            symbol_by_name[name] = node
        for module, line in _language_imports(text, language):
            target = external_module_node(module, language)
            nodes.append(target)
            edges.append(
                Edge(
                    id=edge_id(module_node.id, target.id, "imports", f"{language}-parser:{module}"),
                    source_id=module_node.id,
                    target_id=target.id,
                    type="imports",
                    provenance_source=f"{language}-parser",
                    file_path=file_path,
                    line=line,
                )
            )
        for call_name, line in parse_js_ts_calls(text):
            callee = symbol_by_name.get(call_name.split(".")[-1])
            caller = _nearest_symbol(symbol_by_name.values(), line) or module_node
            if callee and caller.id != callee.id:
                edges.append(
                    Edge(
                        id=edge_id(caller.id, callee.id, "calls", f"{language}-parser:{line}:{call_name}"),
                        source_id=caller.id,
                        target_id=callee.id,
                        type="calls",
                        provenance_source=f"{language}-parser",
                        file_path=file_path,
                        line=line,
                        metadata={"call": call_name},
                    )
                )
        return _dedupe_nodes(nodes), _dedupe_edges(edges), []

    def _extract_sql(
        self,
        file_path: str,
        text: str,
        file_node: Node,
    ) -> tuple[list[Node], list[Edge], list[str]]:
        module_name = normalize_path(file_path).replace("/", ".")
        module_node = Node(
            id=node_id("module", module_name),
            type="module",
            name=Path(file_path).stem,
            qualified_name=module_name,
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language="sql",
            content_hash=file_node.content_hash,
            metadata={"parser": "sql-patterns"},
        )
        nodes: list[Node] = [module_node]
        edges: list[Edge] = [
            Edge(
                id=edge_id(file_node.id, module_node.id, "contains", "sql-parser"),
                source_id=file_node.id,
                target_id=module_node.id,
                type="contains",
                provenance_source="sql-parser",
                file_path=file_path,
                line=1,
            )
        ]
        for edge_type, table, line in extract_table_references(text):
            qn = f"database::{table}"
            table_node = Node(
                id=node_id("database_table", qn),
                type="database_table",
                name=table,
                qualified_name=qn,
                file_path=file_path,
                line_start=line,
                line_end=line,
                language="sql",
                content_hash=file_node.content_hash,
                metadata={"parser": "sql-patterns"},
            )
            nodes.append(table_node)
            edges.append(
                Edge(
                    id=edge_id(module_node.id, table_node.id, edge_type, f"sql-parser:{table}:{line}"),
                    source_id=module_node.id,
                    target_id=table_node.id,
                    type=cast(EdgeType, edge_type),
                    provenance_source="sql-parser",
                    file_path=file_path,
                    line=line,
                    metadata={"table": table},
                )
            )
        return _dedupe_nodes(nodes), _dedupe_edges(edges), []

    def _extract_component_file(
        self,
        file_path: str,
        text: str,
        file_node: Node,
        language: str,
    ) -> tuple[list[Node], list[Edge], list[str]]:
        module_name = normalize_path(file_path).replace("/", ".")
        module_node = Node(
            id=node_id("module", module_name),
            type="module",
            name=Path(file_path).stem,
            qualified_name=module_name,
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language=language,
            content_hash=file_node.content_hash,
            confidence_tier="extracted",
            metadata={"parser": f"{language}-component"},
        )
        component_node = Node(
            id=node_id("class", f"{module_name}::{Path(file_path).stem}"),
            type="class",
            name=Path(file_path).stem,
            qualified_name=f"{module_name}::{Path(file_path).stem}",
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language=language,
            content_hash=file_node.content_hash,
            metadata={"kind": "component", "parser": f"{language}-component"},
        )
        nodes: list[Node] = [module_node, component_node]
        edges: list[Edge] = [
            Edge(
                id=edge_id(file_node.id, module_node.id, "contains", f"{language}-component"),
                source_id=file_node.id,
                target_id=module_node.id,
                type="contains",
                provenance_source=f"{language}-component",
                file_path=file_path,
                line=1,
            ),
            Edge(
                id=edge_id(module_node.id, component_node.id, "contains", f"{language}-component"),
                source_id=module_node.id,
                target_id=component_node.id,
                type="contains",
                provenance_source=f"{language}-component",
                file_path=file_path,
                line=1,
            ),
        ]
        for module, line in parse_js_ts_imports(text):
            target = external_module_node(module, language)
            nodes.append(target)
            edges.append(
                Edge(
                    id=edge_id(module_node.id, target.id, "imports", f"{language}-component:{module}"),
                    source_id=module_node.id,
                    target_id=target.id,
                    type="imports",
                    provenance_source=f"{language}-component",
                    file_path=file_path,
                    line=line,
                )
            )
        return _dedupe_nodes(nodes), _dedupe_edges(edges), []

    def _extract_generic_code(
        self,
        file_path: str,
        text: str,
        file_node: Node,
        language: str | None,
    ) -> tuple[list[Node], list[Edge], list[str]]:
        qn = normalize_path(file_path).replace("/", ".")
        module = Node(
            id=node_id("module", qn),
            type="module",
            name=Path(file_path).stem,
            qualified_name=qn,
            file_path=file_path,
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
            language=language,
            content_hash=file_node.content_hash,
            confidence_tier="ambiguous",
            confidence=0.6,
        )
        edge = Edge(
            id=edge_id(file_node.id, module.id, "contains", "generic-code"),
            source_id=file_node.id,
            target_id=module.id,
            type="contains",
            provenance_source="generic-code",
            file_path=file_path,
            line=1,
        )
        return [module], [edge], [f"{language or 'unknown'} extraction is generic for {file_path}"]


def _python_import_names(item: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(item, ast.Import):
        return [alias.name for alias in item.names]
    prefix = "." * item.level + (item.module or "")
    return [f"{prefix}.{alias.name}".strip(".") for alias in item.names]


def _python_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _python_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _python_name(node.func)
    return None


def _enclosing_class(tree: ast.AST, target: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in ast.walk(node):
                if child is target:
                    return node.name
    return None


def _containing_function_node(
    module_name: str,
    tree: ast.AST,
    target: ast.AST,
    symbols: dict[str, Node],
) -> Node | None:
    best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)
            line = getattr(target, "lineno", 0)
            if start <= line <= end and (best is None or start >= best.lineno):
                best = node
    if best is None:
        return None
    owner = _enclosing_class(tree, best)
    qn_name = f"{module_name}.{owner + '.' if owner else ''}{best.name}"
    return next((node for node in symbols.values() if node.qualified_name == qn_name), symbols.get(best.name))


def _with_js_ts_routes(
    file_path: str,
    text: str,
    file_node: Node,
    language: str | None,
    nodes: list[Node],
    edges: list[Edge],
    warnings: list[str],
    provenance: str,
) -> tuple[list[Node], list[Edge], list[str]]:
    module_node = next((node for node in nodes if node.type == "module"), file_node)
    for method, route, line in parse_js_ts_routes(text):
        qn = f"{module_node.qualified_name}::{method} {route}"
        route_node = Node(
            id=node_id("api_endpoint", qn),
            type="api_endpoint",
            name=f"{method} {route}",
            qualified_name=qn,
            file_path=file_path,
            line_start=line,
            line_end=line,
            language=language,
            content_hash=file_node.content_hash,
            metadata={"method": method, "path": route, "parser": provenance},
        )
        nodes.append(route_node)
        edges.append(
            Edge(
                id=edge_id(module_node.id, route_node.id, "routes_to", f"{provenance}:{method}:{route}"),
                source_id=module_node.id,
                target_id=route_node.id,
                type="routes_to",
                provenance_source=provenance,
                file_path=file_path,
                line=line,
            )
        )
    return _dedupe_nodes(nodes), _dedupe_edges(edges), warnings


def _js_ts_symbols(text: str) -> list[tuple[str, str, int]]:
    patterns = [
        (re.compile(r"\bclass\s+([A-Za-z_$][\w$]*)"), "class"),
        (re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\("), "function"),
        (re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\("), "function"),
        (re.compile(r"\bexport\s+default\s+function\s+([A-Za-z_$][\w$]*)\s*\("), "function"),
    ]
    offsets = _line_offsets(text)
    symbols: list[tuple[str, str, int]] = []
    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            symbols.append((match.group(1), kind, _line_for_offset(offsets, match.start())))
    return sorted(symbols, key=lambda item: item[2])


def _language_symbols(text: str, language: str) -> list[tuple[str, str, int]]:
    if language == "go":
        patterns = [
            (re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", re.MULTILINE), "function"),
            (re.compile(r"^\s*type\s+([A-Za-z_]\w*)\s+(?:struct|interface)\b", re.MULTILINE), "type"),
        ]
    elif language == "rust":
        patterns = [
            (
                re.compile(
                    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)\s*[<(]",
                    re.MULTILINE,
                ),
                "function",
            ),
            (
                re.compile(
                    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)",
                    re.MULTILINE,
                ),
                "type",
            ),
        ]
    elif language == "java":
        patterns = [
            (
                re.compile(r"\b(?:class|interface|enum|record)\s+([A-Za-z_]\w*)"),
                "class",
            ),
            (
                re.compile(
                    r"^\s*(?:public|private|protected|static|final|synchronized|abstract|native|\s)+"
                    r"[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(",
                    re.MULTILINE,
                ),
                "function",
            ),
        ]
    elif language in {"c", "cpp"}:
        patterns = [
            (re.compile(r"\b(?:class|struct|enum)\s+([A-Za-z_]\w*)"), "class"),
            (
                re.compile(
                    r"^\s*(?:static\s+|inline\s+|extern\s+|virtual\s+|constexpr\s+)*"
                    r"[A-Za-z_][\w:<>,~*&\s]+\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{",
                    re.MULTILINE,
                ),
                "function",
            ),
        ]
    elif language == "csharp":
        patterns = [
            (re.compile(r"\b(?:class|interface|struct|enum|record)\s+([A-Za-z_]\w*)"), "class"),
            (
                re.compile(
                    r"^\s*(?:public|private|protected|internal|static|async|virtual|override|sealed|partial|\s)+"
                    r"[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(",
                    re.MULTILINE,
                ),
                "function",
            ),
        ]
    elif language == "ruby":
        patterns = [
            (re.compile(r"^\s*class\s+([A-Za-z_:]\w*)", re.MULTILINE), "class"),
            (re.compile(r"^\s*module\s+([A-Za-z_:]\w*)", re.MULTILINE), "type"),
            (re.compile(r"^\s*def\s+(?:self\.)?([A-Za-z_]\w*[!?=]?)", re.MULTILINE), "function"),
        ]
    elif language == "php":
        patterns = [
            (re.compile(r"\b(?:class|interface|trait|enum)\s+([A-Za-z_]\w*)"), "class"),
            (re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\("), "function"),
        ]
    elif language == "kotlin":
        patterns = [
            (re.compile(r"\b(?:class|interface|object|data\s+class|enum\s+class)\s+([A-Za-z_]\w*)"), "class"),
            (re.compile(r"^\s*(?:public|private|protected|internal|suspend|inline|\s)*fun\s+([A-Za-z_]\w*)\s*[<(]", re.MULTILINE), "function"),
        ]
    elif language == "swift":
        patterns = [
            (re.compile(r"\b(?:class|struct|enum|protocol|actor)\s+([A-Za-z_]\w*)"), "class"),
            (re.compile(r"^\s*(?:public|private|internal|fileprivate|open|static|class|\s)*func\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE), "function"),
        ]
    elif language == "scala":
        patterns = [
            (re.compile(r"\b(?:class|object|trait|enum)\s+([A-Za-z_]\w*)"), "class"),
            (re.compile(r"^\s*(?:private|protected|override|implicit|inline|\s)*def\s+([A-Za-z_]\w*)\s*[(:=]", re.MULTILINE), "function"),
        ]
    elif language == "dart":
        patterns = [
            (re.compile(r"\b(?:class|mixin|enum|extension)\s+([A-Za-z_]\w*)"), "class"),
            (
                re.compile(
                    r"^\s*(?:static\s+|async\s+)?(?:[A-Za-z_][\w<>?]*\s+)?([A-Za-z_]\w*)\s*\([^;]*\)\s*(?:async\s*)?\{",
                    re.MULTILINE,
                ),
                "function",
            ),
        ]
    elif language == "lua":
        patterns = [
            (re.compile(r"^\s*(?:local\s+)?function\s+([A-Za-z_][\w.:]*)\s*\(", re.MULTILINE), "function"),
            (re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*function\s*\(", re.MULTILINE), "function"),
        ]
    elif language == "bash":
        patterns = [
            (re.compile(r"^\s*(?:function\s+)?([A-Za-z_][\w-]*)\s*(?:\(\))\s*\{", re.MULTILINE), "function"),
            (re.compile(r"^\s*function\s+([A-Za-z_][\w-]*)\s*\{", re.MULTILINE), "function"),
        ]
    else:
        return []

    offsets = _line_offsets(text)
    symbols: list[tuple[str, str, int]] = []
    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            symbols.append((match.group(1), kind, _line_for_offset(offsets, match.start())))
    return sorted({(name, kind, line) for name, kind, line in symbols}, key=lambda item: item[2])


def _language_imports(text: str, language: str) -> list[tuple[str, int]]:
    offsets = _line_offsets(text)
    imports: list[tuple[str, int]] = []
    if language == "go":
        in_block = False
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("import ("):
                in_block = True
                continue
            if in_block and stripped == ")":
                in_block = False
                continue
            if stripped.startswith("import ") or in_block:
                for match in re.finditer(r'"([^"]+)"', stripped):
                    imports.append((match.group(1), line_number))
    elif language == "rust":
        for match in re.finditer(r"^\s*use\s+([^;]+);", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    elif language == "java":
        for match in re.finditer(r"^\s*import\s+(?:static\s+)?([^;]+);", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    elif language in {"c", "cpp"}:
        for match in re.finditer(r"^\s*#\s*include\s+[<\"]([^>\"]+)[>\"]", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    elif language == "csharp":
        for match in re.finditer(r"^\s*using\s+([^;]+);", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    elif language in {"ruby", "lua"}:
        for match in re.finditer(r"^\s*(?:require|require_relative)\s+['\"]([^'\"]+)['\"]", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    elif language == "php":
        for match in re.finditer(r"^\s*(?:use|include|require(?:_once)?)\s+([^;]+);", text, re.MULTILINE):
            imports.append((match.group(1).strip().strip("'\""), _line_for_offset(offsets, match.start())))
    elif language in {"kotlin", "swift", "scala", "dart"}:
        for match in re.finditer(r"^\s*import\s+([^;\n]+)", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    elif language == "bash":
        for match in re.finditer(r"^\s*(?:source|\.)\s+(.+)$", text, re.MULTILINE):
            imports.append((match.group(1).strip(), _line_for_offset(offsets, match.start())))
    return imports


def _nearest_symbol(nodes: Iterable[Node], line: int) -> Node | None:
    before = [node for node in nodes if (node.line_start or 0) <= line]
    return max(before, key=lambda node: node.line_start or 0) if before else None


def _symbol_end_line(text: str, start_line: int) -> int:
    lines = text.splitlines()
    if not lines:
        return start_line
    brace_balance = 0
    saw_brace = False
    indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip()) if start_line <= len(lines) else 0
    for index in range(start_line, len(lines) + 1):
        line = lines[index - 1]
        brace_balance += line.count("{") - line.count("}")
        saw_brace = saw_brace or "{" in line
        if saw_brace and brace_balance <= 0 and index > start_line:
            return index
        if not saw_brace and index > start_line:
            stripped = line.strip()
            current_indent = len(line) - len(line.lstrip())
            if stripped and current_indent <= indent and not stripped.startswith(("@", "#", "//")):
                return index - 1
    return min(len(lines), start_line + 80)


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _line_for_offset(offsets: list[int], offset: int) -> int:
    line = 1
    for item in offsets:
        if item <= offset:
            line += 1
        else:
            break
    return max(1, line - 1)


def _dedupe_nodes(nodes: list[Node]) -> list[Node]:
    deduped: dict[str, Node] = {}
    for node in nodes:
        deduped[node.id] = node
    return list(deduped.values())


def _dedupe_edges(edges: list[Edge]) -> list[Edge]:
    deduped: dict[str, Edge] = {}
    for edge in edges:
        deduped[edge.id] = edge
    return list(deduped.values())
