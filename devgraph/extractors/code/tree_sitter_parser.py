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
from typing import Literal

from devgraph.core.ids import edge_id, node_id, normalize_path
from devgraph.core.schema import Edge, ExtractionResult, Node
from devgraph.extractors.base import (
    BaseExtractor,
    contains_edge,
    external_module_node,
    make_chunk,
    make_file_node,
    make_file_record,
    read_text,
)
from devgraph.extractors.code.calls import parse_js_ts_calls
from devgraph.extractors.code.imports import parse_js_ts_imports
from devgraph.extractors.code.languages import language_for_path
from devgraph.extractors.code.routes import parse_js_ts_routes
from devgraph.extractors.code.tests import is_test_symbol


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
        else:
            nodes, edges, warnings = self._extract_generic_code(record.path, text, file_node, language)
        all_nodes = [file_node, *nodes]
        all_edges = [contains_edge(file_node, node, "code-extractor") for node in nodes if node.file_path]
        all_edges.extend(edges)
        return ExtractionResult(
            file=record,
            nodes=all_nodes,
            edges=all_edges,
            chunks=[make_chunk(record.path, text, "source", file_node)],
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
                line_end=line,
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
        for method, route, line in parse_js_ts_routes(text):
            qn = f"{module_name}::{method} {route}"
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
                metadata={"method": method, "path": route},
            )
            nodes.append(route_node)
            edges.append(
                Edge(
                    id=edge_id(module_node.id, route_node.id, "routes_to", f"js-ts-parser:{method}:{route}"),
                    source_id=module_node.id,
                    target_id=route_node.id,
                    type="routes_to",
                    provenance_source="js-ts-parser",
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


def _nearest_symbol(nodes: Iterable[Node], line: int) -> Node | None:
    before = [node for node in nodes if (node.line_start or 0) <= line]
    return max(before, key=lambda node: node.line_start or 0) if before else None


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
