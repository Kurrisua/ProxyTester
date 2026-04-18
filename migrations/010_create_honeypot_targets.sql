-- Phase 0 draft migration. Optional DB-backed honeypot target catalog.

CREATE TABLE honeypot_targets (
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
