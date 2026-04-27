from __future__ import annotations

import json
import os
from urllib.parse import urljoin, urlparse

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult
from security.access.client import AccessClient
from security.diff import compare_resource_results


class ResourceIntegrityChecker(BaseSecurityChecker):
    name = "resource_integrity_checker"
    stage = "resource_integrity"
    order = 25

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> SecurityResult:
        target_url = context.runtime.get("honeypot_url") or os.getenv("HONEYPOT_BASE_URL")
        if not target_url:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="honeypot_url_not_configured",
                funnel_stage=5,
                evidence={"status": "skipped", "note": "set HONEYPOT_BASE_URL to enable resource integrity checks"},
            )

        base_url = _origin(target_url)
        manifest_url = urljoin(base_url, "/honeypot/manifest")
        client = AccessClient(
            timeout=int(os.getenv("HONEYPOT_TIMEOUT_SECONDS", "10")),
            user_agent=context.runtime.get("user_agent"),
        )
        manifest_result = client.fetch_direct(manifest_url)
        if not manifest_result.success or not manifest_result.body_text:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.ERROR.value,
                outcome=ScanOutcome.ERROR.value,
                error=manifest_result.error_message or "honeypot_manifest_unavailable",
                funnel_stage=5,
                evidence={"manifest": manifest_result.__dict__},
            )

        resources = _resource_targets(manifest_result.body_text)
        if not resources:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="honeypot_manifest_has_no_resources",
                funnel_stage=5,
                evidence={"manifestUrl": manifest_url},
            )

        diffs = []
        observations = []
        events = []
        for resource in resources:
            resource_url = resource.get("url") or urljoin(base_url, resource["path"])
            direct = client.fetch_direct(resource_url)
            proxied = client.fetch_via_proxy(resource_url, context.proxy)
            diff = compare_resource_results(resource.get("targetType", "resource"), direct, proxied)
            diffs.append(diff)
            observations.append(_observation_from_diff(diff))
            if diff.is_modified:
                events.append(_event_from_diff(diff))

        modified = [diff for diff in diffs if diff.is_modified]
        failures = [diff for diff in diffs if diff.failure_type]
        risk_level = _highest_risk(diff.risk_level for diff in diffs)
        risk_tags = sorted({tag for diff in diffs for tag in diff.risk_tags})

        if modified:
            outcome = ScanOutcome.ANOMALOUS.value
            success = True
        elif failures:
            outcome = ScanOutcome.ERROR.value
            success = False
        else:
            outcome = ScanOutcome.NORMAL.value
            success = True

        return SecurityResult(
            checker_name=self.name,
            success=success,
            stage=self.stage,
            risk_level=risk_level,
            risk_tags=risk_tags,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=outcome,
            funnel_stage=5,
            scan_depth="light",
            evidence={
                "manifestUrl": manifest_url,
                "roundIndex": context.runtime.get("round_index", 1),
                "userAgent": context.runtime.get("user_agent"),
                "resourceCount": len(resources),
                "modifiedCount": len(modified),
                "failureCount": len(failures),
                "resourceDiffs": [diff.to_dict() for diff in diffs],
                "resourceObservations": observations,
                "behaviorEvents": events,
            },
        )


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _resource_targets(manifest_body: str) -> list[dict]:
    payload = json.loads(manifest_body)
    return [target for target in payload.get("targets", []) if target.get("targetType") != "html"]


def _observation_from_diff(diff) -> dict:
    return {
        "resource_url": diff.resource_url,
        "resource_type": diff.resource_type,
        "direct_status_code": diff.direct_status_code,
        "proxy_status_code": diff.proxy_status_code,
        "direct_sha256": diff.direct_sha256,
        "proxy_sha256": diff.proxy_sha256,
        "direct_size": diff.direct_size,
        "proxy_size": diff.proxy_size,
        "direct_mime_type": diff.direct_mime_type,
        "proxy_mime_type": diff.proxy_mime_type,
        "is_modified": diff.is_modified,
        "failure_type": diff.failure_type,
        "risk_level": diff.risk_level,
        "summary": diff.to_dict(),
    }


def _event_from_diff(diff) -> dict:
    event_type = diff.risk_tags[0] if diff.risk_tags else "resource_replacement"
    return {
        "event_type": event_type,
        "behavior_class": BehaviorClass.RESOURCE_REPLACEMENT.value,
        "risk_level": diff.risk_level,
        "confidence": 0.9,
        "target_url": diff.resource_url,
        "target_type": diff.resource_type,
        "affected_resource_url": diff.resource_url,
        "evidence": diff.to_dict(),
        "summary": f"Resource integrity changed for {diff.resource_type}: {diff.resource_url}",
    }


def _highest_risk(levels) -> str:
    order = {
        RiskLevel.UNKNOWN.value: 0,
        RiskLevel.LOW.value: 1,
        RiskLevel.MEDIUM.value: 2,
        RiskLevel.HIGH.value: 3,
        RiskLevel.CRITICAL.value: 4,
    }
    return max(levels, key=lambda level: order.get(level, 0), default=RiskLevel.UNKNOWN.value)
