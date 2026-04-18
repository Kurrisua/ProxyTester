from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult
from security.diff.html_diff import HtmlDiffSummary
from security.rules import classify_html_diff


class DomDiffChecker(BaseSecurityChecker):
    name = "dom_diff_checker"
    stage = "dom_diff"
    order = 20
    funnel_stage = 4

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.http or context.proxy.https

    def check(self, context: CheckContext) -> SecurityResult:
        honeypot_result = _latest_honeypot_result(context)
        if honeypot_result is None:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="honeypot_result_required",
                funnel_stage=self.funnel_stage,
                evidence={"status": "skipped", "note": "run honeypot_checker before dom_diff_checker"},
            )

        diff_payload = (honeypot_result.evidence or {}).get("diff")
        if not diff_payload:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="honeypot_diff_unavailable",
                funnel_stage=self.funnel_stage,
                evidence={"honeypotOutcome": honeypot_result.outcome},
            )

        summary = _summary_from_payload(diff_payload)
        risk_level, risk_tags = classify_html_diff(summary)
        dom_tags = [tag for tag in risk_tags if tag in {"script_injection", "hidden_iframe", "form_hijack", "external_resource_added", "event_handler_injection"}]
        anomalous = bool(dom_tags)
        events = [_event_from_tag(tag, summary) for tag in dom_tags]
        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            risk_level=risk_level if anomalous else RiskLevel.LOW.value,
            risk_tags=dom_tags,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.ANOMALOUS.value if anomalous else ScanOutcome.NORMAL.value,
            funnel_stage=self.funnel_stage,
            scan_depth="light",
            evidence={
                "targetUrl": (honeypot_result.evidence or {}).get("targetUrl"),
                "roundIndex": (honeypot_result.evidence or {}).get("roundIndex"),
                "userAgent": (honeypot_result.evidence or {}).get("userAgent"),
                "diff": summary.to_dict(),
                "behaviorEvents": events,
            },
        )


def _latest_honeypot_result(context: CheckContext) -> SecurityResult | None:
    for result in reversed(context.security_results):
        if result.checker_name == "honeypot_checker":
            return result
    return None


def _summary_from_payload(payload: dict) -> HtmlDiffSummary:
    return HtmlDiffSummary(
        direct_hash=payload.get("directHash"),
        proxy_hash=payload.get("proxyHash"),
        status_changed=bool(payload.get("statusChanged")),
        hash_changed=bool(payload.get("hashChanged")),
        added_tags=list(payload.get("addedTags") or []),
        removed_tags=list(payload.get("removedTags") or []),
        added_external_urls=list(payload.get("addedExternalUrls") or []),
        added_event_handlers=list(payload.get("addedEventHandlers") or []),
        form_action_changed=bool(payload.get("formActionChanged")),
    )


def _event_from_tag(tag: str, summary: HtmlDiffSummary) -> dict:
    risk_level = RiskLevel.CRITICAL.value if tag == "form_hijack" else RiskLevel.HIGH.value if tag in {"script_injection", "hidden_iframe", "event_handler_injection"} else RiskLevel.MEDIUM.value
    behavior_class = {
        "script_injection": BehaviorClass.SCRIPT_INJECTION.value,
        "event_handler_injection": BehaviorClass.SCRIPT_INJECTION.value,
        "hidden_iframe": BehaviorClass.SCRIPT_INJECTION.value,
        "form_hijack": BehaviorClass.CONTENT_TAMPERING.value,
        "external_resource_added": BehaviorClass.REDIRECT_MANIPULATION.value,
    }.get(tag, BehaviorClass.CONTENT_TAMPERING.value)
    return {
        "event_type": tag,
        "behavior_class": behavior_class,
        "risk_level": risk_level,
        "confidence": 0.82,
        "target_type": "html_dom",
        "selector": _selector_for_tag(tag, summary),
        "evidence": summary.to_dict(),
        "summary": f"DOM risk detected: {tag}",
    }


def _selector_for_tag(tag: str, summary: HtmlDiffSummary) -> str | None:
    if tag == "script_injection":
        return "script"
    if tag == "hidden_iframe":
        return "iframe"
    if tag == "form_hijack":
        return "form[action]"
    if tag == "event_handler_injection":
        return ", ".join(summary.added_event_handlers)
    return None
