# File: database/migrations.py
"""Numbered SQLite migrations and verified pre-upgrade backup support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable

from database.contract import APPLICATION_VERSION, CURRENT_SCHEMA_VERSION


class MigrationError(RuntimeError):
    """Raised when migration history or an upgrade is unsafe."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum_material: str
    method_name: str

    @property
    def checksum(self) -> str:
        """Handle checksum for the maintained Delivery List Scanner workflow."""
        value = f"{self.version}\n{self.name}\n{self.checksum_material}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()


MIGRATIONS = (
    Migration(1, "v096_baseline", "Delivery List Scanner v096 canonical SQLite schema", "_migration_001_v096_baseline"),
    Migration(
        2,
        "v097_production_database",
        "UTC audit fields, relational constraints, immutable history, machine scanning tables, query indexes, and atomic FK validation; final-v097-r1",
        "_migration_002_v097_production_database",
    ),
    Migration(
        3,
        "v120_user_line_updates",
        "Per-user current-and-future delivery-list line update notices and explicit review acknowledgements; v120-r1",
        "_migration_003_v120_user_line_updates",
    ),
    Migration(
        4,
        "v135_operations_workflows",
        "Internal reject tracking, manual delivery entries, per-line operational flags, and immutable packing-list print snapshots; v135-r1",
        "_migration_004_v135_operations_workflows",
    ),
)


def utc_now() -> str:
    """Handle utc now for the maintained Delivery List Scanner workflow."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migration_by_version(version: int) -> Migration:
    """Handle migration by version for the maintained Delivery List Scanner workflow."""
    for migration in MIGRATIONS:
        if migration.version == version:
            return migration
    raise KeyError(version)


def ensure_migration_table(connection: Any) -> None:
    """Handle ensure migration table for the maintained Delivery List Scanner workflow."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at_utc TEXT NOT NULL,
            execution_ms INTEGER NOT NULL DEFAULT 0 CHECK (execution_ms >= 0),
            app_version TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.commit()


def installed_migrations(connection: Any) -> dict[int, dict[str, Any]]:
    """Handle installed migrations for the maintained Delivery List Scanner workflow."""
    ensure_migration_table(connection)
    rows = connection.execute(
        "SELECT version, name, checksum, applied_at_utc, execution_ms, app_version FROM schema_migrations ORDER BY version"
    ).fetchall()
    return {
        int(row["version"]): {
            "version": int(row["version"]),
            "name": str(row["name"]),
            "checksum": str(row["checksum"]),
            "applied_at_utc": str(row["applied_at_utc"]),
            "execution_ms": int(row["execution_ms"]),
            "app_version": str(row["app_version"]),
        }
        for row in rows
    }


def validate_installed_checksums(connection: Any) -> None:
    """Handle validate installed checksums for the maintained Delivery List Scanner workflow."""
    installed = installed_migrations(connection)
    for version, row in installed.items():
        try:
            expected = migration_by_version(version)
        except KeyError as exc:
            raise MigrationError(f"Database contains unknown migration version {version}") from exc
        if row["checksum"] != expected.checksum:
            raise MigrationError(
                f"Migration {version:03d} checksum mismatch. The installed schema history must not be edited."
            )


def has_application_tables(connection: Any) -> bool:
    """Handle has application tables for the maintained Delivery List Scanner workflow."""
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'delivery_lists'"
    ).fetchone()
    return bool(row)


def baseline_legacy_v096(connection: Any, owner: Any) -> bool:
    """Handle baseline legacy v096 for the maintained Delivery List Scanner workflow."""
    installed = installed_migrations(connection)
    if installed or not has_application_tables(connection):
        return False
    owner._verify_v096_baseline(connection)
    migration = migration_by_version(1)
    connection.execute(
        "INSERT INTO schema_migrations (version, name, checksum, applied_at_utc, execution_ms, app_version) VALUES (?, ?, ?, ?, 0, ?)",
        (migration.version, migration.name, migration.checksum, utc_now(), "096-baseline"),
    )
    connection.commit()
    return True


def prepare_v096_compatibility_schema(connection: Any, owner: Any, installed: dict[int, dict[str, Any]]) -> None:
    """Complete the canonical v096 schema before the v097 table rebuild.

    Some floor databases were created during development before every v096
    support table and additive column existed. Merely recording the v096
    baseline is not enough for those databases: later startup work expects
    auxiliary tables such as ``system_metadata``, and the v097 rebuild expects
    fields such as ``priority_delivery_date``.

    Re-run the canonical v096 schema method here because it is deliberately
    idempotent: ``CREATE TABLE IF NOT EXISTS`` adds missing support tables, and
    the maintained compatibility helper adds only absent columns. Existing
    rows are not recreated or replaced. This also repairs a database that
    already carries the v096 baseline record but was created before the schema
    was complete.
    """
    if 2 in installed:
        return
    baseline = migration_by_version(1)
    initializer = getattr(owner, baseline.method_name, None)
    if not callable(initializer):
        raise MigrationError(
            "The database requires v096 schema completion, but the current store does not provide it."
        )
    initializer(connection)
    connection.commit()


def _ensure_column(connection: Any, table: str, column: str, definition: str) -> None:
    """Add one compatibility column only when it is absent."""
    columns = {str(row["name"]) for row in connection.execute(f"PRAGMA table_info([{table}])").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE [{table}] ADD COLUMN [{column}] {definition}")


def _migration_004_v135_operations_workflows(connection: Any) -> None:
    """Add internal rejects, manual orders, packing history, and per-line flags."""
    _ensure_column(connection, "line_items", "manual_only", "INTEGER NOT NULL DEFAULT 0 CHECK (manual_only IN (0, 1))")
    _ensure_column(connection, "line_items", "manual_source", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "line_items", "internal_reject_count", "INTEGER NOT NULL DEFAULT 0 CHECK (internal_reject_count >= 0)")
    _ensure_column(connection, "line_items", "last_reject_reason", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "line_items", "last_reject_location", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "line_items", "last_rejected_at", "TEXT NOT NULL DEFAULT ''")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS reject_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS reject_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS reject_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_date TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
            customer TEXT NOT NULL DEFAULT '',
            job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '',
            reason_label TEXT NOT NULL,
            location_label TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            rejected_at TEXT NOT NULL,
            rejected_by TEXT NOT NULL DEFAULT '',
            source_list_id TEXT NOT NULL DEFAULT '',
            source_line_item_id TEXT NOT NULL DEFAULT '',
            affected_list_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(affected_list_ids_json)),
            scan_qty_reduced INTEGER NOT NULL DEFAULT 0 CHECK (scan_qty_reduced >= 0)
        );
        CREATE TABLE IF NOT EXISTS packing_list_prints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rack_code TEXT NOT NULL,
            rack_name TEXT NOT NULL DEFAULT '',
            delivery_date TEXT NOT NULL DEFAULT '',
            printed_at TEXT NOT NULL,
            printed_by TEXT NOT NULL DEFAULT '',
            piece_qty INTEGER NOT NULL DEFAULT 0 CHECK (piece_qty >= 0),
            line_count INTEGER NOT NULL DEFAULT 0 CHECK (line_count >= 0),
            snapshot_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(snapshot_json))
        );
        CREATE TABLE IF NOT EXISTS manual_delivery_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_date TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL CHECK (qty > 0),
            route TEXT NOT NULL,
            customer TEXT NOT NULL DEFAULT '',
            job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '',
            dimensions TEXT NOT NULL DEFAULT '',
            manual_only INTEGER NOT NULL DEFAULT 0 CHECK (manual_only IN (0, 1)),
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            target_list_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(target_list_ids_json))
        );
        CREATE INDEX IF NOT EXISTS idx_reject_events_date_time
            ON reject_events(delivery_date, rejected_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_reject_events_order_item
            ON reject_events(order_no, item_no, rejected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_packing_list_prints_time
            ON packing_list_prints(printed_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_manual_delivery_entries_date
            ON manual_delivery_entries(delivery_date, created_at DESC, id DESC);
        """
    )
    created = utc_now()
    reason_defaults = ("Damaged / broken", "Edge chip", "Scratch / surface defect", "Incorrect size", "Other")
    location_defaults = ("Cutting", "Polisher", "Washer", "Tempering", "Wrapper", "Staging", "Rack / transport", "Other")
    for sort_order, label in enumerate(reason_defaults, start=1):
        connection.execute(
            "INSERT OR IGNORE INTO reject_reasons (label, active, sort_order, created_by, created_at, updated_at) VALUES (?, 1, ?, 'system', ?, ?)",
            (label, sort_order, created, created),
        )
    for sort_order, label in enumerate(location_defaults, start=1):
        connection.execute(
            "INSERT OR IGNORE INTO reject_locations (label, active, sort_order, created_by, created_at, updated_at) VALUES (?, 1, ?, 'system', ?, ?)",
            (label, sort_order, created, created),
        )


def run_sqlite_migrations(connection: Any, owner: Any) -> list[int]:
    """Handle run sqlite migrations for the maintained Delivery List Scanner workflow."""
    ensure_migration_table(connection)
    baseline_legacy_v096(connection, owner)
    validate_installed_checksums(connection)
    installed = installed_migrations(connection)
    prepare_v096_compatibility_schema(connection, owner, installed)
    installed = installed_migrations(connection)
    applied: list[int] = []
    for migration in MIGRATIONS:
        if migration.version > CURRENT_SCHEMA_VERSION or migration.version in installed:
            continue
        started = time.monotonic()
        method: Callable[[Any], None] | None = globals().get(migration.method_name)
        if not callable(method):
            method = getattr(owner, migration.method_name)
        foreign_keys_disabled = migration.version >= 2
        try:
            if foreign_keys_disabled:
                connection.commit()
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute("BEGIN IMMEDIATE")
            method(connection)
            elapsed_ms = max(int((time.monotonic() - started) * 1000), 0)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, checksum, applied_at_utc, execution_ms, app_version) VALUES (?, ?, ?, ?, ?, ?)",
                (migration.version, migration.name, migration.checksum, utc_now(), elapsed_ms, APPLICATION_VERSION),
            )
            if foreign_keys_disabled:
                violations = connection.execute("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise MigrationError(
                        f"Migration {migration.version:03d} left {len(violations)} foreign-key violation(s)"
                    )
            connection.commit()
            if foreign_keys_disabled:
                connection.execute("PRAGMA foreign_keys = ON")
        except Exception:
            connection.rollback()
            if foreign_keys_disabled:
                connection.execute("PRAGMA foreign_keys = ON")
            raise
        applied.append(migration.version)
        installed[migration.version] = {"checksum": migration.checksum}
    validate_installed_checksums(connection)
    if max(installed_migrations(connection), default=0) != CURRENT_SCHEMA_VERSION:
        raise MigrationError("Database did not reach the expected schema version")
    return applied


def database_needs_upgrade(path: Path) -> bool:
    """Handle database needs upgrade for the maintained Delivery List Scanner workflow."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    connection = sqlite3.connect(path)
    try:
        if not has_application_tables(connection):
            return False
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()
        if not table:
            return True
        row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
        return int(row[0] or 0) < CURRENT_SCHEMA_VERSION
    finally:
        connection.close()


def create_verified_backup(database_path: Path, backup_dir: Path | None = None) -> Path:
    """Create and verify an online SQLite backup without modifying the source."""
    database_path = database_path.resolve()
    if not database_path.exists():
        raise FileNotFoundError(database_path)
    target_dir = (backup_dir or database_path.parent / "backups").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = target_dir / f"{database_path.stem}-before-v{APPLICATION_VERSION}-{stamp}.db"
    source = sqlite3.connect(database_path, timeout=60)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
        destination.commit()
        result = destination.execute("PRAGMA integrity_check").fetchone()
        if not result or str(result[0]).lower() != "ok":
            raise MigrationError(f"Backup integrity check failed: {result[0] if result else 'no result'}")
        foreign_keys = destination.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            raise MigrationError(f"Backup contains {len(foreign_keys)} foreign-key violation(s)")
    except Exception:
        destination.close()
        source.close()
        if target.exists():
            target.unlink()
        raise
    destination.close()
    source.close()
    return target
