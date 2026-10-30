from __future__ import annotations

import hashlib

from app.catalog import default_catalog
from app.generate.layers import frozen_prefix, IDENTITY, POLICY
from app.generate.prompt import build_prompt, prefix_bytes, prompt_version
from app.rag.fixtures import FixtureRetriever
from app.types import Decision, Language, RiskLevel, SessionState, SpeechAct, Stage, Tone


def _decision(act: SpeechAct, turn_note: str) -> Decision:
    return Decision(
        speech_act=act,
        stage=Stage.DISCOVERY,
        user_intent="discover",
        draft_brief=turn_note,
        language=Language.PT_BR,
        risk_level=RiskLevel.NONE,
        tone=Tone.WARM,
        rag_stage=Stage.DISCOVERY,
    )


def test_prefix_is_identity_plus_policy():
    expected = (IDENTITY + "\n\n" + POLICY).encode("utf-8")
    assert prefix_bytes() == expected
    assert frozen_prefix().encode("utf-8") == expected


def test_prompt_version_is_sha256_of_prefix():
    digest = hashlib.sha256(prefix_bytes()).hexdigest()
    assert prompt_version() == f"sha256:{digest}"


def test_prefix_byte_identical_across_turns():
    catalog = default_catalog()
    retriever = FixtureRetriever()
    state_a = SessionState(session_id="a", turn=1)
    state_b = SessionState(session_id="a", turn=4)
    chunks = retriever.retrieve(Stage.DISCOVERY, "oi")
    p1 = build_prompt(
        state=state_a,
        user_message="oi",
        decision=_decision(SpeechAct.GREET, "greet"),
        chunks=chunks,
        catalog=catalog,
    )
    p2 = build_prompt(
        state=state_b,
        user_message="ela gosta de verde",
        decision=_decision(SpeechAct.ASK_TASTE, "ask"),
        chunks=retriever.retrieve(Stage.RECOMMEND, "verde"),
        catalog=catalog,
    )
    assert p1.prefix_bytes == p2.prefix_bytes
    assert p1.prefix_bytes == prefix_bytes()
    assert p1.version == p2.version == prompt_version()
    assert p1.dynamic != p2.dynamic


def test_policy_edit_would_change_version():
    original = prefix_bytes()
    mutated = original + b"\n# extra"
    assert prompt_version(mutated) != prompt_version(original)
