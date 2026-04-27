-- Phase 0 draft migration. Tracks proxy collection sources.

CREATE TABLE proxy_sources (
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
