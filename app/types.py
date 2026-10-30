"""Typed decision packet answered every turn (~15 fields) plus session types."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SpeechAct(str, Enum):
    GREET = "greet"
    ASK_NEED = "ask_need"
    ASK_OCCASION = "ask_occasion"
    ASK_TASTE = "ask_taste"
    ASK_CAFFEINE = "ask_caffeine"
    ASK_BUDGET = "ask_budget"
    ASK_EXPERIENCE = "ask_experience"
    EDUCATE = "educate"
    RECOMMEND = "recommend"
    COMPARE = "compare"
    OFFER = "offer"
    HANDLE_OBJECTION = "handle_objection"
    CONFIRM = "confirm"
    HANDOFF = "handoff"
    CLOSE = "close"


class Stage(str, Enum):
    DISCOVERY = "discovery"
    EDUCATE = "educate"
    RECOMMEND = "recommend"
    OFFER = "offer"
    HANDOFF = "handoff"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"


class Tone(str, Enum):
    WARM = "warm"
    NEUTRAL = "neutral"
    CAREFUL = "careful"


class Language(str, Enum):
    PT_BR = "pt-BR"
    EN = "en"


ASK_ACTS = {
    SpeechAct.ASK_NEED,
    SpeechAct.ASK_OCCASION,
    SpeechAct.ASK_TASTE,
    SpeechAct.ASK_CAFFEINE,
    SpeechAct.ASK_BUDGET,
    SpeechAct.ASK_EXPERIENCE,
}

SLOT_ORDER = ("need", "occasion", "taste", "caffeine", "budget", "experience")

ACT_TO_STAGE = {
    SpeechAct.GREET: Stage.DISCOVERY,
    SpeechAct.ASK_NEED: Stage.DISCOVERY,
    SpeechAct.ASK_OCCASION: Stage.DISCOVERY,
    SpeechAct.ASK_TASTE: Stage.DISCOVERY,
    SpeechAct.ASK_CAFFEINE: Stage.DISCOVERY,
    SpeechAct.ASK_BUDGET: Stage.DISCOVERY,
    SpeechAct.ASK_EXPERIENCE: Stage.DISCOVERY,
    SpeechAct.EDUCATE: Stage.EDUCATE,
    SpeechAct.RECOMMEND: Stage.RECOMMEND,
    SpeechAct.COMPARE: Stage.RECOMMEND,
    SpeechAct.HANDLE_OBJECTION: Stage.RECOMMEND,
    SpeechAct.OFFER: Stage.OFFER,
    SpeechAct.CONFIRM: Stage.OFFER,
    SpeechAct.HANDOFF: Stage.HANDOFF,
    SpeechAct.CLOSE: Stage.DISCOVERY,
}


class Decision(BaseModel):
    """Structured answers the Decider fills each turn. The writer must not invent strategy."""

    speech_act: SpeechAct
    stage: Stage
    user_intent: str = ""
    slots_filled: dict[str, str] = Field(default_factory=dict)
    next_slot: str | None = None
    should_offer: bool = False
    should_handoff: bool = False
    risk_level: RiskLevel = RiskLevel.NONE
    risk_codes: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    objection_type: str | None = None
    tone: Tone = Tone.WARM
    rag_stage: Stage = Stage.DISCOVERY
    language: Language = Language.PT_BR
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    draft_brief: str = ""

    def compact(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SessionState(BaseModel):
    session_id: str
    turn: int = 0
    last_offer_turn: int | None = None
    offers_made: int = 0
    slots: dict[str, str] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    handed_off: bool = False
    language: Language = Language.PT_BR
    transcript: list[Message] = Field(default_factory=list)

    @property
    def turns_since_offer(self) -> int | None:
        if self.last_offer_turn is None:
            return None
        return self.turn - self.last_offer_turn


class CatalogItem(BaseModel):
    id: str
    name: str
    price_cents: int
    currency: str = "BRL"
    category: str
    tags: list[str] = Field(default_factory=list)
    blurb: str = ""

    @property
    def price_label(self) -> str:
        major = self.price_cents / 100
        return f"{major:.2f} {self.currency}"


class Chunk(BaseModel):
    stage: Stage
    text: str
    source: str = "fixtures"


class TurnContext(BaseModel):
    state: SessionState
    user_message: str
    catalog_ids: list[str] = Field(default_factory=list)
