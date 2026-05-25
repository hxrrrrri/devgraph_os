"""Test symbol helpers."""

from __future__ import annotations


def is_test_symbol(name: str) -> bool:
    lower = name.lower()
    return lower.startswith("test") or lower.endswith("test") or ".test" in lower or ".spec" in lower

