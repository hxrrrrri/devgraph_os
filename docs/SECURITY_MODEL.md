# Security Model

DevGraph OS defaults to local-only processing.

- No telemetry.
- No analytics.
- No cloud calls by default.
- Local SQLite storage under `.devgraph/`.
- `.env` values are redacted and only variable names are stored.
- Likely secret values in docs/config chunks are redacted.
- LLM enrichment is opt-in through `devgraph.toml`.
- `devgraph doctor` reports privacy-sensitive settings.

Before any future external model integration sends code or docs outside the machine, the integration must display a clear warning and require explicit user action.

