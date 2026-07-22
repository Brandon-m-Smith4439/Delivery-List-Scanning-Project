from dataclasses import replace
from pathlib import Path
import unittest
import uuid

from delivery_store import SQLiteDeliveryStore
from scanner_config import load_config


ROOT = Path(__file__).resolve().parents[1]


class ScanUndoRedoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = ROOT / "_verification" / "unit-tests" / f"scan-undo-{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        config = replace(
            load_config(ROOT),
            database_path=self.tmp_path / "scanner.db",
            environment="production",
            sample_path=self.tmp_path / "no-sample.json",
        )
        self.store = SQLiteDeliveryStore(config)
        self.store.initialize()
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO delivery_lists (id,label,delivery_date,stage,scanner,status,revision,created_at) "
                "VALUES ('staging-list','Undo Test','2026-07-21','Staging - Airport Rd','Airport Rd','active',1,'2026-07-21T12:00:00+00:00')"
            )
            connection.execute(
                """
                INSERT INTO line_items (
                    id,list_id,source_id,barcode,order_no,item_no,qty,scanned_qty,customer,job,product
                ) VALUES ('item-1','staging-list','source-1','T200235999001000','235999','001',5,0,'Test Customer','88660001 TEST JOB','3/8 Clear Tempered')
                """
            )
            connection.commit()

    def add_event(self, event_type: str, qty: int) -> None:
        with self.store.connect() as connection:
            connection.execute("UPDATE line_items SET scanned_qty = scanned_qty + ? WHERE id = 'item-1'", (qty,))
            connection.execute(
                """
                INSERT INTO scan_events (
                    list_id,line_item_id,barcode,canonical_barcode,user_name,station,
                    event_type,message,reason,qty_delta,created_at
                ) VALUES ('staging-list','item-1','T200235999001000','T200235999001000','tester','Test',?,?,?,?,'2026-07-21T12:01:00+00:00')
                """,
                (event_type, "Accepted", "", qty),
            )
            connection.commit()

    def scanned_qty(self) -> int:
        with self.store.connect() as connection:
            return int(connection.execute("SELECT scanned_qty FROM line_items WHERE id = 'item-1'").fetchone()[0])

    def test_manual_scan_can_be_undone_and_redone(self) -> None:
        self.add_event("manual_scan", 1)

        undo_payload = self.store.undo_last_scan("staging-list", "tester", "Test")
        self.assertEqual(self.scanned_qty(), 0)
        self.assertEqual(undo_payload["lastScan"]["eventType"], "undo")
        self.assertEqual(undo_payload["lastScan"]["qtyDelta"], -1)

        redo_payload = self.store.redo_last_undo("staging-list", "tester", "Test")
        self.assertEqual(self.scanned_qty(), 1)
        self.assertEqual(redo_payload["lastScan"]["eventType"], "redo")
        self.assertEqual(redo_payload["lastScan"]["qtyDelta"], 1)

    def test_multi_piece_event_reverses_actual_quantity_only_once(self) -> None:
        self.add_event("scan", 3)

        first = self.store.undo_last_scan("staging-list", "tester", "Test")
        self.assertEqual(self.scanned_qty(), 0)
        self.assertEqual(first["lastScan"]["qtyDelta"], -3)

        second = self.store.undo_last_scan("staging-list", "tester", "Test")
        self.assertEqual(self.scanned_qty(), 0)
        self.assertEqual(second["lastScan"]["message"], "Nothing to undo")

    def test_open_staging_rack_quantity_tracks_undo_and_redo(self) -> None:
        self.add_event("scan", 2)
        with self.store.connect() as connection:
            rack = connection.execute("SELECT id FROM racks WHERE rack_code = 'R1S'").fetchone()
            self.assertIsNotNone(rack)
            connection.execute(
                """
                INSERT INTO rack_items (rack_id,line_item_id,qty,status,added_by,added_at,reason)
                VALUES (?,'item-1',2,'Active','tester','2026-07-21T12:01:00+00:00','Test assignment')
                """,
                (rack["id"],),
            )
            connection.commit()

        self.store.undo_last_scan("staging-list", "tester", "Test")
        with self.store.connect() as connection:
            rack_item = connection.execute("SELECT qty,status FROM rack_items WHERE line_item_id = 'item-1'").fetchone()
            self.assertEqual((rack_item["qty"], rack_item["status"]), (2, "Removed"))

        self.store.redo_last_undo("staging-list", "tester", "Test")
        with self.store.connect() as connection:
            rack_item = connection.execute("SELECT qty,status FROM rack_items WHERE line_item_id = 'item-1'").fetchone()
            self.assertEqual((rack_item["qty"], rack_item["status"]), (2, "Active"))

    def test_rack_location_change_is_blocked_after_outbound_scan(self) -> None:
        self.add_event("scan", 1)
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO delivery_lists (id,label,delivery_date,stage,scanner,status,revision,created_at) "
                "VALUES ('outbound-list','Outbound Test','2026-07-21','Outbound - Airport Rd','Airport Rd','active',1,'2026-07-21T12:00:00+00:00')"
            )
            connection.execute(
                """
                INSERT INTO line_items (
                    id,list_id,source_id,barcode,order_no,item_no,qty,scanned_qty,customer,job,product
                ) VALUES ('outbound-item','outbound-list','source-1','T200235999001000','235999','001',5,1,'Test Customer','88660001 TEST JOB','3/8 Clear Tempered')
                """
            )
            connection.commit()

        with self.assertRaisesRegex(ValueError, "scanned Outbound"):
            self.store.assign_line_item_to_rack(
                {"lineItemId": "item-1", "rackCode": "R1S"},
                "tester",
            )


if __name__ == "__main__":
    unittest.main()
