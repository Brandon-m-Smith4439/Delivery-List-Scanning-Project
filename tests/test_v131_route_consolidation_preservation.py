"""Regression tests for audited route-copy consolidation during floor transfer."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "upgrade_floor_database.py"


def load_transfer_module():
    spec = importlib.util.spec_from_file_location("upgrade_floor_database_v131_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_validation_database(path: Path, *, consolidated: bool, audited: bool = True, preserve_progress: bool = True) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE delivery_lists (
                id TEXT PRIMARY KEY,
                delivery_date TEXT NOT NULL,
                stage TEXT NOT NULL,
                scanner TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE line_items (
                id TEXT PRIMARY KEY,
                list_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                barcode TEXT NOT NULL DEFAULT '',
                order_no TEXT NOT NULL,
                item_no TEXT NOT NULL,
                qty INTEGER NOT NULL,
                scanned_qty INTEGER NOT NULL,
                job TEXT NOT NULL DEFAULT '',
                customer TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL DEFAULT '',
                entity_id TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        lists = [
            ("staging", "2026-07-24", "Staging - Airport Rd", "Airport Rd"),
            ("outbound", "2026-07-24", "Outbound - Airport Rd", "Airport Rd"),
            ("receive-it", "2026-07-24", "Inbound - Indian Trail", "Indian Trail"),
            ("receive-cpu", "2026-07-24", "Customer Pickup", "Customer Pickup"),
        ]
        connection.executemany(
            "INSERT INTO delivery_lists (id, delivery_date, stage, scanner) VALUES (?, ?, ?, ?)",
            lists,
        )
        connection.executemany(
            """
            INSERT INTO line_items (
                id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty, job, customer
            ) VALUES (?, ?, 'source-100-001', 'T200100001000001', '100', '001', ?, ?, 'JOB-1', 'Customer')
            """,
            [
                ("line-staging", "staging", 5, 3),
                ("line-outbound", "outbound", 5, 2),
                ("line-receive-a", "receive-it", 5, 4 if preserve_progress else 2),
            ],
        )
        if not consolidated:
            connection.execute(
                """
                INSERT INTO line_items (
                    id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty, job, customer
                ) VALUES ('line-receive-b', 'receive-cpu', 'source-100-001', 'T200100001000001', '100', '001', 5, 4, 'JOB-1', 'Customer')
                """
            )
        elif audited:
            connection.execute(
                "INSERT INTO audit_events (action, payload_json) VALUES (?, ?)",
                (
                    "merge_line_item_reference",
                    json.dumps({"sourceLineItemId": "line-receive-b", "targetListId": "receive-it"}),
                ),
            )
        connection.commit()
    finally:
        connection.close()


class RouteConsolidationPreservationTests(unittest.TestCase):
    def test_audited_receiving_duplicate_is_allowed(self) -> None:
        module = load_transfer_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source.db"
            upgraded = temp / "upgraded.db"
            create_validation_database(source, consolidated=False)
            create_validation_database(upgraded, consolidated=True)

            result = module.compare_preserved_counts(
                {"line_items": 4, "audit_events": 0},
                {"line_items": 3, "audit_events": 1},
                source_path=source,
                upgraded_path=upgraded,
            )

            self.assertEqual(result["line_items"]["before"], 4)
            self.assertEqual(result["line_items"]["after"], 3)
            self.assertEqual(result["line_items"]["consolidated_rows"], 1)
            self.assertIn("scan progress preserved", result["line_items"]["validation"])

    def test_unaudited_line_item_removal_still_fails(self) -> None:
        module = load_transfer_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source.db"
            upgraded = temp / "upgraded.db"
            create_validation_database(source, consolidated=False)
            create_validation_database(upgraded, consolidated=True, audited=False)

            with self.assertRaisesRegex(module.TransferError, "not recorded"):
                module.compare_preserved_counts(
                    {"line_items": 4},
                    {"line_items": 3},
                    source_path=source,
                    upgraded_path=upgraded,
                )

    def test_staging_row_removal_is_never_treated_as_consolidation(self) -> None:
        module = load_transfer_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source.db"
            upgraded = temp / "upgraded.db"
            create_validation_database(source, consolidated=False)
            create_validation_database(upgraded, consolidated=False)
            connection = sqlite3.connect(upgraded)
            try:
                connection.execute("DELETE FROM line_items WHERE id = 'line-staging'")
                connection.execute(
                    "INSERT INTO audit_events (action, payload_json) VALUES (?, ?)",
                    ("merge_line_item_reference", json.dumps({"sourceLineItemId": "line-staging"})),
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaisesRegex(module.TransferError, "staging or outbound"):
                module.compare_preserved_counts(
                    {"line_items": 4},
                    {"line_items": 3},
                    source_path=source,
                    upgraded_path=upgraded,
                )

    def test_scan_progress_regression_still_fails(self) -> None:
        module = load_transfer_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source.db"
            upgraded = temp / "upgraded.db"
            create_validation_database(source, consolidated=False)
            create_validation_database(upgraded, consolidated=True, preserve_progress=False)

            with self.assertRaisesRegex(module.TransferError, "scan progress decreased"):
                module.compare_preserved_counts(
                    {"line_items": 4},
                    {"line_items": 3},
                    source_path=source,
                    upgraded_path=upgraded,
                )


if __name__ == "__main__":
    unittest.main()
