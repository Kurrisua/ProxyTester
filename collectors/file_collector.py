from __future__ import annotations

import logging

from core.interfaces import BaseProxyCollector, ProxySourceDefinition
from core.models.proxy_model import ProxyModel


class FileProxyCollector(BaseProxyCollector):
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def collect(self, source: str | ProxySourceDefinition) -> set[ProxyModel]:
        file_path = source.location if isinstance(source, ProxySourceDefinition) else source
        proxies: set[ProxyModel] = set()
        invalid_lines = 0
        with open(file_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()
                try:
                    ip, port = parts[0].split(":")
                    source = parts[1] if len(parts) > 1 else "unknown"
                    proxies.add(ProxyModel(ip=ip, port=int(port), source=source))
                except ValueError:
                    invalid_lines += 1
                    continue
        self.logger.info(
            "Collected %s proxies from file %s (invalid lines: %s)",
            len(proxies),
            file_path,
            invalid_lines,
        )
        return proxies
