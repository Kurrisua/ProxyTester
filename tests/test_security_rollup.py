from __future__ import annotations

import unittest

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import SecurityResult
from scheduler.check_pipeline import CheckPipeline
from scoring.security_scorer import SecurityScorer
from services.proxy_query_service import ProxyQueryService
from storage.mysql.security_repositories import InMemorySecurityRepository


class ScriptInjectionChecker(BaseSecurityChecker):
    name = "script_injection_checker"
    stage = "dom_diff"
    order = 1
    funnel_stage = 4

    def supports(self, context: CheckContext) -> bool:
        return True

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.ANOMALOUS.value,
            risk_level=RiskLevel.HIGH.value,
            risk_tags=["script_injection", "event_handler_injection"],
            evidence={
                "targetUrl": "http://honeypot.test/static/basic",
                "diff": {"addedTags": ["script"]},
                "behaviorEvents": [
                    {
                        "event_type": "script_injection",
                        "behavior_class": BehaviorClass.SCRIPT_INJECTION.value,
                        "risk_level": RiskLevel.HIGH.value,
                        "confidence": 0.9,
                        "summary": "script injected",
                    }
                ],
            },
        )


class SecurityRollupTest(unittest.TestCase):
    def test_security_scorer_rolls_anomalous_behavior_into_proxy_summary(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8080, proxy_type="HTTP", is_alive=True, http=True)
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[ScriptInjectionChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        context = pipeline.run_batch([proxy])[0]

        self.assertEqual(context.proxy.security_risk, RiskLevel.HIGH.value)
        self.assertLess(context.proxy.security_score, 35)
        self.assertEqual(context.proxy.behavior_class, BehaviorClass.SCRIPT_INJECTION.value)
        self.assertEqual(context.proxy.anomaly_trigger_count, 1)
        self.assertEqual(context.proxy.security_check_count, 1)
        self.assertEqual(context.proxy.anomaly_trigger_rate, 1.0)
        self.assertIn("script_injection", context.proxy.security_flags)
        self.assertIn("confidence_high", context.proxy.security_flags)
        self.assertEqual(context.score_results[-1].breakdown["trigger_pattern"], "stable_anomalous")
        self.assertEqual(context.score_results[-1].breakdown["confidence"], 0.95)
        self.assertEqual(len(scan_repo.evidence_files), 1)
        self.assertEqual(scan_repo.evidence_files[0]["evidence_type"], "inline_summary")

    def test_proxy_api_exposes_security_summary_fields(self) -> None:
        proxy = ProxyModel(ip="127.0.0.1", port=8080)
        proxy.security_risk = RiskLevel.HIGH.value
        proxy.security_score = 35
        proxy.behavior_class = BehaviorClass.SCRIPT_INJECTION.value
        proxy.security_flags = ["script_injection", "conditional_trigger", "confidence_high"]
        proxy.anomaly_trigger_count = 1
        proxy.security_check_count = 2
        proxy.anomaly_trigger_rate = 0.5

        payload = ProxyQueryService.to_dict(proxy)

        self.assertEqual(payload["securityRisk"], RiskLevel.HIGH.value)
        self.assertEqual(payload["securityScore"], 35)
        self.assertEqual(payload["behaviorClass"], BehaviorClass.SCRIPT_INJECTION.value)
        self.assertEqual(payload["securitySummary"]["anomalyTriggerCount"], 1)
        self.assertEqual(payload["securitySummary"]["securityCheckCount"], 2)
        self.assertEqual(payload["securitySummary"]["triggerPattern"], "conditional_trigger")
        self.assertEqual(payload["securitySummary"]["confidenceLevel"], "high")


if __name__ == "__main__":
    unittest.main()
