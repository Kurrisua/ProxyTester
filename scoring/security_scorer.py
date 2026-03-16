from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseScorer
from core.models.results import ScoreResult

RISK_PRIORITY = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class SecurityScorer(BaseScorer):
    name = "security_scorer"

    def score(self, context: CheckContext) -> None:
        highest = "low"
        flags: list[str] = []
        evidence: dict = {}
        for result in context.security_results:
            if RISK_PRIORITY.get(result.risk_level, 0) > RISK_PRIORITY.get(highest, 0):
                highest = result.risk_level
            flags.extend(result.risk_tags)
            if result.evidence:
                evidence[result.checker_name] = result.evidence
        context.proxy.security_risk = highest if context.security_results else "unknown"
        context.proxy.security_flags = list(dict.fromkeys(flags))
        context.proxy.security_evidence = evidence
        context.add_score_result(
            ScoreResult(
                scorer_name=self.name,
                score=max(0, 100 - (RISK_PRIORITY.get(highest, 1) - 1) * 25),
                breakdown={"risk_level": context.proxy.security_risk, "flags": context.proxy.security_flags},
            )
        )
