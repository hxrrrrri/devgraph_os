# Contributing

DevGraph OS is built as a local-first open-source developer tool. Contributions should preserve deterministic provenance, privacy defaults, and clear module boundaries.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy devgraph
pnpm install
pnpm typecheck
```

## Guidelines

- Keep parser-derived facts separate from inferred, LLM, ambiguous, and user-approved facts.
- Do not add telemetry, analytics, or cloud dependencies to default workflows.
- Prefer small, testable modules.
- Add fixtures for parser and graph changes.
- Update docs when CLI, schema, or MCP behavior changes.

