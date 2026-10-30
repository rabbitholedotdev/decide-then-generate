from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.catalog import Catalog, default_catalog
from app.decider.mock import MockDecider
from app.decider.protocol import Decider
from app.generate.prompt import PromptBundle, build_prompt
from app.generate.writer import TemplateWriter, Writer
from app.guard.pipeline import GuardReport, run_guard
from app.rag.fixtures import FixtureRetriever
from app.rag.protocol import Retriever
from app.sessions import STORE, MemorySessionStore
from app.settings import Settings, get_settings
from app.state_machine import apply_turn_bookkeeping, enforce
from app.types import Decision, SessionState, TurnContext


@dataclass
class TurnResult:
    session_id: str
    reply: str
    decision: Decision
    prompt_version: str
    guard: GuardReport
    retriever: str
    decider: str
    writer: str

    def compact(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "reply": self.reply,
            "prompt_version": self.prompt_version,
            "decision": self.decision.compact(),
            "guard": self.guard.compact(),
            "retriever": self.retriever,
            "decider": self.decider,
            "writer": self.writer,
        }


class Assistant:
    def __init__(
        self,
        *,
        decider: Decider | None = None,
        writer: Writer | None = None,
        retriever: Retriever | None = None,
        catalog: Catalog | None = None,
        sessions: MemorySessionStore | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.catalog = catalog or default_catalog()
        self.decider = decider or MockDecider(self.catalog)
        self.writer = writer or TemplateWriter(self.catalog)
        self.retriever = retriever or FixtureRetriever(self.settings.rag_dir)
        self.sessions = sessions or STORE

    async def turn(self, message: str, session_id: str | None = None) -> TurnResult:
        sid = session_id or self.sessions.new_id()
        state = self.sessions.get(sid)
        state.turn += 1
        ctx = TurnContext(
            state=state,
            user_message=message,
            catalog_ids=sorted(self.catalog.ids()),
        )
        raw_decision = await self.decider.decide(ctx)
        decision = enforce(state, raw_decision, self.settings)
        chunks = self.retriever.retrieve(decision.rag_stage, message)
        bundle = build_prompt(
            state=state,
            user_message=message,
            decision=decision,
            chunks=chunks,
            catalog=self.catalog,
        )
        draft = await self.writer.write(bundle, decision)

        async def regen(violations: str) -> str:
            repaired = PromptBundle(
                prefix=bundle.prefix,
                layer_retrieve=bundle.layer_retrieve,
                layer_decision=bundle.layer_decision,
                layer_transcript=bundle.layer_transcript + "\n\nFix violations:\n" + violations,
                version=bundle.version,
            )
            return await self.writer.write(repaired, decision)

        reply, report = await run_guard(
            reply=draft,
            decision=decision,
            catalog=self.catalog,
            regenerate=regen,
        )
        apply_turn_bookkeeping(state, decision, message, reply)
        self.sessions.put(state)
        return TurnResult(
            session_id=sid,
            reply=reply,
            decision=decision,
            prompt_version=bundle.version,
            guard=report,
            retriever=self.retriever.name,
            decider=getattr(self.decider, "name", "decider"),
            writer=getattr(self.writer, "name", "writer"),
        )


def default_assistant() -> Assistant:
    from app.decider.protocol import build_decider
    from app.generate.writer import build_writer
    from app.rag.protocol import build_retriever

    settings = get_settings()
    catalog = default_catalog()
    return Assistant(
        decider=build_decider(settings),
        writer=build_writer(settings),
        retriever=build_retriever(settings),
        catalog=catalog,
        settings=settings,
    )
