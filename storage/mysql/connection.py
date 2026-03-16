from __future__ import annotations

import os

import pymysql


def create_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3307)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "proxy_pool"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
