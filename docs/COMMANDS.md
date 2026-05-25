# Commands

```bash
devgraph init
devgraph build
devgraph update
devgraph watch
devgraph status
devgraph status --json
devgraph doctor
devgraph doctor --json
devgraph ask "How does authentication work?"
devgraph search "login user authentication"
devgraph search "login user authentication" --json
devgraph embed --local-hash
devgraph explain src/auth/login.ts
devgraph path AuthService DatabasePool
devgraph trace AuthService.login
devgraph review
devgraph review --base origin/main
devgraph review --staged
devgraph review --json
devgraph review --files src/auth.py src/server.ts
devgraph debug "paste stack trace or bug description here"
devgraph debug "paste stack trace or bug description here" --json
devgraph onboard
devgraph dashboard
devgraph wiki
devgraph ingest ./docs
devgraph ingest ./paper.pdf
devgraph ingest ./README.md
devgraph remember --kind decision "We use SQLite as the local graph store."
devgraph memories
devgraph memories --json
devgraph forget memory:<id>
devgraph handoff
devgraph export --format graphml
devgraph export --format obsidian
devgraph export --format json
devgraph export --format neo4j
devgraph serve
devgraph mcp
```

`build` indexes all supported files, records parser provenance, emits focused chunks, refreshes inferred test/import links, and writes a latest local snapshot. `update` uses git status or diff data, records changed files in SQLite, reparses changed files, marks deleted files, and refreshes inferred relationships.

`review` writes Markdown and JSON reports under `.devgraph/reports/`. Use `--files` to force a review scope even when there is no git diff; DevGraph will fall back to source excerpts for those files.

`remember` stores user-approved local memories in SQLite. Secret-looking `key=value` or `key: value` lines are redacted before storage.

`embed` is explicit. Embeddings are disabled by default. `--local-hash` uses DevGraph's deterministic dependency-free local vectorizer; `sentence-transformers` can be configured for a local model when the optional embeddings extra is installed.

`search` always uses SQLite FTS and exact symbol matching. It adds semantic matches only when embeddings are enabled and indexed.
