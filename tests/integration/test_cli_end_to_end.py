from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app


def test_cli_end_to_end_core_commands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("def main():\n    return True\n", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["build"]).exit_code == 0
    assert runner.invoke(app, ["status", "--json"]).exit_code == 0
    assert runner.invoke(app, ["explain", "app.py"]).exit_code == 0
    assert runner.invoke(app, ["review", "--json", "--files", "app.py"]).exit_code == 0
    assert runner.invoke(app, ["debug", 'File "app.py", line 1, in main', "--json"]).exit_code == 0
    assert runner.invoke(app, ["onboard"]).exit_code == 0
    assert runner.invoke(app, ["handoff"]).exit_code == 0
