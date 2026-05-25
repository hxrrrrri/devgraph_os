"""Tree-sitter adapter boundary.

The implementation is intentionally isolated so callers can distinguish
high-confidence Tree-sitter facts from regex or AST fallbacks.
"""

from __future__ import annotations

from devgraph.extractors.code.semantic_tree_sitter import (
    SemanticParseResult,
    TreeSitterSemanticAnalyzer,
)

__all__ = ["SemanticParseResult", "TreeSitterSemanticAnalyzer"]
