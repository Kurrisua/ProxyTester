-- Phase 0 draft migration. Stores indexes to evidence files, not large blobs.

CREATE TABLE security_evidence_files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    event_id BIGINT UNSIGNED NULL,
    proxy_id INT NULL,
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
    CONSTRAINT fk_security_evidence_files_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_security_evidence_files_event
        FOREIGN KEY (event_id) REFERENCES security_behavior_events(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_security_evidence_files_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
