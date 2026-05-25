# Commands

```bash
devgraph init
devgraph build
devgraph update
devgraph watch
devgraph status
devgraph ask "How does authentication work?"
devgraph explain src/auth/login.ts
devgraph path AuthService DatabasePool
devgraph trace AuthService.login
devgraph review
devgraph review --base origin/main
devgraph review --staged
devgraph debug "paste stack trace or bug description here"
devgraph onboard
devgraph dashboard
devgraph wiki
devgraph ingest ./docs
devgraph ingest ./paper.pdf
devgraph ingest ./README.md
devgraph handoff
devgraph export --format graphml
devgraph export --format obsidian
devgraph export --format json
devgraph serve
devgraph mcp
devgraph doctor
```

`build` indexes all supported files. `update` uses git status or diff data and reparses changed files. `review` writes Markdown and JSON reports under `.devgraph/reports/`.

