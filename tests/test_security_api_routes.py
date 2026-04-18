from __future__ import annotations

import importlib.util
import unittest


class FakeSecurityQueryService:
    closed = False

    def close(self) -> None:
        self.closed = True

    def get_overview(self) -> dict:
        return {
            "totalProxies": 2,
            "activeProxies": 1,
            "uncheckedProxies": 1,
            "normalProxies": 1,
            "suspiciousProxies": 0,
            "maliciousProxies": 0,
            "riskCounts": {"unknown": 1, "low": 1},
            "behaviorCounts": {"normal": 2},
            "scanRecordCounts": [],
            "funnelStats": [],
            "riskTrend": [],
            "protocolCounts": {"http": 1, "https": 1, "socks5": 0, "unknown": 0},
            "geoRiskRanking": [],
            "topEvents": [],
            "recentBatches": [],
        }

    def list_batches(self, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        return ([{"batchId": "batch-1", "status": "completed"}], 1)

    def get_batch_detail(self, batch_id: str, record_limit: int = 100) -> dict | None:
        if batch_id == "missing":
            return None
        return {"batch": {"batchId": batch_id}, "stageStats": [], "records": []}

    def list_events(self, page: int = 1, limit: int = 20, filters: dict | None = None) -> tuple[list[dict], int]:
        return ([{"id": 1, "eventType": "script_injection", "riskLevel": "high"}], 1)

    def get_geo_summary(self) -> list[dict]:
        return [{"countryCode": "UNKNOWN", "countryName": "Unknown", "totalProxies": 2}]


class SecurityApiRoutesTest(unittest.TestCase):
    def test_security_routes_return_structured_payloads(self) -> None:
        if importlib.util.find_spec("flask") is None:
            self.skipTest("Flask is not installed in this Python environment")

        from api.routes import security_routes
        from api.app_factory import create_app

        original_service = security_routes.SecurityQueryService
        security_routes.SecurityQueryService = FakeSecurityQueryService
        try:
            app = create_app()
            client = app.test_client()

            overview = client.get("/api/security/overview")
            self.assertEqual(overview.status_code, 200)
            self.assertEqual(overview.get_json()["riskCounts"]["unknown"], 1)
            self.assertIn("funnelStats", overview.get_json())
            self.assertEqual(overview.get_json()["protocolCounts"]["https"], 1)

            batches = client.get("/api/security/batches")
            self.assertEqual(batches.status_code, 200)
            self.assertEqual(batches.get_json()["data"][0]["batchId"], "batch-1")

            detail = client.get("/api/security/batches/batch-1")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.get_json()["batch"]["batchId"], "batch-1")

            missing = client.get("/api/security/batches/missing")
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.get_json()["error"], "scan_batch_not_found")

            events = client.get("/api/security/events")
            self.assertEqual(events.status_code, 200)
            self.assertEqual(events.get_json()["data"][0]["eventType"], "script_injection")

            geo = client.get("/api/security/geo")
            self.assertEqual(geo.status_code, 200)
            self.assertEqual(geo.get_json()["data"][0]["countryName"], "Unknown")
        finally:
            security_routes.SecurityQueryService = original_service


if __name__ == "__main__":
    unittest.main()
