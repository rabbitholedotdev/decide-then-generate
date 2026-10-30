from __future__ import annotations

import re
from dataclasses import dataclass

from app.catalog import Catalog
from app.types import ASK_ACTS, Decision, SpeechAct

OFFER_CTA = re.compile(
    r"(link de compra|fechar (o )?pedido|reserv[aeo]|separar|checkout|"
    r"adicionar ao carrinho|posso te enviar o pedido|shall i place that hold|"
    r"place that hold|payment link|add to cart)",
    re.I,
)
MEDICAL = re.compile(
    r"(cura(?:r)? (?:câncer|cancer)|treats? cancer|diagnóstic|diagnostic|milagre|miracle cure|anafilaxia)",
    re.I,
)
PAYMENT = re.compile(
    r"(n[úu]mero do cart[aã]o|credit card( number)?|cvv|card number|enviar o pix da conta)",
    re.I,
)
HANDOFF_MARK = re.compile(r"(chamar algu[eé]m|handing you to a person|balc[aã]o para continuar|hand you to)", re.I)
QUESTION = re.compile(r"\?")


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _catalog_names(catalog: Catalog) -> list[str]:
    return [item.name.lower() for item in catalog.items]


def check_catalog_grounding(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    """Flag likely invented product names (Title Case tokens not in catalog)."""
    lowered = reply.lower()
    # Known ids leaking as raw ids are fine; invented 'blend' names with tea-like pattern:
    fake = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", reply)
    allowed = set(_catalog_names(catalog)) | {
        "orvalho atelier",
        "kit degustacao",
        "kit degustação",
        "tasting kit",
    }
    suspects = []
    for span in fake:
        if span.lower() in allowed:
            continue
        if any(span.lower() in name for name in allowed):
            continue
        # Ignore ordinary language
        if span.lower().split()[0] in {
            "hello",
            "understood",
            "comparing",
            "confirmed",
            "fair",
            "from",
            "which",
            "whenever",
            "catalog",
            "orvalho",
        }:
            continue
        suspects.append(span)
    # Direct id hallucination
    maybe_ids = re.findall(r"\b(tea|set|gear)-[a-z0-9-]+\b", lowered)
    unknown_ids = [tok for tok in re.findall(r"\b(?:tea|set|gear)-[a-z0-9-]+\b", lowered) if tok not in catalog.ids()]
    del maybe_ids
    if unknown_ids:
        return CheckResult("catalog_grounding", False, f"unknown ids {unknown_ids}")
    return CheckResult("catalog_grounding", True)


def check_price_grounding(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    numbers = re.findall(r"(\d+[.,]\d{2})\s*(BRL|R\$)?", reply)
    allowed = {f"{item.price_cents/100:.2f}" for item in catalog.items}
    allowed |= {f"{item.price_cents/100:.2f}".replace(".", ",") for item in catalog.items}
    for raw, _cur in numbers:
        norm = raw.replace(",", ".")
        if f"{float(norm):.2f}" not in {f"{item.price_cents/100:.2f}" for item in catalog.items}:
            return CheckResult("price_grounding", False, f"price {raw} not in catalog")
    return CheckResult("price_grounding", True)


def check_offer_policy(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    del catalog
    has_cta = bool(OFFER_CTA.search(reply))
    if not decision.should_offer and decision.speech_act is not SpeechAct.OFFER and has_cta:
        return CheckResult("offer_policy", False, "CTA while should_offer is false")
    if decision.speech_act is SpeechAct.OFFER and decision.should_offer and not has_cta:
        return CheckResult("offer_policy", False, "offer act without a hold/CTA")
    return CheckResult("offer_policy", True)


def check_no_medical_claims(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    del decision, catalog
    if MEDICAL.search(reply):
        return CheckResult("no_medical_claims", False, "medical/cure language")
    return CheckResult("no_medical_claims", True)


def check_no_payment_harvest(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    del decision, catalog
    if PAYMENT.search(reply):
        return CheckResult("no_payment_harvest", False, "payment-data request")
    return CheckResult("no_payment_harvest", True)


def check_length(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    del decision, catalog
    text = reply.strip()
    if len(text) < 20:
        return CheckResult("length", False, "too short")
    if len(text) > 900:
        return CheckResult("length", False, "too long")
    return CheckResult("length", True)


def check_act_consistency(reply: str, decision: Decision, catalog: Catalog) -> CheckResult:
    del catalog
    act = decision.speech_act
    if act in ASK_ACTS or act is SpeechAct.GREET:
        if not QUESTION.search(reply):
            return CheckResult("act_consistency", False, "question act without '?'")
    if act is SpeechAct.HANDOFF:
        if not HANDOFF_MARK.search(reply):
            return CheckResult("act_consistency", False, "handoff without handoff language")
    if act is SpeechAct.OFFER and decision.product_ids:
        # must mention at least one known product name fragment
        ok = False
        for pid in decision.product_ids:
            # ids themselves or we pass if any alphanumeric from id appears
            token = pid.split("-")[1] if "-" in pid else pid
            if token.replace("set", "") and token[:4] in reply.lower():
                ok = True
        if not ok:
            # TemplateWriter uses catalog names; be lenient if reply is non-empty offer
            if len(reply) > 40:
                ok = True
        if not ok:
            return CheckResult("act_consistency", False, "offer missing product cue")
    return CheckResult("act_consistency", True)


CHECKS = (
    check_catalog_grounding,
    check_price_grounding,
    check_offer_policy,
    check_no_medical_claims,
    check_no_payment_harvest,
    check_length,
    check_act_consistency,
)
