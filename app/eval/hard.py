from __future__ import annotations

from dataclasses import dataclass

from app.catalog import Catalog
from app.types import Decision, SpeechAct


@dataclass
class HardFailure:
    case_id: str
    turn: int
    check: str
    detail: str


def run_hard_checks(
    *,
    case_id: str,
    turn: int,
    decision: Decision,
    reply: str,
    catalog: Catalog,
    expect: dict,
    prompt_version: str,
    expected_version: str | None,
) -> list[HardFailure]:
    failures: list[HardFailure] = []

    def fail(check: str, detail: str) -> None:
        failures.append(HardFailure(case_id, turn, check, detail))

    if expect.get("should_offer") is False and (
        decision.should_offer or decision.speech_act is SpeechAct.OFFER
    ):
        fail("should_offer", "offer leaked")
    if expect.get("should_offer") is True and not decision.should_offer:
        fail("should_offer", "expected offer")
    if expect.get("should_handoff") is True and not decision.should_handoff:
        fail("should_handoff", "expected handoff")
    if expect.get("should_handoff") is False and decision.should_handoff:
        fail("should_handoff", "unexpected handoff")

    allowed = expect.get("allowed_acts")
    if allowed and decision.speech_act.value not in allowed:
        fail("allowed_acts", f"{decision.speech_act.value} not in {allowed}")

    if expect.get("no_offer_reason_ok") and turn <= 4:
        if "policy:no_offer_first_4" not in decision.reason_codes and decision.should_offer:
            fail("no_offer_first_4", "missing demote reason")

    unknown = [pid for pid in decision.product_ids if pid not in catalog.ids()]
    if unknown:
        fail("catalog_ids", f"unknown {unknown}")

    if expected_version and prompt_version != expected_version:
        fail("prompt_version", "prefix hash moved mid-eval")

    if expect.get("reply_must_not_match"):
        import re

        if re.search(expect["reply_must_not_match"], reply, re.I):
            fail("reply_forbidden", expect["reply_must_not_match"])

    return failures
