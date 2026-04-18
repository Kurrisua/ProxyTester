from __future__ import annotations

import hashlib
import importlib.util
import unittest

from security.access.models import AccessResult
from security.diff import compare_access_results
from security.rules import classify_html_diff


class HoneypotMvpTest(unittest.TestCase):
    def test_honeypot_manifest_and_static_page_are_available(self) -> None:
        if importlib.util.find_spec("flask") is None:
            self.skipTest("Flask is not installed in this Python environment")
        from api.app_factory import create_app

        app = create_app()
        client = app.test_client()

        manifest_response = client.get("/honeypot/manifest")
        self.assertEqual(manifest_response.status_code, 200)
        targets = manifest_response.get_json()["targets"]
        self.assertTrue(any(target["path"] == "/honeypot/static/basic" for target in targets))

        page_response = client.get("/honeypot/static/basic")
        self.assertEqual(page_response.status_code, 200)
        self.assertIn(b"ProxyTester Honeypot", page_response.data)

    def test_html_diff_detects_obvious_script_injection(self) -> None:
        direct_body = "<html><body><main><form action='/safe'></form></main></body></html>"
        proxy_body = "<html><body><main><form action='/safe'></form><script src='http://evil.test/a.js'></script></main></body></html>"
        direct = AccessResult(
            success=True,
            mode="direct",
            target_url="http://example.test",
            status_code=200,
            body_text=direct_body,
            body_bytes_sha256=hashlib.sha256(direct_body.encode("utf-8")).hexdigest(),
        )
        proxied = AccessResult(
            success=True,
            mode="proxy",
            target_url="http://example.test",
            status_code=200,
            body_text=proxy_body,
            body_bytes_sha256=hashlib.sha256(proxy_body.encode("utf-8")).hexdigest(),
        )

        summary = compare_access_results(direct, proxied)
        risk_level, risk_tags = classify_html_diff(summary)

        self.assertTrue(summary.has_dom_risk)
        self.assertEqual(risk_level, "high")
        self.assertIn("script_injection", risk_tags)


if __name__ == "__main__":
    unittest.main()
