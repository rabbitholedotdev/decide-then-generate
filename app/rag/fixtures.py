"""Stage-keyed RAG. Zero embeddings per turn on this path."""

from __future__ import annotations

from pathlib import Path

from app.settings import ROOT
from app.types import Chunk, Stage

STAGE_FILES = {
    Stage.DISCOVERY: "discovery.md",
    Stage.EDUCATE: "educate.md",
    Stage.RECOMMEND: "recommend.md",
    Stage.OFFER: "offer.md",
    Stage.HANDOFF: "handoff.md",
}


class FixtureRetriever:
    name = "fixtures"

    def __init__(self, rag_dir: Path | None = None):
        self.rag_dir = rag_dir or (ROOT / "fixtures" / "rag")
        self._cache: dict[Stage, Chunk] = {}
        for stage, filename in STAGE_FILES.items():
            path = self.rag_dir / filename
            self._cache[stage] = Chunk(stage=stage, text=path.read_text(encoding="utf-8"), source=str(path.name))

    def retrieve(self, stage: Stage, query: str) -> list[Chunk]:
        del query  # intentionally unused: no embedding, no lexical search
        chunk = self._cache.get(stage) or self._cache[Stage.DISCOVERY]
        return [chunk]
