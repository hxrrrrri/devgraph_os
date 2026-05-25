"""Token budget utilities."""

from __future__ import annotations

BUDGETS = {
    "tiny": 700,
    "normal": 4000,
    "deep": 12000,
    "full": 1_000_000,
}


def budget_tokens(name: str | None) -> int:
    return BUDGETS.get(name or "normal", BUDGETS["normal"])


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_to_budget(text: str, budget: int) -> str:
    if budget >= BUDGETS["full"] or estimate_tokens(text) <= budget:
        return text
    max_chars = max(256, budget * 4)
    return text[:max_chars].rstrip() + "\n\n[trimmed to token budget]"

