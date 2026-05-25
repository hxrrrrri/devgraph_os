# VS Code Extension

The extension lives in `apps/vscode-extension`.

It contributes:

- DevGraph: Initialize Project
- DevGraph: Build Graph
- DevGraph: Update Graph
- DevGraph: Review Current Changes
- DevGraph: Explain Current File
- DevGraph: Explain Symbol
- DevGraph: Ask About Project
- DevGraph: Open Dashboard
- DevGraph: Generate Handoff

The extension calls the local `devgraph` CLI with child processes. This keeps v1 simple and avoids a second backend. The sidebar displays graph status from `devgraph status --json`.

