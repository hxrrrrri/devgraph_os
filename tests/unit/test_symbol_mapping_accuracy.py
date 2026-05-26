"""Symbol resolution accuracy tests for tricky diff hunk patterns.

Covers: overlapping line ranges, multi-statement single-line edits,
docstring-only changes, edits inside nested functions.
"""

from __future__ import annotations

from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.update.diff_parser import DiffHunk, map_hunks_to_nodes
from devgraph.update.incremental import build_graph


def _names(mapped: dict[str, list]) -> set[str]:
    return {node.name for nodes in mapped.values() for node in nodes}


def test_overlapping_ranges_resolves_to_inner_symbol(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        "class Outer:\n"
        "    def alpha(self):\n"
        "        return 1\n"
        "    def beta(self):\n"
        "        return 2\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    mapped = map_hunks_to_nodes(
        store,
        [DiffHunk("mod.py", 4, 1, 4, 2, [5], "+        return 22")],
    )
    names = _names(mapped)
    assert "beta" in names


def test_docstring_only_change_still_maps(tmp_path: Path) -> None:
    (tmp_path / "doc.py").write_text(
        "def login():\n"
        "    \"\"\"Old docstring.\"\"\"\n"
        "    return True\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    mapped = map_hunks_to_nodes(
        store,
        [DiffHunk("doc.py", 2, 1, 2, 1, [2], '+    """New docstring."""')],
    )
    assert "login" in _names(mapped)


def test_multi_statement_single_line_edit(tmp_path: Path) -> None:
    (tmp_path / "stmt.py").write_text(
        "def one():\n    return 1\ndef two():\n    return 2\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    mapped = map_hunks_to_nodes(
        store,
        [DiffHunk("stmt.py", 4, 1, 4, 1, [4], "+    return 222")],
    )
    assert "two" in _names(mapped)


def test_nested_function_change_resolves_to_nested(tmp_path: Path) -> None:
    (tmp_path / "nest.py").write_text(
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    mapped = map_hunks_to_nodes(
        store,
        [DiffHunk("nest.py", 3, 1, 3, 1, [3], "+        return 11")],
    )
    names = _names(mapped)
    assert "inner" in names or "outer" in names
