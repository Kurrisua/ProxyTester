from __future__ import annotations

from core.models.proxy_model import ProxyModel
from storage.mysql.proxy_repository import MySQLProxyRepository


class ProxyQueryService:
    def __init__(self, repository=None):
        self.repository = repository or MySQLProxyRepository()

    def close(self):
        self.repository.__exit__(None, None, None)

    def list_proxies(self, filters: dict | None = None, page: int = 1, limit: int = 10, sort: str = "response_time") -> tuple[list[dict], int]:
        proxies, total = self.repository.list_proxies(filters=filters, page=page, limit=limit, sort=sort)
        return [self.to_dict(proxy) for proxy in proxies], total

    def get_filters(self) -> dict:
        return self.repository.get_filters()

    def get_stats(self) -> dict:
        return self.repository.get_stats()

    def get_high_quality_proxies(self, min_score: int = 2, limit: int = 10) -> list[dict]:
        return [self.to_dict(proxy) for proxy in self.repository.get_high_quality_proxies(min_score, limit)]

    def delete_proxy(self, ip: str, port: int) -> None:
        self.repository.delete_proxy(ip, port)

    @staticmethod
    def to_dict(proxy: ProxyModel) -> dict:
        total = proxy.success_count + proxy.fail_count
        success_rate = round((proxy.success_count / total * 100) if total > 0 else 0, 1)
        status = "失效"
        status_color = "red"
        if proxy.is_alive:
            if proxy.response_time and proxy.response_time < 500:
                status = "存活"
                status_color = "green"
            else:
                status = "缓慢"
                status_color = "yellow"

        anonymity_map = {
            "high_anonymous": "高匿",
            "anonymous": "匿名",
            "transparent": "透明",
        }
        types = []
        if proxy.http:
            types.append("HTTP")
        if proxy.https:
            types.append("HTTPS")
        if proxy.socks5:
            types.append("SOCKS5")
        return {
            "id": f"{proxy.ip}:{proxy.port}",
            "ip": proxy.ip,
            "port": proxy.port,
            "source": proxy.source,
            "location": {
                "country": proxy.country or "Unknown",
                "city": proxy.city or "Unknown",
                "flag": "N/A",
                "lat": 0,
                "lng": 0,
            },
            "types": types,
            "anonymity": anonymity_map.get(proxy.anonymity, "未知"),
            "speed": proxy.response_time or 0,
            "successRate": success_rate,
            "businessScore": proxy.business_score,
            "qualityScore": proxy.quality_score,
            "securityRisk": proxy.security_risk,
            "securityFlags": proxy.security_flags,
            "lastCheck": proxy.last_check_time.strftime("%Y-%m-%d %H:%M:%S") if proxy.last_check_time else "Unknown",
            "status": status,
            "statusColor": status_color,
        }
