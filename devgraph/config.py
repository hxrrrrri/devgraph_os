"""Configuration loading and project initialization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from devgraph.constants import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_DASHBOARD_PORT,
    DEFAULT_EXCLUDES,
    DEFAULT_IGNORE_FILE,
    DEFAULT_STORAGE_DIR,
)

try:  # pragma: no cover - Python 3.10 compatibility path
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


class ProjectConfig(BaseModel):
    name: str = "devgraph-project"


class IndexingConfig(BaseModel):
    include: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    respect_gitignore: bool = True


class StorageConfig(BaseModel):
    path: str = DEFAULT_STORAGE_DIR


class ReviewConfig(BaseModel):
    default_base: str = "origin/main"
    max_depth: int = 2
    token_budget: str = "normal"


class PrivacyConfig(BaseModel):
    store_env_values: bool = False
    allow_llm_enrichment: bool = False


class DashboardConfig(BaseModel):
    port: int = DEFAULT_DASHBOARD_PORT


class DevGraphConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    indexing: IndexingConfig = Field(default_factory=IndexingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)

    @property
    def storage_path(self) -> Path:
        return Path(self.storage.path)


DEFAULT_CONFIG_TEXT = """[project]
name = "my-project"

[indexing]
include = ["**/*"]
exclude = [".git/**", ".devgraph/**", "node_modules/**", "dist/**", "build/**", ".venv/**", "__pycache__/**", "*.pyc", "*.lock"]
respect_gitignore = true

[storage]
path = ".devgraph"

[review]
default_base = "origin/main"
max_depth = 2
token_budget = "normal"

[privacy]
store_env_values = false
allow_llm_enrichment = false

[dashboard]
port = 38987
"""


DEFAULT_IGNORE_TEXT = """.git/**
.devgraph/**
node_modules/**
dist/**
build/**
.venv/**
__pycache__/**
*.pyc
*.lock
coverage/**
"""


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / DEFAULT_CONFIG_FILE).exists() or (candidate / ".git").exists():
            return candidate
    return current


def load_config(project_root: Path | None = None) -> DevGraphConfig:
    root = (project_root or find_project_root()).resolve()
    path = root / DEFAULT_CONFIG_FILE
    if not path.exists():
        return DevGraphConfig(project=ProjectConfig(name=root.name))
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    config = DevGraphConfig.model_validate(data)
    if config.project.name == "my-project":
        config.project.name = root.name
    return config


def ensure_project(project_root: Path, platform: str | None = None) -> list[Path]:
    created: list[Path] = []
    config_path = project_root / DEFAULT_CONFIG_FILE
    if not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG_TEXT.replace('"my-project"', f'"{project_root.name}"'), encoding="utf-8")
        created.append(config_path)
    ignore_path = project_root / DEFAULT_IGNORE_FILE
    if not ignore_path.exists():
        ignore_path.write_text(DEFAULT_IGNORE_TEXT, encoding="utf-8")
        created.append(ignore_path)
    storage_path = project_root / DEFAULT_STORAGE_DIR
    for child in ["cache", "snapshots", "reports", "wiki", "sessions", "exports"]:
        path = storage_path / child
        path.mkdir(parents=True, exist_ok=True)
    if platform:
        created.extend(_write_platform_instructions(project_root, platform))
    return created


def _write_platform_instructions(project_root: Path, platform: str) -> list[Path]:
    from devgraph.integrations.generic import (
        platform_instruction_targets,
        render_platform_instructions,
    )

    known = {"claude", "codex", "cursor", "copilot", "gemini", "generic", "all"}
    if platform not in known:
        raise ValueError(
            "platform must be one of: claude, codex, cursor, copilot, gemini, generic, all"
        )
    requested = ["claude", "codex", "cursor", "copilot", "gemini", "generic"] if platform == "all" else [platform]
    created: list[Path] = []
    for item in requested:
        target = project_root / platform_instruction_targets().get(item, f"DEVGRAPH_{item.upper()}.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_platform_instructions(item), encoding="utf-8")
        created.append(target)
    return created


def config_as_dict(config: DevGraphConfig) -> dict[str, Any]:
    return config.model_dump()
