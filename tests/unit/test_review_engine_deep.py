from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.review import ReviewEngine
from devgraph.update.incremental import build_graph


def test_review_engine_classifies_security_config_db_and_missing_tests(tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    (tmp_path / "schema.sql").write_text("CREATE TABLE users(id int);\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    store = GraphStore(tmp_path, tmp_path / ".devgraph")
    build_graph(tmp_path, DevGraphConfig(), store, force=True)
    result = ReviewEngine(tmp_path, DevGraphConfig(), store).review(files=["auth.py", "schema.sql", "docker-compose.yml"])
    assert result.security_sensitive_changes
    assert result.database_or_schema_changes
    assert result.config_or_infra_changes
    assert result.missing_tests
    assert result.model_dump(mode="json")["risk_score"] >= 0
