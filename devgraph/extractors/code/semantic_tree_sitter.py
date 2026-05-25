"""Tree-sitter semantic extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from devgraph.core.ids import edge_id, node_id, normalize_path
from devgraph.core.schema import Edge, Node, NodeType
from devgraph.extractors.base import external_module_node
from devgraph.extractors.code.languages import TREE_SITTER_LANGUAGE_NAMES
from devgraph.extractors.code.tests import is_test_symbol

DEFINITION_TYPES = {
    "python": {
        "class_definition": "class",
        "function_definition": "function",
    },
    "javascript": {
        "class_declaration": "class",
        "function_declaration": "function",
        "generator_function_declaration": "function",
        "method_definition": "function",
        "variable_declarator": "function",
    },
    "typescript": {
        "class_declaration": "class",
        "abstract_class_declaration": "class",
        "function_declaration": "function",
        "generator_function_declaration": "function",
        "method_definition": "function",
        "public_field_definition": "function",
        "variable_declarator": "function",
        "interface_declaration": "type",
        "type_alias_declaration": "type",
        "enum_declaration": "type",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "function",
        "type_spec": "type",
    },
    "rust": {
        "function_item": "function",
        "struct_item": "type",
        "enum_item": "type",
        "trait_item": "type",
        "type_item": "type",
    },
    "java": {
        "class_declaration": "class",
        "interface_declaration": "class",
        "enum_declaration": "class",
        "record_declaration": "class",
        "method_declaration": "function",
        "constructor_declaration": "function",
    },
    "c": {
        "function_definition": "function",
        "struct_specifier": "type",
        "enum_specifier": "type",
    },
    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "type",
        "enum_specifier": "type",
    },
    "csharp": {
        "class_declaration": "class",
        "interface_declaration": "class",
        "struct_declaration": "type",
        "enum_declaration": "type",
        "method_declaration": "function",
    },
    "ruby": {
        "class": "class",
        "module": "type",
        "method": "function",
        "singleton_method": "function",
    },
    "php": {
        "class_declaration": "class",
        "interface_declaration": "class",
        "trait_declaration": "class",
        "function_definition": "function",
        "method_declaration": "function",
    },
    "kotlin": {
        "class_declaration": "class",
        "object_declaration": "class",
        "function_declaration": "function",
    },
    "swift": {
        "class_declaration": "class",
        "struct_declaration": "class",
        "enum_declaration": "class",
        "protocol_declaration": "class",
        "function_declaration": "function",
    },
    "scala": {
        "class_definition": "class",
        "object_definition": "class",
        "trait_definition": "class",
        "function_definition": "function",
    },
    "dart": {
        "class_definition": "class",
        "mixin_declaration": "class",
        "function_signature": "function",
        "function_body": "function",
    },
    "lua": {
        "function_declaration": "function",
        "function_definition": "function",
    },
    "bash": {
        "function_definition": "function",
    },
}

IMPORT_TYPES = {
    "import_statement",
    "import_from_statement",
    "import_declaration",
    "import_spec",
    "use_declaration",
}

CALL_TYPES = {"call_expression", "call", "method_invocation", "function_call_expression"}

COMPLEXITY_TYPES = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "for_in_statement",
    "while_statement",
    "do_statement",
    "match_expression",
    "switch_expression",
    "switch_statement",
    "case_clause",
    "catch_clause",
    "conditional_expression",
    "ternary_expression",
}


@dataclass
class SemanticParseResult:
    available: bool
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class TreeSitterSemanticAnalyzer:
    def analyze(
        self,
        file_path: str,
        text: str,
        file_node: Node,
        language: str | None,
        source_path: Path | None = None,
    ) -> SemanticParseResult:
        parser = _parser_for(language, source_path)
        if parser is None or language is None:
            return SemanticParseResult(
                available=False,
                warnings=[f"Tree-sitter parser unavailable for {language or 'unknown'}."],
            )
        source = text.encode("utf-8", errors="replace")
        try:
            tree = parser.parse(source)
        except Exception as exc:
            return SemanticParseResult(
                available=False,
                warnings=[f"Tree-sitter parse failed for {file_path}: {exc}"],
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
            metadata={"parser": "tree-sitter", "tree_sitter_language": _tree_sitter_name(language, source_path)},
        )

        nodes: list[Node] = [module_node]
        edges: list[Edge] = [
            Edge(
                id=edge_id(file_node.id, module_node.id, "contains", "tree-sitter"),
                source_id=file_node.id,
                target_id=module_node.id,
                type="contains",
                provenance_source="tree-sitter",
                file_path=file_path,
                line=1,
            )
        ]
        symbol_by_name: dict[str, Node] = {}
        tree_nodes = list(_walk(tree.root_node))

        for item in tree_nodes:
            kind = DEFINITION_TYPES.get(language, {}).get(item.type)
            if not kind or _skip_definition(item):
                continue
            name = _definition_name(item, source)
            if not name:
                continue
            node_type = "test" if kind == "function" and is_test_symbol(name) else kind
            qn = f"{module_name}::{name}"
            semantic_node = Node(
                id=node_id(node_type, qn),
                type=cast(NodeType, node_type),
                name=name,
                qualified_name=qn,
                file_path=file_path,
                line_start=item.start_point[0] + 1,
                line_end=item.end_point[0] + 1,
                language=language,
                content_hash=file_node.content_hash,
                tags=_tags(item, source),
                summary=_leading_comment(item, source),
                metadata={
                    "parser": "tree-sitter",
                    "tree_sitter_node_type": item.type,
                    "signature": _signature(item, source),
                    "parameters": _field_text(item, source, "parameters"),
                    "return_type": _return_type(item, source),
                    "complexity": _complexity(item),
                    "visibility": _visibility(item, source),
                },
            )
            nodes.append(semantic_node)
            symbol_by_name[name] = semantic_node

        for item in tree_nodes:
            if item.type in IMPORT_TYPES:
                for imported in _imports_from_node(item, source, language):
                    target = external_module_node(imported, language)
                    nodes.append(target)
                    edges.append(
                        Edge(
                            id=edge_id(module_node.id, target.id, "imports", f"tree-sitter:{imported}"),
                            source_id=module_node.id,
                            target_id=target.id,
                            type="imports",
                            provenance_source="tree-sitter",
                            file_path=file_path,
                            line=item.start_point[0] + 1,
                        )
                    )
            if item.type in CALL_TYPES:
                call_name = _call_name(item, source)
                if not call_name:
                    continue
                callee = symbol_by_name.get(call_name.split(".")[-1].split("::")[-1])
                caller = _nearest_symbol(symbol_by_name.values(), item.start_point[0] + 1) or module_node
                if callee and caller.id != callee.id:
                    edges.append(
                        Edge(
                            id=edge_id(
                                caller.id,
                                callee.id,
                                "calls",
                                f"tree-sitter:{item.start_point[0] + 1}:{call_name}",
                            ),
                            source_id=caller.id,
                            target_id=callee.id,
                            type="calls",
                            provenance_source="tree-sitter",
                            file_path=file_path,
                            line=item.start_point[0] + 1,
                            metadata={"call": call_name},
                        )
                    )
        return SemanticParseResult(
            available=True,
            nodes=_dedupe_nodes(nodes),
            edges=_dedupe_edges(edges),
        )


def _parser_for(language: str | None, source_path: Path | None) -> Any | None:
    language_name = _tree_sitter_name(language, source_path)
    if not language_name:
        return None
    try:
        from tree_sitter_language_pack import get_parser

        return get_parser(cast(Any, language_name))
    except Exception:
        return None


def _tree_sitter_name(language: str | None, source_path: Path | None) -> str | None:
    if language == "typescript" and source_path and source_path.suffix.lower() == ".tsx":
        return "tsx"
    return TREE_SITTER_LANGUAGE_NAMES.get(language or "")


def _walk(node: Any) -> list[Any]:
    nodes = [node]
    for child in node.children:
        if child.is_named:
            nodes.extend(_walk(child))
    return nodes


def _skip_definition(node: Any) -> bool:
    if node.type != "variable_declarator":
        return False
    value = node.child_by_field_name("value")
    return value is None or value.type not in {"arrow_function", "function", "function_expression"}


def _definition_name(node: Any, source: bytes) -> str | None:
    name = node.child_by_field_name("name")
    if name is not None:
        return _text(name, source)
    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        nested = _definition_name(declarator, source)
        if nested:
            return nested
    for child in node.children:
        if child.type in {"identifier", "type_identifier", "property_identifier", "field_identifier"}:
            return _text(child, source)
    for child in node.children:
        if child.type in {"function_declarator", "pointer_declarator", "array_declarator", "init_declarator"}:
            nested = _definition_name(child, source)
            if nested:
                return nested
    return None


def _signature(node: Any, source: bytes) -> str:
    body = node.child_by_field_name("body")
    end = body.start_byte if body is not None else node.end_byte
    return source[node.start_byte:end].decode("utf-8", errors="replace").strip()


def _field_text(node: Any, source: bytes, field_name: str) -> str | None:
    child = node.child_by_field_name(field_name)
    return _text(child, source) if child is not None else None


def _return_type(node: Any, source: bytes) -> str | None:
    if "class" in node.type or node.type in {"interface_declaration", "struct_item", "enum_item", "trait_item", "type_spec"}:
        return None
    for field_name in ("return_type", "type"):
        value = _field_text(node, source, field_name)
        if value:
            return value
    for child in node.children:
        if child.type in {"type_annotation", "primitive_type", "type_identifier"}:
            return _text(child, source)
    return None


def _visibility(node: Any, source: bytes) -> str | None:
    prefix = _signature(node, source).split("(", 1)[0].lower()
    for marker in ("public", "private", "protected", "pub"):
        if marker in prefix.split():
            return marker
    return None


def _tags(node: Any, source: bytes) -> list[str]:
    signature = _signature(node, source).lower()
    tags = ["tree-sitter"]
    for marker in ("async", "export", "static", "abstract"):
        if marker in signature.split():
            tags.append(marker)
    return tags


def _leading_comment(node: Any, source: bytes) -> str | None:
    previous = node.prev_named_sibling
    if previous is None or "comment" not in previous.type:
        return None
    if previous.end_point[0] + 1 < node.start_point[0]:
        return None
    return _text(previous, source).strip()


def _complexity(node: Any) -> int:
    score = 1
    for child in _walk(node):
        if child is node:
            continue
        if child.type in COMPLEXITY_TYPES:
            score += 1
        elif child.type == "binary_expression":
            text = " ".join(grand.type for grand in child.children)
            if "&&" in text or "||" in text:
                score += 1
    return score


def _imports_from_node(node: Any, source: bytes, language: str) -> list[str]:
    text = _text(node, source).strip()
    if language == "python":
        return _python_imports(node, source)
    if language in {"javascript", "typescript"}:
        strings = _quoted_strings(text)
        return strings or _nonempty([text.removeprefix("import").strip()])
    if language == "go":
        return _quoted_strings(text)
    if language == "rust":
        return _nonempty([text.removeprefix("use").rstrip(";").strip()])
    if language == "java":
        return _nonempty([text.removeprefix("import").removeprefix("static").rstrip(";").strip()])
    return []


def _python_imports(node: Any, source: bytes) -> list[str]:
    if node.type == "import_statement":
        return [
            _text(child, source).strip()
            for child in node.children
            if child.type in {"dotted_name", "aliased_import"}
        ]
    if node.type == "import_from_statement":
        module = node.child_by_field_name("module_name")
        prefix = _text(module, source).strip() if module is not None else ""
        names: list[str] = []
        for child in node.children:
            if child.type in {"dotted_name", "aliased_import"} and child is not module:
                name = _text(child, source).strip()
                names.append(f"{prefix}.{name}".strip(".") if prefix else name)
        return names or ([prefix] if prefix else [])
    return []


def _quoted_strings(text: str) -> list[str]:
    values: list[str] = []
    current = ""
    quote: str | None = None
    for char in text:
        if quote is None and char in {"'", '"'}:
            quote = char
            current = ""
        elif quote == char:
            values.append(current)
            quote = None
        elif quote is not None:
            current += char
    return values


def _call_name(node: Any, source: bytes) -> str | None:
    function = node.child_by_field_name("function")
    if function is None and node.children:
        function = node.children[0]
    if function is None:
        return None
    return _expression_name(function, source)


def _expression_name(node: Any, source: bytes) -> str:
    if node.type in {"identifier", "property_identifier", "field_identifier", "type_identifier"}:
        return _text(node, source)
    if node.type in {"member_expression", "selector_expression", "field_expression", "scoped_identifier"}:
        parts = [
            _expression_name(child, source)
            for child in node.children
            if child.is_named
        ]
        return ".".join(part for part in parts if part)
    return _text(node, source).split("(", 1)[0].strip()


def _nearest_symbol(nodes: Any, line: int) -> Node | None:
    before = [node for node in nodes if (node.line_start or 0) <= line <= (node.line_end or 0)]
    if before:
        return max(before, key=lambda node: node.line_start or 0)
    previous = [node for node in nodes if (node.line_start or 0) <= line]
    return max(previous, key=lambda node: node.line_start or 0) if previous else None


def _text(node: Any, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _nonempty(values: list[str]) -> list[str]:
    return [value for value in values if value]


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
