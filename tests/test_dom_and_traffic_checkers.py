from __future__ import annotations

import unittest

from core.context.check_context import CheckContext
from core.models.enums import ExecutionStatus, RiskLevel, ScanOutcome
from core.models.proxy_model import ProxyModel
from core.models.results import SecurityResult
from security.diff.html_diff import HtmlDiffSummary
from security.plugins.dom_diff_checker import DomDiffChecker
from security.plugins.traffic_analysis_checker import TrafficAnalysisChecker


class DomAndTrafficCheckerTest(unittest.TestCase):
    def test_dom_diff_checker_requires_honeypot_result(self) -> None:
        context = CheckContext(proxy=ProxyModel(ip="127.0.0.1", port=8080, http=True))

        result = DomDiffChecker().check(context)

        self.assertEqual(result.execution_status, ExecutionStatus.SKIPPED.value)
        self.assertEqual(result.outcome, ScanOutcome.SKIPPED.value)
        self.assertEqual(result.skip_reason, "honeypot_result_required")

    def test_dom_diff_checker_turns_dom_risk_into_events(self) -> None:
        context = CheckContext(proxy=ProxyModel(ip="127.0.0.1", port=8080, http=True))
        diff = HtmlDiffSummary(
            direct_hash="direct",
            proxy_hash="proxy",
            status_changed=False,
            hash_changed=True,
            added_tags=["script"],
            added_external_urls=["https://evil.example/payload.js"],
        )
        context.add_security_result(
            SecurityResult(
                checker_name="honeypot_checker",
                success=True,
                outcome=ScanOutcome.ANOMALOUS.value,
                risk_level=RiskLevel.HIGH.value,
                evidence={"targetUrl": "http://honeypot.test/static/basic", "diff": diff.to_dict()},
            )
        )

        result = DomDiffChecker().check(context)

        self.assertEqual(result.execution_status, ExecutionStatus.COMPLETED.value)
        self.assertEqual(result.outcome, ScanOutcome.ANOMALOUS.value)
        self.assertEqual(result.risk_level, RiskLevel.HIGH.value)
        self.assertIn("script_injection", result.risk_tags)
        self.assertEqual(result.evidence["behaviorEvents"][0]["event_type"], "script_injection")

    def test_traffic_analysis_skips_when_not_requested(self) -> None:
        proxy = ProxyModel(ip="127.0.0.1", port=8080, is_alive=True, proxy_type="HTTP")
        context = CheckContext(proxy=proxy)

        result = TrafficAnalysisChecker().check(context)

        self.assertEqual(result.execution_status, ExecutionStatus.SKIPPED.value)
        self.assertEqual(result.skip_reason, "dynamic_observation_not_requested")

    def test_traffic_analysis_marks_later_anomaly_as_delayed_trigger(self) -> None:
        proxy = ProxyModel(ip="127.0.0.1", port=8080, is_alive=True, proxy_type="HTTP")
        context = CheckContext(proxy=proxy, runtime={"round_index": 2, "observation_step": {"userAgent": "Mobile"}})
        context.add_security_result(
            SecurityResult(
                checker_name="dom_diff_checker",
                success=True,
                execution_status=ExecutionStatus.COMPLETED.value,
                outcome=ScanOutcome.ANOMALOUS.value,
                risk_level=RiskLevel.HIGH.value,
                risk_tags=["script_injection"],
            )
        )

        result = TrafficAnalysisChecker().check(context)

        self.assertEqual(result.outcome, ScanOutcome.ANOMALOUS.value)
        self.assertEqual(result.risk_level, RiskLevel.HIGH.value)
        self.assertIn("delayed_trigger", result.risk_tags)
        self.assertEqual(result.evidence["behaviorEvents"][0]["event_type"], "delayed_trigger")


if __name__ == "__main__":
    unittest.main()
