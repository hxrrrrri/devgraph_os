"""Local-first embedding providers and indexing helpers."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, cast

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.core.schema import Chunk, ExtractionResult, Node

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")


class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    def dimensions(self) -> int:
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts into normalized vectors."""


class EmbeddingRecord(TypedDict):
    entity_id: str
    entity_type: str
    text: str
    file_path: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LocalHashEmbeddingProvider:
    """Deterministic local embedding provider.

    This is not a hosted semantic model. It is a zero-dependency, normalized
    hashing vectorizer over code/doc tokens that gives DevGraph a local vector
    index for hybrid retrieval immediately.
    """

    dimensions: int = 256
    provider_name: str = "local-hash"
    model_name: str = "devgraph-local-hash-v1"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(_vectorize(text, self.dimensions)) for text in texts]


class SentenceTransformersEmbeddingProvider:
    """Optional local sentence-transformers provider.

    The model name must resolve locally or be deliberately available in the
    user's Python environment. DevGraph does not download or call hosted APIs.
    """

    provider_name = "sentence-transformers"

    def __init__(self, model_name: str, dimensions: int = 384) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Install sentence-transformers and provide a local model path to use this provider."
            ) from exc
        self.model_name = model_name
        self.dimensions = dimensions
        self._model = SentenceTransformer(model_name, local_files_only=True)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def provider_from_config(config: DevGraphConfig | None = None) -> EmbeddingProvider:
    if config and config.retrieval.embedding_provider in {"local", "sentence-transformers"}:
        return SentenceTransformersEmbeddingProvider(
            config.retrieval.embedding_model,
            dimensions=config.retrieval.embedding_dimensions,
        )
    dimensions = config.retrieval.embedding_dimensions if config else 256
    model = config.retrieval.embedding_model if config else "devgraph-local-hash-v1"
    return LocalHashEmbeddingProvider(dimensions=dimensions, model_name=model)


def index_extraction_embeddings(
    store: GraphStore,
    result: ExtractionResult,
    config: DevGraphConfig,
) -> int:
    if not config.retrieval.embeddings_enabled:
        return 0
    provider = provider_from_config(config)
    records = [*_node_records(result.nodes), *_chunk_records(result.chunks)]
    if not records:
        return 0
    vectors = provider.embed([record["text"] for record in records])
    for record, vector in zip(records, vectors, strict=True):
        store.upsert_embedding(
            entity_id=record["entity_id"],
            entity_type=record["entity_type"],
            provider=provider.provider_name,
            model=provider.model_name,
            vector=vector,
            text=record["text"],
            file_path=record["file_path"],
            metadata=record["metadata"],
        )
    store.connection.commit()
    return len(records)


def semantic_search(
    store: GraphStore,
    query: str,
    limit: int = 10,
    config: DevGraphConfig | None = None,
    entity_types: list[str] | None = None,
) -> list[dict[str, object]]:
    if not query.strip() or (config is not None and not config.retrieval.embeddings_enabled):
        return []
    provider = provider_from_config(config)
    query_vector = provider.embed([query])[0]
    return store.search_embeddings(
        query_vector,
        provider=provider.provider_name,
        model=provider.model_name,
        limit=limit,
        entity_types=entity_types,
    )


def index_existing_embeddings(store: GraphStore, config: DevGraphConfig, force_local_hash: bool = False) -> int:
    """Index existing graph nodes and chunks with a local provider."""
    if not config.retrieval.embeddings_enabled and not force_local_hash:
        return 0
    provider: EmbeddingProvider = (
        LocalHashEmbeddingProvider() if force_local_hash else provider_from_config(config)
    )
    nodes = [
        store._row_to_node(row)
        for row in store.connection.execute("SELECT * FROM nodes").fetchall()
    ]
    chunks = [
        store._row_to_chunk(row)
        for row in store.connection.execute("SELECT * FROM chunks").fetchall()
    ]
    records = [*_node_records(nodes), *_chunk_records(chunks)]
    if not records:
        return 0
    vectors = provider.embed([record["text"] for record in records])
    for record, vector in zip(records, vectors, strict=True):
        store.upsert_embedding(
            entity_id=record["entity_id"],
            entity_type=record["entity_type"],
            provider=provider.provider_name,
            model=provider.model_name,
            vector=vector,
            text=record["text"],
            file_path=record["file_path"],
            metadata=record["metadata"],
        )
    store.connection.commit()
    return len(records)


def _node_records(nodes: Iterable[Node]) -> list[EmbeddingRecord]:
    records: list[EmbeddingRecord] = []
    for node in nodes:
        text = " ".join(
            part
            for part in [
                node.type,
                node.name,
                node.qualified_name,
                node.summary or "",
                " ".join(node.tags),
                " ".join(str(value) for value in node.metadata.values() if isinstance(value, str)),
            ]
            if part
        )
        records.append(
            {
                "entity_id": node.id,
                "entity_type": "node",
                "text": text,
                "file_path": node.file_path,
                "metadata": {"node_type": node.type, "qualified_name": node.qualified_name},
            }
        )
    return records


def _chunk_records(chunks: Iterable[Chunk]) -> list[EmbeddingRecord]:
    return [
        {
            "entity_id": chunk.id,
            "entity_type": "chunk",
            "text": chunk.content,
            "file_path": chunk.file_path,
            "metadata": cast(
                dict[str, Any],
                {
                    "kind": chunk.kind,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "node_id": chunk.node_id,
                },
            ),
        }
        for chunk in chunks
    ]


def _vectorize(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    for token in tokens:
        _add_feature(vector, token, 1.0)
        for part in _split_identifier(token):
            _add_feature(vector, f"part:{part}", 0.75)
    for left, right in zip(tokens, tokens[1:], strict=False):
        _add_feature(vector, f"{left}::{right}", 0.5)
    return vector


def _split_identifier(token: str) -> list[str]:
    snake_parts = token.replace("-", "_").split("_")
    parts: list[str] = []
    for item in snake_parts:
        parts.extend(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[0-9]+", item) or [item])
    return [part.lower() for part in parts if part]


def _add_feature(vector: list[float], feature: str, weight: float) -> None:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    index = value % len(vector)
    sign = 1.0 if value & 1 else -1.0
    vector[index] += sign * weight


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
