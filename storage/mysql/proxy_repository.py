from __future__ import annotations

import logging
from contextlib import AbstractContextManager

from core.interfaces.checker_base import BaseProxyRepository
from core.models.proxy_model import ProxyModel
from storage.mysql.connection import create_connection


class MySQLProxyRepository(BaseProxyRepository, AbstractContextManager):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conn = create_connection()
        self.cursor = self.conn.cursor()
        self.logger.info("Opened MySQL connection for proxy repository")
        self._ensure_columns()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing MySQL connection for proxy repository")
        self.cursor.close()
        self.conn.close()

    def _ensure_columns(self) -> None:
        for column, ddl in {
            "business_score": "ALTER TABLE proxies ADD COLUMN business_score INT DEFAULT 0",
            "quality_score": "ALTER TABLE proxies ADD COLUMN quality_score INT DEFAULT 0",
            "security_risk": "ALTER TABLE proxies ADD COLUMN security_risk VARCHAR(32) DEFAULT 'unknown'",
        }.items():
            try:
                self.cursor.execute(f"SHOW COLUMNS FROM proxies LIKE '{column}'")
                if not self.cursor.fetchone():
                    self.cursor.execute(ddl)
                    self.conn.commit()
            except Exception:
                self.conn.rollback()

    def save_proxy(self, proxy: ProxyModel) -> None:
        data = proxy.to_db_dict()
        self.cursor.execute("SELECT id, success_count, fail_count FROM proxies WHERE ip = %s AND port = %s", (proxy.ip, proxy.port))
        existing = self.cursor.fetchone()
        if existing:
            self.cursor.execute(
                """
                UPDATE proxies SET
                    source = %s,
                    country = %s,
                    city = %s,
                    proxy_type = %s,
                    anonymity = %s,
                    response_time = %s,
                    business_score = %s,
                    success_count = %s,
                    fail_count = %s,
                    last_check_time = %s,
                    is_alive = %s,
                    quality_score = %s,
                    security_risk = %s
                WHERE id = %s
                """,
                (
                    data["source"],
                    data["country"],
                    data["city"],
                    data["proxy_type"],
                    data["anonymity"],
                    data["response_time"],
                    data["business_score"],
                    existing["success_count"] + data["success_count"],
                    existing["fail_count"] + data["fail_count"],
                    data["last_check_time"],
                    data["is_alive"],
                    data["quality_score"],
                    data["security_risk"],
                    existing["id"],
                ),
            )
        else:
            self.cursor.execute(
                """
                INSERT INTO proxies (
                    ip, port, source, country, city, proxy_type, anonymity,
                    response_time, business_score, success_count, fail_count,
                    last_check_time, is_alive, quality_score, security_risk
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    data["ip"],
                    data["port"],
                    data["source"],
                    data["country"],
                    data["city"],
                    data["proxy_type"],
                    data["anonymity"],
                    data["response_time"],
                    data["business_score"],
                    data["success_count"],
                    data["fail_count"],
                    data["last_check_time"],
                    data["is_alive"],
                    data["quality_score"],
                    data["security_risk"],
                ),
            )
        self.conn.commit()

    def list_proxies(self, filters: dict | None = None, page: int = 1, limit: int = 10, sort: str = "response_time") -> tuple[list[ProxyModel], int]:
        filters = filters or {}
        conditions = []
        params: list = []
        if filters.get("country"):
            conditions.append("country = %s")
            params.append(filters["country"])
        if filters.get("proxy_type"):
            conditions.append("proxy_type LIKE %s")
            params.append(f"%{filters['proxy_type']}%")
        if filters.get("status") == "存活":
            conditions.append("is_alive = 1 AND response_time < 500")
        elif filters.get("status") == "失效":
            conditions.append("is_alive = 0")
        elif filters.get("status") == "缓慢":
            conditions.append("is_alive = 1 AND response_time >= 500")
        if filters.get("min_business_score") is not None:
            conditions.append("business_score >= %s")
            params.append(filters["min_business_score"])

        sql = "SELECT * FROM proxies"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        order_by = "last_check_time DESC"
        if sort == "response_time":
            order_by = "CASE WHEN response_time IS NULL OR response_time = 0 THEN 999999 ELSE response_time END ASC"
        elif sort == "success_rate":
            order_by = "(success_count / NULLIF(success_count + fail_count, 0)) DESC"
        elif sort == "business_score":
            order_by = "business_score DESC, CASE WHEN response_time IS NULL OR response_time = 0 THEN 999999 ELSE response_time END ASC"
        elif sort == "quality_score":
            order_by = "quality_score DESC, CASE WHEN response_time IS NULL OR response_time = 0 THEN 999999 ELSE response_time END ASC"

        offset = (page - 1) * limit
        sql += f" ORDER BY {order_by} LIMIT %s OFFSET %s"
        query_params = [*params, limit, offset]
        self.cursor.execute(sql, query_params)
        rows = self.cursor.fetchall()

        count_sql = "SELECT COUNT(*) AS total FROM proxies"
        if conditions:
            count_sql += " WHERE " + " AND ".join(conditions)
        self.cursor.execute(count_sql, params)
        total = self.cursor.fetchone()["total"]
        return [ProxyModel.from_db_row(row) for row in rows], total

    def get_filters(self) -> dict:
        self.cursor.execute("SELECT DISTINCT country FROM proxies WHERE country IS NOT NULL AND country != ''")
        countries = [row["country"] for row in self.cursor.fetchall()]

        self.cursor.execute("SELECT country, COUNT(*) as count FROM proxies GROUP BY country ORDER BY count DESC LIMIT 1")
        main_country = self.cursor.fetchone()

        self.cursor.execute("SELECT DISTINCT proxy_type FROM proxies WHERE proxy_type IS NOT NULL AND proxy_type != ''")
        proxy_types: list[str] = []
        for row in self.cursor.fetchall():
            for item in row["proxy_type"].split("_"):
                if item not in proxy_types:
                    proxy_types.append(item)

        self.cursor.execute(
            """
            SELECT business_score, COUNT(*) as count
            FROM proxies
            WHERE is_alive = 1
            GROUP BY business_score
            ORDER BY business_score DESC
            """
        )
        distribution = {row["business_score"]: row["count"] for row in self.cursor.fetchall()}

        return {
            "countries": countries,
            "mainCountry": main_country["country"] if main_country else "Unknown",
            "proxyTypes": proxy_types,
            "businessScoreDistribution": distribution,
        }

    def get_stats(self) -> dict:
        self.cursor.execute("SELECT COUNT(*) AS total FROM proxies")
        total = self.cursor.fetchone()["total"]
        self.cursor.execute("SELECT COUNT(*) AS active FROM proxies WHERE is_alive = 1")
        active = self.cursor.fetchone()["active"]
        self.cursor.execute("SELECT COUNT(DISTINCT country) AS countries FROM proxies WHERE country IS NOT NULL")
        countries = self.cursor.fetchone()["countries"]
        self.cursor.execute("SELECT AVG(response_time) AS avg_time FROM proxies WHERE response_time IS NOT NULL AND is_alive = 1")
        avg_time = self.cursor.fetchone()["avg_time"] or 0
        self.cursor.execute("SELECT COUNT(*) AS high_quality FROM proxies WHERE is_alive = 1 AND business_score >= 2")
        high_quality = self.cursor.fetchone()["high_quality"]
        self.cursor.execute("SELECT AVG(business_score) AS avg_business_score FROM proxies WHERE is_alive = 1")
        avg_business_score = self.cursor.fetchone()["avg_business_score"] or 0
        return {
            "totalProxies": total,
            "activeProxies": active,
            "countriesCount": countries,
            "avgResponseTime": round(avg_time, 1),
            "highQualityProxies": high_quality,
            "avgBusinessScore": round(avg_business_score, 1),
            "responseTimeChange": -40,
            "activeChange": 12,
        }

    def get_high_quality_proxies(self, min_score: int = 2, limit: int = 10) -> list[ProxyModel]:
        self.cursor.execute(
            """
            SELECT * FROM proxies
            WHERE is_alive = 1 AND business_score >= %s
            ORDER BY business_score DESC, quality_score DESC, response_time ASC
            LIMIT %s
            """,
            (min_score, limit),
        )
        return [ProxyModel.from_db_row(row) for row in self.cursor.fetchall()]

    def delete_proxy(self, ip: str, port: int) -> None:
        self.cursor.execute("DELETE FROM proxies WHERE ip = %s AND port = %s", (ip, port))
        self.conn.commit()
