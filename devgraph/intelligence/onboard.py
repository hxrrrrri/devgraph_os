"""Onboarding report generation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from devgraph.core.graph_store import GraphStore


class OnboardingEngine:
    def __init__(self, root: Path, store: GraphStore) -> None:
        self.root = root
        self.store = store

    def generate(self) -> Path:
        status = self.store.get_status(self.root.name)
        files = self._important_files()
        symbols = self._important_symbols()
        lines = [
            "# DevGraph Project Onboarding",
            "",
            "## Project overview",
            f"- Project: `{status.project}`",
            f"- Files indexed: {status.total_files}",
            f"- Nodes: {status.total_nodes}",
            f"- Edges: {status.total_edges}",
            "",
            "## Language summary",
            *[f"- {language}: {count}" for language, count in status.languages.items()],
            "",
            "## Architecture layers",
            "- Code modules and files are represented as `module`, `class`, `function`, and `test` nodes.",
            "- Documentation is represented as `document` and `section` nodes.",
            "- Config and infra artifacts are represented as `config`, `pipeline`, and `resource` nodes.",
            "",
            "## Important files",
            *[f"- `{path}`" for path in files],
            "",
            "## Read these files first",
            *[f"- `{path}`" for path in files[:8]],
            "",
            "## Key symbols",
            *[f"- `{symbol}`" for symbol in symbols[:20]],
            "",
            "## Glossary",
            "- extracted: deterministic parser result.",
            "- inferred: deterministic indirect inference.",
            "- ambiguous: uncertain result needing review.",
            "",
            "## Guided tour",
            "1. Start with the README and top-level config files.",
            "2. Inspect high-degree modules from the key symbols list.",
            "3. Use `devgraph explain <file>` for each subsystem entry point.",
            "4. Run `devgraph review` before changing public APIs or configs.",
            "",
            "## Suggested questions",
            "- How is the project organized?",
            "- Which files should I read before editing authentication or persistence?",
            "- What tests cover the module I am changing?",
        ]
        reports = self.store.storage_path / "reports"
        wiki = self.store.storage_path / "wiki"
        reports.mkdir(parents=True, exist_ok=True)
        wiki.mkdir(parents=True, exist_ok=True)
        report_path = reports / "onboarding.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        (wiki / "index.md").write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def _important_files(self) -> list[str]:
        rows = self.store.connection.execute(
            """
            SELECT file_path, COUNT(*) AS count
            FROM nodes
            WHERE file_path IS NOT NULL
            GROUP BY file_path
            ORDER BY count DESC
            LIMIT 20
            """
        ).fetchall()
        return [row["file_path"] for row in rows]

    def _important_symbols(self) -> list[str]:
        rows = self.store.connection.execute(
            """
            SELECT n.qualified_name, COUNT(e.id) AS degree
            FROM nodes n
            LEFT JOIN edges e ON e.source_id = n.id OR e.target_id = n.id
            WHERE n.type IN ('module', 'class', 'function', 'service', 'api_endpoint')
            GROUP BY n.id
            ORDER BY degree DESC
            LIMIT 30
            """
        ).fetchall()
        counter = Counter(row["qualified_name"] for row in rows)
        return list(counter.keys())

