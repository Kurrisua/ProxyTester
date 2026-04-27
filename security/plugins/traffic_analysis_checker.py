from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult


class TrafficAnalysisChecker(BaseSecurityChecker):
    name = "traffic_analysis_checker"
    stage = "dynamic_observation"
    order = 40
    funnel_stage = 7

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> SecurityResult:
        round_index = int(context.runtime.get("round_index", 1))
        observation_step = context.runtime.get("observation_step")
        completed = [
            result
            for result in context.security_results
            if result.execution_status == ExecutionStatus.COMPLETED.value
            and result.checker_name != self.name
        ]
        anomalous = [result for result in completed if result.outcome == ScanOutcome.ANOMALOUS.value]
        if not observation_step and round_index == 1:
            return SecurityResult(
                checker_name=self.name,
                success=False,
                stage=self.stage,
                risk_level=RiskLevel.UNKNOWN.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.SKIPPED.value,
                skip_reason="dynamic_observation_not_requested",
                funnel_stage=self.funnel_stage,
                evidence={"status": "skipped", "note": "run DynamicObservationRunner or set round_index > 1 for multi-round traffic analysis"},
            )

        risk_tags = sorted({tag for result in anomalous for tag in result.risk_tags})
        events = []
        if anomalous:
            trigger_tag = "delayed_trigger" if round_index > 1 else "conditional_trigger"
            risk_tags.append(trigger_tag)
            events.append(
                {
                    "event_type": trigger_tag,
                    "behavior_class": BehaviorClass.STEALTHY_MALICIOUS.value,
                    "risk_level": _highest_risk(result.risk_level for result in anomalous),
                    "confidence": 0.68 if round_index == 1 else 0.78,
                    "target_url": context.runtime.get("observation_target_url"),
                    "target_type": "dynamic_observation",
                    "evidence": {
                        "roundIndex": round_index,
                        "observationStep": observation_step,
                        "anomalousCheckers": [result.checker_name for result in anomalous],
                    },
                    "summary": f"Anomalous behavior observed during dynamic round {round_index}",
                }
            )

        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            risk_level=_highest_risk(result.risk_level for result in anomalous) if anomalous else RiskLevel.LOW.value,
            risk_tags=list(dict.fromkeys(risk_tags)),
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.ANOMALOUS.value if anomalous else ScanOutcome.NORMAL.value,
            funnel_stage=self.funnel_stage,
            scan_depth="multi_round",
            precondition_summary={
                "roundIndex": round_index,
                "observationStep": observation_step,
                "completedSecurityChecks": [result.checker_name for result in completed],
            },
            evidence={
                "roundIndex": round_index,
                "observationStep": observation_step,
                "anomalousCheckers": [result.checker_name for result in anomalous],
                "behaviorEvents": events,
            },
        )


def _highest_risk(levels) -> str:
    order = {
        RiskLevel.UNKNOWN.value: 0,
        RiskLevel.LOW.value: 1,
        RiskLevel.MEDIUM.value: 2,
        RiskLevel.HIGH.value: 3,
        RiskLevel.CRITICAL.value: 4,
    }
    return max(levels, key=lambda level: order.get(level, 0), default=RiskLevel.UNKNOWN.value)
