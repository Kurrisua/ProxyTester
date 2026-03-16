from __future__ import annotations

from dataclasses import dataclass, field

from core.models.proxy_model import ProxyModel
from core.models.results import CheckResult, ScoreResult, SecurityResult


@dataclass
class CheckContext:
    proxy: ProxyModel
    check_results: list[CheckResult] = field(default_factory=list)
    security_results: list[SecurityResult] = field(default_factory=list)
    score_results: list[ScoreResult] = field(default_factory=list)
    runtime: dict = field(default_factory=dict)

    def add_check_result(self, result: CheckResult) -> None:
        self.check_results.append(result)

    def add_security_result(self, result: SecurityResult) -> None:
        self.security_results.append(result)

    def add_score_result(self, result: ScoreResult) -> None:
        self.score_results.append(result)
