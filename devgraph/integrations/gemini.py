"""Gemini CLI integration."""

from __future__ import annotations

from devgraph.integrations.generic import render_platform_instructions


def render() -> str:
    return render_platform_instructions("gemini")

