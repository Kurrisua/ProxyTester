from __future__ import annotations

import json
from pathlib import Path

from core.interfaces import BaseProxyDataTransformer


class LastDataJsonTransformer(BaseProxyDataTransformer):
    def transform(self, source_path: str, output_path: str) -> dict:
        source = Path(source_path)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        proxies: list[dict] = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                parts = line.split()
                endpoint = parts[0]
                source_name = parts[1] if len(parts) > 1 else "unknown"

                try:
                    ip, port = endpoint.split(":")
                    proxies.append(
                        {
                            "ip": ip,
                            "port": int(port),
                            "source": source_name,
                            "raw": line,
                            "line_number": line_number,
                            "tags": [],
                            "metadata": {},
                        }
                    )
                except ValueError:
                    continue

        payload = {
            "dataset": source.stem,
            "source_file": str(source),
            "record_count": len(proxies),
            "format": "proxy-collection/v1",
            "proxies": proxies,
        }

        with target.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        return payload
