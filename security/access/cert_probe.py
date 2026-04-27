from __future__ import annotations

import hashlib
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.models.proxy_model import ProxyModel


@dataclass
class CertificateProbeResult:
    success: bool
    mode: str
    host: str
    port: int = 443
    fingerprint_sha256: str | None = None
    issuer: str | None = None
    subject: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    is_self_signed: bool = False
    certificate_summary: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None

    def to_observation(self, *, risk_level: str = "unknown", is_mismatch: bool = False) -> dict[str, Any]:
        return {
            "observation_mode": self.mode,
            "host": self.host,
            "port": self.port,
            "fingerprint_sha256": self.fingerprint_sha256,
            "issuer": self.issuer,
            "subject": self.subject,
            "not_before": self.not_before,
            "not_after": self.not_after,
            "is_self_signed": self.is_self_signed,
            "is_mismatch": is_mismatch,
            "risk_level": risk_level,
            "certificate_summary": {
                **self.certificate_summary,
                "errorType": self.error_type,
            },
            "error_message": self.error_message,
        }


class CertificateProbe:
    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def probe_direct(self, host: str, port: int = 443) -> CertificateProbeResult:
        try:
            with socket.create_connection((host, port), timeout=self.timeout) as sock:
                return self._probe_tls_socket(sock, "direct", host, port)
        except socket.timeout as exc:
            return self._error("direct", host, port, "timeout", exc)
        except OSError as exc:
            return self._error("direct", host, port, "network_error", exc)
        except Exception as exc:
            return self._error("direct", host, port, "unknown_error", exc)

    def probe_via_proxy(self, proxy: ProxyModel, host: str, port: int = 443) -> CertificateProbeResult:
        if proxy.socks5 and not (proxy.http or proxy.https):
            return CertificateProbeResult(
                success=False,
                mode="proxy",
                host=host,
                port=port,
                error_type="unsupported_proxy_type",
                error_message="SOCKS5 certificate probing requires a SOCKS socket dependency that is not installed.",
            )

        try:
            with socket.create_connection((proxy.ip, proxy.port), timeout=self.timeout) as sock:
                self._open_http_connect_tunnel(sock, host, port)
                return self._probe_tls_socket(sock, "proxy", host, port)
        except socket.timeout as exc:
            return self._error("proxy", host, port, "timeout", exc)
        except OSError as exc:
            return self._error("proxy", host, port, "network_error", exc)
        except Exception as exc:
            return self._error("proxy", host, port, "proxy_connect_error", exc)

    def _probe_tls_socket(self, sock: socket.socket, mode: str, host: str, port: int) -> CertificateProbeResult:
        context = ssl.create_default_context()
        try:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                der_cert = tls_sock.getpeercert(binary_form=True)
                cert = tls_sock.getpeercert()
        except ssl.SSLCertVerificationError as exc:
            return self._error(mode, host, port, "tls_validation_error", exc)
        except ssl.SSLError as exc:
            return self._error(mode, host, port, "tls_error", exc)

        fingerprint = hashlib.sha256(der_cert).hexdigest() if der_cert else None
        subject = self._name_to_string(cert.get("subject", ()))
        issuer = self._name_to_string(cert.get("issuer", ()))
        not_before = self._parse_cert_time(cert.get("notBefore"))
        not_after = self._parse_cert_time(cert.get("notAfter"))
        return CertificateProbeResult(
            success=True,
            mode=mode,
            host=host,
            port=port,
            fingerprint_sha256=fingerprint,
            issuer=issuer,
            subject=subject,
            not_before=not_before,
            not_after=not_after,
            is_self_signed=bool(subject and issuer and subject == issuer),
            certificate_summary={
                "version": cert.get("version"),
                "serialNumber": cert.get("serialNumber"),
                "subjectAltName": cert.get("subjectAltName", ()),
            },
        )

    def _open_http_connect_tunnel(self, sock: socket.socket, host: str, port: int) -> None:
        request = (
            f"CONNECT {host}:{port} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Proxy-Connection: keep-alive\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response and len(response) < 8192:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk
        status_line = response.split(b"\r\n", 1)[0].decode("iso-8859-1", errors="replace")
        if " 200 " not in f" {status_line} ":
            raise OSError(f"CONNECT tunnel failed: {status_line}")

    @staticmethod
    def _name_to_string(name: tuple) -> str | None:
        parts: list[str] = []
        for group in name:
            for key, value in group:
                parts.append(f"{key}={value}")
        return ", ".join(parts) if parts else None

    @staticmethod
    def _parse_cert_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
        except ValueError:
            return None

    @staticmethod
    def _error(mode: str, host: str, port: int, error_type: str, exc: Exception) -> CertificateProbeResult:
        return CertificateProbeResult(
            success=False,
            mode=mode,
            host=host,
            port=port,
            error_type=error_type,
            error_message=str(exc),
        )
