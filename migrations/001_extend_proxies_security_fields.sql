-- Phase 0 draft migration. Review and back up existing data before running.
-- Extends proxies with latest security summary fields only.

ALTER TABLE proxies
    ADD COLUMN security_score INT NULL,
    ADD COLUMN behavior_class VARCHAR(64) NULL,
    ADD COLUMN risk_tags JSON NULL,
    ADD COLUMN has_content_tampering TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN has_resource_replacement TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN has_mitm_risk TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN anomaly_trigger_count INT NOT NULL DEFAULT 0,
    ADD COLUMN security_check_count INT NOT NULL DEFAULT 0,
    ADD COLUMN anomaly_trigger_rate DECIMAL(6,4) NULL,
    ADD COLUMN last_security_check_time DATETIME NULL;

CREATE INDEX idx_proxies_behavior_class ON proxies (behavior_class);
CREATE INDEX idx_proxies_last_security_check_time ON proxies (last_security_check_time);
