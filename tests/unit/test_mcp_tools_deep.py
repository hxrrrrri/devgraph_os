from pathlib import Path

from devgraph.config import ensure_project
from devgraph.server.mcp_server import DevGraphMcpTools


def test_mcp_deep_tools_return_json_safe_payloads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    ensure_project(tmp_path)
    (tmp_path / "app.py").write_text("def main():\n    return True\n", encoding="utf-8")
    tools = DevGraphMcpTools(tmp_path)
    tools.build_or_update_graph(incremental=False)
    node = tools.query_graph("main")["nodes"][0]
    assert tools.get_node_detail(node["id"])["node"]["qualified_name"]
    assert tools.get_file_context("app.py")["chunks"]
    assert "snapshots" in tools.list_snapshots()
