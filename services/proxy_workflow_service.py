from __future__ import annotations

from pathlib import Path

from collectors import (
    DEFAULT_LAST_DATA_JSON_PATH,
    DEFAULT_LAST_DATA_PATH,
    DeadpoolSeedRunner,
    DefaultProxySourceProvider,
    FileProxyCollector,
    LastDataJsonTransformer,
)
from core.models.proxy_model import ProxyModel
from services.proxy_check_service import ProxyCheckService


class ProxyWorkflowService:
    def __init__(
        self,
        source_provider: DefaultProxySourceProvider | None = None,
        collector: FileProxyCollector | None = None,
        transformer: LastDataJsonTransformer | None = None,
        check_service: ProxyCheckService | None = None,
        deadpool_runner: DeadpoolSeedRunner | None = None,
    ):
        self.source_provider = source_provider or DefaultProxySourceProvider()
        self.collector = collector or FileProxyCollector()
        self.transformer = transformer or LastDataJsonTransformer()
        self.check_service = check_service or ProxyCheckService()
        self.deadpool_runner = deadpool_runner or DeadpoolSeedRunner()

    def run_automated_workflow(
        self,
        refresh_external_sources: bool = True,
        include_deadpool_sources: bool = True,
        max_workers: int = 150,
        save_to_db: bool = True,
        canonical_output_path: str | None = None,
        json_output_path: str | None = None,
    ) -> dict:
        refresh_summary = None
        if refresh_external_sources and include_deadpool_sources:
            refresh_summary = self.deadpool_runner.run()

        self.source_provider = DefaultProxySourceProvider(include_deadpool=include_deadpool_sources)
        collected_proxies, source_stats = self.collect_all_sources()

        canonical_path = Path(canonical_output_path or DEFAULT_LAST_DATA_PATH)
        self.write_canonical_dataset(collected_proxies, canonical_path)

        json_path = Path(json_output_path or DEFAULT_LAST_DATA_JSON_PATH)
        dataset_payload = self.transformer.transform(str(canonical_path), str(json_path))

        alive_proxies = self.check_service.run_full_check(
            list(collected_proxies.values()),
            max_workers=max_workers,
            save_to_db=save_to_db,
        )

        return {
            "success": True,
            "refreshSummary": refresh_summary,
            "sources": source_stats,
            "sourceCount": len(source_stats),
            "collectedCount": len(collected_proxies),
            "aliveCount": len(alive_proxies),
            "savedToDb": save_to_db,
            "canonicalFile": str(canonical_path),
            "jsonFile": str(json_path),
            "jsonRecordCount": dataset_payload.get("record_count", 0),
        }

    def collect_all_sources(self) -> tuple[dict[tuple[str, int], ProxyModel], list[dict]]:
        merged: dict[tuple[str, int], ProxyModel] = {}
        source_stats: list[dict] = []

        for source in self.source_provider.list_sources():
            source_path = Path(source.location)
            if not source.enabled:
                source_stats.append({"name": source.name, "path": str(source_path), "enabled": False, "count": 0, "status": "disabled"})
                continue
            if not source_path.exists():
                source_stats.append({"name": source.name, "path": str(source_path), "enabled": True, "count": 0, "status": "missing"})
                continue

            proxies = self.collector.collect(source)
            for proxy in proxies:
                key = (proxy.ip, proxy.port)
                if key in merged:
                    merged[key].source = self._merge_source_names(merged[key].source, proxy.source)
                else:
                    merged[key] = proxy

            source_stats.append(
                {
                    "name": source.name,
                    "path": str(source_path),
                    "enabled": True,
                    "count": len(proxies),
                    "status": "loaded",
                }
            )

        return merged, source_stats

    def write_canonical_dataset(self, proxies: dict[tuple[str, int], ProxyModel], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for proxy in sorted(proxies.values(), key=lambda item: (item.ip, item.port)):
                handle.write(f"{proxy.ip}:{proxy.port} {proxy.source}\n")

    @staticmethod
    def _merge_source_names(left: str, right: str) -> str:
        names: list[str] = []
        for value in (left, right):
            for item in value.split("|"):
                clean = item.strip()
                if clean and clean not in names:
                    names.append(clean)
        return "|".join(names)
