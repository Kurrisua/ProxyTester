from __future__ import annotations

import os
import pymysql
from storage.mysql.connection import get_connection_config


PROXIES_TABLE_SQL = """
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


def read_sql_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def execute_sql(cursor, sql: str):
    statements = sql.strip().split(';')
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"Warning: {e}")


def main():
    config = get_connection_config()
    db_name = config.pop('database')
    
    try:
        print(f"Connecting to MySQL at {config['host']}:{config['port']}")
        connection = pymysql.connect(**config, database='mysql')
        cursor = connection.cursor()
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{db_name}' ensured")
        
        cursor.close()
        connection.close()
        
        config['database'] = db_name
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        
        print("Creating proxies table...")
        execute_sql(cursor, PROXIES_TABLE_SQL)
        
        migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
        sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        for sql_file in sql_files:
            filepath = os.path.join(migrations_dir, sql_file)
            print(f"Executing migration: {sql_file}")
            sql_content = read_sql_file(filepath)
            execute_sql(cursor, sql_content)
        
        connection.commit()
        print("\nAll tables created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    main()
