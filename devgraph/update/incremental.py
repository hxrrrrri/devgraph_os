"""Build and incremental update orchestration."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.extractors.registry import ExtractorRegistry, classify_file
from devgraph.update.fingerprints import file_hash
from devgraph.update.git import changed_files, diff_patch
from devgraph.update.ignore import IgnoreMatcher


@dataclass
class BuildStats:
    scanned: int = 0
    indexed: int = 0
    skipped: int = 0
    deleted: int = 0
    warnings: list[str] = field(default_factory=list)


def scan_files(root: Path, config: DevGraphConfig) -> list[Path]:
    matcher = IgnoreMatcher(root, config.indexing.exclude, config.indexing.respect_gitignore)
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if matcher.ignored(path):
            continue
        rel = path.relative_to(root).as_posix()
        if not _included(rel, config.indexing.include):
            continue
        category, _language = classify_file(path)
        if category == "unknown":
            continue
        files.append(path)
    return sorted(files)


def build_graph(root: Path, config: DevGraphConfig, store: GraphStore, force: bool = False) -> BuildStats:
    registry = ExtractorRegistry(config)
    stats = BuildStats()
    indexed_hashes = _indexed_hashes(store)
    for path in scan_files(root, config):
        stats.scanned += 1
        rel = path.relative_to(root).as_posix()
        digest = file_hash(path)
        if not force and indexed_hashes.get(rel) == digest:
            stats.skipped += 1
            continue
        result = registry.extract(root, path)
        stats.warnings.extend(result.warnings)
        store.replace_file_graph(result.file, result.nodes, result.edges, result.chunks)
        stats.indexed += 1
    if stats.indexed:
        store.refresh_inferred_relationships()
        store.create_snapshot(
            "latest",
            {"operation": "build", "indexed": stats.indexed, "scanned": stats.scanned},
        )
    return stats


def update_graph(
    root: Path,
    config: DevGraphConfig,
    store: GraphStore,
    base: str | None = None,
    staged: bool = False,
) -> BuildStats:
    registry = ExtractorRegistry(config)
    stats = BuildStats()
    changes = changed_files(root, base=base, staged=staged)
    if not changes:
        return build_graph(root, config, store, force=False)
    for change in changes:
        path = root / change.path
        stats.scanned += 1
        store.record_change(
            file_path=change.path,
            status=change.status,
            patch=change.patch or diff_patch(root, change.path, base=base, staged=staged),
            base_ref=base,
            staged=staged,
            metadata={"operation": "update"},
        )
        if not path.exists() or change.status.upper().startswith("D"):
            store.mark_file_deleted(change.path)
            stats.deleted += 1
            continue
        category, _language = classify_file(path)
        if category == "unknown":
            stats.skipped += 1
            continue
        result = registry.extract(root, path)
        stats.warnings.extend(result.warnings)
        store.replace_file_graph(result.file, result.nodes, result.edges, result.chunks)
        stats.indexed += 1
    if stats.indexed or stats.deleted:
        store.refresh_inferred_relationships()
        store.create_snapshot(
            "latest",
            {
                "operation": "update",
                "indexed": stats.indexed,
                "deleted": stats.deleted,
                "scanned": stats.scanned,
                "base": base,
                "staged": staged,
            },
        )
    return stats


def _indexed_hashes(store: GraphStore) -> dict[str, str]:
    rows = store.connection.execute("SELECT path, content_hash FROM files WHERE is_deleted = 0").fetchall()
    return {row["path"]: row["content_hash"] for row in rows}


def _included(path: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    for pattern in patterns:
        if pattern in {"*", "**", "**/*"}:
            return True
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.endswith("/**") and path.startswith(pattern[:-3].rstrip("/") + "/"):
            return True
    return False
