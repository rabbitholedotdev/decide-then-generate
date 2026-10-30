"""Optional Qdrant path. Mockable client + embedder. Not the default."""

from __future__ import annotations

from typing import Any, Protocol

from app.types import Chunk, Stage


class QdrantLike(Protocol):
    def search(self, collection_name: str, query_vector: list[float], limit: int, query_filter: Any) -> list[Any]:
        ...


class QdrantRetriever:
    name = "qdrant"

    def __init__(
        self,
        url: str = "http://127.0.0.1:6333",
        collection: str = "orvalho_stage_chunks",
        embedder=None,
        client: QdrantLike | None = None,
    ):
        self.url = url
        self.collection = collection
        self.embedder = embedder
        self.client = client

    def retrieve(self, stage: Stage, query: str) -> list[Chunk]:
        if self.embedder is None:
            raise RuntimeError("QdrantRetriever requires an embedder; the default app path uses fixtures.")
        if self.client is None:
            raise RuntimeError("QdrantRetriever requires a client; inject a fake in tests.")
        vector = self.embedder.embed(query)
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=3,
            query_filter={"stage": stage.value},
        )
        chunks: list[Chunk] = []
        for hit in hits:
            payload = getattr(hit, "payload", None) or hit.get("payload", {})
            chunks.append(
                Chunk(
                    stage=Stage(payload.get("stage", stage.value)),
                    text=payload.get("text", ""),
                    source=payload.get("source", "qdrant"),
                )
            )
        return chunks
