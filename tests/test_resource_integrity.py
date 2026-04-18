from __future__ import annotations

import hashlib
import unittest

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import SecurityResult
from scheduler.check_pipeline import CheckPipeline
from scoring.security_scorer import SecurityScorer
from security.access.models import AccessResult
from security.diff import compare_resource_results
from storage.mysql.security_repositories import InMemorySecurityRepository


class ResourceEvidenceChecker(BaseSecurityChecker):
    name = "resource_evidence_checker"
    stage = "resource_integrity"
    order = 1

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
            risk_tags=["script_modified"],
            evidence={
                "resourceObservations": [
                    {
                        "resource_url": "http://honeypot.test/site.js",
                        "resource_type": "javascript",
                        "direct_sha256": "a" * 64,
                        "proxy_sha256": "b" * 64,
                        "is_modified": True,
                        "risk_level": RiskLevel.HIGH.value,
                    }
                ],
                "behaviorEvents": [
                    {
                        "event_type": "script_modified",
                        "behavior_class": BehaviorClass.RESOURCE_REPLACEMENT.value,
                        "risk_level": RiskLevel.HIGH.value,
                        "summary": "script changed",
                    }
                ],
            },
        )


class ResourceIntegrityTest(unittest.TestCase):
    def test_resource_diff_distinguishes_modified_resource_from_fetch_failure(self) -> None:
        direct_body = b"window.safe=true;"
        proxy_body = b"window.safe=false;"
        direct = AccessResult(
            success=True,
            mode="direct",
            target_url="http://honeypot.test/site.js",
            status_code=200,
            body_bytes_sha256=hashlib.sha256(direct_body).hexdigest(),
            body_size=len(direct_body),
            mime_type="application/javascript; charset=utf-8",
        )
        proxied = AccessResult(
            success=True,
            mode="proxy",
            target_url="http://honeypot.test/site.js",
            status_code=200,
            body_bytes_sha256=hashlib.sha256(proxy_body).hexdigest(),
            body_size=len(proxy_body),
            mime_type="application/javascript; charset=utf-8",
        )

        diff = compare_resource_results("javascript", direct, proxied)

        self.assertTrue(diff.is_modified)
        self.assertIsNone(diff.failure_type)
        self.assertEqual(diff.risk_level, RiskLevel.HIGH.value)
        self.assertIn("script_modified", diff.risk_tags)

        failed_proxy = AccessResult(False, "proxy", "http://honeypot.test/site.js", error_type="timeout")
        failure = compare_resource_results("javascript", direct, failed_proxy)

        self.assertFalse(failure.is_modified)
        self.assertEqual(failure.failure_type, "proxy_timeout")
        self.assertIn("resource_fetch_failed", failure.risk_tags)

    def test_pipeline_persists_resource_observations_and_events(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8080, proxy_type="HTTP", is_alive=True, http=True)
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[ResourceEvidenceChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy])

        self.assertEqual(len(scan_repo.resource_observations), 1)
        self.assertEqual(scan_repo.resource_observations[0]["record_id"], 1)
        self.assertEqual(scan_repo.events[0]["event_type"], "script_modified")
        self.assertEqual(scan_repo.events[0]["record_id"], 1)


if __name__ == "__main__":
    unittest.main()
