# DevGraph OS

DevGraph OS is a local-first AI context engine for software projects. It builds a persistent developer knowledge graph from code, docs, configs, infrastructure files, commits, diffs, and developer sessions, then exposes that intelligence through a CLI, MCP tools, AI-agent slash commands, a VS Code extension, and a web dashboard.

Developers and AI coding agents should never read a codebase blindly again.

## What It Does

- Indexes repositories into a SQLite-backed graph with deterministic provenance.
- Extracts files, symbols, imports, calls, docs, configs, routes, tests, and change data.
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
devgraph serve
```

The default storage lives under `.devgraph/`.

## CLI Examples

```bash
devgraph ask "How does authentication work?"
devgraph path AuthService DatabasePool
devgraph trace AuthService.login
devgraph review --base origin/main
devgraph review --staged
devgraph review --files src/auth.py src/server.ts
devgraph debug "TypeError in src/auth/login.ts line 42"
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

The server exposes a compact tool surface including `build_or_update_graph`, `get_project_status`, `doctor`, `get_context`, `review_changes`, `explain`, `query_graph`, memory tools, and `handoff_session`. See [docs/MCP.md](docs/MCP.md).

## VS Code Extension

The extension in `apps/vscode-extension` shells out to the local `devgraph` CLI. It contributes command palette actions for initialize, build, update, review, explain, ask, doctor, memory capture, dashboard, and handoff. See [docs/VSCODE_EXTENSION.md](docs/VSCODE_EXTENSION.md).

## Dashboard

The dashboard in `apps/dashboard` is a Vite/React app backed by the local HTTP server:

```bash
devgraph dashboard
```

The dashboard includes graph visualization, review, debug, onboarding, and knowledge lenses backed by local HTTP APIs.

## Architecture

DevGraph OS has four main layers:

1. Extractors convert project artifacts into typed graph nodes, edges, and retrievable chunks.
2. The SQLite graph store persists canonical facts, FTS indexes, snapshots, sessions, and provenance.
3. Intelligence modules run review, debug, onboarding, explain, handoff, and context-packing workflows.
4. Interfaces expose the same engine through CLI, MCP, dashboard, VS Code, and slash-command templates.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Privacy Model

DevGraph OS is local-first by default:

- No telemetry.
- No analytics.
- No cloud calls by default.
- `.env` values and likely secrets are redacted.
- Deterministic facts, inferred facts, LLM facts, ambiguous facts, and user-approved facts carry separate confidence tiers.
- Optional LLM enrichment must be explicitly enabled in `devgraph.toml`.

## Roadmap

The first implementation focuses on a usable local graph, review context, MCP tools, dashboard shell, and VS Code shell. Future work expands Tree-sitter coverage, semantic embeddings, richer flow detection, multi-repo graphs, and optional managed collaboration workflows. See [docs/ROADMAP.md](docs/ROADMAP.md).
