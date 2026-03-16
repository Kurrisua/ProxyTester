from __future__ import annotations

import requests

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult

IP_DIRECT_PROVIDERS = [
    {
        "name": "ip-api-direct",
        "url": "http://ip-api.com/json/{ip}",
        "parser": lambda data: None if data.get("status") != "success" else {
            "country": data.get("country"),
            "city": data.get("city"),
            "isp": data.get("isp"),
        },
    },
    {
        "name": "ipinfo-direct",
        "url": "https://ipinfo.io/{ip}/json",
        "parser": lambda data: {
            "country": data.get("country"),
            "city": data.get("city"),
            "isp": data.get("org"),
        },
    },
]


class IpGeoFallbackChecker(BaseChecker):
    name = "ip_geo_fallback_checker"
    stage = "geo"
    order = 80

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_alive and not context.proxy.country

    def check(self, context: CheckContext) -> CheckResult:
        for provider in IP_DIRECT_PROVIDERS:
            try:
                response = requests.get(provider["url"].format(ip=context.proxy.ip), timeout=self.timeout)
                parsed = provider["parser"](response.json())
                if parsed:
                    return CheckResult(
                        self.name,
                        self.stage,
                        True,
                        metadata={
                            "geo_source": provider["name"],
                            "country": parsed.get("country"),
                            "city": parsed.get("city"),
                            "isp": parsed.get("isp"),
                        },
                    )
            except Exception:
                continue
        return CheckResult(self.name, self.stage, False, error="ip_geo_fallback_failed")
