from pathlib import Path

import pytest

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.extractors.registry import ExtractorRegistry
from devgraph.retrieval.search import search_graph
from devgraph.update.incremental import build_graph


def test_tree_sitter_semantic_extraction_for_typescript(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_language_pack")
    path = tmp_path / "server.ts"
    path.write_text(
        "import { validateUser } from './service';\n"
        "export async function login(user: User): Promise<boolean> {\n"
        "  return validateUser(user);\n"
        "}\n",
        encoding="utf-8",
    )

    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)

    login = next(node for node in result.nodes if node.name == "login")
    assert login.metadata["parser"] == "tree-sitter"
    assert login.metadata["parameters"] == "(user: User)"
    assert "Promise<boolean>" in login.metadata["return_type"]
    assert any(edge.type == "imports" and edge.provenance_source == "tree-sitter" for edge in result.edges)


def test_local_embeddings_are_indexed_and_used_for_search(tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text(
        "def login_user(username: str) -> bool:\n"
        "    return username == 'admin'\n",
        encoding="utf-8",
    )
    config = DevGraphConfig()
    config.retrieval.embeddings_enabled = True
    config.retrieval.embedding_provider = "local-hash"
    config.retrieval.embedding_dimensions = 256
    config.retrieval.embedding_model = "devgraph-local-hash-v1"
    store = GraphStore(tmp_path, tmp_path / ".devgraph")

    stats = build_graph(tmp_path, config, store, force=True)
    payload = search_graph(store, "login user authentication", limit=5, config=config)

    assert stats.embeddings_indexed > 0
    assert store.connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] > 0
    assert payload["semantic"]
    assert any(item.get("file_path") == "auth.py" for item in payload["semantic"])


def test_local_import_resolver_links_relative_modules(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_language_pack")
    (tmp_path / "index.ts").write_text(
        "import { validateUser } from './service';\n"
        "export function login(user: string) { return validateUser(user); }\n",
        encoding="utf-8",
    )
    (tmp_path / "service.ts").write_text(
        "export function validateUser(user: string) { return Boolean(user); }\n",
        encoding="utf-8",
    )
    config = DevGraphConfig()
    store = GraphStore(tmp_path, tmp_path / ".devgraph")

    build_graph(tmp_path, config, store, force=True)

    rows = store.connection.execute(
        """
        SELECT target.qualified_name
        FROM edges e
        JOIN nodes target ON target.id = e.target_id
        WHERE e.provenance_source = 'local-import-resolver'
        """
    ).fetchall()
    assert any(row["qualified_name"] == "service.ts" for row in rows)
