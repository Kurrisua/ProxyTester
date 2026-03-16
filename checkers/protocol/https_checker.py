from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult
from utils.http_client import open_socket


class HttpsChecker(BaseChecker):
    name = "https_checker"
    stage = "protocol"
    order = 30

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_alive

    def check(self, context: CheckContext) -> CheckResult:
        try:
            sock = open_socket(context.proxy.ip, context.proxy.port, self.timeout)
            request = b"CONNECT www.baidu.com:443 HTTP/1.1\r\nHost: www.baidu.com:443\r\n\r\n"
            sock.sendall(request)
            response = sock.recv(4096)
            sock.close()
            status_line = response.split(b"\r\n", 1)[0]
            ok = status_line.startswith(b"HTTP/") and b"200" in status_line
            return CheckResult(self.name, self.stage, ok, metadata={"https": ok})
        except Exception as exc:
            return CheckResult(self.name, self.stage, False, error=str(exc), metadata={"https": False})
