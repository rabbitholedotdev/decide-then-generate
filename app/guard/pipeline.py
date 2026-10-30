from __future__ import annotations

from dataclasses import dataclass, field

from app.catalog import Catalog
from app.guard.checks import CHECKS, CheckResult
from app.types import Decision


@dataclass
class GuardReport:
    passed: bool
    regenerated: bool
    checks: list[CheckResult] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    def compact(self) -> dict:
        return {
            "passed": self.passed,
            "regenerated": self.regenerated,
            "violations": self.violations,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks],
        }


def evaluate(reply: str, decision: Decision, catalog: Catalog) -> GuardReport:
    checks = [fn(reply, decision, catalog) for fn in CHECKS]
    violations = [f"{c.name}: {c.detail}" for c in checks if not c.ok]
    return GuardReport(passed=not violations, regenerated=False, checks=checks, violations=violations)


def fallback_reply(decision: Decision) -> str:
    if decision.should_handoff:
        return (
            "Entendi. Vou chamar alguém do balcão para continuar com você. "
            "Não vou seguir com venda por aqui."
        )
    if decision.should_offer:
        return "Posso separar o item combinado no balcão para você levar hoje. Quer que eu faça essa reserva?"
    return (
        "Posso te orientar só com o catálogo da casa. Me diz o que você busca — "
        "chá do dia a dia, presente ou preparo?"
    )


async def run_guard(
    *,
    reply: str,
    decision: Decision,
    catalog: Catalog,
    regenerate,
) -> tuple[str, GuardReport]:
    """At most one regeneration, then a canned safe fallback."""
    report = evaluate(reply, decision, catalog)
    if report.passed:
        return reply, report
    repaired = await regenerate("; ".join(report.violations))
    second = evaluate(repaired, decision, catalog)
    second.regenerated = True
    if second.passed:
        return repaired, second
    return fallback_reply(decision), second
