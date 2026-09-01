# File: tests/test_import_consistency.py
"""Regression coverage for delivery-list stage routing and import quantities."""

from __future__ import annotations

import unittest
import shutil
from dataclasses import replace
from pathlib import Path

from backend.config import load_config
from backend.store import SQLiteDeliveryStore, canonical_clear_glass_label, glass_cost_profile, glass_profile_identity_key, rack_barcode_text
from backend.production_files import ProductionFileService


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

    def test_stage_preset_queries_follow_renamed_inbound_and_outbound_labels(self) -> None:
        verification_root = ROOT / "_verification_stage_aliases"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            payload = {
                "deliveryDate": "2026-08-18",
                "items": [imported_item("240111", "1", 2, "alias:1")],
            }
            store.import_delivery_list({"payload": payload, "fileName": "Delivery List 08-18-2026.xlsx", "user": "admin"})
            with store.connect() as connection:
                connection.execute(
                    "UPDATE delivery_lists SET stage = 'Outbound' WHERE id = ?",
                    ("2026-08-18-outbound-airport",),
                )
                connection.execute(
                    "UPDATE delivery_lists SET stage = 'Inbound' WHERE id = ?",
                    ("2026-08-18-inbound-indian-trail",),
                )
                connection.commit()

                inbound_list = store.active_indian_trail_list(connection, "2026-08-18")
                self.assertIsNotNone(inbound_list)
                self.assertEqual(inbound_list["stage"], "Inbound")

                rows = store.find_manual_bay_line_items(connection, "T200240111001000")
                self.assertTrue(rows)
                self.assertIn(
                    "2026-08-18-inbound-indian-trail",
                    {row["list_id"] for row in rows},
                )
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_renamed_stage_presets_restore_full_outbound_to_indian_trail_bay_flow(self) -> None:
        """Stage display/scanner renames must not change physical workflow behavior."""
        verification_root = ROOT / "_verification_inbound_restore"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()

            # Deliberately avoid every legacy workflow word. If any path still
            # depends on "Staging", "Outbound", "Inbound", or "Indian Trail",
            # this test will fail instead of accidentally passing by text match.
            for value, label, preset, scanner in (
                ("staging-airport", "Load Prep", "airport_staging", "Prep Floor"),
                ("outbound-airport", "Shipping", "airport_outbound", "Shipping Dock"),
                ("inbound-indian-trail", "Receiving", "indian_trail", "Receiving Dock"),
            ):
                store.add_manual_edit_lookup(
                    {
                        "type": "stage_definition",
                        "value": value,
                        "label": label,
                        "preset": preset,
                        "scanner": scanner,
                    },
                    "admin",
                )

            payload = {
                "deliveryDate": "2026-09-10",
                "items": [imported_item("240777", "1", 1, "preset-restore:1")],
            }
            created = store.import_delivery_list(
                {"payload": payload, "fileName": "Delivery List 09-10-2026.xlsx", "user": "admin"}
            )
            stage_meta = {row["id"]: row for row in created["lists"] if row["deliveryDate"] == "2026-09-10"}
            self.assertEqual(stage_meta["2026-09-10-staging-airport"]["stage"], "Load Prep")
            self.assertEqual(stage_meta["2026-09-10-staging-airport"]["stagePreset"], "airport_staging")
            self.assertEqual(stage_meta["2026-09-10-outbound-airport"]["stage"], "Shipping")
            self.assertEqual(stage_meta["2026-09-10-outbound-airport"]["stagePreset"], "airport_outbound")
            self.assertEqual(stage_meta["2026-09-10-inbound-indian-trail"]["stage"], "Receiving")
            self.assertEqual(stage_meta["2026-09-10-inbound-indian-trail"]["stagePreset"], "indian_trail")

            barcode = str(payload["items"][0]["barcode"])

            # Receiving before Outbound must still hit the dedicated Indian Trail
            # prerequisite gate and ask for the maintained supervisor override.
            blocked_receive = store.receive_indian_trail_scan(
                {
                    "listId": "2026-09-10-inbound-indian-trail",
                    "barcode": barcode,
                    "station": "Receiving Dock",
                },
                "admin",
            )
            self.assertFalse(blocked_receive["ok"])
            self.assertTrue(blocked_receive["outboundOverrideRequired"])
            self.assertIn("not been scanned Staging and Outbound", blocked_receive["message"])

            # Outbound before Staging must also keep the original Staging/rack gate.
            blocked_outbound = store.record_scan(
                {
                    "listId": "2026-09-10-outbound-airport",
                    "barcode": barcode,
                    "user": "admin",
                    "station": "Shipping Dock",
                }
            )
            self.assertTrue(blocked_outbound["outboundOverrideRequired"])
            self.assertTrue(blocked_outbound["outboundNeedsStaging"])
            self.assertTrue(blocked_outbound["outboundNeedsTransportation"])

            with store.connect() as connection:
                rack = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(rack)
            rack_code = str(rack["rack_code"])

            staged = store.record_scan(
                {
                    "listId": "2026-09-10-staging-airport",
                    "barcode": barcode,
                    "rackCode": rack_code,
                    "user": "admin",
                    "station": "Prep Floor",
                }
            )
            staged_item = staged["items"][0]
            self.assertEqual(staged_item["scanned"], 1)
            self.assertEqual(staged_item["rackCode"], rack_code)

            outbound = store.record_scan(
                {
                    "listId": "2026-09-10-outbound-airport",
                    "barcode": barcode,
                    "user": "admin",
                    "station": "Shipping Dock",
                }
            )
            self.assertEqual(outbound["items"][0]["scanned"], 1)

            # Outbound must reserve a real bay on the renamed receiving stage.
            inbound_before = store.get_delivery_list("2026-09-10-inbound-indian-trail")
            self.assertEqual(inbound_before["meta"]["stagePreset"], "indian_trail")
            preassigned = inbound_before["items"][0]
            self.assertTrue(preassigned["bayCode"])
            self.assertEqual(preassigned["bayStatus"], "PreAssigned")
            self.assertEqual(preassigned["rackCode"], rack_code)
            reserved_bay = preassigned["bayCode"]

            received = store.receive_indian_trail_scan(
                {
                    "listId": "2026-09-10-inbound-indian-trail",
                    "barcode": barcode,
                    "station": "Receiving Dock",
                },
                "admin",
            )
            self.assertTrue(received["ok"])

            # Physical receipt owns Location after the scan: Bay is current,
            # transport Rack remains only as history for traceability.
            inbound_after = store.get_delivery_list("2026-09-10-inbound-indian-trail")
            received_item = inbound_after["items"][0]
            self.assertEqual(received_item["scanned"], 1)
            self.assertEqual(received_item["bayCode"], reserved_bay)
            self.assertEqual(received_item["bayStatus"], "Received")
            self.assertEqual(received_item["rackCode"], "")
            self.assertEqual(received_item["lastRackCode"], rack_code)

            with store.connect() as connection:
                assignment = connection.execute(
                    """
                    SELECT ba.status, b.bay_code
                    FROM bay_assignments ba
                    JOIN bays b ON b.id = ba.bay_id
                    WHERE ba.line_item_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
                    ORDER BY ba.id DESC LIMIT 1
                    """,
                    (received_item["id"],),
                ).fetchone()
            self.assertIsNotNone(assignment)
            self.assertEqual(assignment["status"], "Received")
            self.assertEqual(assignment["bay_code"], reserved_bay)
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_all_six_stage_presets_remain_functional_after_custom_names(self) -> None:
        verification_root = ROOT / "_verification_all_stage_presets"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()

            definitions = (
                ("staging-airport", "Load Prep", "airport_staging", "Prep Floor", ""),
                ("outbound-airport", "Shipping", "airport_outbound", "Shipping Dock", ""),
                ("inbound-indian-trail", "Receiving", "indian_trail", "Receiving Dock", ""),
                ("bfs-greenville", "Branch Hub", "greenville", "Branch Dock", "GNV"),
                ("customer-pickup", "Pickup Counter", "cpu", "Pickup Desk", "CPU"),
                ("dtc", "Direct Delivery", "dtc", "Direct Dock", "DTC"),
            )
            for value, label, preset, scanner, route_code in definitions:
                store.add_manual_edit_lookup(
                    {
                        "type": "stage_definition",
                        "value": value,
                        "label": label,
                        "preset": preset,
                        "scanner": scanner,
                        "routeCode": route_code,
                    },
                    "admin",
                )

            items = []
            for index, route in enumerate(("IT", "GNV", "CPU", "DTC"), start=1):
                item = imported_item(f"25100{index}", "1", 1, f"all-stage:{index}")
                item["route"] = route
                item["sourceRoute"] = route
                item["job"] = f"CUSTOM {route} WORK"
                item["barcode"] = f"T20025100{index}001000"
                items.append(item)

            created = store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-09-11", "items": items},
                    "fileName": "Delivery List 09-11-2026.xlsx",
                    "user": "admin",
                }
            )
            by_id = {row["id"]: row for row in created["lists"]}
            expected = {
                "2026-09-11-staging-airport": ("Load Prep", "airport_staging"),
                "2026-09-11-outbound-airport": ("Shipping", "airport_outbound"),
                "2026-09-11-inbound-indian-trail": ("Receiving", "indian_trail"),
                "2026-09-11-bfs-greenville": ("Branch Hub", "greenville"),
                "2026-09-11-customer-pickup": ("Pickup Counter", "cpu"),
                "2026-09-11-dtc": ("Direct Delivery", "dtc"),
            }
            self.assertEqual(set(by_id), set(expected))
            for list_id, (display_name, preset) in expected.items():
                self.assertEqual(by_id[list_id]["stage"], display_name)
                self.assertEqual(by_id[list_id]["stagePreset"], preset)

            # Destination stages use the generic scanner path. Confirm each one
            # remains fully scan-capable when its display/scanner labels contain
            # none of the legacy CPU/GNV/DTC wording.
            for list_id, item_index, station, preset in (
                ("2026-09-11-bfs-greenville", 2, "Branch Dock", "greenville"),
                ("2026-09-11-customer-pickup", 3, "Pickup Desk", "cpu"),
                ("2026-09-11-dtc", 4, "Direct Dock", "dtc"),
            ):
                result = store.record_scan(
                    {
                        "listId": list_id,
                        "barcode": f"T20025100{item_index}001000",
                        "user": "admin",
                        "station": station,
                    }
                )
                self.assertEqual(result["meta"]["stagePreset"], preset)
                self.assertEqual(result["items"][0]["scanned"], 1)
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_inbound_override_recommends_existing_same_order_bay(self) -> None:
        verification_root = ROOT / "_verification_same_order_bay"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()

            first = imported_item("252001", "1", 1, "same-order:1")
            second = imported_item("252001", "2", 1, "same-order:2")
            first["barcode"] = "T200252001001000"
            second["barcode"] = "T200252001002000"
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-09-12", "items": [first, second]},
                    "fileName": "Delivery List 09-12-2026.xlsx",
                    "user": "admin",
                }
            )
            with store.connect() as connection:
                rack = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(rack)
            rack_code = str(rack["rack_code"])

            # Fully move item 1 into its bay so item 2 has a same-order physical
            # location to reuse when an Outbound prerequisite is overridden.
            store.record_scan(
                {"listId": "2026-09-12-staging-airport", "barcode": first["barcode"], "rackCode": rack_code, "user": "admin", "station": "Airport Rd"}
            )
            store.record_scan(
                {"listId": "2026-09-12-outbound-airport", "barcode": first["barcode"], "user": "admin", "station": "Airport Rd"}
            )
            received_first = store.receive_indian_trail_scan(
                {"listId": "2026-09-12-inbound-indian-trail", "barcode": first["barcode"], "station": "Indian Trail"},
                "admin",
            )
            self.assertTrue(received_first["ok"])
            first_bay = str(received_first["bayCode"])
            self.assertTrue(first_bay)

            blocked_second = store.receive_indian_trail_scan(
                {"listId": "2026-09-12-inbound-indian-trail", "barcode": second["barcode"], "station": "Indian Trail"},
                "admin",
            )
            self.assertFalse(blocked_second["ok"])
            self.assertTrue(blocked_second["outboundOverrideRequired"])
            self.assertEqual(blocked_second["existingOrderBayCode"], first_bay)
            self.assertEqual(blocked_second["preassignedBayCode"], first_bay)


            overridden_second = store.receive_indian_trail_scan(
                {
                    "listId": "2026-09-12-inbound-indian-trail",
                    "barcode": second["barcode"],
                    "station": "Indian Trail",
                    "outboundOverride": True,
                    "bayCode": first_bay,
                },
                "admin",
            )
            self.assertTrue(overridden_second["ok"])
            inbound_after_override = store.get_delivery_list("2026-09-12-inbound-indian-trail")
            second_after = next(item for item in inbound_after_override["items"] if item["item"] == "002")
            self.assertTrue(second_after["inboundOverrideUsed"])
            self.assertEqual(second_after["inboundOverrideLabel"], "OUTBOUND OVERRIDE")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_v0449_indian_trail_override_backfills_prerequisites_clears_rack_and_keeps_received_bay(self) -> None:
        verification_root = ROOT / "_verification_v449_it_override"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()

            item = imported_item("257901", "1", 1, "it-override:1")
            item["barcode"] = "T200257901001000"
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-09-14", "items": [item]},
                    "fileName": "Delivery List 09-14-2026.xlsx",
                    "user": "admin",
                }
            )
            with store.connect() as connection:
                staging = connection.execute(
                    "SELECT id FROM line_items WHERE list_id = ? LIMIT 1",
                    ("2026-09-14-staging-airport",),
                ).fetchone()
                rack = connection.execute(
                    "SELECT id, rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
                self.assertIsNotNone(staging)
                self.assertIsNotNone(rack)
                connection.execute(
                    """
                    INSERT INTO rack_items (rack_id, line_item_id, qty, status, added_by, added_at, reason, destination_override)
                    VALUES (?, ?, 1, 'Active', 'admin', '2026-09-14T08:00:00+00:00', 'Legacy rack assignment', '')
                    """,
                    (rack["id"], staging["id"]),
                )
                connection.commit()

            blocked = store.receive_indian_trail_scan(
                {"listId": "2026-09-14-inbound-indian-trail", "barcode": item["barcode"], "station": "Indian Trail"},
                "admin",
            )
            self.assertFalse(blocked["ok"])
            self.assertTrue(blocked["outboundOverrideRequired"])

            received = store.receive_indian_trail_scan(
                {
                    "listId": "2026-09-14-inbound-indian-trail",
                    "barcode": item["barcode"],
                    "station": "Indian Trail",
                    "outboundOverride": True,
                },
                "admin",
            )
            self.assertTrue(received["ok"])
            self.assertEqual(received["prerequisiteReconciliation"]["stagingQtyAdded"], 1)
            self.assertEqual(received["prerequisiteReconciliation"]["outboundQtyAdded"], 1)
            self.assertIn(str(rack["rack_code"]), received["clearedRackCodes"])
            self.assertTrue(received["bayCode"])

            with store.connect() as connection:
                staging_qty = connection.execute(
                    "SELECT scanned_qty FROM line_items WHERE list_id = ? LIMIT 1",
                    ("2026-09-14-staging-airport",),
                ).fetchone()["scanned_qty"]
                outbound_qty = connection.execute(
                    "SELECT scanned_qty FROM line_items WHERE list_id = ? LIMIT 1",
                    ("2026-09-14-outbound-airport",),
                ).fetchone()["scanned_qty"]
                rack_item = connection.execute(
                    "SELECT status, reason FROM rack_items WHERE rack_id = ? AND line_item_id = ?",
                    (rack["id"], staging["id"]),
                ).fetchone()
                self.assertEqual(staging_qty, 1)
                self.assertEqual(outbound_qty, 1)
                self.assertEqual(rack_item["status"], "Removed")
                self.assertEqual(rack_item["reason"], "Overridden by IT")

            inbound = store.get_delivery_list("2026-09-14-inbound-indian-trail")
            inbound_item = inbound["items"][0]
            self.assertEqual(inbound_item["bayCode"], received["bayCode"])
            self.assertEqual(inbound_item["bayStatus"], "Received")
            self.assertTrue(inbound_item["bayAssignmentId"])
            self.assertEqual(inbound_item["lastRackRemovalReason"], "Overridden by IT")
            self.assertEqual(inbound_item["inboundOverrideLabel"], "OUTBOUND OVERRIDE")

            staging_payload = store.get_delivery_list("2026-09-14-staging-airport")
            staging_item = staging_payload["items"][0]
            self.assertEqual(staging_item["scanned"], 1)
            self.assertEqual(staging_item["lastRackRemovalReason"], "Overridden by IT")

            bays = store.get_bays()
            alternate = next(
                bay for bay in bays
                if str(bay.get("bayCode") or "") != received["bayCode"]
                and str(bay.get("status") or "").lower() == "empty"
            )
            moved = store.move_bay_assignment(
                {
                    "assignmentId": inbound_item["bayAssignmentId"],
                    "newBayCode": alternate["bayCode"],
                    "reason": "Changed from Inbound Scan page",
                },
                "admin",
            )
            self.assertTrue(moved["ok"])
            self.assertEqual(moved["status"], "Received")
            refreshed = store.get_delivery_list("2026-09-14-inbound-indian-trail")
            self.assertEqual(refreshed["items"][0]["bayCode"], alternate["bayCode"])
            self.assertEqual(refreshed["items"][0]["bayStatus"], "Received")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_v0448_piece_level_timing_uses_active_delivery_date(self) -> None:
        verification_root = ROOT / "_verification_v448_timing"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            item = imported_item("258001", "1", 2, "timing:1")
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-09-15", "items": [item]},
                    "fileName": "Delivery List 09-15-2026.xlsx",
                    "user": "admin",
                }
            )
            list_id = "2026-09-15-outbound-airport"
            with store.connect() as connection:
                line = connection.execute(
                    "SELECT id, barcode FROM line_items WHERE list_id = ? LIMIT 1",
                    (list_id,),
                ).fetchone()
                self.assertIsNotNone(line)
                connection.execute("UPDATE line_items SET scanned_qty = 2 WHERE id = ?", (line["id"],))
                for message, created_at in (
                    ("On-time piece", "2026-09-15T10:00:00+00:00"),
                    ("Late piece", "2026-09-16T10:00:00+00:00"),
                ):
                    connection.execute(
                        """
                        INSERT INTO scan_events (
                            list_id, line_item_id, barcode, canonical_barcode, user_name,
                            station, event_type, message, reason, qty_delta, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            list_id, line["id"], line["barcode"], line["barcode"], "admin",
                            "Airport Rd", "scan", message, "", 1, created_at,
                        ),
                    )
                connection.commit()
                metrics = store.list_timing_metrics(connection, list_id, "2026-09-15")
                self.assertEqual(metrics["onTimeQty"], 1)
                self.assertEqual(metrics["lateQty"], 1)
                self.assertEqual(metrics["timedQty"], 2)
                self.assertEqual(metrics["onTimePercent"], 50)

                connection.execute(
                    "UPDATE line_items SET priority_delivery_date = ? WHERE id = ?",
                    ("2026-09-16", line["id"]),
                )
                connection.commit()
                moved_metrics = store.list_timing_metrics(connection, list_id, "2026-09-15")
                self.assertEqual(moved_metrics["onTimeQty"], 2)
                self.assertEqual(moved_metrics["lateQty"], 0)
                self.assertEqual(moved_metrics["onTimePercent"], 100)
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_v0448_received_bay_survives_cross_stage_refresh(self) -> None:
        verification_root = ROOT / "_verification_v448_bay_refresh"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()
            item = imported_item("258101", "1", 1, "bay-refresh:1")
            item["barcode"] = "T200258101001000"
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-09-18", "items": [item]},
                    "fileName": "Delivery List 09-18-2026.xlsx",
                    "user": "admin",
                }
            )
            with store.connect() as connection:
                rack = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(rack)
            rack_code = str(rack["rack_code"])
            store.record_scan(
                {"listId": "2026-09-18-staging-airport", "barcode": item["barcode"], "rackCode": rack_code, "user": "admin", "station": "Airport Rd"}
            )
            store.record_scan(
                {"listId": "2026-09-18-outbound-airport", "barcode": item["barcode"], "user": "admin", "station": "Airport Rd"}
            )
            received = store.receive_indian_trail_scan(
                {"listId": "2026-09-18-inbound-indian-trail", "barcode": item["barcode"], "station": "Indian Trail"},
                "admin",
            )
            self.assertTrue(received["ok"])
            bay_code = str(received["bayCode"])
            self.assertTrue(bay_code)

            # Simulate a legacy/stale assignment still attached to the sibling
            # Outbound copy. Fresh Inbound reads must resolve the physical Bay by
            # Order/Item identity instead of falling back to the rack.
            with store.connect() as connection:
                inbound_line = connection.execute(
                    "SELECT id FROM line_items WHERE list_id = ? LIMIT 1",
                    ("2026-09-18-inbound-indian-trail",),
                ).fetchone()
                outbound_line = connection.execute(
                    "SELECT id FROM line_items WHERE list_id = ? LIMIT 1",
                    ("2026-09-18-outbound-airport",),
                ).fetchone()
                self.assertIsNotNone(inbound_line)
                self.assertIsNotNone(outbound_line)
                connection.execute(
                    "UPDATE bay_assignments SET line_item_id = ? WHERE line_item_id = ? AND status = 'Received'",
                    (outbound_line["id"], inbound_line["id"]),
                )
                connection.commit()

            refreshed = store.get_delivery_list("2026-09-18-inbound-indian-trail")
            refreshed_item = refreshed["items"][0]
            self.assertEqual(refreshed_item["bayCode"], bay_code)
            self.assertEqual(refreshed_item["bayStatus"], "Received")
            self.assertTrue(refreshed_item["received"])
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

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


    def test_v0450_twenty_piece_rack_inbound_bay_and_manual_scan_lifecycle(self) -> None:
        """Exercise the floor's full 20-piece rack path, including Manual Scan branches."""
        verification_root = ROOT / "_verification_v0450_twenty_piece"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()
                rack = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(rack)
            rack_code = str(rack["rack_code"])
            delivery_date = "2026-09-21"

            # v0.450 regression: ten two-piece orders produce 20 physical scans while
            # staying within the seeded Standard-bay inventory (siblings share a bay).
            items = []
            for order_index in range(10):
                order = str(261000 + order_index)
                for item_no in ("1", "2"):
                    items.append(imported_item(order, item_no, 1, f"v0450:{order}:{item_no}"))
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": delivery_date, "items": items},
                    "fileName": "Delivery List 09-21-2026.xlsx",
                    "user": "admin",
                }
            )

            staging_id = f"{delivery_date}-staging-airport"
            outbound_id = f"{delivery_date}-outbound-airport"
            inbound_id = f"{delivery_date}-inbound-indian-trail"

            # Load all 20 pieces into one rack. Every fifth item uses the same exact
            # order/item text accepted by the browser's Manual Scan path.
            for index, item in enumerate(items, start=1):
                order_item = f"{item['order']}{item['item']}"
                result = store.record_scan(
                    {
                        "listId": staging_id,
                        "barcode": order_item if index % 5 == 0 else item["barcode"],
                        "rackCode": rack_code,
                        "isManual": index % 5 == 0,
                        "user": "admin",
                        "station": "Airport Rd",
                    }
                )
                self.assertEqual(result["items"][index - 1]["scanned"], 1)

            with store.connect() as connection:
                active_rack_qty = connection.execute(
                    "SELECT COALESCE(SUM(qty), 0) FROM rack_items WHERE rack_id = (SELECT id FROM racks WHERE rack_code = ?) AND status = 'Active'",
                    (rack_code,),
                ).fetchone()[0]
            self.assertEqual(active_rack_qty, 20)

            # Scan the physical rack Outbound once. It must advance every rack row
            # and reserve one receiving bay per order before the truck reaches IT.
            outbound = store.record_scan(
                {
                    "listId": outbound_id,
                    "barcode": rack_barcode_text(rack_code, delivery_date),
                    "user": "admin",
                    "station": "Airport Rd",
                }
            )
            self.assertEqual(outbound["outboundScannedQty"], 20)
            inbound_before = store.get_delivery_list(inbound_id)
            self.assertEqual(len(inbound_before["items"]), 20)
            preassigned = {row["sourceId"]: row["bayCode"] for row in inbound_before["items"]}
            self.assertTrue(all(preassigned.values()))
            self.assertTrue(all(row["bayStatus"] == "PreAssigned" for row in inbound_before["items"]))
            order_bays = {}
            for row in inbound_before["items"]:
                order_bays.setdefault(row["order"], set()).add(row["bayCode"])
            self.assertEqual(len(order_bays), 10)
            self.assertTrue(all(len(bays) == 1 for bays in order_bays.values()))

            # Receive each piece one at a time. Rack ownership must clear one piece
            # at a time while the preassigned bay becomes the physical Received bay.
            for index, item in enumerate(items, start=1):
                order_item = f"{item['order']}{item['item']}"
                received = store.receive_indian_trail_scan(
                    {
                        "listId": inbound_id,
                        "barcode": order_item if index % 4 == 0 else item["barcode"],
                        "isManual": index % 4 == 0,
                        "station": "Indian Trail",
                    },
                    "admin",
                )
                self.assertTrue(received["ok"])
                self.assertEqual(received["bayCode"], preassigned[f"{item['order']}-{str(item['item']).zfill(3)}"])
                with store.connect() as connection:
                    remaining = connection.execute(
                        "SELECT COALESCE(SUM(qty), 0) FROM rack_items WHERE rack_id = (SELECT id FROM racks WHERE rack_code = ?) AND status = 'Active'",
                        (rack_code,),
                    ).fetchone()[0]
                self.assertEqual(remaining, 20 - index)

            inbound_received = store.get_delivery_list(inbound_id)
            self.assertTrue(all(row["scanned"] == 1 for row in inbound_received["items"]))
            self.assertTrue(all(row["bayStatus"] == "Received" for row in inbound_received["items"]))
            self.assertTrue(all(row["rackCode"] == "" for row in inbound_received["items"]))
            self.assertTrue(all(row["lastRackCode"] == rack_code for row in inbound_received["items"]))

            # Bay Map scan-out clears each physical assignment. Manual scan-out is
            # exercised too, and the Inbound payload must retain the former bay as history.
            for index, item in enumerate(items, start=1):
                order_item = f"{item['order']}{item['item']}"
                cleared = store.scan_out_bay_item(
                    {
                        "barcode": order_item if index % 6 == 0 else item["barcode"],
                        "isManual": index % 6 == 0,
                        "station": "Bay Map",
                    },
                    "admin",
                )
                self.assertTrue(cleared["ok"])
                self.assertEqual(cleared["bayCode"], preassigned[f"{item['order']}-{str(item['item']).zfill(3)}"])

            with store.connect() as connection:
                active_assignments = connection.execute(
                    "SELECT COUNT(*) FROM bay_assignments WHERE status NOT IN ('Cleared', 'Cancelled')"
                ).fetchone()[0]
            self.assertEqual(active_assignments, 0)

            inbound_cleared = store.get_delivery_list(inbound_id)
            for row in inbound_cleared["items"]:
                self.assertEqual(row["bayCode"], "")
                self.assertEqual(row["lastBayCode"], preassigned[row["sourceId"]])
                self.assertEqual(row["lastBayAssignmentStatus"], "Cleared")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_v0450_rush_remake_missing_glass_search_and_bay_lifecycle(self) -> None:
        """Verify each maintained priority intake path reaches and leaves a receiving bay."""
        verification_root = ROOT / "_verification_v0450_priority_lifecycle"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()
                rack = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(rack)
            rack_code = str(rack["rack_code"])
            delivery_date = "2026-09-22"

            rush = imported_item("262001", "1", 1, "v0450-priority:rush")
            remake = imported_item("262002", "1", 1, "v0450-priority:remake")
            remake["job"] = "88262002.2R TEST JOB"
            missing = imported_item("262003", "1", 1, "v0450-priority:missing")

            store.create_priority_intake_request(
                {
                    "priorityType": "Rush",
                    "jobNumber": rush["job"],
                    "reason": "Priority customer request",
                    "responsible": "Test Operator",
                    "emailMode": "none",
                },
                "admin",
            )
            store.create_priority_intake_request(
                {
                    "priorityType": "Remake",
                    "jobNumber": "88262002",
                    "reason": "Replacement glass required",
                    "responsible": "Test Operator",
                    "emailMode": "none",
                },
                "admin",
            )
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": delivery_date, "items": [rush, remake, missing]},
                    "fileName": "Delivery List 09-22-2026.xlsx",
                    "user": "admin",
                }
            )

            inbound_id = f"{delivery_date}-inbound-indian-trail"
            inbound = store.get_delivery_list(inbound_id)
            missing_row = next(row for row in inbound["items"] if row["order"] == missing["order"])
            marked = store.mark_sdi(
                {
                    "lineItemIds": [missing_row["id"]],
                    "orderType": "Rush",
                    "reason": "Missing lite replacement",
                    "responsible": "Test Operator",
                    "emailMode": "none",
                },
                "admin",
            )
            self.assertTrue(marked["ok"])

            # v0.469 keeps historical existing-order Rush marks searchable but
            # no longer exposes Missing Glass Rush as a standalone flag type.
            expected_kinds = {
                rush["order"]: "rush",
                remake["order"]: "remake",
                missing["order"]: "rush",
            }
            for order, expected_kind in expected_kinds.items():
                results = store.global_search(order)
                match = next(result for result in results if result["order"] == order)
                self.assertEqual(match["priorityBanner"]["kind"], expected_kind)

            staging_id = f"{delivery_date}-staging-airport"
            outbound_id = f"{delivery_date}-outbound-airport"
            for item in (rush, remake, missing):
                staged = store.record_scan(
                    {
                        "listId": staging_id,
                        "barcode": item["barcode"],
                        "rackCode": rack_code,
                        "user": "admin",
                        "station": "Airport Rd",
                    }
                )
                self.assertEqual(next(row for row in staged["items"] if row["order"] == item["order"])["scanned"], 1)

            outbound = store.record_scan(
                {
                    "listId": outbound_id,
                    "barcode": rack_barcode_text(rack_code, delivery_date),
                    "user": "admin",
                    "station": "Airport Rd",
                }
            )
            self.assertEqual(outbound["outboundScannedQty"], 3)

            before_receive = store.get_delivery_list(inbound_id)
            bay_by_order = {row["order"]: row["bayCode"] for row in before_receive["items"]}
            self.assertTrue(all(bay_by_order.values()))
            for item in (rush, remake, missing):
                received = store.receive_indian_trail_scan(
                    {"listId": inbound_id, "barcode": item["barcode"], "station": "Indian Trail"},
                    "admin",
                )
                self.assertTrue(received["ok"])
                self.assertEqual(received["bayCode"], bay_by_order[item["order"]])

            physically_received = store.get_delivery_list(inbound_id)
            self.assertTrue(all(row["bayStatus"] == "Received" for row in physically_received["items"]))
            for item in (rush, remake, missing):
                cleared = store.scan_out_bay_item(
                    {"barcode": item["barcode"], "station": "Bay Map"},
                    "admin",
                )
                self.assertTrue(cleared["ok"])

            after_clear = store.get_delivery_list(inbound_id)
            self.assertTrue(all(row["bayCode"] == "" for row in after_clear["items"]))
            self.assertTrue(all(row["lastBayCode"] for row in after_clear["items"]))
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()


    def test_v0451_global_search_combines_dimensions_flags_and_priority_metadata(self) -> None:
        """Smart Search should AND arbitrary order metadata with maintained priority flags."""
        verification_root = ROOT / "_verification_v0451_global_search"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            delivery_date = "2026-09-29"

            rush = imported_item("273001", "1", 1, "v0451-search:rush")
            rush["dimensions"] = "73 x 64"
            rush["customer"] = "ALPHA BUILDERS"
            remake = imported_item("273002", "1", 1, "v0451-search:remake")
            remake["dimensions"] = "73 x 64"
            remake["job"] = "88273002.2R TEST JOB"
            missing = imported_item("273003", "1", 1, "v0451-search:missing")
            missing["dimensions"] = "81 x 50"
            normal = imported_item("273004", "1", 1, "v0451-search:normal")
            normal["dimensions"] = "73 x 64"

            store.create_priority_intake_request(
                {
                    "priorityType": "Rush",
                    "jobNumber": rush["job"],
                    "reason": "Hot replacement",
                    "responsible": "Search Tester",
                    "emailMode": "none",
                },
                "admin",
            )
            store.create_priority_intake_request(
                {
                    "priorityType": "Remake",
                    "jobNumber": "88273002",
                    "reason": "Remake verification",
                    "responsible": "Search Tester",
                    "emailMode": "none",
                },
                "admin",
            )
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": delivery_date, "items": [rush, remake, missing, normal]},
                    "fileName": "Delivery List 09-29-2026.xlsx",
                    "user": "admin",
                }
            )

            inbound = store.get_delivery_list(f"{delivery_date}-inbound-indian-trail")
            missing_row = next(row for row in inbound["items"] if row["order"] == missing["order"])
            marked = store.mark_sdi(
                {
                    "lineItemIds": [missing_row["id"]],
                    "orderType": "Rush",
                    "reason": "Broke at Barefoot",
                    "responsible": "Search Tester",
                    "emailMode": "none",
                },
                "admin",
            )
            self.assertTrue(marked["ok"])

            rush_results = store.global_search("rush")
            rush_kinds = {row["order"]: row.get("priorityBanner", {}).get("kind") for row in rush_results}
            self.assertEqual(rush_kinds.get(rush["order"]), "rush")
            self.assertEqual(rush_kinds.get(missing["order"]), "rush")

            remake_results = store.global_search("remake")
            self.assertEqual(next(row for row in remake_results if row["order"] == remake["order"])["priorityBanner"]["kind"], "remake")
            reason_results = store.global_search("broke barefoot rush")
            self.assertEqual([row["order"] for row in reason_results], [missing["order"]])

            # The central v0.451 behavior: all terms must belong to the same order.
            combined = store.global_search("73 x 64 rush")
            self.assertEqual([row["order"] for row in combined], [rush["order"]])
            compact_dimensions = store.global_search("73x64 remake")
            self.assertEqual([row["order"] for row in compact_dimensions], [remake["order"]])
            self.assertEqual([row["order"] for row in store.global_search("alpha rush")], [rush["order"]])

            # Priority reason/responsible metadata is part of the same search corpus.
            self.assertEqual([row["order"] for row in store.global_search("hot replacement")], [rush["order"]])
            responsible_results = store.global_search("search tester broke")
            self.assertEqual([row["order"] for row in responsible_results], [missing["order"]])
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()


    def test_v0452_combined_glass_metadata_and_it_override_scan_history(self) -> None:
        verification_root = ROOT / "_verification_v0452_alias_override"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_bays(connection)
                store.seed_bay_auto_assign_settings(connection)
                store.seed_racks(connection)
                connection.commit()

            # Preserve each source profile's stored color for reversible uncombine,
            # while exposing one explicit alias target for the browser's v0.452
            # effective-color resolver.
            store.upsert_glass_profile(
                {"value": "French Antique", "label": "French Antique", "color": "#2FA84F"},
                "admin",
            )
            store.upsert_glass_profile(
                {"value": "1/4 French Antique Mirror", "label": "1/4 French Antique Mirror", "color": "#173B65"},
                "admin",
            )
            combined = store.combine_glass_profiles(
                {"target": "1/4 French Antique Mirror", "values": ["French Antique"]},
                "admin",
            )
            alias = next(row for row in combined["glassAliases"] if row["value"] == "French Antique")
            self.assertEqual(alias["label"], "1/4 French Antique Mirror")
            colors = {row["value"]: row.get("color") for row in combined["glassColors"]}
            self.assertEqual(colors["French Antique"], "#2FA84F")
            self.assertEqual(colors["1/4 French Antique Mirror"], "#173B65")

            item = imported_item("274001", "1", 1, "v0452-it-override:1")
            item["barcode"] = "T200274001001000"
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-09-30", "items": [item]},
                    "fileName": "Delivery List 09-30-2026.xlsx",
                    "user": "admin",
                }
            )

            blocked = store.receive_indian_trail_scan(
                {"listId": "2026-09-30-inbound-indian-trail", "barcode": item["barcode"], "station": "Indian Trail"},
                "admin",
            )
            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["missingPrerequisites"], ["staging", "outbound"])

            received = store.receive_indian_trail_scan(
                {
                    "listId": "2026-09-30-inbound-indian-trail",
                    "barcode": item["barcode"],
                    "station": "Indian Trail",
                    "outboundOverride": True,
                },
                "admin",
            )
            self.assertTrue(received["ok"])
            self.assertEqual(received["prerequisiteReconciliation"]["stagingQtyAdded"], 1)
            self.assertEqual(received["prerequisiteReconciliation"]["outboundQtyAdded"], 1)

            staging = store.get_delivery_list("2026-09-30-staging-airport")["items"][0]
            outbound = store.get_delivery_list("2026-09-30-outbound-airport")["items"][0]
            self.assertEqual(staging["scanned"], 1)
            self.assertEqual(outbound["scanned"], 1)
            self.assertEqual(staging["lastScannedStation"], "Scan Override IT")
            self.assertEqual(outbound["lastScannedStation"], "Scan Override IT")

            with store.connect() as connection:
                override_events = connection.execute(
                    """
                    SELECT list_id, event_type, station, qty_delta
                    FROM scan_events
                    WHERE event_type = 'scan_override_it'
                    ORDER BY id
                    """
                ).fetchall()
                self.assertEqual(len(override_events), 2)
                self.assertEqual({row["station"] for row in override_events}, {"Scan Override IT"})
                self.assertEqual({row["qty_delta"] for row in override_events}, {1})
                staging_metrics = store.list_timing_metrics(connection, "2026-09-30-staging-airport", "2026-09-30")
                outbound_metrics = store.list_timing_metrics(connection, "2026-09-30-outbound-airport", "2026-09-30")
                self.assertEqual(staging_metrics["timedQty"], 0)
                self.assertEqual(outbound_metrics["timedQty"], 0)

            # A partially inconsistent legacy case (Outbound present, Staging absent)
            # is also caught instead of silently receiving with mismatched stages.
            second = imported_item("274002", "1", 1, "v0452-it-override:2")
            second["barcode"] = "T200274002001000"
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-10-01", "items": [second]},
                    "fileName": "Delivery List 10-01-2026.xlsx",
                    "user": "admin",
                }
            )
            with store.connect() as connection:
                connection.execute(
                    "UPDATE line_items SET scanned_qty = 1 WHERE list_id = ?",
                    ("2026-10-01-outbound-airport",),
                )
                connection.commit()
            mismatch = store.receive_indian_trail_scan(
                {"listId": "2026-10-01-inbound-indian-trail", "barcode": second["barcode"], "station": "Indian Trail"},
                "admin",
            )
            self.assertFalse(mismatch["ok"])
            self.assertEqual(mismatch["missingPrerequisites"], ["staging"])
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_v0460_clear_glass_requires_explicit_heat_treatment_in_statistics(self) -> None:
        self.assertEqual(canonical_clear_glass_label("3/8 Clear"), "3/8 Clear Annealed")
        self.assertEqual(canonical_clear_glass_label("3/8 Clear Annealed"), "3/8 Clear Annealed")
        self.assertEqual(canonical_clear_glass_label("3/8 Clear Tempered"), "3/8 Clear Tempered")
        self.assertEqual(canonical_clear_glass_label("3/8 UltraClear"), "3/8 UltraClear Annealed")
        self.assertEqual(canonical_clear_glass_label("1/4 French Antique Mirror"), "1/4 French Antique Mirror")
        self.assertEqual(glass_cost_profile("3/8 Clear")[0], "3/8 Clear Annealed")

        verification_root = ROOT / "_verification_v0460_clear_glass"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            annealed = imported_item("275001", "1", 2, "v0460-clear:1")
            annealed["product"] = "3/8 Clear"
            tempered = imported_item("275002", "1", 1, "v0460-clear:2")
            tempered["product"] = "3/8 Clear Tempered"
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-02", "items": [annealed, tempered]},
                "fileName": "Delivery List 10-02-2026.xlsx",
                "user": "admin",
            })

            staging_items = store.get_delivery_list("2026-10-02-staging-airport")["items"]
            by_order = {item["order"]: item for item in staging_items}
            self.assertEqual(by_order["275001"]["product"], "3/8 Clear")
            self.assertEqual(by_order["275001"]["glassType"], "3/8 Clear Annealed")
            self.assertEqual(by_order["275002"]["glassType"], "3/8 Clear Tempered")

            report = store.reports_summary({"dateFrom": "2026-10-02", "dateTo": "2026-10-02"})
            glass_rows = {row["glassType"]: row["qty"] for row in report["glassQuantityByType"]}
            self.assertNotIn("3/8 Clear", glass_rows)
            self.assertEqual(glass_rows.get("3/8 Clear Annealed"), 2)
            self.assertEqual(glass_rows.get("3/8 Clear Tempered"), 1)
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()



    def test_v0461_persisted_glass_aliases_uncombine_after_restart_and_label_normalization(self) -> None:
        self.assertEqual(glass_profile_identity_key("3/8 Clear"), glass_profile_identity_key("3/8 Clear Annealed"))

        verification_root = ROOT / "_verification_v0461_uncombine"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            # Simulate a combination created by an older release before the
            # explicit Annealed wording became the maintained profile identity.
            with store.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO admin_lookup_values
                        (type, value, label, category, match_terms, is_active, source, created_at, updated_at)
                    VALUES ('glass_alias', ?, ?, '', '', 1, 'manual', ?, ?)
                    """,
                    ("3/8 Clear Legacy Name", "3/8 Clear", "2026-08-01T12:00:00Z", "2026-08-01T12:00:00Z"),
                )
                connection.commit()

            before = store.get_manual_edit_lookups()
            self.assertEqual(len(before["glassAliases"]), 1)
            alias = before["glassAliases"][0]
            self.assertEqual(alias["target"], "3/8 Clear")
            self.assertEqual(alias["targetKey"], glass_profile_identity_key("3/8 Clear Annealed"))

            # Recreate the store to prove this does not depend on browser/server
            # session memory. A normalized current target must still separate it.
            restarted = self.make_store(verification_root)
            result = restarted.uncombine_glass_profiles({"targets": ["3/8 Clear Annealed"]}, "admin")
            self.assertEqual(result["glassAliases"], [])
            with restarted.connect() as connection:
                row = connection.execute(
                    "SELECT is_active, source FROM admin_lookup_values WHERE type = 'glass_alias' AND value = ?",
                    ("3/8 Clear Legacy Name",),
                ).fetchone()
            self.assertEqual(int(row["is_active"]), 0)
            self.assertEqual(row["source"], "manual-hidden")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()



    def test_v0468_whole_delivery_list_edit_deduplicates_and_updates_shared_fields_only(self) -> None:
        verification_root = ROOT / "_verification_v0468_whole_edit"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            item = imported_item("276001", "1", 2, "v0468-whole:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-05", "items": [item]},
                "fileName": "Delivery List 10-05-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as connection:
                connection.execute(
                    "UPDATE line_items SET scanned_qty = 1 WHERE list_id = ?",
                    ("2026-10-05-staging-airport",),
                )
                connection.commit()
                before_rows = connection.execute(
                    "SELECT id, list_id, scanned_qty FROM line_items WHERE order_no = ? AND item_no = ? ORDER BY list_id",
                    ("276001", "001"),
                ).fetchall()
            self.assertGreaterEqual(len(before_rows), 3)
            before_scanned = {row["id"]: int(row["scanned_qty"] or 0) for row in before_rows}

            whole = store.admin_search_line_items(
                "",
                "",
                20,
                0,
                {"wholeList": True, "deliveryDate": "2026-10-05"},
            )
            self.assertTrue(whole["wholeList"])
            self.assertEqual(whole["total"], 1)
            self.assertEqual(len(whole["results"]), 1)
            logical = whole["results"][0]
            self.assertGreaterEqual(int(logical["stageCopyCount"]), 3)

            result = store.update_line_item(
                {
                    "lineItemId": logical["lineItemId"],
                    "customer": "WHOLE LIST CUSTOMER",
                    "dimensions": '40" x 60"',
                    "qty": 3,
                    # Whole-list mode must ignore physical stage-owned values.
                    "scanned": 0,
                    "location": "",
                    "editScope": "whole",
                },
                "admin",
            )
            self.assertGreaterEqual(int(result["stageRecordCount"]), 3)
            with store.connect() as connection:
                after_rows = connection.execute(
                    "SELECT id, customer, dimensions, qty, scanned_qty FROM line_items WHERE order_no = ? AND item_no = ? ORDER BY list_id",
                    ("276001", "001"),
                ).fetchall()
            self.assertEqual({row["customer"] for row in after_rows}, {"WHOLE LIST CUSTOMER"})
            self.assertEqual({row["dimensions"] for row in after_rows}, {'40" x 60"'})
            self.assertEqual({int(row["qty"] or 0) for row in after_rows}, {3})
            self.assertEqual({row["id"]: int(row["scanned_qty"] or 0) for row in after_rows}, before_scanned)
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                shutil.rmtree(verification_root)



    def test_v0470_production_fabrication_is_item_specific_and_blocks_staging_until_complete(self) -> None:
        """Denver/Waterjet evidence must match the exact item before Staging can proceed."""
        verification_root = ROOT / "_verification_v0470_fabrication"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        database_path = verification_root / "scanner.db"
        hardware_dir = verification_root / "Hardware Lists"
        sketches_dir = verification_root / "Sketches"
        programs_dir = verification_root / "Programs"
        completed_wj_dir = verification_root / "Completed WJ"
        for folder in (hardware_dir, sketches_dir, programs_dir, completed_wj_dir):
            folder.mkdir()
        try:
            store = self.make_store(verification_root)
            with store.connect() as connection:
                store.seed_racks(connection)
                connection.commit()

            config = replace(
                store.config,
                hardware_lists_dir=hardware_dir,
                sketches_dir=sketches_dir,
                programs_dir=programs_dir,
                completed_wj_dir=completed_wj_dir,
            )
            store.production_files = ProductionFileService(config)

            item = imported_item("279470", "1", 1, "v0470-fabrication:1")
            item["job"] = "88279470 FAB TEST"
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-19", "items": [item]},
                "fileName": "Delivery List 10-19-2026.xlsx",
                "user": "admin",
            })
            (sketches_dir / "279470-001 Sketch.txt").write_text("Assigned Machine: Denver CNC", encoding="utf-8")
            (sketches_dir / "279470-002 Sketch.txt").write_text("Assigned Machine: WATER JET", encoding="utf-8")
            # Wrong-item Denver evidence must never satisfy item 001.
            (programs_dir / "279470-002.egl").write_text("wrong item", encoding="utf-8")
            store.production_files = ProductionFileService(config)
            item_files = store.production_files.item_assets("279470", "001", "88279470 FAB TEST")
            self.assertEqual([row["name"] for row in item_files["sketches"]], ["279470-001 Sketch.txt"])
            self.assertEqual(item_files["programs"], [])

            blocked = store.record_scan({
                "listId": "2026-10-19-staging-airport",
                "barcode": item["barcode"],
                "user": "admin",
                "station": "Airport Rd",
            })
            self.assertTrue(blocked["fabricationGate"]["blockStaging"])
            self.assertEqual(blocked["fabricationGate"]["machine"], "Denver CNC")
            self.assertIn("Fabrication required", blocked["lastScan"]["message"])
            with store.connect() as connection:
                staged_line = connection.execute(
                    "SELECT id, scanned_qty FROM line_items WHERE list_id = ? AND order_no = ? LIMIT 1",
                    ("2026-10-19-staging-airport", "279470"),
                ).fetchone()
                self.assertIsNotNone(staged_line)
                self.assertEqual(int(staged_line["scanned_qty"] or 0), 0)
                rack = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' ORDER BY id LIMIT 1"
                ).fetchone()
                self.assertIsNotNone(rack)
                rack_code = str(rack["rack_code"])

            (programs_dir / "279470-001.egl").write_text("fabricated", encoding="utf-8")
            # Keep the same service instance: the retry path must refresh only
            # the previously-missing evidence share instead of waiting for TTL.
            scanned = store.record_scan({
                "listId": "2026-10-19-staging-airport",
                "barcode": item["barcode"],
                "rackCode": rack_code,
                "user": "admin",
                "station": "Airport Rd",
            })
            self.assertNotIn("fabricationGate", scanned)
            with store.connect() as connection:
                staged_line = connection.execute(
                    "SELECT id, scanned_qty FROM line_items WHERE list_id = ? AND order_no = ? LIMIT 1",
                    ("2026-10-19-staging-airport", "279470"),
                ).fetchone()
                self.assertEqual(int(staged_line["scanned_qty"] or 0), 1)
                rack_item = connection.execute(
                    "SELECT ri.id FROM rack_items ri JOIN racks r ON r.id = ri.rack_id WHERE r.rack_code = ? AND ri.status = 'Active' LIMIT 1",
                    (rack_code,),
                ).fetchone()
                self.assertIsNotNone(rack_item)
                rack_item_id = int(rack_item["id"])

            store.complete_rack({"rackCode": rack_code}, "admin")
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                store.clear_rack_item({"rackItemId": rack_item_id}, "admin")
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                store.clear_rack({"rackCode": rack_code}, "admin")
            with store.connect() as connection:
                target = connection.execute(
                    "SELECT rack_code FROM racks WHERE active = 1 AND LOWER(status) = 'open' AND rack_code <> ? ORDER BY id LIMIT 1",
                    (rack_code,),
                ).fetchone()
                self.assertIsNotNone(target)
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                store.move_rack_item({"rackItemId": rack_item_id, "targetRackCode": str(target["rack_code"])}, "admin")

            store.uncomplete_rack({"rackCode": rack_code}, "admin")
            store.clear_rack_item({"rackItemId": rack_item_id}, "admin")
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0470_statistics_common_size_combines_rotated_dimensions(self) -> None:
        """Size frequency treats width/height rotation as the same physical lite."""
        verification_root = ROOT / "_verification_v0470_statistics_sizes"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        try:
            store = self.make_store(verification_root)
            first = imported_item("279472", "1", 2, "v0470-size:1")
            second = imported_item("279472", "2", 3, "v0470-size:2")
            first["dimensions"] = '28" x 79 1/2"'
            second["dimensions"] = '79 1/2" x 28"'
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-20", "items": [first, second]},
                "fileName": "Delivery List 10-20-2026.xlsx",
                "user": "admin",
            })

            report = store.reports_summary({"dateFrom": "2026-10-20", "dateTo": "2026-10-20"})
            glass_row = next(
                row for row in report["glassSizeFrequencyByType"]
                if "Clear Tempered" in str(row.get("glassType") or "")
            )
            self.assertEqual(glass_row["totalPieces"], 5)
            self.assertEqual(len(glass_row["sizes"]), 1)
            self.assertEqual(glass_row["sizes"][0]["dimensions"], '28" × 79 1/2"')
            self.assertEqual(glass_row["sizes"][0]["pieces"], 5)
            self.assertEqual(glass_row["mostCommonSize"]["pieces"], 5)
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0470_waterjet_and_unavailable_share_safety(self) -> None:
        """Waterjet completion is recognized while unavailable shares never create false scan blocks."""
        verification_root = ROOT / "_verification_v0470_waterjet"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        hardware_dir = verification_root / "Hardware Lists"
        sketches_dir = verification_root / "Sketches"
        programs_dir = verification_root / "Programs"
        completed_wj_dir = verification_root / "Completed WJ"
        for folder in (hardware_dir, sketches_dir, programs_dir, completed_wj_dir):
            folder.mkdir()
        try:
            config = replace(
                load_config(ROOT),
                hardware_lists_dir=hardware_dir,
                sketches_dir=sketches_dir,
                programs_dir=programs_dir,
                completed_wj_dir=completed_wj_dir,
            )
            (sketches_dir / "279471-001 Sketch.txt").write_text("Assigned machine: WATER JET", encoding="utf-8")
            service = ProductionFileService(config)
            missing = service.fabrication_status("279471", "001", "88279471")
            self.assertEqual(missing["machine"], "Waterjet")
            self.assertTrue(missing["blockStaging"])

            (completed_wj_dir / "279471-001 Complete.dxf").write_text("complete", encoding="utf-8")
            service = ProductionFileService(config)
            complete = service.fabrication_status("279471", "001", "88279471")
            self.assertTrue(complete["fabricated"])
            self.assertFalse(complete["blockStaging"])

            missing_root = verification_root / "Disconnected Completed WJ"
            disconnected_config = replace(config, completed_wj_dir=missing_root)
            disconnected = ProductionFileService(disconnected_config).fabrication_status("279471", "001", "88279471")
            self.assertEqual(disconnected["machine"], "Waterjet")
            self.assertIsNone(disconnected["fabricated"])
            self.assertFalse(disconnected["enforceable"])
            self.assertFalse(disconnected["blockStaging"])
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0472_machine_evidence_overrides_sketch_and_settings_persist(self) -> None:
        """Admin settings persist, while completed evidence owns the actual machine."""
        verification_root = ROOT / "_verification_v0472_production_settings"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        hardware_dir = verification_root / "Hardware Lists"
        sketches_dir = verification_root / "Sketches"
        programs_dir = verification_root / "Programs"
        completed_wj_dir = verification_root / "Completed WJ"
        for folder in (hardware_dir, sketches_dir, programs_dir, completed_wj_dir):
            folder.mkdir()
        try:
            store = self.make_store(verification_root)
            saved = store.update_production_file_settings(
                {
                    "enabled": True,
                    "enforceStaging": True,
                    "cacheMinutes": 7,
                    "roots": {
                        "hardware": str(hardware_dir),
                        "sketches": str(sketches_dir),
                        "programs": str(programs_dir),
                        "completedWaterjet": str(completed_wj_dir),
                    },
                    "machineTerms": {
                        "denver": ["DENVER", "DENVER CNC"],
                        "waterjet": ["WATER JET", "WATERJET", "WJ"],
                    },
                },
                "admin",
            )
            self.assertEqual(saved["cacheMinutes"], 7)
            self.assertEqual(saved["roots"]["programs"], str(programs_dir))

            (sketches_dir / "279473-001 Sketch.txt").write_text(
                "Assigned machine: WATER JET", encoding="utf-8"
            )
            (programs_dir / "279473-001.egl").write_text("Denver completion", encoding="utf-8")
            store.production_files = ProductionFileService(store.config)
            store.production_files.configure(store.get_production_file_settings())
            fast_status = store.production_files.fabrication_status(
                "279473", "001", "88279473", allow_content_read=False
            )
            self.assertEqual(fast_status["assignedMachine"], "Waterjet")
            self.assertEqual(fast_status["actualMachine"], "Denver CNC")
            status = store.production_files.fabrication_status("279473", "001", "88279473")
            self.assertEqual(status["assignedMachine"], "Waterjet")
            self.assertEqual(status["actualMachine"], "Denver CNC")
            self.assertTrue(status["machineOverride"])
            self.assertTrue(status["fabricated"])
            self.assertFalse(status["blockStaging"])
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0472_network_asset_lookup_never_walks_share_on_request_thread(self) -> None:
        """Mapped production drives schedule refresh and return the cached view immediately."""
        config = replace(
            load_config(ROOT),
            hardware_lists_dir=Path("I:/Production/Hardware"),
            sketches_dir=Path("I:/Production/Sketches"),
            programs_dir=Path("I:/Production/Programs"),
            completed_wj_dir=Path("I:/Production/Completed WJ"),
        )
        service = ProductionFileService(config)
        scheduled: list[list[str] | None] = []
        service.refresh_async = lambda kinds=None: scheduled.append(kinds)  # type: ignore[method-assign]
        service._walk_root = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("request thread walked share"))  # type: ignore[method-assign]
        self.assertEqual(service.assets("sketch"), [])
        self.assertEqual(scheduled, [["sketch"]])


    def test_v0469_unified_priority_work_applies_existing_and_waits_for_future_import(self) -> None:
        """Unified Priority Work handles imported and future Rush/Remake/Both orders."""
        verification_root = ROOT / "_verification_v0469_priority_work"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            delivery_date = "2026-10-12"
            existing = imported_item("279001", "1", 2, "v0469-existing:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": delivery_date, "items": [existing]},
                "fileName": "Delivery List 10-12-2026.xlsx",
                "user": "admin",
            })

            lookup = store.priority_work_lookup("88279001", "Both")
            self.assertTrue(lookup["found"])
            self.assertEqual(lookup["deliveryDate"], delivery_date)
            applied = store.submit_priority_work(
                {
                    "priorityType": "Both",
                    "jobNumber": "88279001",
                    "deliveryDate": "2026-10-14",
                    "reason": "Missing Glass",
                    "responsible": "Priority Tester",
                    "emailMode": "none",
                },
                "admin",
            )
            self.assertTrue(applied["ok"])
            self.assertEqual(applied["action"], "applied")
            self.assertEqual(applied["priorityType"], "Both")
            self.assertEqual(applied["matchedDeliveryDate"], "2026-10-14")
            with store.connect() as connection:
                existing_rows = connection.execute(
                    "SELECT process_state, priority_delivery_date FROM line_items WHERE source_id = ? ORDER BY list_id",
                    ("279001-001",),
                ).fetchall()
            self.assertGreaterEqual(len(existing_rows), 3)
            self.assertTrue(all("Rush" in str(row["process_state"] or "") for row in existing_rows))
            self.assertTrue(all("Remake" in str(row["process_state"] or "") for row in existing_rows))
            self.assertEqual({str(row["priority_delivery_date"] or "") for row in existing_rows}, {"2026-10-14"})
            inbound = store.get_delivery_list(f"{delivery_date}-inbound-indian-trail")
            existing_row = next(row for row in inbound["items"] if row["sourceId"] == "279001-001")
            self.assertEqual(existing_row["priorityBanner"]["kind"], "both")
            self.assertEqual(existing_row["priorityBanner"]["label"], "Rush + Remake")
            self.assertEqual(existing_row["priorityBanner"]["reason"], "Missing Glass")

            queued = store.submit_priority_work(
                {
                    "priorityType": "Remake",
                    "jobNumber": "88279002",
                    "deliveryDate": "2026-10-16",
                    "reason": "Missing Glass",
                    "responsible": "Priority Tester",
                    "emailMode": "none",
                },
                "admin",
            )
            self.assertTrue(queued["ok"])
            self.assertEqual(queued["action"], "queued")
            self.assertFalse(queued["lookupResult"]["found"])

            future = imported_item("279002", "1", 1, "v0469-future:1")
            future["job"] = "88279002.2R TEST JOB"
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-15", "items": [future]},
                "fileName": "Delivery List 10-15-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as connection:
                future_rows = connection.execute(
                    "SELECT process_state, priority_delivery_date FROM line_items WHERE source_id = ? ORDER BY list_id",
                    ("279002-001",),
                ).fetchall()
            self.assertGreaterEqual(len(future_rows), 3)
            self.assertTrue(all("Remake" in str(row["process_state"] or "") for row in future_rows))
            self.assertEqual({str(row["priority_delivery_date"] or "") for row in future_rows}, {"2026-10-16"})
            matched_request = next(
                request for request in store.priority_intake_requests()
                if request.get("jobNumber") == "88279002"
            )
            self.assertEqual(matched_request["status"], "matched")
            self.assertEqual(matched_request["matchedDeliveryDate"], "2026-10-16")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                shutil.rmtree(verification_root)


if __name__ == "__main__":
    unittest.main()
