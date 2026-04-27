from __future__ import annotations

import unittest

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import BehaviorClass, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import SecurityResult
from scheduler.check_pipeline import CheckPipeline
from scoring.security_scorer import SecurityScorer
from security.access.cert_probe import CertificateProbeResult
from security.diff import compare_certificate_results
from security.plugins.mitm_checker import MitmChecker
from storage.mysql.security_repositories import InMemorySecurityRepository


class CertificateEvidenceChecker(BaseSecurityChecker):
    name = "certificate_evidence_checker"
    stage = "mitm_detection"
    order = 1
    funnel_stage = 6

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
            risk_tags=["cert_mismatch", "mitm_suspected"],
            evidence={
                "certificateObservations": [
                    {
                        "observation_mode": "direct",
                        "host": "honeypot.test",
                        "port": 443,
                        "fingerprint_sha256": "a" * 64,
                        "risk_level": RiskLevel.UNKNOWN.value,
                    },
                    {
                        "observation_mode": "proxy",
                        "host": "honeypot.test",
                        "port": 443,
                        "fingerprint_sha256": "b" * 64,
                        "is_mismatch": True,
                        "risk_level": RiskLevel.HIGH.value,
                    },
                ],
                "behaviorEvents": [
                    {
                        "event_type": "mitm_suspected",
                        "behavior_class": BehaviorClass.MITM_SUSPECTED.value,
                        "risk_level": RiskLevel.HIGH.value,
                        "summary": "certificate changed",
                    }
                ],
            },
        )


class MitmCertificateTest(unittest.TestCase):
    def test_certificate_diff_detects_fingerprint_mismatch(self) -> None:
        direct = CertificateProbeResult(
            success=True,
            mode="direct",
            host="honeypot.test",
            fingerprint_sha256="a" * 64,
            issuer="organizationName=Trusted CA",
            subject="commonName=honeypot.test",
        )
        proxied = CertificateProbeResult(
            success=True,
            mode="proxy",
            host="honeypot.test",
            fingerprint_sha256="b" * 64,
            issuer="organizationName=Proxy CA",
            subject="commonName=honeypot.test",
        )

        diff = compare_certificate_results(direct, proxied)

        self.assertTrue(diff.is_mismatch)
        self.assertEqual(diff.risk_level, RiskLevel.HIGH.value)
        self.assertIn("cert_mismatch", diff.risk_tags)
        self.assertIn("mitm_suspected", diff.risk_tags)

    def test_http_only_proxy_records_mitm_not_applicable(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8080, proxy_type="HTTP", is_alive=True, http=True)
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[MitmChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy])

        self.assertEqual(len(scan_repo.records), 1)
        self.assertEqual(scan_repo.records[0].checker_name, "mitm_checker")
        self.assertEqual(scan_repo.records[0].funnel_stage, 6)
        self.assertEqual(scan_repo.records[0].outcome, ScanOutcome.NOT_APPLICABLE.value)

    def test_pipeline_persists_certificate_observations_and_mitm_event(self) -> None:
        scan_repo = InMemorySecurityRepository()
        proxy = ProxyModel(ip="127.0.0.1", port=8443, proxy_type="HTTPS", is_alive=True, https=True)
        pipeline = CheckPipeline(
            checkers=[],
            security_checkers=[CertificateEvidenceChecker()],
            scorers=[SecurityScorer()],
            scan_repository=scan_repo,
            max_workers=1,
        )

        pipeline.run_batch([proxy])

        self.assertEqual(len(scan_repo.certificate_observations), 2)
        self.assertEqual(scan_repo.certificate_observations[0]["record_id"], 1)
        self.assertTrue(scan_repo.certificate_observations[1]["is_mismatch"])
        self.assertEqual(scan_repo.events[0]["event_type"], "mitm_suspected")
        self.assertEqual(scan_repo.events[0]["record_id"], 1)


if __name__ == "__main__":
    unittest.main()
