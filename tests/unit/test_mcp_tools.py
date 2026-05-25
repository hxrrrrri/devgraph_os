from pathlib import Path

from devgraph.config import ensure_project
from devgraph.server.mcp_server import DevGraphMcpTools


def test_mcp_tool_json_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    ensure_project(tmp_path)
    (tmp_path / "app.py").write_text("def main():\n    return True\n", encoding="utf-8")
    tools = DevGraphMcpTools(tmp_path)
    build = tools.build_or_update_graph(incremental=False)
    status = tools.get_project_status()
    context = tools.get_context("explain", "main")
    assert build["indexed"] >= 1
    assert status["total_nodes"] > 0
    assert "context_pack" in context
