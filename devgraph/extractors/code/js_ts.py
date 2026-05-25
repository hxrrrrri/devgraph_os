"""JavaScript and TypeScript fallback helpers."""

from __future__ import annotations

from devgraph.extractors.code.calls import parse_js_ts_calls
from devgraph.extractors.code.imports import parse_js_ts_imports
from devgraph.extractors.code.routes import parse_js_ts_routes

__all__ = ["parse_js_ts_calls", "parse_js_ts_imports", "parse_js_ts_routes"]
