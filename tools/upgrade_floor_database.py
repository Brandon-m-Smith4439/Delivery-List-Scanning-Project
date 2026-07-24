#!/usr/bin/env python3
"""Safely move an older floor SQLite database into the current scanner project.

The transfer is intentionally a clone-and-upgrade operation, not a row-by-row
merge. The selected floor database remains untouched. The current project's
SQLite database is backed up, replaced with an online SQLite backup of the
floor database, and then upgraded by the current application's maintained
schema/migration code.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_NAME = "delivery-scanner-pilot.db"
REQUIRED_LEGACY_TABLES = {
    "delivery_lists",
    "line_items",
    "scan_events",
    "audit_events",
    "users",
    "racks",
    "bays",
}
EXCLUDED_COUNT_TABLES = {"sqlite_sequence", "schema_migrations"}


class TransferError(RuntimeError):
    """Raised when the transfer cannot safely continue."""


@dataclass
class DatabaseSnapshot:
    path: str
    size_bytes: int
    schema_version: int
    integrity_check: str
    foreign_key_violations: int
    table_counts: dict[str, int]


@dataclass
class TransferReport:
    started_at_utc: str
    completed_at_utc: str
    project_root: str
    source_database: str
    target_database: str
    backup_folder: str
    source_backup: str
    target_backup: str
    failed_upgrade_copy: str
    migrations_applied: list[int]
    expected_schema_version: int
    source_snapshot: dict[str, Any]
    upgraded_snapshot: dict[str, Any]
    preserved_table_counts: dict[str, dict[str, Any]]
    status: str
    message: str


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clone an older floor Delivery List Scanner SQLite database into the "
            "current project and run the current maintained migrations."
        )
    )
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Current/new Delivery List Scanner project folder.",
    )
    parser.add_argument(
        "--source",
        default=os.environ.get("DLS_FLOOR_TRANSFER_SOURCE", ""),
        help=(
            "Old floor database file, old project folder, or old project data folder. "
            f"Folders are searched for data/{DEFAULT_DATABASE_NAME} and {DEFAULT_DATABASE_NAME}."
        ),
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for the old project/database path when --source was not supplied.",
    )
    parser.add_argument(
        "--target",
        default="",
        help="Optional explicit current-project SQLite target path.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the TRANSFER confirmation prompt. Intended for automated tests only.",
    )
    parser.add_argument(
        "--keep-failed-target",
        action="store_true",
        help="Keep the failed upgraded target in place instead of restoring the prior target.",
    )
    args = parser.parse_args(argv)
    repair_merged_windows_project_root(args)
    return args


def repair_merged_windows_project_root(args: argparse.Namespace) -> None:
    """Repair the Windows trailing-backslash quoting failure from older BAT launchers.

    A quoted argument ending in a backslash can escape its closing quote under the
    Windows command-line parser. In the affected launcher, ``--interactive`` was
    consequently appended to the project-root value. The current BAT removes the
    trailing separator before launch, while this guard keeps already-extracted old
    launchers from producing a misleading missing-project error.
    """
    raw = str(args.project_root or "")
    for suffix in ('" --interactive', "' --interactive"):
        if raw.endswith(suffix):
            args.project_root = raw[: -len(suffix)]
            args.interactive = True
            return


def prompt_source_path() -> str:
    """Read the source path inside Python so CMD metacharacters cannot close the BAT."""
    print("Paste the OLD project folder, its data folder, or the old database file.")
    print("Example: C:\\Delivery List Scanner OLD")
    try:
        return input("Old floor project/database path: ").strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise TransferError("No source path was entered. Nothing was changed.") from exc


def resolve_source_argument(args: argparse.Namespace) -> str:
    """Return a supplied, drag-dropped, environment, or interactively entered path."""
    value = str(args.source or "").strip()
    if not value and args.interactive:
        value = prompt_source_path()
    if not value:
        raise TransferError(
            "No source database path was supplied. Run the BAT and paste the old project "
            "folder or database path when prompted."
        )
    return value


def normalize_user_path(value: str) -> Path:
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        raise TransferError("No source database path was supplied.")
    return Path(os.path.expandvars(text)).expanduser()


def resolve_source_database(value: str) -> Path:
    candidate = normalize_user_path(value)
    if candidate.is_dir():
        choices = [
            candidate / "data" / DEFAULT_DATABASE_NAME,
            candidate / DEFAULT_DATABASE_NAME,
        ]
        for path in choices:
            if path.is_file():
                return path.resolve()
        raise TransferError(
            "The selected folder does not contain the scanner database. Expected either "
            f"{choices[0]} or {choices[1]}."
        )
    if not candidate.is_file():
        raise TransferError(f"The old floor database was not found: {candidate}")
    return candidate.resolve()


def project_python_import(project_root: Path) -> None:
    root_text = str(project_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def resolve_target_database(project_root: Path, explicit_target: str = "") -> tuple[Path, str]:
    if explicit_target:
        return normalize_user_path(explicit_target).resolve(), "sqlite"

    project_python_import(project_root)
    try:
        from scanner_config import load_config
    except Exception as exc:  # pragma: no cover - exercised through subprocess tests
        raise TransferError(
            "The current project could not load scanner_config.py. Run this tool from the "
            "new/current Delivery List Scanner project folder."
        ) from exc

    config = load_config(project_root)
    database_type = str(getattr(config, "database_type", "sqlite") or "sqlite").lower()
    database_path = Path(getattr(config, "database_path", project_root / "data" / DEFAULT_DATABASE_NAME))
    return database_path.expanduser().resolve(), database_type


def quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def connect_read_only(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=60)
    connection.row_factory = sqlite3.Row
    return connection


def connect_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=60)
    connection.row_factory = sqlite3.Row
    return connection


def user_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    result: dict[str, int] = {}
    for table in user_tables(connection):
        try:
            row = connection.execute(f"SELECT COUNT(*) AS count_value FROM {quote_identifier(table)}").fetchone()
            result[table] = int(row["count_value"] if row else 0)
        except sqlite3.DatabaseError as exc:
            raise TransferError(f"Could not count records in {table}: {exc}") from exc
    return result


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    """Return the current columns for one SQLite table."""
    return {str(row["name"]) for row in connection.execute(
        f"PRAGMA table_info({quote_identifier(table)})"
    ).fetchall()}


def selectable_column(
    table_alias: str, columns: set[str], column: str, output_name: str, default_sql: str = "''"
) -> str:
    """Build a SELECT expression that tolerates older optional columns."""
    if column in columns:
        return f"{table_alias}.{quote_identifier(column)} AS {quote_identifier(output_name)}"
    return f"{default_sql} AS {quote_identifier(output_name)}"


def line_item_preservation_rows(path: Path) -> dict[str, dict[str, Any]]:
    """Read the stable line-item identity fields used by transfer validation.

    Early floor databases do not all have the same optional columns, so this
    reader selects only columns that exist and supplies safe defaults for the
    rest. The resulting records are read-only validation data.
    """
    connection = connect_read_only(path)
    try:
        tables = set(user_tables(connection))
        if "line_items" not in tables or "delivery_lists" not in tables:
            return {}
        line_columns = table_columns(connection, "line_items")
        list_columns = table_columns(connection, "delivery_lists")
        required_line = {"id", "list_id", "order_no", "item_no", "qty", "scanned_qty"}
        required_list = {"id", "delivery_date", "stage"}
        if not required_line.issubset(line_columns) or not required_list.issubset(list_columns):
            return {}

        expressions = [
            selectable_column("li", line_columns, "id", "line_id"),
            selectable_column("li", line_columns, "list_id", "list_id"),
            selectable_column("li", line_columns, "source_id", "source_id"),
            selectable_column("li", line_columns, "barcode", "barcode"),
            selectable_column("li", line_columns, "order_no", "order_no"),
            selectable_column("li", line_columns, "item_no", "item_no"),
            selectable_column("li", line_columns, "job", "job"),
            selectable_column("li", line_columns, "customer", "customer"),
            selectable_column("li", line_columns, "qty", "qty", "0"),
            selectable_column("li", line_columns, "scanned_qty", "scanned_qty", "0"),
            selectable_column("dl", list_columns, "delivery_date", "delivery_date"),
            selectable_column("dl", list_columns, "stage", "stage"),
            selectable_column("dl", list_columns, "scanner", "scanner"),
        ]
        rows = connection.execute(
            "SELECT " + ", ".join(expressions)
            + " FROM line_items li LEFT JOIN delivery_lists dl ON dl.id = li.list_id"
        ).fetchall()
        return {str(row["line_id"]): dict(row) for row in rows}
    finally:
        connection.close()


def stage_family(value: Any) -> str:
    """Reduce a stage label to the three route-copy families used by the app."""
    text = str(value or "").strip().lower()
    if "staging" in text:
        return "staging"
    if "outbound" in text:
        return "outbound"
    return "receiving"


def logical_line_item_key(record: dict[str, Any]) -> tuple[str, str, str]:
    """Return a route-copy-independent logical identity for one line item."""
    source_token = str(record.get("barcode") or "").strip()
    if not source_token:
        source_token = str(record.get("source_id") or "").strip()
    if not source_token:
        source_token = "|".join(
            str(record.get(name) or "").strip()
            for name in ("order_no", "item_no", "job", "customer")
        )
    return (
        str(record.get("delivery_date") or "").strip(),
        source_token,
        stage_family(record.get("stage")),
    )


def merged_line_item_ids(path: Path) -> set[str]:
    """Read source IDs recorded by the maintained route-duplicate merge audit."""
    connection = connect_read_only(path)
    try:
        if "audit_events" not in set(user_tables(connection)):
            return set()
        columns = table_columns(connection, "audit_events")
        if not {"action", "payload_json"}.issubset(columns):
            return set()
        rows = connection.execute(
            "SELECT payload_json FROM audit_events WHERE action = ?",
            ("merge_line_item_reference",),
        ).fetchall()
        merged: set[str] = set()
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                continue
            source_id = str(payload.get("sourceLineItemId") or "").strip()
            if source_id:
                merged.add(source_id)
        return merged
    finally:
        connection.close()


def validate_line_item_consolidation(source_path: Path, upgraded_path: Path) -> dict[str, Any]:
    """Validate an intentional reduction caused by route-copy consolidation.

    Current startup repairs can merge duplicate receiving-stage copies of the
    same logical item. A raw row-count comparison treats that safe repair as
    data loss. This check allows the reduction only when every removed row is a
    receiving-stage duplicate, every removal has the maintained merge audit,
    and an equivalent logical row remains with at least the same quantity and
    scanned progress.
    """
    before = line_item_preservation_rows(source_path)
    after = line_item_preservation_rows(upgraded_path)
    if not before or not after:
        raise TransferError(
            "Line-item counts decreased, but the transfer could not read enough legacy "
            "identity data to prove that the removed rows were safe route duplicates."
        )

    removed_ids = sorted(set(before) - set(after))
    if not removed_ids:
        raise TransferError(
            "Line-item counts decreased without identifiable removed line-item IDs."
        )

    non_receiving = [
        line_id for line_id in removed_ids
        if stage_family(before[line_id].get("stage")) != "receiving"
    ]
    if non_receiving:
        raise TransferError(
            "Line-item preservation failed because staging or outbound rows disappeared: "
            + ", ".join(non_receiving[:10])
        )

    audited_merges = merged_line_item_ids(upgraded_path)
    unaudited = [line_id for line_id in removed_ids if line_id not in audited_merges]
    if unaudited:
        raise TransferError(
            "Line-item preservation failed because removed rows were not recorded by the "
            "maintained route-duplicate merge audit: " + ", ".join(unaudited[:10])
        )

    after_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in after.values():
        after_groups.setdefault(logical_line_item_key(record), []).append(record)

    missing_logical: list[str] = []
    quantity_regressions: list[str] = []
    for line_id in removed_ids:
        source_record = before[line_id]
        candidates = after_groups.get(logical_line_item_key(source_record), [])
        if not candidates:
            missing_logical.append(line_id)
            continue
        old_qty = int(source_record.get("qty") or 0)
        old_scanned = int(source_record.get("scanned_qty") or 0)
        max_qty = max(int(record.get("qty") or 0) for record in candidates)
        max_scanned = max(int(record.get("scanned_qty") or 0) for record in candidates)
        if max_qty < old_qty or max_scanned < old_scanned:
            quantity_regressions.append(
                f"{line_id} (qty {old_qty}->{max_qty}, scanned {old_scanned}->{max_scanned})"
            )

    if missing_logical:
        raise TransferError(
            "Line-item preservation failed because no equivalent receiving row remained for: "
            + ", ".join(missing_logical[:10])
        )
    if quantity_regressions:
        raise TransferError(
            "Line-item preservation failed because consolidated quantities or scan progress decreased: "
            + "; ".join(quantity_regressions[:10])
        )

    return {
        "consolidated_rows": len(removed_ids),
        "audited_merge_rows": len(removed_ids),
        "validation": "audited receiving-route duplicates consolidated; logical quantities and scan progress preserved",
    }


def schema_version(connection: sqlite3.Connection) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
    ).fetchone()
    if not exists:
        return 0
    row = connection.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
    return int(row["version"] if row else 0)


def integrity_result(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0] if row else "no result")


def foreign_key_violation_count(connection: sqlite3.Connection) -> int:
    return len(connection.execute("PRAGMA foreign_key_check").fetchall())


def snapshot_database(path: Path) -> DatabaseSnapshot:
    if not path.is_file() or path.stat().st_size <= 0:
        raise TransferError(f"Database file is missing or empty: {path}")
    connection = connect_read_only(path)
    try:
        integrity = integrity_result(connection)
        if integrity.lower() != "ok":
            raise TransferError(f"SQLite integrity check failed for {path}: {integrity}")
        return DatabaseSnapshot(
            path=str(path),
            size_bytes=path.stat().st_size,
            schema_version=schema_version(connection),
            integrity_check=integrity,
            foreign_key_violations=foreign_key_violation_count(connection),
            table_counts=table_counts(connection),
        )
    finally:
        connection.close()


def verify_floor_schema(snapshot: DatabaseSnapshot) -> None:
    tables = set(snapshot.table_counts)
    missing = sorted(REQUIRED_LEGACY_TABLES - tables)
    if missing:
        raise TransferError(
            "The selected database is older than the maintained v096-compatible floor schema "
            "or is not a Delivery List Scanner database. Missing required tables: "
            + ", ".join(missing)
            + ". Nothing was changed."
        )
    if snapshot.foreign_key_violations:
        raise TransferError(
            f"The old floor database contains {snapshot.foreign_key_violations} foreign-key "
            "violation(s). Repair or provide the database for review before upgrading."
        )


def verified_online_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    source_connection = connect_read_only(source)
    destination_connection = connect_database(destination)
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
        integrity = integrity_result(destination_connection)
        if integrity.lower() != "ok":
            raise TransferError(f"Backup integrity check failed for {destination}: {integrity}")
        violations = foreign_key_violation_count(destination_connection)
        if violations:
            raise TransferError(
                f"Backup validation found {violations} foreign-key violation(s) in {destination}."
            )
    finally:
        destination_connection.close()
        source_connection.close()


def remove_sqlite_sidecars(database_path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(database_path) + suffix)
        if not sidecar.exists():
            continue
        try:
            sidecar.unlink()
        except OSError as exc:
            raise TransferError(
                f"Could not remove {sidecar.name}. The current web app may still be running. "
                "Close every scanner server window and retry."
            ) from exc


def read_expected_schema_version(project_root: Path) -> int:
    project_python_import(project_root)
    try:
        from database_contract import CURRENT_SCHEMA_VERSION
    except Exception as exc:
        raise TransferError(
            "The current project could not load database_contract.py. The current application "
            "files must be complete before transferring floor data."
        ) from exc
    return int(CURRENT_SCHEMA_VERSION)


def run_current_migrations(project_root: Path, target_path: Path) -> tuple[list[int], int]:
    project_python_import(project_root)
    os.environ["DLS_DATABASE_TYPE"] = "sqlite"
    os.environ["DLS_DATABASE_PATH"] = str(target_path)

    expected_version = read_expected_schema_version(project_root)
    connection = connect_read_only(target_path)
    try:
        before_version = schema_version(connection)
    finally:
        connection.close()

    try:
        from scanner_config import load_config
        from delivery_store import create_store
    except Exception as exc:
        raise TransferError(
            "The current scanner migration modules could not be imported. Confirm that "
            "scanner_config.py, delivery_store.py, database_contract.py, and "
            "database_migrations.py are present in the current project."
        ) from exc

    config = load_config(project_root)
    if str(getattr(config, "database_type", "sqlite") or "sqlite").lower() != "sqlite":
        raise TransferError("The floor transfer utility supports SQLite projects only.")
    store = create_store(config)
    store.initialize()

    connection = connect_read_only(target_path)
    try:
        after_version = schema_version(connection)
    finally:
        connection.close()
    if after_version != expected_version:
        raise TransferError(
            f"The upgraded database reached schema version {after_version}, but the current "
            f"application expects version {expected_version}."
        )
    applied = list(range(before_version + 1, after_version + 1)) if after_version > before_version else []
    return applied, expected_version


def compare_preserved_counts(
    source_counts: dict[str, int],
    upgraded_counts: dict[str, int],
    *,
    source_path: Path | None = None,
    upgraded_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    missing_tables: list[str] = []
    decreased: list[str] = []
    for table, old_count in sorted(source_counts.items()):
        if table in EXCLUDED_COUNT_TABLES:
            continue
        if table not in upgraded_counts:
            missing_tables.append(table)
            continue
        new_count = int(upgraded_counts[table])
        result[table] = {"before": int(old_count), "after": new_count}
        if new_count >= int(old_count):
            continue
        if table == "line_items" and source_path is not None and upgraded_path is not None:
            consolidation = validate_line_item_consolidation(source_path, upgraded_path)
            result[table].update(consolidation)
            continue
        decreased.append(f"{table} ({old_count} -> {new_count})")
    if missing_tables:
        raise TransferError(
            "The upgraded database is missing table(s) that existed in the old floor database: "
            + ", ".join(missing_tables)
        )
    if decreased:
        raise TransferError(
            "Record preservation validation failed because table counts decreased: "
            + "; ".join(decreased)
        )
    return result


def write_report(path: Path, report: TransferReport) -> None:
    path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def display_summary(snapshot: DatabaseSnapshot, title: str) -> None:
    counts = snapshot.table_counts
    print(title)
    print(f"  File: {snapshot.path}")
    print(f"  Size: {snapshot.size_bytes:,} bytes")
    print(f"  Schema version: {snapshot.schema_version}")
    for table in ("delivery_lists", "line_items", "scan_events", "racks", "rack_items", "bays", "bay_assignments", "users", "imports"):
        if table in counts:
            print(f"  {table}: {counts[table]:,}")


def confirm_transfer(source: Path, target: Path) -> None:
    print("\nIMPORTANT")
    print("- Close the old and new Delivery List Scanner server windows before continuing.")
    print("- The old database will not be modified.")
    print("- The current project's database will be backed up, then replaced by the floor data.")
    print("- This is a replacement/upgrade, not a merge of two active databases.")
    print(f"\nOld floor database: {source}")
    print(f"Current target:      {target}")
    response = input("\nType TRANSFER to continue: ").strip()
    if response != "TRANSFER":
        raise TransferError("Transfer cancelled. Nothing was changed.")


def preserve_failed_target(target: Path, failed_path: Path) -> str:
    if not target.exists():
        return ""
    try:
        verified_online_backup(target, failed_path)
        return str(failed_path)
    except Exception:
        try:
            shutil.copy2(target, failed_path)
            return str(failed_path)
        except Exception:
            return ""


def restore_prior_target(target: Path, target_backup: Path | None) -> None:
    remove_sqlite_sidecars(target)
    if target_backup and target_backup.is_file():
        restore_temp = target.with_name(target.name + ".restore.tmp")
        verified_online_backup(target_backup, restore_temp)
        os.replace(restore_temp, target)
    elif target.exists():
        target.unlink()


def run_transfer(args: argparse.Namespace) -> Path:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise TransferError(f"Current project folder was not found: {project_root}")

    source_text = resolve_source_argument(args)
    source = resolve_source_database(source_text)
    target, database_type = resolve_target_database(project_root, args.target)
    if database_type != "sqlite":
        raise TransferError(
            f"The current project is configured for {database_type}, not SQLite. This tool does not migrate to Azure SQL."
        )
    if source == target:
        raise TransferError(
            "The source and target paths are the same. The current application can upgrade that database "
            "in place on startup; do not run the transfer against the same file."
        )

    source_snapshot = snapshot_database(source)
    verify_floor_schema(source_snapshot)
    display_summary(source_snapshot, "\nOld floor database validated:")

    if not args.yes:
        confirm_transfer(source, target)

    stamp = utc_stamp()
    target.parent.mkdir(parents=True, exist_ok=True)
    backup_folder = target.parent / "backups" / f"floor-database-transfer-{stamp}"
    backup_folder.mkdir(parents=True, exist_ok=False)
    source_backup = backup_folder / "old-floor-database-original.db"
    target_backup = backup_folder / "current-target-before-transfer.db"
    failed_target = backup_folder / "failed-upgraded-target.db"
    report_path = backup_folder / "transfer-report.json"
    incoming = target.with_name(target.name + f".incoming-{stamp}.tmp")

    started_at = utc_now()
    target_backup_path: Path | None = None
    replaced_target = False
    report = TransferReport(
        started_at_utc=started_at,
        completed_at_utc="",
        project_root=str(project_root),
        source_database=str(source),
        target_database=str(target),
        backup_folder=str(backup_folder),
        source_backup=str(source_backup),
        target_backup="",
        failed_upgrade_copy="",
        migrations_applied=[],
        expected_schema_version=0,
        source_snapshot=asdict(source_snapshot),
        upgraded_snapshot={},
        preserved_table_counts={},
        status="running",
        message="Transfer started.",
    )

    try:
        print(f"\nCreating verified source backup: {source_backup}")
        verified_online_backup(source, source_backup)

        if target.exists() and target.stat().st_size > 0:
            print(f"Creating verified current-target backup: {target_backup}")
            verified_online_backup(target, target_backup)
            target_backup_path = target_backup
            report.target_backup = str(target_backup)

        print("Creating a WAL-safe incoming copy of the old floor database...")
        verified_online_backup(source, incoming)

        remove_sqlite_sidecars(target)
        try:
            os.replace(incoming, target)
        except OSError as exc:
            raise TransferError(
                "Windows could not replace the current database. The scanner server is probably still running "
                "or the file is open in another program. Close it and retry."
            ) from exc
        replaced_target = True

        print("Running the current application's maintained database migrations...")
        applied, expected_version = run_current_migrations(project_root, target)
        report.migrations_applied = applied
        report.expected_schema_version = expected_version

        upgraded_snapshot = snapshot_database(target)
        if upgraded_snapshot.foreign_key_violations:
            raise TransferError(
                f"The upgraded database has {upgraded_snapshot.foreign_key_violations} foreign-key violation(s)."
            )
        preserved = compare_preserved_counts(
            source_snapshot.table_counts,
            upgraded_snapshot.table_counts,
            source_path=source_backup,
            upgraded_path=target,
        )
        line_item_result = preserved.get("line_items", {})
        if line_item_result.get("consolidated_rows"):
            print(
                "Validated intentional receiving-route consolidation: "
                f"{line_item_result['consolidated_rows']} duplicate line-item row(s) merged "
                "with audit records and scan progress preserved."
            )
        report.upgraded_snapshot = asdict(upgraded_snapshot)
        report.preserved_table_counts = preserved
        report.status = "success"
        report.message = "Floor database copied, upgraded, and validated successfully."
        report.completed_at_utc = utc_now()
        write_report(report_path, report)

        display_summary(upgraded_snapshot, "\nCurrent database after upgrade:")
        print("\nSUCCESS")
        print("The old floor data is now in the current project database.")
        print(f"Backup and validation report: {backup_folder}")
        print("Keep the old project and this backup folder until floor testing is complete.")
        return report_path
    except Exception as exc:
        report.status = "failed"
        report.message = str(exc)
        report.completed_at_utc = utc_now()
        if replaced_target:
            report.failed_upgrade_copy = preserve_failed_target(target, failed_target)
            if not args.keep_failed_target:
                try:
                    restore_prior_target(target, target_backup_path)
                    report.message += " The prior current-project database was restored."
                except Exception as restore_exc:
                    report.message += f" Automatic target restore also failed: {restore_exc}"
        write_report(report_path, report)
        raise
    finally:
        if incoming.exists():
            incoming.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report_path = run_transfer(args)
        print(f"Report: {report_path}")
        return 0
    except TransferError as exc:
        print(f"\nTRANSFER FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort diagnostic path
        print(f"\nUNEXPECTED TRANSFER FAILURE: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
