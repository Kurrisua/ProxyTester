from __future__ import annotations

from datetime import datetime
from typing import Any

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseScorer
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import ScoreResult, SecurityResult

RISK_PRIORITY = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
RISK_SCORE = {"unknown": None, "low": 92, "medium": 68, "high": 38, "critical": 8}
TAG_WEIGHTS = {
    "form_hijack": 38,
    "mitm_suspected": 32,
    "cert_mismatch": 30,
    "self_signed_cert": 26,
    "script_injection": 30,
    "event_handler_injection": 24,
    "script_modified": 24,
    "file_replaced": 24,
    "mime_type_mismatch": 18,
    "css_modified": 14,
    "external_resource_added": 14,
    "content_hash_changed": 12,
    "status_code_changed": 10,
    "conditional_trigger": 18,
    "delayed_trigger": 16,
}
TAG_BEHAVIOR_PRIORITY = [
    ("form_hijack", BehaviorClass.CONTENT_TAMPERING.value),
    ("mitm_suspected", BehaviorClass.MITM_SUSPECTED.value),
    ("cert_mismatch", BehaviorClass.MITM_SUSPECTED.value),
    ("self_signed_cert", BehaviorClass.MITM_SUSPECTED.value),
    ("script_injection", BehaviorClass.SCRIPT_INJECTION.value),
    ("event_handler_injection", BehaviorClass.SCRIPT_INJECTION.value),
    ("script_modified", BehaviorClass.RESOURCE_REPLACEMENT.value),
    ("file_replaced", BehaviorClass.RESOURCE_REPLACEMENT.value),
    ("css_modified", BehaviorClass.RESOURCE_REPLACEMENT.value),
    ("mime_type_mismatch", BehaviorClass.RESOURCE_REPLACEMENT.value),
    ("external_resource_added", BehaviorClass.REDIRECT_MANIPULATION.value),
    ("content_hash_changed", BehaviorClass.CONTENT_TAMPERING.value),
    ("status_code_changed", BehaviorClass.CONTENT_TAMPERING.value),
]


class SecurityScorer(BaseScorer):
    name = "security_scorer"

    def score(self, context: CheckContext) -> None:
        completed_results = [
            result
            for result in context.security_results
            if result.execution_status == ExecutionStatus.COMPLETED.value
            and result.outcome in {ScanOutcome.NORMAL.value, ScanOutcome.ANOMALOUS.value}
        ]
        executable_results = [
            result
            for result in context.security_results
            if result.execution_status in {ExecutionStatus.COMPLETED.value, ExecutionStatus.ERROR.value, ExecutionStatus.TIMEOUT.value}
        ]
        anomalous_results = [result for result in completed_results if result.outcome == ScanOutcome.ANOMALOUS.value]

        highest = self._highest_risk(completed_results)
        behavior_events = self._behavior_events(completed_results)
        base_flags = self._unique_flags(completed_results)
        trigger_pattern = self._trigger_pattern(completed_results, anomalous_results)
        confidence = self._confidence(completed_results, behavior_events, trigger_pattern)
        derived_flags = self._derived_flags(trigger_pattern, confidence)
        unique_flags = self._unique([*base_flags, *derived_flags])

        security_check_count = len(executable_results)
        anomaly_trigger_count = len(anomalous_results)
        anomaly_trigger_rate = round(anomaly_trigger_count / security_check_count, 4) if security_check_count else None
        risk_level = self._adjust_risk_level(highest, unique_flags, anomaly_trigger_count)
        score = self._weighted_score(risk_level, unique_flags, confidence, anomaly_trigger_rate)
        behavior_class = self._classify_behavior(unique_flags, behavior_events, risk_level, trigger_pattern)

        evidence_summary = {
            "summary": {
                "riskLevel": risk_level,
                "behaviorClass": behavior_class,
                "confidence": confidence,
                "triggerPattern": trigger_pattern,
                "weightedScore": score,
                "anomalyTriggerCount": anomaly_trigger_count,
                "securityCheckCount": security_check_count,
                "anomalyTriggerRate": anomaly_trigger_rate,
                "firstAnomalousRound": self._first_anomalous_round(anomalous_results),
            }
        }
        for result in completed_results:
            if result.evidence:
                evidence_summary[result.checker_name] = self._summarize_evidence(result.evidence)

        context.proxy.security_risk = risk_level if completed_results else RiskLevel.UNKNOWN.value
        context.proxy.security_score = score
        context.proxy.behavior_class = behavior_class
        context.proxy.security_flags = unique_flags
        context.proxy.security_evidence = evidence_summary
        context.proxy.has_content_tampering = any(tag in unique_flags for tag in {"content_hash_changed", "form_hijack", "status_code_changed", "script_injection"})
        context.proxy.has_resource_replacement = any(tag in unique_flags for tag in {"script_modified", "file_replaced", "css_modified", "mime_type_mismatch"})
        context.proxy.has_mitm_risk = any(tag in unique_flags for tag in {"mitm_suspected", "cert_mismatch", "self_signed_cert", "unknown_issuer"})
        context.proxy.anomaly_trigger_count = anomaly_trigger_count
        context.proxy.security_check_count = security_check_count
        context.proxy.anomaly_trigger_rate = anomaly_trigger_rate
        context.proxy.last_security_check_time = datetime.now() if context.security_results else None
        context.add_score_result(
            ScoreResult(
                scorer_name=self.name,
                score=score or 0,
                breakdown={
                    "risk_level": context.proxy.security_risk,
                    "behavior_class": context.proxy.behavior_class,
                    "confidence": confidence,
                    "trigger_pattern": trigger_pattern,
                    "flags": context.proxy.security_flags,
                    "anomaly_trigger_count": anomaly_trigger_count,
                    "security_check_count": security_check_count,
                    "anomaly_trigger_rate": anomaly_trigger_rate,
                },
            )
        )

    @staticmethod
    def _highest_risk(results: list[SecurityResult]) -> str:
        highest = RiskLevel.UNKNOWN.value
        for result in results:
            if RISK_PRIORITY.get(result.risk_level, 0) > RISK_PRIORITY.get(highest, 0):
                highest = result.risk_level
        return highest

    @staticmethod
    def _behavior_events(results: list[SecurityResult]) -> list[dict]:
        events: list[dict] = []
        for result in results:
            if isinstance(result.evidence, dict):
                events.extend(result.evidence.get("behaviorEvents", []) or [])
        return events

    @staticmethod
    def _unique_flags(results: list[SecurityResult]) -> list[str]:
        return SecurityScorer._unique(tag for result in results for tag in result.risk_tags)

    @staticmethod
    def _unique(values) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _trigger_pattern(completed_results: list[SecurityResult], anomalous_results: list[SecurityResult]) -> str:
        if not completed_results:
            return "not_observed"
        if not anomalous_results:
            return "none"
        if len(completed_results) == len(anomalous_results):
            return "stable_anomalous"

        anomalous_rounds = [SecurityScorer._round_index(result) for result in anomalous_results]
        if anomalous_rounds and min(anomalous_rounds) > 1:
            return "delayed_trigger"
        if len(completed_results) > 1:
            return "conditional_trigger"
        return "single_round_anomalous"

    @staticmethod
    def _round_index(result: SecurityResult) -> int:
        if isinstance(result.evidence, dict) and result.evidence.get("roundIndex") is not None:
            return int(result.evidence["roundIndex"])
        if result.precondition_summary.get("roundIndex") is not None:
            return int(result.precondition_summary["roundIndex"])
        return 1

    @staticmethod
    def _first_anomalous_round(results: list[SecurityResult]) -> int | None:
        rounds = [SecurityScorer._round_index(result) for result in results]
        return min(rounds) if rounds else None

    @staticmethod
    def _confidence(results: list[SecurityResult], events: list[dict], trigger_pattern: str) -> float:
        event_confidences = [float(event["confidence"]) for event in events if event.get("confidence") is not None]
        if event_confidences:
            base = max(event_confidences)
        else:
            anomalous_count = len([result for result in results if result.outcome == ScanOutcome.ANOMALOUS.value])
            completed_count = len(results)
            base = 0.35 + min(0.4, anomalous_count * 0.15)
            if completed_count >= 2:
                base += 0.1
        if trigger_pattern in {"stable_anomalous", "delayed_trigger", "conditional_trigger"}:
            base += 0.05
        return round(min(0.99, max(0.0, base)), 2)

    @staticmethod
    def _derived_flags(trigger_pattern: str, confidence: float) -> list[str]:
        flags: list[str] = []
        if trigger_pattern in {"conditional_trigger", "delayed_trigger"}:
            flags.append(trigger_pattern)
        if confidence >= 0.8:
            flags.append("confidence_high")
        elif confidence >= 0.55:
            flags.append("confidence_medium")
        elif confidence > 0:
            flags.append("confidence_low")
        return flags

    @staticmethod
    def _adjust_risk_level(highest: str, flags: list[str], anomaly_count: int) -> str:
        if not anomaly_count:
            return RiskLevel.LOW.value if highest == RiskLevel.LOW.value else highest
        if "form_hijack" in flags:
            return RiskLevel.CRITICAL.value
        if any(tag in flags for tag in {"mitm_suspected", "cert_mismatch", "script_injection"}):
            return RiskLevel.HIGH.value if highest != RiskLevel.CRITICAL.value else highest
        if highest == RiskLevel.LOW.value:
            return RiskLevel.MEDIUM.value
        return highest

    @staticmethod
    def _weighted_score(risk_level: str, flags: list[str], confidence: float, trigger_rate: float | None) -> int | None:
        if risk_level == RiskLevel.UNKNOWN.value:
            return None
        base = RISK_SCORE[risk_level]
        if base is None:
            return None
        tag_penalty = min(42, sum(TAG_WEIGHTS.get(tag, 0) for tag in set(flags)) // 2)
        confidence_penalty = int(confidence * 12) if risk_level in {RiskLevel.MEDIUM.value, RiskLevel.HIGH.value, RiskLevel.CRITICAL.value} else 0
        trigger_penalty = int((trigger_rate or 0) * 10)
        return max(0, min(100, base - tag_penalty - confidence_penalty - trigger_penalty))

    @staticmethod
    def _classify_behavior(flags: list[str], events: list[dict], risk_level: str, trigger_pattern: str) -> str:
        if trigger_pattern in {"conditional_trigger", "delayed_trigger"} and risk_level in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}:
            return BehaviorClass.STEALTHY_MALICIOUS.value
        for event in events:
            behavior_class = event.get("behavior_class")
            if behavior_class and behavior_class != BehaviorClass.NORMAL.value:
                return behavior_class
        for tag, behavior_class in TAG_BEHAVIOR_PRIORITY:
            if tag in flags:
                return behavior_class
        if risk_level in {RiskLevel.LOW.value, RiskLevel.UNKNOWN.value}:
            return BehaviorClass.NORMAL.value
        return BehaviorClass.UNSTABLE_BUT_NON_MALICIOUS.value

    @staticmethod
    def _summarize_evidence(evidence: dict[str, Any]) -> dict:
        summary = {}
        for key in ("targetUrl", "roundIndex", "userAgent", "resourceCount", "modifiedCount", "failureCount", "diff"):
            if key in evidence:
                summary[key] = evidence[key]
        if "behaviorEvents" in evidence:
            summary["behaviorEvents"] = [
                {
                    "event_type": event.get("event_type"),
                    "behavior_class": event.get("behavior_class"),
                    "risk_level": event.get("risk_level"),
                    "confidence": event.get("confidence"),
                    "summary": event.get("summary"),
                }
                for event in evidence.get("behaviorEvents", [])
            ]
        return summary
