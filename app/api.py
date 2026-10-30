from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field

from app.orchestrator import Assistant, default_assistant
from app.types import Decision


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class GuardOut(BaseModel):
    passed: bool
    regenerated: bool
    violations: list[str] = Field(default_factory=list)


class ChatOut(BaseModel):
    session_id: str
    reply: str
    prompt_version: str
    speech_act: str
    stage: str
    should_offer: bool
    should_handoff: bool
    product_ids: list[str]
    reason_codes: list[str]
    guard: GuardOut
    decider: str
    retriever: str
    writer: str
    decision: Decision


class HealthOut(BaseModel):
    status: str
    prompt_version: str
    decider: str
    retriever: str
    writer: str
    catalog_size: int


@lru_cache(maxsize=1)
def get_assistant() -> Assistant:
    return default_assistant()
