from __future__ import annotations

from security.diff.html_diff import HtmlDiffSummary


def classify_html_diff(summary: HtmlDiffSummary) -> tuple[str, list[str]]:
    tags: list[str] = []
    risk_level = "low" if summary.hash_changed else "unknown"

    if "script" in summary.added_tags:
        tags.append("script_injection")
        risk_level = "high"
    if "iframe" in summary.added_tags:
        tags.append("hidden_iframe")
        risk_level = "high"
    if summary.form_action_changed:
        tags.append("form_hijack")
        risk_level = "critical"
    if summary.added_external_urls:
        tags.append("external_resource_added")
        risk_level = max_risk(risk_level, "medium")
    if summary.added_event_handlers:
        tags.append("event_handler_injection")
        risk_level = max_risk(risk_level, "high")
    if summary.status_changed:
        tags.append("status_code_changed")
        risk_level = max_risk(risk_level, "medium")
    if summary.hash_changed and not tags:
        tags.append("content_hash_changed")
        risk_level = max_risk(risk_level, "medium")

    return risk_level, tags


def max_risk(left: str, right: str) -> str:
    order = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return left if order.get(left, 0) >= order.get(right, 0) else right
