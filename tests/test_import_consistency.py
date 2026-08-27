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
            self.assertIn("not been scanned Outbound", blocked_receive["message"])

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


if __name__ == "__main__":
    unittest.main()
