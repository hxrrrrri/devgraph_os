"""Route extraction helpers."""

from __future__ import annotations

import os
import re

ROUTE_RE = re.compile(
    r"\b(?:app|router|server)\.(get|post|put|patch|delete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

NESTJS_CONTROLLER_RE = re.compile(
    r"@Controller\s*\(\s*(?:[\"']([^\"']*)[\"'])?\s*\)",
)

NESTJS_METHOD_RE = re.compile(
    r"@(Get|Post|Put|Patch|Delete|Options|Head|All)\s*\(\s*(?:[\"']([^\"']*)[\"'])?\s*\)",
)

NEXTJS_ROUTE_EXPORT_RE = re.compile(
    r"\bexport\s+(?:async\s+)?(?:const|function|let|var)\s+"
    r"(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b",
)

NEXTJS_SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs"}
NEXTJS_PAGE_SKIP_STEMS = {"_app", "_document", "_error", "_middleware", "middleware"}

PYTHON_DECORATOR_ROUTE_RE = re.compile(
    r"^\s*@(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)\.(get|post|put|patch|delete|options|head|websocket|route)"
    r"\s*\(\s*[\"']([^\"']+)[\"']",
    re.MULTILINE | re.IGNORECASE,
)

FLASK_ROUTE_RE = re.compile(
    r"^\s*@(?:[A-Za-z_]\w*\.)*(?:app|bp|blueprint|[a-z_]\w*)\.route"
    r"\s*\(\s*[\"']([^\"']+)[\"'](?:[^)]*methods\s*=\s*\[([^\]]*)\])?",
    re.MULTILINE | re.IGNORECASE,
)

DJANGO_URL_RE = re.compile(
    r"\b(?:path|re_path|url)\s*\(\s*[\"']([^\"']+)[\"']\s*,\s*([A-Za-z_][\w.]*)",
)


def parse_js_ts_routes(text: str) -> list[tuple[str, str, int]]:
    offsets = _line_offsets(text)
    routes: list[tuple[str, str, int]] = []
    for match in ROUTE_RE.finditer(text):
        routes.append((match.group(1).upper(), match.group(2), _line_for_offset(offsets, match.start())))
    return routes


def parse_python_routes(text: str) -> list[tuple[str, str, int]]:
    """Extract FastAPI/Flask/Django route declarations.

    Returns (HTTP_METHOD, path, line). Method is "ANY" for Django path() / Flask
    route() with no explicit methods.
    """

    offsets = _line_offsets(text)
    routes: list[tuple[str, str, int]] = []

    for match in PYTHON_DECORATOR_ROUTE_RE.finditer(text):
        verb = match.group(2)
        path = match.group(3)
        method = verb.upper() if verb.lower() not in {"route", "websocket"} else (
            "WEBSOCKET" if verb.lower() == "websocket" else "ANY"
        )
        routes.append((method, path, _line_for_offset(offsets, match.start())))

    for match in FLASK_ROUTE_RE.finditer(text):
        path = match.group(1)
        methods_block = match.group(2) or ""
        methods = [m.strip().strip("'\"").upper() for m in methods_block.split(",") if m.strip()]
        line = _line_for_offset(offsets, match.start())
        if methods:
            for method in methods:
                routes.append((method, path, line))
        else:
            routes.append(("GET", path, line))

    for match in DJANGO_URL_RE.finditer(text):
        path = match.group(1)
        routes.append(("ANY", path, _line_for_offset(offsets, match.start())))

    return routes


def parse_nestjs_routes(text: str) -> list[tuple[str, str, int]]:
    """Extract NestJS routes by pairing @Controller prefix with HTTP method decorators.

    Returns (HTTP_METHOD, path, line) tuples.
    """

    controllers = list(NESTJS_CONTROLLER_RE.finditer(text))
    methods = list(NESTJS_METHOD_RE.finditer(text))
    if not methods:
        return []
    offsets = _line_offsets(text)
    routes: list[tuple[str, str, int]] = []
    for match in methods:
        prefix = ""
        for controller in controllers:
            if controller.start() < match.start():
                prefix = controller.group(1) or ""
            else:
                break
        verb = match.group(1).upper()
        sub = (match.group(2) or "").strip("/")
        prefix = prefix.strip("/")
        parts = [segment for segment in (prefix, sub) if segment]
        path = "/" + "/".join(parts) if parts else "/"
        routes.append((verb, path, _line_for_offset(offsets, match.start())))
    return routes


def parse_nextjs_routes_for_path(
    rel_path: str, text: str
) -> list[tuple[str, str, int]]:
    """Extract Next.js file-based routes from app/ and pages/ directories.

    Returns (HTTP_METHOD, route_path, line) tuples. `rel_path` is the POSIX
    repo-relative file path used to derive the route.
    """

    parts = [segment for segment in rel_path.split("/") if segment]
    anchor: str | None = None
    anchor_index: int = -1
    for index, segment in enumerate(parts):
        if segment in {"app", "pages"}:
            anchor = segment
            anchor_index = index
    if anchor is None or anchor_index < 0:
        return []
    segments = parts[anchor_index + 1 :]
    if not segments:
        return []
    filename = segments[-1]
    stem, ext = os.path.splitext(filename)
    if ext.lower() not in NEXTJS_SOURCE_SUFFIXES:
        return []

    directory_segments: list[str] = []
    for segment in segments[:-1]:
        if anchor == "app" and segment.startswith("(") and segment.endswith(")"):
            continue
        directory_segments.append(segment)

    if anchor == "app":
        if stem == "page":
            route_path = "/" + "/".join(directory_segments) if directory_segments else "/"
            return [("GET", _normalize(route_path), 1)]
        if stem == "route":
            route_path = "/" + "/".join(directory_segments) if directory_segments else "/"
            offsets = _line_offsets(text)
            routes: list[tuple[str, str, int]] = []
            for match in NEXTJS_ROUTE_EXPORT_RE.finditer(text):
                routes.append(
                    (
                        match.group(1).upper(),
                        _normalize(route_path),
                        _line_for_offset(offsets, match.start()),
                    )
                )
            return routes
        return []

    if stem in NEXTJS_PAGE_SKIP_STEMS:
        return []
    page_segments = directory_segments if stem == "index" else [*directory_segments, stem]
    page_path = "/" + "/".join(page_segments) if page_segments else "/"
    is_api = bool(directory_segments) and directory_segments[0] == "api"
    method = "ANY" if is_api else "GET"
    return [(method, _normalize(page_path), 1)]


def _normalize(path: str) -> str:
    if path == "/":
        return path
    return path.rstrip("/") or "/"


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

