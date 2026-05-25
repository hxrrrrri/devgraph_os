from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_sql_parser_extracts_database_tables(tmp_path: Path) -> None:
    path = tmp_path / "schema.sql"
    path.write_text("CREATE TABLE users(id int);\nSELECT * FROM users;\n", encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    assert any(node.type == "database_table" and node.name == "users" for node in result.nodes)
    assert any(edge.type in {"reads_from", "writes_to"} for edge in result.edges)
