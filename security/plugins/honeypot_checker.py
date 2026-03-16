from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.results import SecurityResult


class HoneypotChecker(BaseSecurityChecker):
    name = "honeypot_checker"
    order = 10

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=True,
            risk_level="low",
            evidence={"status": "placeholder", "note": "honeypot plugin slot reserved"},
        )
