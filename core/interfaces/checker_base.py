from __future__ import annotations

from abc import ABC, abstractmethod

from core.context.check_context import CheckContext
from core.models.results import CheckResult, SecurityResult


class BaseChecker(ABC):
    name = "base_checker"
    stage = "base"
    order = 100
    enabled = True
    blocking = False

    @abstractmethod
    def supports(self, context: CheckContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def check(self, context: CheckContext) -> CheckResult:
        raise NotImplementedError


class BaseSecurityChecker(ABC):
    name = "base_security_checker"
    stage = "security"
    order = 100
    enabled = True

    @abstractmethod
    def supports(self, context: CheckContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def check(self, context: CheckContext) -> SecurityResult:
        raise NotImplementedError


class BaseScorer(ABC):
    name = "base_scorer"

    @abstractmethod
    def score(self, context: CheckContext) -> None:
        raise NotImplementedError


class BaseProxyRepository(ABC):
    @abstractmethod
    def save_proxy(self, proxy) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_proxies(self, filters: dict | None = None, page: int = 1, limit: int = 10, sort: str = "response_time") -> tuple[list, int]:
        raise NotImplementedError

    @abstractmethod
    def get_filters(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_high_quality_proxies(self, min_score: int = 2, limit: int = 10) -> list:
        raise NotImplementedError

    @abstractmethod
    def delete_proxy(self, ip: str, port: int) -> None:
        raise NotImplementedError
