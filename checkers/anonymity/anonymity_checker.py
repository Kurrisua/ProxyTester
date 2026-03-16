from __future__ import annotations

import time

import requests

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import requests_proxies

DETECTION_TARGETS = [
    {"name": "httpbin", "url": "http://httpbin.org/get"},
    {"name": "ip-api", "url": "http://ip-api.com/json"},
]


class AnonymityChecker(BaseChecker):
    name = "anonymity_checker"
    stage = "anonymity"
    order = 60

    def __init__(self, timeout: int = 10, retry_times: int = 2):
        self.timeout = timeout
        self.retry_times = retry_times

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> CheckResult:
        real_ip = self._load_real_ip()
        if not real_ip:
            return CheckResult(self.name, self.stage, False, error="real_ip_lookup_failed")

        proxies = requests_proxies(context.proxy.ip, context.proxy.port, context.proxy.proxy_type)
        if not proxies:
            return CheckResult(self.name, self.stage, False, error="unsupported_proxy_type")

        for target in DETECTION_TARGETS:
            for _ in range(self.retry_times + 1):
                try:
                    started = time.time()
                    response = requests.get(target["url"], proxies=proxies, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.json()
                    origin = data.get("origin", "") if isinstance(data, dict) else ""
                    origin_ips = [ip.strip() for ip in origin.split(",") if ip.strip()]
                    headers = data.get("headers", {}) if isinstance(data, dict) else {}
                    anonymity = self._determine(real_ip, origin_ips, headers)
                    return CheckResult(
                        self.name,
                        self.stage,
                        True,
                        latency_ms=(time.time() - started) * 1000,
                        metadata={"anonymity": anonymity},
                    )
                except Exception:
                    continue
        return CheckResult(self.name, self.stage, False, error="anonymity_detection_failed")

    def _load_real_ip(self) -> str | None:
        for _ in range(self.retry_times + 1):
            try:
                response = requests.get("http://httpbin.org/ip", timeout=self.timeout)
                return response.json().get("origin", "").split(",")[0].strip()
            except Exception:
                continue
        return None

    @staticmethod
    def _determine(real_ip: str, origin_ips: list[str], headers: dict) -> str:
        if real_ip in origin_ips:
            return "transparent"
        if any(header in headers for header in ["X-Forwarded-For", "X-Real-Ip", "Via", "Proxy-Connection"]):
            return "anonymous"
        return "high_anonymous"
