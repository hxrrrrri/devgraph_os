"""Debug context engine."""

from __future__ import annotations

import re

from devgraph.core.graph_store import GraphStore
from devgraph.retrieval.context_packer import ContextPacker, ContextRequest

STACK_PATH_RE = re.compile(r"(?P<path>[\w./\\-]+\.(?:py|ts|tsx|js|jsx|go|rs|java))(?::(?P<line>\d+))?")


class DebugEngine:
    def __init__(self, store: GraphStore) -> None:
        self.store = store
        self.packer = ContextPacker(store)

    def debug(self, issue: str, budget: str = "normal") -> str:
        seed_files = []
        for match in STACK_PATH_RE.finditer(issue):
            seed_files.append(match.group("path").replace("\\", "/").lstrip("./"))
        entry_points = [f"- `{path}`" for path in seed_files]
        if not entry_points:
            entry_points = ["- No stack-trace file paths were detected."]
        pack = self.packer.pack(
            ContextRequest(
                task_type="debug",
                query=issue,
                seed_files=seed_files,
                token_budget=budget,
                include_source=True,
            )
        )
        return "\n".join(
            [
                "# DevGraph Debug Context",
                "",
                "## Suspected entry points",
                *entry_points,
                "",
                pack,
            ]
        )
