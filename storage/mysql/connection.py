from __future__ import annotations

import os

import pymysql


def _get_env(primary: str, legacy: str, default: str) -> str:
    return os.getenv(primary) or os.getenv(legacy) or default


def get_connection_config() -> dict:
    return {
        "host": _get_env("PROXYTESTER_DB_HOST", "DB_HOST", "localhost"),
        "port": int(_get_env("PROXYTESTER_DB_PORT", "DB_PORT", "3307")),
        "user": _get_env("PROXYTESTER_DB_USER", "DB_USER", "root"),
        "password": _get_env("PROXYTESTER_DB_PASSWORD", "DB_PASSWORD", ""),
        "database": _get_env("PROXYTESTER_DB_NAME", "DB_NAME", "proxy_pool"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }


def create_connection():
    return pymysql.connect(**get_connection_config())
