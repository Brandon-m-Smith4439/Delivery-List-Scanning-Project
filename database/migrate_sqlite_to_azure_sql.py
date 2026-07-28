#!/usr/bin/env python3
"""Validate and migrate Delivery List Scanner SQLite data to Azure SQL.

The default mode is a preflight-only dry run. Supplying ``--execute`` performs
the copy in one transaction, validates row counts and deterministic checksums,
and writes a JSON migration report. Existing Azure rows are never deleted
unless ``--replace`` is explicitly supplied.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Iterable

DATABASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DATABASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.integrity import check_database


TABLE_ORDER = [
    "schema_migrations",
    "delivery_lists",
    "line_items",
    "stations",
    "customer_route_rules",
    "system_metadata",
    "admin_lookup_values",
    "imports",
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "sessions",
    "password_reset_tokens",
    "bays",
    "bay_assignments",
    "bay_events",
    "racks",
    "rack_items",
    "bay_stale_snoozes",
    "bay_manual_input_rules",
    "bay_scan_barcode_rules",
    "bay_auto_assign_settings",
    "customer_email_contacts",
    "customer_email_cc",
    "email_outbox",
    "scan_events",
    "exceptions",
    "audit_events",
    "app_notifications",
    "app_notification_receipts",
    "machines",
    "scanners",
    "machine_events",
]

IDENTITY_TABLES = {
    "scan_events", "customer_route_rules", "admin_lookup_values", "imports", "exceptions",
    "audit_events", "users", "roles", "sessions", "password_reset_tokens", "bays",
    "bay_assignments", "bay_events", "racks", "rack_items", "bay_manual_input_rules",
    "bay_scan_barcode_rules", "customer_email_contacts", "customer_email_cc", "email_outbox",
    "app_notifications", "machines", "scanners", "machine_events",
}

APPEND_ONLY_TRIGGERS = {
    "scan_events": "trg_scan_events_append_only",
    "audit_events": "trg_audit_events_append_only",
    "machine_events": "trg_machine_events_append_only",
}


def parse_args() -> argparse.Namespace:
    """Handle parse args for the maintained Delivery List Scanner workflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", required=True, help="Existing v097 SQLite database")
    parser.add_argument(
        "--connection-string",
        default=os.environ.get("DLS_DATABASE_CONNECTION_STRING", ""),
        help="Azure SQL ODBC connection string; defaults to DLS_DATABASE_CONNECTION_STRING",
    )
    parser.add_argument("--execute", action="store_true", help="Perform the migration; otherwise run source preflight only")
    parser.add_argument("--replace", action="store_true", help="Delete target rows inside the migration transaction")
    parser.add_argument("--initialize-schema", action="store_true", help="Run database/azure_schema.sql before copying")
    parser.add_argument("--report", help="JSON report path; defaults beside the SQLite database")
    return parser.parse_args()


def quote_identifier(name: str) -> str:
    """Handle quote identifier for the maintained Delivery List Scanner workflow."""
    return f"[{str(name).replace(']', ']]')}]"


def sqlite_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    """Handle sqlite columns for the maintained Delivery List Scanner workflow."""
    return [str(row[1]) for row in connection.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()]


def azure_columns(cursor: Any, table: str) -> list[str]:
    """Handle azure columns for the maintained Delivery List Scanner workflow."""
    rows = cursor.execute(
        "SELECT name FROM sys.columns WHERE object_id = OBJECT_ID(?) ORDER BY column_id",
        (f"dbo.{table}",),
    ).fetchall()
    return [str(row[0]) for row in rows]


def normalized_value(value: Any) -> Any:
    """Handle normalized value for the maintained Delivery List Scanner workflow."""
    if value is None:
        return value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, Decimal)):
        decimal_value = Decimal(str(value))
        return format(decimal_value.normalize(), "f")
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?", text):
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return parsed.isoformat(timespec="seconds")
            except ValueError:
                pass
        return value
    if isinstance(value, datetime):
        parsed = value
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.isoformat(timespec="seconds")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def rows_checksum(columns: list[str], rows: Iterable[Iterable[Any]]) -> str:
    """Return an order-independent deterministic checksum for table rows."""
    row_hashes: list[str] = []
    for row in rows:
        payload = {column: normalized_value(value) for column, value in zip(columns, tuple(row))}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        row_hashes.append(hashlib.sha256(encoded).hexdigest())
    digest = hashlib.sha256()
    for row_hash in sorted(row_hashes):
        digest.update(row_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def sqlite_table_snapshot(connection: sqlite3.Connection, table: str, columns: list[str]) -> dict[str, Any]:
    """Handle sqlite table snapshot for the maintained Delivery List Scanner workflow."""
    if not columns:
        return {"rowCount": 0, "checksum": rows_checksum([], []), "columns": []}
    rows = connection.execute(
        f"SELECT {', '.join(quote_identifier(column) for column in columns)} FROM {quote_identifier(table)}"
    ).fetchall()
    return {"rowCount": len(rows), "checksum": rows_checksum(columns, rows), "columns": columns, "rows": rows}


def azure_table_snapshot(cursor: Any, table: str, columns: list[str]) -> dict[str, Any]:
    """Handle azure table snapshot for the maintained Delivery List Scanner workflow."""
    rows = cursor.execute(
        f"SELECT {', '.join(quote_identifier(column) for column in columns)} FROM dbo.{quote_identifier(table)}"
    ).fetchall()
    return {"rowCount": len(rows), "checksum": rows_checksum(columns, rows)}


def write_report(report: dict[str, Any], report_path: Path) -> None:
    """Handle write report for the maintained Delivery List Scanner workflow."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def source_preflight(sqlite_path: Path) -> tuple[sqlite3.Connection, dict[str, Any], dict[str, Any]]:
    """Handle source preflight for the maintained Delivery List Scanner workflow."""
    integrity = check_database(sqlite_path)
    if not integrity["ok"]:
        messages = "; ".join(issue["message"] for issue in integrity["errors"])
        raise RuntimeError(f"SQLite preflight failed: {messages}")
    connection = sqlite3.connect(f"file:{sqlite_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    snapshots: dict[str, Any] = {}
    for table in TABLE_ORDER:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        if not exists:
            continue
        columns = sqlite_columns(connection, table)
        snapshot = sqlite_table_snapshot(connection, table, columns)
        snapshots[table] = {key: value for key, value in snapshot.items() if key != "rows"}
    return connection, integrity, snapshots


def initialize_azure_schema(cursor: Any, connection: Any) -> None:
    """Handle initialize azure schema for the maintained Delivery List Scanner workflow."""
    script = (DATABASE_DIR / "azure_schema.sql").read_text(encoding="utf-8")
    for batch in re.split(r"^\s*GO\s*$", script, flags=re.IGNORECASE | re.MULTILINE):
        if batch.strip():
            cursor.execute(batch)
    connection.commit()


def set_append_only_triggers(cursor: Any, *, enabled: bool) -> None:
    """Handle set append only triggers for the maintained Delivery List Scanner workflow."""
    operation = "ENABLE" if enabled else "DISABLE"
    for table, trigger in APPEND_ONLY_TRIGGERS.items():
        cursor.execute(
            f"IF OBJECT_ID(N'dbo.{trigger}', N'TR') IS NOT NULL "
            f"{operation} TRIGGER dbo.{quote_identifier(trigger)} ON dbo.{quote_identifier(table)}"
        )


def main() -> int:
    """Handle main for the maintained Delivery List Scanner workflow."""
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    if args.replace and not args.execute:
        raise ValueError("--replace requires --execute")
    report_path = Path(args.report).expanduser().resolve() if args.report else sqlite_path.with_name(
        f"{sqlite_path.stem}-azure-migration-report.json"
    )
    report: dict[str, Any] = {
        "startedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sqlitePath": str(sqlite_path),
        "mode": "execute" if args.execute else "dry-run",
        "status": "preflight",
        "sourceIntegrity": {},
        "tables": {},
        "totalRows": 0,
    }
    sqlite_connection: sqlite3.Connection | None = None
    azure_connection: Any = None
    azure_cursor: Any = None
    try:
        sqlite_connection, integrity, source_snapshots = source_preflight(sqlite_path)
        report["sourceIntegrity"] = integrity
        report["tables"] = {table: {"source": snapshot} for table, snapshot in source_snapshots.items()}
        report["totalRows"] = sum(int(snapshot["rowCount"]) for snapshot in source_snapshots.values())
        if not args.execute:
            report["status"] = "dry-run-passed"
            report["completedAtUtc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_report(report, report_path)
            print(f"Preflight passed: {report['totalRows']} rows across {len(source_snapshots)} tables")
            print(f"Report: {report_path}")
            return 0

        if not args.connection_string.strip():
            raise ValueError("An Azure SQL connection string is required with --execute")
        try:
            import pyodbc  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt before running an Azure migration") from exc

        azure_connection = pyodbc.connect(args.connection_string, autocommit=False, timeout=60)
        azure_cursor = azure_connection.cursor()
        azure_cursor.fast_executemany = True
        if args.initialize_schema:
            initialize_azure_schema(azure_cursor, azure_connection)

        history_triggers_disabled = False
        if args.replace:
            set_append_only_triggers(azure_cursor, enabled=False)
            history_triggers_disabled = True
            for table in reversed(TABLE_ORDER):
                azure_cursor.execute(f"DELETE FROM dbo.{quote_identifier(table)}")

        for table in TABLE_ORDER:
            source = source_snapshots.get(table)
            if source is None:
                continue
            source_columns = list(source["columns"])
            target_columns = azure_columns(azure_cursor, table)
            missing_target_columns = sorted(set(source_columns) - set(target_columns))
            if missing_target_columns:
                raise RuntimeError(f"Azure SQL table {table} is missing columns: {', '.join(missing_target_columns)}")
            columns = [column for column in source_columns if column in set(target_columns)]
            target_count = int(
                azure_cursor.execute(f"SELECT COUNT(*) FROM dbo.{quote_identifier(table)}").fetchone()[0]
            )
            if target_count and not args.replace:
                raise RuntimeError(
                    f"Azure SQL table {table} already contains {target_count} row(s). "
                    "Use a new database or --replace after confirming Azure backups."
                )
            source_full = sqlite_table_snapshot(sqlite_connection, table, columns)
            rows = source_full["rows"]
            identity_insert = table in IDENTITY_TABLES and "id" in columns and bool(rows)
            if identity_insert:
                azure_cursor.execute(f"SET IDENTITY_INSERT dbo.{quote_identifier(table)} ON")
            if rows:
                placeholders = ", ".join("?" for _ in columns)
                insert_sql = (
                    f"INSERT INTO dbo.{quote_identifier(table)} "
                    f"({', '.join(quote_identifier(column) for column in columns)}) VALUES ({placeholders})"
                )
                azure_cursor.executemany(insert_sql, [tuple(row[column] for column in columns) for row in rows])
            if identity_insert:
                azure_cursor.execute(f"SET IDENTITY_INSERT dbo.{quote_identifier(table)} OFF")
                max_id = max(int(row["id"] or 0) for row in rows)
                if max_id:
                    azure_cursor.execute(f"DBCC CHECKIDENT ('dbo.{table}', RESEED, {max_id})")

            target = azure_table_snapshot(azure_cursor, table, columns)
            report["tables"][table]["target"] = target
            if int(target["rowCount"]) != int(source_full["rowCount"]):
                raise RuntimeError(f"Row-count validation failed for {table}")
            if target["checksum"] != source_full["checksum"]:
                raise RuntimeError(f"Checksum validation failed for {table}")

        if history_triggers_disabled:
            set_append_only_triggers(azure_cursor, enabled=True)
        azure_connection.commit()
        report["status"] = "migration-passed"
        report["completedAtUtc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write_report(report, report_path)
        print(f"Migration passed: {report['totalRows']} rows copied and validated")
        print(f"Report: {report_path}")
        return 0
    except Exception as exc:
        if azure_connection is not None:
            azure_connection.rollback()
        report["status"] = "failed"
        report["error"] = str(exc)
        report["completedAtUtc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write_report(report, report_path)
        raise
    finally:
        if azure_cursor is not None:
            azure_cursor.close()
        if azure_connection is not None:
            azure_connection.close()
        if sqlite_connection is not None:
            sqlite_connection.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
