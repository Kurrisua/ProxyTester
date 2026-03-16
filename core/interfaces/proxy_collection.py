from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.models.proxy_model import ProxyModel


@dataclass(slots=True)
class ProxySourceDefinition:
    name: str
    kind: str
    location: str
    enabled: bool = True
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProxySourceProvider(ABC):
    @abstractmethod
    def list_sources(self) -> list[ProxySourceDefinition]:
        raise NotImplementedError


class BaseProxyCollector(ABC):
    @abstractmethod
    def collect(self, source: str | ProxySourceDefinition) -> set[ProxyModel]:
        raise NotImplementedError


class BaseProxyDataTransformer(ABC):
    @abstractmethod
    def transform(self, source_path: str, output_path: str) -> dict[str, Any]:
        raise NotImplementedError
