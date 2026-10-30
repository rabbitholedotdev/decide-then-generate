from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import ChatIn, ChatOut, GuardOut, HealthOut, get_assistant
from app.catalog import default_catalog
from app.generate.prompt import prompt_version
from app.orchestrator import Assistant
from app.decider.llm_json import DECISION_JSON_SCHEMA
from app.types import Decision, SpeechAct, Stage

STATIC = Path(__file__).resolve().parent / "static"


def create_app(assistant: Assistant | None = None) -> FastAPI:
    app = FastAPI(
        title="decide-then-generate",
        version=__version__,
        description="Structured Decider chooses; the writer only drafts. Fictional tea counter.",
    )
    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")

    def current() -> Assistant:
        return assistant or get_assistant()

    @app.get("/", response_class=HTMLResponse)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:
        inst = current()
        return HealthOut(
            status="ok",
            prompt_version=prompt_version(),
            decider=getattr(inst.decider, "name", "?"),
            retriever=inst.retriever.name,
            writer=getattr(inst.writer, "name", "?"),
            catalog_size=len(inst.catalog.items),
        )

    @app.get("/v1/catalog")
    def catalog() -> dict:
        cat = default_catalog()
        return {
            "shop": cat.shop_name,
            "items": [item.model_dump() for item in cat.items],
        }

    @app.get("/v1/schema")
    def schema() -> dict:
        return {
            "speech_acts": [a.value for a in SpeechAct],
            "stages": [s.value for s in Stage],
            "decision_fields": list(Decision.model_fields.keys()),
            "json_schema": DECISION_JSON_SCHEMA,
        }

    @app.post("/v1/chat", response_model=ChatOut)
    async def chat(body: ChatIn) -> ChatOut:
        result = await current().turn(body.message, body.session_id)
        return ChatOut(
            session_id=result.session_id,
            reply=result.reply,
            prompt_version=result.prompt_version,
            speech_act=result.decision.speech_act.value,
            stage=result.decision.stage.value,
            should_offer=result.decision.should_offer,
            should_handoff=result.decision.should_handoff,
            product_ids=result.decision.product_ids,
            reason_codes=result.decision.reason_codes,
            guard=GuardOut(
                passed=result.guard.passed,
                regenerated=result.guard.regenerated,
                violations=result.guard.violations,
            ),
            decider=result.decider,
            retriever=result.retriever,
            writer=result.writer,
            decision=result.decision,
        )

    return app


app = create_app()
