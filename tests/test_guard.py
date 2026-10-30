from __future__ import annotations

import pytest

from app.catalog import default_catalog
from app.guard.checks import CHECKS
from app.guard.pipeline import evaluate, run_guard
from app.types import Decision, SpeechAct, Stage


def _decision(**kwargs) -> Decision:
    data = dict(
        speech_act=SpeechAct.RECOMMEND,
        stage=Stage.RECOMMEND,
        should_offer=False,
        rag_stage=Stage.RECOMMEND,
        product_ids=["set-tasting-3"],
        draft_brief="recommend",
    )
    data.update(kwargs)
    return Decision(**data)


def test_seven_named_checks():
    assert len(CHECKS) == 7
    names = [fn.__name__.replace("check_", "") for fn in CHECKS]
    assert names == [
        "catalog_grounding",
        "price_grounding",
        "offer_policy",
        "no_medical_claims",
        "no_payment_harvest",
        "length",
        "act_consistency",
    ]


def test_clean_recommend_passes():
    catalog = default_catalog()
    reply = (
        "Com o que você me contou, eu indicaria Kit degustacao (3 amostras) (39.00 BRL). "
        "Sem fechar nada ainda — isso te atende?"
    )
    report = evaluate(reply, _decision(), catalog)
    assert report.passed, report.violations


def test_invented_price_fails():
    catalog = default_catalog()
    reply = "O Sencha Uji 50g sai por 99.99 BRL hoje, top?"
    report = evaluate(reply, _decision(product_ids=["tea-sencha-50"]), catalog)
    assert not report.passed
    assert any(v.startswith("price_grounding") for v in report.violations)


def test_cta_blocked_when_should_not_offer():
    catalog = default_catalog()
    reply = "Adiciona ao checkout e faz o link de compra agora?"
    report = evaluate(reply, _decision(), catalog)
    assert any("offer_policy" in v for v in report.violations)


def test_medical_and_payment_blocked():
    catalog = default_catalog()
    medical = evaluate("Este chá cura câncer em duas semanas, quer?", _decision(), catalog)
    assert any("no_medical_claims" in v for v in medical.violations)
    payment = evaluate("Me passa o número do cartão e o cvv para eu cobrar.", _decision(), catalog)
    assert any("no_payment_harvest" in v for v in payment.violations)


@pytest.mark.asyncio
async def test_single_regeneration_then_pass():
    catalog = default_catalog()
    decision = _decision(speech_act=SpeechAct.ASK_TASTE, stage=Stage.DISCOVERY, product_ids=[])
    calls = {"n": 0}

    async def regen(_violations: str) -> str:
        calls["n"] += 1
        return "Você prefere verde, preto, oolong ou uma infusão sem cafeína?"

    reply, report = await run_guard(
        reply="ok",
        decision=decision,
        catalog=catalog,
        regenerate=regen,
    )
    assert calls["n"] == 1
    assert report.regenerated is True
    assert report.passed is True
    assert "?" in reply


@pytest.mark.asyncio
async def test_second_failure_uses_fallback():
    catalog = default_catalog()
    decision = _decision()

    async def regen(_violations: str) -> str:
        return "x"

    reply, report = await run_guard(
        reply="x",
        decision=decision,
        catalog=catalog,
        regenerate=regen,
    )
    assert report.regenerated is True
    assert len(reply) >= 20
    assert "catálogo" in reply.lower() or "catalog" in reply.lower()
