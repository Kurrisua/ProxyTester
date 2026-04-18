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
