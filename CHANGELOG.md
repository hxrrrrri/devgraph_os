# Changelog

## 1.3.0 — Graph cockpit (2026-05-26)

### Backend

- New endpoints: `/api/architecture` (full layer partition), `/api/layers/:id`
  (nodes + edges scoped to a layer), `/api/path?source=&target=&cutoff=`
  (shortest path between two node ids).
- New module `devgraph/intelligence/architecture.py` mirrors the dashboard's
  layer classifier (entry / ui / app / domain / data / infra / tests / docs /
  memory) so MCP clients and the dashboard agree on the partition.
- New store method `GraphStore.shortest_path_by_id` (id-based variant of the
  existing query-string `find_path`).

### Dashboard

- Replaced the single radial `GraphView` with a full graph cockpit:
  `ArchitectureOverview` → `LayerDetailGraph` with containers + portals →
  `NodeInspector` sidebar (5 tabs).
- Added mode-aware canvases: `ModeGraph` renders Impact, Flow, and Community
  views with Louvain colouring (`graphology-communities-louvain`).
- Added `PathFinderModal` with on-canvas path highlighting.
- Added `FileExplorer` panel (directory tree, change/risk badges).
- Added `CodeViewer` modal with prism syntax highlight, markdown rendering
  for docs, and per-line diff hunk highlighting from `review.changed_hunks`.
- Added `GuidedTour` (9-step walkthrough) and `LearnPanel` with five
  personas (junior / senior / reviewer / architect / ai-agent).
- Review Lens embeds `<ModeGraph mode="Impact" />` above the existing risk
  gauge.
- Command Center renders a 9-cell architecture snapshot + top-connected
  hubs derived from `deriveArchitecture(graph)`.
- New keyboard shortcuts: `D` (diff), `P` (path), `F` (files), `T` (tour),
  on top of existing `⌘K`, `j`, `k`.

### State / data

- New Zustand store `apps/dashboard/src/store/dashboardStore.ts` replaces
  the ad-hoc `useState` clusters that previously lived inside `App.tsx`.
- New `apps/dashboard/src/graph/graphAdapter.ts` derives architecture
  layers, degree stats, top-connected hubs.

### Tests

- 24 vitest unit + component tests in `apps/dashboard/src/graph/__tests__/`.
- 4 new backend tests in `tests/unit/test_http_api.py` cover the new
  endpoints and the architecture roll-up.

### Bundle

Largest chunk 315 kB (ReactFlow). Total ship 977 kB / 290 kB gzip, under
the 1.1 MB single-chunk hard cap.

## 0.1.0

- Initial monorepo scaffold.
- Python CLI, SQLite graph store, deterministic extractors, review/context/handoff engines.
- MCP server tool surface.
- Dashboard and VS Code extension shells.
