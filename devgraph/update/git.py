"""Git integration helpers."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitChange:
    path: str
    status: str
    patch: str = ""


def run_git(root: Path, args: list[str]) -> str:
    git = shutil.which("git")
    if not git:
        return ""
    try:
        result = subprocess.run(
            [git, *args],  # nosec B603
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def current_branch(root: Path) -> str:
    return run_git(root, ["branch", "--show-current"]) or "unknown"


def recent_commits(root: Path, limit: int = 5) -> list[str]:
    output = run_git(root, ["log", f"-{limit}", "--oneline"])
    return output.splitlines() if output else []


def changed_files(root: Path, base: str | None = None, staged: bool = False) -> list[GitChange]:
    args = ["diff", "--name-status"]
    if staged:
        args.append("--staged")
    elif base:
        args.append(base)
    output = run_git(root, args)
    if not output and not base and not staged:
        output = run_git(root, ["status", "--porcelain"])
        return _parse_porcelain(output)
    changes: list[GitChange] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changes.append(GitChange(path=parts[-1], status=parts[0]))
    return changes


def diff_patch(root: Path, path: str, base: str | None = None, staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--staged")
    elif base:
        args.append(base)
    args.extend(["--", path])
    return run_git(root, args)


def _parse_porcelain(output: str) -> list[GitChange]:
    changes: list[GitChange] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip() or "M"
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changes.append(GitChange(path=path, status=status))
    return changes
