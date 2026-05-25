# Architecture

DevGraph OS is a local-first developer intelligence layer. The first implementation is intentionally modular:

1. Extractors detect and parse files into canonical nodes, edges, chunks, and provenance.
2. The graph store persists data in SQLite with WAL mode and FTS5 indexes.
3. Retrieval and intelligence modules build review, debug, explain, onboarding, and handoff context.
4. Interfaces expose the same engine through CLI, MCP, HTTP, dashboard, VS Code, and slash-command instructions.

The product boundary is the canonical graph schema. Parser facts are marked `extracted`; indirect deterministic relations are `inferred`; model-generated data must be `llm`; uncertain facts are `ambiguous`; manually approved facts are `user`.

## Storage

Default storage:

```txt
.devgraph/
  graph.db
  embeddings.db
  cache/
  snapshots/
  reports/
  wiki/
  sessions/
  exports/
```

Neo4j is not required. It is available only as an export format.

