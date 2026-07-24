"""Numbered SQLite migrations and verified pre-upgrade backup support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable

from database_contract import APPLICATION_VERSION, CURRENT_SCHEMA_VERSION


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


def prepare_v096_compatibility_columns(connection: Any, owner: Any, installed: dict[int, dict[str, Any]]) -> None:
    """Add historical v096 compatibility columns before the v097 table rebuild.

    Some floor databases predate late-v096 additive fields such as
    ``priority_delivery_date`` and ``priority_direct_to_truck`` but otherwise
    contain the complete operational schema. The v097 migration rebuilds
    ``line_items`` and therefore must normalize those additive columns first.
    This step is idempotent and also repairs databases that already carry the
    v096 baseline record but were created before those fields were introduced.
    """
    if 2 in installed:
        return
    upgrader = getattr(owner, "_upgrade_v096_columns", None)
    if not callable(upgrader):
        raise MigrationError(
            "The database requires pre-v097 compatibility repair, but the current store does not provide it."
        )
    upgrader(connection)
    connection.commit()


def run_sqlite_migrations(connection: Any, owner: Any) -> list[int]:
    """Handle run sqlite migrations for the maintained Delivery List Scanner workflow."""
    ensure_migration_table(connection)
    baseline_legacy_v096(connection, owner)
    validate_installed_checksums(connection)
    installed = installed_migrations(connection)
    prepare_v096_compatibility_columns(connection, owner, installed)
    installed = installed_migrations(connection)
    applied: list[int] = []
    for migration in MIGRATIONS:
        if migration.version in installed:
            continue
        started = time.monotonic()
        method: Callable[[Any], None] = getattr(owner, migration.method_name)
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
    target = target_dir / f"{database_path.stem}-before-v097-{stamp}.db"
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
