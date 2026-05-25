# Security Policy

DevGraph OS is local-first and does not send code, docs, graph data, or usage data to external services by default.

## Supported Versions

Security fixes target the latest minor release.

## Reporting a Vulnerability

Open a private security advisory on GitHub or email the maintainers listed in the project metadata. Include reproduction steps, affected versions, and impact.

## Security Model

- Local SQLite storage under `.devgraph/`.
- WAL mode for concurrent local reads.
- `.env` values are not stored by default.
- Likely secrets are redacted before chunk, memory, context, and export storage.
- Embeddings are disabled by default. `devgraph embed --local-hash` is local and deterministic.
- LLM enrichment is opt-in and must show a clear warning before external calls.
- The HTTP dashboard server binds only to `127.0.0.1`.
- File-context APIs reject path traversal.
- External ingested files are copied under `.devgraph/imports/`.
- No telemetry or analytics are allowed in default builds.
