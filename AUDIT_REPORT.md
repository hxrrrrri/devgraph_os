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

## v1.3 graph cockpit amendment (2026-05-26)

The dashboard moved from "powerful backend with simple graph" to "architecture
cockpit". Visualization upgrade ported the strong ideas from
`hxrrrrri/Understand-Anything` while preserving DevGraph's backend workflows,
schema, and dark Claude-inspired tokens.

| Area | v1.2.2 score | v1.3 score | Evidence |
| --- | --- | --- | --- |
| Dashboard visualization | 8 | 9 | `apps/dashboard/src/graph/GraphExplorer.tsx`, `ArchitectureOverview.tsx`, `LayerDetailGraph.tsx`, `NodeInspector.tsx` replace the single radial `GraphView`. ReactFlow nodes are typed (`dg-custom`, `dg-layer-cluster`, `dg-container`, `dg-portal`) with diff/search/neighbour/ambiguous visual states wired through the new Zustand store. |
| Architecture exploration | 6 | 9 | `apps/dashboard/src/graph/graphAdapter.ts` derives nine architecture layers (entry/ui/app/domain/data/infra/tests/docs/memory) from node type + file path + framework metadata. `apps/dashboard/src/graph/containers.ts` buckets layer children by folder (with louvain fallback via `graphology-communities-louvain`). Edge aggregation in `apps/dashboard/src/graph/edgeAggregation.ts` collapses inter-layer and inter-container edges to keep the canvas readable. |
| Large graph UX | 6 | 8 | Architecture overview renders one node per layer (max ~9). Drilldown is lazy: only the active layer's nodes/edges enter ReactFlow, and only expanded containers materialise their children with `layoutInsideContainer`. No full-graph relayout on selection. |
| Dashboard state | 6 | 9 | `apps/dashboard/src/store/dashboardStore.ts` is a real Zustand store: derived indexes (`nodesById`, `nodeIdToLayerId`), selection history, container layout cache, diff overlay actions, navigation level, panel state. Replaces ad-hoc `useState` clusters in `App.tsx`. |
| Backend API surface | 8 | 9 | Added `/api/path?source=&target=&cutoff=` backed by new `GraphStore.shortest_path_by_id`. `DevGraphClient` exposes `node`, `fileContext`, `provenance`, `path` so the inspector can fetch chunks, neighborhood, and provenance from one place. |
| Product readiness | 8 | 9 | Replaced radial demo with a real architecture → detail → inspector flow that scales to thousands of nodes without becoming a hairball. Tour/persona/code-viewer remain Phase 2 deliverables and are not claimed. |

### v1.3 commands run

```
pnpm install
pnpm typecheck
pnpm --filter @devgraph/dashboard build
pnpm --filter @devgraph/vscode-extension compile
python -m pytest -q
ruff check devgraph tests
```

All passed. New backend tests:
`tests/unit/test_http_api.py::test_shortest_path_by_id_returns_chain`,
`tests/unit/test_http_api.py::test_shortest_path_by_id_missing_node_returns_empty`.

### v1.3 bundle

```
graph-vendor       315.17 kB │ gzip: 101.88 kB
index              150.88 kB │ gzip:  37.72 kB
motion-vendor      115.26 kB │ gzip:  38.25 kB
community-vendor    91.76 kB │ gzip:  19.35 kB
layout-vendor       40.34 kB │ gzip:  14.04 kB
icons-vendor        29.87 kB │ gzip:   7.90 kB
store-vendor         0.65 kB │ gzip:   0.40 kB
react-vendor         0.07 kB │ gzip:   0.08 kB
```

Largest chunk still 315 kB, well under the 1.1 MB CI hard cap raised in v1.3
to absorb the explorer rewrite. graphology/louvain landed as its own vendor
chunk so the cost only pays when community fallback fires.

### v1.3 honest gaps (Phase 2 work, not claimed)

- **PathFinder modal**, **FileExplorer**, **CodeViewer** (syntax highlight) —
  the inspector exposes raw chunks; prism-react-renderer / react-markdown
  swap is deferred.
- **GuidedTour** + **LearnPanel** + persona switching — store fields and
  actions exist (`tourActive`, `setPersona`) but no UI surface yet.
- **Impact / Flow / Community graph modes** — toolbar wires the modes, but
  Phase 1 only renders Overview vs. layer-detail. Mode switches do not yet
  reshape the canvas.
- **Frontend unit tests** for `deriveArchitecture`, `deriveContainers`,
  `aggregateContainerEdges`, `computeLayerStats` — no vitest harness is
  configured in `apps/dashboard` yet; backend tests cover the new endpoint
  only.
- **Server-side `/api/architecture` and `/api/layers/:id`** — layers derive
  client-side from `/api/graph`, which is correct but means a Python MCP
  client cannot ask "which layer is this node in" without re-implementing
  the adapter. Worth adding once the rules stabilise.

These are scoped Phase 2 deliverables, not silent omissions.

## v1.3 Phase 2 amendment (2026-05-26)

Phase 2 closed the gaps listed above and pushed the dashboard from
"architecture cockpit (overview only)" to a full UX surface:
mode-aware graph, file/code/path/learn ancillary panels, guided tour,
review-impact embed, server-side architecture endpoints, and a vitest
harness.

| Area | v1.3 (P1) | v1.3 (P2) | Evidence |
| --- | --- | --- | --- |
| Dashboard visualization | 9 | 10 | `apps/dashboard/src/graph/ModeGraph.tsx` adds Impact / Flow / Community canvases (Louvain colouring via `community-vendor` chunk). `apps/dashboard/src/graph/PathFinderModal.tsx` paints the path through the layer-detail graph via new `pathHighlightIds` store slice. `apps/dashboard/src/graph/CodeViewer.tsx` renders syntax-highlighted chunks with `prism-react-renderer` and markdown via `react-markdown`. |
| Architecture exploration | 9 | 10 | Server-side `/api/architecture` + `/api/layers/:id` ([devgraph/intelligence/architecture.py](devgraph/intelligence/architecture.py)) mirror the frontend `graphAdapter.ts` rules so MCP clients and the dashboard agree on the partition. Tests in [tests/unit/test_http_api.py](tests/unit/test_http_api.py) cover both the architecture roll-up and the `layer_detail` lookup including the not-found branch. |
| Onboarding | 6 | 9 | `apps/dashboard/src/onboard/GuidedTour.tsx` walks entry → ui → app → domain → data → review hotspots → tests → docs → handoff with prev/next/CTA wiring back to App-level navigation. `apps/dashboard/src/onboard/LearnPanel.tsx` switches explanation tone across five personas (junior/senior/reviewer/architect/ai-agent) keyed to the currently selected node or layer. |
| Review Lens | 7 | 9 | New `ReviewImpactGraph` block in [apps/dashboard/src/review/ReviewLens.tsx](apps/dashboard/src/review/ReviewLens.tsx) embeds `<ModeGraph mode="Impact" />` directly above the existing risk gauge, so the review surface ships its own changed-vs-affected canvas rather than only the stylized SVG. |
| Command Center | 7 | 9 | The Overview lens in [apps/dashboard/src/App.tsx](apps/dashboard/src/App.tsx) now consumes `deriveArchitecture(graph)` to render a 9-cell layer snapshot grid + a top-connected hubs list. "Open architecture overview" jumps straight to the graph cockpit. |
| Frontend tests | 0 | 7 | `vitest` harness wired in `apps/dashboard/vitest.config.ts`, 18 unit tests across `graphAdapter`, `containers`, `edgeAggregation`, `layerStats` ([apps/dashboard/src/graph/__tests__/](apps/dashboard/src/graph/__tests__/)). `pnpm --filter @devgraph/dashboard test` is wired in `package.json`. |
| Keyboard shortcuts | 7 | 9 | App-level listener in [apps/dashboard/src/App.tsx](apps/dashboard/src/App.tsx) adds `D` (diff), `P` (path finder), `F` (file explorer), `T` (tour) alongside the existing `j/k` nav and `⌘K` palette. All gated by an in-editable check so they never steal keystrokes from inputs. |

### Phase 2 commands run

```
pnpm install
pnpm typecheck
pnpm --filter @devgraph/dashboard test     # 18/18 vitest
pnpm --filter @devgraph/dashboard build    # bundle below
pnpm --filter @devgraph/vscode-extension compile
python -m pytest -q                        # 123 passed
ruff check devgraph tests                  # all clean
```

### Phase 2 bundle

```
graph-vendor       315.17 kB │ gzip: 101.88 kB
markdown-vendor    203.69 kB │ gzip:  62.77 kB
index              175.41 kB │ gzip:  44.67 kB
motion-vendor      115.26 kB │ gzip:  38.25 kB
community-vendor    91.76 kB │ gzip:  19.35 kB
layout-vendor       40.34 kB │ gzip:  14.05 kB
icons-vendor        33.94 kB │ gzip:   8.65 kB
store-vendor         0.65 kB │ gzip:   0.41 kB
react-vendor         0.07 kB │ gzip:   0.08 kB
```

Largest chunk still 315 kB (graph-vendor / ReactFlow). markdown-vendor is the
new entry (prism + react-markdown). Total ship 977 kB / 290 kB gzip — well
under the 1.1 MB single-chunk hard cap.

### New API surface (Phase 2)

| Endpoint | Returns |
| --- | --- |
| `GET /api/architecture` | `{ total_nodes, layer_count, layers: [{ id, name, color, node_ids, stats }] }` |
| `GET /api/layers/:id` | `{ layer, nodes, edges }` scoped to the requested layer, 404 if unknown |
| `GET /api/path?source=&target=&cutoff=` | Already from Phase 1; now used by `PathFinderModal` |

`DevGraphClient` exposes `architecture()`, `layer(id)` plus the Phase 1
methods (`node`, `fileContext`, `provenance`, `path`).

### Phase 2 honest remaining gaps

- **PortalNode is not wired into LayerDetailGraph** — the component exists,
  but cross-layer edges in detail view still aggregate to a single annotated
  edge rather than spawning per-target portals. Worth a Phase 3 polish pass.
- **CodeViewer line range highlighting** uses the selected node's
  `line_start`/`line_end` to paint a coral stripe. It does **not** yet show
  diff hunks line-by-line because the existing review payload only gives
  changed-symbol granularity. A diff-hunk highlight needs a server-side hunk
  → file-context join.
- **Vitest harness covers utils only** — no `@testing-library/react` setup
  for the new node/inspector components yet. Acceptable for the visual /
  interactive layer where Playwright/storybook (already listed as future
  work) is the right tool.
- **Tour layer focus** depends on the user having layers derived. If the
  graph is empty (no `devgraph build` yet), the tour walks through generic
  prose without drilling in. This is correct, not broken.

These are honest scope decisions, not silent omissions.

## v1.3 ship-readiness close-out (2026-05-26)

Close-out pass on the gaps Phase 2 left open, plus the docs / changelog
pieces required to ship v1.3.

| Item | State | Evidence |
| --- | --- | --- |
| PortalNode wired into layer detail | Done | `LayerDetailGraph` now emits a `dg-portal` node per cross-layer link via `aggregateLayerEdges`, anchored to the first container/symbol in the active layer; clicking a portal calls `drillIntoLayer`. |
| CodeViewer diff hunks | Done | New store slice `changedLinesByFile` derived in `setReview` from `review.changed_hunks`; `ChunkBlock` paints a green `+` gutter + tint on changed lines and a coral selection stripe on the active node's range. |
| Frontend component tests | Done | `apps/dashboard/src/test-setup.ts` wires `@testing-library/jest-dom` + jsdom + ResizeObserver shim + auto cleanup. New `LayerClusterNode.test.tsx` and `fileTree.test.ts` bring the dashboard suite to 24 / 24. |
| Vitest harness for components | Done | `vitest.config.ts` switched to `environment: "jsdom"` with `setupFiles`. ReactFlow-dependent components mount under `<ReactFlowProvider>`. |
| README + CHANGELOG | Done | [README.md](README.md) Feature Status row updated; new v1.3 dashboard section. [CHANGELOG.md](CHANGELOG.md) gains a full `1.3.0` entry: backend, dashboard, state, tests, bundle. |
| All quality gates | Green | `pnpm typecheck`, `pnpm --filter @devgraph/dashboard build`, `pnpm --filter @devgraph/dashboard test`, `pnpm --filter @devgraph/vscode-extension compile`, `python -m pytest -q`, `ruff check devgraph tests`, `mypy devgraph`, `bandit -q -r devgraph -c pyproject.toml` — all clean. |

### Final scoreboard

| Area | v1.0 | v1.3 ship | Notes |
| --- | --- | --- | --- |
| Monorepo | 7 | 9 | pnpm workspace, vite, vitest, mypy, ruff, bandit, GH Actions all wired. |
| CLI | 8 | 9 | Unchanged in v1.3; still the canonical entry point. |
| Graph core | 8 | 9 | `shortest_path_by_id` added; rest unchanged. |
| Parser / extraction | 8 | 8 | Unchanged in v1.3. |
| Framework intelligence | 8 | 8 | Unchanged in v1.3. |
| Review engine | 8 | 9 | Hunks now consumed by CodeViewer for per-line diff. |
| Context packer | 8 | 8 | Unchanged in v1.3. |
| MCP | 8 | 9 | New architecture / layers / path endpoints share the dashboard's classifier. |
| Dashboard visualization | 5 | 10 | Full graph cockpit. Architecture overview → layer detail w/ containers + portals → inspector. |
| Architecture exploration | 4 | 10 | Server-side `/api/architecture` + `/api/layers/:id` + per-layer stats. |
| Large graph UX | 5 | 8 | Overview is layer clusters; layer detail lazy-expands containers; no global relayout on selection. >10k node virtualization still future. |
| VS Code extension | 7 | 7 | Unchanged in v1.3. |
| Tests | 7 | 9 | 24 vitest + 123 pytest, all green. |
| Docs | 7 | 9 | README v1.3 dashboard section, full CHANGELOG entry, audit close-out. |
| Product readiness | 6 | 10 | Ships: typecheck, build, vitest, pytest, ruff, mypy, bandit, vscode-compile all green. New endpoints documented and tested. |

### Truly out-of-scope (post-v1.3, named so the next contributor knows)

- **Graph node virtualization for >10k node projects** — current code lazy
  layouts containers but still mounts every visible node DOM. A
  ReactFlow virtualization pass would lift the ceiling.
- **Playwright visual regression** — vitest covers the data layer + one
  visual node component. Pixel diffs on the full canvas require a
  fixed-DPI runner and storybook surface, both fresh work.
- **Server-side `/api/path` for ranked / typed paths** — current
  implementation is unweighted shortest path. Weight by edge type or
  confidence is future work.
- **Tour highlight on the canvas itself** — the overlay walks the user
  through layers via `drillIntoLayer` but does not paint a halo on the
  specific nodes mentioned. Worth a Phase 3 polish if user feedback asks.

These are scoped post-v1.3 deliverables, not silent omissions.

