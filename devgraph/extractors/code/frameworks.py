"""Framework-aware detectors for code extraction.

Each helper is regex-based and conservative. It returns either route tuples
(`(method, path, line)`) or metadata that callers attach to existing nodes.
Tree-sitter is preferred upstream; these helpers fill the framework gap.
"""

from __future__ import annotations

import re

# --- React ----------------------------------------------------------------

REACT_IMPORT_RE = re.compile(
    r"\b(?:import|from)\s+[^;]*['\"]react(?:/[^'\"]+)?['\"]",
)
REACT_HOOK_CALL_RE = re.compile(
    r"\b(use[A-Z]\w*)\s*\(",
)


def detect_react(text: str) -> bool:
    return bool(REACT_IMPORT_RE.search(text))


def react_hook_calls(text: str) -> list[tuple[str, int]]:
    """Return (hook_name, line) for every `useX(...)` invocation."""

    offsets = _line_offsets(text)
    hits: list[tuple[str, int]] = []
    for match in REACT_HOOK_CALL_RE.finditer(text):
        hits.append((match.group(1), _line_for_offset(offsets, match.start())))
    return hits


def is_component_name(name: str) -> bool:
    return bool(name) and name[0].isupper() and name[0].isalpha()


def is_hook_name(name: str) -> bool:
    return bool(name) and name.startswith("use") and len(name) > 3 and name[3].isupper()


# --- Spring Boot ----------------------------------------------------------

SPRING_CLASS_ANNOTATIONS = {
    "RestController": "controller",
    "Controller": "controller",
    "Service": "service",
    "Component": "component",
    "Repository": "repository",
    "Entity": "entity",
    "Configuration": "configuration",
}

SPRING_REQUEST_MAPPING_RE = re.compile(
    r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?(?:[\"']([^\"']*)[\"']|\{[^}]*\})",
)

SPRING_METHOD_RE = re.compile(
    r"@(Get|Post|Put|Patch|Delete|Request)Mapping"
    r"(?:\s*\(\s*(?:value\s*=\s*)?(?:[\"']([^\"']*)[\"'])?[^)]*\))?",
)

SPRING_CLASS_RE = re.compile(
    r"@(RestController|Controller|Service|Component|Repository|Entity|Configuration)"
    r"\b[^\n]*\n(?:[^\n]*\n){0,4}?\s*(?:public\s+|abstract\s+|final\s+)*"
    r"class\s+([A-Za-z_]\w*)",
)


def parse_spring_routes(text: str) -> list[tuple[str, str, int]]:
    offsets = _line_offsets(text)
    # Find optional class-level @RequestMapping prefix
    prefix_match = SPRING_REQUEST_MAPPING_RE.search(text)
    prefix = (prefix_match.group(1) or "").strip("/") if prefix_match else ""
    routes: list[tuple[str, str, int]] = []
    for match in SPRING_METHOD_RE.finditer(text):
        verb_kind = match.group(1).lower()
        if verb_kind == "request":
            continue
        sub = (match.group(2) or "").strip("/")
        segments = [seg for seg in (prefix, sub) if seg]
        path = "/" + "/".join(segments) if segments else "/"
        routes.append((verb_kind.upper(), path, _line_for_offset(offsets, match.start())))
    return routes


def spring_class_kinds(text: str) -> dict[str, str]:
    """Map class name -> kind for any class with a Spring stereotype annotation."""

    kinds: dict[str, str] = {}
    for match in SPRING_CLASS_RE.finditer(text):
        annotation = match.group(1)
        class_name = match.group(2)
        kinds[class_name] = SPRING_CLASS_ANNOTATIONS.get(annotation, "component")
    return kinds


# --- Rails ----------------------------------------------------------------

RAILS_HTTP_VERB_RE = re.compile(
    r"^\s*(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
RAILS_RESOURCES_RE = re.compile(
    r"^\s*(resources|resource)\s+:([A-Za-z_]\w*)",
    re.MULTILINE,
)
RAILS_MODEL_RE = re.compile(
    r"^\s*class\s+([A-Za-z_]\w*)\s*<\s*(ApplicationRecord|ActiveRecord::Base)",
    re.MULTILINE,
)
RAILS_ASSOC_RE = re.compile(
    r"^\s*(has_many|has_one|belongs_to|has_and_belongs_to_many)\s+:([A-Za-z_]\w*)",
    re.MULTILINE,
)


def parse_rails_routes(text: str) -> list[tuple[str, str, int]]:
    offsets = _line_offsets(text)
    routes: list[tuple[str, str, int]] = []
    for match in RAILS_HTTP_VERB_RE.finditer(text):
        verb = match.group(1).upper()
        path = match.group(2)
        if not path.startswith("/"):
            path = "/" + path
        routes.append((verb, path, _line_for_offset(offsets, match.start())))
    for match in RAILS_RESOURCES_RE.finditer(text):
        kind = match.group(1)
        name = match.group(2)
        base = f"/{name}"
        line = _line_for_offset(offsets, match.start())
        if kind == "resources":
            routes.extend(
                [
                    ("GET", base, line),
                    ("POST", base, line),
                    ("GET", f"{base}/:id", line),
                    ("PATCH", f"{base}/:id", line),
                    ("PUT", f"{base}/:id", line),
                    ("DELETE", f"{base}/:id", line),
                ]
            )
        else:
            routes.extend(
                [
                    ("GET", base, line),
                    ("PATCH", base, line),
                    ("PUT", base, line),
                    ("DELETE", base, line),
                ]
            )
    return routes


def rails_models(text: str) -> dict[str, list[tuple[str, str]]]:
    """Return {model_name: [(association_kind, target_name), ...]}."""

    models: dict[str, list[tuple[str, str]]] = {}
    for match in RAILS_MODEL_RE.finditer(text):
        models[match.group(1)] = []
    for match in RAILS_ASSOC_RE.finditer(text):
        kind = match.group(1)
        target = match.group(2)
        if models:
            # Attach to the last-declared model in this file.
            last_model = list(models.keys())[-1]
            models[last_model].append((kind, target))
    return models


# --- Laravel --------------------------------------------------------------

LARAVEL_ROUTE_RE = re.compile(
    r"\bRoute::(get|post|put|patch|delete|options|any|match)\s*\(\s*"
    r"(?:\[[^\]]*\]|[\"']([^\"']+)[\"'])",
)
LARAVEL_RESOURCE_RE = re.compile(
    r"\bRoute::(resource|apiResource)\s*\(\s*[\"']([^\"']+)[\"']",
)
LARAVEL_MODEL_RE = re.compile(
    r"\bclass\s+([A-Za-z_]\w*)\s+extends\s+(Model|Authenticatable|Eloquent\\Model)",
)
LARAVEL_MIGRATION_RE = re.compile(
    r"\bclass\s+([A-Za-z_]\w*)\s+extends\s+Migration",
)


def parse_laravel_routes(text: str) -> list[tuple[str, str, int]]:
    offsets = _line_offsets(text)
    routes: list[tuple[str, str, int]] = []
    for match in LARAVEL_ROUTE_RE.finditer(text):
        verb_word = match.group(1).lower()
        verb = "ANY" if verb_word in {"any", "match"} else verb_word.upper()
        raw_path = match.group(2)
        if raw_path is None:
            continue
        path = raw_path if raw_path.startswith("/") else "/" + raw_path
        routes.append((verb, path, _line_for_offset(offsets, match.start())))
    for match in LARAVEL_RESOURCE_RE.finditer(text):
        base = match.group(2)
        base = base if base.startswith("/") else "/" + base
        line = _line_for_offset(offsets, match.start())
        routes.extend(
            [
                ("GET", base, line),
                ("POST", base, line),
                ("GET", f"{base}/{{id}}", line),
                ("PUT", f"{base}/{{id}}", line),
                ("PATCH", f"{base}/{{id}}", line),
                ("DELETE", f"{base}/{{id}}", line),
            ]
        )
    return routes


def laravel_models(text: str) -> list[str]:
    return [match.group(1) for match in LARAVEL_MODEL_RE.finditer(text)]


def laravel_migrations(text: str) -> list[str]:
    return [match.group(1) for match in LARAVEL_MIGRATION_RE.finditer(text)]


# --- Prisma ---------------------------------------------------------------

PRISMA_MODEL_RE = re.compile(
    r"^\s*model\s+([A-Za-z_]\w*)\s*\{([^}]*)\}",
    re.MULTILINE | re.DOTALL,
)
PRISMA_FIELD_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s+([A-Za-z_]\w*(?:\[\])?\??)(?:\s+([^#\n]*))?$",
    re.MULTILINE,
)


def parse_prisma_models(
    text: str,
) -> list[tuple[str, list[tuple[str, str, str]], int]]:
    """Return [(model_name, [(field_name, field_type, attributes)], line)]."""

    offsets = _line_offsets(text)
    models: list[tuple[str, list[tuple[str, str, str]], int]] = []
    for match in PRISMA_MODEL_RE.finditer(text):
        name = match.group(1)
        body = match.group(2)
        fields: list[tuple[str, str, str]] = []
        for field in PRISMA_FIELD_RE.finditer(body):
            field_name = field.group(1)
            if field_name in {"model", "enum", "datasource", "generator"}:
                continue
            field_type = field.group(2)
            attrs = (field.group(3) or "").strip()
            fields.append((field_name, field_type, attrs))
        line = _line_for_offset(offsets, match.start())
        models.append((name, fields, line))
    return models


# --- SQLAlchemy / Alembic -------------------------------------------------

SQLALCHEMY_MODEL_RE = re.compile(
    r"^\s*class\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*:",
    re.MULTILINE,
)
SQLALCHEMY_TABLENAME_RE = re.compile(
    r"^\s*__tablename__\s*=\s*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
SQLALCHEMY_COLUMN_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*(?::\s*Mapped\[[^\]]+\])?\s*=\s*"
    r"(?:mapped_column|Column)\s*\(",
    re.MULTILINE,
)
SQLALCHEMY_RELATIONSHIP_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*(?::\s*[^=]+)?\s*=\s*relationship\s*\(\s*"
    r"[\"']([A-Za-z_]\w*)[\"']",
    re.MULTILINE,
)

ALEMBIC_OP_RE = re.compile(
    r"\bop\.(create_table|drop_table|add_column|drop_column|alter_column|"
    r"create_index|drop_index|rename_table|create_foreign_key|drop_constraint)"
    r"\s*\(\s*[\"']([^\"']+)[\"']",
)


def parse_sqlalchemy_models(text: str) -> list[dict[str, object]]:
    base_hints = ("Base", "DeclarativeBase", "Model", "db.Model")
    candidates = []
    for match in SQLALCHEMY_MODEL_RE.finditer(text):
        bases = match.group(2)
        if any(hint in bases for hint in base_hints):
            candidates.append((match.group(1), match.start()))
    tablename_by_pos = {
        match.start(): match.group(1) for match in SQLALCHEMY_TABLENAME_RE.finditer(text)
    }
    columns_by_pos = {match.start(): match.group(1) for match in SQLALCHEMY_COLUMN_RE.finditer(text)}
    relationships_by_pos = {
        match.start(): (match.group(1), match.group(2))
        for match in SQLALCHEMY_RELATIONSHIP_RE.finditer(text)
    }
    offsets = _line_offsets(text)
    models: list[dict[str, object]] = []
    for index, (name, start) in enumerate(candidates):
        end = candidates[index + 1][1] if index + 1 < len(candidates) else len(text)
        body_range = (start, end)
        tablename = next(
            (value for position, value in tablename_by_pos.items() if body_range[0] <= position < body_range[1]),
            None,
        )
        columns = [value for position, value in columns_by_pos.items() if body_range[0] <= position < body_range[1]]
        relationships = [
            value for position, value in relationships_by_pos.items() if body_range[0] <= position < body_range[1]
        ]
        models.append(
            {
                "name": name,
                "tablename": tablename,
                "columns": columns,
                "relationships": relationships,
                "line": _line_for_offset(offsets, start),
            }
        )
    return models


def parse_alembic_ops(text: str) -> list[tuple[str, str, int]]:
    offsets = _line_offsets(text)
    ops: list[tuple[str, str, int]] = []
    for match in ALEMBIC_OP_RE.finditer(text):
        ops.append((match.group(1), match.group(2), _line_for_offset(offsets, match.start())))
    return ops


# --- shared helpers -------------------------------------------------------


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
