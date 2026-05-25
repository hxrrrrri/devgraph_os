# DevGraph OS Audit Report

Date: 2026-05-25

| Area | Previous score | New score | Evidence |
|---|---:|---:|---|
| Monorepo structure | 7 | 8 | Backend, dashboard, VS Code, schema/client packages, docs, tests, and CI-ready commands remain in one workspace. |
| CLI | 7 | 8 | Added `debug --json`, `embed`, safer external ingest, richer review/handoff/memory behavior. |
| SQLite graph core | 8 | 8 | Existing FTS/provenance/memory/session/snapshot store retained; imports directory added. |
| Parser/extraction | 5 | 8 | Added requested parser module boundaries, broader language registry, Tree-sitter adapter, SQL table extraction, Vue/Svelte component nodes, Terraform/Kubernetes/RST extraction. |
| Incremental update | 7 | 8 | Existing update path retained; diff parser and changed-symbol mapping added. |
| Review engine | 5 | 8 | Review now emits hunks, changed symbols, impacted flows/files, tests, missing tests, API/config/security/database classifications, prioritized items, and richer risk scoring. |
| Context packer | 5 | 8 | Packs now use readable graph paths, focused chunks, task-specific sections, memories, provenance/confidence, and token trimming. |
| MCP | 7 | 8 | Added node detail, file context, review artifacts, provenance, and snapshots. Existing tools now have docstrings and richer JSON. |
| Dashboard | 5 | 8 | Rebuilt as dark command center with icon rail, command bar, KPI cards, charts, graph explorer, review/debug/knowledge/onboarding/flow lenses. |
| VS Code extension | 5 | 7 | Added settings, configured binary, dashboard startup, search/trace/handoff/report commands, and richer sidebar status. |
| Knowledge ingestion | 4 | 7 | Added focused Markdown/RST chunks, config chunks, SQL chunks, Terraform/Kubernetes extraction, external import copy, and wiki expansion. |
| Handoff | 6 | 8 | Handoff now writes markdown/JSON with branch, graph freshness, changed symbols, impacted files, reports, memories, TODO/FIXME scan, and continuation prompt. |
| Tests | 5 | 8 | Added required unit/integration coverage; full suite has 40 tests passing. |
| Docs | 6 | 8 | Updated README, commands, architecture, MCP, VS Code, graph schema, context engine, security model, examples, dashboard, roadmap, and security policy. |
| Product readiness | 6 | 8 | Local-first defaults, quality gates pass, dashboard/extension build. Remaining work is deeper per-language Tree-sitter queries and richer docs-code claim validation. |

## Implemented Features

- Focused chunking by code symbol, Markdown heading, config key, SQL statement, and generic line windows.
- Optional Tree-sitter adapter with conservative fallback extraction.
- Multilanguage fallback extraction for Python, JS/TS/TSX, Go, Rust, Java, C/C++, C#, Ruby, PHP, Kotlin, Swift, Scala, Dart, Lua, Bash, SQL, Vue, and Svelte.
- Unified diff parser and changed-line to graph-node mapping.
- Deep review JSON schema and reports.
- Readable context packs with no internal IDs in graph path sections.
- Structured debug stack parsing for Python, Node/TypeScript, Java, Go, and Rust.
- Cross-agent handoff artifacts and memory commands.
- Expanded MCP and HTTP API endpoints.
- Premium dark dashboard consuming local backend APIs.
- VS Code extension settings, commands, dashboard launch, and richer sidebar.
- External import handling and secret redaction improvements.
- Wiki output expanded with architecture, flows, symbols, decisions, and review.

## Remaining Limitations

- Tree-sitter extraction is strongest where grammars and generic node names match; some languages still rely on regex fallbacks.
- Framework route extraction is currently strongest for common JS/TS Express-style routes.
- Semantic search is disabled by default. `--local-hash` provides deterministic local vectors; sentence-transformers requires explicit local setup.
- Stale docs detection is conservative and not yet a full claim verifier.
- Dashboard bundle is large because graph visualization, charts, and animation libraries ship together.

## Commands Run

```bash
python -m pytest
ruff check .
mypy devgraph
bandit -q -r devgraph -c pyproject.toml
pnpm install
pnpm typecheck
pnpm --filter @devgraph/dashboard build
pnpm --filter @devgraph/vscode-extension compile
```

## Test Results

- `python -m pytest`: 40 passed.
- `ruff check .`: passed.
- `mypy devgraph`: passed.
- `bandit -q -r devgraph -c pyproject.toml`: passed.
- `pnpm typecheck`: passed.
- `pnpm --filter @devgraph/dashboard build`: passed with Vite chunk-size warning.
- `pnpm --filter @devgraph/vscode-extension compile`: passed.

## Known Risks

- Broad parser fallback coverage is useful but not equivalent to fully curated Tree-sitter queries per language.
- Review/debug intelligence is deterministic and rule-based; it should be treated as decision support, not an autonomous reviewer.
- Large repositories may need graph pagination and dashboard virtualization beyond the current limits.

## Next Roadmap

1. Add language-specific Tree-sitter queries for Ruby/PHP/C#/Kotlin/Swift/Scala/Dart/Lua/Bash.
2. Add framework plugins for Django/FastAPI/Flask/Nest/Next/Spring/Rails/Laravel.
3. Expand stale-doc detection into symbol/file claim validation.
4. Add graph pagination and code-split dashboard chunks.
5. Add more CI fixtures for staged/base-branch git diffs.
