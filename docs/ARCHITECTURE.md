# Architecture

DevGraph OS has four layers.

1. Extractors parse code, docs, configs, infra, SQL, and imported documents into nodes, edges, chunks, confidence tiers, and provenance.
2. The SQLite graph store persists files, nodes, edges, chunks, FTS indexes, changes, memories, sessions, snapshots, provenance, and optional embeddings.
3. Intelligence modules provide review, debug, explain, onboarding, handoff, flows, communities, ranking, and context packing.
4. Interfaces expose the engine through CLI, MCP, HTTP/dashboard, VS Code, exports, and wiki generation.

Tree-sitter is optional. Python uses standard-library AST. If a grammar is unavailable or extraction is uncertain, facts are conservative and marked `ambiguous` or `inferred`.
