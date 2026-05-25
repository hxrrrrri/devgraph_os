# Context Engine

Context packs are task-specific and deterministic.

Supported task types are `review`, `debug`, `explain`, `ask`, `onboard`, `refactor`, and `handoff`.

The packer ranks by exact symbol match, local FTS/semantic matches when available, graph neighborhood, confidence, provenance, changed-file seeds, tests, docs/config relevance, and token budget.

User-facing graph paths use readable qualified names:

```text
src/auth.py::AuthService.login --calls--> src/db.py::Database.connect
```

Internal IDs are not shown in the graph path section. Source excerpts come from focused chunks with file path and line ranges.
