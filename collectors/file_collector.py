from __future__ import annotations

from core.models.proxy_model import ProxyModel


class FileProxyCollector:
    def collect(self, file_path: str) -> set[ProxyModel]:
        proxies: set[ProxyModel] = set()
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
                    continue
        return proxies
