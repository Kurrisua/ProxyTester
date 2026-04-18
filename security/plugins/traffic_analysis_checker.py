from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult


class TrafficAnalysisChecker(BaseSecurityChecker):
    name = "traffic_analysis_checker"
    order = 40

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=False,
            risk_level=RiskLevel.UNKNOWN.value,
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.SKIPPED.value,
            skip_reason="traffic_analysis_checker_not_implemented",
            evidence={"status": "placeholder", "note": "traffic analysis plugin slot reserved"},
        )
