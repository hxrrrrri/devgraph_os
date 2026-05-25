"""Language registry for code extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from devgraph.extractors.code.languages import TREE_SITTER_LANGUAGE_NAMES, language_for_path


@dataclass(frozen=True)
class LanguageSpec:
    language: str
    tree_sitter_name: str | None
    family: str
    supported: bool = True


LANGUAGE_REGISTRY: dict[str, LanguageSpec] = {
    "python": LanguageSpec("python", "python", "python"),
    "javascript": LanguageSpec("javascript", "javascript", "js-ts"),
    "typescript": LanguageSpec("typescript", "typescript", "js-ts"),
    "go": LanguageSpec("go", "go", "compiled"),
    "rust": LanguageSpec("rust", "rust", "compiled"),
    "java": LanguageSpec("java", "java", "jvm"),
    "c": LanguageSpec("c", "c", "native"),
    "cpp": LanguageSpec("cpp", "cpp", "native"),
    "csharp": LanguageSpec("csharp", "c_sharp", "dotnet"),
    "ruby": LanguageSpec("ruby", "ruby", "dynamic"),
    "php": LanguageSpec("php", "php", "dynamic"),
    "kotlin": LanguageSpec("kotlin", "kotlin", "jvm"),
    "swift": LanguageSpec("swift", "swift", "native"),
    "scala": LanguageSpec("scala", "scala", "jvm"),
    "dart": LanguageSpec("dart", "dart", "mobile"),
    "lua": LanguageSpec("lua", "lua", "dynamic"),
    "bash": LanguageSpec("bash", "bash", "shell"),
    "sql": LanguageSpec("sql", None, "database"),
    "vue": LanguageSpec("vue", None, "component"),
    "svelte": LanguageSpec("svelte", None, "component"),
}


def spec_for_path(path: Path) -> LanguageSpec | None:
    language = language_for_path(path)
    return LANGUAGE_REGISTRY.get(language or "")


def tree_sitter_name(language: str | None, path: Path | None = None) -> str | None:
    if language == "typescript" and path and path.suffix.lower() == ".tsx":
        return "tsx"
    return TREE_SITTER_LANGUAGE_NAMES.get(language or "")
