from __future__ import annotations

import hashlib
from typing import Any

import requests

from core.models.proxy_model import ProxyModel
from security.access.models import AccessResult
from utils.http_client import requests_proxies, timed_get


class AccessClient:
    def __init__(self, timeout: int = 10, max_body_bytes: int = 256_000, user_agent: str | None = None):
        self.timeout = timeout
        self.max_body_bytes = max_body_bytes
        self.user_agent = user_agent

    def fetch_direct(self, url: str) -> AccessResult:
        return self._fetch(url, mode="direct", proxies=None)

    def fetch_via_proxy(self, url: str, proxy: ProxyModel) -> AccessResult:
        return self._fetch(url, mode="proxy", proxies=requests_proxies(proxy.ip, proxy.port, proxy.proxy_type))

    def _fetch(self, url: str, *, mode: str, proxies: dict[str, str] | None) -> AccessResult:
        try:
            response, elapsed_ms = timed_get(url, proxies=proxies, timeout=self.timeout, headers=self._headers())
            body = response.content[: self.max_body_bytes]
            text = self._decode_text(response, body)
            return AccessResult(
                success=True,
                mode=mode,
                target_url=url,
                final_url=response.url,
                status_code=response.status_code,
                response_headers={key: value for key, value in response.headers.items()},
                body_text=text,
                body_bytes_sha256=hashlib.sha256(body).hexdigest(),
                body_size=len(response.content),
                mime_type=response.headers.get("Content-Type"),
                elapsed_ms=elapsed_ms,
                redirect_chain=self._redirect_chain(response),
            )
        except requests.Timeout as exc:
            return self._error_result(url, mode, "timeout", exc)
        except requests.ConnectionError as exc:
            return self._error_result(url, mode, "network_error", exc)
        except requests.RequestException as exc:
            return self._error_result(url, mode, "request_error", exc)
        except Exception as exc:
            return self._error_result(url, mode, "unknown_error", exc)

    @staticmethod
    def _decode_text(response: requests.Response, body: bytes) -> str | None:
        content_type = response.headers.get("Content-Type", "")
        if not any(marker in content_type for marker in ("text", "html", "json", "javascript")):
            return None
        encoding = response.encoding or "utf-8"
        return body.decode(encoding, errors="replace")

    @staticmethod
    def _redirect_chain(response: requests.Response) -> list[dict[str, Any]]:
        return [
            {"statusCode": item.status_code, "url": item.url, "location": item.headers.get("Location")}
            for item in response.history
        ]

    @staticmethod
    def _error_result(url: str, mode: str, error_type: str, exc: Exception) -> AccessResult:
        return AccessResult(False, mode, url, error_type=error_type, error_message=str(exc))

    def _headers(self) -> dict[str, str] | None:
        if not self.user_agent:
            return None
        return {"User-Agent": self.user_agent}
