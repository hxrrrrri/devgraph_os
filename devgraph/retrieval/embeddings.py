"""Embedding interface placeholder.

Embeddings are intentionally disabled by default because DevGraph OS is
local-first. A future local embedding provider can implement this boundary.
"""

from __future__ import annotations


class EmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("No embedding provider configured.")

