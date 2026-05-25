from devgraph.core.schema import Node
from devgraph.retrieval.chunking import chunk_code, chunk_config, chunk_markdown, chunk_sql


def test_code_chunking_uses_symbol_ranges() -> None:
    text = "def login():\n    return True\n\ndef logout():\n    return False\n"
    node = Node(
        id="function:login",
        type="function",
        name="login",
        qualified_name="auth.login",
        file_path="auth.py",
        line_start=1,
        line_end=2,
    )
    chunks = chunk_code("auth.py", text, [node])
    assert chunks[0].node_id == node.id
    assert chunks[0].line_start == 1
    assert "logout" not in chunks[0].content


def test_markdown_and_config_and_sql_chunks_are_focused_and_redacted() -> None:
    markdown = "# A\none\n## B\ntwo\n"
    section = Node(id="section:b", type="section", name="B", qualified_name="README.md#B", file_path="README.md", line_start=3)
    assert chunk_markdown("README.md", markdown, [section])[0].line_start == 3
    config = chunk_config("app.yaml", "api_key: secret\nserver:\n  port: 1\n")
    assert "secret" not in config[0].content
    sql = chunk_sql("schema.sql", "CREATE TABLE users(id int);\nSELECT * FROM users;\n")
    assert len(sql) == 2
