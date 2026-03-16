from __future__ import annotations

import requests

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import requests_proxies

BUSINESS_TARGETS = [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "Baidu", "url": "https://www.baidu.com"},
    {"name": "GitHub", "url": "https://github.com"},
]


class BusinessAvailabilityChecker(BaseChecker):
    name = "business_availability_checker"
    stage = "business"
    order = 90

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> CheckResult:
        proxies = requests_proxies(context.proxy.ip, context.proxy.port, context.proxy.proxy_type)
        accessible: list[str] = []
        for target in BUSINESS_TARGETS:
            try:
                response = requests.get(
                    target["url"],
                    proxies=proxies,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                if 200 <= response.status_code < 300:
                    accessible.append(target["name"])
            except Exception:
                continue
        return CheckResult(
            self.name,
            self.stage,
            bool(accessible),
            metadata={"business_score": len(accessible), "accessible_targets": accessible},
        )
