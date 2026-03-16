from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import timed_get

DETECTION_TARGETS = [
    {"name": "httpbin", "url": "http://httpbin.org/ip", "kind": "http"},
    {"name": "ip.sb", "url": "http://api.ip.sb/ip", "kind": "text"},
    {"name": "ipinfo", "url": "https://ipinfo.io/ip", "kind": "text"},
    {"name": "ip-api", "url": "http://ip-api.com/json", "kind": "json", "ip_field": "query"},
]


class HttpChecker(BaseChecker):
    name = "http_checker"
    stage = "protocol"
    order = 40

    def __init__(self, timeout: int = 10, retry_times: int = 2):
        self.timeout = timeout
        self.retry_times = retry_times

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_alive

    def check(self, context: CheckContext) -> CheckResult:
        proxies = {
            "http": f"http://{context.proxy.ip}:{context.proxy.port}",
            "https": f"http://{context.proxy.ip}:{context.proxy.port}",
        }
        last_error = None
        for target in DETECTION_TARGETS:
            for _ in range(self.retry_times + 1):
                try:
                    response, latency_ms = timed_get(
                        target["url"],
                        proxies=proxies,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    origin_ip = self._parse_origin(target, response)
                    ok = context.proxy.ip in origin_ip if origin_ip else False
                    if ok:
                        return CheckResult(
                            self.name,
                            self.stage,
                            True,
                            latency_ms=latency_ms,
                            metadata={
                                "http": True,
                                "working_target": target["name"],
                                "origin_ip": origin_ip,
                            },
                        )
                except Exception as exc:
                    last_error = str(exc)
        return CheckResult(self.name, self.stage, False, error=last_error, metadata={"http": False})

    @staticmethod
    def _parse_origin(target: dict, response) -> str:
        if target["kind"] == "json":
            data = response.json()
            return data.get(target.get("ip_field", "origin"), "")
        if target["kind"] == "text":
            return response.text.strip()
        data = response.json()
        return data.get("origin", "")
