from __future__ import annotations

from storage.mysql.security_query_repository import MySQLSecurityQueryRepository


class SecurityQueryService:
    def __init__(self, repository=None):
        self.repository = repository or MySQLSecurityQueryRepository()

    def close(self) -> None:
        self.repository.close()

    def get_overview(self) -> dict:
        return self.repository.get_overview()

    def list_batches(self, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        return self.repository.list_batches(page=page, limit=limit)

    def get_batch_detail(self, batch_id: str, record_limit: int = 100) -> dict | None:
        return self.repository.get_batch_detail(batch_id=batch_id, record_limit=record_limit)

    def list_events(self, page: int = 1, limit: int = 20, filters: dict | None = None) -> tuple[list[dict], int]:
        return self.repository.list_events(page=page, limit=limit, filters=filters)

    def get_geo_summary(self) -> list[dict]:
        return self.repository.get_geo_summary()

    def get_geo_region_detail(self, country: str) -> dict:
        return self.repository.get_geo_region_detail(country)

    def get_proxy_security_detail(self, ip: str, port: int, record_limit: int = 80, event_limit: int = 40) -> dict:
        return self.repository.get_proxy_security_detail(ip, port, record_limit=record_limit, event_limit=event_limit)

    def get_proxy_security_history(self, ip: str, port: int, limit: int = 80) -> list[dict]:
        return self.repository.get_proxy_security_history(ip, port, limit=limit)

    def get_proxy_security_events(self, ip: str, port: int, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        return self.repository.get_proxy_security_events(ip, port, page=page, limit=limit)

    def get_event_detail(self, event_id: int) -> dict | None:
        return self.repository.get_event_detail(event_id)

    def get_behavior_stats(self) -> list[dict]:
        return self.repository.get_behavior_stats()

    def get_risk_trend(self, days: int = 14) -> list[dict]:
        return self.repository.get_risk_trend(days=days)

    def get_event_type_distribution(self) -> list[dict]:
        return self.repository.get_event_type_distribution()

    def get_risk_distribution(self) -> dict:
        return self.repository.get_risk_distribution()
