from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult


class DomDiffChecker(BaseSecurityChecker):
    name = "dom_diff_checker"
    order = 20

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.http or context.proxy.https

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=False,
            risk_level=RiskLevel.UNKNOWN.value,
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.SKIPPED.value,
            skip_reason="dom_diff_checker_not_implemented",
            evidence={"status": "placeholder", "note": "dom diff plugin slot reserved"},
        )
