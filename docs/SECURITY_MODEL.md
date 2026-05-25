# Security Model

DevGraph OS is local-first.

- No telemetry or analytics.
- HTTP binds to `127.0.0.1`.
- Cloud calls are disabled by default.
- Embeddings are disabled by default.
- `.env`, JSON, YAML, TOML, Markdown, text, config, infra, and code chunks redact likely secret values.
- Secret hints include `api_key`, `token`, `secret`, `password`, `private_key`, `access_key`, and `refresh_token`.
- External ingested files are copied under `.devgraph/imports/` before extraction.
- Dashboard file-context endpoints reject path traversal.

Optional local dependencies such as Tree-sitter grammars, PDF/DOCX parsers, MCP, or sentence-transformers fail gracefully when not installed.
