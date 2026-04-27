from __future__ import annotations

import os

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult
from security.access.client import AccessClient
from security.diff import compare_access_results
from security.rules import classify_html_diff


class HoneypotChecker(BaseSecurityChecker):
    name = "honeypot_checker"
    order = 10

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> SecurityResult:
        target_url = context.runtime.get("honeypot_url") or os.getenv("HONEYPOT_BASE_URL")
        if not target_url:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="honeypot_url_not_configured",
                evidence={"status": "skipped", "note": "set HONEYPOT_BASE_URL to enable direct vs proxy comparison"},
            )

        client = AccessClient(
            timeout=int(os.getenv("HONEYPOT_TIMEOUT_SECONDS", "10")),
            user_agent=context.runtime.get("user_agent"),
        )
        direct = client.fetch_direct(target_url)
        proxied = client.fetch_via_proxy(target_url, context.proxy)

        if not direct.success:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.ERROR.value,
                outcome=ScanOutcome.ERROR.value,
                error=direct.error_message,
                evidence={"targetUrl": target_url, "roundIndex": context.runtime.get("round_index", 1), "userAgent": context.runtime.get("user_agent"), "direct": direct.__dict__, "proxy": proxied.__dict__},
            )
        if not proxied.success:
            status = ExecutionStatus.TIMEOUT.value if proxied.error_type == "timeout" else ExecutionStatus.ERROR.value
            outcome = ScanOutcome.TIMEOUT.value if proxied.error_type == "timeout" else ScanOutcome.ERROR.value
            return SecurityResult(
                checker_name=self.name,
                success=False,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=status,
                outcome=outcome,
                error=proxied.error_message,
                evidence={"targetUrl": target_url, "roundIndex": context.runtime.get("round_index", 1), "userAgent": context.runtime.get("user_agent"), "direct": direct.__dict__, "proxy": proxied.__dict__},
            )

        diff = compare_access_results(direct, proxied)
        risk_level, risk_tags = classify_html_diff(diff)
        anomalous = diff.hash_changed or diff.status_changed or diff.has_dom_risk
        return SecurityResult(
            checker_name=self.name,
            success=True,
            risk_level=risk_level if anomalous else RiskLevel.LOW.value,
            risk_tags=risk_tags,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.ANOMALOUS.value if anomalous else ScanOutcome.NORMAL.value,
            evidence={
                "targetUrl": target_url,
                "roundIndex": context.runtime.get("round_index", 1),
                "userAgent": context.runtime.get("user_agent"),
                "direct": direct.__dict__,
                "proxy": proxied.__dict__,
                "diff": diff.to_dict(),
            },
        )
