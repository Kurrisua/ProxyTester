from __future__ import annotations

import logging

from checkers.registry import build_default_checkers
from collectors import DEFAULT_LAST_DATA_PATH, FileProxyCollector
from scheduler.check_pipeline import CheckPipeline
from scoring.composite_scorer import build_default_scorers
from security.registry import build_default_security_checkers
from storage.mysql.proxy_repository import MySQLProxyRepository


class ProxyCheckService:
    def __init__(self, repository=None, scan_repository=None):
        self.repository = repository
        self.scan_repository = scan_repository
        self.logger = logging.getLogger(__name__)

    def load_from_file(self, file_path: str | None = None):
        file_path = file_path or str(DEFAULT_LAST_DATA_PATH)
        self.logger.info("Loading proxies from file: %s", file_path)
        return FileProxyCollector().collect(file_path)

    def run_full_check(self, proxies, max_workers: int = 150, save_to_db: bool = True):
        total = len(proxies)
        self.logger.info(
            "Preparing full proxy check (count=%s, max_workers=%s, save_to_db=%s)",
            total,
            max_workers,
            save_to_db,
        )
        repository = self.repository
        scan_repository = self.scan_repository
        created_scan_repository = None
        if save_to_db and repository is None:
            self.logger.info("Creating MySQL repository for persistence")
            repository = MySQLProxyRepository()
        if save_to_db and scan_repository is None:
            from storage.mysql.security_repositories import MySQLSecurityRepository

            self.logger.info("Creating MySQL security repository for scan records")
            scan_repository = MySQLSecurityRepository()
            created_scan_repository = scan_repository
        pipeline = CheckPipeline(
            checkers=build_default_checkers(),
            security_checkers=build_default_security_checkers(),
            scorers=build_default_scorers(),
            repository=repository if save_to_db else None,
            scan_repository=scan_repository if save_to_db else self.scan_repository,
            max_workers=max_workers,
        )
        contexts = pipeline.run_batch(proxies)
        alive = [context.proxy for context in contexts if context.proxy.is_alive]
        self.logger.info("Full proxy check completed: %s/%s proxies alive", len(alive), total)
        if save_to_db and repository is not None:
            self.logger.info("Closing MySQL repository")
            repository.__exit__(None, None, None)
        if created_scan_repository is not None:
            self.logger.info("Closing MySQL security repository")
            created_scan_repository.close()
        return alive
