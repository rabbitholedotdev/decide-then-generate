from __future__ import annotations

from app.settings import Settings
from app.state_machine import enforce
from app.types import Decision, RiskLevel, SessionState, SpeechAct, Stage


def _offer(reason: str = "ready") -> Decision:
    return Decision(
        speech_act=SpeechAct.OFFER,
        stage=Stage.OFFER,
        should_offer=True,
        product_ids=["set-tasting-3"],
        reason_codes=[reason],
        draft_brief="offer now",
        rag_stage=Stage.OFFER,
    )


def test_no_offer_in_first_four_turns():
    cfg = Settings()
    for turn in range(1, 5):
        state = SessionState(session_id="s", turn=turn)
        out = enforce(state, _offer(), cfg)
        assert out.should_offer is False
        assert out.speech_act is not SpeechAct.OFFER
        assert "policy:no_offer_first_4" in out.reason_codes


def test_offer_allowed_on_turn_five():
    state = SessionState(session_id="s", turn=5)
    out = enforce(state, _offer(), Settings())
    assert out.should_offer is True
    assert out.speech_act is SpeechAct.OFFER


def test_offer_interval():
    state = SessionState(session_id="s", turn=6, last_offer_turn=5, offers_made=1)
    out = enforce(state, _offer(), Settings())
    assert out.should_offer is False
    assert "policy:offer_interval" in out.reason_codes
    state2 = SessionState(session_id="s", turn=8, last_offer_turn=5, offers_made=1)
    out2 = enforce(state2, _offer(), Settings())
    assert out2.should_offer is True


def test_max_offers():
    state = SessionState(session_id="s", turn=9, last_offer_turn=5, offers_made=2)
    out = enforce(state, _offer(), Settings())
    assert out.should_offer is False
    assert "policy:max_offers" in out.reason_codes


def test_handoff_on_high_risk():
    state = SessionState(session_id="s", turn=2)
    decision = Decision(
        speech_act=SpeechAct.RECOMMEND,
        stage=Stage.RECOMMEND,
        should_offer=True,
        risk_level=RiskLevel.HIGH,
        risk_codes=["legal"],
        product_ids=["tea-sencha-50"],
        rag_stage=Stage.RECOMMEND,
    )
    out = enforce(state, decision, Settings())
    assert out.speech_act is SpeechAct.HANDOFF
    assert out.should_handoff is True
    assert out.should_offer is False
    assert out.product_ids == []
    assert "policy:handoff_risk" in out.reason_codes
