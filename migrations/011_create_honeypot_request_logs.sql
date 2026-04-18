-- Phase 0 draft migration. Optional honeypot request log table.

CREATE TABLE honeypot_request_logs (
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
    CONSTRAINT fk_honeypot_request_logs_target
        FOREIGN KEY (target_id) REFERENCES honeypot_targets(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
