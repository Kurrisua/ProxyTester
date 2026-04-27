from __future__ import annotations

import os
from urllib.parse import urlparse

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult
from security.access.cert_probe import CertificateProbe
from security.diff import compare_certificate_results


class MitmChecker(BaseSecurityChecker):
    name = "mitm_checker"
    stage = "mitm_detection"
    order = 30
    funnel_stage = 6

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.https or context.proxy.socks5

    def check(self, context: CheckContext) -> SecurityResult:
        target_url = context.runtime.get("mitm_target_url") or os.getenv("MITM_TARGET_URL") or os.getenv("HONEYPOT_HTTPS_URL")
        if not target_url:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="mitm_target_url_not_configured",
                funnel_stage=self.funnel_stage,
                precondition_summary=self._preconditions(context),
                evidence={"status": "skipped", "note": "set MITM_TARGET_URL or HONEYPOT_HTTPS_URL to enable TLS certificate comparison"},
            )

        parsed = urlparse(target_url)
        if parsed.scheme != "https" or not parsed.hostname:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.NOT_APPLICABLE.value,
                skip_reason="mitm_target_must_be_https",
                funnel_stage=self.funnel_stage,
                precondition_summary={**self._preconditions(context), "targetUrl": target_url},
                evidence={"targetUrl": target_url},
            )

        port = parsed.port or 443
        probe = CertificateProbe(timeout=int(os.getenv("MITM_TIMEOUT_SECONDS", "10")))
        direct = probe.probe_direct(parsed.hostname, port)
        proxied = probe.probe_via_proxy(context.proxy, parsed.hostname, port)
        diff = compare_certificate_results(direct, proxied)
        anomalous = bool(diff.risk_tags and "mitm_suspected" in diff.risk_tags)

        observations = [
            direct.to_observation(risk_level=RiskLevel.UNKNOWN.value, is_mismatch=False),
            proxied.to_observation(risk_level=diff.risk_level, is_mismatch=diff.is_mismatch),
        ]
        events = []
        if anomalous:
            events.append(
                {
                    "event_type": "mitm_suspected",
                    "behavior_class": BehaviorClass.MITM_SUSPECTED.value,
                    "risk_level": diff.risk_level,
                    "confidence": 0.85,
                    "target_url": target_url,
                    "target_type": "tls_certificate",
                    "before_value": direct.fingerprint_sha256,
                    "after_value": proxied.fingerprint_sha256,
                    "evidence": diff.to_dict(),
                    "summary": f"TLS certificate changed for {parsed.hostname}:{port}",
                }
            )

        if not direct.success:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                risk_tags=diff.risk_tags,
                execution_status=ExecutionStatus.ERROR.value,
                outcome=ScanOutcome.ERROR.value,
                error=direct.error_message,
                funnel_stage=self.funnel_stage,
                precondition_summary={**self._preconditions(context), "targetUrl": target_url},
                evidence={"targetUrl": target_url, "direct": direct.__dict__, "proxy": proxied.__dict__, "diff": diff.to_dict(), "certificateObservations": observations},
            )

        if not proxied.success:
            status = ExecutionStatus.TIMEOUT.value if proxied.error_type == "timeout" else ExecutionStatus.ERROR.value
            outcome = ScanOutcome.TIMEOUT.value if proxied.error_type == "timeout" else ScanOutcome.ERROR.value
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                risk_tags=diff.risk_tags,
                execution_status=status,
                outcome=outcome,
                error=proxied.error_message,
                funnel_stage=self.funnel_stage,
                precondition_summary={**self._preconditions(context), "targetUrl": target_url},
                evidence={"targetUrl": target_url, "direct": direct.__dict__, "proxy": proxied.__dict__, "diff": diff.to_dict(), "certificateObservations": observations},
            )

        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            risk_level=diff.risk_level,
            risk_tags=diff.risk_tags,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.ANOMALOUS.value if anomalous else ScanOutcome.NORMAL.value,
            funnel_stage=self.funnel_stage,
            precondition_summary={**self._preconditions(context), "targetUrl": target_url},
            evidence={
                "targetUrl": target_url,
                "direct": direct.__dict__,
                "proxy": proxied.__dict__,
                "diff": diff.to_dict(),
                "certificateObservations": observations,
                "behaviorEvents": events,
            },
        )

    @staticmethod
    def _preconditions(context: CheckContext) -> dict:
        return {
            "proxyType": context.proxy.proxy_type,
            "https": context.proxy.https,
            "socks5": context.proxy.socks5,
            "httpOnly": context.proxy.http and not context.proxy.https and not context.proxy.socks5,
        }
