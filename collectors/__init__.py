"""Proxy collectors."""

from collectors.deadpool_runner import DeadpoolSeedRunner
from collectors.defaults import (
    DEADPOOL_DIR,
    DEADPOOL_FIR_PATH,
    DEADPOOL_GIT_PATH,
    DEADPOOL_HTTP_PATH,
    DEADPOOL_LAST_DATA_PATH,
    DEFAULT_LAST_DATA_JSON_PATH,
    DEFAULT_LAST_DATA_PATH,
)
from collectors.file_collector import FileProxyCollector
from collectors.source_provider import DefaultProxySourceProvider
from collectors.transformers.last_data_to_json import LastDataJsonTransformer

__all__ = [
    "DEADPOOL_DIR",
    "DEADPOOL_FIR_PATH",
    "DEADPOOL_GIT_PATH",
    "DEADPOOL_HTTP_PATH",
    "DEADPOOL_LAST_DATA_PATH",
    "DEFAULT_LAST_DATA_JSON_PATH",
    "DEFAULT_LAST_DATA_PATH",
    "DeadpoolSeedRunner",
    "DefaultProxySourceProvider",
    "FileProxyCollector",
    "LastDataJsonTransformer",
]
