"""Deterministic typed Decider. No LLM. Used in tests and the default demo path."""

from __future__ import annotations

from app.catalog import Catalog, default_catalog
from app.types import (
    ASK_ACTS,
    SLOT_ORDER,
    ACT_TO_STAGE,
    Decision,
    Language,
    RiskLevel,
    SpeechAct,
    Tone,
    TurnContext,
)

GIFT_WORDS = ("presente", "gift", "aniversário", "aniversario", "natal", "birthday")
SELF_WORDS = ("pra mim", "para mim", "for me", "uso próprio", "uso proprio")
GREEN = ("verde", "green", "sencha", "gramin")
BLACK = ("preto", "black", "darjeeling")
OOLONG = ("oolong", "wulong", "tieguan")
HERBAL = ("ervas", "herbal", "camomila", "chamomile", "rooibos")
CAFFEINE_FREE = ("sem cafeína", "sem cafeina", "decaf", "caffeine-free", "sem cafe")
LOW_CAFFEINE = ("pouca cafeína", "pouca cafeina", "low caffeine", "à noite", "a noite", "evening")
WANTS_CAFFEINE = ("com cafeína", "com cafeina", "preciso acordar", "morning")
BEGINNER = ("iniciante", "beginner", "nunca tomei", "nunca tomei chá", "nunca tomei cha")
EXPERIENCED = ("experiente", "já tomo", "ja tomo", "gyokuro", "gongfu")
BUDGET_LOW = ("barato", "até 40", "ate 40", "cheap", "econômico", "economico")
BUDGET_MID = ("até 90", "ate 90", "médio", "medio")
BUDGET_HIGH = ("pode ser caro", "acima de 90", "chaleira", "kettle", "investir")
BUY_WORDS = ("quero esse", "vou levar", "fecha", "pode separar", "i'll take", "ill take", "buy")
BYE_WORDS = ("tchau", "obrigado", "obrigada", "thanks", "bye", "é só isso", "e so isso")
COMPARE_WORDS = ("diferença", "diferenca", "compare", "versus", "vs ")
EDUCATE_WORDS = ("como preparar", "como fazer", "infusão", "infusao", "brew", "temperatura")
ANGRY = ("absurdo", "péssimo", "pessimo", "incompetent", "ridículo", "ridiculo")
LEGAL = ("advogado", "lawyer", "procon", "processar", "lawsuit", "indenização", "indenizacao")
PAYMENT = ("número do cartão", "numero do cartao", "credit card", "cvv", "card number")
MEDICAL = (
    "cura cancer",
    "cura câncer",
    "treat cancer",
    "diagnóstico",
    "diagnostico",
    "alergia grave",
    "anafilaxia",
)
OBJECTION_PRICE = ("caro", "expensive", "não tenho", "nao tenho")
OBJECTION_TIME = ("não tenho tempo", "nao tenho tempo", "complicado")

ASK_FOR_SLOT = {
    "need": SpeechAct.ASK_NEED,
    "occasion": SpeechAct.ASK_OCCASION,
    "taste": SpeechAct.ASK_TASTE,
    "caffeine": SpeechAct.ASK_CAFFEINE,
    "budget": SpeechAct.ASK_BUDGET,
    "experience": SpeechAct.ASK_EXPERIENCE,
}


def detect_language(text: str, fallback: Language) -> Language:
    lowered = text.lower()
    pt_hits = sum(
        w in lowered
        for w in ("não", "nao", "chá", "cha", "presente", "quero", "você", "voce", "obrigado")
    )
    en_hits = sum(w in lowered for w in ("the", "please", "tea", "gift", "hello", "thanks"))
    if pt_hits > en_hits:
        return Language.PT_BR
    if en_hits > pt_hits:
        return Language.EN
    return fallback


def detect_risk(text: str) -> tuple[RiskLevel, list[str]]:
    lowered = text.lower()
    codes: list[str] = []
    if any(w in lowered for w in LEGAL):
        codes.append("legal")
    if any(w in lowered for w in PAYMENT):
        codes.append("payment_data")
    if any(w in lowered for w in MEDICAL):
        codes.append("medical")
    if any(w in lowered for w in ANGRY):
        codes.append("anger")
    high = {"legal", "payment_data", "medical"}
    if high.intersection(codes):
        return RiskLevel.HIGH, codes
    if codes:
        return RiskLevel.LOW, codes
    return RiskLevel.NONE, []


def extract_slots(message: str, prior: dict[str, str]) -> dict[str, str]:
    slots = dict(prior)
    lowered = message.lower()
    if any(w in lowered for w in GIFT_WORDS):
        slots["occasion"] = "gift"
        slots.setdefault("need", "tea")
    elif any(w in lowered for w in SELF_WORDS):
        slots["occasion"] = "self"
        slots.setdefault("need", "tea")
    if any(w in lowered for w in GREEN):
        slots["taste"] = "green"
        slots.setdefault("need", "tea")
    elif any(w in lowered for w in BLACK):
        slots["taste"] = "black"
        slots.setdefault("need", "tea")
    elif any(w in lowered for w in OOLONG):
        slots["taste"] = "oolong"
        slots.setdefault("need", "tea")
    elif any(w in lowered for w in HERBAL):
        slots["taste"] = "herbal"
        slots.setdefault("need", "tea")
    if any(w in lowered for w in CAFFEINE_FREE):
        slots["caffeine"] = "none"
    elif any(w in lowered for w in LOW_CAFFEINE):
        slots["caffeine"] = "low"
    elif any(w in lowered for w in WANTS_CAFFEINE):
        slots["caffeine"] = "regular"
    if any(w in lowered for w in BEGINNER):
        slots["experience"] = "beginner"
    elif any(w in lowered for w in EXPERIENCED):
        slots["experience"] = "experienced"
    if any(w in lowered for w in BUDGET_HIGH):
        slots["budget"] = "high"
    elif any(w in lowered for w in BUDGET_MID):
        slots["budget"] = "mid"
    elif any(w in lowered for w in BUDGET_LOW):
        slots["budget"] = "low"
    if "chá" in lowered or "cha" in lowered or "tea" in lowered:
        slots.setdefault("need", "tea")
    if "chaleira" in lowered or "kettle" in lowered:
        slots["need"] = "gear"
    return slots


def next_missing_slot(slots: dict[str, str]) -> str | None:
    for key in SLOT_ORDER:
        if not slots.get(key):
            return key
    return None


def pick_products(slots: dict[str, str], catalog: Catalog) -> list[str]:
    occasion = slots.get("occasion")
    taste = slots.get("taste")
    caffeine = slots.get("caffeine")
    experience = slots.get("experience")
    budget = slots.get("budget")
    need = slots.get("need")

    if need == "gear" or budget == "high":
        return ["gear-kettle"]
    if occasion == "gift" and experience == "beginner":
        return ["set-gift-starter"]
    if experience == "beginner" and not taste:
        return ["set-tasting-3"]
    if caffeine == "none":
        return ["tea-chamomile-30"] if occasion == "gift" else ["tea-rooibos-40"]
    if caffeine == "low":
        return ["tea-houjicha-50"]
    if taste == "green":
        return ["tea-sencha-50"]
    if taste == "black":
        return ["tea-darjeeling-50"]
    if taste == "oolong":
        return ["tea-tieguanyin-40"]
    if taste == "herbal":
        return ["tea-chamomile-30"]
    if occasion == "gift":
        return ["set-tasting-3"]
    known = catalog.ids()
    return [pid for pid in ["set-tasting-3"] if pid in known]


def _filled_count(slots: dict[str, str]) -> int:
    return sum(1 for key in SLOT_ORDER if slots.get(key))


class MockDecider:
    name = "mock"

    def __init__(self, catalog: Catalog | None = None):
        self.catalog = catalog or default_catalog()

    async def decide(self, ctx: TurnContext) -> Decision:
        text = ctx.user_message
        language = detect_language(text, ctx.state.language)
        risk_level, risk_codes = detect_risk(text)
        slots = extract_slots(text, ctx.state.slots)
        lowered = text.lower()

        if risk_level is RiskLevel.HIGH or ctx.state.handed_off:
            act = SpeechAct.HANDOFF
            products: list[str] = []
            nxt = None
            brief = "Acknowledge the risk, stop selling, hand to a human."
            reasons = ["risk:high"] + risk_codes
        elif any(w in lowered for w in BYE_WORDS) and _filled_count(slots) >= 0:
            act = SpeechAct.CLOSE
            products = []
            nxt = None
            brief = "Thank them and close without a new question."
            reasons = ["user:bye"]
        elif any(w in lowered for w in BUY_WORDS) and _filled_count(slots) >= 2:
            act = SpeechAct.CONFIRM
            products = pick_products(slots, self.catalog)[:1]
            nxt = None
            brief = "Confirm the chosen item and the hold-at-counter next step."
            reasons = ["user:commit"]
        elif any(w in lowered for w in EDUCATE_WORDS):
            act = SpeechAct.EDUCATE
            products = pick_products(slots, self.catalog)[:1]
            nxt = next_missing_slot(slots)
            brief = "Give brewing notes from retrieved context only."
            reasons = ["user:how_to"]
        elif any(w in lowered for w in COMPARE_WORDS):
            act = SpeechAct.COMPARE
            products = pick_products(slots, self.catalog)[:2]
            if len(products) < 2:
                products = ["tea-sencha-50", "tea-houjicha-50"]
            nxt = next_missing_slot(slots)
            brief = "Compare the two catalog items on taste and caffeine."
            reasons = ["user:compare"]
        elif any(w in lowered for w in OBJECTION_PRICE) and _filled_count(slots) >= 3:
            act = SpeechAct.HANDLE_OBJECTION
            products = ["set-tasting-3"]
            nxt = None
            brief = "Address price with the tasting kit. Do not discount invented SKUs."
            reasons = ["objection:price"]
        elif any(w in lowered for w in OBJECTION_TIME):
            act = SpeechAct.HANDLE_OBJECTION
            products = pick_products(slots, self.catalog)[:1]
            nxt = None
            brief = "Address time: tasting kit or a single easy tin."
            reasons = ["objection:time"]
        elif ctx.state.turn <= 1 and not ctx.state.transcript:
            act = SpeechAct.GREET
            products = []
            nxt = "need"
            brief = "Greet once and ask what they are looking for."
            reasons = ["open:greet"]
            slots.setdefault("need", "")
        else:
            nxt = next_missing_slot(slots)
            ready = _filled_count(slots) >= 3
            if ready:
                products = pick_products(slots, self.catalog)
                # Mock still *proposes* offer when ready; state machine may demote.
                if ctx.state.turn > 4 and ctx.state.offers_made < 2:
                    act = SpeechAct.OFFER
                    brief = "Offer a concrete next step on the named catalog item(s)."
                    reasons = ["ready:offer"]
                else:
                    act = SpeechAct.RECOMMEND
                    brief = "Recommend at most two catalog items. No purchase CTA."
                    reasons = ["ready:recommend"]
            elif nxt:
                act = ASK_FOR_SLOT[nxt]
                products = []
                brief = f"Ask only for slot {nxt}."
                reasons = [f"slot:missing:{nxt}"]
            else:
                act = SpeechAct.RECOMMEND
                products = pick_products(slots, self.catalog)
                nxt = None
                brief = "Recommend from filled slots."
                reasons = ["ready:slots_full"]

        products = self.catalog.filter_ids(products)
        stage = ACT_TO_STAGE[act]
        should_offer = act is SpeechAct.OFFER
        should_handoff = act is SpeechAct.HANDOFF
        tone = Tone.CAREFUL if risk_level is not RiskLevel.NONE else Tone.WARM
        if act in ASK_ACTS:
            confidence = 0.9
        elif act is SpeechAct.HANDOFF:
            confidence = 0.95
        else:
            confidence = 0.75

        # Keep empty strings out of slots_filled
        clean_slots = {k: v for k, v in slots.items() if v}

        return Decision(
            speech_act=act,
            stage=stage,
            user_intent=_intent(act, clean_slots),
            slots_filled=clean_slots,
            next_slot=nxt if act in ASK_ACTS or act is SpeechAct.GREET else None,
            should_offer=should_offer,
            should_handoff=should_handoff,
            risk_level=risk_level,
            risk_codes=risk_codes,
            product_ids=products,
            objection_type=_objection(act, reasons),
            tone=tone,
            rag_stage=stage,
            language=language,
            confidence=confidence,
            reason_codes=reasons,
            draft_brief=brief,
        )


def _intent(act: SpeechAct, slots: dict[str, str]) -> str:
    if act is SpeechAct.HANDOFF:
        return "escalate"
    if act is SpeechAct.OFFER:
        return "ready_to_offer"
    if act is SpeechAct.RECOMMEND:
        return "ready_to_recommend"
    if act in ASK_ACTS or act is SpeechAct.GREET:
        return "discover"
    if act is SpeechAct.EDUCATE:
        return "learn"
    if act is SpeechAct.CLOSE:
        return "exit"
    if act is SpeechAct.CONFIRM:
        return "commit"
    return act.value


def _objection(act: SpeechAct, reasons: list[str]) -> str | None:
    if act is not SpeechAct.HANDLE_OBJECTION:
        return None
    for reason in reasons:
        if reason.startswith("objection:"):
            return reason.split(":", 1)[1]
        return "unspecified"
