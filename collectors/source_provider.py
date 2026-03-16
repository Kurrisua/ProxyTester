from __future__ import annotations

from core.interfaces import BaseProxySourceProvider, ProxySourceDefinition

from collectors.defaults import DEFAULT_LAST_DATA_PATH


class DefaultProxySourceProvider(BaseProxySourceProvider):
    def list_sources(self) -> list[ProxySourceDefinition]:
        return [
            ProxySourceDefinition(
                name="lastData",
                kind="file",
                location=str(DEFAULT_LAST_DATA_PATH),
                description="Default local proxy dataset used by the checker pipeline.",
                metadata={
                    "format": "ip:port source_name",
                    "extensible_kinds": ["file", "http_api", "feed", "crawler", "plugin"],
                },
            )
        ]
