-- Phase 0 draft migration. Stores resource hash/MIME/size comparison summaries.

CREATE TABLE security_resource_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    proxy_id INT NULL,
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
    CONSTRAINT fk_resource_observations_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_resource_observations_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
