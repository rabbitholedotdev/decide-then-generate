from __future__ import annotations

from typing import Protocol

from app.settings import Settings, get_settings
from app.types import Decision, TurnContext


class Decider(Protocol):
    name: str

    async def decide(self, ctx: TurnContext) -> Decision:
        """Answer the typed decision form for this turn."""


def build_decider(settings: Settings | None = None) -> Decider:
    cfg = settings or get_settings()
    if cfg.decider == "llm_json":
        from app.decider.llm_json import LlmJsonDecider

        return LlmJsonDecider()
    from app.decider.mock import MockDecider

    return MockDecider()
