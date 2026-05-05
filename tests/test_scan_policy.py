from __future__ import annotations

import os
import unittest

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import Applicability, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import SecurityResult
from scheduler.check_pipeline import CheckPipeline
from scoring.security_scorer import SecurityScorer
from security.policy import ScanPolicy, validate_security_checker
from storage.mysql.security_repositories import InMemorySecurityRepository


class PolicyProbeChecker(BaseSecurityChecker):
    name = "policy_probe_checker"
    stage = "policy_probe"
    order = 10
    funnel_stage = 4
    scan_depth = "deep"
    cost_level = "medium"
    required_capabilities = ("web",)
    required_config = ("PROXYTESTER_TEST_REQUIRED_URL",)
    produces_events = ("policy_probe",)
    description = "Test checker for scan policy routing."

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable and (context.proxy.http or context.proxy.https)

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            risk_level=RiskLevel.LOW.value,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.NORMAL.value,
            funnel_stage=self.funnel_stage,
            scan_depth=self.scan_depth,
        )


class TlsOnlyChecker(PolicyProbeChecker):
    name = "tls_only_checker"
    required_capabilities = ("tls_proxy",)
    required_config = ()


class ScanPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("PROXYTESTER_TEST_REQUIRED_URL", None)

    def test_checker_contract_validation_accepts_metadata(self) -> None:
        self.assertEqual(validate_security_checker(PolicyProbeChecker()), [])

    def test_policy_records_depth_limited_checker_as_skipped(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = _http_proxy()
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[PolicyProbeChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy], runtime={"max_scan_depth": "standard"})

        self.assertEqual(scan_repo.records[0].checker_name, "policy_probe_checker")
        self.assertEqual(scan_repo.records[0].outcome, ScanOutcome.SKIPPED.value)
        self.assertEqual(scan_repo.records[0].skip_reason, "scan_depth_limited_by_policy")

    def test_policy_records_missing_config_as_skipped(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = _http_proxy()
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[PolicyProbeChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy], runtime={"max_scan_depth": "deep"})

        self.assertEqual(scan_repo.records[0].execution_status, ExecutionStatus.SKIPPED.value)
        self.assertEqual(scan_repo.records[0].outcome, ScanOutcome.SKIPPED.value)
        self.assertEqual(scan_repo.records[0].skip_reason, "missing_config:PROXYTESTER_TEST_REQUIRED_URL")

    def test_policy_records_missing_capability_as_not_applicable(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = _http_proxy()
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[TlsOnlyChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy], runtime={"max_scan_depth": "deep"})

        self.assertEqual(scan_repo.records[0].applicability, Applicability.NOT_APPLICABLE.value)
        self.assertEqual(scan_repo.records[0].outcome, ScanOutcome.NOT_APPLICABLE.value)
        self.assertEqual(scan_repo.records[0].skip_reason, "missing_capability:tls_proxy")

    def test_runtime_policy_can_enable_deep_checker(self) -> None:
        os.environ["PROXYTESTER_TEST_REQUIRED_URL"] = "http://honeypot.test"
        scan_repo = InMemorySecurityRepository()
        proxy = _http_proxy()
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[PolicyProbeChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy], runtime={"scan_policy": ScanPolicy(name="deep-test", max_scan_depth="deep")})

        self.assertEqual(scan_repo.records[0].execution_status, ExecutionStatus.COMPLETED.value)
        self.assertEqual(scan_repo.records[0].outcome, ScanOutcome.NORMAL.value)


def _http_proxy() -> ProxyModel:
    proxy = ProxyModel(ip="127.0.0.1", port=8080)
    proxy.is_alive = True
    proxy.http = True
    proxy.proxy_type = "HTTP"
    return proxy


if __name__ == "__main__":
    unittest.main()
