"""Policy counters live in code, not in the prompt.

- no offer in the first N turns
- minimum interval between offers
- hard cap on offers
- high-risk always becomes handoff
"""

from __future__ import annotations

from app.settings import Settings, get_settings
from app.types import ACT_TO_STAGE, Decision, RiskLevel, SpeechAct, SessionState, Stage, Tone


def demote_offer(decision: Decision, reason: str) -> Decision:
    act = SpeechAct.RECOMMEND if decision.product_ids else SpeechAct.ASK_NEED
    if not decision.product_ids and decision.next_slot == "occasion":
        act = SpeechAct.ASK_OCCASION
    elif not decision.product_ids and decision.next_slot:
        mapping = {
            "need": SpeechAct.ASK_NEED,
            "occasion": SpeechAct.ASK_OCCASION,
            "taste": SpeechAct.ASK_TASTE,
            "caffeine": SpeechAct.ASK_CAFFEINE,
            "budget": SpeechAct.ASK_BUDGET,
            "experience": SpeechAct.ASK_EXPERIENCE,
        }
        act = mapping.get(decision.next_slot, SpeechAct.ASK_NEED)
    stage = ACT_TO_STAGE[act]
    return decision.model_copy(
        update={
            "speech_act": act,
            "stage": stage,
            "rag_stage": stage,
            "should_offer": False,
            "reason_codes": [*decision.reason_codes, reason],
            "draft_brief": (
                "Do not offer a purchase. "
                + (decision.draft_brief if act is SpeechAct.RECOMMEND else f"Ask for {decision.next_slot}.")
            ),
        }
    )


def force_handoff(decision: Decision, reason: str) -> Decision:
    return decision.model_copy(
        update={
            "speech_act": SpeechAct.HANDOFF,
            "stage": Stage.HANDOFF,
            "rag_stage": Stage.HANDOFF,
            "should_offer": False,
            "should_handoff": True,
            "risk_level": RiskLevel.HIGH,
            "tone": Tone.CAREFUL,
            "product_ids": [],
            "reason_codes": [*decision.reason_codes, reason],
            "draft_brief": "Stop selling. Hand the visitor to a human. No new products.",
        }
    )


def enforce(state: SessionState, decision: Decision, settings: Settings | None = None) -> Decision:
    cfg = settings or get_settings()
    if (
        decision.should_handoff
        or decision.risk_level is RiskLevel.HIGH
        or state.handed_off
        or "legal" in decision.risk_codes
        or "payment_data" in decision.risk_codes
        or "medical" in decision.risk_codes
    ):
        return force_handoff(decision, "policy:handoff_risk")

    wants_offer = decision.should_offer or decision.speech_act is SpeechAct.OFFER
    if wants_offer:
        if state.turn <= cfg.no_offer_until_turn:
            return demote_offer(decision, "policy:no_offer_first_4")
        if (
            state.last_offer_turn is not None
            and (state.turn - state.last_offer_turn) < cfg.min_turns_between_offers
        ):
            return demote_offer(decision, "policy:offer_interval")
        if state.offers_made >= cfg.max_offers:
            return demote_offer(decision, "policy:max_offers")

    if decision.speech_act is SpeechAct.OFFER:
        decision = decision.model_copy(update={"should_offer": True, "stage": Stage.OFFER, "rag_stage": Stage.OFFER})
    return decision


def apply_turn_bookkeeping(state: SessionState, decision: Decision, user_message: str, reply: str) -> None:
    from app.types import Message

    state.slots.update({k: v for k, v in decision.slots_filled.items() if v})
    state.language = decision.language
    if decision.risk_codes:
        for code in decision.risk_codes:
            if code not in state.risk_flags:
                state.risk_flags.append(code)
    if decision.speech_act is SpeechAct.OFFER and decision.should_offer:
        state.last_offer_turn = state.turn
        state.offers_made += 1
    if decision.should_handoff or decision.speech_act is SpeechAct.HANDOFF:
        state.handed_off = True
    state.transcript.append(Message(role="user", content=user_message))
    state.transcript.append(Message(role="assistant", content=reply))
