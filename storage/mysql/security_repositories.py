from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime

from core.models.scan_record import SecurityScanBatch, SecurityScanRecord


class SecurityScanBatchRepository(ABC):
    @abstractmethod
    def create_batch(self, batch: SecurityScanBatch) -> None:
        raise NotImplementedError

    @abstractmethod
    def finish_batch(self, batch_id: str, status: str, error_message: str | None = None) -> None:
        raise NotImplementedError


class SecurityScanRecordRepository(ABC):
    @abstractmethod
    def save_scan_record(self, record: SecurityScanRecord) -> int | None:
        raise NotImplementedError


class SecurityBehaviorEventRepository(ABC):
    @abstractmethod
    def save_behavior_event(self, event: dict) -> None:
        raise NotImplementedError


class SecurityEvidenceRepository(ABC):
    @abstractmethod
    def save_evidence_file(self, evidence: dict) -> None:
        raise NotImplementedError


class SecurityResourceObservationRepository(ABC):
    @abstractmethod
    def save_resource_observation(self, observation: dict) -> None:
        raise NotImplementedError


class SecurityCertificateObservationRepository(ABC):
    @abstractmethod
    def save_certificate_observation(self, observation: dict) -> None:
        raise NotImplementedError


class InMemorySecurityRepository(
    SecurityScanBatchRepository,
    SecurityScanRecordRepository,
    SecurityBehaviorEventRepository,
    SecurityEvidenceRepository,
    SecurityResourceObservationRepository,
    SecurityCertificateObservationRepository,
):
    """Test-friendly repository that records scan semantics without touching MySQL."""

    def __init__(self) -> None:
        self.batches: list[SecurityScanBatch] = []
        self.records: list[SecurityScanRecord] = []
        self.events: list[dict] = []
        self.evidence_files: list[dict] = []
        self.resource_observations: list[dict] = []
        self.certificate_observations: list[dict] = []

    def create_batch(self, batch: SecurityScanBatch) -> None:
        self.batches.append(batch)

    def finish_batch(self, batch_id: str, status: str, error_message: str | None = None) -> None:
        for batch in self.batches:
            if batch.batch_id == batch_id:
                batch.status = status
                batch.finished_at = datetime.now()
                batch.error_message = error_message
                return

    def save_scan_record(self, record: SecurityScanRecord) -> int | None:
        self.records.append(record)
        return len(self.records)

    def save_behavior_event(self, event: dict) -> None:
        self.events.append(event)

    def save_evidence_file(self, evidence: dict) -> None:
        self.evidence_files.append(evidence)

    def save_resource_observation(self, observation: dict) -> None:
        self.resource_observations.append(observation)

    def save_certificate_observation(self, observation: dict) -> None:
        self.certificate_observations.append(observation)


class MySQLSecurityRepository(
    SecurityScanBatchRepository,
    SecurityScanRecordRepository,
    SecurityBehaviorEventRepository,
    SecurityEvidenceRepository,
    SecurityResourceObservationRepository,
    SecurityCertificateObservationRepository,
):
    def __init__(self, connection=None) -> None:
        if connection is None:
            from storage.mysql.connection import create_connection

            connection = create_connection()
        self.conn = connection
        self.cursor = self.conn.cursor()
        self._batch_pk_by_uuid: dict[str, int] = {}
        self._lock = threading.RLock()

    def create_batch(self, batch: SecurityScanBatch) -> None:
        with self._lock:
            self.cursor.execute(
                """
                INSERT INTO security_scan_batches (
                    batch_id, scan_mode, scan_policy, max_scan_depth, status,
                    target_proxy_count, parameters, started_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    batch.batch_id,
                    batch.scan_mode,
                    batch.scan_policy,
                    batch.max_scan_depth,
                    batch.status,
                    batch.target_proxy_count,
                    self._json(batch.parameters),
                    batch.started_at,
                ),
            )
            self.conn.commit()
            self._batch_pk_by_uuid[batch.batch_id] = int(self.cursor.lastrowid)

    def finish_batch(self, batch_id: str, status: str, error_message: str | None = None) -> None:
        with self._lock:
            self.cursor.execute(
                """
                UPDATE security_scan_batches
                SET status = %s,
                    finished_at = %s,
                    elapsed_seconds = TIMESTAMPDIFF(MICROSECOND, started_at, %s) / 1000000,
                    error_message = %s
                WHERE batch_id = %s
                """,
                (status, datetime.now(), datetime.now(), error_message, batch_id),
            )
            self.conn.commit()

    def save_scan_record(self, record: SecurityScanRecord) -> int | None:
        with self._lock:
            batch_pk = self._resolve_batch_pk(record.batch_id)
            proxy_pk = record.proxy_id or self._resolve_proxy_pk(record.proxy_ip, record.proxy_port)
            self.cursor.execute(
                """
                INSERT INTO security_scan_records (
                    batch_id, proxy_id, proxy_ip, proxy_port, round_index, funnel_stage,
                    stage, checker_name, scan_depth, applicability, execution_status,
                    outcome, skip_reason, precondition_summary, elapsed_ms, is_anomalous,
                    risk_level, risk_tags, evidence, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    batch_pk,
                    proxy_pk,
                    record.proxy_ip,
                    record.proxy_port,
                    record.round_index,
                    record.funnel_stage,
                    record.stage,
                    record.checker_name,
                    record.scan_depth,
                    record.applicability,
                    record.execution_status,
                    record.outcome,
                    record.skip_reason,
                    self._json(record.precondition_summary),
                    record.elapsed_ms,
                    1 if record.is_anomalous else 0,
                    record.risk_level,
                    self._json(record.risk_tags),
                    self._json(record.evidence),
                    record.error_message,
                ),
            )
            self.conn.commit()
            return int(self.cursor.lastrowid)

    def save_behavior_event(self, event: dict) -> None:
        with self._lock:
            batch_id = event.get("batch_id")
            if isinstance(batch_id, str):
                batch_id = self._resolve_batch_pk(batch_id)
            self.cursor.execute(
                """
                INSERT INTO security_behavior_events (
                    record_id, batch_id, proxy_id, event_type, behavior_class, risk_level,
                    confidence, target_url, target_type, selector, affected_resource_url,
                    external_domain, before_value, after_value, evidence, summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.get("record_id"),
                    batch_id,
                    event.get("proxy_id"),
                    event["event_type"],
                    event.get("behavior_class"),
                    event.get("risk_level", "unknown"),
                    event.get("confidence"),
                    event.get("target_url"),
                    event.get("target_type"),
                    event.get("selector"),
                    event.get("affected_resource_url"),
                    event.get("external_domain"),
                    event.get("before_value"),
                    event.get("after_value"),
                    self._json(event.get("evidence")),
                    event.get("summary"),
                ),
            )
            self.conn.commit()

    def save_evidence_file(self, evidence: dict) -> None:
        with self._lock:
            self.cursor.execute(
                """
                INSERT INTO security_evidence_files (
                    record_id, event_id, proxy_id, evidence_type, storage_path,
                    sha256, size_bytes, mime_type, summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evidence.get("record_id"),
                    evidence.get("event_id"),
                    evidence.get("proxy_id"),
                    evidence["evidence_type"],
                    evidence["storage_path"],
                    evidence.get("sha256"),
                    evidence.get("size_bytes"),
                    evidence.get("mime_type"),
                    evidence.get("summary"),
                ),
            )
            self.conn.commit()

    def save_resource_observation(self, observation: dict) -> None:
        with self._lock:
            self.cursor.execute(
                """
                INSERT INTO security_resource_observations (
                    record_id, proxy_id, resource_url, resource_type,
                    direct_status_code, proxy_status_code, direct_sha256, proxy_sha256,
                    direct_size, proxy_size, direct_mime_type, proxy_mime_type,
                    is_modified, failure_type, risk_level, summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    observation.get("record_id"),
                    observation.get("proxy_id"),
                    observation["resource_url"],
                    observation.get("resource_type"),
                    observation.get("direct_status_code"),
                    observation.get("proxy_status_code"),
                    observation.get("direct_sha256"),
                    observation.get("proxy_sha256"),
                    observation.get("direct_size"),
                    observation.get("proxy_size"),
                    observation.get("direct_mime_type"),
                    observation.get("proxy_mime_type"),
                    1 if observation.get("is_modified") else 0,
                    observation.get("failure_type"),
                    observation.get("risk_level", "unknown"),
                    self._json(observation.get("summary")),
                ),
            )
            self.conn.commit()

    def save_certificate_observation(self, observation: dict) -> None:
        with self._lock:
            self.cursor.execute(
                """
                INSERT INTO security_certificate_observations (
                    record_id, proxy_id, observation_mode, host, port, fingerprint_sha256,
                    issuer, subject, not_before, not_after, is_self_signed, is_mismatch,
                    risk_level, certificate_summary, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    observation.get("record_id"),
                    observation.get("proxy_id"),
                    observation["observation_mode"],
                    observation["host"],
                    observation.get("port", 443),
                    observation.get("fingerprint_sha256"),
                    observation.get("issuer"),
                    observation.get("subject"),
                    observation.get("not_before"),
                    observation.get("not_after"),
                    1 if observation.get("is_self_signed") else 0,
                    1 if observation.get("is_mismatch") else 0,
                    observation.get("risk_level", "unknown"),
                    self._json(observation.get("certificate_summary")),
                    observation.get("error_message"),
                ),
            )
            self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.cursor.close()
            self.conn.close()

    def _resolve_batch_pk(self, batch_id: str) -> int:
        with self._lock:
            if batch_id in self._batch_pk_by_uuid:
                return self._batch_pk_by_uuid[batch_id]
            self.cursor.execute("SELECT id FROM security_scan_batches WHERE batch_id = %s", (batch_id,))
            row = self.cursor.fetchone()
            if not row:
                raise ValueError(f"Unknown security scan batch: {batch_id}")
            self._batch_pk_by_uuid[batch_id] = int(row["id"])
            return self._batch_pk_by_uuid[batch_id]

    def _resolve_proxy_pk(self, ip: str, port: int) -> int | None:
        with self._lock:
            self.cursor.execute("SELECT id FROM proxies WHERE ip = %s AND port = %s", (ip, port))
            row = self.cursor.fetchone()
            return int(row["id"]) if row else None

    @staticmethod
    def _json(value) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str)
