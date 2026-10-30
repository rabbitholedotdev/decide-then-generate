from __future__ import annotations

from typing import Protocol

from app.settings import Settings, get_settings
from app.types import Chunk, Stage


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        """Vector for a query. Must not be called on the fixtures path."""


class Retriever(Protocol):
    name: str

    def retrieve(self, stage: Stage, query: str) -> list[Chunk]:
        """Return stage-scoped chunks. Fixtures path ignores query embeddings."""


def build_retriever(settings: Settings | None = None, embedder: Embedder | None = None) -> Retriever:
    cfg = settings or get_settings()
    if cfg.retriever == "qdrant":
        from app.rag.qdrant import QdrantRetriever

        return QdrantRetriever(url=cfg.qdrant_url, collection=cfg.qdrant_collection, embedder=embedder)
    from app.rag.fixtures import FixtureRetriever

    return FixtureRetriever(cfg.rag_dir)
