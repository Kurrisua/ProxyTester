-- Phase 0 draft migration. Stores classified behavior/anomaly events.

CREATE TABLE security_behavior_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NULL,
    batch_id BIGINT UNSIGNED NULL,
    proxy_id INT NULL,
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
    CONSTRAINT fk_security_behavior_events_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_security_behavior_events_batch
        FOREIGN KEY (batch_id) REFERENCES security_scan_batches(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_security_behavior_events_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
