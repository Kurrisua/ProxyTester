from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EXPECTED_MIGRATIONS = [
    "001_extend_proxies_security_fields.sql",
    "002_create_security_scan_batches.sql",
    "003_create_security_scan_records.sql",
    "004_create_security_behavior_events.sql",
    "005_create_security_evidence_files.sql",
    "006_create_security_certificate_observations.sql",
    "007_create_security_resource_observations.sql",
    "008_create_proxy_sources.sql",
    "009_create_proxy_check_records.sql",
    "010_create_honeypot_targets.sql",
    "011_create_honeypot_request_logs.sql",
]


EXPECTED_TABLES = {
    "proxies": {
        "security_risk",
        "security_score",
        "behavior_class",
        "risk_tags",
        "has_content_tampering",
        "has_resource_replacement",
        "has_mitm_risk",
        "anomaly_trigger_count",
        "security_check_count",
        "anomaly_trigger_rate",
        "last_security_check_time",
    },
    "security_scan_batches": {"batch_id", "scan_policy", "max_scan_depth", "status"},
    "security_scan_records": {
        "batch_id",
        "proxy_id",
        "funnel_stage",
        "stage",
        "checker_name",
        "scan_depth",
        "applicability",
        "execution_status",
        "outcome",
        "skip_reason",
        "precondition_summary",
    },
    "security_behavior_events": {"record_id", "batch_id", "proxy_id", "event_type", "risk_level"},
    "security_evidence_files": {"record_id", "event_id", "proxy_id", "evidence_type", "storage_path"},
    "security_certificate_observations": {"record_id", "proxy_id", "observation_mode", "fingerprint_sha256"},
    "security_resource_observations": {"record_id", "proxy_id", "resource_url", "resource_type", "is_modified"},
    "proxy_sources": {"name", "source_type", "location", "enabled"},
    "proxy_check_records": {"proxy_id", "checked_at", "check_type", "is_alive"},
    "honeypot_targets": {"name", "target_type", "path", "url", "enabled"},
    "honeypot_request_logs": {"request_id", "target_id", "method", "path", "response_body_hash"},
}


def check_local_files() -> int:
    migrations_dir = ROOT / "migrations"
    found = {path.name for path in migrations_dir.glob("*.sql")}
    missing = [name for name in EXPECTED_MIGRATIONS if name not in found]
    extra = sorted(found - set(EXPECTED_MIGRATIONS))

    print(f"Migration directory: {migrations_dir}")
    print(f"Expected SQL files: {len(EXPECTED_MIGRATIONS)}")
    print(f"Found SQL files: {len(found)}")
    if missing:
        print("Missing migration files:")
        for name in missing:
            print(f"  - {name}")
    if extra:
        print("Extra migration files:")
        for name in extra:
            print(f"  - {name}")
    if not missing:
        print("Local migration file check: OK")
    return 1 if missing else 0


def check_database_schema() -> int:
    from storage.mysql.connection import create_connection, get_connection_config

    config = get_connection_config()
    safe_config = {key: value for key, value in config.items() if key not in {"password", "cursorclass"}}
    print(f"Checking MySQL schema with config: {safe_config}")

    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db_name, VERSION() AS version")
            row = cursor.fetchone()
            print(f"Connected database: {row['db_name']} (MySQL {row['version']})")

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                """
            )
            existing_tables = {row["table_name"] for row in cursor.fetchall()}

            missing_tables = sorted(set(EXPECTED_TABLES) - existing_tables)
            if missing_tables:
                print("Missing expected tables:")
                for table in missing_tables:
                    print(f"  - {table}")

            missing_columns: dict[str, list[str]] = {}
            for table, expected_columns in EXPECTED_TABLES.items():
                if table not in existing_tables:
                    continue
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = %s
                    """,
                    (table,),
                )
                existing_columns = {row["column_name"] for row in cursor.fetchall()}
                missing = sorted(expected_columns - existing_columns)
                if missing:
                    missing_columns[table] = missing

            if missing_columns:
                print("Missing expected columns:")
                for table, columns in missing_columns.items():
                    print(f"  - {table}: {', '.join(columns)}")

            if not missing_tables and not missing_columns:
                print("Database migration schema check: OK")
                return 0
            return 1
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ProxyTester migration files and, optionally, the live MySQL schema.")
    parser.add_argument("--check-db", action="store_true", help="Also connect to MySQL and run read-only information_schema checks.")
    args = parser.parse_args()

    status = check_local_files()
    if args.check_db:
        status = max(status, check_database_schema())
    else:
        print("Database schema check skipped. Add --check-db to run read-only MySQL checks.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
