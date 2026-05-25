from pathlib import Path

from typer.testing import CliRunner

from devgraph.cli import app


def test_memory_cli_remember_list_forget(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    memory = runner.invoke(app, ["remember", "--kind", "decision", "api_key=secret"])
    assert memory.exit_code == 0
    memory_id = memory.stdout.strip()
    listed = runner.invoke(app, ["memories", "--json"])
    assert "<redacted>" in listed.stdout
    assert "api_key=secret" not in listed.stdout
    forgotten = runner.invoke(app, ["forget", memory_id])
    assert forgotten.exit_code == 0
