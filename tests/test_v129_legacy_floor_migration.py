"""Regression tests for v129 legacy floor database compatibility repair."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "database_migrations.py"


def load_migration_module():
    contract = types.ModuleType("database_contract")
    contract.APPLICATION_VERSION = "129"
    contract.CURRENT_SCHEMA_VERSION = 3
    previous = sys.modules.get("database_contract")
    sys.modules["database_contract"] = contract
    try:
        spec = importlib.util.spec_from_file_location("database_migrations_v129_test", MIGRATION_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("database_contract", None)
        else:
            sys.modules["database_contract"] = previous


class LegacyFloorOwner:
    def __init__(self) -> None:
        self.compatibility_repairs = 0
        self.migration_two_saw_columns = False

    def _verify_v096_baseline(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'delivery_lists'"
        ).fetchone()
        if not row:
            raise RuntimeError("missing delivery_lists")

    def _upgrade_v096_columns(self, connection: sqlite3.Connection) -> None:
        self.compatibility_repairs += 1
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(line_items)")}
        if "source_route" not in columns:
            connection.execute("ALTER TABLE line_items ADD COLUMN source_route TEXT NOT NULL DEFAULT ''")
        if "priority_delivery_date" not in columns:
            connection.execute("ALTER TABLE line_items ADD COLUMN priority_delivery_date TEXT NOT NULL DEFAULT ''")
        if "priority_direct_to_truck" not in columns:
            connection.execute(
                "ALTER TABLE line_items ADD COLUMN priority_direct_to_truck INTEGER NOT NULL DEFAULT 0"
            )
        connection.commit()

    def _migration_001_v096_baseline(self, connection: sqlite3.Connection) -> None:
        raise AssertionError("legacy databases should be baselined, not recreated")

    def _migration_002_v097_production_database(self, connection: sqlite3.Connection) -> None:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(line_items)")}
        required = {"source_route", "priority_delivery_date", "priority_direct_to_truck"}
        self.migration_two_saw_columns = required.issubset(columns)
        if not self.migration_two_saw_columns:
            raise sqlite3.OperationalError("no such column: priority_delivery_date")

    def _migration_003_v120_user_line_updates(self, connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE IF NOT EXISTS line_update_notices (id INTEGER PRIMARY KEY)")


def create_pre_late_v096_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE delivery_lists (
            id TEXT PRIMARY KEY,
            delivery_date TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE line_items (
            id TEXT PRIMARY KEY,
            list_id TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL,
            scanned_qty INTEGER NOT NULL
        );
        INSERT INTO delivery_lists VALUES ('list-1', '2026-07-24', 'Staging', 'active');
        INSERT INTO line_items VALUES ('line-1', 'list-1', '10001', '001', 3, 2);
        """
    )
    connection.commit()
    return connection


class LegacyFloorMigrationTests(unittest.TestCase):
    def test_baselined_legacy_database_gets_columns_before_v097_rebuild(self) -> None:
        module = load_migration_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            connection = create_pre_late_v096_database(Path(temp_dir) / "floor.db")
            owner = LegacyFloorOwner()
            try:
                applied = module.run_sqlite_migrations(connection, owner)
                self.assertEqual(applied, [2, 3])
                self.assertEqual(owner.compatibility_repairs, 1)
                self.assertTrue(owner.migration_two_saw_columns)
                self.assertEqual(
                    connection.execute("SELECT scanned_qty FROM line_items WHERE id = 'line-1'").fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0],
                    3,
                )
            finally:
                connection.close()

    def test_existing_v096_baseline_record_is_repaired_too(self) -> None:
        module = load_migration_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            connection = create_pre_late_v096_database(Path(temp_dir) / "floor.db")
            module.ensure_migration_table(connection)
            migration = module.migration_by_version(1)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(version, name, checksum, applied_at_utc, execution_ms, app_version) "
                "VALUES (?, ?, ?, ?, 0, ?)",
                (migration.version, migration.name, migration.checksum, module.utc_now(), "096-baseline"),
            )
            connection.commit()
            owner = LegacyFloorOwner()
            try:
                applied = module.run_sqlite_migrations(connection, owner)
                self.assertEqual(applied, [2, 3])
                self.assertEqual(owner.compatibility_repairs, 1)
                self.assertTrue(owner.migration_two_saw_columns)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
