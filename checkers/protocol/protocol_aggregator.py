from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult


class ProtocolAggregator(BaseChecker):
    name = "protocol_aggregator"
    stage = "protocol"
    order = 50

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_alive

    def check(self, context: CheckContext) -> CheckResult:
        protocol_results = {item.checker_name: item for item in context.check_results}
        http_ok = bool(protocol_results.get("http_checker") and protocol_results["http_checker"].success)
        https_ok = bool(protocol_results.get("https_checker") and protocol_results["https_checker"].success)
        socks_ok = bool(protocol_results.get("socks5_checker") and protocol_results["socks5_checker"].success)
        success = http_ok or https_ok or socks_ok
        return CheckResult(
            self.name,
            self.stage,
            success,
            metadata={
                "http": http_ok,
                "https": https_ok,
                "socks5": socks_ok,
            },
        )
