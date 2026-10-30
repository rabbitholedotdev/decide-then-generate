from __future__ import annotations

import json

import pytest

from app.catalog import default_catalog
from app.decider.llm_json import LlmJsonDecider
from app.decider.mock import MockDecider, extract_slots
from app.types import Decision, RiskLevel, SessionState, SpeechAct, Stage, TurnContext


@pytest.fixture
def decider():
    return MockDecider(default_catalog())


async def _decide(decider: MockDecider, text: str, turn: int = 1, **state_kw) -> Decision:
    state = SessionState(session_id="s", turn=turn, **state_kw)
    return await decider.decide(TurnContext(state=state, user_message=text, catalog_ids=sorted(default_catalog().ids())))


@pytest.mark.asyncio
async def test_first_turn_greets(decider):
    d = await _decide(decider, "oi", turn=1)
    assert d.speech_act is SpeechAct.GREET
    assert d.should_offer is False


@pytest.mark.asyncio
async def test_gift_green_fills_slots(decider):
    d = await _decide(decider, "quero um cha verde para presente", turn=2)
    assert d.slots_filled.get("occasion") == "gift"
    assert d.slots_filled.get("taste") == "green"
    assert d.slots_filled.get("need") == "tea"


@pytest.mark.asyncio
async def test_legal_is_high_risk_handoff(decider):
    d = await _decide(decider, "vou processar voces no procon com advogado", turn=1)
    assert d.speech_act is SpeechAct.HANDOFF
    assert d.risk_level is RiskLevel.HIGH
    assert d.should_handoff is True


@pytest.mark.asyncio
async def test_mock_proposes_offer_when_ready(decider):
    d = await _decide(
        decider,
        "e iniciante e pode ate 90",
        turn=5,
        slots={"need": "tea", "occasion": "gift", "taste": "green"},
    )
    assert d.speech_act is SpeechAct.OFFER
    assert d.should_offer is True
    assert d.product_ids


@pytest.mark.asyncio
async def test_llm_json_decider_parses_structured_output():
    payload = {
        "speech_act": "ask_taste",
        "stage": "discovery",
        "user_intent": "discover",
        "slots_filled": {"need": "tea"},
        "next_slot": "taste",
        "should_offer": False,
        "should_handoff": False,
        "risk_level": "none",
        "risk_codes": [],
        "product_ids": ["not-a-real-sku", "tea-sencha-50"],
        "objection_type": None,
        "tone": "warm",
        "rag_stage": "discovery",
        "language": "pt-BR",
        "confidence": 0.8,
        "reason_codes": ["llm"],
        "draft_brief": "ask taste",
    }

    class _Msg:
        content = json.dumps(payload)

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kwargs):
            assert kwargs["response_format"] == {"type": "json_object"}
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    decider = LlmJsonDecider(client=_Client())
    ctx = TurnContext(
        state=SessionState(session_id="s", turn=2),
        user_message="quero cha",
        catalog_ids=sorted(default_catalog().ids()),
    )
    decision = await decider.decide(ctx)
    assert decision.speech_act is SpeechAct.ASK_TASTE
    assert decision.product_ids == ["tea-sencha-50"]
    assert "decider:llm_json" in decision.reason_codes


@pytest.mark.asyncio
async def test_llm_json_falls_back_on_bad_payload():
    class _Msg:
        content = "not-json"

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kwargs):
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    decider = LlmJsonDecider(client=_Client())
    ctx = TurnContext(
        state=SessionState(session_id="s", turn=1),
        user_message="oi",
        catalog_ids=sorted(default_catalog().ids()),
    )
    decision = await decider.decide(ctx)
    assert "decider:llm_json_fallback" in decision.reason_codes
    assert decision.speech_act in {SpeechAct.GREET, SpeechAct.ASK_NEED}


def test_extract_slots_caffeine_free():
    slots = extract_slots("quero algo sem cafeina para a noite", {})
    assert slots.get("caffeine") in {"none", "low"}
