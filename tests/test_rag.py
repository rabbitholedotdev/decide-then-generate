from __future__ import annotations

import pytest

from app.rag.fixtures import FixtureRetriever
from app.rag.qdrant import QdrantRetriever
from app.types import Stage


class ExplodingEmbedder:
    def embed(self, text: str) -> list[float]:
        raise AssertionError(f"0 embedding/turn expected on fixtures path, got {text!r}")


def test_fixture_retrieve_is_stage_keyed_and_embedding_free():
    retriever = FixtureRetriever()
    chunks = retriever.retrieve(Stage.RECOMMEND, "invent a superblend please")
    assert retriever.name == "fixtures"
    assert len(chunks) == 1
    assert chunks[0].stage is Stage.RECOMMEND
    assert "set-tasting-3" in chunks[0].text
    # embedder is not even a collaborator on this path
    exploding = ExplodingEmbedder()
    more = retriever.retrieve(Stage.HANDOFF, "advogado")
    assert more[0].stage is Stage.HANDOFF
    with pytest.raises(AssertionError):
        exploding.embed("should not be called by fixtures")


def test_qdrant_path_is_mockable():
    class FakeHit(dict):
        payload = {"stage": "educate", "text": "70-75 C sencha", "source": "fake"}

    class FakeClient:
        def search(self, collection_name, query_vector, limit, query_filter):
            assert collection_name == "orvalho_stage_chunks"
            assert query_vector == [0.1, 0.2]
            assert query_filter["stage"] == "educate"
            assert limit == 3
            return [FakeHit()]

    class UnitEmbedder:
        def embed(self, text: str) -> list[float]:
            assert "sencha" in text
            return [0.1, 0.2]

    retriever = QdrantRetriever(embedder=UnitEmbedder(), client=FakeClient())
    chunks = retriever.retrieve(Stage.EDUCATE, "how to brew sencha")
    assert retriever.name == "qdrant"
    assert chunks[0].text.startswith("70-75")


def test_qdrant_without_embedder_fails_closed():
    with pytest.raises(RuntimeError):
        QdrantRetriever().retrieve(Stage.DISCOVERY, "oi")
