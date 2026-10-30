"""LLM Decider: model returns JSON, pydantic validates. Writer still does not decide."""

from __future__ import annotations

import json
from typing import Any

from app.decider.mock import MockDecider
from app.models_loader import task_model
from app.openai_client import get_async_openai
from app.types import ACT_TO_STAGE, Decision, TurnContext

DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "speech_act",
        "stage",
        "user_intent",
        "slots_filled",
        "next_slot",
        "should_offer",
        "should_handoff",
        "risk_level",
        "risk_codes",
        "product_ids",
        "objection_type",
        "tone",
        "rag_stage",
        "language",
        "confidence",
        "reason_codes",
        "draft_brief",
    ],
    "properties": {
        "speech_act": {
            "type": "string",
            "enum": [
                "greet",
                "ask_need",
                "ask_occasion",
                "ask_taste",
                "ask_caffeine",
                "ask_budget",
                "ask_experience",
                "educate",
                "recommend",
                "compare",
                "offer",
                "handle_objection",
                "confirm",
                "handoff",
                "close",
            ],
        },
        "stage": {
            "type": "string",
            "enum": ["discovery", "educate", "recommend", "offer", "handoff"],
        },
        "user_intent": {"type": "string"},
        "slots_filled": {"type": "object", "additionalProperties": {"type": "string"}},
        "next_slot": {"type": ["string", "null"]},
        "should_offer": {"type": "boolean"},
        "should_handoff": {"type": "boolean"},
        "risk_level": {"type": "string", "enum": ["none", "low", "high"]},
        "risk_codes": {"type": "array", "items": {"type": "string"}},
        "product_ids": {"type": "array", "items": {"type": "string"}},
        "objection_type": {"type": ["string", "null"]},
        "tone": {"type": "string", "enum": ["warm", "neutral", "careful"]},
        "rag_stage": {
            "type": "string",
            "enum": ["discovery", "educate", "recommend", "offer", "handoff"],
        },
        "language": {"type": "string", "enum": ["pt-BR", "en"]},
        "confidence": {"type": "number"},
        "reason_codes": {"type": "array", "items": {"type": "string"}},
        "draft_brief": {"type": "string"},
    },
}

SYSTEM = """You are the Decider, not the shop voice.
Fill the typed decision form for this turn. Do not write the customer-facing reply.
Honor policy:
- product_ids must come from the catalog id list
- should_offer true only when enough slots are filled and speech_act is offer
- should_handoff / risk_level=high for legal, payment-data, medical, or uncontainable anger
- one next_slot among: need, occasion, taste, caffeine, budget, experience
Return JSON only matching this schema:
""" + json.dumps(DECISION_JSON_SCHEMA)


class LlmJsonDecider:
    name = "llm_json"

    def __init__(self, client=None, fallback: MockDecider | None = None):
        self._client = client
        self._fallback = fallback or MockDecider()

    async def decide(self, ctx: TurnContext) -> Decision:
        spec = task_model("decide")
        client = self._client or get_async_openai()
        payload = {
            "turn": ctx.state.turn,
            "slots": ctx.state.slots,
            "last_offer_turn": ctx.state.last_offer_turn,
            "offers_made": ctx.state.offers_made,
            "handed_off": ctx.state.handed_off,
            "catalog_ids": ctx.catalog_ids,
            "user_message": ctx.user_message,
            "recent_transcript": [m.model_dump() for m in ctx.state.transcript[-6:]],
        }
        try:
            response = await client.chat.completions.create(
                model=spec.model,
                temperature=spec.temperature,
                max_tokens=spec.max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            decision = Decision.model_validate(data)
            decision.stage = ACT_TO_STAGE.get(decision.speech_act, decision.stage)
            decision.rag_stage = decision.stage
            decision.product_ids = [pid for pid in decision.product_ids if pid in set(ctx.catalog_ids)]
            decision.reason_codes = [*decision.reason_codes, "decider:llm_json"]
            return decision
        except Exception:
            fallback = await self._fallback.decide(ctx)
            fallback.reason_codes = [*fallback.reason_codes, "decider:llm_json_fallback"]
            return fallback
