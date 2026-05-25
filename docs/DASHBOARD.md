# Dashboard

The dashboard is served locally by `devgraph dashboard` on `127.0.0.1`.

It consumes real local API data from `/api/status`, `/api/graph`, `/api/review`, `/api/debug`, `/api/onboarding`, `/api/handoff`, `/api/communities`, `/api/flows`, `/api/memories`, `/api/snapshots`, and provenance/file-context endpoints.

## Lenses

- Command Center: graph KPIs, risk score, language/type/confidence charts, hotspots, memories, and health.
- Graph Explorer: interactive node/edge graph with type filters, minimap, animated flow edges, and node detail drawer.
- Review Lens: changed symbols, hunks, risk gauge, impacted files, missing tests, and copyable context pack.
- Debug Lens: stack trace input, parsed frames, suspected nodes, configs/tests, and debugging order.
- Onboarding Lens: read-first files, architecture steps, and top flow hints.
- Knowledge Lens: docs/config coverage and stale-doc candidates.
- Flow Lens: calls, routes, database references, dependencies, and data-flow style edges.

No static fake product data is rendered. Empty states reflect missing or stale graph data.
