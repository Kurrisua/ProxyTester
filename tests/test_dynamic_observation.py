from __future__ import annotations

import unittest

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import SecurityResult
from scheduler.check_pipeline import CheckPipeline
from scoring.security_scorer import SecurityScorer
from security.observation import DynamicObservationPlan, DynamicObservationRunner
from storage.mysql.security_repositories import InMemorySecurityRepository


class RuntimeEchoChecker(BaseSecurityChecker):
    name = "runtime_echo_checker"
    stage = "dynamic_observation"
    order = 1
    funnel_stage = 7

    def supports(self, context: CheckContext) -> bool:
        return True

    def check(self, context: CheckContext) -> SecurityResult:
        round_index = context.runtime["round_index"]
        target_url = context.runtime["honeypot_url"]
        user_agent = context.runtime.get("user_agent")
        anomalous = "mobile" in (user_agent or "").lower()
        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.ANOMALOUS.value if anomalous else ScanOutcome.NORMAL.value,
            risk_level=RiskLevel.MEDIUM.value if anomalous else RiskLevel.LOW.value,
            risk_tags=["conditional_trigger"] if anomalous else [],
            funnel_stage=self.funnel_stage,
            evidence={
                "targetUrl": target_url,
                "roundIndex": round_index,
                "userAgent": user_agent,
            },
        )


class DynamicObservationTest(unittest.TestCase):
    def test_dynamic_observation_records_rounds_and_preconditions(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8080, proxy_type="HTTP", is_alive=True, http=True)
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[RuntimeEchoChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )
        plan = DynamicObservationPlan.from_targets(
            ["http://honeypot.test/static/basic"],
            user_agents=["ProxyTester Desktop", "ProxyTester Mobile"],
        )

        contexts = DynamicObservationRunner(pipeline).run_for_proxy(proxy, plan)

        self.assertEqual(len(contexts), 2)
        self.assertEqual(scan_repo.batches[0].scan_mode, "dynamic_observation")
        self.assertEqual(scan_repo.batches[0].max_scan_depth, "multi_round")
        self.assertEqual([record.round_index for record in scan_repo.records], [1, 2])
        self.assertEqual(scan_repo.records[0].precondition_summary["userAgent"], "ProxyTester Desktop")
        self.assertEqual(scan_repo.records[1].precondition_summary["userAgent"], "ProxyTester Mobile")
        self.assertEqual(scan_repo.records[1].outcome, ScanOutcome.ANOMALOUS.value)
        self.assertEqual(contexts[-1].proxy.anomaly_trigger_count, 1)
        self.assertIn("confidence_medium", contexts[-1].proxy.security_flags)

    def test_dynamic_observation_plan_expands_target_and_user_agent_matrix(self) -> None:
        plan = DynamicObservationPlan.from_targets(
            ["http://honeypot.test/a", "http://honeypot.test/b"],
            user_agents=["Desktop", "Mobile"],
        )

        self.assertEqual([step.round_index for step in plan.steps], [1, 2, 3, 4])
        self.assertEqual(plan.steps[2].target_url, "http://honeypot.test/b")
        self.assertEqual(plan.steps[3].user_agent, "Mobile")

    def test_multi_round_mixed_results_can_be_scored_as_stealthy(self) -> None:
        proxy = ProxyModel(ip="127.0.0.1", port=8080, proxy_type="HTTP", is_alive=True, http=True)
        context = CheckContext(proxy=proxy)
        context.add_security_result(
            SecurityResult(
                checker_name="round_1",
                success=True,
                stage="dynamic_observation",
                execution_status=ExecutionStatus.COMPLETED.value,
                outcome=ScanOutcome.NORMAL.value,
                risk_level=RiskLevel.LOW.value,
                evidence={"roundIndex": 1, "userAgent": "Desktop"},
            )
        )
        context.add_security_result(
            SecurityResult(
                checker_name="round_2",
                success=True,
                stage="dynamic_observation",
                execution_status=ExecutionStatus.COMPLETED.value,
                outcome=ScanOutcome.ANOMALOUS.value,
                risk_level=RiskLevel.HIGH.value,
                risk_tags=["script_injection"],
                evidence={"roundIndex": 2, "userAgent": "Mobile"},
            )
        )

        SecurityScorer().score(context)

        self.assertEqual(context.proxy.behavior_class, BehaviorClass.STEALTHY_MALICIOUS.value)
        self.assertIn("delayed_trigger", context.proxy.security_flags)
        self.assertEqual(context.score_results[-1].breakdown["trigger_pattern"], "delayed_trigger")


if __name__ == "__main__":
    unittest.main()
