from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.catalog import default_catalog
from app.eval.hard import HardFailure, run_hard_checks
from app.eval.judge import Judge, MockJudge
from app.generate.prompt import prompt_version
from app.orchestrator import Assistant
from app.sessions import MemorySessionStore
from app.settings import ROOT


def load_gold(path: Path | None = None) -> list[dict[str, Any]]:
    gold_path = path or (ROOT / "fixtures" / "eval" / "gold.json")
    return json.loads(gold_path.read_text(encoding="utf-8"))


async def run_eval(
    *,
    assistant: Assistant | None = None,
    judge: Judge | None = None,
    gold: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    catalog = default_catalog()
    gold_cases = gold if gold is not None else load_gold()
    inst = assistant or Assistant(sessions=MemorySessionStore())
    scored_by = judge or MockJudge()
    version = prompt_version()
    failures: list[HardFailure] = []
    cases_out: list[dict[str, Any]] = []

    for case in gold_cases:
        store = MemorySessionStore()
        inst.sessions = store
        sid = store.new_id()
        turns_out = []
        for idx, step in enumerate(case["turns"], start=1):
            result = await inst.turn(step["user"], session_id=sid)
            expect = step.get("expect") or {}
            hard = run_hard_checks(
                case_id=case["id"],
                turn=idx,
                decision=result.decision,
                reply=result.reply,
                catalog=catalog,
                expect=expect,
                prompt_version=result.prompt_version,
                expected_version=version,
            )
            failures.extend(hard)
            judge_score = await scored_by.score(
                case_id=case["id"],
                user=step["user"],
                reply=result.reply,
                decision=result.decision,
            )
            turns_out.append(
                {
                    "turn": idx,
                    "user": step["user"],
                    "reply": result.reply,
                    "speech_act": result.decision.speech_act.value,
                    "should_offer": result.decision.should_offer,
                    "should_handoff": result.decision.should_handoff,
                    "reason_codes": result.decision.reason_codes,
                    "prompt_version": result.prompt_version,
                    "guard": result.guard.compact(),
                    "judge": judge_score.compact(),
                    "hard_failures": [f.check + ": " + f.detail for f in hard],
                }
            )
        cases_out.append({"id": case["id"], "turns": turns_out})

    passed = not failures
    report = {
        "passed": passed,
        "prompt_version": version,
        "hard_failures": [
            {"case": f.case_id, "turn": f.turn, "check": f.check, "detail": f.detail} for f in failures
        ],
        "cases": cases_out,
        "judge": getattr(scored_by, "name", "judge"),
        "n_cases": len(cases_out),
        "n_hard_failures": len(failures),
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Eval report",
        f"- passed: **{report['passed']}**",
        f"- prompt_version: `{report['prompt_version']}`",
        f"- cases: {report['n_cases']}",
        f"- hard failures: {report['n_hard_failures']}",
        f"- judge: {report['judge']}",
        "",
    ]
    if report["hard_failures"]:
        lines.append("## Hard failures")
        for fail in report["hard_failures"]:
            lines.append(f"- {fail['case']} t{fail['turn']}: {fail['check']} — {fail['detail']}")
        lines.append("")
    lines.append("## Cases")
    for case in report["cases"]:
        lines.append(f"### {case['id']}")
        for turn in case["turns"]:
            lines.append(
                f"- t{turn['turn']} act={turn['speech_act']} offer={turn['should_offer']} "
                f"handoff={turn['should_handoff']}"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run synthetic-gold eval")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    import asyncio

    report = asyncio.run(run_eval())
    print(render_markdown(report))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
