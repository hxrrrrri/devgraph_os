# DevGraph OS

DevGraph OS is a local-first AI context engine for software projects. It builds a persistent developer knowledge graph from code, docs, configs, infrastructure files, commits, diffs, and developer sessions, then exposes that intelligence through a CLI, MCP tools, AI-agent slash commands, a VS Code extension, and a web dashboard.

Developers and AI coding agents should never read a codebase blindly again.

## Feature Status

Honest maturity per area. Treat *Beta* as working but rough edges; *Experimental* as best-effort with known gaps; *Planned* as not implemented.

| Area | Status | Notes |
|---|---|---|
| Python extraction (tree-sitter primary, AST fallback) | Implemented | All `def`/`class`/imports/calls via tree-sitter; AST handles parse errors. |
| JS/TS/TSX/Go/Rust/Java/C/C++/C#/Ruby/PHP/Kotlin/Swift/Scala/Bash extraction | Implemented | Real tree-sitter; provenance tested per language. |
| FastAPI / Flask / Django route extraction | Beta | Decorator + URLconf patterns; mounted routers resolve to local paths only. |
| Express-style JS/TS routes | Implemented | `app.get/post/...` pattern; `framework="express"` metadata. |
| NestJS route plugin | Beta | `@Controller` prefix + `@Get/@Post/@Put/@Patch/@Delete/@Options/@Head/@All` decorators. Fixture: `tests/fixtures/repos/ts_nestjs_app`. |
| Next.js file-based routes | Beta | `app/` (`page`, `route`, route groups stripped) + `pages/` (incl. `pages/api`). Fixture: `tests/fixtures/repos/react_next_app`. |
| Spring / Rails / Laravel route plugins | Planned | — |
| SQL table extraction + chunking | Implemented | `CREATE TABLE`, `ALTER`, `INSERT INTO`, `JOIN`. |
| Migration risk detector (DROP, NOT NULL w/o default, FK, type change) | Implemented | Surfaces structured warnings in `review.json`. |
| Review engine (changed symbols, impacted files, risk score, prioritized items) | Implemented | Rule-based; treat as decision support, not autonomous reviewer. |
| Public API compatibility detector | Beta | Path/name heuristics; no signature-diff check yet. |
| Test coverage gap heuristic | Beta | Graph-based "no related test" signal; not real coverage. |
| Local SQLite graph + FTS + provenance | Implemented | Migrations, snapshots, memories. |
| Local embeddings (`--local-hash`) | Beta | Deterministic local vectors; sentence-transformers opt-in. |
| Incremental update + diff parser | Implemented | Hunks mapped to graph nodes. |
| Cross-agent handoff (markdown + JSON) | Implemented | Branch, changed symbols, impacted files, continue prompt. |
| MCP tool surface | Implemented | `build_or_update_graph`, `get_context`, `review_changes`, `query_graph`, memory. |
| Dashboard (graph cockpit: architecture overview, layer drill, modes, inspector, path finder, file/code viewer, tour, persona) | Implemented (v1.3) | Vite manualChunks split (largest chunk 315 kB); 24 vitest unit + component tests; no graph virtualization on >10k node graphs yet. |
| VS Code extension (commands, status view, CodeLens) | Beta | CodeLens for explain/review on Python/JS/TS; webview node-detail Planned. |
| Fixture repos | Beta | `python_fastapi_service`, `ts_nestjs_app`, `react_next_app` landed; `ts_express_app`, `mixed_docs_config_repo`, `migration_database_repo` Planned. |
| CI (lint, typecheck, security, tests, dashboard build, bundle-size guard) | Implemented | GitHub Actions; pnpm + pip caching. |
| Stale-doc / claim verifier | Experimental | Conservative; not a full claim verifier. |
| Wiki generation | Implemented | Markdown wiki from graph. |
| Coverage thresholds in CI | Planned | Baseline not yet established. |

## What It Does

- Indexes repositories into a SQLite-backed graph with deterministic provenance.
- Extracts files, symbols, imports, calls, docs, configs, routes, tests, and change data.
- Uses Tree-sitter semantic extraction for supported local grammars and Python AST extraction for Python.
- Supports optional local embeddings for hybrid FTS/vector retrieval without cloud calls.
- Answers explain, ask, review, debug, onboarding, and handoff workflows from graph-grounded context.
- Serves a local dashboard and MCP tool surface for AI coding agents.
- Keeps all default processing local with no telemetry and no cloud calls.

## Quick Start

```bash
pip install -e .
devgraph init
devgraph build
devgraph status
devgraph explain src/auth/login.ts
devgraph review
devgraph dashboard
```

The default storage lives under `.devgraph/`.

## CLI Examples

```bash
devgraph ask "How does authentication work?"
devgraph search "login user authentication" --json
devgraph path AuthService DatabasePool
devgraph trace AuthService.login
devgraph review --base origin/main
devgraph review --staged
devgraph review --files src/auth.py src/server.ts
devgraph debug "TypeError in src/auth/login.ts line 42" --json
devgraph embed --local-hash
devgraph remember --kind decision "We use SQLite as the local graph store."
devgraph memories
devgraph onboard
devgraph handoff
devgraph export --format json
devgraph wiki
```

## MCP Usage

Start the MCP server:

```bash
devgraph mcp
```

The server exposes a compact tool surface including `build_or_update_graph`, `get_project_status`, `doctor`, `get_context`, `review_changes`, `explain`, hybrid `query_graph`/`search`, memory tools, and `handoff_session`. See [docs/MCP.md](docs/MCP.md).

## VS Code Extension

The extension in `apps/vscode-extension` shells out to the local `devgraph` CLI. It contributes command palette actions for initialize, build, update, review, explain, ask, doctor, memory capture, dashboard, and handoff. See [docs/VSCODE_EXTENSION.md](docs/VSCODE_EXTENSION.md).

## Dashboard

The dashboard in `apps/dashboard` is a Vite/React app backed by the local HTTP server:

```bash
devgraph dashboard
```

The dashboard is a dark developer command center with command, graph, review,
debug, onboarding, knowledge, and flow lenses backed by local HTTP APIs.

**v1.3 graph cockpit** ships an Understand-Anything-style architecture
explorer on top of the DevGraph engine:

- **Architecture overview** — 9 derived layers (entry / ui / app / domain /
  data / infra / tests / docs / memory) rendered as cluster nodes with
  inter-layer edge weights.
- **Layer detail** — drill into a layer to see folder/community containers
  with expand-on-click, intra-container edges, and portal nodes that link
  to other layers.
- **Modes** — Overview, Architecture, Impact (changed + 1-hop), Flow
  (left-to-right call/route/read/write chains), Community (Louvain
  partition).
- **Node inspector** — five tabs (overview, source, relations, provenance,
  review impact) fed by `/api/node/:id`, `/api/file-context`,
  `/api/provenance/:id`.
- **Path finder** — pick a source and target node, get the shortest path
  on the canvas via `/api/path`.
- **File explorer** — directory tree with changed / affected / risk
  badges; click a file to open the code viewer.
- **Code viewer** — syntax highlight via `prism-react-renderer`, markdown
  rendering for docs, per-line diff highlighting from
  `review.changed_hunks`.
- **Guided tour & learn panel** — 9-step walkthrough plus five persona
  voices (junior / senior / reviewer / architect / ai-agent).
- **Keyboard** — `⌘K` palette, `j`/`k` nav, `D` diff, `P` path, `F` files,
  `T` tour.

The dashboard's architecture endpoints (`/api/architecture`,
`/api/layers/:id`, `/api/path`) are stable and intended for MCP / agent
consumers as well.

## Architecture

DevGraph OS has four main layers:

1. Extractors convert project artifacts into typed graph nodes, edges, semantic metadata, SQL/database references, API routes, and focused retrievable chunks.
2. The SQLite graph store persists canonical facts, FTS indexes, local embedding vectors, snapshots, sessions, and provenance.
3. Intelligence modules run review, debug, onboarding, explain, handoff, hybrid search, and context-packing workflows.
4. Interfaces expose the same engine through CLI, MCP, dashboard, VS Code, and slash-command templates.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Privacy Model

DevGraph OS is local-first by default:

- No telemetry.
- No analytics.
- No cloud calls by default. Embeddings are disabled unless explicitly enabled or run with `devgraph embed --local-hash`.
- `.env` values and likely secrets are redacted.
- Deterministic facts, inferred facts, LLM facts, ambiguous facts, and user-approved facts carry separate confidence tiers.
- Optional LLM enrichment must be explicitly enabled in `devgraph.toml`.

## Roadmap

## Current Limitations

- Tree-sitter is used when `tree-sitter-language-pack` is installed; otherwise DevGraph falls back to conservative AST/regex extraction and marks uncertain facts.
- Review, debug, onboarding, and handoff are deterministic rule-based intelligence workflows. They are useful without an LLM, but they do not claim autonomous reasoning.
- Optional `sentence-transformers` semantic search requires local model availability. DevGraph never calls hosted embedding APIs unless future OpenAI-compatible settings are explicitly configured.
- Dashboard data comes from the local HTTP API; if the graph is stale, the UI shows stale or empty states rather than fake data.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the remaining product roadmap.
