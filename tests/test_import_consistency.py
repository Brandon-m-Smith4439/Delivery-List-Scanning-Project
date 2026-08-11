# File: tests/test_import_consistency.py
"""Regression coverage for delivery-list stage routing and import quantities."""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from backend.config import load_config
from backend.store import SQLiteDeliveryStore


ROOT = Path(__file__).resolve().parents[1]


def imported_item(order: str, item: str, qty: int, source_id: str) -> dict[str, object]:
    return {
        "sourceId": source_id,
        "order": order,
        "item": item,
        "qty": qty,
        "job": f"88{order} TEST JOB",
        "customer": "TEST CUSTOMER",
        "product": '3/8" Clear Tempered',
        "route": "IT",
        "sourceRoute": "IT",
        "barcode": f"T200{order}{item.zfill(3)}000",
    }


class ImportConsistencyTests(unittest.TestCase):
    def make_store(self, folder: Path) -> SQLiteDeliveryStore:
        base = load_config(ROOT)
        config = replace(
            base,
            root=folder,
            data_dir=folder,
            database_path=folder / "scanner.db",
            temp_delivery_lists_dir=folder,
            sample_path=ROOT / "data" / "sample-delivery-list.json",
            environment="production",
        )
        store = SQLiteDeliveryStore(config)
        with store.connect() as connection:
            store.create_schema(connection)
        return store

    def test_legacy_stage_copy_totals_are_normalized_to_physical_pieces(self) -> None:
        store = SQLiteDeliveryStore.__new__(SQLiteDeliveryStore)
        stages = [
            {
                "listId": "2026-08-13-staging-airport",
                "stage": "Staging - Airport Rd",
                "changedLineCount": 17,
                "newPieceQty": 18,
                "addedPieceQty": 18,
                "changedPieceQty": 18,
                "totalQty": 80,
            },
            {
                "listId": "2026-08-13-outbound-airport",
                "stage": "Outbound - Airport Rd",
                "changedLineCount": 17,
                "newPieceQty": 18,
                "addedPieceQty": 18,
                "changedPieceQty": 18,
                "totalQty": 80,
            },
            {
                "listId": "2026-08-13-inbound-indian-trail",
                "stage": "Inbound - Indian Trail",
                "changedLineCount": 17,
                "newPieceQty": 18,
                "addedPieceQty": 18,
                "changedPieceQty": 18,
                "totalQty": 69,
            },
        ]
        normalized = store.normalize_import_change_summary(
            {"addedPieceQty": 54, "changedPieceQty": 54, "stages": stages}
        )
        self.assertEqual(normalized["addedPieceQty"], 18)
        self.assertEqual(normalized["changedPieceQty"], 18)

        route_stage_only = store.normalize_import_change_summary({
            "stages": [{
                "listId": "2026-08-13-customer-pickup",
                "stage": "Customer Pickup",
                "created": True,
                "changedLineCount": 2,
                "addedPieceQty": 8,
                "changedPieceQty": 8,
            }]
        })
        self.assertFalse(route_stage_only["newDeliveryList"])

    def test_indian_trail_import_update_and_restore_keep_correct_stages_and_counts(self) -> None:
        verification_root = ROOT / "_verification"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            payload = {
                "deliveryDate": "2026-08-14",
                "items": [
                    imported_item("240001", "1", 2, "test:1"),
                    imported_item("240001", "2", 3, "test:2"),
                ],
            }

            created = store.import_delivery_list(
                {"payload": payload, "fileName": "Delivery List 08-14-2026.xlsx", "user": "admin"}
            )
            stage_ids = {
                row["id"] for row in created["lists"] if row["deliveryDate"] == "2026-08-14"
            }
            self.assertEqual(
                stage_ids,
                {
                    "2026-08-14-staging-airport",
                    "2026-08-14-outbound-airport",
                    "2026-08-14-inbound-indian-trail",
                },
            )
            self.assertNotIn("2026-08-14-customer-pickup", stage_ids)
            self.assertTrue(created["newDeliveryList"])
            self.assertEqual(created["addedPieceQty"], 5)

            updated_payload = {
                **payload,
                "items": [
                    *payload["items"],
                    imported_item("240002", "1", 4, "test:3"),
                ],
            }
            updated = store.import_delivery_list(
                {"payload": updated_payload, "fileName": "Delivery List 08-14-2026.xlsx", "user": "admin"}
            )
            self.assertFalse(updated["newDeliveryList"])
            self.assertEqual(updated["createdCount"], 0)
            self.assertEqual(updated["addedPieceQty"], 4)

            store.delete_delivery_date("2026-08-14", "admin")
            restored = store.import_delivery_list(
                {"payload": updated_payload, "fileName": "Delivery List 08-14-2026.xlsx", "user": "admin"}
            )
            self.assertFalse(restored["newDeliveryList"])
            self.assertEqual(restored["createdCount"], 0)
            self.assertEqual(restored["reactivatedCount"], 3)

            with store.connect() as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()


if __name__ == "__main__":
    unittest.main()
