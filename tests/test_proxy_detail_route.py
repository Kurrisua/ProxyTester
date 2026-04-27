from __future__ import annotations

import importlib.util
import unittest


class FakeProxyQueryService:
    def close(self) -> None:
        pass

    def get_proxy_detail(self, ip: str, port: int) -> dict | None:
        if ip == "127.0.0.2":
            return None
        return {
            "proxy": {
                "id": f"{ip}:{port}",
                "ip": ip,
                "port": port,
                "status": "alive",
                "securityRisk": "unknown",
            },
            "security": {
                "stageStats": [],
                "records": [],
                "events": [],
                "batches": [],
                "resources": [],
                "certificates": [],
            },
        }


class ProxyDetailRouteTest(unittest.TestCase):
    def test_proxy_detail_route_returns_structured_payload(self) -> None:
        if importlib.util.find_spec("flask") is None:
            self.skipTest("Flask is not installed in this Python environment")

        from api.routes import proxy_routes
        from api.app_factory import create_app

        original_service = proxy_routes.ProxyQueryService
        proxy_routes.ProxyQueryService = FakeProxyQueryService
        try:
            app = create_app()
            client = app.test_client()

            response = client.get("/api/proxies/127.0.0.1:8080")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["proxy"]["id"], "127.0.0.1:8080")
            self.assertEqual(payload["security"]["records"], [])

            missing = client.get("/api/proxies/127.0.0.2:8080")
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.get_json()["error"], "proxy_not_found")
        finally:
            proxy_routes.ProxyQueryService = original_service


if __name__ == "__main__":
    unittest.main()
