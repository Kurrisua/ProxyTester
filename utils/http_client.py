from __future__ import annotations

import socket
import time

import requests


def requests_proxies(ip: str, port: int, proxy_type: str | None = None) -> dict | None:
    if proxy_type == "SOCKS5":
        return {
            "http": f"socks5h://{ip}:{port}",
            "https": f"socks5h://{ip}:{port}",
        }
    if proxy_type in {"HTTPS", "HTTP_HTTPS", "HTTPS_SOCKS5", "ALL"}:
        return {
            "http": f"http://{ip}:{port}",
            "https": f"http://{ip}:{port}",
        }
    if proxy_type == "HTTP":
        return {"http": f"http://{ip}:{port}"}
    return {
        "http": f"http://{ip}:{port}",
        "https": f"http://{ip}:{port}",
    }


def timed_get(url: str, *, proxies: dict | None = None, timeout: int = 10, allow_redirects: bool = True):
    started = time.time()
    response = requests.get(
        url,
        proxies=proxies,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )
    latency_ms = (time.time() - started) * 1000
    return response, latency_ms


def tcp_connect(ip: str, port: int, timeout: int = 3) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()
        return True
    except Exception:
        return False


def open_socket(ip: str, port: int, timeout: int = 5):
    return socket.create_connection((ip, port), timeout=timeout)
