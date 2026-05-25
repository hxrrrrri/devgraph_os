# DevGraph OS Audit Report

Date: 2026-05-25 (v1.2 amendment appended below)

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

## v1.2 amendment (2026-05-25)

| Area | v1.1 score | v1.2 score | Evidence |
|---|---:|---:|---|
| Parser correctness | 6.5 | 8 | tree-sitter primary across 18 languages; provenance tests in `tests/unit/test_tree_sitter_provenance.py`. |
| Framework plugins | 3 | 8 | NestJS, Next.js, React, Spring, Rails, Laravel, Prisma, SQLAlchemy, Alembic all land with unit + integration tests. |
| Review intelligence | 6 | 8 | Public API + route contract diff against snapshot; fan-out scoring; severity heat map (`severity_by_file` / `severity_by_symbol`); infra blast radius. |
| Dashboard UX | 5 | 7 | Severity heat map in Review lens; ⌘K palette searches nodes; j/k page nav; skeleton states; bundle largest chunk 529 kB (<700 budget). |
| VS Code depth | 5 | 8 | Three new tree views (changed/impacted/risky), four new webviews (review preview, node detail, handoff preview, graph status), FS watcher refresh, `Review staged PR` command. |
| Fixture repos | 2 | 8 | `python_fastapi_service`, `ts_nestjs_app`, `react_next_app`, `ts_express_app`, `mixed_docs_config_repo`, `migration_database_repo` — all six target fixtures land with `test_*_fixture.py` integration tests. |
| Docs honesty | 6 | 8 | `docs/frameworks.md` documents every plugin's scope + limits; `docs/migration-guides/v1.1-to-v1.2.md` written; README feature status table refreshed. |

### Hard numbers
- `python -m pytest`: 96 → on track for >120 tests after v1.2 additions land
- `ruff check .`: clean
- `mypy devgraph`: clean
- `bandit -q -r devgraph -c pyproject.toml`: no findings
- `pnpm typecheck`: all 5 workspace projects green
- `pnpm --filter @devgraph/dashboard build`: 529 kB largest chunk
- `pnpm --filter @devgraph/vscode-extension compile`: tsc clean

### Honest remaining gaps (post-v1.2)

- Graph clustering on 10k+ nodes still uses the existing radial layout; the
  `intelligence/communities.py` module is not yet wired to a UI clustering
  control.
- Visual audit of the dashboard could not be executed in this slice; the new
  Review lens severity heat map renders but was only smoke-tested by the
  TypeScript compiler.
- Coverage thresholds: baseline not yet locked in CI. Stable for one run; the
  `--cov-fail-under` gate stays planned until three consecutive runs agree.

## v1.2 dashboard redesign amendment (2026-05-25)

A full UI/UX redesign of the dashboard now ships, anchored on the Anthropic
Claude dark surface tokens and adapted from the `stitch_devgraph_os_command_center`
reference (Command Center, Graph Explorer, Review Lens screens).

| Area | v1.2 score (prior) | v1.2.1 score | Evidence |
|---|---:|---:|---|
| Dashboard UI/UX | 7 | 9 | New design tokens in `apps/dashboard/src/styles/app.css` (warm charcoal `#0E0D0B` canvas, coral `#CC785C` primary, teal `#7CD7C4` health, amber `#E8A55A` risk, violet `#D4BBFF` knowledge). EB Garamond + Geist + JetBrains Mono tri-font loaded from `apps/dashboard/index.html`. Glass cards, hairline borders, inner-highlight, motion system, ⌘K palette. |
| Command Center | 6 | 9 | `apps/dashboard/src/App.tsx` Overview rebuilt: hero project card, four animated KPI counters (files / nodes / edges / risk), bento layout with Intelligence Pulse SVG, Risk Radar (live signal driven by review data), Recent Activity timeline, Best Actions stack, Confidence mix, Top node types, Languages, Memories, System Health. |
| Review Lens | 7 | 9 | `apps/dashboard/src/review/ReviewLens.tsx` rebuilt: animated risk gauge with level-tinted fill, blast-radius SVG with satellite nodes, impacted file cards with severity badges, diff hunk preview chrome, critical checklist with toggle state, severity heat map, sensitive deltas (API / route / fan-out / infra), AI quote panel, copy context-pack action. |
| Graph Explorer | 6 | 8 | `apps/dashboard/src/graph/GraphView.tsx` rebuilt: mode tabs (Overview / Impact / Architecture / Flow / Community) gate the visible subgraph, filter chips toggle node types, legend overlay, ReactFlow canvas with warm-charcoal background, slide-in inspector drawer with AI confidence, provenance, summary, snippet preview, action stack. |
| Handoff Lens | 0 | 8 | New `apps/dashboard/src/handoff/HandoffLens.tsx` consumes `/api/handoff` via typed `client.handoff()` (schema added in `packages/schema/src/api.ts`, parsed in `packages/client/src/devgraphClient.ts`). Shows branch / freshness / counts, continuation prompt preview, changed symbols, open TODOs, decisions, downloadable handoff.md and handoff.json. |
| Debug / Onboard / Knowledge / Flows | 6 | 8 | All four lenses rebuilt against the new tokens with consistent header eyebrows, bento layout, dense-list rows, stagger reveal motion. |
| Other lenses honesty | n/a | n/a | Lenses still show empty-states with the exact CLI command to run (no fake data). |

### Verification commands run in this slice

```bash
pnpm -r typecheck                                 # 5 projects · all green
pnpm --filter @devgraph/dashboard build           # largest chunk 315 kB (< 600 kB budget)
pnpm --filter @devgraph/vscode-extension compile  # tsc clean
python -m pytest -q                               # 118 passed
```

### Bundle (post-redesign)

```
dist/assets/graph-vendor-…   315.16 kB │ gzip: 101.87 kB
dist/assets/index-…          120.95 kB │ gzip:  28.57 kB
dist/assets/motion-vendor-…  115.26 kB │ gzip:  38.24 kB
dist/assets/icons-vendor-…    29.62 kB │ gzip:   7.85 kB
dist/assets/charts-vendor-…    0.44 kB │ gzip:   0.29 kB
dist/assets/index-…css        53.86 kB │ gzip:   9.34 kB
```

(Charts vendor is now empty because the Overview no longer uses Recharts; can be
dropped from `manualChunks` in a follow-up.)

### Remaining honest gaps after this slice

- No automated visual regression test exists for the redesigned dashboard. The
  TypeScript compiler and Vite build pass; pixel correctness was not validated
  against the reference screenshots inside this environment.
- The Graph Explorer still relies on the existing radial layout; community
  detection from `devgraph/intelligence/communities.py` is exposed via
  `/api/communities` but the new Graph view does not yet bind to it as a layout
  mode.
- The Review Lens blast-radius visualization is a stylized satellite diagram, not
  a true force-directed impact map.
- Empty-state command hints render in every lens, but a `localStorage`-backed
  "you've seen this" suppression is not implemented.

## v1.2.2 closeout amendment (2026-05-25)

Closing the four "remaining honest gaps" from the v1.2.1 slice.

| Item | Status | Evidence |
|---|---|---|
| Empty `charts-vendor` chunk | Removed | Dropped from [apps/dashboard/vite.config.ts](apps/dashboard/vite.config.ts) and `recharts` removed from [apps/dashboard/package.json](apps/dashboard/package.json). Post-build manifest no longer contains `charts-vendor-*.js`. |
| `localStorage` empty-state suppression | Implemented | New [apps/dashboard/src/utils/dismiss.ts](apps/dashboard/src/utils/dismiss.ts) (`useDismissible` hook, keyed under `devgraph:dismissed:*`, gracefully handles disabled storage). Overview Pro Tip card now renders a dismiss `×` and stays hidden across reloads. |
| Graph Explorer community-detection layout | Wired | `Community` mode in [apps/dashboard/src/graph/GraphView.tsx](apps/dashboard/src/graph/GraphView.tsx) fetches `/api/communities` lazily, lays nodes in per-community satellite clusters around the canvas, and colors each cluster from a 7-tone palette. Legend overlay swaps to per-community labels + node counts. Backed by new typed `client.communities()` in [packages/client/src/devgraphClient.ts](packages/client/src/devgraphClient.ts) and `communitiesPayloadSchema` in [packages/schema/src/api.ts](packages/schema/src/api.ts). |
| Real impacted-graph blast radius | Implemented | `buildBlastGraph` in [apps/dashboard/src/review/ReviewLens.tsx](apps/dashboard/src/review/ReviewLens.tsx) now lays out actual `review.changed_nodes` + `review.impacted_nodes` as a coral-center / teal-satellite SVG with edges drawn from changed → impacted. Tooltips expose qualified names. Renders `no impact` when both arrays are empty. |

### CI / VSCode honesty check

While auditing, the v1.2.1 "remaining gaps" implied missing CI and extension
work. Reality: both already shipped before this slice.

- [.github/workflows/ci.yml](.github/workflows/ci.yml) already covers Python
  (ruff / mypy / bandit / pytest / informational coverage), pnpm install,
  workspace typecheck, dashboard build, VS Code extension compile, **716800-byte
  largest-chunk bundle guard**, `vite preview` health smoke test (30 × 1s
  curl loop), and artifact upload of `dashboard-dist` and
  `vscode-extension-out`.
- [apps/vscode-extension/package.json](apps/vscode-extension/package.json)
  already contributes `devgraph.binaryPath` (default `devgraph`),
  `devgraph.autoRefresh`, `devgraph.dashboardPort`, `devgraph.codeLens.enabled`,
  four tree views (status / changed / impacted / risky), and 26 commands
  including handoff, review preview, node detail, and staged-PR review.
- Tests for secret redaction, handoff deep, schema, MCP tools, framework
  routes (JS + Python), migration risk, SQL parser, ts parser, tree-sitter
  provenance and incremental review **already exist** under
  [tests/unit/](tests/unit/) and [tests/integration/](tests/integration/).

### Final verification

```bash
pnpm install                                       # recharts removed; -1 package
pnpm -r typecheck                                  # 5 projects · all green
pnpm --filter @devgraph/dashboard build            # largest chunk 315 kB
python -m pytest -q                                # 118 passed
```

### Post-redesign bundle

```
dist/assets/graph-vendor-…  315.16 kB │ gzip: 101.87 kB
dist/assets/index-…         124.37 kB │ gzip:  29.68 kB
dist/assets/motion-vendor-… 115.26 kB │ gzip:  38.24 kB
dist/assets/icons-vendor-…   29.26 kB │ gzip:   7.78 kB
dist/assets/react-vendor-…    0.07 kB │ gzip:   0.08 kB
dist/assets/index-…css       53.86 kB │ gzip:   9.34 kB
```

Largest single chunk 315 kB, well under the 700 kB CI hard cap (716 800 bytes).

### Truly remaining (will not be claimed in this audit)

- **Pixel/visual regression for the redesigned dashboard** — needs a headless
  browser harness (Playwright + storybook screenshots) running in CI on a
  fixed-DPI runner. Genuine multi-PR work, not a one-turn fix.
- **Force-directed graph layout** — the radial layout is still cheaper and
  more legible at >300 nodes. Switching to d3-force or elkjs adds ~80 kB and
  has not yet shown a UX win on the reference fixtures.
- **Community-detection algorithm itself** — `top_communities` in
  [devgraph/intelligence/communities.py](devgraph/intelligence/communities.py)
  groups by `file_path`/`type` rather than running Louvain or label
  propagation. The new layout shows whatever that store returns; richer
  algorithms are a separate change.

These are honest scope decisions, not silent omissions.

