from __future__ import annotations

import pytest

from app.eval.judge import MockJudge
from app.eval.runner import run_eval
from app.orchestrator import Assistant
from app.sessions import MemorySessionStore


@pytest.mark.asyncio
async def test_gold_eval_passes_with_mock_judge(assistant: Assistant):
    report = await run_eval(assistant=assistant, judge=MockJudge())
    assert report["passed"], report["hard_failures"]
    assert report["n_cases"] == 4
    assert report["prompt_version"].startswith("sha256:")
    assert report["judge"] == "mock"
    versions = {
        turn["prompt_version"] for case in report["cases"] for turn in case["turns"]
    }
    assert versions == {report["prompt_version"]}


@pytest.mark.asyncio
async def test_eval_uses_fresh_sessions_per_case(assistant: Assistant):
    assistant.sessions = MemorySessionStore()
    report = await run_eval(assistant=assistant)
    handoff = next(c for c in report["cases"] if c["id"] == "handoff_legal")
    assert handoff["turns"][0]["should_handoff"] is True
    discovery = next(c for c in report["cases"] if c["id"] == "no_offer_first_four")
    assert all(t["should_offer"] is False for t in discovery["turns"])
