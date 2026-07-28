#!/usr/bin/env python3
"""Validate a Delivery List Scanner SQLite database without changing it."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.contract import (  # noqa: E402
    CURRENT_SCHEMA_VERSION,
    INDEX_DESCRIPTIONS,
    JSON_COLUMNS,
    REQUIRED_COLUMNS,
    TABLE_DESCRIPTIONS,
    TIMESTAMP_COLUMNS,
)
from database.migrations import MIGRATIONS  # noqa: E402


def parse_timestamp(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.astimezone(timezone.utc).utcoffset() == timezone.utc.utcoffset(None)


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
    )


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info([{table}])").fetchall()}


def add_issue(report: dict[str, Any], severity: str, code: str, message: str, **details: Any) -> None:
    report[severity].append({"code": code, "message": message, **details})


def check_database(database_path: str | Path) -> dict[str, Any]:
    path = Path(database_path).expanduser().resolve()
    report: dict[str, Any] = {
        "database": str(path),
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": False,
        "schemaVersion": 0,
        "errors": [],
        "warnings": [],
        "checks": {},
        "rowCounts": {},
    }
    if not path.exists():
        add_issue(report, "errors", "database_missing", f"Database not found: {path}")
        return report

    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        integrity_rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()]
        report["checks"]["integrityCheck"] = integrity_rows
        if integrity_rows != ["ok"]:
            add_issue(report, "errors", "integrity_check", "SQLite integrity_check failed", results=integrity_rows)

        foreign_key_rows = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]
        report["checks"]["foreignKeyViolations"] = len(foreign_key_rows)
        if foreign_key_rows:
            add_issue(
                report,
                "errors",
                "foreign_key_check",
                f"Found {len(foreign_key_rows)} foreign-key violation(s)",
                examples=foreign_key_rows[:20],
            )

        actual_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        missing_tables = sorted(set(TABLE_DESCRIPTIONS) - actual_tables)
        if missing_tables:
            add_issue(report, "errors", "missing_tables", "Canonical tables are missing", tables=missing_tables)

        column_differences: dict[str, list[str]] = {}
        for table, required in REQUIRED_COLUMNS.items():
            if table not in actual_tables:
                continue
            missing = sorted(required - table_columns(connection, table))
            if missing:
                column_differences[table] = missing
        report["checks"]["missingColumns"] = column_differences
        if column_differences:
            add_issue(report, "errors", "missing_columns", "Canonical columns are missing", tables=column_differences)

        if "schema_migrations" in actual_tables:
            migration_rows = connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
            versions = [int(row[0]) for row in migration_rows]
            report["schemaVersion"] = max(versions, default=0)
            expected_checksums = {migration.version: migration.checksum for migration in MIGRATIONS}
            for version, name, checksum in migration_rows:
                if int(version) not in expected_checksums:
                    add_issue(report, "errors", "unknown_migration", f"Unknown migration {version}: {name}")
                elif str(checksum) != expected_checksums[int(version)]:
                    add_issue(report, "errors", "migration_checksum", f"Migration {int(version):03d} checksum mismatch")
            missing_versions = sorted(set(expected_checksums) - set(versions))
            if missing_versions:
                add_issue(report, "errors", "missing_migrations", "Required migrations are not installed", versions=missing_versions)
            if report["schemaVersion"] != CURRENT_SCHEMA_VERSION:
                add_issue(
                    report,
                    "errors",
                    "schema_version",
                    f"Expected schema version {CURRENT_SCHEMA_VERSION}, found {report['schemaVersion']}",
                )

        actual_indexes = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        missing_indexes = sorted(set(INDEX_DESCRIPTIONS) - actual_indexes)
        report["checks"]["missingIndexes"] = missing_indexes
        if missing_indexes:
            add_issue(report, "warnings", "missing_indexes", "Documented query indexes are missing", indexes=missing_indexes)

        duplicate_queries = {
            "line_items_list_source": (
                "SELECT list_id || '|' || source_id, COUNT(*) FROM line_items "
                "WHERE is_deleted = 0 GROUP BY list_id, source_id HAVING COUNT(*) > 1"
            ),
            "rack_items_rack_line": (
                "SELECT CAST(rack_id AS TEXT) || '|' || line_item_id, COUNT(*) FROM rack_items "
                "WHERE is_deleted = 0 GROUP BY rack_id, line_item_id HAVING COUNT(*) > 1"
            ),
            "machine_code": "SELECT machine_code, COUNT(*) FROM machines WHERE is_deleted = 0 GROUP BY machine_code HAVING COUNT(*) > 1",
            "scanner_code": "SELECT scanner_code, COUNT(*) FROM scanners WHERE is_deleted = 0 GROUP BY scanner_code HAVING COUNT(*) > 1",
        }
        duplicate_results: dict[str, list[list[Any]]] = {}
        for name, query in duplicate_queries.items():
            try:
                rows = [list(row) for row in connection.execute(query).fetchmany(20)]
            except sqlite3.Error:
                rows = []
            if rows:
                duplicate_results[name] = rows
        report["checks"]["duplicateBusinessKeys"] = duplicate_results
        if duplicate_results:
            add_issue(report, "warnings", "duplicate_business_keys", "Potential duplicate business keys found", results=duplicate_results)

        malformed_timestamps: dict[str, list[dict[str, Any]]] = {}
        for table, columns in TIMESTAMP_COLUMNS.items():
            if table not in actual_tables:
                continue
            actual_columns = table_columns(connection, table)
            for column in sorted(columns & actual_columns):
                rows = connection.execute(
                    f"SELECT rowid, [{column}] FROM [{table}] WHERE COALESCE([{column}], '') <> ''"
                ).fetchall()
                bad = [{"rowid": row[0], "value": row[1]} for row in rows if not parse_timestamp(row[1])]
                if bad:
                    malformed_timestamps[f"{table}.{column}"] = bad[:20]
        report["checks"]["malformedTimestamps"] = malformed_timestamps
        if malformed_timestamps:
            add_issue(report, "errors", "malformed_timestamps", "Malformed or timezone-naive timestamps found", fields=malformed_timestamps)

        malformed_json: dict[str, list[dict[str, Any]]] = {}
        for table, columns in JSON_COLUMNS.items():
            if table not in actual_tables:
                continue
            actual_columns = table_columns(connection, table)
            for column in sorted(columns & actual_columns):
                rows = connection.execute(
                    f"SELECT rowid, [{column}] FROM [{table}] WHERE COALESCE([{column}], '') <> ''"
                ).fetchall()
                bad: list[dict[str, Any]] = []
                for rowid, value in rows:
                    try:
                        json.loads(str(value))
                    except (TypeError, ValueError):
                        bad.append({"rowid": rowid, "value": str(value)[:200]})
                if bad:
                    malformed_json[f"{table}.{column}"] = bad[:20]
        report["checks"]["malformedJson"] = malformed_json
        if malformed_json:
            add_issue(report, "errors", "malformed_json", "Malformed JSON values found", fields=malformed_json)

        for table in sorted(actual_tables):
            try:
                report["rowCounts"][table] = int(connection.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0])
            except sqlite3.Error:
                continue
    finally:
        connection.close()

    report["ok"] = not report["errors"]
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", default=str(ROOT / "data" / "delivery-scanner-pilot.db"))
    parser.add_argument("--json", action="store_true", help="Print the complete machine-readable report")
    parser.add_argument("--report", help="Optional path for a JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = check_database(args.database)
    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Database: {report['database']}")
        print(f"Schema version: {report['schemaVersion']}")
        print(f"Integrity: {'PASS' if report['ok'] else 'FAIL'}")
        for issue in report["errors"]:
            print(f"ERROR {issue['code']}: {issue['message']}")
        for issue in report["warnings"]:
            print(f"WARN  {issue['code']}: {issue['message']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
