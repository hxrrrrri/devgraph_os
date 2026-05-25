# Graph Schema

Core tables are `files`, `nodes`, `edges`, `chunks`, `provenance`, `changes`, `memories`, `sessions`, `snapshots`, and optional `embeddings`.

Important node types include `file`, `module`, `class`, `function`, `test`, `api_endpoint`, `database_table`, `schema`, `config`, `resource`, `document`, `section`, `flow`, and `decision`.

Important edge types include `contains`, `imports`, `calls`, `inherits`, `implements`, `tested_by`, `depends_on`, `reads_from`, `writes_to`, `routes_to`, `documents`, and `affects`.

Every parser fact carries `confidence_tier`: `extracted`, `inferred`, `ambiguous`, `llm`, or `user`.

Chunks include `file_path`, optional `node_id`, `kind`, line range, token estimate, hash, metadata, and provenance.
