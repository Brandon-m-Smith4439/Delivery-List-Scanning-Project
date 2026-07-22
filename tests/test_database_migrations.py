from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sqlite3
import unittest
import uuid

from database_migrations import MIGRATIONS, MigrationError, database_needs_upgrade
from delivery_store import SQLiteDeliveryStore
from scanner_config import load_config
from tools.database_integrity_check import check_database


ROOT = Path(__file__).resolve().parents[1]


def config_for(tmp_path: Path, *, production: bool = True):
    base = load_config(ROOT)
    return replace(
        base,
        database_path=tmp_path / "scanner.db",
        environment="production" if production else "development",
        sample_path=tmp_path / "sample-does-not-exist.json",
    )


def create_legacy_v096_database(tmp_path: Path) -> tuple[SQLiteDeliveryStore, Path]:
    config = config_for(tmp_path)
    store = SQLiteDeliveryStore(config)
    with store.connect() as connection:
        store._migration_001_v096_baseline(connection)
        connection.execute(
            "INSERT INTO delivery_lists (id,label,delivery_date,stage,scanner,status,revision,created_at) "
            "VALUES ('list-1','Test','2026-07-21','Staging - Airport Rd','Airport Rd','active',1,'2026-07-21T12:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO line_items (id,list_id,source_id,barcode,order_no,item_no,qty,scanned_qty) "
            "VALUES ('item-1','list-1','source-1','T20000000100100','235000','001',3,2)"
        )
        connection.execute(
            "INSERT INTO scan_events (list_id,line_item_id,barcode,event_type,message,qty_delta,created_at) "
            "VALUES ('list-1','item-1','T20000000100100','scan','Accepted',2,'2026-07-21T12:01:00+00:00')"
        )
        connection.commit()
    return store, Path(config.database_path)


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = ROOT / "_verification" / "unit-tests" / f"dls-v097-{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        # Verification output is intentionally left in the ignored test folder.
        # Windows floor/security policies can keep SQLite handles briefly after
        # close, making eager recursive cleanup unreliable.
        pass

    def test_existing_v096_database_is_backed_up_baselined_and_preserved(self) -> None:
        store, database = create_legacy_v096_database(self.tmp_path)
        self.assertTrue(database_needs_upgrade(database))
        store.initialize()
        with store.connect() as connection:
            migrations = connection.execute("SELECT version, checksum FROM schema_migrations ORDER BY version").fetchall()
            self.assertEqual([row["version"] for row in migrations], [1, 2])
            self.assertEqual([row["checksum"] for row in migrations], [migration.checksum for migration in MIGRATIONS])
            item = connection.execute("SELECT order_no,item_no,qty,scanned_qty FROM line_items WHERE id='item-1'").fetchone()
            self.assertEqual(tuple(item), ("235000", "001", 3, 2))
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM scan_events").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(len(list((self.tmp_path / "backups").glob("scanner-before-v097-*.db"))), 1)
        self.assertTrue(check_database(database)["ok"])

    def test_new_production_database_uses_migrations_without_demo_rows(self) -> None:
        store = SQLiteDeliveryStore(config_for(self.tmp_path))
        store.initialize()
        with store.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM delivery_lists").fetchone()[0], 0)
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('machines','scanners','machine_events')"
                )
            }
            self.assertEqual(tables, {"machines", "scanners", "machine_events"})

    def test_migrations_are_idempotent_and_do_not_create_second_backup(self) -> None:
        store, _ = create_legacy_v096_database(self.tmp_path)
        store.initialize()
        first_backups = list((self.tmp_path / "backups").glob("*.db"))
        store.initialize()
        self.assertEqual(list((self.tmp_path / "backups").glob("*.db")), first_backups)
        with store.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 2)

    def test_quantity_checks_and_immutable_history_are_enforced(self) -> None:
        store, _ = create_legacy_v096_database(self.tmp_path)
        store.initialize()
        with store.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE line_items SET scanned_qty = qty + 1 WHERE id = 'item-1'")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE scan_events SET message = 'changed' WHERE id = 1")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM scan_events WHERE id = 1")
            connection.execute(
                "INSERT INTO machine_events (event_type, qty, order_no, item_no, created_at_utc) "
                "VALUES ('scan', 1, '235000', '001', '2026-07-21T12:02:00+00:00')"
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE machine_events SET qty = 2 WHERE id = 1")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM machine_events WHERE id = 1")

    def test_migration_checksum_tampering_is_rejected(self) -> None:
        store, _ = create_legacy_v096_database(self.tmp_path)
        store.initialize()
        with store.connect() as connection:
            connection.execute("UPDATE schema_migrations SET checksum = 'bad' WHERE version = 1")
            connection.commit()
        with self.assertRaises(MigrationError):
            store.initialize()


if __name__ == "__main__":
    unittest.main()
