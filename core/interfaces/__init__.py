"""Stable interfaces shared by services and adapters."""

from core.interfaces.checker_base import (
    BaseChecker,
    BaseProxyRepository,
    BaseScorer,
    BaseSecurityChecker,
)
from core.interfaces.proxy_collection import (
    BaseProxyCollector,
    BaseProxyDataTransformer,
    BaseProxySourceProvider,
    ProxySourceDefinition,
)

__all__ = [
    "BaseChecker",
    "BaseProxyCollector",
    "BaseProxyDataTransformer",
    "BaseProxyRepository",
    "BaseProxySourceProvider",
    "BaseScorer",
    "BaseSecurityChecker",
    "ProxySourceDefinition",
]
