from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import tcp_connect


class TcpChecker(BaseChecker):
    name = "tcp_checker"
    stage = "connectivity"
    order = 10
    blocking = True

    def __init__(self, timeout: int = 3):
        self.timeout = timeout

    def supports(self, context: CheckContext) -> bool:
        return True

    def check(self, context: CheckContext) -> CheckResult:
        ok = tcp_connect(context.proxy.ip, context.proxy.port, self.timeout)
        return CheckResult(
            checker_name=self.name,
            stage=self.stage,
            success=ok,
            metadata={"alive": ok},
        )
