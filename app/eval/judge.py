from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.types import Decision


@dataclass
class JudgeScore:
    coherence: float
    faithfulness: float
    rationale: str
    name: str = "mock"

    def compact(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "coherence": self.coherence,
            "faithfulness": self.faithfulness,
            "rationale": self.rationale,
        }


class Judge(Protocol):
    name: str

    async def score(self, *, case_id: str, user: str, reply: str, decision: Decision) -> JudgeScore:
        ...


class MockJudge:
    """Deterministic judge for CI. Swap for LlmJudge when an API key exists."""

    name = "mock"

    async def score(self, *, case_id: str, user: str, reply: str, decision: Decision) -> JudgeScore:
        del case_id, user
        coherent = 1.0 if len(reply) >= 20 else 0.0
        faithful = 1.0 if decision.speech_act.value in reply.lower() or len(reply) >= 20 else 0.6
        return JudgeScore(
            coherence=coherent,
            faithfulness=faithful,
            rationale="mock judge: length and non-empty reply",
            name=self.name,
        )


class LlmJudge:
    name = "llm"

    def __init__(self, client=None):
        self._client = client

    async def score(self, *, case_id: str, user: str, reply: str, decision: Decision) -> JudgeScore:
        from app.models_loader import task_model
        from app.openai_client import get_async_openai

        spec = task_model("judge")
        client = self._client or get_async_openai()
        prompt = (
            "Score coherence and catalog faithfulness 0-1. JSON "
            '{"coherence":0.0,"faithfulness":0.0,"rationale":"..."}\n'
            f"case={case_id}\nuser={user}\nact={decision.speech_act}\nreply={reply}"
        )
        response = await client.chat.completions.create(
            model=spec.model,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        import json

        data = json.loads(response.choices[0].message.content or "{}")
        return JudgeScore(
            coherence=float(data.get("coherence", 0)),
            faithfulness=float(data.get("faithfulness", 0)),
            rationale=str(data.get("rationale", "")),
            name=self.name,
        )
