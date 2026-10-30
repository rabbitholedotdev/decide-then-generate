from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.catalog import Catalog
from app.generate.layers import frozen_prefix
from app.types import Chunk, Decision, SessionState

PROMPT_HASH_ALGO = "sha256"


def prefix_bytes() -> bytes:
    return frozen_prefix().encode("utf-8")


def prompt_version(prefix: bytes | None = None) -> str:
    digest = hashlib.sha256(prefix if prefix is not None else prefix_bytes()).hexdigest()
    return f"{PROMPT_HASH_ALGO}:{digest}"


@dataclass(frozen=True)
class PromptBundle:
    prefix: str
    layer_retrieve: str
    layer_decision: str
    layer_transcript: str
    version: str

    @property
    def prefix_bytes(self) -> bytes:
        return self.prefix.encode("utf-8")

    @property
    def dynamic(self) -> str:
        return "\n\n".join([self.layer_retrieve, self.layer_decision, self.layer_transcript])

    @property
    def full(self) -> str:
        return self.prefix + "\n\n" + self.dynamic

    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.prefix},
            {"role": "user", "content": self.dynamic},
        ]


def _layer_retrieve(chunks: list[Chunk], catalog: Catalog, product_ids: list[str]) -> str:
    texts = "\n\n".join(chunk.text.strip() for chunk in chunks) or "(no retrieval)"
    focus = catalog.render_for_prompt(product_ids) if product_ids else catalog.render_for_prompt()
    return (
        "Layer 3 — retrieved context (stage RAG + catalog excerpts):\n"
        f"{texts}\n\n"
        f"Catalog rows you may name:\n{focus}"
    )


def _layer_decision(decision: Decision) -> str:
    packet = json.dumps(decision.compact(), ensure_ascii=False, indent=2)
    return (
        "Layer 4 — Decision packet (obey; do not second-guess):\n"
        f"{packet}\n"
        f"Draft brief: {decision.draft_brief}"
    )


def _layer_transcript(state: SessionState, user_message: str) -> str:
    lines = []
    for msg in state.transcript[-8:]:
        lines.append(f"{msg.role}: {msg.content}")
    lines.append(f"user: {user_message}")
    body = "\n".join(lines)
    return "Layer 5 — transcript and current utterance:\n" + body


def build_prompt(
    *,
    state: SessionState,
    user_message: str,
    decision: Decision,
    chunks: list[Chunk],
    catalog: Catalog,
) -> PromptBundle:
    prefix = frozen_prefix()
    return PromptBundle(
        prefix=prefix,
        layer_retrieve=_layer_retrieve(chunks, catalog, decision.product_ids),
        layer_decision=_layer_decision(decision),
        layer_transcript=_layer_transcript(state, user_message),
        version=prompt_version(prefix.encode("utf-8")),
    )
