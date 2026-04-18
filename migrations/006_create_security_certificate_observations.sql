-- Phase 0 draft migration. Stores TLS certificate observations and comparisons.

CREATE TABLE security_certificate_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    proxy_id INT NULL,
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
    CONSTRAINT fk_certificate_observations_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_certificate_observations_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
