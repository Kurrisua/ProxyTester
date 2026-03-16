from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.results import SecurityResult


class MitmChecker(BaseSecurityChecker):
    name = "mitm_checker"
    order = 30

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.https or context.proxy.socks5

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=True,
            risk_level="low",
            evidence={"status": "placeholder", "note": "mitm plugin slot reserved"},
        )
