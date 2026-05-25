"""Extractor registry and file classification."""

from __future__ import annotations

from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.constants import (
    SUPPORTED_CODE_EXTENSIONS,
    SUPPORTED_CONFIG_EXTENSIONS,
    SUPPORTED_DOC_EXTENSIONS,
)
from devgraph.core.schema import ExtractionResult
from devgraph.extractors.base import BaseExtractor
from devgraph.extractors.code.tree_sitter_parser import CodeExtractor
from devgraph.extractors.config.env_parser import EnvExtractor
from devgraph.extractors.config.json_parser import JsonExtractor
from devgraph.extractors.config.toml_parser import TomlExtractor
from devgraph.extractors.config.yaml_parser import YamlExtractor
from devgraph.extractors.docs.markdown import MarkdownExtractor
from devgraph.extractors.docs.office import OfficeExtractor
from devgraph.extractors.docs.pdf import PdfExtractor
from devgraph.extractors.docs.rst import RstExtractor
from devgraph.extractors.docs.text import TextExtractor
from devgraph.extractors.infra.docker import DockerExtractor
from devgraph.extractors.infra.github_actions import GitHubActionsExtractor
from devgraph.extractors.infra.kubernetes import KubernetesExtractor
from devgraph.extractors.infra.terraform import TerraformExtractor


def classify_file(path: Path) -> tuple[str, str | None]:
    name = path.name
    suffix = path.suffix.lower()
    if name == "Dockerfile" or name.endswith(".Dockerfile"):
        return "infra", "dockerfile"
    if suffix in {".tf", ".tfvars"}:
        return "infra", "terraform"
    if ".github" in path.parts and suffix in {".yml", ".yaml"}:
        return "infra", "github-actions"
    if suffix in SUPPORTED_CODE_EXTENSIONS:
        return "code", SUPPORTED_CODE_EXTENSIONS[suffix]
    if suffix in SUPPORTED_DOC_EXTENSIONS:
        return "document", SUPPORTED_DOC_EXTENSIONS[suffix]
    if name == ".env" or name.endswith(".env") or suffix == ".env":
        return "config", "env"
    if suffix in SUPPORTED_CONFIG_EXTENSIONS:
        return "config", SUPPORTED_CONFIG_EXTENSIONS[suffix]
    return "unknown", None


class ExtractorRegistry:
    def __init__(self, config: DevGraphConfig) -> None:
        self.config = config
        self._code = CodeExtractor(config)
        self._by_language: dict[str, BaseExtractor] = {
            "markdown": MarkdownExtractor(config),
            "rst": RstExtractor(config),
            "text": TextExtractor(config),
            "pdf": PdfExtractor(config),
            "office": OfficeExtractor(config),
            "json": JsonExtractor(config),
            "yaml": YamlExtractor(config),
            "toml": TomlExtractor(config),
            "env": EnvExtractor(config),
            "dockerfile": DockerExtractor(config),
            "github-actions": GitHubActionsExtractor(config),
            "terraform": TerraformExtractor(config),
            "kubernetes": KubernetesExtractor(config),
        }

    def extract(self, root: Path, path: Path) -> ExtractionResult:
        category, language = classify_file(path)
        if category == "code":
            return self._code.extract(root, path)
        if language in self._by_language:
            return self._by_language[language].extract(root, path)
        return TextExtractor(self.config).extract(root, path)

