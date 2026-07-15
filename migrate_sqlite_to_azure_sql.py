#!/usr/bin/env python
"""Copy an existing Delivery List Scanner SQLite database into Azure SQL.

Run this once after the Azure SQL schema has been initialized. By default the
script refuses to copy into non-empty target tables. Pass --replace only for a
controlled migration into a disposable/backup-protected Azure SQL database.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
import sqlite3
import sys
from typing import Any


TABLE_ORDER = [
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
]

IDENTITY_TABLES = {
    "scan_events",
    "customer_route_rules",
    "admin_lookup_values",
    "imports",
    "exceptions",
    "audit_events",
    "users",
    "roles",
    "sessions",
    "password_reset_tokens",
    "bays",
    "bay_assignments",
    "bay_events",
    "racks",
    "rack_items",
    "bay_manual_input_rules",
    "bay_scan_barcode_rules",
    "customer_email_contacts",
    "customer_email_cc",
    "email_outbox",
    "app_notifications",
}


def parse_args() -> argparse.Namespace:
    """Purpose: Parse args for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", required=True, help="Path to the existing delivery-scanner SQLite .db file")
    parser.add_argument(
        "--connection-string",
        default=os.environ.get("DLS_DATABASE_CONNECTION_STRING", ""),
        help="Azure SQL ODBC connection string; defaults to DLS_DATABASE_CONNECTION_STRING",
    )
    parser.add_argument("--replace", action="store_true", help="Delete target rows before importing")
    parser.add_argument(
        "--initialize-schema",
        action="store_true",
        help="Run azure_sql_schema.sql before copying data",
    )
    return parser.parse_args()


def quote_identifier(name: str) -> str:
    """Purpose: Run the quote identifier workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return f"[{str(name).replace(']', ']]')}]"


def sqlite_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    """Purpose: Run the SQLite columns workflow for the delivery-list scanner.

    Effects: This function reads or changes database records.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return [str(row[1]) for row in connection.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()]


def azure_columns(cursor: Any, table: str) -> list[str]:
    """Purpose: Run the Azure columns workflow for the delivery-list scanner.

    Effects: This function reads or changes database records.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    rows = cursor.execute(
        """
        SELECT name
        FROM sys.columns
        WHERE object_id = OBJECT_ID(?)
        ORDER BY column_id
        """,
        (f"dbo.{table}",),
    ).fetchall()
    return [str(row[0]) for row in rows]


def main() -> int:
    """Purpose: Run the main workflow for the delivery-list scanner.

    Effects: This function reads or changes database records.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    if not args.connection_string.strip():
        raise ValueError("An Azure SQL connection string is required")

    try:
        import pyodbc  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt before running the migration") from exc

    sqlite_connection = sqlite3.connect(sqlite_path)
    sqlite_connection.row_factory = sqlite3.Row
    azure_connection = pyodbc.connect(args.connection_string, autocommit=False, timeout=60)
    azure_cursor = azure_connection.cursor()
    azure_cursor.fast_executemany = True

    try:
        if args.initialize_schema:
            schema_path = Path(__file__).resolve().with_name("azure_sql_schema.sql")
            script = schema_path.read_text(encoding="utf-8")
            for batch in re.split(r"^\s*GO\s*$", script, flags=re.IGNORECASE | re.MULTILINE):
                if batch.strip():
                    azure_cursor.execute(batch)
            azure_connection.commit()
            print("Azure SQL schema initialized")

        if args.replace:
            for table in reversed(TABLE_ORDER):
                azure_cursor.execute(f"DELETE FROM dbo.{quote_identifier(table)}")
            azure_connection.commit()

        total_rows = 0
        for table in TABLE_ORDER:
            source_exists = sqlite_connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            if not source_exists:
                print(f"SKIP {table}: source table does not exist")
                continue

            target_count = int(azure_cursor.execute(f"SELECT COUNT(*) FROM dbo.{quote_identifier(table)}").fetchone()[0])
            if target_count and not args.replace:
                raise RuntimeError(
                    f"Azure SQL table {table} already contains {target_count} row(s). "
                    "Use a new database or rerun with --replace after confirming backups."
                )

            source_columns = sqlite_columns(sqlite_connection, table)
            target_column_set = set(azure_columns(azure_cursor, table))
            columns = [column for column in source_columns if column in target_column_set]
            if not columns:
                print(f"SKIP {table}: no matching columns")
                continue

            source_rows = sqlite_connection.execute(
                f"SELECT {', '.join(quote_identifier(column) for column in columns)} FROM {quote_identifier(table)}"
            ).fetchall()
            if not source_rows:
                print(f"OK   {table}: 0 rows")
                continue

            identity_insert = table in IDENTITY_TABLES and "id" in columns
            if identity_insert:
                azure_cursor.execute(f"SET IDENTITY_INSERT dbo.{quote_identifier(table)} ON")

            placeholders = ", ".join("?" for _ in columns)
            insert_sql = (
                f"INSERT INTO dbo.{quote_identifier(table)} "
                f"({', '.join(quote_identifier(column) for column in columns)}) VALUES ({placeholders})"
            )
            azure_cursor.executemany(insert_sql, [tuple(row[column] for column in columns) for row in source_rows])

            if identity_insert:
                azure_cursor.execute(f"SET IDENTITY_INSERT dbo.{quote_identifier(table)} OFF")
                max_id = max(int(row["id"] or 0) for row in source_rows)
                if max_id:
                    azure_cursor.execute(f"DBCC CHECKIDENT ('dbo.{table}', RESEED, {max_id})")

            azure_connection.commit()
            total_rows += len(source_rows)
            print(f"OK   {table}: {len(source_rows)} rows")

        print(f"Migration complete: {total_rows} total rows copied to Azure SQL")
        return 0
    except Exception:
        azure_connection.rollback()
        raise
    finally:
        azure_cursor.close()
        azure_connection.close()
        sqlite_connection.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
