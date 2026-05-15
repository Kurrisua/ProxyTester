from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql


def _get_env(primary: str, legacy: str, default: str) -> str:
    return os.getenv(primary) or os.getenv(legacy) or default


def get_connection_config() -> dict:
    return {
        "host": _get_env("PROXYTESTER_DB_HOST", "DB_HOST", "localhost"),
        "port": int(_get_env("PROXYTESTER_DB_PORT", "DB_PORT", "3307")),
        "user": _get_env("PROXYTESTER_DB_USER", "DB_USER", "root"),
        "password": _get_env("PROXYTESTER_DB_PASSWORD", "DB_PASSWORD", "710893"),
        "database": _get_env("PROXYTESTER_DB_NAME", "DB_NAME", "proxy_pool"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }


PROXIES_TABLE = """
CREATE TABLE IF NOT EXISTS proxies (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ip VARCHAR(64) NOT NULL,
    port INT NOT NULL,
    source VARCHAR(512) DEFAULT 'unknown',
    is_alive TINYINT(1) NOT NULL DEFAULT 0,
    proxy_type VARCHAR(64) DEFAULT NULL,
    anonymity VARCHAR(64) DEFAULT NULL,
    exit_ip VARCHAR(64) DEFAULT NULL,
    country VARCHAR(128) DEFAULT NULL,
    city VARCHAR(128) DEFAULT NULL,
    isp VARCHAR(255) DEFAULT NULL,
    response_time DOUBLE DEFAULT NULL,
    business_score INT NOT NULL DEFAULT 0,
    quality_score INT NOT NULL DEFAULT 0,
    success_count INT NOT NULL DEFAULT 0,
    fail_count INT NOT NULL DEFAULT 0,
    last_check_time DATETIME DEFAULT NULL,
    security_risk VARCHAR(32) NOT NULL DEFAULT 'unknown',
    security_score INT DEFAULT NULL,
    behavior_class VARCHAR(64) DEFAULT NULL,
    risk_tags JSON DEFAULT NULL,
    has_content_tampering TINYINT(1) NOT NULL DEFAULT 0,
    has_resource_replacement TINYINT(1) NOT NULL DEFAULT 0,
    has_mitm_risk TINYINT(1) NOT NULL DEFAULT 0,
    anomaly_trigger_count INT NOT NULL DEFAULT 0,
    security_check_count INT NOT NULL DEFAULT 0,
    anomaly_trigger_rate DECIMAL(6,4) DEFAULT NULL,
    last_security_check_time DATETIME DEFAULT NULL,
    first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_proxy_ip_port (ip, port),
    KEY idx_alive_type (is_alive, proxy_type),
    KEY idx_country (country),
    KEY idx_quality_score (quality_score),
    KEY idx_security_risk (security_risk),
    KEY idx_behavior_class (behavior_class),
    KEY idx_last_security_check_time (last_security_check_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


SECURITY_SCAN_BATCHES = """
CREATE TABLE IF NOT EXISTS security_scan_batches (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    batch_id CHAR(36) NOT NULL,
    scan_mode VARCHAR(64) NOT NULL DEFAULT 'honeypot',
    scan_policy VARCHAR(64) NOT NULL DEFAULT 'funnel_standard',
    max_scan_depth VARCHAR(32) NOT NULL DEFAULT 'standard',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    target_proxy_count INT NOT NULL DEFAULT 0,
    checked_proxy_count INT NOT NULL DEFAULT 0,
    skipped_proxy_count INT NOT NULL DEFAULT 0,
    error_proxy_count INT NOT NULL DEFAULT 0,
    normal_proxy_count INT NOT NULL DEFAULT 0,
    suspicious_proxy_count INT NOT NULL DEFAULT 0,
    malicious_proxy_count INT NOT NULL DEFAULT 0,
    anomaly_event_count INT NOT NULL DEFAULT 0,
    light_scan_count INT NOT NULL DEFAULT 0,
    standard_scan_count INT NOT NULL DEFAULT 0,
    deep_scan_count INT NOT NULL DEFAULT 0,
    browser_scan_count INT NOT NULL DEFAULT 0,
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    elapsed_seconds DOUBLE NULL,
    parameters JSON NULL,
    error_message TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_security_batch_id (batch_id),
    KEY idx_security_scan_batches_status (status),
    KEY idx_security_scan_batches_policy (scan_policy),
    KEY idx_security_scan_batches_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


SECURITY_SCAN_RECORDS = """
CREATE TABLE IF NOT EXISTS security_scan_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    batch_id BIGINT UNSIGNED NOT NULL,
    proxy_id BIGINT UNSIGNED NULL,
    proxy_ip VARCHAR(64) NOT NULL,
    proxy_port INT NOT NULL,
    round_index INT NOT NULL DEFAULT 1,
    funnel_stage INT NOT NULL DEFAULT 0,
    stage VARCHAR(64) NOT NULL,
    checker_name VARCHAR(128) NOT NULL,
    scan_depth VARCHAR(32) NOT NULL DEFAULT 'light',
    applicability VARCHAR(32) NOT NULL DEFAULT 'applicable',
    execution_status VARCHAR(32) NOT NULL DEFAULT 'completed',
    outcome VARCHAR(32) NOT NULL DEFAULT 'normal',
    skip_reason VARCHAR(255) NULL,
    precondition_summary JSON NULL,
    target_url VARCHAR(2048) NULL,
    target_type VARCHAR(64) NULL,
    access_mode VARCHAR(32) NULL,
    user_agent VARCHAR(512) NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    elapsed_ms DOUBLE NULL,
    direct_status_code INT NULL,
    proxy_status_code INT NULL,
    direct_hash CHAR(64) NULL,
    proxy_hash CHAR(64) NULL,
    is_anomalous TINYINT(1) NOT NULL DEFAULT 0,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'unknown',
    risk_tags JSON NULL,
    diff_summary JSON NULL,
    cert_summary JSON NULL,
    resource_summary JSON NULL,
    evidence JSON NULL,
    error_message TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_security_scan_records_batch_proxy_round (batch_id, proxy_id, round_index),
    KEY idx_security_scan_records_proxy_time (proxy_id, started_at),
    KEY idx_security_scan_records_stage_checker (stage, checker_name),
    KEY idx_security_scan_records_applicability (applicability),
    KEY idx_security_scan_records_execution_status (execution_status),
    KEY idx_security_scan_records_funnel_stage (funnel_stage),
    CONSTRAINT fk_security_scan_records_batch FOREIGN KEY (batch_id) REFERENCES security_scan_batches(id) ON DELETE RESTRICT,
    CONSTRAINT fk_security_scan_records_proxy FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


SECURITY_BEHAVIOR_EVENTS = """
CREATE TABLE IF NOT EXISTS security_behavior_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    batch_id BIGINT UNSIGNED NULL,
    proxy_id BIGINT UNSIGNED NULL,
    event_type VARCHAR(128) NOT NULL,
    behavior_class VARCHAR(64) NULL,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'unknown',
    confidence DECIMAL(5,4) NULL,
    target_url VARCHAR(2048) NULL,
    target_type VARCHAR(64) NULL,
    selector VARCHAR(512) NULL,
    affected_resource_url VARCHAR(2048) NULL,
    external_domain VARCHAR(255) NULL,
    before_value TEXT NULL,
    after_value TEXT NULL,
    evidence JSON NULL,
    summary TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_security_behavior_events_proxy_type_time (proxy_id, event_type, created_at),
    KEY idx_security_behavior_events_event_type (event_type),
    KEY idx_security_behavior_events_risk_level (risk_level),
    KEY idx_security_behavior_events_batch (batch_id),
    CONSTRAINT fk_security_behavior_events_record FOREIGN KEY (record_id) REFERENCES security_scan_records(id) ON DELETE SET NULL,
    CONSTRAINT fk_security_behavior_events_batch FOREIGN KEY (batch_id) REFERENCES security_scan_batches(id) ON DELETE SET NULL,
    CONSTRAINT fk_security_behavior_events_proxy FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


SECURITY_EVIDENCE_FILES = """
CREATE TABLE IF NOT EXISTS security_evidence_files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    event_id BIGINT UNSIGNED NULL,
    proxy_id BIGINT UNSIGNED NULL,
    evidence_type VARCHAR(64) NOT NULL,
    storage_path VARCHAR(2048) NOT NULL,
    sha256 CHAR(64) NULL,
    size_bytes BIGINT UNSIGNED NULL,
    mime_type VARCHAR(128) NULL,
    summary TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_security_evidence_files_record (record_id),
    KEY idx_security_evidence_files_event (event_id),
    KEY idx_security_evidence_files_proxy (proxy_id),
    KEY idx_security_evidence_files_type (evidence_type),
    CONSTRAINT fk_security_evidence_files_record FOREIGN KEY (record_id) REFERENCES security_scan_records(id) ON DELETE SET NULL,
    CONSTRAINT fk_security_evidence_files_event FOREIGN KEY (event_id) REFERENCES security_behavior_events(id) ON DELETE SET NULL,
    CONSTRAINT fk_security_evidence_files_proxy FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


SECURITY_CERTIFICATE_OBSERVATIONS = """
CREATE TABLE IF NOT EXISTS security_certificate_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    proxy_id BIGINT UNSIGNED NULL,
    observation_mode VARCHAR(32) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL DEFAULT 443,
    fingerprint_sha256 CHAR(64) NULL,
    issuer VARCHAR(512) NULL,
    subject VARCHAR(512) NULL,
    not_before DATETIME NULL,
    not_after DATETIME NULL,
    is_self_signed TINYINT(1) NOT NULL DEFAULT 0,
    is_mismatch TINYINT(1) NOT NULL DEFAULT 0,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'unknown',
    certificate_summary JSON NULL,
    error_message TEXT NULL,
    observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_certificate_observations_record (record_id),
    KEY idx_certificate_observations_proxy (proxy_id),
    KEY idx_certificate_observations_fingerprint (fingerprint_sha256),
    KEY idx_certificate_observations_host (host),
    CONSTRAINT fk_certificate_observations_record FOREIGN KEY (record_id) REFERENCES security_scan_records(id) ON DELETE SET NULL,
    CONSTRAINT fk_certificate_observations_proxy FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


SECURITY_RESOURCE_OBSERVATIONS = """
CREATE TABLE IF NOT EXISTS security_resource_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    proxy_id BIGINT UNSIGNED NULL,
    resource_url VARCHAR(2048) NOT NULL,
    resource_type VARCHAR(64) NULL,
    direct_status_code INT NULL,
    proxy_status_code INT NULL,
    direct_sha256 CHAR(64) NULL,
    proxy_sha256 CHAR(64) NULL,
    direct_size INT NULL,
    proxy_size INT NULL,
    direct_mime_type VARCHAR(128) NULL,
    proxy_mime_type VARCHAR(128) NULL,
    is_modified TINYINT(1) NOT NULL DEFAULT 0,
    failure_type VARCHAR(64) NULL,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'unknown',
    summary JSON NULL,
    observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_resource_observations_record (record_id),
    KEY idx_resource_observations_proxy (proxy_id),
    KEY idx_resource_observations_modified (is_modified),
    KEY idx_resource_observations_type (resource_type),
    CONSTRAINT fk_resource_observations_record FOREIGN KEY (record_id) REFERENCES security_scan_records(id) ON DELETE SET NULL,
    CONSTRAINT fk_resource_observations_proxy FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


PROXY_SOURCES = """
CREATE TABLE IF NOT EXISTS proxy_sources (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    location VARCHAR(1024) NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    last_refresh_time DATETIME NULL,
    last_success_time DATETIME NULL,
    last_error TEXT NULL,
    total_collected INT NOT NULL DEFAULT 0,
    unique_collected INT NOT NULL DEFAULT 0,
    alive_count INT NOT NULL DEFAULT 0,
    suspicious_count INT NOT NULL DEFAULT 0,
    malicious_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_proxy_sources_name (name),
    KEY idx_proxy_sources_enabled (enabled),
    KEY idx_proxy_sources_type (source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


PROXY_CHECK_RECORDS = """
CREATE TABLE IF NOT EXISTS proxy_check_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    proxy_id BIGINT UNSIGNED NULL,
    checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    check_type VARCHAR(64) NOT NULL DEFAULT 'full',
    is_alive TINYINT(1) NOT NULL DEFAULT 0,
    proxy_type VARCHAR(64) NULL,
    anonymity VARCHAR(64) NULL,
    response_time DOUBLE NULL,
    business_score INT NULL,
    quality_score INT NULL,
    exit_ip VARCHAR(64) NULL,
    country VARCHAR(128) NULL,
    city VARCHAR(128) NULL,
    isp VARCHAR(255) NULL,
    error_message TEXT NULL,
    metadata JSON NULL,
    PRIMARY KEY (id),
    KEY idx_proxy_check_records_proxy_time (proxy_id, checked_at),
    KEY idx_proxy_check_records_checked_at (checked_at),
    CONSTRAINT fk_proxy_check_records_proxy FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


HONEYPOT_TARGETS = """
CREATE TABLE IF NOT EXISTS honeypot_targets (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    path VARCHAR(512) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    expected_status_code INT NOT NULL DEFAULT 200,
    expected_mime_type VARCHAR(128) NULL,
    expected_sha256 CHAR(64) NULL,
    manifest JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_honeypot_targets_path (path),
    KEY idx_honeypot_targets_enabled_type (enabled, target_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


HONEYPOT_REQUEST_LOGS = """
CREATE TABLE IF NOT EXISTS honeypot_request_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    request_id CHAR(36) NULL,
    target_id BIGINT UNSIGNED NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    method VARCHAR(16) NOT NULL,
    path VARCHAR(1024) NOT NULL,
    source_ip VARCHAR(64) NULL,
    user_agent VARCHAR(512) NULL,
    request_headers JSON NULL,
    response_status_code INT NULL,
    response_body_hash CHAR(64) NULL,
    response_size INT NULL,
    PRIMARY KEY (id),
    KEY idx_honeypot_request_logs_requested_at (requested_at),
    KEY idx_honeypot_request_logs_source_ip (source_ip),
    KEY idx_honeypot_request_logs_path (path(255)),
    CONSTRAINT fk_honeypot_request_logs_target FOREIGN KEY (target_id) REFERENCES honeypot_targets(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def main():
    config = get_connection_config()
    
    try:
        print("Connecting to MySQL at %s:%d/%s" % (config['host'], config['port'], config['database']))
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        
        tables = [
            ("proxies", PROXIES_TABLE),
            ("security_scan_batches", SECURITY_SCAN_BATCHES),
            ("security_scan_records", SECURITY_SCAN_RECORDS),
            ("security_behavior_events", SECURITY_BEHAVIOR_EVENTS),
            ("security_evidence_files", SECURITY_EVIDENCE_FILES),
            ("security_certificate_observations", SECURITY_CERTIFICATE_OBSERVATIONS),
            ("security_resource_observations", SECURITY_RESOURCE_OBSERVATIONS),
            ("proxy_sources", PROXY_SOURCES),
            ("proxy_check_records", PROXY_CHECK_RECORDS),
            ("honeypot_targets", HONEYPOT_TARGETS),
            ("honeypot_request_logs", HONEYPOT_REQUEST_LOGS),
        ]
        
        for table_name, sql in tables:
            print("Creating/updating table: %s" % table_name)
            try:
                cursor.execute(sql)
                print("  OK: %s created successfully" % table_name)
            except Exception as e:
                print("  ERROR: %s" % str(e))
        
        connection.commit()
        print("")
        print("All tables created/updated successfully!")
        
    except Exception as e:
        print("")
        print("Error: %s" % str(e))
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    main()
