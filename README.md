# DevGraph OS

DevGraph OS is a local-first AI context engine for software projects. It builds a persistent developer knowledge graph from code, docs, configs, infrastructure files, commits, diffs, and developer sessions, then exposes that intelligence through a CLI, MCP tools, AI-agent slash commands, a VS Code extension, and a web dashboard.

Developers and AI coding agents should never read a codebase blindly again.

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

The dashboard is a dark developer command center with command, graph, review, debug, onboarding, knowledge, and flow lenses backed by local HTTP APIs.

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
