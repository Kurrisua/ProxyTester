from __future__ import annotations

from checkers.registry import build_default_checkers
from collectors import DEFAULT_LAST_DATA_PATH, FileProxyCollector
from scheduler.check_pipeline import CheckPipeline
from scoring.composite_scorer import build_default_scorers
from security.registry import build_default_security_checkers
from storage.mysql.proxy_repository import MySQLProxyRepository


class ProxyCheckService:
    def __init__(self, repository=None):
        self.repository = repository

    def load_from_file(self, file_path: str | None = None):
        file_path = file_path or str(DEFAULT_LAST_DATA_PATH)
        return FileProxyCollector().collect(file_path)

    def run_full_check(self, proxies, max_workers: int = 150, save_to_db: bool = True):
        repository = self.repository
        if save_to_db and repository is None:
            repository = MySQLProxyRepository()
        pipeline = CheckPipeline(
            checkers=build_default_checkers(),
            security_checkers=build_default_security_checkers(),
            scorers=build_default_scorers(),
            repository=repository if save_to_db else None,
            max_workers=max_workers,
        )
        contexts = pipeline.run_batch(proxies)
        alive = [context.proxy for context in contexts if context.proxy.is_alive]
        if save_to_db and repository is not None:
            repository.__exit__(None, None, None)
        return alive
