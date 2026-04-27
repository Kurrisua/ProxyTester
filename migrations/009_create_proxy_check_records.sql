-- Phase 0 draft migration. Stores basic availability/protocol history.

CREATE TABLE proxy_check_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    proxy_id INT NULL,
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
    CONSTRAINT fk_proxy_check_records_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
