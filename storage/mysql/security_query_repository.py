from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from storage.mysql.connection import create_connection


class MySQLSecurityQueryRepository:
    def __init__(self, connection=None) -> None:
        self.conn = connection or create_connection()
        self.cursor = self.conn.cursor()

    def close(self) -> None:
        self.cursor.close()
        self.conn.close()

    def get_overview(self) -> dict:
        self.cursor.execute("SELECT COUNT(*) AS total FROM proxies")
        total = self.cursor.fetchone()["total"]
        self.cursor.execute("SELECT COUNT(*) AS active FROM proxies WHERE is_alive = 1")
        active = self.cursor.fetchone()["active"]

        self.cursor.execute(
            """
            SELECT COALESCE(security_risk, 'unknown') AS risk_level, COUNT(*) AS count
            FROM proxies
            GROUP BY COALESCE(security_risk, 'unknown')
            """
        )
        risk_counts = {row["risk_level"]: row["count"] for row in self.cursor.fetchall()}

        self.cursor.execute(
            """
            SELECT COALESCE(behavior_class, 'normal') AS behavior_class, COUNT(*) AS count
            FROM proxies
            GROUP BY COALESCE(behavior_class, 'normal')
            """
        )
        behavior_counts = {row["behavior_class"]: row["count"] for row in self.cursor.fetchall()}

        self.cursor.execute(
            """
            SELECT execution_status, outcome, COUNT(*) AS count
            FROM security_scan_records
            GROUP BY execution_status, outcome
            """
        )
        scan_record_counts = [
            {"executionStatus": row["execution_status"], "outcome": row["outcome"], "count": row["count"]}
            for row in self.cursor.fetchall()
        ]

        self.cursor.execute(
            """
            SELECT event_type, risk_level, COUNT(*) AS count
            FROM security_behavior_events
            GROUP BY event_type, risk_level
            ORDER BY count DESC
            LIMIT 20
            """
        )
        top_events = [
            {"eventType": row["event_type"], "riskLevel": row["risk_level"], "count": row["count"]}
            for row in self.cursor.fetchall()
        ]

        self.cursor.execute(
            """
            SELECT batch_id, status, scan_policy, max_scan_depth, target_proxy_count,
                   checked_proxy_count, anomaly_event_count, started_at, finished_at
            FROM security_scan_batches
            ORDER BY created_at DESC
            LIMIT 5
            """
        )
        recent_batches = [self._batch_row_to_dict(row) for row in self.cursor.fetchall()]

        return {
            "totalProxies": total,
            "activeProxies": active,
            "uncheckedProxies": risk_counts.get("unknown", 0),
            "normalProxies": risk_counts.get("low", 0),
            "suspiciousProxies": risk_counts.get("medium", 0),
            "maliciousProxies": risk_counts.get("high", 0) + risk_counts.get("critical", 0),
            "riskCounts": risk_counts,
            "behaviorCounts": behavior_counts,
            "scanRecordCounts": scan_record_counts,
            "funnelStats": self._get_funnel_stats(),
            "riskTrend": self._get_risk_trend(days=14),
            "protocolCounts": self._get_protocol_distribution(),
            "geoRiskRanking": self._get_geo_risk_ranking(limit=10),
            "topEvents": top_events,
            "recentBatches": recent_batches,
        }

    def list_batches(self, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        offset = (page - 1) * limit
        self.cursor.execute("SELECT COUNT(*) AS total FROM security_scan_batches")
        total = self.cursor.fetchone()["total"]
        self.cursor.execute(
            """
            SELECT batch_id, status, scan_mode, scan_policy, max_scan_depth,
                   target_proxy_count, checked_proxy_count, skipped_proxy_count,
                   error_proxy_count, normal_proxy_count, suspicious_proxy_count,
                   malicious_proxy_count, anomaly_event_count, started_at,
                   finished_at, elapsed_seconds, parameters, error_message,
                   created_at, updated_at
            FROM security_scan_batches
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        return [self._batch_row_to_dict(row) for row in self.cursor.fetchall()], total

    def get_batch_detail(self, batch_id: str, record_limit: int = 100) -> dict | None:
        self.cursor.execute(
            """
            SELECT *
            FROM security_scan_batches
            WHERE batch_id = %s
            """,
            (batch_id,),
        )
        batch = self.cursor.fetchone()
        if not batch:
            return None

        self.cursor.execute(
            """
            SELECT funnel_stage, stage, execution_status, outcome, COUNT(*) AS count
            FROM security_scan_records
            WHERE batch_id = %s
            GROUP BY funnel_stage, stage, execution_status, outcome
            ORDER BY funnel_stage, stage, execution_status, outcome
            """,
            (batch["id"],),
        )
        stage_stats = [
            {
                "funnelStage": row["funnel_stage"],
                "stage": row["stage"],
                "executionStatus": row["execution_status"],
                "outcome": row["outcome"],
                "count": row["count"],
            }
            for row in self.cursor.fetchall()
        ]

        self.cursor.execute(
            """
            SELECT id, proxy_ip, proxy_port, round_index, funnel_stage, stage,
                   checker_name, scan_depth, applicability, execution_status,
                   outcome, skip_reason, precondition_summary, elapsed_ms,
                   is_anomalous, risk_level, risk_tags, error_message, created_at
            FROM security_scan_records
            WHERE batch_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (batch["id"], record_limit),
        )
        records = [self._record_row_to_dict(row) for row in self.cursor.fetchall()]

        return {
            "batch": self._batch_row_to_dict(batch),
            "stageStats": stage_stats,
            "records": records,
        }

    def get_proxy_security_detail(self, ip: str, port: int, record_limit: int = 80, event_limit: int = 40) -> dict:
        self.cursor.execute("SELECT id FROM proxies WHERE ip = %s AND port = %s", (ip, port))
        proxy = self.cursor.fetchone()
        proxy_id = proxy["id"] if proxy else None

        self.cursor.execute(
            """
            SELECT r.funnel_stage, r.stage, r.execution_status, r.outcome, COUNT(*) AS count
            FROM security_scan_records r
            WHERE r.proxy_ip = %s AND r.proxy_port = %s
            GROUP BY r.funnel_stage, r.stage, r.execution_status, r.outcome
            ORDER BY r.funnel_stage, r.stage, r.execution_status, r.outcome
            """,
            (ip, port),
        )
        stage_stats = [
            {
                "funnelStage": row["funnel_stage"],
                "stage": row["stage"],
                "executionStatus": row["execution_status"],
                "outcome": row["outcome"],
                "count": row["count"],
            }
            for row in self.cursor.fetchall()
        ]

        self.cursor.execute(
            """
            SELECT id, proxy_ip, proxy_port, round_index, funnel_stage, stage,
                   checker_name, scan_depth, applicability, execution_status,
                   outcome, skip_reason, precondition_summary, elapsed_ms,
                   is_anomalous, risk_level, risk_tags, error_message, created_at
            FROM security_scan_records
            WHERE proxy_ip = %s AND proxy_port = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (ip, port, record_limit),
        )
        records = [self._record_row_to_dict(row) for row in self.cursor.fetchall()]

        events = []
        self.cursor.execute(
            """
            SELECT e.id, e.record_id, e.batch_id, e.proxy_id, e.event_type,
                   e.behavior_class, e.risk_level, e.confidence, e.target_url,
                   e.target_type, e.selector, e.affected_resource_url,
                   e.external_domain, e.evidence, e.summary, e.created_at
            FROM security_behavior_events e
            LEFT JOIN security_scan_records r ON e.record_id = r.id
            WHERE (r.proxy_ip = %s AND r.proxy_port = %s)
               OR (%s IS NOT NULL AND e.proxy_id = %s)
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT %s
            """,
            (ip, port, proxy_id, proxy_id, event_limit),
        )
        events = [self._event_row_to_dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute(
            """
            SELECT ro.id, ro.record_id, ro.proxy_id, ro.resource_url, ro.resource_type,
                   ro.direct_status_code, ro.proxy_status_code, ro.direct_sha256,
                   ro.proxy_sha256, ro.direct_size, ro.proxy_size, ro.direct_mime_type,
                   ro.proxy_mime_type, ro.is_modified, ro.failure_type,
                   ro.risk_level, ro.summary, ro.observed_at
            FROM security_resource_observations ro
            LEFT JOIN security_scan_records r ON ro.record_id = r.id
            WHERE (r.proxy_ip = %s AND r.proxy_port = %s)
               OR (%s IS NOT NULL AND ro.proxy_id = %s)
            ORDER BY ro.observed_at DESC, ro.id DESC
            LIMIT 80
            """,
            (ip, port, proxy_id, proxy_id),
        )
        resources = [self._resource_row_to_dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute(
            """
            SELECT co.id, co.record_id, co.proxy_id, co.observation_mode, co.host,
                   co.port, co.fingerprint_sha256, co.issuer, co.subject,
                   co.not_before, co.not_after, co.is_self_signed, co.is_mismatch,
                   co.risk_level, co.certificate_summary, co.error_message,
                   co.observed_at
            FROM security_certificate_observations co
            LEFT JOIN security_scan_records r ON co.record_id = r.id
            WHERE (r.proxy_ip = %s AND r.proxy_port = %s)
               OR (%s IS NOT NULL AND co.proxy_id = %s)
            ORDER BY co.observed_at DESC, co.id DESC
            LIMIT 80
            """,
            (ip, port, proxy_id, proxy_id),
        )
        certificates = [self._certificate_row_to_dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute(
            """
            SELECT b.batch_id, b.status, b.scan_mode, b.scan_policy, b.max_scan_depth,
                   b.target_proxy_count, b.checked_proxy_count, b.skipped_proxy_count,
                   b.error_proxy_count, b.normal_proxy_count, b.suspicious_proxy_count,
                   b.malicious_proxy_count, b.anomaly_event_count, b.started_at,
                   b.finished_at, b.elapsed_seconds, b.parameters, b.error_message,
                   b.created_at, b.updated_at
            FROM security_scan_batches b
            JOIN security_scan_records r ON r.batch_id = b.id
            WHERE r.proxy_ip = %s AND r.proxy_port = %s
            GROUP BY b.id
            ORDER BY MAX(r.created_at) DESC
            LIMIT 10
            """,
            (ip, port),
        )
        batches = [self._batch_row_to_dict(row) for row in self.cursor.fetchall()]

        return {
            "stageStats": stage_stats,
            "records": records,
            "events": events,
            "batches": batches,
            "resources": resources,
            "certificates": certificates,
        }

    def list_events(self, page: int = 1, limit: int = 20, filters: dict | None = None) -> tuple[list[dict], int]:
        filters = filters or {}
        conditions = []
        params: list[Any] = []
        if filters.get("event_type"):
            conditions.append("e.event_type = %s")
            params.append(filters["event_type"])
        if filters.get("risk_level"):
            conditions.append("e.risk_level = %s")
            params.append(filters["risk_level"])
        if filters.get("country"):
            conditions.append("COALESCE(p.country, 'Unknown') = %s")
            params.append(filters["country"])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        self.cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM security_behavior_events e
            LEFT JOIN proxies p ON e.proxy_id = p.id
            {where}
            """,
            params,
        )
        total = self.cursor.fetchone()["total"]

        offset = (page - 1) * limit
        self.cursor.execute(
            f"""
            SELECT e.id, e.record_id, e.batch_id, e.proxy_id, e.event_type, e.behavior_class,
                   e.risk_level, e.confidence, e.target_url, e.target_type, e.selector,
                   e.affected_resource_url, e.external_domain, e.evidence, e.summary,
                   e.created_at
            FROM security_behavior_events e
            LEFT JOIN proxies p ON e.proxy_id = p.id
            {where}
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        return [self._event_row_to_dict(row) for row in self.cursor.fetchall()], total

    def get_geo_summary(self) -> list[dict]:
        self.cursor.execute(
            """
            SELECT COALESCE(country, 'Unknown') AS country,
                   COUNT(*) AS total,
                   SUM(CASE WHEN is_alive = 1 THEN 1 ELSE 0 END) AS active,
                   SUM(CASE WHEN COALESCE(security_risk, 'unknown') = 'unknown' THEN 1 ELSE 0 END) AS unchecked,
                   SUM(CASE WHEN security_risk = 'low' THEN 1 ELSE 0 END) AS normal,
                   SUM(CASE WHEN security_risk = 'medium' THEN 1 ELSE 0 END) AS suspicious,
                   SUM(CASE WHEN security_risk IN ('high', 'critical') THEN 1 ELSE 0 END) AS malicious,
                   AVG(CASE WHEN is_alive = 1 THEN response_time ELSE NULL END) AS avg_response_time,
                   CASE MAX(CASE COALESCE(security_risk, 'unknown')
                       WHEN 'critical' THEN 4
                       WHEN 'high' THEN 3
                       WHEN 'medium' THEN 2
                       WHEN 'low' THEN 1
                       ELSE 0
                   END)
                       WHEN 4 THEN 'critical'
                       WHEN 3 THEN 'high'
                       WHEN 2 THEN 'medium'
                       WHEN 1 THEN 'low'
                       ELSE 'unknown'
                   END AS top_risk_level
            FROM proxies
            GROUP BY COALESCE(country, 'Unknown')
            ORDER BY total DESC
            """
        )
        rows = self.cursor.fetchall()
        return [
            {
                "countryCode": self._country_code(row["country"]),
                "countryName": row["country"],
                "totalProxies": row["total"],
                "activeProxies": int(row["active"] or 0),
                "uncheckedProxies": int(row["unchecked"] or 0),
                "normalProxies": int(row["normal"] or 0),
                "suspiciousProxies": int(row["suspicious"] or 0),
                "maliciousProxies": int(row["malicious"] or 0),
                "avgResponseTimeMs": round(float(row["avg_response_time"] or 0), 1),
                "protocols": self._protocol_distribution_for_country(row["country"]),
                "topRiskLevel": row["top_risk_level"] or "unknown",
                "topEventTypes": self._top_events_for_country(row["country"]),
            }
            for row in rows
        ]

    def get_geo_region_detail(self, country: str) -> dict:
        summaries = self.get_geo_summary()
        summary = next((item for item in summaries if item["countryName"] == country or item["countryCode"] == country), None)
        country_name = summary["countryName"] if summary else country
        if country_name == "Unknown":
            country_condition = "country IS NULL OR country = ''"
            params: tuple = ()
        else:
            country_condition = "country = %s"
            params = (country_name,)

        self.cursor.execute(
            f"""
            SELECT ip, port, proxy_type, is_alive, response_time, security_risk,
                   behavior_class, risk_tags, last_security_check_time
            FROM proxies
            WHERE {country_condition}
            ORDER BY
                CASE COALESCE(security_risk, 'unknown')
                    WHEN 'critical' THEN 5
                    WHEN 'high' THEN 4
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 2
                    ELSE 1
                END DESC,
                last_security_check_time DESC
            LIMIT 20
            """,
            params,
        )
        proxies = [
            {
                "proxy": f"{row['ip']}:{row['port']}",
                "ip": row["ip"],
                "port": row["port"],
                "proxyType": row["proxy_type"],
                "isAlive": bool(row["is_alive"]),
                "responseTime": row["response_time"],
                "securityRisk": row["security_risk"],
                "behaviorClass": row["behavior_class"],
                "riskTags": self._parse_json(row.get("risk_tags"), []),
                "lastSecurityCheckTime": self._dt(row.get("last_security_check_time")),
            }
            for row in self.cursor.fetchall()
        ]

        events, _ = self.list_events(page=1, limit=20, filters={"country": country_name})
        return {"summary": summary or {"countryCode": "UNKNOWN", "countryName": country_name}, "topProxies": proxies, "recentEvents": events}

    def get_proxy_security_history(self, ip: str, port: int, limit: int = 80) -> list[dict]:
        self.cursor.execute(
            """
            SELECT id, proxy_ip, proxy_port, round_index, funnel_stage, stage,
                   checker_name, scan_depth, applicability, execution_status,
                   outcome, skip_reason, precondition_summary, elapsed_ms,
                   is_anomalous, risk_level, risk_tags, error_message, created_at
            FROM security_scan_records
            WHERE proxy_ip = %s AND proxy_port = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (ip, port, limit),
        )
        return [self._record_row_to_dict(row) for row in self.cursor.fetchall()]

    def get_proxy_security_events(self, ip: str, port: int, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        self.cursor.execute("SELECT id FROM proxies WHERE ip = %s AND port = %s", (ip, port))
        proxy = self.cursor.fetchone()
        proxy_id = proxy["id"] if proxy else None
        where = "(r.proxy_ip = %s AND r.proxy_port = %s) OR (%s IS NOT NULL AND e.proxy_id = %s)"
        params = [ip, port, proxy_id, proxy_id]
        self.cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM security_behavior_events e
            LEFT JOIN security_scan_records r ON e.record_id = r.id
            WHERE {where}
            """,
            params,
        )
        total = self.cursor.fetchone()["total"]
        offset = (page - 1) * limit
        self.cursor.execute(
            f"""
            SELECT e.id, e.record_id, e.batch_id, e.proxy_id, e.event_type,
                   e.behavior_class, e.risk_level, e.confidence, e.target_url,
                   e.target_type, e.selector, e.affected_resource_url,
                   e.external_domain, e.evidence, e.summary, e.created_at
            FROM security_behavior_events e
            LEFT JOIN security_scan_records r ON e.record_id = r.id
            WHERE {where}
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        return [self._event_row_to_dict(row) for row in self.cursor.fetchall()], total

    def get_event_detail(self, event_id: int) -> dict | None:
        self.cursor.execute(
            """
            SELECT e.id, e.record_id, e.batch_id, e.proxy_id, e.event_type,
                   e.behavior_class, e.risk_level, e.confidence, e.target_url,
                   e.target_type, e.selector, e.affected_resource_url,
                   e.external_domain, e.evidence, e.summary, e.created_at,
                   p.ip, p.port, p.country, p.proxy_type,
                   r.stage, r.checker_name, r.funnel_stage, r.outcome,
                   r.execution_status, r.risk_tags
            FROM security_behavior_events e
            LEFT JOIN proxies p ON e.proxy_id = p.id
            LEFT JOIN security_scan_records r ON e.record_id = r.id
            WHERE e.id = %s
            """,
            (event_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        event = self._event_row_to_dict(row)
        self.cursor.execute(
            """
            SELECT id, record_id, event_id, proxy_id, evidence_type, storage_path,
                   sha256, size_bytes, mime_type, summary, created_at
            FROM security_evidence_files
            WHERE event_id = %s OR record_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 40
            """,
            (event_id, row["record_id"]),
        )
        evidence_files = [
            {
                "id": item["id"],
                "recordId": item["record_id"],
                "eventId": item["event_id"],
                "proxyId": item["proxy_id"],
                "evidenceType": item["evidence_type"],
                "storagePath": item["storage_path"],
                "sha256": item["sha256"],
                "sizeBytes": item["size_bytes"],
                "mimeType": item["mime_type"],
                "summary": item["summary"],
                "createdAt": self._dt(item["created_at"]),
            }
            for item in self.cursor.fetchall()
        ]
        return {
            "event": event,
            "proxy": {
                "ip": row.get("ip"),
                "port": row.get("port"),
                "country": row.get("country"),
                "proxyType": row.get("proxy_type"),
            },
            "record": {
                "id": row.get("record_id"),
                "stage": row.get("stage"),
                "checkerName": row.get("checker_name"),
                "funnelStage": row.get("funnel_stage"),
                "outcome": row.get("outcome"),
                "executionStatus": row.get("execution_status"),
                "riskTags": self._parse_json(row.get("risk_tags"), []),
            },
            "evidenceFiles": evidence_files,
        }

    def get_behavior_stats(self) -> list[dict]:
        self.cursor.execute(
            """
            SELECT COALESCE(behavior_class, 'normal') AS behavior_class,
                   COALESCE(risk_level, 'unknown') AS risk_level,
                   COUNT(*) AS count
            FROM security_behavior_events
            GROUP BY COALESCE(behavior_class, 'normal'), COALESCE(risk_level, 'unknown')
            ORDER BY count DESC
            """
        )
        return [{"behaviorClass": row["behavior_class"], "riskLevel": row["risk_level"], "count": row["count"]} for row in self.cursor.fetchall()]

    def get_risk_trend(self, days: int = 14) -> list[dict]:
        return self._get_risk_trend(days=days)

    def get_event_type_distribution(self) -> list[dict]:
        self.cursor.execute(
            """
            SELECT event_type, risk_level, COUNT(*) AS count
            FROM security_behavior_events
            GROUP BY event_type, risk_level
            ORDER BY count DESC
            """
        )
        return [{"eventType": row["event_type"], "riskLevel": row["risk_level"], "count": row["count"]} for row in self.cursor.fetchall()]

    def get_risk_distribution(self) -> dict:
        self.cursor.execute(
            """
            SELECT COALESCE(security_risk, 'unknown') AS risk_level, COUNT(*) AS count
            FROM proxies
            GROUP BY COALESCE(security_risk, 'unknown')
            """
        )
        return {row["risk_level"]: row["count"] for row in self.cursor.fetchall()}

    def _protocol_distribution_for_country(self, country: str) -> dict:
        if country == "Unknown":
            self.cursor.execute("SELECT proxy_type, COUNT(*) AS count FROM proxies WHERE country IS NULL OR country = '' GROUP BY proxy_type")
        else:
            self.cursor.execute("SELECT proxy_type, COUNT(*) AS count FROM proxies WHERE country = %s GROUP BY proxy_type", (country,))
        return self._protocol_counts_from_rows(self.cursor.fetchall())

    def _top_events_for_country(self, country: str) -> list[dict]:
        if country == "Unknown":
            country_where = "p.country IS NULL OR p.country = ''"
            params: tuple = ()
        else:
            country_where = "p.country = %s"
            params = (country,)
        self.cursor.execute(
            f"""
            SELECT e.event_type, e.risk_level, COUNT(*) AS count
            FROM security_behavior_events e
            LEFT JOIN proxies p ON e.proxy_id = p.id
            WHERE {country_where}
            GROUP BY e.event_type, e.risk_level
            ORDER BY count DESC
            LIMIT 5
            """,
            params,
        )
        return [
            {"eventType": row["event_type"], "riskLevel": row["risk_level"], "count": row["count"]}
            for row in self.cursor.fetchall()
        ]

    def _get_funnel_stats(self) -> list[dict]:
        self.cursor.execute(
            """
            SELECT COALESCE(funnel_stage, -1) AS funnel_stage,
                   COALESCE(stage, 'unknown') AS stage,
                   outcome,
                   COUNT(*) AS count
            FROM security_scan_records
            GROUP BY COALESCE(funnel_stage, -1), COALESCE(stage, 'unknown'), outcome
            ORDER BY funnel_stage, stage, outcome
            """
        )
        grouped: dict[tuple[int, str], dict] = {}
        for row in self.cursor.fetchall():
            key = (int(row["funnel_stage"]), row["stage"])
            item = grouped.setdefault(
                key,
                {
                    "funnelStage": int(row["funnel_stage"]),
                    "stage": row["stage"],
                    "total": 0,
                    "normal": 0,
                    "anomalous": 0,
                    "notApplicable": 0,
                    "skipped": 0,
                    "error": 0,
                    "timeout": 0,
                },
            )
            count = int(row["count"] or 0)
            outcome = row["outcome"]
            item["total"] += count
            if outcome == "not_applicable":
                item["notApplicable"] += count
            elif outcome in item:
                item[outcome] += count
        return list(grouped.values())

    def _get_risk_trend(self, days: int = 14) -> list[dict]:
        start_day = date.today() - timedelta(days=days - 1)
        self.cursor.execute(
            """
            SELECT DATE(created_at) AS day,
                   COUNT(*) AS total_records,
                   SUM(CASE WHEN outcome = 'anomalous' THEN 1 ELSE 0 END) AS anomalous_records,
                   SUM(CASE WHEN risk_level IN ('high', 'critical') THEN 1 ELSE 0 END) AS high_risk_records,
                   COUNT(DISTINCT CONCAT(proxy_ip, ':', proxy_port)) AS checked_proxies
            FROM security_scan_records
            WHERE created_at >= %s
            GROUP BY DATE(created_at)
            ORDER BY day
            """,
            (start_day,),
        )
        rows = {self._date_key(row["day"]): row for row in self.cursor.fetchall()}
        trend = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            key = day.isoformat()
            row = rows.get(key)
            total = int(row["total_records"] or 0) if row else 0
            anomalous = int(row["anomalous_records"] or 0) if row else 0
            trend.append(
                {
                    "date": key,
                    "totalRecords": total,
                    "checkedProxies": int(row["checked_proxies"] or 0) if row else 0,
                    "anomalousRecords": anomalous,
                    "highRiskRecords": int(row["high_risk_records"] or 0) if row else 0,
                    "anomalyRate": round((anomalous / total) * 100, 1) if total else 0,
                }
            )
        return trend

    def _get_protocol_distribution(self) -> dict:
        self.cursor.execute("SELECT proxy_type, COUNT(*) AS count FROM proxies GROUP BY proxy_type")
        return self._protocol_counts_from_rows(self.cursor.fetchall())

    def _get_geo_risk_ranking(self, limit: int = 10) -> list[dict]:
        countries = self.get_geo_summary()
        countries.sort(
            key=lambda item: (
                item["maliciousProxies"] * 3 + item["suspiciousProxies"] * 2 + item["uncheckedProxies"],
                item["totalProxies"],
            ),
            reverse=True,
        )
        return countries[:limit]

    @staticmethod
    def _protocol_counts_from_rows(rows: list[dict]) -> dict:
        protocols = {"http": 0, "https": 0, "socks5": 0, "unknown": 0}
        for row in rows:
            proxy_type = (row.get("proxy_type") or "").upper()
            count = int(row.get("count") or 0)
            tokens = [part.strip() for part in proxy_type.replace("/", ",").replace("|", ",").split(",") if part.strip()]
            if not tokens and proxy_type:
                tokens = proxy_type.split()
            matched = False
            for token in tokens:
                if token == "HTTP":
                    protocols["http"] += count
                    matched = True
                elif token == "HTTPS":
                    protocols["https"] += count
                    matched = True
                elif token == "SOCKS5":
                    protocols["socks5"] += count
                    matched = True
            if not matched:
                protocols["unknown"] += count
        return protocols

    @staticmethod
    def _country_code(country: str) -> str:
        country_map = {
            "United States": "US",
            "USA": "US",
            "China": "CN",
            "Hong Kong": "HK",
            "Japan": "JP",
            "Singapore": "SG",
            "Germany": "DE",
            "France": "FR",
            "United Kingdom": "GB",
            "Russia": "RU",
            "Brazil": "BR",
            "India": "IN",
            "Canada": "CA",
            "Australia": "AU",
            "Netherlands": "NL",
            "South Korea": "KR",
        }
        return country_map.get(country, "UNKNOWN")

    def _batch_row_to_dict(self, row: dict) -> dict:
        return {
            "batchId": row["batch_id"],
            "status": row["status"],
            "scanMode": row.get("scan_mode"),
            "scanPolicy": row.get("scan_policy"),
            "maxScanDepth": row.get("max_scan_depth"),
            "targetProxyCount": row.get("target_proxy_count", 0),
            "checkedProxyCount": row.get("checked_proxy_count", 0),
            "skippedProxyCount": row.get("skipped_proxy_count", 0),
            "errorProxyCount": row.get("error_proxy_count", 0),
            "normalProxyCount": row.get("normal_proxy_count", 0),
            "suspiciousProxyCount": row.get("suspicious_proxy_count", 0),
            "maliciousProxyCount": row.get("malicious_proxy_count", 0),
            "anomalyEventCount": row.get("anomaly_event_count", 0),
            "startedAt": self._dt(row.get("started_at")),
            "finishedAt": self._dt(row.get("finished_at")),
            "elapsedSeconds": row.get("elapsed_seconds"),
            "parameters": self._parse_json(row.get("parameters")),
            "errorMessage": row.get("error_message"),
            "createdAt": self._dt(row.get("created_at")),
            "updatedAt": self._dt(row.get("updated_at")),
        }

    def _record_row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "proxy": f"{row['proxy_ip']}:{row['proxy_port']}",
            "proxyIp": row["proxy_ip"],
            "proxyPort": row["proxy_port"],
            "roundIndex": row["round_index"],
            "funnelStage": row["funnel_stage"],
            "stage": row["stage"],
            "checkerName": row["checker_name"],
            "scanDepth": row["scan_depth"],
            "applicability": row["applicability"],
            "executionStatus": row["execution_status"],
            "outcome": row["outcome"],
            "skipReason": row["skip_reason"],
            "preconditionSummary": self._parse_json(row.get("precondition_summary"), {}),
            "elapsedMs": row["elapsed_ms"],
            "isAnomalous": bool(row["is_anomalous"]),
            "riskLevel": row["risk_level"],
            "riskTags": self._parse_json(row.get("risk_tags"), []),
            "errorMessage": row["error_message"],
            "createdAt": self._dt(row["created_at"]),
        }

    def _event_row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "recordId": row["record_id"],
            "batchId": row["batch_id"],
            "proxyId": row["proxy_id"],
            "eventType": row["event_type"],
            "behaviorClass": row["behavior_class"],
            "riskLevel": row["risk_level"],
            "confidence": float(row["confidence"]) if row["confidence"] is not None else None,
            "targetUrl": row["target_url"],
            "targetType": row["target_type"],
            "selector": row["selector"],
            "affectedResourceUrl": row["affected_resource_url"],
            "externalDomain": row["external_domain"],
            "evidence": self._parse_json(row.get("evidence")),
            "summary": row["summary"],
            "createdAt": self._dt(row["created_at"]),
        }

    def _resource_row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "recordId": row["record_id"],
            "proxyId": row["proxy_id"],
            "resourceUrl": row["resource_url"],
            "resourceType": row["resource_type"],
            "directStatusCode": row["direct_status_code"],
            "proxyStatusCode": row["proxy_status_code"],
            "directSha256": row["direct_sha256"],
            "proxySha256": row["proxy_sha256"],
            "directSize": row["direct_size"],
            "proxySize": row["proxy_size"],
            "directMimeType": row["direct_mime_type"],
            "proxyMimeType": row["proxy_mime_type"],
            "isModified": bool(row["is_modified"]),
            "failureType": row["failure_type"],
            "riskLevel": row["risk_level"],
            "summary": self._parse_json(row.get("summary")),
            "observedAt": self._dt(row["observed_at"]),
        }

    def _certificate_row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "recordId": row["record_id"],
            "proxyId": row["proxy_id"],
            "observationMode": row["observation_mode"],
            "host": row["host"],
            "port": row["port"],
            "fingerprintSha256": row["fingerprint_sha256"],
            "issuer": row["issuer"],
            "subject": row["subject"],
            "notBefore": self._dt(row["not_before"]),
            "notAfter": self._dt(row["not_after"]),
            "isSelfSigned": bool(row["is_self_signed"]),
            "isMismatch": bool(row["is_mismatch"]),
            "riskLevel": row["risk_level"],
            "certificateSummary": self._parse_json(row.get("certificate_summary")),
            "errorMessage": row["error_message"],
            "observedAt": self._dt(row["observed_at"]),
        }

    @staticmethod
    def _parse_json(value, default=None):
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)

    @staticmethod
    def _date_key(value) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @staticmethod
    def _dt(value) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else None
