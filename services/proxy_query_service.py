from __future__ import annotations

from core.models.proxy_model import ProxyModel


class ProxyQueryService:
    def __init__(self, repository=None):
        if repository is None:
            from storage.mysql.proxy_repository import MySQLProxyRepository

            repository = MySQLProxyRepository()
        self.repository = repository

    def close(self):
        if hasattr(self.repository, "__exit__"):
            self.repository.__exit__(None, None, None)
        elif hasattr(self.repository, "close"):
            self.repository.close()

    def list_proxies(self, filters: dict | None = None, page: int = 1, limit: int = 10, sort: str = "response_time") -> tuple[list[dict], int]:
        proxies, total = self.repository.list_proxies(filters=filters, page=page, limit=limit, sort=sort)
        return [self.to_dict(proxy) for proxy in proxies], total

    def get_filters(self) -> dict:
        return self.repository.get_filters()

    def get_stats(self) -> dict:
        return self.repository.get_stats()

    def get_high_quality_proxies(self, min_score: int = 2, limit: int = 10) -> list[dict]:
        return [self.to_dict(proxy) for proxy in self.repository.get_high_quality_proxies(min_score, limit)]

    def get_proxy_detail(self, ip: str, port: int) -> dict | None:
        if not hasattr(self.repository, "get_proxy_by_address"):
            return None

        proxy = self.repository.get_proxy_by_address(ip, port)
        if proxy is None:
            return None

        from storage.mysql.security_query_repository import MySQLSecurityQueryRepository

        security_repository = MySQLSecurityQueryRepository()
        try:
            security_detail = security_repository.get_proxy_security_detail(ip, port)
        finally:
            security_repository.close()

        return {
            "proxy": self.to_dict(proxy),
            "security": security_detail,
        }

    def delete_proxy(self, ip: str, port: int) -> None:
        self.repository.delete_proxy(ip, port)

    @staticmethod
    def to_dict(proxy: ProxyModel) -> dict:
        total = proxy.success_count + proxy.fail_count
        success_rate = round((proxy.success_count / total * 100) if total > 0 else 0, 1)
        status = "dead"
        status_color = "red"
        if proxy.is_alive:
            if proxy.response_time and proxy.response_time < 500:
                status = "alive"
                status_color = "green"
            else:
                status = "slow"
                status_color = "yellow"

        anonymity_map = {
            "high_anonymous": "high_anonymous",
            "anonymous": "anonymous",
            "transparent": "transparent",
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
            "anonymity": anonymity_map.get(proxy.anonymity, "unknown"),
            "speed": proxy.response_time or 0,
            "successRate": success_rate,
            "businessScore": proxy.business_score,
            "qualityScore": proxy.quality_score,
            "securityRisk": proxy.security_risk,
            "securityScore": proxy.security_score,
            "behaviorClass": proxy.behavior_class,
            "securityFlags": proxy.security_flags,
            "securitySummary": {
                "hasContentTampering": proxy.has_content_tampering,
                "hasResourceReplacement": proxy.has_resource_replacement,
                "hasMitmRisk": proxy.has_mitm_risk,
                "anomalyTriggerCount": proxy.anomaly_trigger_count,
                "securityCheckCount": proxy.security_check_count,
                "anomalyTriggerRate": proxy.anomaly_trigger_rate,
                "triggerPattern": ProxyQueryService._trigger_pattern(proxy),
                "confidenceLevel": ProxyQueryService._confidence_level(proxy),
                "evidenceSummary": proxy.security_evidence.get("summary") if isinstance(proxy.security_evidence, dict) else None,
                "lastSecurityCheck": proxy.last_security_check_time.strftime("%Y-%m-%d %H:%M:%S") if proxy.last_security_check_time else None,
            },
            "lastCheck": proxy.last_check_time.strftime("%Y-%m-%d %H:%M:%S") if proxy.last_check_time else "Unknown",
            "status": status,
            "statusColor": status_color,
        }

    @staticmethod
    def _trigger_pattern(proxy: ProxyModel) -> str:
        if isinstance(proxy.security_evidence, dict):
            summary = proxy.security_evidence.get("summary") or {}
            if summary.get("triggerPattern"):
                return summary["triggerPattern"]
        for tag in ("delayed_trigger", "conditional_trigger"):
            if tag in proxy.security_flags:
                return tag
        if proxy.anomaly_trigger_count > 0 and proxy.security_check_count > 0:
            if proxy.anomaly_trigger_count == proxy.security_check_count:
                return "stable_anomalous"
            return "single_round_anomalous"
        return "none" if proxy.security_check_count else "not_observed"

    @staticmethod
    def _confidence_level(proxy: ProxyModel) -> str:
        for tag in ("confidence_high", "confidence_medium", "confidence_low"):
            if tag in proxy.security_flags:
                return tag.replace("confidence_", "")
        return "unknown"
