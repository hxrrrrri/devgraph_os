from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app


def test_cli_smoke_init_build_status_explain(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("def main():\n    return True\n", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    build = runner.invoke(app, ["build"])
    assert build.exit_code == 0, build.output
    status = runner.invoke(app, ["status", "--json"])
    assert status.exit_code == 0, status.output
    explain = runner.invoke(app, ["explain", "main"])
    assert explain.exit_code == 0, explain.output
    assert "DevGraph Context Pack" in explain.output
