from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import open_socket


class Socks5Checker(BaseChecker):
    name = "socks5_checker"
    stage = "protocol"
    order = 20

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_alive

    def check(self, context: CheckContext) -> CheckResult:
        try:
            sock = open_socket(context.proxy.ip, context.proxy.port, self.timeout)
            sock.sendall(b"\x05\x01\x00")
            response = sock.recv(2)
            sock.close()
            ok = response == b"\x05\x00"
            return CheckResult(self.name, self.stage, ok, metadata={"socks5": ok})
        except Exception as exc:
            return CheckResult(self.name, self.stage, False, error=str(exc), metadata={"socks5": False})
