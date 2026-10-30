from __future__ import annotations

import pytest

from app.types import SpeechAct


@pytest.mark.asyncio
async def test_full_turn_uses_fixtures_retriever(assistant):
    result = await assistant.turn("oi")
    assert result.retriever == "fixtures"
    assert result.decider == "mock"
    assert result.writer == "template"
    assert result.decision.speech_act is SpeechAct.GREET
    assert result.guard.passed


@pytest.mark.asyncio
async def test_handoff_persists(assistant):
    first = await assistant.turn("vou processar voces no procon com advogado")
    assert first.decision.speech_act is SpeechAct.HANDOFF
    second = await assistant.turn("ainda quero sencha", session_id=first.session_id)
    assert second.decision.speech_act is SpeechAct.HANDOFF
    assert second.decision.should_offer is False
