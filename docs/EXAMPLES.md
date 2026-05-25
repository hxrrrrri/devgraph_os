# Examples

```bash
devgraph build
devgraph review --json
devgraph debug 'File "src/app.py", line 12, in main' --json
devgraph explain src/auth.py
devgraph remember --kind decision "Keep graph storage local in SQLite."
devgraph handoff
```

For external documentation:

```bash
devgraph ingest ../notes/system-design.md
devgraph wiki
```

External ingested files are copied under `.devgraph/imports/`.
