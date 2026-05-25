# MCP

Start the MCP server:

```bash
devgraph mcp
```

Tools:

| Tool | Purpose |
| --- | --- |
| `build_or_update_graph` | Build or incrementally update the project graph |
| `get_project_status` | Return graph health, freshness, node counts, and warnings |
| `doctor` | Return local configuration and privacy diagnostics |
| `get_context` | Universal context router for review/debug/explain/ask/onboard |
| `review_changes` | Risk-scored code review context |
| `debug_issue` | Debug context from error, stack trace, or symptom |
| `explain` | Explain a file, function, class, module, concept, or flow |
| `query_graph` | Query graph by symbol, file, relation, or pattern |
| `find_path` | Find relationship path between two graph nodes |
| `trace_flow` | Trace execution or domain flow |
| `search` | Keyword/FTS search, with a semantic-search boundary for future local embeddings |
| `generate_onboarding` | Create guided project tour |
| `handoff_session` | Export session handoff context |
| `remember` | Store a user-approved local project memory |
| `list_memories` | List local project memories |
| `forget_memory` | Delete a local project memory |

The MCP layer uses the same local SQLite store as the CLI.

All tool results are JSON-safe dictionaries and lists. Context-pack tools return Markdown in a `context_pack` field so agent clients can pass it directly into a coding model.
