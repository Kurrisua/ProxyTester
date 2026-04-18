from __future__ import annotations

import unittest

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker, BaseSecurityChecker
from core.models.enums import Applicability, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import CheckResult, SecurityResult
from scheduler.check_pipeline import CheckPipeline
from scoring.security_scorer import SecurityScorer
from services.proxy_query_service import ProxyQueryService
from storage.mysql.security_repositories import InMemorySecurityRepository


class PassingTcpChecker(BaseChecker):
    name = "tcp_checker"
    stage = "connectivity"
    order = 10
    blocking = True

    def supports(self, context: CheckContext) -> bool:
        return True

    def check(self, context: CheckContext) -> CheckResult:
        return CheckResult(self.name, self.stage, True, metadata={"alive": True})


class FailingTcpChecker(PassingTcpChecker):
    def check(self, context: CheckContext) -> CheckResult:
        return CheckResult(self.name, self.stage, False, metadata={"alive": False})


class UnsupportedChecker(BaseChecker):
    name = "unsupported_checker"
    stage = "protocol"
    order = 20

    def supports(self, context: CheckContext) -> bool:
        return False

    def check(self, context: CheckContext) -> CheckResult:
        raise AssertionError("unsupported checker should not run")


class SkippedSecurityChecker(BaseSecurityChecker):
    name = "skipped_security_checker"
    stage = "security"
    order = 10

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=False,
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.SKIPPED.value,
            skip_reason="not_implemented",
        )


class Phase0SemanticsTest(unittest.TestCase):
    def test_stable_enum_values(self) -> None:
        self.assertEqual(Applicability.NOT_APPLICABLE.value, "not_applicable")
        self.assertEqual(ExecutionStatus.TIMEOUT.value, "timeout")
        self.assertEqual(RiskLevel.UNKNOWN.value, "unknown")
        self.assertEqual(ScanOutcome.ANOMALOUS.value, "anomalous")

    def test_api_mapping_returns_english_status_values(self) -> None:
        proxy = ProxyModel(ip="127.0.0.1", port=8080)
        proxy.is_alive = True
        proxy.response_time = 42
        proxy.anonymity = "high_anonymous"

        payload = ProxyQueryService.to_dict(proxy)

        self.assertEqual(payload["status"], "alive")
        self.assertEqual(payload["anonymity"], "high_anonymous")

    def test_pipeline_records_not_applicable_and_skipped_results(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8080)
        pipeline = CheckPipeline(
            checkers=[PassingTcpChecker(), UnsupportedChecker()],
            security_checkers=[SkippedSecurityChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        contexts = pipeline.run_batch([proxy])

        self.assertEqual(len(contexts), 1)
        outcomes = {(record.checker_name, record.outcome) for record in scan_repo.records}
        self.assertIn(("unsupported_checker", ScanOutcome.NOT_APPLICABLE.value), outcomes)
        self.assertIn(("skipped_security_checker", ScanOutcome.SKIPPED.value), outcomes)
        self.assertEqual(contexts[0].proxy.security_risk, RiskLevel.UNKNOWN.value)

    def test_dead_proxy_security_checks_are_recorded_as_skipped(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8081)
        pipeline = CheckPipeline(
            checkers=[FailingTcpChecker(), UnsupportedChecker()],
            security_checkers=[SkippedSecurityChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy])

        records = {(record.checker_name, record.outcome, record.skip_reason) for record in scan_repo.records}
        self.assertIn(("unsupported_checker", ScanOutcome.SKIPPED.value, "previous_blocking_checker_failed"), records)
        self.assertIn(("skipped_security_checker", ScanOutcome.SKIPPED.value, "proxy_not_usable"), records)


if __name__ == "__main__":
    unittest.main()
