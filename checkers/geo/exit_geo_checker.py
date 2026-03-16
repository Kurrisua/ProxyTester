from __future__ import annotations

import requests

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import requests_proxies

GEO_PROVIDERS = [
    {
        "name": "ip-api",
        "url": "http://ip-api.com/json",
        "https_required": False,
        "parser": lambda data: None if data.get("status") != "success" else {
            "ip": data.get("query"),
            "country": data.get("country"),
            "city": data.get("city"),
            "isp": data.get("isp"),
        },
    },
    {
        "name": "ipinfo",
        "url": "https://ipinfo.io/json",
        "https_required": True,
        "parser": lambda data: {
            "ip": data.get("ip"),
            "country": data.get("country"),
            "city": data.get("city"),
            "isp": data.get("org"),
        },
    },
    {
        "name": "ip.sb",
        "url": "https://api.ip.sb/geoip",
        "https_required": True,
        "parser": lambda data: {
            "ip": data.get("ip"),
            "country": data.get("country"),
            "city": data.get("city"),
            "isp": data.get("isp"),
        },
    },
]


class ExitGeoChecker(BaseChecker):
    name = "exit_geo_checker"
    stage = "geo"
    order = 70

    def __init__(self, timeout: int = 6):
        self.timeout = timeout

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable

    def check(self, context: CheckContext) -> CheckResult:
        proxies = requests_proxies(context.proxy.ip, context.proxy.port, context.proxy.proxy_type)
        for provider in GEO_PROVIDERS:
            if provider["https_required"] and not (context.proxy.https or context.proxy.socks5):
                continue
            try:
                response = requests.get(provider["url"], proxies=proxies, timeout=self.timeout)
                response.raise_for_status()
                parsed = provider["parser"](response.json())
                if parsed and parsed.get("country"):
                    return CheckResult(
                        self.name,
                        self.stage,
                        True,
                        metadata={
                            "geo_source": "proxy-exit",
                            "provider": provider["name"],
                            "exit_ip": parsed.get("ip"),
                            "country": parsed.get("country"),
                            "city": parsed.get("city"),
                            "isp": parsed.get("isp"),
                        },
                    )
            except Exception:
                continue
        return CheckResult(self.name, self.stage, False, error="exit_geo_failed")
