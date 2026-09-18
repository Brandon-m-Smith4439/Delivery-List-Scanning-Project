# File: tests/test_import_consistency.py
"""Regression coverage for delivery-list stage routing and import quantities."""

from __future__ import annotations

import unittest
from unittest import mock
import errno
import json
import zipfile
from io import BytesIO
import shutil
import os
import threading
import time
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from backend.config import load_config
from backend.store import SQLiteDeliveryStore, build_delivery_lists, canonical_clear_glass_label, glass_cost_profile, glass_profile_identity_key, rack_barcode_text, parse_aw_delivery_workbook
from automation.sql_delivery_export.import_delivery_folder import direct_sql_sync, scanner_payload_from_sql_export
from backend.production_files import ProductionFileService
from backend.operations import OperationsFeatureService
from backend.automation_control import DeliveryAutomationController
from database.migrations import _migration_019_v516_aw_eastern_timestamp_contract, run_sqlite_migrations
from database.time_utils import normalize_aw_plant_timestamp, normalize_utc_timestamp, parse_aw_plant_timestamp, parse_utc_timestamp, plant_time_zone


ROOT = Path(__file__).resolve().parents[1]


def automation_test_config_payload(working_root: Path) -> dict[str, object]:
    """Build non-secret maintained defaults when release packages omit local config."""
    working_root = Path(working_root)
    return {
        "Version": "v121",
        "ProjectRoot": str(ROOT),
        "WorkingRoot": str(working_root),
        "DestinationFolder": str(working_root / "Temp Delivery Lists"),
        "Automation": {"Mode": "sql-export-and-import", "ScheduleEnabled": False, "AllowWebGuiControl": True},
        "Schedule": {
            "IncrementalIntervalMinutes": 60,
            "IncrementalPastDays": 2,
            "IncrementalFutureDays": 14,
            "FullPastDays": 7,
            "FullFutureDays": 90,
            "FullRefreshTime": "17:00",
        },
        "Notifications": {"Enabled": True, "NotifyOnNoChanges": True},
        "RejectSync": {"Enabled": True, "IncrementalPastDays": 30, "FullPastDays": 365},
        "ProductionSync": {
            "Enabled": True,
            "ScheduledEnabled": True,
            "IncludeCuttingBookings": True,
            "CuttingBookingLookbackDays": 120,
            "OrderLookbackDays": 14,
            "QueryBatchSize": 60,
            "QueryTimeoutSeconds": 75,
            "GenerationHistoryDepth": 4,
            "CrystalReportFile": "Prodman_CuttingLabel_Optimisation.rpt",
            "CrystalReportPrintPointId": 846,
        },
        "Database": {"Server": "TEST", "Database": "TEST", "AuthenticationMode": "Windows", "QueryTimeoutSeconds": 75},
        "Runtime": {},
        "Import": {"Mode": "direct-store"},
    }


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

    def test_direct_aw_sql_payload_preserves_source_identity_and_workbook_formatting(self) -> None:
        payload = scanner_payload_from_sql_export(
            {
                "deliveryDate": "2026-09-02",
                "dimensionUnitsPerInch": 32,
                "rows": [
                    {
                        "product": '3/8" Clear Tempered',
                        "job": "DIRECT TEST",
                        "order": 990001,
                        "item": 7,
                        "sourceOrder": 240111,
                        "sourceItem": 1,
                        "quantity": "2.0",
                        "widthUnits": 2400,
                        "heightUnits": 2048,
                        "customer": "TEST CUSTOMER",
                        "route": "IT",
                        "remake": "RM",
                        "dimensionsOverride": "",
                    }
                ],
            }
        )
        item = payload["items"][0]
        self.assertEqual(item["id"], "aw-sql:240111:001")
        self.assertEqual(item["order"], "990001")
        self.assertEqual(item["item"], "007")
        self.assertEqual(item["qty"], 2)
        self.assertEqual(item["dimensions"], '75" x 64"')
        self.assertEqual(item["processState"], "External Remake")

    def test_sql_server_timestamps_are_normalized_and_migration_preserves_event_identity(self) -> None:
        verification_root = ROOT / "_verification_timestamp_migration"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            source = {
                "awRowId": "timestamp-row-1",
                "orderNr": "991001",
                "itemNr": "1",
                "bomId": 0,
                "quantity": 1,
                "breakageDate": "2026-09-04T10:00:33.2730000",
                "sourceLastChangedAt": "2026-09-04T10:01:34.1234567",
                "originalJobNumber": "88001",
                "reasonCode": 1,
                "locationCode": 1,
            }
            expected_event_key = store._aw_reject_event_key(source)
            store.sync_aw_reject_rows([source])
            with store.connect() as con:
                event = con.execute(
                    "SELECT event_key, breakage_date, source_last_changed_at FROM aw_reject_events WHERE event_key=?",
                    (expected_event_key,),
                ).fetchone()
                raw = con.execute(
                    "SELECT event_key, breakage_date, last_changed_at FROM aw_reject_source_rows WHERE aw_row_id=?",
                    ("timestamp-row-1",),
                ).fetchone()
                mirror = con.execute(
                    "SELECT rejected_at FROM reject_events WHERE source_type='aw' AND source_external_key=?",
                    (expected_event_key,),
                ).fetchone()
            self.assertEqual(event["event_key"], expected_event_key)
            self.assertEqual(raw["event_key"], expected_event_key)
            for value in (event["breakage_date"], event["source_last_changed_at"], raw["breakage_date"], raw["last_changed_at"], mirror["rejected_at"]):
                self.assertTrue(str(value).endswith("+00:00"), value)
                self.assertEqual(parse_utc_timestamp(value).utcoffset(), timezone.utc.utcoffset(None))

            # Simulate one pre-schema-18 database row and prove the numbered
            # migration repairs values without changing immutable event IDs.
            with store.connect() as con:
                con.execute("UPDATE aw_reject_events SET breakage_date=? WHERE event_key=?", (source["breakageDate"], expected_event_key))
                con.execute("UPDATE aw_reject_source_rows SET last_changed_at=? WHERE aw_row_id=?", (source["sourceLastChangedAt"], "timestamp-row-1"))
                con.execute("DELETE FROM schema_migrations WHERE version IN (18, 19, 20, 21)")
                run_sqlite_migrations(con, store)
                repaired = con.execute(
                    "SELECT event_key, breakage_date FROM aw_reject_events WHERE event_key=?",
                    (expected_event_key,),
                ).fetchone()
                repaired_source = con.execute(
                    "SELECT last_changed_at FROM aw_reject_source_rows WHERE aw_row_id=?",
                    ("timestamp-row-1",),
                ).fetchone()
                installed = int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
            self.assertEqual(installed, 21)
            self.assertEqual(repaired["event_key"], expected_event_key)
            self.assertEqual(repaired["breakage_date"], "2026-09-04T14:00:33+00:00")
            self.assertEqual(repaired_source["last_changed_at"], "2026-09-04T14:01:34+00:00")
            self.assertEqual(normalize_utc_timestamp("2026-09-04T10:00:33Z"), "2026-09-04T10:00:33+00:00")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v521_machine_configuration_persists_without_schema_change(self) -> None:
        verification_root = ROOT / "_verification_machine_configuration_v521"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                before_schema = int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0)
            saved = store.update_machine_configuration({
                "machines": [
                    {"code": "denver", "name": "Denver CNC", "terms": ["DENVER"], "color": "#2563eb", "progressRank": 0, "active": True, "completionKind": "denver"},
                    {"code": "waterjet", "name": "WaterJet", "terms": ["WATERJET"], "color": "#7c3aed", "progressRank": 0, "active": True, "completionKind": "waterjet"},
                    {"code": "edge-polisher", "name": "Edge Polisher", "terms": ["EDGE POLISH"], "color": "#118855", "progressRank": 15, "active": True, "completionKind": "custom"},
                ]
            }, "v521-test")
            self.assertEqual(before_schema, 21)
            with store.connect() as con:
                after_schema = int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0)
            self.assertEqual(after_schema, 21)
            by_code = {row["code"]: row for row in saved["machines"]}
            self.assertEqual(by_code["edge-polisher"]["name"], "Edge Polisher")
            self.assertEqual(by_code["edge-polisher"]["color"], "#118855")
            self.assertEqual(by_code["edge-polisher"]["progressRank"], 15)
            reread = {row["code"]: row for row in store.get_machine_configuration()["machines"]}
            self.assertEqual(reread["edge-polisher"]["terms"], ["EDGE POLISH"])
            with store.connect() as con:
                audit = con.execute(
                    "SELECT action FROM audit_events WHERE action='update_machine_configuration' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(audit)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_workbook_rm_marker_is_external_remake(self) -> None:
        fake_rows = [
            (1, {"A": '3/8" Clear Tempered'}),
            (2, {
                "A": "884200 TEST JOB", "E": "4200", "F": "1", "G": "2",
                "H": '36" x 72"', "I": "TEST CUSTOMER", "J": "RM", "L": "IT",
            }),
        ]
        with mock.patch("backend.store.read_xlsx_rows", return_value=fake_rows), mock.patch(
            "backend.store.delivery_date_from_rows_or_name", return_value="2026-09-02"
        ):
            payload = parse_aw_delivery_workbook(Path("Delivery List 09-02-2026.xlsx"))
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["processState"], "External Remake")
        self.assertEqual(payload["items"][0]["queueState"], "RM")

    def test_direct_aw_sql_sync_uses_maintained_scanner_importer(self) -> None:
        verification_root = ROOT / "_verification_direct_aw_sql"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            envelope = {
                "sourceName": "A+W SQL 2026-09-02",
                "sourcePath": "aw-sql://SQLAWGLASS/BFSMAIN/SYSADM/BW_AUFTR_KOPF+BW_AUFTR_POS/2026-09-02",
                "sourceHash": "direct-test-hash",
                "payload": {
                    "deliveryDate": "2026-09-02",
                    "dimensionUnitsPerInch": 32,
                    "rows": [
                        {
                            "product": '3/8" Clear Tempered',
                            "job": "DIRECT TEST",
                            "order": 240222,
                            "item": 1,
                            "sourceOrder": 240222,
                            "sourceItem": 1,
                            "quantity": 2,
                            "widthUnits": 2400,
                            "heightUnits": 2048,
                            "customer": "TEST CUSTOMER",
                            "route": "IT",
                            "remake": "",
                            "dimensionsOverride": "",
                        }
                    ],
                },
            }
            summary = direct_sql_sync(
                store,
                verification_root,
                ["2026-09-02"],
                {"2026-09-02"},
                "direct-sync-test",
                [envelope],
                build_delivery_lists,
                allow_source_removals=False,
            )
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["sourceMode"], "aw_sql_direct")
            self.assertEqual(summary["newFileCount"], 1)
            self.assertEqual(summary["failedFileCount"], 0)
            with store.connect() as connection:
                imported = connection.execute(
                    "SELECT source_name, source_path, source_hash, import_kind FROM imports ORDER BY id DESC LIMIT 1"
                ).fetchone()
            self.assertEqual(imported["source_name"], "A+W SQL 2026-09-02")
            self.assertEqual(imported["source_hash"], "direct-test-hash")
            self.assertEqual(imported["import_kind"], "aw_sql_direct_sync")
            self.assertTrue(str(imported["source_path"]).startswith("aw-sql://SQLAWGLASS/"))
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_aw_reject_sync_groups_bom_rows_and_preserves_external_row_ids(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_sync"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            shared = {
                "orderNr": "238091",
                "itemNr": "1",
                "keyIndex": 1,
                "subPosition": 0,
                "quantity": 1,
                "breakageDate": "2026-09-01T15:27:42.0000000",
                "originalJobNumber": "6455",
                "replacementJobNumber": "",
                "reasonCode": 137,
                "reasonLabel": "Broke in Machine",
                "locationCode": 5,
                "locationLabel": "Grinding",
                "fromScanner": 1,
                "breakageUser": "Brandon Smith",
                "sourceLastChangedAt": "2026-09-01T15:27:42.0000000",
                "sourceLastChangedUser": "Brandon Smith",
                "timelineEmployee": "Brandon Smith",
                "registrationPointId": 3000,
                "registrationPoint": "08 - Tempering Complete",
                "machine": "Fuse Cube",
                "bookingMessage": "Reject",
            }
            rows = [
                {**shared, "awRowId": "row-bom0", "bomId": 0, "bomNode": 0, "workTypeId": 60, "workType": "Tempering", "scanMode": "Explicit"},
                {**shared, "awRowId": "row-bom1", "bomId": 1, "bomNode": 0, "workTypeId": 10, "workType": "Automatic Cutting", "scanMode": "Implicit"},
                {**shared, "awRowId": "row-bom2", "bomId": 2, "bomNode": 1, "workTypeId": 20, "workType": "Polishing", "scanMode": "Implicit"},
            ]
            result = store.sync_aw_reject_rows(rows, source_window={"windowStart": "2026-08-01", "windowEnd": "2026-09-02"})
            self.assertTrue(result["ok"])
            self.assertEqual(result["sourceRows"], 3)
            self.assertEqual(result["logicalEvents"], 1)
            self.assertEqual(result["insertedSourceRows"], 3)
            self.assertEqual(result["newInternalRejects"], 1)

            listed = store.list_aw_rejects(order_no="238091", item_no="1")["rejects"]
            self.assertEqual(len(listed), 1)
            event = listed[0]
            self.assertEqual(event["sourceRowCount"], 3)
            self.assertEqual(event["reason"], "Broke in Machine")
            self.assertEqual(event["location"], "Grinding")
            self.assertEqual(event["workType"], "Tempering")
            self.assertEqual(event["scanMode"], "Explicit")
            self.assertEqual(event["machine"], "Fuse Cube")

            refreshed = [{**row, "replacementJobNumber": "9001", "sourceLastChangedAt": "2026-09-02T09:15:00.0000000"} for row in rows]
            second = store.sync_aw_reject_rows(refreshed)
            self.assertEqual(second["logicalEvents"], 1)
            self.assertEqual(second["newInternalRejects"], 0)
            with store.connect() as connection:
                counts = connection.execute(
                    "SELECT (SELECT COUNT(*) FROM aw_reject_events) AS events, (SELECT COUNT(*) FROM aw_reject_source_rows) AS source_rows"
                ).fetchone()
            self.assertEqual(int(counts["events"]), 1)
            self.assertEqual(int(counts["source_rows"]), 3)
            self.assertEqual(store.list_aw_rejects(order_no="238091")["rejects"][0]["replacementJobNumber"], "9001")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                verification_root.rmdir()

    def test_existing_aw_cache_backfills_internal_reject_mirror_on_startup_reconciliation(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_startup_backfill_v485"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-02", "items": [imported_item("991000", "1", 1, "aw-cache-backfill:1")]},
                "fileName": "Delivery List 09-02-2026.xlsx",
                "user": "admin",
            })
            row = {
                "awRowId": "cached-bom0", "orderNr": "991000", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-01T12:00:00.0000000", "originalJobNumber": "7100",
                "reasonCode": 137, "reasonLabel": "Broke in Machine",
                "locationCode": 5, "locationLabel": "Grinding", "fromScanner": 1,
                "breakageUser": "A+W User", "bookingMessage": "Reject",
            }
            store.sync_aw_reject_rows([row])
            with store.connect() as con:
                con.execute("DELETE FROM reject_events WHERE source_type='aw'")
                con.commit()
                self.assertEqual(con.execute("SELECT COUNT(*) FROM aw_reject_events").fetchone()[0], 1)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM reject_events WHERE source_type='aw'").fetchone()[0], 0)
            result = store.ensure_aw_internal_reject_mirrors()
            self.assertTrue(result["startupBackfill"])
            self.assertEqual(result["mirroredInternalRejects"], 1)
            self.assertEqual(result["newInternalRejects"], 0)
            with store.connect() as con:
                mirror = con.execute("SELECT reason_label, location_label, scan_qty_reduced FROM reject_events WHERE source_type='aw'").fetchone()
            self.assertEqual(mirror["reason_label"], "Broke in Machine")
            self.assertEqual(mirror["location_label"], "Grinding")
            self.assertEqual(int(mirror["scan_qty_reduced"] or 0), 0)
            # The reconciliation is idempotent once the mirror exists.
            again = store.ensure_aw_internal_reject_mirrors()
            self.assertEqual(again["sourceRows"], 0)
            self.assertEqual(again["mirroredInternalRejects"], 0)
            self.assertEqual(again["newInternalRejects"], 0)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_startup_skips_pending_aw_rollbacks_until_post_import_retry(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_startup_pending_v500"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            row = {
                "awRowId": "pending-bom0", "orderNr": "991100", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-01T12:00:00+00:00", "originalJobNumber": "7101",
                "reasonCode": 137, "reasonLabel": "Broke in Machine",
                "locationCode": 5, "locationLabel": "Grinding", "fromScanner": 1,
                "breakageUser": "A+W User", "timelineEmployee": "A+W User", "bookingMessage": "Reject",
            }
            first = store.sync_aw_reject_rows([row])
            self.assertEqual(first["pendingOperationalRollbacks"], 1)
            with store.connect() as con:
                self.assertEqual(con.execute("SELECT rollback_applied_at FROM aw_reject_source_rows WHERE aw_row_id='pending-bom0'").fetchone()[0], "")

            # Normal server startup must not repeatedly replay every historical
            # pending reject when no delivery line could possibly be reset yet.
            startup = store.ensure_aw_internal_reject_mirrors()
            self.assertEqual(startup["sourceRows"], 0)

            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-03", "items": [imported_item("991100", "1", 6, "pending-reject:1")]},
                "fileName": "Delivery List 09-03-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as con:
                con.execute("UPDATE line_items SET scanned_qty=6 WHERE order_no='991100' AND item_no='001'")
                con.commit()

            post_import = store.ensure_aw_internal_reject_mirrors(retry_pending_rollbacks=True)
            self.assertEqual(post_import["operationalRollbacks"], 1)
            with store.connect() as con:
                states = [int(row[0] or 0) for row in con.execute("SELECT scanned_qty FROM line_items WHERE order_no='991100' AND item_no='001'").fetchall()]
                marker = con.execute("SELECT rollback_applied_at FROM aw_reject_source_rows WHERE aw_row_id='pending-bom0'").fetchone()[0]
            self.assertTrue(states)
            self.assertTrue(all(value == 5 for value in states))
            self.assertTrue(str(marker or ""))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_reject_new_codes_auto_register_and_unmapped_label_changes_refresh(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_new_codes_v485"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            operations = OperationsFeatureService(store, store.config, verification_root)
            row = {
                "awRowId": "new-code-bom0", "orderNr": "990100", "itemNr": "2", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-02T10:15:00.0000000", "originalJobNumber": "7001",
                "reasonCode": 141, "reasonLabel": "New A+W Reason",
                "locationCode": 18, "locationLabel": "New A+W Location",
                "fromScanner": 1, "breakageUser": "A+W User", "bookingMessage": "Reject",
            }
            store.sync_aw_reject_rows([row])
            mappings = {(value["kind"], value["sourceCode"]): value for value in store.list_reject_value_mappings()}
            self.assertEqual(mappings[("reason", 141)]["sourceLabel"], "New A+W Reason")
            self.assertEqual(mappings[("location", 18)]["sourceLabel"], "New A+W Location")
            event = operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]
            self.assertEqual(event["reason_label"], "New A+W Reason")
            self.assertEqual(event["location_label"], "New A+W Location")

            # With no scanner override, a renamed A+W lookup label becomes the
            # current display value on the next synchronization.
            store.sync_aw_reject_rows([{
                **row,
                "reasonLabel": "Renamed A+W Reason",
                "locationLabel": "Renamed A+W Location",
                "sourceLastChangedAt": "2026-09-02T11:15:00.0000000",
            }])
            event = operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]
            self.assertEqual(event["reason_label"], "Renamed A+W Reason")
            self.assertEqual(event["location_label"], "Renamed A+W Location")
            mappings = {(value["kind"], value["sourceCode"]): value for value in store.list_reject_value_mappings()}
            self.assertEqual(mappings[("reason", 141)]["sourceLabel"], "Renamed A+W Reason")
            self.assertEqual(mappings[("location", 18)]["sourceLabel"], "Renamed A+W Location")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_reject_internal_mirror_rolls_back_scan_state_once(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_rollback_v486"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {
                    "deliveryDate": "2026-09-02",
                    "items": [imported_item("238091", "1", 6, "aw-reject:no-rollback")],
                },
                "fileName": "Delivery List 09-02-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as connection:
                line = connection.execute(
                    "SELECT id, list_id, barcode FROM line_items WHERE order_no='238091' AND item_no='001' LIMIT 1"
                ).fetchone()
                connection.execute(
                    "UPDATE line_items SET scanned_qty=6 WHERE order_no=? AND item_no=?",
                    ("238091", "001"),
                )
                connection.execute(
                    "INSERT INTO scan_events (list_id, line_item_id, barcode, canonical_barcode, user_name, station, event_type, message, qty_delta, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (line["list_id"], line["id"], line["barcode"], line["barcode"], "tester", "TEST", "scan", "Test scan", 1, "2026-09-01T15:00:00+00:00"),
                )
                connection.commit()
            row = {
                "awRowId": "no-rollback-bom0",
                "orderNr": "238091", "itemNr": "1", "bomId": 0, "keyIndex": 1, "subPosition": 0,
                "quantity": 1, "breakageDate": "2026-09-01T15:27:42.0000000", "originalJobNumber": "6455",
                "reasonCode": 137, "reasonLabel": "Broke in Machine", "locationCode": 5, "locationLabel": "Grinding",
                "fromScanner": 1, "breakageUser": "Brandon Smith", "workTypeId": 60, "workType": "Tempering",
                "registrationPointId": 3000, "registrationPoint": "08 - Tempering Complete", "bookingMessage": "Reject",
            }
            result = store.sync_aw_reject_rows([row])
            self.assertEqual(result["mirroredInternalRejects"], 1)
            self.assertEqual(result["newInternalRejects"], 1)
            with store.connect() as connection:
                states = connection.execute(
                    "SELECT scanned_qty, internal_reject_count FROM line_items WHERE order_no='238091' AND item_no='001'"
                ).fetchall()
                scans = connection.execute(
                    "SELECT user_name, station, event_type, qty_delta FROM scan_events WHERE line_item_id IN (SELECT id FROM line_items WHERE order_no='238091' AND item_no='001') ORDER BY id"
                ).fetchall()
                mirror = connection.execute(
                    "SELECT source_type, scan_qty_reduced, delivery_date FROM reject_events WHERE source_type='aw'"
                ).fetchone()
            self.assertTrue(states)
            self.assertTrue(all(int(state["scanned_qty"] or 0) == 5 for state in states))
            self.assertTrue(all(int(state["internal_reject_count"] or 0) == 1 for state in states))
            reset_rows = [scan for scan in scans if str(scan["event_type"]) == "reject_reset"]
            self.assertEqual(len(reset_rows), len(states))
            self.assertTrue(any(str(scan["event_type"]) == "scan" for scan in scans))
            self.assertTrue(all(int(scan["qty_delta"] or 0) <= 0 for scan in reset_rows))
            self.assertEqual(str(mirror["source_type"]), "aw")
            self.assertEqual(int(mirror["scan_qty_reduced"] or 0), len(states))
            self.assertEqual(str(mirror["delivery_date"]), "2026-09-02")
            with store.connect() as connection:
                source = connection.execute(
                    "SELECT rollback_applied_at, rollback_scan_qty_reduced FROM aw_reject_source_rows WHERE aw_row_id='no-rollback-bom0'"
                ).fetchone()
                first_reset_count = connection.execute(
                    "SELECT COUNT(*) FROM scan_events WHERE event_type='reject_reset'"
                ).fetchone()[0]
            self.assertTrue(str(source["rollback_applied_at"] or ""))
            self.assertEqual(int(source["rollback_scan_qty_reduced"] or 0), len(states))

            # A source refresh must not replay the operational reset.
            store.sync_aw_reject_rows([{**row, "sourceLastChangedAt": "2026-09-02T12:00:00+00:00"}])
            with store.connect() as connection:
                second_states = connection.execute(
                    "SELECT scanned_qty FROM line_items WHERE order_no='238091' AND item_no='001'"
                ).fetchall()
                second_reset_count = connection.execute(
                    "SELECT COUNT(*) FROM scan_events WHERE event_type='reject_reset'"
                ).fetchone()[0]
            self.assertTrue(all(int(state["scanned_qty"] or 0) == 5 for state in second_states))
            self.assertEqual(second_reset_count, first_reset_count)

            unchanged = store.sync_aw_reject_rows([{**row, "sourceLastChangedAt": "2026-09-02T12:00:00+00:00"}])
            self.assertTrue(unchanged.get("skippedUnchanged"))
            self.assertEqual(int(unchanged.get("unchangedSourceRows") or 0), 1)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_rejects_feed_standard_timeline_and_machine_statistics(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_reporting_v487"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {
                    "deliveryDate": "2026-09-03",
                    "items": [{**imported_item("238296", "1", 1, "aw-reporting:1"), "dimensions": '48" x 14"'}],
                },
                "fileName": "Delivery List 09-03-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_reject_rows([{
                "awRowId": "reporting-bom0", "orderNr": "238296", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-02T12:22:00+00:00", "originalJobNumber": "6492",
                "reasonCode": 137, "reasonLabel": "Broke in Machine",
                "locationCode": 5, "locationLabel": "Grinding",
                "fromScanner": 1, "breakageUser": "Brandon Smith",
                "workTypeId": 60, "workType": "Tempering",
                "registrationPointId": 3000, "registrationPoint": "08 - Tempering Complete",
                "machine": "Fuse Cube", "scanMode": "Explicit", "bookingMessage": "Reject",
            }])

            operations = OperationsFeatureService(store, store.config, verification_root)
            timeline = operations.list_rejects(date_from="2026-09-02", date_to="2026-09-02")["rejects"]
            self.assertEqual(len(timeline), 1)
            self.assertEqual(timeline[0]["source_type"], "aw")
            self.assertEqual(timeline[0]["reason_label"], "Broke in Machine")
            self.assertEqual(timeline[0]["location_label"], "Grinding")
            self.assertEqual(timeline[0]["aw_machine"], "Fuse Cube")
            self.assertEqual(timeline[0]["aw_work_type"], "Tempering")

            report = store.reports_summary({"dateFrom": "2026-09-02", "dateTo": "2026-09-02"})
            self.assertEqual(report["breakage"]["internalRejects"]["eventCount"], 1)
            self.assertEqual(report["breakage"]["internalRejects"]["pieces"], 1)
            machines = report["breakage"]["internalByMachine"]
            self.assertEqual(machines[0]["machine"], "Fuse Cube")
            self.assertEqual(machines[0]["eventCount"], 1)
            self.assertEqual(machines[0]["reasons"][0]["reason"], "Broke in Machine")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_reject_timeline_defaults_to_two_calendar_weeks_and_pages_server_side(self) -> None:
        verification_root = ROOT / "_verification_reject_paging_v489"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            operations = OperationsFeatureService(store, store.config, verification_root)
            with store.connect() as con:
                for index in range(1, 66):
                    con.execute(
                        """
                        INSERT INTO reject_events (
                            delivery_date, order_no, item_no, qty, reason_label,
                            location_label, rejected_at, rejected_by
                        ) VALUES (?, ?, ?, 1, 'Break', 'Cutting', ?, ?)
                        """,
                        (
                            "2026-09-03",
                            f"88{index:04d}",
                            "001",
                            f"2026-09-02T12:{index % 60:02d}:00+00:00",
                            "Operator A" if index % 2 else "Operator B",
                        ),
                    )
                con.execute(
                    """
                    INSERT INTO reject_events (
                        delivery_date, order_no, item_no, qty, reason_label,
                        location_label, rejected_at, rejected_by
                    ) VALUES ('2026-08-01', '770001', '001', 1, 'Old Break', 'Old', '2026-08-01T12:00:00+00:00', 'Old User')
                    """
                )
                con.commit()

            class FixedDate(date):
                @classmethod
                def today(cls) -> "FixedDate":
                    return cls(2026, 9, 6)

            with mock.patch("backend.operations.date", FixedDate):
                first = operations.list_rejects(limit=50, page=1)
                self.assertEqual(first["dateFrom"], "2026-08-24")
                self.assertEqual(first["dateTo"], "2026-09-06")
                self.assertEqual(first["totalCount"], 65)
                self.assertEqual(first["totalPages"], 2)
                self.assertEqual(len(first["rejects"]), 50)
                self.assertEqual(first["summary"]["eventCount"], 65)
                self.assertNotIn("Old User", first["filterOptions"]["users"])

                second = operations.list_rejects(limit=50, page=2)
                self.assertEqual(len(second["rejects"]), 15)
                self.assertEqual(second["page"], 2)

                filtered = operations.list_rejects(limit=50, page=1, rejected_by="Operator A")
                self.assertTrue(filtered["rejects"])
                self.assertTrue(all(row["rejected_by"] == "Operator A" for row in filtered["rejects"]))
                self.assertLess(filtered["totalCount"], first["totalCount"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_reject_actor_prefers_exact_reject_booking_employee_and_repairs_existing_mirror(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_actor_v489"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-03", "items": [imported_item("238400", "1", 1, "aw-actor:1")]},
                "fileName": "Delivery List 09-03-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as con:
                con.execute("UPDATE line_items SET scanned_qty=1 WHERE order_no='238400' AND item_no='001'")
                con.commit()
            store.sync_aw_reject_rows([{
                "awRowId": "actor-bom0", "orderNr": "238400", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-02T14:10:00+00:00", "originalJobNumber": "6510",
                "reasonCode": 137, "reasonLabel": "Broke in Machine",
                "locationCode": 5, "locationLabel": "Grinding",
                "fromScanner": 1,
                "breakageUser": "Vinny Spaulding",
                "timelineEmployee": "Brandon Smith",
                "workTypeId": 60, "workType": "Tempering",
                "registrationPointId": 3000, "registrationPoint": "08 - Tempering Complete",
                "machine": "Fuse Cube", "scanMode": "Explicit", "bookingMessage": "Reject",
            }])
            with store.connect() as con:
                mirror = con.execute("SELECT rejected_by FROM reject_events WHERE source_type='aw'").fetchone()
                event = con.execute("SELECT event_key, breakage_user, timeline_employee FROM aw_reject_events").fetchone()
                self.assertEqual(mirror["rejected_by"], "Brandon Smith")
                self.assertEqual(event["breakage_user"], "Brandon Smith")
                self.assertEqual(event["timeline_employee"], "Brandon Smith")

                # Simulate v0.488-v0.499 records written with the mutable
                # PROD_BREAKAGE maintenance user instead of the booking employee.
                con.execute("UPDATE reject_events SET rejected_by='Vinny Spaulding' WHERE source_type='aw'")
                con.execute("UPDATE aw_reject_events SET breakage_user='Vinny Spaulding'")

                # scan_events is intentionally append-only. Insert a representative
                # legacy row carrying the old actor and old verbose message rather
                # than illegally mutating history. v0.500 must project the verified
                # FS_BOOK_HISTORY actor at read time while the raw audit row remains
                # byte-for-byte attributable to its original write.
                line = con.execute(
                    "SELECT id, list_id, barcode FROM line_items WHERE order_no='238400' AND item_no='001' LIMIT 1"
                ).fetchone()
                con.execute(
                    """
                    INSERT INTO scan_events (
                        list_id, line_item_id, barcode, canonical_barcode, user_name, station,
                        event_type, message, reason, qty_delta, created_at
                    ) VALUES (?, ?, ?, ?, 'Vinny Spaulding', 'A+W Reject', 'reject_reset', ?, ?, -1, ?)
                    """,
                    (
                        line["list_id"], line["id"], line["barcode"], line["barcode"],
                        f"A+W Internal reject reset 238400-001 ({event['event_key']})",
                        "Legacy A+W reject-reset actor test",
                        "2026-09-02T14:11:00+00:00",
                    ),
                )
                list_id = str(line["list_id"])
                con.commit()

            repaired = store.ensure_aw_internal_reject_mirrors()
            self.assertGreaterEqual(int(repaired.get("actorCorrections") or 0), 2)
            with store.connect() as con:
                mirror = con.execute("SELECT rejected_by FROM reject_events WHERE source_type='aw'").fetchone()
                event = con.execute("SELECT breakage_user FROM aw_reject_events").fetchone()
                raw_scan_users = [row[0] for row in con.execute("SELECT user_name FROM scan_events WHERE event_type='reject_reset'").fetchall()]
            projected_scan_users = [row["user"] for row in store.get_scan_events(list_id) if row["eventType"] == "reject_reset"]
            self.assertEqual(mirror["rejected_by"], "Brandon Smith")
            self.assertEqual(event["breakage_user"], "Brandon Smith")
            self.assertIn("Vinny Spaulding", raw_scan_users)
            self.assertTrue(projected_scan_users)
            self.assertTrue(all(user == "Brandon Smith" for user in projected_scan_users))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_reject_mirror_mapping_source_refresh_manual_override_and_bulk_relabel(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_mapping_v485"
        verification_root.mkdir(exist_ok=True)
        database_path = verification_root / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            store = self.make_store(verification_root)
            operations = OperationsFeatureService(store, store.config, verification_root)
            row = {
                "awRowId": "mapping-row-1",
                "orderNr": "238091",
                "itemNr": "1",
                "bomId": 0,
                "keyIndex": 1,
                "subPosition": 0,
                "quantity": 1,
                "breakageDate": "2026-09-01T15:27:42.0000000",
                "originalJobNumber": "6455",
                "replacementJobNumber": "",
                "reasonCode": 137,
                "reasonLabel": "Broke in Machine",
                "locationCode": 5,
                "locationLabel": "Grinding",
                "fromScanner": 1,
                "breakageUser": "Brandon Smith",
                "workTypeId": 60,
                "workType": "Tempering",
                "registrationPointId": 3000,
                "registrationPoint": "08 - Tempering Complete",
                "bookingMessage": "Reject",
            }
            result = store.sync_aw_reject_rows([row])
            self.assertEqual(result["mirroredInternalRejects"], 1)
            internal = operations.list_rejects("2026-09-01", "2026-09-03")["rejects"]
            self.assertEqual(len(internal), 1)
            self.assertEqual(internal[0]["source_type"], "aw")
            self.assertEqual(internal[0]["reason_label"], "Broke in Machine")
            self.assertEqual(internal[0]["location_label"], "Grinding")
            self.assertEqual(int(internal[0]["scan_qty_reduced"]), 0)

            # A code-based mapping updates the current mirror and survives an A+W
            # source-label rename because the numeric code remains authoritative.
            store.update_reject_value_mapping("location", 5, "Polisher", "admin")
            self.assertEqual(operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]["location_label"], "Polisher")
            refreshed = {
                **row,
                "locationLabel": "Grinding Station",
                "sourceLastChangedAt": "2026-09-02T10:00:00.0000000",
            }
            store.sync_aw_reject_rows([refreshed])
            self.assertEqual(operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]["location_label"], "Polisher")
            mapping = next(value for value in store.list_reject_value_mappings() if value["kind"] == "location" and value["sourceCode"] == 5)
            self.assertEqual(mapping["sourceLabel"], "Grinding Station")
            self.assertEqual(mapping["mappedLabel"], "Polisher")

            # An individual historical correction is a scanner-side override and
            # must not be erased by source refreshes or later code-map changes.
            reject_id = int(operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]["id"])
            operations.update_reject(
                {
                    "id": reject_id,
                    "reason": "Reviewed breakage",
                    "location": "Special Polisher",
                    "notes": "Corrected after investigation",
                    "qty": 2,
                    "rejectedAt": "2026-09-01T15:30:00+00:00",
                },
                "admin",
            )
            store.update_reject_value_mapping("location", 5, "Polisher 2", "admin")
            store.sync_aw_reject_rows([{**refreshed, "locationLabel": "Grinding Updated", "sourceLastChangedAt": "2026-09-02T11:00:00.0000000"}])
            overridden = operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]
            self.assertEqual(overridden["reason_label"], "Reviewed breakage")
            self.assertEqual(overridden["location_label"], "Special Polisher")
            self.assertEqual(int(overridden["qty"]), 2)
            self.assertEqual(overridden["notes"], "Corrected after investigation")

            # Deliberate bulk replacements work for both dimensions and update
            # the associated A+W code mappings so future synchronization keeps them.
            reason_bulk = operations.bulk_relabel_rejects("reason", "Reviewed breakage", "Investigated breakage", "admin")
            self.assertEqual(reason_bulk["affectedEvents"], 1)
            self.assertIn(137, reason_bulk["awCodes"])
            self.assertEqual(operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]["reason_label"], "Investigated breakage")

            bulk = operations.bulk_relabel_rejects("location", "Special Polisher", "Polisher Bay", "admin")
            self.assertEqual(bulk["affectedEvents"], 1)
            self.assertIn(5, bulk["awCodes"])
            after_bulk = operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]
            self.assertEqual(after_bulk["location_label"], "Polisher Bay")
            self.assertEqual(json.loads(after_bulk["manual_override_json"])["location"], "Polisher Bay")
            store.sync_aw_reject_rows([{**refreshed, "locationLabel": "Grinding New Name", "sourceLastChangedAt": "2026-09-02T12:00:00.0000000"}])
            final_reject = operations.list_rejects("2026-09-01", "2026-09-03")["rejects"][0]
            self.assertEqual(final_reject["location_label"], "Polisher Bay")
            self.assertEqual(final_reject["reason_label"], "Investigated breakage")
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()
            if verification_root.exists():
                shutil.rmtree(verification_root, ignore_errors=True)

    def test_egl_history_remains_fabrication_evidence_after_file_deletion_and_restart(self) -> None:
        verification_root = ROOT / "_verification_egl_history_v485"
        shutil.rmtree(verification_root, ignore_errors=True)
        data_dir = verification_root / "data"
        programs = verification_root / "Programs"
        sketches = verification_root / "Sketches"
        hardware = verification_root / "Hardware"
        completed = verification_root / "Completed WJ"
        for folder in (data_dir, programs, sketches, hardware, completed):
            folder.mkdir(parents=True, exist_ok=True)
        try:
            base = load_config(ROOT)
            config = replace(
                base,
                root=verification_root,
                data_dir=data_dir,
                programs_dir=programs,
                sketches_dir=sketches,
                hardware_lists_dir=hardware,
                completed_wj_dir=completed,
            )
            egl = programs / "23809101-test.egl"
            egl.write_text("DENVER TEST PROGRAM", encoding="utf-8")
            service = ProductionFileService(config, cache_seconds=15)
            service.assets("program", refresh=True)
            live = service.fabrication_status("238091", "1", "6455")
            self.assertTrue(live["fabricated"])
            self.assertFalse(live["evidence"]["historical"])
            self.assertTrue(live["evidence"]["existsNow"])
            service._persist_index()

            egl.unlink()
            service.assets("program", refresh=True)
            historical = service.fabrication_status("238091", "1", "6455")
            self.assertTrue(historical["fabricated"])
            self.assertTrue(historical["evidence"]["historical"])
            self.assertFalse(historical["evidence"]["existsNow"])
            self.assertEqual(historical["programs"], [])
            service._persist_index()

            restarted = ProductionFileService(config, cache_seconds=15)
            after_restart = restarted.fabrication_status("238091", "1", "6455")
            self.assertTrue(after_restart["fabricated"])
            self.assertTrue(after_restart["evidence"]["historical"])
            self.assertEqual(restarted.index_status()["historicalEglCount"], 1)
            self.assertIsNone(restarted.resolve_asset(after_restart["evidence"]["id"]))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_internal_reject_requires_newer_or_overwritten_fabrication_evidence(self) -> None:
        verification_root = ROOT / "_verification_reject_fabrication_reset_v486"
        shutil.rmtree(verification_root, ignore_errors=True)
        data_dir = verification_root / "data"
        programs = verification_root / "Programs"
        sketches = verification_root / "Sketches"
        hardware = verification_root / "Hardware"
        completed = verification_root / "Completed WJ"
        for folder in (data_dir, programs, sketches, hardware, completed):
            folder.mkdir(parents=True, exist_ok=True)
        try:
            base = load_config(ROOT)
            config = replace(
                base,
                root=verification_root,
                data_dir=data_dir,
                programs_dir=programs,
                sketches_dir=sketches,
                hardware_lists_dir=hardware,
                completed_wj_dir=completed,
            )
            egl = programs / "23809101-test.egl"
            egl.write_text("ORIGINAL DENVER PROGRAM", encoding="utf-8")
            # Keep the synthetic evidence comfortably inside the maintained
            # seven-day production-file index. A fixed September 1 timestamp
            # made this regression expire exactly one week later even though
            # the reject/reset behavior itself was still correct.
            now_utc = datetime.now(timezone.utc)
            before_reject_dt = now_utc - timedelta(hours=2)
            reject_dt = now_utc - timedelta(hours=1)
            after_reject_dt = now_utc - timedelta(minutes=30)
            before_reject = before_reject_dt.timestamp()
            os.utime(egl, (before_reject, before_reject))
            service = ProductionFileService(config, cache_seconds=15)
            service.assets("program", refresh=True)
            reject_time = reject_dt.isoformat()

            stale = service.fabrication_status("238091", "1", "6455", evidence_after=reject_time)
            self.assertFalse(stale["fabricated"])
            self.assertTrue(stale["evidenceResetRequired"])
            self.assertIsNotNone(stale["staleEvidence"])
            self.assertIsNone(stale["evidence"])

            # Overwriting the exact same program after the reject creates new
            # fabrication evidence even though the filename did not change.
            egl.write_text("RE-FABRICATED DENVER PROGRAM", encoding="utf-8")
            after_reject = after_reject_dt.timestamp()
            os.utime(egl, (after_reject, after_reject))
            service.assets("program", refresh=True)
            refreshed = service.fabrication_status("238091", "1", "6455", evidence_after=reject_time)
            self.assertTrue(refreshed["fabricated"])
            self.assertGreater(float(refreshed["evidence"]["modifiedAt"]), before_reject)
            self.assertIsNone(refreshed["staleEvidence"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_reject_source_identity_change_does_not_replay_rollback(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_rekey_v486"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-02", "items": [imported_item("238092", "1", 1, "aw-reject:rekey")]},
                "fileName": "Delivery List 09-02-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as con:
                con.execute("UPDATE line_items SET scanned_qty=1 WHERE order_no='238092' AND item_no='001'")
                con.commit()
            row = {
                "awRowId": "stable-source-guid", "orderNr": "238092", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-01T15:27:42+00:00", "originalJobNumber": "6456",
                "reasonCode": 137, "reasonLabel": "Broke in Machine", "locationCode": 5,
                "locationLabel": "Grinding", "fromScanner": 1, "breakageUser": "A+W User",
            }
            store.sync_aw_reject_rows([row])
            with store.connect() as con:
                self.assertTrue(all(int(value[0] or 0) == 0 for value in con.execute(
                    "SELECT scanned_qty FROM line_items WHERE order_no='238092' AND item_no='001'"
                ).fetchall()))
                con.execute("UPDATE line_items SET scanned_qty=1 WHERE order_no='238092' AND item_no='001'")
                con.commit()

            # A+W corrects the timestamp, which changes the logical event key,
            # but the preserved raw ROWID proves the rollback already happened.
            store.sync_aw_reject_rows([{**row, "breakageDate": "2026-09-01T15:27:43+00:00"}])
            with store.connect() as con:
                states = con.execute(
                    "SELECT scanned_qty FROM line_items WHERE order_no='238092' AND item_no='001'"
                ).fetchall()
                reset_count = con.execute("SELECT COUNT(*) FROM scan_events WHERE event_type='reject_reset'").fetchone()[0]
                mirror = con.execute("SELECT scan_qty_reduced, operational_rollback_applied_at FROM reject_events WHERE source_type='aw'").fetchone()
            self.assertTrue(all(int(value["scanned_qty"] or 0) == 1 for value in states))
            self.assertGreater(int(reset_count or 0), 0)
            self.assertGreater(int(mirror["scan_qty_reduced"] or 0), 0)
            self.assertTrue(str(mirror["operational_rollback_applied_at"] or ""))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_reject_operational_reset_removes_rack_and_bay_quantity(self) -> None:
        verification_root = ROOT / "_verification_aw_reject_rack_bay_v486"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                store.seed_bays(con)
                store.seed_racks(con)
                con.commit()
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-02", "items": [imported_item("238093", "1", 1, "aw-reject:rack-bay")]},
                "fileName": "Delivery List 09-02-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as con:
                lines = con.execute(
                    "SELECT id, list_id FROM line_items WHERE order_no='238093' AND item_no='001' ORDER BY id"
                ).fetchall()
                self.assertGreaterEqual(len(lines), 2)
                con.execute("UPDATE line_items SET scanned_qty=1 WHERE order_no='238093' AND item_no='001'")
                rack = con.execute("SELECT id FROM racks WHERE active=1 ORDER BY id LIMIT 1").fetchone()
                bay = con.execute("SELECT id FROM bays WHERE active=1 ORDER BY id LIMIT 1").fetchone()
                self.assertIsNotNone(rack)
                self.assertIsNotNone(bay)
                con.execute(
                    "INSERT INTO rack_items (rack_id,line_item_id,qty,status,added_by,added_at,reason,destination_override) VALUES (?,?,1,'Active','tester','2026-09-01T14:00:00+00:00','test','')",
                    (rack["id"], lines[0]["id"]),
                )
                con.execute(
                    "INSERT INTO bay_assignments (delivery_list_id,line_item_id,bay_id,assigned_qty,status,assigned_by,assigned_at,reason) VALUES (?,?,?,1,'Received','tester','2026-09-01T14:00:00+00:00','test')",
                    (lines[1]["list_id"], lines[1]["id"], bay["id"]),
                )
                con.commit()
            store.sync_aw_reject_rows([{
                "awRowId": "rack-bay-source", "orderNr": "238093", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "subPosition": 0, "quantity": 1,
                "breakageDate": "2026-09-01T15:27:42+00:00", "originalJobNumber": "6457",
                "reasonCode": 137, "reasonLabel": "Broke in Machine", "locationCode": 5,
                "locationLabel": "Grinding", "fromScanner": 1, "breakageUser": "A+W User",
            }])
            with store.connect() as con:
                rack_row = con.execute("SELECT qty,status,reason FROM rack_items WHERE line_item_id=?", (lines[0]["id"],)).fetchone()
                bay_row = con.execute("SELECT assigned_qty,status,reason FROM bay_assignments WHERE line_item_id=?", (lines[1]["id"],)).fetchone()
            # rack_items preserves the positive historical quantity and uses
            # status=Removed to represent zero active allocation.
            self.assertEqual(int(rack_row["qty"] or 0), 1)
            self.assertEqual(str(rack_row["status"]), "Removed")
            self.assertEqual(str(rack_row["reason"]), "A+W Internal reject")
            self.assertEqual(int(bay_row["assigned_qty"] or 0), 0)
            self.assertEqual(str(bay_row["status"]), "Cleared")
            self.assertEqual(str(bay_row["reason"]), "A+W Internal reject")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_manual_internal_reject_preserves_removed_rack_history(self) -> None:
        verification_root = ROOT / "_verification_manual_reject_rack_history_v486"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            operations = OperationsFeatureService(store, store.config, verification_root)
            with store.connect() as con:
                store.seed_bays(con)
                store.seed_racks(con)
                con.commit()
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-02", "items": [imported_item("238094", "1", 1, "manual-reject:rack-bay")]},
                "fileName": "Delivery List 09-02-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as con:
                lines = con.execute(
                    "SELECT id, list_id FROM line_items WHERE order_no='238094' AND item_no='001' ORDER BY id"
                ).fetchall()
                self.assertGreaterEqual(len(lines), 2)
                con.execute("UPDATE line_items SET scanned_qty=1 WHERE order_no='238094' AND item_no='001'")
                rack = con.execute("SELECT id FROM racks WHERE active=1 ORDER BY id LIMIT 1").fetchone()
                bay = con.execute("SELECT id FROM bays WHERE active=1 ORDER BY id LIMIT 1").fetchone()
                con.execute(
                    "INSERT INTO rack_items (rack_id,line_item_id,qty,status,added_by,added_at,reason,destination_override) VALUES (?,?,1,'Active','tester','2026-09-01T14:00:00+00:00','test','')",
                    (rack["id"], lines[0]["id"]),
                )
                con.execute(
                    "INSERT INTO bay_assignments (delivery_list_id,line_item_id,bay_id,assigned_qty,status,assigned_by,assigned_at,reason) VALUES (?,?,?,1,'Received','tester','2026-09-01T14:00:00+00:00','test')",
                    (lines[1]["list_id"], lines[1]["id"], bay["id"]),
                )
                con.commit()

            operations.create_reject(
                {
                    "deliveryDate": "2026-09-02",
                    "order": "238094",
                    "item": "1",
                    "qty": 1,
                    "reason": "Test Reject",
                    "location": "Test Station",
                },
                "tester",
            )
            with store.connect() as con:
                rack_row = con.execute(
                    "SELECT qty,status,reason FROM rack_items WHERE line_item_id=?", (lines[0]["id"],)
                ).fetchone()
                bay_row = con.execute(
                    "SELECT assigned_qty,status,reason FROM bay_assignments WHERE line_item_id=?", (lines[1]["id"],)
                ).fetchone()
            self.assertEqual(int(rack_row["qty"] or 0), 1)
            self.assertEqual(str(rack_row["status"]), "Removed")
            self.assertEqual(str(rack_row["reason"]), "Internal reject")
            self.assertEqual(int(bay_row["assigned_qty"] or 0), 0)
            self.assertEqual(str(bay_row["status"]), "Cleared")
            self.assertEqual(str(bay_row["reason"]), "Internal reject")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_automation_reject_sync_settings_round_trip(self) -> None:
        verification_root = ROOT / "_verification_automation_reject_settings_v485"
        shutil.rmtree(verification_root, ignore_errors=True)
        config_dir = verification_root / "automation" / "sql_delivery_export"
        config_dir.mkdir(parents=True, exist_ok=True)
        source_config = ROOT / "automation" / "sql_delivery_export" / "sql-export.config.json"
        config_path = config_dir / "sql-export.config.json"
        config_payload = json.loads(source_config.read_text(encoding="utf-8")) if source_config.is_file() else automation_test_config_payload(verification_root / "runtime")
        config_path.write_text(json.dumps(config_payload, indent=2) + "\n", encoding="utf-8")
        base = load_config(ROOT)
        scanner_config = replace(base, root=verification_root, data_dir=verification_root / "data")
        try:
            with mock.patch.dict(os.environ, {"DLS_SQL_EXPORT_CONFIG": str(config_path)}), \
                 mock.patch.object(DeliveryAutomationController, "_refresh_runtime_scripts_if_safe", return_value=[]), \
                 mock.patch.object(DeliveryAutomationController, "_schedule_installed", return_value=False):
                controller = DeliveryAutomationController(verification_root, scanner_config, None)
                dashboard = controller.get_dashboard()
                self.assertTrue(dashboard["settings"]["rejectSyncEnabled"])
                self.assertEqual(dashboard["settings"]["rejectIncrementalPastDays"], 30)
                self.assertEqual(dashboard["settings"]["rejectFullPastDays"], 365)
                payload = dict(dashboard["settings"])
                payload.update({
                    "automationMode": "sql-export-and-import",
                    "rejectSyncEnabled": False,
                    "rejectIncrementalPastDays": 45,
                    "rejectFullPastDays": 730,
                })
                saved = controller.save_settings(payload, "admin")
                self.assertFalse(saved["settings"]["rejectSyncEnabled"])
                self.assertEqual(saved["settings"]["rejectIncrementalPastDays"], 45)
                self.assertEqual(saved["settings"]["rejectFullPastDays"], 730)
                persisted = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(persisted["RejectSync"], {"Enabled": False, "IncrementalPastDays": 45, "FullPastDays": 730})
                payload["rejectFullPastDays"] = 10
                with self.assertRaisesRegex(ValueError, "cannot be shorter"):
                    controller.save_settings(payload, "admin")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_automation_dashboard_recovers_orphaned_web_gui_running_state(self) -> None:
        """A dead manual child must not keep Status & Logs yellow forever."""
        verification_root = ROOT / "_verification_automation_stale_run_v503"
        shutil.rmtree(verification_root, ignore_errors=True)
        config_dir = verification_root / "automation" / "sql_delivery_export"
        runtime_root = verification_root / "runtime"
        state_dir = runtime_root / "State"
        logs_dir = runtime_root / "Logs"
        config_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        source_config = ROOT / "automation" / "sql_delivery_export" / "sql-export.config.json"
        config_payload = json.loads(source_config.read_text(encoding="utf-8")) if source_config.is_file() else automation_test_config_payload(runtime_root)
        config_payload["WorkingRoot"] = str(runtime_root)
        config_path = config_dir / "sql-export.config.json"
        config_path.write_text(json.dumps(config_payload, indent=2) + "\n", encoding="utf-8")

        task_id = "stale503test"
        log_path = logs_dir / f"web-gui-{task_id}.log"
        log_path.write_text("controller launched PowerShell\n", encoding="utf-8")
        stale_status = {
            "taskId": task_id,
            "running": True,
            "action": "sql-export-and-import",
            "startedAt": "2026-09-03T14:44:36+00:00",
            "message": "Delivery-list automation started.",
            "currentStep": "Reading A+W delivery rows for 2026-09-10",
            "logPath": str(log_path),
            "summaryPath": str(state_dir / "web-gui-summary.json"),
            "runOrigin": "manual",
        }
        (state_dir / "web-gui-run.json").write_text(
            json.dumps(stale_status, indent=2) + "\n", encoding="utf-8"
        )

        base = load_config(ROOT)
        scanner_config = replace(base, root=verification_root, data_dir=verification_root / "data")
        try:
            with mock.patch.dict(os.environ, {"DLS_SQL_EXPORT_CONFIG": str(config_path)}), \
                 mock.patch.object(DeliveryAutomationController, "_refresh_runtime_scripts_if_safe", return_value=[]), \
                 mock.patch.object(DeliveryAutomationController, "_schedule_installed", return_value=False):
                controller = DeliveryAutomationController(verification_root, scanner_config, None)
                dashboard = controller.get_dashboard()

            self.assertFalse(dashboard["running"])
            self.assertFalse(dashboard["lastRun"]["running"])
            self.assertFalse(dashboard["lastRun"]["succeeded"])
            self.assertTrue(dashboard["lastRun"]["recoveredStaleRun"])
            self.assertIn("stale Running status was cleared automatically", dashboard["lastRun"]["currentStep"])

            persisted = json.loads((state_dir / "web-gui-run.json").read_text(encoding="utf-8"))
            self.assertFalse(persisted["running"])
            self.assertTrue(persisted["recoveredStaleRun"])
            self.assertIn("stale Running status was cleared automatically", log_path.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_automation_gui_status_retries_replace_without_losing_valid_json(self) -> None:
        """A transient Windows file lock must not stop the automation output worker."""
        verification_root = ROOT / "_verification_automation_status_v510"
        shutil.rmtree(verification_root, ignore_errors=True)
        state_dir = verification_root / "State"
        state_dir.mkdir(parents=True, exist_ok=True)
        status_path = state_dir / "web-gui-run.json"
        controller = DeliveryAutomationController.__new__(DeliveryAutomationController)
        controller._gui_status_lock = threading.Lock()
        status = {"taskId": "status-v510", "running": True, "currentStep": "Import complete"}
        real_replace = os.replace
        attempts = 0

        def transient_replace(source, destination):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise PermissionError(errno.EACCES, "temporary sharing violation")
            return real_replace(source, destination)

        try:
            with mock.patch.object(
                controller,
                "_runtime_paths",
                return_value={"gui_run": status_path},
            ), mock.patch(
                "backend.automation_control.os.replace",
                side_effect=transient_replace,
            ), mock.patch("backend.automation_control.time.sleep") as mocked_sleep:
                self.assertTrue(controller._write_gui_status({}, status))

            self.assertEqual(attempts, 2)
            mocked_sleep.assert_called_once()
            self.assertEqual(json.loads(status_path.read_text(encoding="utf-8")), status)
            self.assertEqual(list(state_dir.glob("*.tmp")), [])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

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

            # v0.533: completed/inactive work is still historical truth. Smart
            # Search must not hide it just because the delivery list is no longer
            # active, and an exact order search must continue to resolve it.
            with store.connect() as connection:
                connection.execute(
                    "UPDATE line_items SET scanned_qty = qty WHERE order_no IN (?, ?)",
                    (rush["order"], missing["order"]),
                )
                connection.execute(
                    "UPDATE delivery_lists SET status = 'inactive' WHERE delivery_date = ?",
                    (delivery_date,),
                )
                connection.commit()
            inactive_rush_results = store.global_search("rush")
            self.assertIn(rush["order"], [row["order"] for row in inactive_rush_results])
            self.assertIn(missing["order"], [row["order"] for row in inactive_rush_results])
            self.assertEqual(store.global_search(rush["order"])[0]["order"], rush["order"])

            # Equal-relevance text matches are ordered newest first.
            newer = imported_item("273099", "1", 1, "v0533-search:newer")
            newer["customer"] = "ALPHA BUILDERS"
            store.import_delivery_list(
                {
                    "payload": {"deliveryDate": "2026-10-02", "items": [newer]},
                    "fileName": "Delivery List 10-02-2026.xlsx",
                    "user": "admin",
                }
            )
            alpha_results = store.global_search("alpha")
            self.assertGreaterEqual(len(alpha_results), 2)
            self.assertEqual(alpha_results[0]["order"], newer["order"])
            self.assertIn(rush["order"], [row["order"] for row in alpha_results])
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

    def test_v0541_staging_fabrication_override_waits_for_success_and_is_audited(self) -> None:
        """A confirmed Staging override must save only after rack/destination gates accept the scan."""
        verification_root = ROOT / "_verification_v0541_fabrication_override"
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
            with store.connect() as connection:
                store.seed_racks(connection)
                racks = connection.execute(
                    "SELECT id, rack_code FROM racks WHERE active = 1 ORDER BY id LIMIT 2"
                ).fetchall()
                self.assertGreaterEqual(len(racks), 2)
                open_rack = str(racks[0]["rack_code"])
                blocked_rack = str(racks[1]["rack_code"])
                connection.execute("UPDATE racks SET status='Completed' WHERE id=?", (racks[1]["id"],))
                connection.commit()

            config = replace(
                store.config,
                hardware_lists_dir=hardware_dir,
                sketches_dir=sketches_dir,
                programs_dir=programs_dir,
                completed_wj_dir=completed_wj_dir,
            )
            store.production_files = ProductionFileService(config)
            item = imported_item("279471", "1", 1, "v0541-fabrication-override:1")
            item["job"] = "88279471 FAB OVERRIDE"
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-19", "items": [item]},
                "fileName": "Delivery List 10-19-2026.xlsx",
                "user": "admin",
            })
            (sketches_dir / "279471-001 Sketch.txt").write_text("Assigned Machine: Denver CNC", encoding="utf-8")
            store.production_files = ProductionFileService(config)

            blocked = store.record_scan({
                "listId": "2026-10-19-staging-airport",
                "barcode": item["barcode"],
                "rackCode": blocked_rack,
                "fabricationOverride": True,
                "user": "admin",
                "station": "Airport Rd",
            })
            self.assertFalse(blocked["lastScan"]["ok"])
            with store.connect() as connection:
                saved = connection.execute(
                    "SELECT COUNT(*) FROM manual_production_progress_overrides WHERE order_no=? AND item_no=?",
                    ("279471", "001"),
                ).fetchone()[0]
            self.assertEqual(int(saved), 0)

            overridden = store.record_scan({
                "listId": "2026-10-19-staging-airport",
                "barcode": item["barcode"],
                "rackCode": open_rack,
                "fabricationOverride": True,
                "user": "admin",
                "station": "Airport Rd",
            })
            self.assertTrue(overridden["lastScan"]["ok"])
            self.assertNotIn("fabricationGate", overridden)
            override_hints = store.aw_fabrication_hints_for_requests([{
                "order": "279471", "item": "001", "job": item["job"],
                "deliveryDate": "2026-10-19", "key": "override-check",
            }])
            self.assertTrue(override_hints["override-check"]["manualMachineComplete"])
            self.assertEqual(override_hints["override-check"]["manualMachineCode"], "denver")
            with store.connect() as connection:
                audit = connection.execute(
                    "SELECT id FROM audit_events WHERE action='staging_fabrication_override' ORDER BY id DESC LIMIT 1"
                ).fetchone()
                self.assertIsNotNone(audit)
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
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=hardware_dir,
                sketches_dir=sketches_dir,
                programs_dir=programs_dir,
                completed_wj_dir=completed_wj_dir,
            )
            config.data_dir.mkdir()
            (sketches_dir / "279471-001 Sketch.txt").write_text("Assigned machine: WATER JET", encoding="utf-8")
            service = ProductionFileService(config)
            missing = service.fabrication_status("279471", "001", "88279471")
            self.assertEqual(missing["machine"], "Waterjet")
            self.assertTrue(missing["blockStaging"])

            (completed_wj_dir / "279471-001 Complete.nce").write_text("complete", encoding="utf-8")
            service = ProductionFileService(config)
            complete = service.fabrication_status("279471", "001", "88279471")
            self.assertTrue(complete["fabricated"])
            self.assertFalse(complete["blockStaging"])

            missing_root = verification_root / "Disconnected Completed WJ"
            disconnected_config = replace(config, completed_wj_dir=missing_root)
            disconnected = ProductionFileService(disconnected_config).fabrication_status("279471", "001", "88279471")
            self.assertEqual(disconnected["machine"], "Waterjet")
            self.assertTrue(disconnected["fabricated"])
            self.assertFalse(disconnected["blockStaging"])

            # With no prior completion memory, an unavailable completion share
            # remains unknown and non-enforceable rather than creating a false block.
            (sketches_dir / "279472-001 Sketch.txt").write_text("Assigned machine: WATER JET", encoding="utf-8")
            unknown = ProductionFileService(disconnected_config).fabrication_status("279472", "001", "88279472")
            self.assertEqual(unknown["machine"], "Waterjet")
            self.assertIsNone(unknown["fabricated"])
            self.assertFalse(unknown["enforceable"])
            self.assertFalse(unknown["blockStaging"])
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
                    "lookbackDays": 7,
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
            self.assertEqual(saved["lookbackDays"], 7)
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
            # v0.474 no-content checks intentionally do not parse sketch files;
            # exact assignment is resolved lazily when the order/item is opened.
            self.assertEqual(fast_status["assignedMachine"], "")
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
        with mock.patch.object(Path, "stat", side_effect=FileNotFoundError("disconnected mapped drive")):
            available, reason = service._probe_root("sketch", Path("I:/Production/Sketches"))
        self.assertFalse(available)
        self.assertIn("Mapped drive not reachable", reason)


    def test_v0473_production_index_uses_recent_window_and_waterjet_nce_evidence(self) -> None:
        """Production indexing ignores old files and only .nce proves Waterjet completion."""
        verification_root = ROOT / "_verification_v0473_recent_production"
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
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=hardware_dir,
                sketches_dir=sketches_dir,
                programs_dir=programs_dir,
                completed_wj_dir=completed_wj_dir,
            )
            config.data_dir.mkdir()
            recent_program = programs_dir / "279474-001.egl"
            old_program = programs_dir / "279475-001.egl"
            recent_wj = completed_wj_dir / "279476-001.nce"
            unrelated_wj = completed_wj_dir / "279476-001.dxf"
            for path in (recent_program, old_program, recent_wj, unrelated_wj):
                path.write_text(path.suffix, encoding="utf-8")
            old_timestamp = time.time() - (9 * 86400)
            os.utime(old_program, (old_timestamp, old_timestamp))

            service = ProductionFileService(config)
            with mock.patch.object(service, "refresh_async"):
                service.configure({"lookbackDays": 7, "cacheMinutes": 5})
            program_names = {asset.name for asset in service.assets("program", refresh=True)}
            waterjet_names = {asset.name for asset in service.assets("completed_wj", refresh=True)}
            self.assertIn(recent_program.name, program_names)
            self.assertNotIn(old_program.name, program_names)
            self.assertEqual(waterjet_names, {recent_wj.name})

            # Expanding the Admin window makes the older Denver evidence eligible
            # without changing any file or database content.
            with mock.patch.object(service, "refresh_async"):
                service.configure({"lookbackDays": 10, "cacheMinutes": 5})
            expanded_names = {asset.name for asset in service.assets("program", refresh=True)}
            self.assertIn(old_program.name, expanded_names)
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)


    def test_v0473_recent_index_prunes_old_directory_subtrees(self) -> None:
        """The recent production index must not recurse through known-old history trees."""
        verification_root = ROOT / "_verification_v0473_pruned_tree"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        programs_dir = verification_root / "Programs"
        recent_dir = programs_dir / "Recent"
        archive_dir = programs_dir / "Archive"
        recent_dir.mkdir(parents=True)
        (archive_dir / "2024" / "January").mkdir(parents=True)
        (recent_dir / "279477-001.egl").write_text("recent", encoding="utf-8")
        (archive_dir / "2024" / "January" / "199999-001.egl").write_text("old", encoding="utf-8")
        old_timestamp = time.time() - (30 * 86400)
        for old_folder in (archive_dir / "2024" / "January", archive_dir / "2024", archive_dir):
            os.utime(old_folder, (old_timestamp, old_timestamp))
        try:
            config = replace(
                load_config(ROOT),
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=verification_root / "Hardware Lists",
                sketches_dir=verification_root / "Sketches",
                programs_dir=programs_dir,
                completed_wj_dir=verification_root / "Completed WJ",
            )
            for folder in (config.data_dir, config.hardware_lists_dir, config.sketches_dir, config.completed_wj_dir):
                Path(folder).mkdir(parents=True, exist_ok=True)
            service = ProductionFileService(config)
            service.configure({"lookbackDays": 7, "cacheMinutes": 5})
            original_scandir = os.scandir
            visited: list[str] = []

            def tracking_scandir(path):
                visited.append(os.path.normcase(os.path.normpath(str(path))))
                return original_scandir(path)

            with mock.patch("backend.production_files.os.scandir", side_effect=tracking_scandir):
                names = {asset.name for asset in service.assets("program", refresh=True)}

            self.assertEqual(names, {"279477-001.egl"})
            archive_key = os.path.normcase(os.path.normpath(str(archive_dir)))
            self.assertNotIn(archive_key, visited, "Old production history was recursively opened")
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)


    def test_v0474_sketch_pages_assign_exact_items_and_program_names(self) -> None:
        """Order-level sketch PDFs map machines by Order.Item page markers; programs use Order+2-digit Item."""
        verification_root = ROOT / "_verification_v0474_sketch_contract"
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
            from reportlab.pdfgen import canvas

            sketch = sketches_dir / "238245 Sketch.pdf"
            pdf = canvas.Canvas(str(sketch))
            pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(220, 400, "238245.1")
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(210, 410, "238245.2")
            pdf.drawString(250, 380, "WJ")
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(200, 410, "238245.3")
            pdf.drawString(220, 380, "DENVER 1")
            pdf.save()
            (programs_dir / "23824503.egl").write_text("Denver complete", encoding="utf-8")
            (programs_dir / "23824502.egl").write_text("wrong machine evidence", encoding="utf-8")
            (completed_wj_dir / "23824502.nce").write_text("Waterjet complete", encoding="utf-8")

            config = replace(
                load_config(ROOT),
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=hardware_dir,
                sketches_dir=sketches_dir,
                programs_dir=programs_dir,
                completed_wj_dir=completed_wj_dir,
            )
            config.data_dir.mkdir()
            service = ProductionFileService(config)

            item2 = service.item_assets("238245", "2", "")
            self.assertEqual(len(item2["sketches"]), 1)
            self.assertEqual(item2["sketches"][0]["pageNumber"], 2)
            self.assertEqual(item2["sketches"][0]["itemMarker"], "238245.2")
            self.assertEqual(item2["sketches"][0]["machineHint"], "Waterjet")
            self.assertEqual(item2["fabrication"]["assignedMachine"], "Waterjet")
            self.assertEqual(item2["fabrication"]["actualMachine"], "Waterjet")
            self.assertTrue(item2["fabrication"]["fabricated"])

            item3 = service.item_assets("238245", "3", "")
            self.assertEqual(item3["sketches"][0]["pageNumber"], 3)
            self.assertEqual(item3["sketches"][0]["machineHint"], "Denver CNC")
            self.assertEqual([row["name"] for row in item3["programs"]], ["23824503.egl"])
            self.assertTrue(item3["fabrication"]["fabricated"])
            self.assertEqual(item3["fabrication"]["actualMachine"], "Denver CNC")

            item1 = service.fabrication_status("238245", "1", "")
            self.assertTrue(item1["sketchMatched"])
            self.assertEqual(item1["assignedMachine"], "")
            self.assertIsNone(item1["fabricated"])
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0474_background_sketch_index_never_parses_pdf_content(self) -> None:
        """Recent sketch refresh is metadata-only; machine parsing occurs only for a requested order."""
        verification_root = ROOT / "_verification_v0474_metadata_only_index"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        sketches_dir = verification_root / "Sketches"
        sketches_dir.mkdir()
        (sketches_dir / "238245 Sketch.pdf").write_bytes(b"%PDF-1.4 metadata fixture")
        try:
            config = replace(
                load_config(ROOT),
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=verification_root / "Hardware Lists",
                sketches_dir=sketches_dir,
                programs_dir=verification_root / "Programs",
                completed_wj_dir=verification_root / "Completed WJ",
            )
            for folder in (config.data_dir, config.hardware_lists_dir, config.programs_dir, config.completed_wj_dir):
                Path(folder).mkdir(parents=True, exist_ok=True)
            service = ProductionFileService(config)
            with mock.patch.object(service, "_sketch_page_assignments", side_effect=AssertionError("index parsed sketch PDF")):
                names = {asset.name for asset in service.assets("sketch", refresh=True)}
            self.assertEqual(names, {"238245 Sketch.pdf"})
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v515_sketch_transient_read_and_stale_index_recover(self) -> None:
        """A temporary PDF read miss must not become a durable Order Details miss."""
        verification_root = ROOT / "_verification_v515_sketch_retry"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir()
        sketches_dir = verification_root / "Sketches"
        sketches_dir.mkdir()
        try:
            from reportlab.pdfgen import canvas
            from pypdf import PdfReader as RealPdfReader

            sketch = sketches_dir / "238455 Sketch.pdf"
            pdf = canvas.Canvas(str(sketch))
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(210, 410, "238455.1")
            pdf.drawString(230, 380, "DENVER 2")
            pdf.save()

            config = replace(
                load_config(ROOT),
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=verification_root / "Hardware Lists",
                sketches_dir=sketches_dir,
                programs_dir=verification_root / "Programs",
                completed_wj_dir=verification_root / "Completed WJ",
            )
            for folder in (config.data_dir, config.hardware_lists_dir, config.programs_dir, config.completed_wj_dir):
                Path(folder).mkdir(parents=True, exist_ok=True)
            service = ProductionFileService(config)
            asset = service.matches("sketch", "238455", "", "", limit=8, require_item=False)[0]
            calls = 0

            def flaky_reader(path):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise OSError("network PDF still being copied")
                return RealPdfReader(path)

            with mock.patch.object(service, "_prime_sketch_preview_pages_async"), \
                 mock.patch("pypdf.PdfReader", side_effect=flaky_reader):
                self.assertEqual(service.sketch_item_views("238455", "1", ""), [])
                self.assertNotIn(asset.asset_id, service._sketch_page_cache)
                recovered = service.sketch_item_views("238455", "1", "")
            self.assertEqual(calls, 2)
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0]["pageNumber"], 1)
            self.assertEqual(recovered[0]["itemMarker"], "238455.1")
            self.assertEqual(recovered[0]["machineHint"], "Denver CNC")

            with mock.patch.object(service, "matches", return_value=[]), \
                 mock.patch.object(service, "_is_network_root", return_value=True), \
                 mock.patch.object(service, "refresh_async") as refresh_async:
                self.assertEqual(service.sketch_item_views("238999", "1", ""), [])
                refresh_async.assert_called_once_with(["sketch"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0475_global_search_reports_physical_stage_progress_once(self) -> None:
        """Smart Search receives one progress record per synchronized stage, not duplicated stage rows."""
        verification_root = ROOT / "_verification_v0475_search_progress"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        try:
            store = self.make_store(verification_root)
            order = "279475"
            delivery_date = "2026-09-08"
            item = imported_item(order, "1", 2, "v0475-progress:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": delivery_date, "items": [item]},
                "fileName": "Delivery List 09-08-2026.xlsx",
                "user": "admin",
            })
            match = next(row for row in store.global_search(order) if row["order"] == order)
            stages = match.get("progressStages") or []
            presets = {row.get("stagePreset"): row for row in stages}
            self.assertIn("airport_staging", presets)
            self.assertIn("airport_outbound", presets)
            self.assertEqual(presets["airport_staging"]["qty"], 2)
            self.assertEqual(presets["airport_staging"]["scanned"], 0)
            self.assertEqual(presets["airport_outbound"]["qty"], 2)
            self.assertEqual(presets["airport_outbound"]["scanned"], 0)
            self.assertEqual(len(stages), len({row.get("stagePreset") for row in stages}))
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0513_global_search_attaches_current_cutting_state_after_final_match(self) -> None:
        """Smart Search enriches only its final result set with the current A+W Cutting generation."""
        verification_root = ROOT / "_verification_v0513_search_cutting"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        try:
            store = self.make_store(verification_root)
            order = "279513"
            delivery_date = "2026-09-08"
            item = imported_item(order, "1", 1, "v0513-cutting:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": delivery_date, "items": [item]},
                "fileName": "Delivery List 09-08-2026.xlsx",
                "user": "admin",
            })
            now = "2026-09-08T14:10:00+00:00"
            with store.connect() as con:
                con.execute(
                    """
                    INSERT INTO aw_cutting_generations (
                        order_no, item_no, key_index, batch_job_number,
                        optimization_number, optimization_status_code,
                        batch_creation_at, optimization_last_changed_at,
                        first_seen_at, last_seen_at, synced_at
                    ) VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order, "001", "9513", 8513, 500, now, now, now, now, now),
                )
                con.commit()

            match = next(row for row in store.global_search(order) if row["order"] == order)
            cutting = match.get("cutting") or {}
            self.assertTrue(cutting.get("dataAvailable"))
            self.assertTrue(cutting.get("complete"))
            self.assertEqual(cutting.get("state"), "cut")
            self.assertEqual(cutting.get("optimization"), 8513)
            self.assertIn("progressStages", match)
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0475_missing_child_on_reachable_mapped_parent_is_not_drive_error(self) -> None:
        """A missing Completed WJ child must not blame I: when its parent is reachable."""
        config = replace(
            load_config(ROOT),
            hardware_lists_dir=Path("I:/Production/Hardware"),
            sketches_dir=Path("I:/Production/Sketches"),
            programs_dir=Path("I:/Production/Programs"),
            completed_wj_dir=Path("I:/Production/Completed WJ"),
        )
        service = ProductionFileService(config)
        target = Path("I:/Production/Completed WJ")
        target_key = str(target).replace("\\", "/")
        parent_key = str(target.parent).replace("\\", "/")

        def fake_stat(path_obj, *args, **kwargs):
            key = str(path_obj).replace("\\", "/")
            if key == target_key:
                raise FileNotFoundError(target_key)
            if key == parent_key:
                return mock.Mock(st_mode=0o040755)
            raise FileNotFoundError(key)

        with mock.patch("backend.production_files.os.name", "nt"), mock.patch.object(Path, "stat", fake_stat):
            available, reason = service._probe_root("completed_wj", target)
        self.assertFalse(available)
        self.assertIn("Folder not found", reason)
        self.assertIn("parent is reachable", reason)
        self.assertNotIn("Mapped drive not reachable", reason)

    def test_v0476_waterjet_folder_resolves_repeated_space_alias_and_machine_colors(self) -> None:
        """Completed  WJ is accepted from a legacy one-space setting; machine colors persist."""
        verification_root = ROOT / "_verification_v0476_waterjet_alias"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        actual_wj = verification_root / "Completed  WJ"
        actual_wj.mkdir()
        (actual_wj / "23824502.nce").write_text("waterjet complete", encoding="utf-8")
        try:
            config = replace(
                load_config(ROOT),
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=verification_root / "Hardware Lists",
                sketches_dir=verification_root / "Sketches",
                programs_dir=verification_root / "Programs",
                completed_wj_dir=verification_root / "Completed WJ",
            )
            for folder in (config.data_dir, config.hardware_lists_dir, config.sketches_dir, config.programs_dir):
                Path(folder).mkdir(parents=True, exist_ok=True)
            service = ProductionFileService(config)
            service.configure({
                "lookbackDays": 7,
                "machineColors": {"denver": "#13579b", "waterjet": "#8642c7"},
            })
            assets = service.assets("completed_wj", refresh=True)
            self.assertEqual([asset.name for asset in assets], ["23824502.nce"])
            self.assertEqual(Path(assets[0].root).name, "Completed  WJ")
            self.assertEqual(service.settings_snapshot()["machineColors"]["denver"], "#13579b")
            self.assertEqual(service.settings_snapshot()["machineColors"]["waterjet"], "#8642c7")
            self.assertTrue(service.index_status()["resolvedRoots"]["completed_wj"].endswith("Completed  WJ"))
            original_resolver = service._resolve_root_alias
            service._resolve_root_alias = lambda _root: (_ for _ in ()).throw(AssertionError("index_status must not touch production shares"))
            try:
                self.assertTrue(service.index_status()["resolvedRoots"]["completed_wj"].endswith("Completed  WJ"))
            finally:
                service._resolve_root_alias = original_resolver
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

    def test_v0477_requested_sketch_pages_persist_without_reparsing_pdf(self) -> None:
        """Exact PDF page matches survive a restart without turning indexing into a PDF crawl."""
        verification_root = ROOT / "_verification_v0477_sketch_page_cache"
        if verification_root.exists():
            shutil.rmtree(verification_root)
        verification_root.mkdir()
        sketches_dir = verification_root / "Sketches"
        sketches_dir.mkdir()
        try:
            from reportlab.pdfgen import canvas

            sketch = sketches_dir / "238477 Sketch.pdf"
            pdf = canvas.Canvas(str(sketch))
            pdf.drawString(180, 400, "238477.3 DENVER")
            pdf.save()
            config = replace(
                load_config(ROOT),
                root=verification_root,
                data_dir=verification_root / "data",
                hardware_lists_dir=verification_root / "Hardware Lists",
                sketches_dir=sketches_dir,
                programs_dir=verification_root / "Programs",
                completed_wj_dir=verification_root / "Completed WJ",
            )
            for folder in (config.data_dir, config.hardware_lists_dir, config.programs_dir, config.completed_wj_dir):
                Path(folder).mkdir(parents=True, exist_ok=True)

            service = ProductionFileService(config)
            service.assets("sketch", refresh=True)
            first = service.sketch_item_views("238477", "3")
            self.assertEqual(first[0]["pageNumber"], 1)
            service._persist_index()

            with mock.patch.object(ProductionFileService, "_is_network_root", return_value=True):
                restored = ProductionFileService(config)
                with mock.patch("pypdf.PdfReader", side_effect=AssertionError("persisted page was reparsed")):
                    second = restored.sketch_item_views("238477", "3")
            self.assertEqual(second[0]["itemMarker"], "238477.3")
            self.assertEqual(second[0]["machineHint"], "Denver CNC")
        finally:
            if verification_root.exists():
                shutil.rmtree(verification_root)

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

    def test_v0506_production_count_groups_actual_pieces_by_glass_and_excludes_yield_percentage(self) -> None:
        """Production Count deduplicates stage copies and keeps Yield Percentage out of statistics/email rows."""
        verification_root = ROOT / "_verification_v0505_production_count"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            new_item = imported_item("281001", "1", 4, "v0505-new:1")
            new_item["customer"] = "NEW GLASS CUSTOMER"
            new_item["dimensions"] = '48" x 72"'
            second_new_item = imported_item("281004", "1", 5, "v0506-new-mirror:1")
            second_new_item["customer"] = "MIRROR CUSTOMER"
            second_new_item["product"] = '1/4" Mirror'
            second_new_item["dimensions"] = '22" x 36"'
            remake_item = imported_item("281002", "2", 2, "v0505-remake:2")
            remake_item["processState"] = "External Remake"
            remake_item["queueState"] = "RM"
            remake_item["customer"] = "REMAKE CUSTOMER"
            remake_item["dimensions"] = '36" x 60"'
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-11-06", "items": [new_item, second_new_item, remake_item]},
                "fileName": "Delivery List 11-06-2026.xlsx",
                "user": "admin",
            })
            # Same-day A+W correction: Production Count must use the latest Qty
            # for an item that first arrived today instead of freezing Qty 4.
            corrected_new_item = dict(new_item)
            corrected_new_item["qty"] = 6
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-11-06", "items": [corrected_new_item, second_new_item, remake_item]},
                "fileName": "Delivery List 11-06-2026.xlsx",
                "user": "admin",
            })

            with store.connect() as connection:
                # One logical imported Order/Item creates synchronized stage
                # rows. Production Count now uses their immutable earliest
                # created_at_utc, so place that first-import time on a controlled
                # plant-local reporting day and prove stage-copy deduplication.
                connection.execute(
                    "UPDATE line_items SET created_at_utc = '2026-11-05T13:00:00+00:00'"
                )
                connection.execute(
                    "UPDATE line_update_notices SET created_at = '2026-11-05T08:00:00+00:00'"
                )
                connection.execute(
                    "UPDATE line_items SET process_state = 'Rush', queue_state = 'Priority Rush' WHERE order_no = '281001'"
                )
                rush_notices = connection.execute(
                    "SELECT id, snapshot_json FROM line_update_notices"
                ).fetchall()
                for notice in rush_notices:
                    snapshot = json.loads(str(notice["snapshot_json"] or "{}"))
                    if str(snapshot.get("order") or "") != "281001":
                        continue
                    snapshot["processState"] = "Rush"
                    snapshot["queueState"] = "Priority Rush"
                    connection.execute(
                        "UPDATE line_update_notices SET snapshot_json = ? WHERE id = ?",
                        (json.dumps(snapshot, sort_keys=True, separators=(",", ":")), notice["id"]),
                    )
                connection.execute(
                    """
                    INSERT INTO reject_events (
                        delivery_date, order_no, item_no, qty, customer, product,
                        reason_label, location_label, rejected_at, rejected_by
                    ) VALUES ('2026-11-06','281001','001',1,'NEW GLASS CUSTOMER','3/8 Clear Tempered',
                              'Scratch','Tempering','2026-11-05T09:15:00+00:00','Operator One')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO reject_events (
                        delivery_date, order_no, item_no, qty, customer, product,
                        reason_label, location_label, rejected_at, rejected_by
                    ) VALUES ('2026-11-06','281003','001',3,'YIELD CUSTOMER','3/8 Clear Tempered',
                              'Yield Percentage','Cutting','2026-11-05T10:30:00+00:00','Operator Two')
                    """
                )
                connection.commit()

            report = store.reports_summary({"dateFrom": "2026-11-05", "dateTo": "2026-11-05"})
            activity = report["productionActivity"]
            self.assertEqual(activity["newProduction"]["pieces"], 11)
            self.assertEqual(activity["newProduction"]["itemCount"], 2)
            self.assertEqual(activity["newProduction"]["orderCount"], 2)
            self.assertEqual(activity["newProduction"]["rows"][0]["order"], "281001")
            new_rows_by_order = {row["order"]: row for row in activity["newProduction"]["rows"]}
            self.assertTrue(new_rows_by_order["281001"]["rush"])
            self.assertFalse(new_rows_by_order["281004"]["rush"])
            self.assertEqual(new_rows_by_order["281001"]["barcode"], new_item["barcode"])
            self.assertEqual(new_rows_by_order["281001"]["processState"], "Rush")
            self.assertEqual(new_rows_by_order["281001"]["queueState"], "Priority Rush")
            by_glass = {row["glassType"]: row for row in activity["newProduction"]["byGlass"]}
            self.assertEqual(activity["newProduction"]["byDate"], [{
                "date": "2026-11-05", "pieces": 11, "itemCount": 2, "orderCount": 2,
            }])
            self.assertEqual(by_glass['1/4 Mirror']["pieces"], 5)
            self.assertEqual(by_glass['1/4 Mirror']["itemCount"], 1)
            self.assertEqual(by_glass['3/8" Clear Tempered']["pieces"], 6)
            self.assertEqual(by_glass['3/8" Clear Tempered']["deliveryDates"], ["2026-11-06"])
            self.assertEqual(activity["externalRemakes"]["pieces"], 2)
            self.assertEqual(activity["externalRemakes"]["itemCount"], 1)
            self.assertEqual(activity["externalRemakes"]["rows"][0]["order"], "281002")
            self.assertEqual(activity["internalRejects"]["pieces"], 1)
            self.assertEqual(activity["internalRejects"]["eventCount"], 1)
            self.assertEqual(activity["internalRejects"]["rows"][0]["reason"], "Scratch")
            self.assertEqual(activity["internalRejects"]["rows"][0]["glassType"], '3/8" Clear Tempered')
            self.assertEqual(activity["internalRejects"]["rows"][0]["dimensions"], '48" x 72"')
            self.assertGreater(activity["internalRejects"]["rows"][0]["sqft"], 0)
            self.assertEqual(activity["yieldPercentageExcluded"]["pieces"], 3)
            self.assertEqual(activity["yieldPercentageExcluded"]["eventCount"], 1)
            # Yield Percentage is not just omitted from the email detail payload;
            # it is also excluded from the existing breakage/statistics totals.
            self.assertEqual(report["breakage"]["internalRejects"]["pieces"], 1)
            self.assertEqual(report["breakage"]["internalRejects"]["eventCount"], 1)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0538_statistics_event_metrics_use_plant_local_day_boundaries(self) -> None:
        """Event-day Statistics must follow America/New_York rather than UTC midnight."""
        verification_root = ROOT / "_verification_v0538_statistics_local_day"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            item = imported_item("281038", "1", 2, "v0538-local-day:1")
            item["customer"] = "LOCAL DAY AUDIT"
            item["dimensions"] = '24" x 36"'
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-11-12", "items": [item]},
                "fileName": "Delivery List 11-12-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as connection:
                list_row = connection.execute(
                    "SELECT id FROM delivery_lists WHERE delivery_date='2026-11-12' ORDER BY id LIMIT 1"
                ).fetchone()
                line_row = connection.execute(
                    "SELECT id FROM line_items WHERE order_no='281038' AND item_no='001' ORDER BY id LIMIT 1"
                ).fetchone()
                list_id = str(list_row["id"])
                line_id = str(line_row["id"])
                # 01:00 UTC Nov 6 is 8 PM Nov 5 in Monroe; 05:00 UTC is midnight Nov 6.
                for stamp, event_type, barcode in (
                    ("2026-11-06T01:00:00+00:00", "scan", "local-prior-scan"),
                    ("2026-11-06T01:05:00+00:00", "error", "local-prior-error"),
                    ("2026-11-06T05:00:00+00:00", "scan", "local-current-scan"),
                    ("2026-11-06T05:05:00+00:00", "duplicate", "local-current-duplicate"),
                ):
                    connection.execute(
                        """INSERT INTO scan_events
                           (list_id,line_item_id,barcode,canonical_barcode,user_name,station,event_type,message,reason,qty_delta,created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (list_id, line_id, barcode, barcode, "Plant Operator", "TC22", event_type, event_type, "", 1 if event_type == "scan" else 0, stamp),
                    )
                for stamp in ("2026-11-06T01:10:00+00:00", "2026-11-06T05:10:00+00:00"):
                    connection.execute(
                        """INSERT INTO audit_events
                           (entity_type,entity_id,action,user_name,station,reason,payload_json,created_at)
                           VALUES ('scan',?,'manual_scan','Plant Operator','TC22','','{}',?)""",
                        (line_id, stamp),
                    )
                for stamp, order_no in (("2026-11-06T01:15:00+00:00", "281038"), ("2026-11-06T05:15:00+00:00", "281039")):
                    connection.execute(
                        """INSERT INTO reject_events
                           (delivery_date,order_no,item_no,qty,customer,product,reason_label,location_label,rejected_at,rejected_by)
                           VALUES ('2026-11-12',?, '001',1,'LOCAL DAY AUDIT','3/8 Clear Tempered','Scratch','Tempering',?,'Plant Operator')""",
                        (order_no, stamp),
                    )
                connection.commit()

            prior = store.reports_summary({"dateFrom": "2026-11-05", "dateTo": "2026-11-05"})
            current = store.reports_summary({"dateFrom": "2026-11-06", "dateTo": "2026-11-06"})
            self.assertEqual(prior["scansByOperator"], [{"user": "Plant Operator", "scans": 1}])
            self.assertEqual(prior["badScanCount"], 1)
            self.assertEqual(prior["duplicateScanCount"], 0)
            self.assertEqual(prior["manualScanCount"], 1)
            self.assertEqual(prior["breakage"]["internalRejects"]["pieces"], 1)
            self.assertEqual(current["scansByOperator"], [{"user": "Plant Operator", "scans": 1}])
            self.assertEqual(current["badScanCount"], 0)
            self.assertEqual(current["duplicateScanCount"], 1)
            self.assertEqual(current["manualScanCount"], 1)
            self.assertEqual(current["breakage"]["internalRejects"]["pieces"], 1)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0536_production_count_uses_immutable_first_import_and_stable_remake_identity(self) -> None:
        """Routine review-notice refreshes must not manufacture new production."""
        verification_root = ROOT / "_verification_v0536_production_first_import"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            mirror = imported_item("281050", "1", 139, "v0536-mirror-original:1")
            mirror["customer"] = "MIRROR COUNT AUDIT"
            mirror["product"] = '1/4" Mirror'
            mirror["dimensions"] = '24" x 36"'
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-11-12", "items": [mirror]},
                "fileName": "Delivery List 11-12-2026.xlsx",
                "user": "admin",
            })

            with store.connect() as connection:
                # The physical Order/Item really first arrived at 8 PM plant time on Nov 5 (01:00 UTC Nov 6). Simulate
                # the latest-review ledger being regenerated on Nov 6. v0.535's
                # notice-based Production Count would have moved all 139 pieces
                # onto Nov 6; v0.536 must leave them on the immutable first day.
                connection.execute(
                    "UPDATE line_items SET created_at_utc = '2026-11-06T01:00:00+00:00' WHERE order_no = '281050'"
                )
                connection.execute(
                    "UPDATE line_update_notices SET created_at = '2026-11-06T14:00:00+00:00', change_type = 'new' WHERE delivery_date = '2026-11-12'"
                )
                connection.commit()

            first_day = store.reports_summary({"dateFrom": "2026-11-05", "dateTo": "2026-11-05"})["productionActivity"]
            refresh_day = store.reports_summary({"dateFrom": "2026-11-06", "dateTo": "2026-11-06"})["productionActivity"]
            self.assertEqual(first_day["newProduction"]["pieces"], 139)
            self.assertEqual(first_day["newProduction"]["itemCount"], 1)
            self.assertEqual(first_day["newProduction"]["byGlass"][0]["glassType"], '1/4 Mirror')
            self.assertEqual(refresh_day["newProduction"]["pieces"], 0)

            with store.connect() as connection:
                # A+W corrects that same logical item to External Remake without
                # preserving the old source-row identity. Current state and the
                # transition notice must move the item out of New Production,
                # not count the same 139 pieces in both categories.
                connection.execute(
                    "UPDATE line_items SET source_id = 'v0536-mirror-remake:1', process_state = 'External Remake', queue_state = 'RM' WHERE order_no = '281050'"
                )
                notices = connection.execute(
                    "SELECT id, snapshot_json FROM line_update_notices WHERE delivery_date = '2026-11-12'"
                ).fetchall()
                for notice in notices:
                    snapshot = json.loads(str(notice["snapshot_json"] or "{}"))
                    snapshot["sourceId"] = "v0536-mirror-remake:1"
                    snapshot["processState"] = "External Remake"
                    snapshot["queueState"] = "RM"
                    snapshot["previous"] = {
                        "sourceId": "v0536-mirror-original:1",
                        "processState": "New Line",
                        "queueState": "",
                    }
                    connection.execute(
                        "UPDATE line_update_notices SET created_at = '2026-11-05T15:00:00+00:00', change_type = 'updated', snapshot_json = ? WHERE id = ?",
                        (json.dumps(snapshot, sort_keys=True, separators=(",", ":")), int(notice["id"])),
                    )
                connection.commit()

            corrected = store.reports_summary({"dateFrom": "2026-11-05", "dateTo": "2026-11-05"})["productionActivity"]
            self.assertEqual(corrected["newProduction"]["pieces"], 0)
            self.assertEqual(corrected["externalRemakes"]["pieces"], 139)
            self.assertEqual(corrected["externalRemakes"]["itemCount"], 1)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0536_production_count_does_not_recount_delivery_date_moves(self) -> None:
        """Moving the same A+W Order/Item to another delivery date is not a new order."""
        verification_root = ROOT / "_verification_v0536_production_delivery_move"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            item = imported_item("281060", "1", 3, "v0536-moved-order:1")
            item["product"] = '1/4" Mirror'
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-11-12", "items": [item]},
                "fileName": "Delivery List 11-12-2026.xlsx",
                "user": "admin",
            })
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-11-19", "items": [item]},
                "fileName": "Delivery List 11-19-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as connection:
                connection.execute(
                    """UPDATE line_items SET created_at_utc='2026-11-05T15:00:00+00:00', updated_at_utc='2026-11-05T15:00:00+00:00'
                       WHERE list_id IN (SELECT id FROM delivery_lists WHERE delivery_date='2026-11-12') AND order_no='281060'"""
                )
                connection.execute(
                    """UPDATE line_items SET created_at_utc='2026-11-06T15:00:00+00:00', updated_at_utc='2026-11-06T15:00:00+00:00'
                       WHERE list_id IN (SELECT id FROM delivery_lists WHERE delivery_date='2026-11-19') AND order_no='281060'"""
                )
                connection.execute(
                    "UPDATE line_update_notices SET created_at='2026-11-06T15:00:00+00:00' WHERE delivery_date='2026-11-19'"
                )
                connection.commit()

            first_day = store.reports_summary({"dateFrom": "2026-11-05", "dateTo": "2026-11-05"})["productionActivity"]["newProduction"]
            moved_day = store.reports_summary({"dateFrom": "2026-11-06", "dateTo": "2026-11-06"})["productionActivity"]["newProduction"]
            self.assertEqual(first_day["pieces"], 3)
            self.assertEqual(first_day["itemCount"], 1)
            self.assertEqual(first_day["rows"][0]["deliveryDate"], "2026-11-19")
            self.assertEqual(moved_day["pieces"], 0)
            self.assertEqual(moved_day["itemCount"], 0)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_aw_cutting_generations_follow_latest_remake_and_reject_cutoff(self) -> None:
        verification_root = ROOT / "_verification_aw_cutting_v498"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            common = {
                "orderNr": "238221", "itemNr": "1", "quantity": 1, "cutQuantity": 0,
                "itemBarcodeStart": "130191", "weight": 83.88, "surfaceArea": 17.48,
                "customerName": "FRAMED MIRROR", "sgBestText1": "43479331.5 30** CEDAR",
                "routeText": "<n.e.>", "productDescription": '1/4" Mirror',
                "positionQuantity": 1, "positionWidth": 1018, "positionHeight": 570,
            }
            rows = [
                {**common, "sourceRowId": "old-cut", "bomId": 1, "keyIndex": 0, "batchJobNumber": "6474",
                 "batchStatusCode": 500, "batchCreatedAt": "2026-08-31T15:22:37",
                 "optimizationNumber": 8309, "optimizationStatusCode": 500, "aggregateId": 1000, "cutQuantity": 1,
                 "cuttingBookingAt": "2026-09-01T07:08:00", "cuttingBookingEmployee": "Intermac Cutting",
                 "cuttingBookingRowId": "book-old", "bomBarcodeStart": "130192"},
                {**common, "sourceRowId": "current-cut", "bomId": 1, "keyIndex": 2, "batchJobNumber": "9176",
                 "batchStatusCode": 400, "batchCreatedAt": "2026-09-02T15:23:23",
                 "optimizationNumber": 8361, "optimizationStatusCode": 100, "aggregateId": 1000,
                 "bomBarcodeStart": "130192"},
                {**common, "sourceRowId": "current-fab", "bomId": 2, "keyIndex": 2, "batchJobNumber": "9176",
                 "batchStatusCode": 400, "batchCreatedAt": "2026-09-02T15:23:23",
                 "optimizationNumber": 0, "optimizationStatusCode": 0, "aggregateId": 2000},
            ]
            first = store.sync_aw_cutting_rows(rows)
            self.assertEqual(first["generations"], 2)
            self.assertEqual(first["inserted"], 2)

            state = store.aw_cutting_state("238221", "1", "2026-09-02T10:55:27")
            self.assertEqual(state["batch"], "9176")
            self.assertEqual(state["optimization"], 8361)
            self.assertEqual(state["state"], "optimized")
            self.assertFalse(state["complete"])
            self.assertEqual(state["cuttingBarcodeStart"], "130192")
            self.assertAlmostEqual(state["weight"], 83.88, places=2)
            self.assertEqual(len(state["history"]), 2)
            self.assertEqual(state["customerName"], "FRAMED MIRROR")
            self.assertEqual(state["sgBestText1"], "43479331.5 30** CEDAR")
            self.assertEqual(state["productDescription"], '1/4" Mirror')
            self.assertEqual(state["positionWidth"], 1018.0)

            unknown = store.aw_cutting_state("999999", "1")
            self.assertEqual(unknown["state"], "unknown")
            self.assertFalse(unknown["dataAvailable"])

            order_item = imported_item("238221", "1", 1, "v0498-cutting-order:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-04", "items": [order_item]},
                "fileName": "Delivery List 09-04-2026.xlsx",
                "user": "admin",
            })
            with store.connect() as connection:
                connection.execute(
                    "UPDATE line_items SET last_rejected_at = ? WHERE order_no = ? AND item_no IN (?, ?)",
                    ("2026-09-02T10:55:27", "238221", "1", "001"),
                )
            detail = store.get_order_detail("238221", include_production=False)
            self.assertEqual(detail["items"][0]["cutting"]["batch"], "9176")
            self.assertEqual(detail["items"][0]["cutting"]["optimization"], 8361)
            self.assertEqual(detail["items"][0]["cutting"]["state"], "optimized")

            class FabricatedProductionFiles:
                @staticmethod
                def item_assets(order, item, job, *, evidence_after="", label_hint=None):
                    return {
                        "fabrication": {
                            "fabricated": True, "actualMachine": "Denver CNC", "machine": "Denver CNC",
                            "evidenceAfter": evidence_after, "evidence": {"name": "238221-1.egl"},
                        },
                        "hardware": [], "sketches": [], "programs": [],
                    }

                @staticmethod
                def order_assets(order, job):
                    return {"hardware": [], "sketches": []}

                @staticmethod
                def availability():
                    return {}

            store.production_files = FabricatedProductionFiles()
            fabricated_detail = store.get_order_detail("238221", include_production=True)
            fabricated_cutting = fabricated_detail["items"][0]["cutting"]
            self.assertEqual(fabricated_cutting["state"], "optimized")
            self.assertFalse(fabricated_cutting["complete"])
            self.assertTrue(fabricated_cutting["downstreamFabricationObserved"])
            self.assertEqual(fabricated_cutting["fabricationMachine"], "Denver CNC")

            no_generation = store.aw_cutting_irregularities({"complete": True, "batch": "", "optimization": 0})
            self.assertEqual(no_generation[0]["code"], "cut_without_batch_or_optimization")
            batch_without_optimization = store.aw_cutting_irregularities({"complete": True, "batch": "9176", "optimization": 0})
            self.assertEqual(batch_without_optimization[0]["code"], "cut_in_batch_without_optimization")
            self.assertEqual(store.aw_cutting_irregularities({"complete": True, "batch": "9176", "optimization": 8361}), [])
            self.assertEqual(store.aw_cutting_irregularities({"complete": False, "batch": "9176", "optimization": 0}), [])

            recut_state = store.aw_cutting_state("238221", "1", "2026-09-03T08:00:00")
            self.assertEqual(recut_state["state"], "needs_recut")
            self.assertFalse(recut_state["complete"])

            batch_only_rows = [dict(row) for row in rows]
            batch_only_rows[1]["batchStatusCode"] = 500
            store.sync_aw_cutting_rows(batch_only_rows)
            batch_only_state = store.aw_cutting_state("238221", "1", "2026-09-02T10:55:27")
            self.assertEqual(batch_only_state["state"], "optimized")
            self.assertFalse(batch_only_state["complete"])

            released_rows = [dict(row) for row in rows]
            released_rows[1]["optimizationStatusCode"] = 200
            released = store.sync_aw_cutting_rows(released_rows)
            self.assertGreaterEqual(released["updated"], 1)
            self.assertEqual(store.aw_cutting_state("238221", "001", "2026-09-02T10:55:27")["state"], "released")

            booked_rows = [dict(row) for row in released_rows]
            booked_rows[1].update({
                "batchStatusCode": 500, "optimizationStatusCode": 500,
                "cuttingBookingAt": "2026-09-02T16:10:00",
                "cuttingBookingEmployee": "Intermac Cutting", "cuttingBookingRowId": "book-current",
            })
            booked = store.sync_aw_cutting_rows(booked_rows)
            self.assertGreaterEqual(booked["updated"], 1)
            state = store.aw_cutting_state("238221", "1", "2026-09-02T10:55:27")
            self.assertEqual(state["state"], "cut")
            self.assertTrue(state["complete"])
            self.assertEqual(state["cutCompletedBy"], "Intermac Cutting")

            unchanged = store.sync_aw_cutting_rows(booked_rows)
            self.assertEqual(unchanged["unchanged"], 2)
            self.assertEqual(unchanged["updated"], 0)

            # v0.544: the current optimization status is authoritative. An older
            # Booked observation stays in retained history but cannot keep a
            # current Optimized state marked Cut.
            regressed_rows = [dict(row) for row in booked_rows]
            regressed_rows[1].update({
                "optimizationStatusCode": 100, "cuttingBookingAt": "",
                "cuttingBookingEmployee": "", "cuttingBookingRowId": "", "cutQuantity": 0,
            })
            store.sync_aw_cutting_rows(regressed_rows)
            current_optimized = store.aw_cutting_state("238221", "1", "2026-09-02T10:55:27")
            self.assertFalse(current_optimized["complete"])
            self.assertEqual(current_optimized["state"], "optimized")
            self.assertEqual(current_optimized["evidenceSource"], "")
            rejected_again = store.aw_cutting_state("238221", "1", "2026-09-03T08:00:00")
            self.assertFalse(rejected_again["complete"])
            self.assertEqual(rejected_again["state"], "needs_recut")
            remake_row = {
                **common, "sourceRowId": "next-remake", "bomId": 1, "keyIndex": 3,
                "batchJobNumber": "9300", "batchStatusCode": 400,
                "batchCreatedAt": "2026-09-03T09:00:00", "optimizationNumber": 8400,
                "optimizationStatusCode": 100, "aggregateId": 1000,
            }
            store.sync_aw_cutting_rows([remake_row])
            remake_state = store.aw_cutting_state("238221", "1", "2026-09-02T10:55:27")
            self.assertFalse(remake_state["complete"])
            self.assertEqual(remake_state["keyIndex"], 3)

            # v0.502 regression from the live 238330 probe: the newest remake
            # v0.544: physical-looking plate/cut-quantity evidence is diagnostic
            # only. Without a current Booked optimization, the pane is not Cut.
            probe_rows = [{
                "sourceRowId": "238330-current", "orderNr": "238330", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "batchJobNumber": "9179", "batchStatusCode": 500,
                "batchDescription": "Reject batch Brandon Smith 09/03/2026",
                "batchCreatedAt": "2026-09-03T08:06:32", "optimizationNumber": 8366,
                "optimizationStatusCode": 0, "optimizationSequence": 4, "optimizationSequenceRowId": "seq-8366-4",
                "optimizationPlateNumber": 1, "optimizationPlateCut": 1, "optimizationPlateStockBooked": 1,
                "optimizationPlateLastChangedAt": "2026-09-03T09:31:12",
                "optimizationPlateLastChangedUser": "Intermac Cutting",
                "optimizationSheetCount": 1, "shapeNumber": 99,
                "processRows": [
                    {"workTypeId": 10, "workType": "Automatic Cutting", "workSequence": 1, "machine": "Cutting"},
                    {"workTypeId": 20, "workType": "Polishing", "workSequence": 2, "edgeData": "11110000", "machine": "Kodiak (Polisher)"},
                ],
                "quantity": 1, "cutQuantity": 1, "aggregateId": 1000, "lastAggregateId": 2000,
            }]
            probe_sync = store.sync_aw_cutting_rows(probe_rows)
            self.assertEqual(probe_sync["generations"], 1)
            probe_state = store.aw_cutting_state("238330", "1", "2026-09-03T07:50:00")
            self.assertEqual(probe_state["state"], "optimized")
            self.assertFalse(probe_state["complete"])
            self.assertEqual(probe_state["optimization"], 8366)
            self.assertEqual(probe_state["optimizationSequence"], 4)
            self.assertEqual(probe_state["optimizationPlateNumber"], 1)
            self.assertTrue(probe_state["optimizationPlateCut"])
            self.assertTrue(probe_state["optimizationPlateStockBooked"])
            self.assertEqual(probe_state["optimizationSheetCount"], 1)
            self.assertEqual(probe_state["shapeNumber"], 99)
            self.assertEqual(probe_state["sequenceAssignments"][0]["sequence"], 4)
            self.assertEqual(probe_state["sequenceAssignments"][0]["plateNumber"], 1)
            self.assertEqual(probe_state["processRows"][1]["edgeData"], "11110000")
            self.assertEqual(probe_state["evidenceSource"], "")
            post_probe_reject = store.aw_cutting_state("238330", "1", "2026-09-03T10:00:00")
            self.assertEqual(post_probe_reject["state"], "needs_recut")
            self.assertFalse(post_probe_reject["complete"])


            # v0.504 live regression: Order 238076 / Item 1 is Batch 6455,
            # Optimization 8286 and A+W reports the optimization as Booked with
            # raw status 460. That status must be retained and interpreted as Cut.
            status_460_rows = [{
                "sourceRowId": "238076-booked-460", "orderNr": "238076", "itemNr": "1", "bomId": 0,
                "keyIndex": 0, "batchJobNumber": "6455", "batchStatusCode": 500,
                "batchCreatedAt": "2026-08-29T08:00:00", "optimizationNumber": 8286,
                "optimizationStatusCode": 460, "optimizationStatusSource": "PROD_OPTI_STATISTICS", "optimizationSequence": 7,
                "optimizationSequenceRowId": "seq-8286-7", "optimizationPlateNumber": 2,
                "optimizationPlateCut": 1, "optimizationPlateStockBooked": 1,
                "quantity": 1, "cutQuantity": 1, "aggregateId": 1000,
            }]
            store.sync_aw_cutting_rows(status_460_rows)
            status_460_state = store.aw_cutting_state("238076", "001")
            self.assertEqual(status_460_state["batch"], "6455")
            self.assertEqual(status_460_state["optimization"], 8286)
            self.assertEqual(status_460_state["optimizationStatusCode"], 460)
            self.assertEqual(status_460_state["optimizationStatusSource"], "PROD_OPTI_STATISTICS")
            self.assertEqual(status_460_state["state"], "cut")
            self.assertTrue(status_460_state["complete"])
            self.assertEqual(status_460_state["evidenceSource"], "optimization_status_460")
            status_460_item = imported_item("238076", "1", 1, "v0504-status-460-order:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-03", "items": [status_460_item]},
                "fileName": "Delivery List 09-03-2026.xlsx",
                "user": "admin",
            })
            status_460_detail = store.get_order_detail("238076", include_production=False)
            detail_cutting = status_460_detail["items"][0]["cutting"]
            self.assertEqual(detail_cutting["batch"], "6455")
            self.assertEqual(detail_cutting["optimization"], 8286)
            self.assertEqual(detail_cutting["optimizationStatusCode"], 460)
            self.assertEqual(detail_cutting["state"], "cut")
            self.assertEqual(detail_cutting["sequenceAssignments"][0]["sequence"], 7)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v523_cutting_sync_plan_skips_complete_until_lifecycle_reset(self) -> None:
        verification_root = ROOT / "_verification_v523_cutting_skip_plan"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(exist_ok=True)
        try:
            store = self.make_store(verification_root)
            order = "289523"
            item = imported_item(order, "1", 1, "v0523-cutting-plan:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-10", "items": [item]},
                "fileName": "Delivery List 09-10-2026.xlsx",
                "user": "admin",
            })
            completed_row = {
                "sourceRowId": "v523-cut", "orderNr": order, "itemNr": "1", "bomId": 1,
                "keyIndex": 2, "batchJobNumber": "9523", "batchStatusCode": 500,
                "batchCreatedAt": "2026-09-10T06:00:00", "optimizationNumber": 95230,
                "optimizationStatusCode": 500, "optimizationLastChangedAt": "2026-09-10T06:15:00",
                "quantity": 1, "cutQuantity": 1, "aggregateId": 1000,
                "cuttingBookingAt": "2026-09-10T06:16:00", "cuttingBookingEmployee": "CUT",
                "cuttingBookingRowId": "v523-book",
            }
            store.sync_aw_cutting_rows([completed_row])
            direct = [{"payload": {"rows": [{
                "order": order, "item": 1, "job": item["job"], "remake": "",
            }]}}]

            before_counts = {}
            with store.connect() as connection:
                for table in ("delivery_lists", "line_items", "aw_cutting_generations", "reject_events"):
                    before_counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

            plan = store.aw_cutting_sync_plan(direct, [], delivery_date_from="2026-09-01")
            self.assertTrue(plan["ok"])
            self.assertEqual(plan["completedItemCount"], 1)
            self.assertEqual(plan["refreshItemCount"], 0)
            self.assertEqual(plan["skipItems"][0]["order"], order)
            self.assertEqual(plan["skipItems"][0]["item"], "001")
            self.assertEqual(plan["skipItems"][0]["keyIndex"], 2)
            self.assertEqual(plan["fullyCompletedOrders"], [order])

            # A current-run reject must make the piece queryable before reject
            # synchronization writes anything into the scanner database.
            rejected = store.aw_cutting_sync_plan(direct, [{
                "orderNr": order, "itemNr": "1", "breakageDate": "2026-09-10T07:00:00",
            }], delivery_date_from="2026-09-01")
            self.assertEqual(rejected["completedItemCount"], 0)
            self.assertEqual(rejected["resetItemCount"], 1)
            self.assertEqual(rejected["resetItems"][0]["reason"], "new_reject")

            changed_job = [{"payload": {"rows": [{
                "order": order, "item": 1, "job": "NEW REMAKE JOB", "remake": "",
            }]}}]
            job_reset = store.aw_cutting_sync_plan(changed_job, [], delivery_date_from="2026-09-01")
            self.assertEqual(job_reset["completedItemCount"], 0)
            self.assertEqual(job_reset["resetItems"][0]["reason"], "job_changed")

            remake = [{"payload": {"rows": [{
                "order": order, "item": 1, "job": item["job"], "remake": "RM",
            }]}}]
            remake_reset = store.aw_cutting_sync_plan(remake, [], delivery_date_from="2026-09-01")
            self.assertEqual(remake_reset["completedItemCount"], 0)
            self.assertEqual(remake_reset["resetItems"][0]["reason"], "remake_changed")

            with store.connect() as connection:
                for table, expected in before_counts.items():
                    self.assertEqual(int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]), expected)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0511_scan_bundle_cutting_and_order_detail_step_timestamps(self) -> None:
        verification_root = ROOT / "_verification_v0511_cutting_progress"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            item = imported_item("511101", "1", 1, "v511-cutting-progress:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-22", "items": [item]},
                "fileName": "Delivery List 09-22-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_cutting_rows([{
                "sourceRowId": "v511-cutting-row", "orderNr": "511101", "itemNr": "1", "bomId": 0,
                "keyIndex": 0, "batchJobNumber": "9511", "batchStatusCode": 400,
                "batchCreatedAt": "2026-09-21T08:00:00", "optimizationNumber": 8511,
                "optimizationStatusCode": 100, "optimizationLastChangedAt": "2026-09-21T09:15:00",
                "quantity": 1, "cutQuantity": 0,
            }])

            bundle = store.get_delivery_date_scan_bundle("2026-09-22")
            bundle_items = [
                row
                for record in bundle["records"]
                for row in record["payload"]["items"]
                if row["order"] == "511101" and str(row["item"]).lstrip("0") == "1"
            ]
            self.assertTrue(bundle_items)
            self.assertTrue(all(row["cutting"]["optimization"] == 8511 for row in bundle_items))
            self.assertTrue(all(row["cutting"]["state"] == "optimized" for row in bundle_items))

            scan_time = "2026-09-22T14:35:00+00:00"
            with store.connect() as con:
                stage_line = con.execute(
                    """
                    SELECT li.id, li.list_id, li.barcode
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE li.order_no='511101' AND li.item_no='001'
                    ORDER BY CASE lower(dl.stage) WHEN 'staging' THEN 0 ELSE 1 END, dl.id
                    LIMIT 1
                    """
                ).fetchone()
                self.assertIsNotNone(stage_line)
                con.execute(
                    """
                    INSERT INTO scan_events (
                        list_id, line_item_id, barcode, canonical_barcode, user_name, station,
                        event_type, message, reason, qty_delta, created_at
                    ) VALUES (?, ?, ?, ?, 'admin', 'Airport Rd', 'scan', 'v0.511 timestamp', '', 1, ?)
                    """,
                    (stage_line["list_id"], stage_line["id"], stage_line["barcode"], stage_line["barcode"], scan_time),
                )

            detail = store.get_order_detail("511101", include_production=False)
            stage_times = [stage["lastScannedAt"] for stage in detail["items"][0]["stages"] if stage["lastScannedAt"]]
            self.assertIn(scan_time, stage_times)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0512_order_detail_remake_reason_and_production_status_access_filter(self) -> None:
        verification_root = ROOT / "_verification_v0512_order_detail_priority"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            remake = imported_item("512101", "1", 2, "v512-remake:1")
            remake["processState"] = "External Remake"
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-23", "items": [remake]},
                "fileName": "Delivery List 09-23-2026.xlsx",
                "user": "admin",
            })

            detail = store.get_order_detail("512101", include_production=False)
            self.assertTrue(detail["items"])
            priority = detail["items"][0].get("priorityBanner") or {}
            self.assertEqual(priority.get("kind"), "remake")
            self.assertEqual(priority.get("label"), "External Remake")
            self.assertEqual(priority.get("reason"), "Imported A+W RM marker")

            requested = [
                {"key": "allowed", "order": "512101", "item": "1", "job": ""},
                {"key": "missing", "order": "999999", "item": "1", "job": ""},
            ]
            allowed = store.filter_accessible_production_status_requests({"stageAccess": ["*"]}, requested)
            self.assertEqual([row["key"] for row in allowed], ["allowed"])
            denied = store.filter_accessible_production_status_requests({"stageAccess": ["No Such Stage"]}, requested)
            self.assertEqual(denied, [])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0507_runtime_indexes_compact_catalog_and_focused_summaries(self) -> None:
        verification_root = ROOT / "_verification_v0507_runtime"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            payload = {
                "payload": {
                    "deliveryDate": "2026-09-04",
                    "items": [
                        imported_item("507101", "1", 3, "v507-runtime:1"),
                        imported_item("507102", "2", 2, "v507-runtime:2"),
                    ],
                },
                "fileName": "Delivery List 09-04-2026.xlsx",
                "user": "admin",
            }
            store.import_delivery_list(payload)
            with store.connect() as con:
                installed = int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0)
                indexes = {str(row["name"]) for row in con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
                self.assertEqual(installed, 21)
            for name in {
                "idx_line_items_active_order_item_v507",
                "idx_delivery_lists_active_date_revision_v507",
                "idx_scan_events_list_recent_v507",
                "idx_line_update_notices_list_recent_v507",
                "idx_aw_cutting_order_item_recent_v507",
            }:
                self.assertIn(name, indexes)

            full = {row["id"]: row for row in store.get_delivery_lists()}
            compact = {row["id"]: row for row in store.get_delivery_lists_compact()}
            self.assertEqual(set(compact), set(full))
            for list_id, row in compact.items():
                self.assertEqual(row["totalQty"], full[list_id]["totalQty"])
                self.assertEqual(row["scannedQty"], full[list_id]["scannedQty"])
                self.assertEqual(row["itemCount"], full[list_id]["itemCount"])
                self.assertTrue(row["compact"])

            wanted = sorted(full)[:2]
            focused = {row["id"]: row for row in store.get_delivery_list_summaries(wanted)}
            self.assertEqual(set(focused), set(wanted))
            for list_id in wanted:
                self.assertEqual(focused[list_id]["totalQty"], full[list_id]["totalQty"])
                self.assertIn("sourceTotalQty", focused[list_id])
                self.assertIn("latestUpdateAt", focused[list_id])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0507_order_detail_core_preserves_aw_cutting_without_touching_network_share(self) -> None:
        verification_root = ROOT / "_verification_v0507_order_detail"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-04", "items": [imported_item("238076", "1", 1, "v507-238076:1")]},
                "fileName": "Delivery List 09-04-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_cutting_rows([{
                "sourceRowId": "238076-v507", "orderNr": "238076", "itemNr": "1",
                "bomId": 0, "keyIndex": 0, "batchJobNumber": "6455", "batchStatusCode": 500,
                "batchCreatedAt": "2026-08-29T08:00:00", "optimizationNumber": 8286,
                "optimizationStatusCode": 460, "optimizationStatusSource": "PROD_OPTI_STATISTICS",
                "optimizationLastChangedAt": "2026-08-30T12:00:00", "quantity": 1, "cutQuantity": 1,
                "aggregateId": 1000,
            }], source_window={"coverage": {"requestedOrderCount": 1, "matchedOrderCount": 1, "missingOrderCount": 0}})

            fake_service = mock.Mock()
            fake_service.item_assets.side_effect = AssertionError("core Order Details must not touch production shares")
            fake_service.order_assets.side_effect = AssertionError("core Order Details must not touch production shares")
            store.production_files = fake_service
            detail = store.get_order_detail("238076", include_production=False)
            cutting = detail["items"][0]["cutting"]
            self.assertEqual(cutting["batch"], "6455")
            self.assertEqual(cutting["optimization"], 8286)
            self.assertEqual(cutting["optimizationStatusCode"], 460)
            self.assertEqual(cutting["optimizationStatusSource"], "PROD_OPTI_STATISTICS")
            self.assertEqual(cutting["state"], "cut")
            self.assertTrue(cutting["complete"])
            fake_service.item_assets.assert_not_called()
            fake_service.order_assets.assert_not_called()
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)



    def test_v0507_mod13_crystal_edge_parameters_round_trip(self) -> None:
        verification_root = ROOT / "_verification_v0507_mod13_label"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-10", "items": [imported_item("238375", "3", 1, "v507-mod13:1")]},
                "fileName": "Delivery List 09-10-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_cutting_rows([{
                "sourceRowId": "238375-mod13", "orderNr": "238375", "itemNr": "3",
                "bomId": 0, "keyIndex": 0, "batchJobNumber": "6508", "batchStatusCode": 500,
                "optimizationNumber": 8363, "optimizationStatusCode": 500,
                "shapeNumber": 13, "shapeParameterUnitsPerInch": 32,
                "shapeParameters": [1880, 1878, 1444, 1438, 0, 0, 0, 0],
                "quantity": 1, "cutQuantity": 1, "aggregateId": 1000,
            }])
            detail = store.get_order_detail("238375", include_production=False)
            cutting = detail["items"][0]["cutting"]
            self.assertEqual(cutting["shapeNumber"], 13)
            self.assertEqual(cutting["shapeParameterUnitsPerInch"], 32)
            self.assertEqual(cutting["shapeParameters"][:4], [1880.0, 1878.0, 1444.0, 1438.0])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v0507_end_to_end_cutting_rush_rack_bay_reject_and_recut_workflow(self) -> None:
        """Run one physical order from A+W Cutting through Rush, rack, IT bay, reject and recut.

        This deliberately crosses the same store methods used by the scanner, Racks,
        Bay Map, Rejects and Order Details pages so a regression cannot pass by testing
        isolated helpers while the operator workflow is broken.
        """
        verification_root = ROOT / "_verification_v0507_full_floor_workflow"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            operations = OperationsFeatureService(store, store.config, verification_root)
            with store.connect() as con:
                store.seed_bays(con)
                store.seed_bay_auto_assign_settings(con)
                store.seed_racks(con)
                con.commit()
                rack = con.execute(
                    "SELECT rack_code FROM racks WHERE active=1 AND LOWER(status)='open' ORDER BY id LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(rack)
            rack_code = str(rack["rack_code"])

            delivery_date = "2026-09-18"
            item = imported_item("289701", "1", 2, "v0507-floor:1")
            item["customer"] = "V0507 FLOOR CUSTOMER"
            item["dimensions"] = '58 3/4" x 45 1/8"'
            store.import_delivery_list({
                "payload": {"deliveryDate": delivery_date, "items": [item]},
                "fileName": "Delivery List 09-18-2026.xlsx",
                "user": "admin",
            })

            # A+W physical lifecycle: Optimized -> Released/Cutting -> Booked/Cut.
            base_cutting = {
                "sourceRowId": "v0507-floor-generation-0", "orderNr": "289701", "itemNr": "1",
                "bomId": 0, "keyIndex": 0, "batchJobNumber": "9701", "batchStatusCode": 200,
                "batchCreatedAt": "2026-09-03T07:00:00+00:00", "optimizationNumber": 89701,
                "optimizationStatusSource": "PROD_OPTIMIZATION", "optimizationSequence": 4,
                "optimizationSequenceRowId": "v0507-seq-0", "optimizationPlateNumber": 1,
                "quantity": 2, "cutQuantity": 0, "aggregateId": 1000,
            }
            store.sync_aw_cutting_rows([{**base_cutting, "optimizationStatusCode": 100}])
            detail = store.get_order_detail("289701", include_production=False)
            self.assertEqual(detail["items"][0]["cutting"]["state"], "optimized")
            self.assertEqual(detail["items"][0]["cutting"]["batch"], "9701")
            self.assertEqual(detail["items"][0]["cutting"]["optimization"], 89701)

            store.sync_aw_cutting_rows([{**base_cutting, "optimizationStatusCode": 200}])
            self.assertEqual(store.aw_cutting_state("289701", "001")["state"], "released")

            store.sync_aw_cutting_rows([{
                **base_cutting,
                "optimizationStatusCode": 460,
                "optimizationStatusSource": "PROD_OPTI_STATISTICS",
                "optimizationLastChangedAt": "2026-09-03T08:00:00+00:00",
                "optimizationPlateCut": 1,
                "optimizationPlateStockBooked": 1,
                "optimizationPlateLastChangedAt": "2026-09-03T08:00:00+00:00",
                "optimizationPlateLastChangedUser": "Intermac Cutting",
                "cutQuantity": 2,
            }])
            cut_detail = store.get_order_detail("289701", include_production=False)["items"][0]["cutting"]
            self.assertEqual(cut_detail["state"], "cut")
            self.assertTrue(cut_detail["complete"])
            self.assertEqual(cut_detail["optimizationStatusCode"], 460)
            self.assertEqual(cut_detail["optimizationStatusSource"], "PROD_OPTI_STATISTICS")

            # Apply an operator Rush to the already-imported order. It must be visible
            # across synchronized stage copies without changing physical quantities.
            rush = store.submit_priority_work({
                "priorityType": "Rush",
                "jobNumber": str(item["job"]).split()[0],
                "deliveryDate": "2026-09-17",
                "reason": "End-to-end workflow verification",
                "responsible": "Workflow Tester",
                "emailMode": "none",
            }, "admin")
            self.assertTrue(rush["ok"])
            self.assertEqual(rush["action"], "applied")
            inbound_id = f"{delivery_date}-inbound-indian-trail"
            rush_item = store.get_delivery_list(inbound_id)["items"][0]
            self.assertEqual(rush_item["priorityBanner"]["kind"], "rush")
            self.assertEqual(rush_item["priorityDeliveryDate"], "2026-09-17")

            staging_id = f"{delivery_date}-staging-airport"
            outbound_id = f"{delivery_date}-outbound-airport"
            for _ in range(2):
                staged = store.record_scan({
                    "listId": staging_id, "barcode": item["barcode"], "rackCode": rack_code,
                    "user": "admin", "station": "Airport Rd",
                })
            self.assertEqual(staged["items"][0]["scanned"], 2)

            completed = store.complete_rack({"rackCode": rack_code}, "admin")
            completed_rack = next(row for row in completed["racks"] if row["code"] == rack_code)
            self.assertEqual(str(completed_rack["status"]).lower(), "closed")

            # Marking On The Way performs the maintained rack-level Outbound scan.
            departed = store.mark_rack_on_way({"rackCode": rack_code}, "admin")
            departed_rack = next(row for row in departed["racks"] if row["code"] == rack_code)
            self.assertEqual(str(departed_rack["status"]).lower(), "in transit")
            self.assertEqual(store.get_delivery_list(outbound_id)["items"][0]["scanned"], 2)

            # Not On The Way must reverse only this rack's Outbound evidence, reopen
            # the rack, and allow the exact same complete/depart sequence again.
            reopened = store.not_on_way_rack({"rackCode": rack_code}, "admin")
            self.assertEqual(reopened["undonePieceQty"], 2)
            self.assertEqual(store.get_delivery_list(outbound_id)["items"][0]["scanned"], 0)
            store.complete_rack({"rackCode": rack_code}, "admin")
            store.mark_rack_on_way({"rackCode": rack_code}, "admin")
            self.assertEqual(store.get_delivery_list(outbound_id)["items"][0]["scanned"], 2)

            inbound_before = store.get_delivery_list(inbound_id)
            self.assertEqual(inbound_before["items"][0]["bayStatus"], "PreAssigned")
            preassigned_bay = inbound_before["items"][0]["bayCode"]
            self.assertTrue(preassigned_bay)

            for _ in range(2):
                received = store.receive_indian_trail_scan(
                    {"listId": inbound_id, "barcode": item["barcode"], "station": "Indian Trail"},
                    "admin",
                )
                self.assertTrue(received["ok"])
            received_item = store.get_delivery_list(inbound_id)["items"][0]
            self.assertEqual(received_item["scanned"], 2)
            self.assertEqual(received_item["bayStatus"], "Received")
            self.assertEqual(received_item["rackCode"], "")
            assignment_id = int(received_item["bayAssignmentId"])

            # Exercise Bay Map policy states without deleting physical history.
            bays = store.get_bays()
            alternate = next(
                row for row in bays
                if row["bayCode"] != preassigned_bay and str(row.get("status") or "").lower() == "empty"
            )
            alternate_code = str(alternate["bayCode"])
            store.set_bay_status({"bayCode": alternate_code, "status": "ManualAssign", "reason": "Workflow test hold"}, "admin")
            self.assertEqual(next(row for row in store.get_bays() if row["bayCode"] == alternate_code)["sourceStatus"], "ManualAssign")
            store.set_bay_status({"bayCode": alternate_code, "status": "ScanBlocked", "reason": "Workflow test block"}, "admin")
            self.assertEqual(next(row for row in store.get_bays() if row["bayCode"] == alternate_code)["sourceStatus"], "ScanBlocked")
            store.set_bay_status({"bayCode": alternate_code, "status": "Available", "reason": "Workflow test release"}, "admin")

            moved = store.move_bay_assignment({
                "assignmentId": assignment_id, "newBayCode": alternate_code, "reason": "Workflow test move",
            }, "admin")
            self.assertTrue(moved["ok"])
            self.assertEqual(moved["status"], "Received")
            self.assertEqual(store.get_delivery_list(inbound_id)["items"][0]["bayCode"], alternate_code)

            # Clear/restore must be reversible and preserve the exact assignment.
            store.clear_bay_assignment({"assignmentId": assignment_id, "reason": "Workflow test clear"}, "admin")
            cleared_item = store.get_delivery_list(inbound_id)["items"][0]
            self.assertEqual(cleared_item["bayCode"], "")
            self.assertEqual(cleared_item["lastBayCode"], alternate_code)
            restored = store.restore_bay_assignment({"assignmentId": assignment_id, "reason": "Workflow test restore"}, "admin")
            self.assertEqual(restored["bayCode"], alternate_code)

            # Old Bay review, per-user notification claim and snooze all operate on
            # the same active assignment and must not change the physical bay.
            old_assigned_at = (datetime.now(timezone.utc) - timedelta(days=12)).isoformat(timespec="seconds")
            with store.connect() as con:
                con.execute("UPDATE bay_assignments SET assigned_at=? WHERE id=?", (old_assigned_at, assignment_id))
                con.commit()
            stale = store.get_stale_bay_orders()
            stale_row = next(row for row in stale if int(row["assignmentId"]) == assignment_id)
            self.assertGreaterEqual(stale_row["daysOld"], 11)
            first_claim = store.claim_stale_bay_alert("workflow.tester", len(stale))
            second_claim = store.claim_stale_bay_alert("workflow.tester", len(stale))
            self.assertTrue(first_claim["shouldNotify"])
            self.assertFalse(second_claim["shouldNotify"])
            snoozed = store.snooze_stale_bay_orders({"assignmentId": assignment_id, "days": 2}, "admin")
            self.assertTrue(snoozed["ok"])
            self.assertFalse(any(int(row["assignmentId"]) == assignment_id for row in store.get_stale_bay_orders()))
            self.assertTrue(any(int(row["assignmentId"]) == assignment_id for row in store.get_stale_bay_orders(include_snoozed=True)))

            # Reject only one of the two physical pieces. Every synchronized stage and
            # the live bay allocation must lose exactly one piece, not the whole line.
            reject = operations.create_reject({
                "deliveryDate": delivery_date, "order": "289701", "item": "1", "qty": 1,
                "reason": "Workflow Test Breakage", "location": "Tempering",
            }, "workflow.tester")
            self.assertTrue(reject["ok"])
            for list_id in (staging_id, outbound_id, inbound_id):
                self.assertEqual(store.get_delivery_list(list_id)["items"][0]["scanned"], 1)
            with store.connect() as con:
                bay_after_reject = con.execute(
                    "SELECT assigned_qty,status FROM bay_assignments WHERE id=?", (assignment_id,)
                ).fetchone()
            self.assertEqual(int(bay_after_reject["assigned_qty"] or 0), 1)
            self.assertNotIn(str(bay_after_reject["status"]), {"Cleared", "Cancelled"})
            rejected_detail = store.get_order_detail("289701", include_production=False)["items"][0]
            self.assertEqual(rejected_detail["cutting"]["state"], "needs_recut")
            replacement_time = (datetime.fromisoformat(rejected_detail["lastRejectedAt"]) + timedelta(minutes=1)).isoformat(timespec="seconds")

            # A replacement generation is independent from the prior Cut evidence.
            replacement = {
                "sourceRowId": "v0507-floor-generation-1", "orderNr": "289701", "itemNr": "1",
                "bomId": 0, "keyIndex": 1, "batchJobNumber": "9702", "batchStatusCode": 200,
                "batchCreatedAt": replacement_time,
                "optimizationNumber": 89702, "optimizationStatusSource": "PROD_OPTIMIZATION",
                "optimizationSequence": 1, "optimizationSequenceRowId": "v0507-seq-1",
                "optimizationPlateNumber": 1, "quantity": 1, "cutQuantity": 0, "aggregateId": 1000,
            }
            store.sync_aw_cutting_rows([{**replacement, "optimizationStatusCode": 100}])
            self.assertEqual(store.aw_cutting_state("289701", "1")["state"], "optimized")
            store.sync_aw_cutting_rows([{
                **replacement, "optimizationStatusCode": 500, "optimizationStatusSource": "PROD_OPTI_STATISTICS",
                "optimizationPlateCut": 1, "optimizationPlateStockBooked": 1, "cutQuantity": 1,
                "optimizationLastChangedAt": replacement_time,
            }])
            final_cutting = store.get_order_detail("289701", include_production=False)["items"][0]["cutting"]
            self.assertEqual(final_cutting["batch"], "9702")
            self.assertEqual(final_cutting["optimization"], 89702)
            self.assertEqual(final_cutting["state"], "cut")

            # Statistics uses physical first-seen/reject quantities, not multiplied
            # synchronized stage copies or the Rush banner itself.
            report_day = datetime.now(plant_time_zone()).date().isoformat()
            report = store.reports_summary({"dateFrom": report_day, "dateTo": report_day})
            activity = report["productionActivity"]
            self.assertEqual(activity["newProduction"]["pieces"], 2)
            self.assertEqual(activity["newProduction"]["itemCount"], 1)
            self.assertEqual(activity["internalRejects"]["pieces"], 1)
            self.assertEqual(activity["internalRejects"]["eventCount"], 1)

            # Scan the remaining good piece out of its bay and prove the old-bay
            # history survives while no active assignment remains for it.
            scanned_out = store.scan_out_bay_item({"barcode": item["barcode"], "station": "Bay Map"}, "admin")
            self.assertTrue(scanned_out["ok"])
            final_inbound = store.get_delivery_list(inbound_id)["items"][0]
            self.assertEqual(final_inbound["bayCode"], "")
            self.assertEqual(final_inbound["lastBayCode"], alternate_code)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0507_rack_return_and_bay_map_editor_workflow(self) -> None:
        """Cover rack return plus Bay Map create/move/layout/status/delete administration."""
        verification_root = ROOT / "_verification_v0507_rack_bay_editor"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                store.seed_bays(con)
                store.seed_bay_auto_assign_settings(con)
                store.seed_racks(con)
                con.commit()
                racks = con.execute(
                    "SELECT rack_code FROM racks WHERE active=1 AND LOWER(status)='open' ORDER BY id LIMIT 2"
                ).fetchall()
            self.assertGreaterEqual(len(racks), 2)
            rack_code = str(racks[0]["rack_code"])
            second_rack_code = str(racks[1]["rack_code"])

            item = imported_item("289702", "1", 1, "v0507-return:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-19", "items": [item]},
                "fileName": "Delivery List 09-19-2026.xlsx", "user": "admin",
            })
            store.record_scan({
                "listId": "2026-09-19-staging-airport", "barcode": item["barcode"],
                "rackCode": rack_code, "user": "admin", "station": "Airport Rd",
            })
            with store.connect() as con:
                rack_item = con.execute(
                    "SELECT ri.id FROM rack_items ri JOIN racks r ON r.id=ri.rack_id "
                    "WHERE r.rack_code=? AND ri.status='Active' LIMIT 1",
                    (rack_code,),
                ).fetchone()
            self.assertIsNotNone(rack_item)
            store.move_rack_item({"rackItemId": int(rack_item["id"]), "targetRackCode": second_rack_code}, "admin")
            with store.connect() as con:
                moved_code = con.execute(
                    "SELECT r.rack_code FROM rack_items ri JOIN racks r ON r.id=ri.rack_id WHERE ri.id=?",
                    (int(rack_item["id"]),),
                ).fetchone()[0]
            self.assertEqual(str(moved_code), second_rack_code)

            moved_back = store.move_rack_contents({
                "sourceRackCode": second_rack_code,
                "targetRackCode": rack_code,
                "deliveryDate": "2026-09-19",
            }, "admin")
            self.assertTrue(moved_back["ok"])
            self.assertEqual(int(moved_back["movedPieceQty"]), 1)
            with store.connect() as con:
                moved_back_code = con.execute(
                    "SELECT r.rack_code FROM rack_items ri JOIN racks r ON r.id=ri.rack_id WHERE ri.id=?",
                    (int(rack_item["id"]),),
                ).fetchone()[0]
            self.assertEqual(str(moved_back_code), rack_code)

            store.complete_rack({"rackCode": rack_code}, "admin")
            returned = store.return_rack({"rackCode": rack_code}, "admin")
            returned_rack = next(row for row in returned["racks"] if row["code"] == rack_code)
            self.assertEqual(str(returned_rack["status"]).lower(), "open")
            with store.connect() as con:
                active_qty = con.execute(
                    "SELECT COALESCE(SUM(ri.qty),0) FROM rack_items ri JOIN racks r ON r.id=ri.rack_id WHERE r.rack_code=? AND ri.status='Active'",
                    (rack_code,),
                ).fetchone()[0]
            self.assertEqual(int(active_qty or 0), 0)

            created = store.create_bays({
                "mapSection": "V0507 TEST GROUP", "bayCategory": "Standard", "prefix": "V507", "count": 2,
                "layoutRow": 40, "layoutCol": 40,
            }, "admin")
            self.assertEqual(len(created["created"]), 2)
            first_code, second_code = created["created"]
            self.assertTrue(any(row.get("mapSection") == "V0507 TEST GROUP" for row in store.get_bays()))

            store.update_bay_layout({
                "bayCode": first_code, "displayName": "V507 Primary", "mapSection": "V0507 TEST GROUP",
                "bayCategory": "Oversize", "layoutRow": 41, "layoutCol": 42, "capacityQty": 3, "active": True,
            }, "admin")
            updated = next(row for row in store.get_bays() if row["bayCode"] == first_code)
            self.assertEqual(updated["displayName"], "V507 Primary")
            self.assertEqual(updated["bayCategory"], "Oversize")
            self.assertEqual(int(updated["capacityQty"]), 3)

            positioned = store.set_bay_group_position({
                "mapSection": "V0507 TEST GROUP", "layoutRow": 45, "layoutCol": 46,
            }, "admin")
            self.assertTrue(positioned["ok"])
            moved = store.move_bay_group({
                "mapSection": "V0507 TEST GROUP", "rowDelta": 2, "colDelta": -1,
            }, "admin")
            self.assertEqual(moved["moved"], 2)

            store.set_bay_status({"bayCode": second_code, "status": "ManualAssign", "reason": "Editor test"}, "admin")
            store.set_bay_status({"bayCode": second_code, "status": "Available", "reason": "Editor test complete"}, "admin")
            deleted_one = store.delete_bay({"bayCode": second_code}, "admin")
            self.assertTrue(deleted_one["ok"])
            deleted_group = store.delete_bay_group({"mapSection": "V0507 TEST GROUP"}, "admin")
            self.assertEqual(deleted_group["deletedCount"], 1)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v0516_aw_plant_time_uses_eastern_dst_and_preserves_absolute_values(self) -> None:
        self.assertEqual(normalize_aw_plant_timestamp("2026-09-03T05:04:41"), "2026-09-03T09:04:41+00:00")
        self.assertEqual(normalize_aw_plant_timestamp("2026-12-03T05:04:41"), "2026-12-03T10:04:41+00:00")
        self.assertEqual(normalize_aw_plant_timestamp("2026-09-03T05:04:41+00:00"), "2026-09-03T05:04:41+00:00")
        self.assertEqual(parse_aw_plant_timestamp("2026-09-03T05:04:41").timestamp(), datetime(2026, 9, 3, 9, 4, 41, tzinfo=timezone.utc).timestamp())

    def test_v0516_aw_reject_and_cutting_sync_normalize_naive_plant_clocks(self) -> None:
        verification_root = ROOT / "_verification_v0516_aw_eastern_sync"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True)
        try:
            store = self.make_store(verification_root)
            reject = {
                "awRowId": "v516-reject-1", "orderNr": "298516", "itemNr": "1", "bomId": 1, "keyIndex": 0,
                "quantity": 1, "breakageDate": "2026-09-03T05:04:41", "reasonCode": "137", "reasonLabel": "Chipped",
                "locationCode": "5", "locationLabel": "Grinding", "sourceLastChangedAt": "2026-09-03T05:05:41",
            }
            store.sync_aw_reject_rows([reject])
            with store.connect() as con:
                source = con.execute("SELECT breakage_date, last_changed_at FROM aw_reject_source_rows WHERE aw_row_id=?", ("v516-reject-1",)).fetchone()
                logical = con.execute("SELECT breakage_date FROM aw_reject_events WHERE order_no='298516'").fetchone()
            self.assertEqual(source["breakage_date"], "2026-09-03T09:04:41+00:00")
            self.assertEqual(source["last_changed_at"], "2026-09-03T09:05:41+00:00")
            self.assertEqual(logical["breakage_date"], "2026-09-03T09:04:41+00:00")

            store.sync_aw_cutting_rows([{
                "orderNr": "298516", "itemNr": "1", "keyIndex": 0, "batchJobNumber": "9516",
                "batchStatusCode": 460, "batchDescription": "Booked", "batchCreatedAt": "2026-09-03T06:00:00",
                "batchLastChangedAt": "2026-09-03T06:10:00", "optimizationNumber": 8516,
                "optimizationStatusCode": 200, "optimizationDate": "2026-09-03T06:05:00",
                "optimizationLastChangedAt": "2026-09-03T06:08:00", "quantity": 1, "cutQuantity": 0,
            }])
            with store.connect() as con:
                row = con.execute("SELECT batch_creation_at, optimization_date FROM aw_cutting_generations WHERE order_no='298516'").fetchone()
            self.assertEqual(row["batch_creation_at"], "2026-09-03T10:00:00+00:00")
            self.assertEqual(row["optimization_date"], "2026-09-03T10:05:00+00:00")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0516_migration_19_repairs_legacy_aw_clocks_and_is_repeat_safe(self) -> None:
        verification_root = ROOT / "_verification_v0516_migration19"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True)
        try:
            store = self.make_store(verification_root)
            delivery_date = "2026-09-08"
            item = imported_item("298519", "1", 1, "v516-m19:1")
            store.import_delivery_list({"payload": {"deliveryDate": delivery_date, "items": [item]}, "fileName": "Delivery List 09-08-2026.xlsx", "user": "admin"})
            raw_reject = {
                "awRowId": "v516-m19-reject", "orderNr": "298519", "itemNr": "1", "bomId": 1, "keyIndex": 0,
                "quantity": 1, "breakageDate": "2026-09-03T05:04:41", "reasonCode": "137", "reasonLabel": "Chipped",
                "locationCode": "5", "locationLabel": "Grinding", "sourceLastChangedAt": "2026-09-03T05:05:41",
            }
            store.sync_aw_reject_rows([raw_reject])
            store.sync_aw_cutting_rows([{
                "orderNr": "298519", "itemNr": "1", "keyIndex": 0, "batchJobNumber": "9519",
                "batchStatusCode": 460, "batchDescription": "Booked", "batchCreatedAt": "2026-09-03T06:00:00",
                "optimizationNumber": 8519, "optimizationStatusCode": 200,
                "optimizationDate": "2026-09-03T06:05:00", "optimizationPlateLastChangedAt": "2026-09-03T06:08:00",
                "quantity": 1, "cutQuantity": 0,
            }])
            with store.connect() as con:
                event_key = con.execute("SELECT event_key FROM aw_reject_source_rows WHERE aw_row_id='v516-m19-reject'").fetchone()[0]
                # Simulate schema-18 storage: A+W wall clock was tagged +00:00,
                # while preserved source JSON still contains the original naive SQL clock.
                con.execute("UPDATE aw_reject_source_rows SET breakage_date='2026-09-03T05:04:41+00:00', last_changed_at='2026-09-03T05:05:41+00:00' WHERE aw_row_id='v516-m19-reject'")
                con.execute("UPDATE aw_reject_events SET breakage_date='2026-09-03T05:04:41+00:00', source_last_changed_at='2026-09-03T05:05:41+00:00' WHERE event_key=?", (event_key,))
                con.execute("UPDATE reject_events SET rejected_at='2026-09-03T05:04:41+00:00' WHERE source_type='aw' AND source_external_key=?", (event_key,))
                cutting_payload = con.execute("SELECT source_payload_json FROM aw_cutting_generations WHERE order_no='298519'").fetchone()[0]
                payload = json.loads(cutting_payload)
                payload.setdefault("cutEvidence", {})["plateLastChangedAt"] = "2026-09-03T06:08:00"
                con.execute("UPDATE aw_cutting_generations SET batch_creation_at='2026-09-03T06:00:00', optimization_date='2026-09-03T06:05:00', source_payload_json=? WHERE order_no='298519'", (json.dumps(payload),))
                con.commit()
                _migration_019_v516_aw_eastern_timestamp_contract(con)
                first = con.execute("SELECT breakage_date, last_changed_at FROM aw_reject_source_rows WHERE aw_row_id='v516-m19-reject'").fetchone()
                mirrored = con.execute("SELECT rejected_at FROM reject_events WHERE source_type='aw' AND source_external_key=?", (event_key,)).fetchone()
                cutting = con.execute("SELECT batch_creation_at, optimization_date, source_payload_json FROM aw_cutting_generations WHERE order_no='298519'").fetchone()
                self.assertEqual(first["breakage_date"], "2026-09-03T09:04:41+00:00")
                self.assertEqual(first["last_changed_at"], "2026-09-03T09:05:41+00:00")
                self.assertEqual(mirrored["rejected_at"], "2026-09-03T09:04:41+00:00")
                self.assertEqual(cutting["batch_creation_at"], "2026-09-03T10:00:00+00:00")
                self.assertEqual(cutting["optimization_date"], "2026-09-03T10:05:00+00:00")
                self.assertEqual(json.loads(cutting["source_payload_json"])["cutEvidence"]["plateLastChangedAt"], "2026-09-03T10:08:00+00:00")
                snapshot = tuple(first) + (mirrored["rejected_at"], cutting["batch_creation_at"], cutting["optimization_date"], cutting["source_payload_json"])
                _migration_019_v516_aw_eastern_timestamp_contract(con)
                second = con.execute("SELECT breakage_date, last_changed_at FROM aw_reject_source_rows WHERE aw_row_id='v516-m19-reject'").fetchone()
                mirrored2 = con.execute("SELECT rejected_at FROM reject_events WHERE source_type='aw' AND source_external_key=?", (event_key,)).fetchone()
                cutting2 = con.execute("SELECT batch_creation_at, optimization_date, source_payload_json FROM aw_cutting_generations WHERE order_no='298519'").fetchone()
                self.assertEqual(snapshot, tuple(second) + (mirrored2["rejected_at"], cutting2["batch_creation_at"], cutting2["optimization_date"], cutting2["source_payload_json"]))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0516_persistent_exact_sketch_page_cache_survives_source_outage(self) -> None:
        verification_root = ROOT / "_verification_v0516_sketch_memory"
        shutil.rmtree(verification_root, ignore_errors=True)
        sketches_dir = verification_root / "Sketches"
        sketches_dir.mkdir(parents=True)
        try:
            from reportlab.pdfgen import canvas

            sketch_path = sketches_dir / "298516 Sketch.pdf"
            pdf = canvas.Canvas(str(sketch_path))
            pdf.drawString(180, 400, "298516.1 DENVER")
            pdf.save()
            config = replace(
                load_config(ROOT), root=verification_root, data_dir=verification_root / "data",
                hardware_lists_dir=verification_root / "Hardware Lists", sketches_dir=sketches_dir,
                programs_dir=verification_root / "Programs", completed_wj_dir=verification_root / "Completed WJ",
            )
            for folder in (config.data_dir, config.hardware_lists_dir, config.programs_dir, config.completed_wj_dir):
                Path(folder).mkdir(parents=True, exist_ok=True)
            service = ProductionFileService(config)
            assets = service.assets("sketch", refresh=True)
            self.assertEqual(len(assets), 1)
            cached = service.cached_sketch_page(assets[0].asset_id, 1)
            self.assertIsNotNone(cached)
            cached_path = cached[0]
            self.assertTrue(cached_path.exists())
            sketch_path.unlink()
            offline = service.cached_sketch_page(assets[0].asset_id, 1)
            self.assertIsNotNone(offline)
            self.assertEqual(offline[0], cached_path)
            self.assertGreater(cached_path.stat().st_size, 0)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v0507_route_destination_scan_matrix_and_statistics_dedupe(self) -> None:
        """Exercise every maintained delivery route through staging/outbound/destination scans.

        The test intentionally imports CPU, DTC, Greenville and Indian Trail together so
        shared Staging/Outbound lists must contain all physical work while each destination
        list contains only its own route. Statistics must still count each Order/Item once.
        """
        verification_root = ROOT / "_verification_v0507_route_matrix"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                store.seed_racks(con)
                store.seed_bays(con)
                store.seed_bay_auto_assign_settings(con)
                con.commit()
                rack_rows = con.execute(
                    "SELECT rack_code FROM racks WHERE active=1 AND LOWER(status)='open' ORDER BY id LIMIT 4"
                ).fetchall()
            self.assertGreaterEqual(len(rack_rows), 4)
            rack_codes = [str(row["rack_code"]) for row in rack_rows]

            delivery_date = datetime.now(plant_time_zone()).date().isoformat()
            route_specs = [
                ("CPU", "customer-pickup", "cpu", 1),
                ("DTC", "dtc", "dtc", 2),
                ("GNV", "bfs-greenville", "greenville", 3),
                ("IT", "inbound-indian-trail", "indian_trail", 4),
            ]
            items = []
            for index, (route, _suffix, _preset, qty) in enumerate(route_specs, start=1):
                item = imported_item(f"28971{index}", "1", qty, f"v0507-route:{route.lower()}")
                item["route"] = route
                item["sourceRoute"] = route
                item["product"] = '1/4" Clear Annealed'
                item["dimensions"] = f'{30 + index}" x {40 + index}"'
                items.append(item)

            store.import_delivery_list({
                "payload": {"deliveryDate": delivery_date, "items": items},
                "fileName": f"Delivery List {delivery_date}.xlsx",
                "user": "admin",
            })

            staging_id = f"{delivery_date}-staging-airport"
            outbound_id = f"{delivery_date}-outbound-airport"
            staging = store.get_delivery_list(staging_id)
            outbound = store.get_delivery_list(outbound_id)
            self.assertEqual({row["order"] for row in staging["items"]}, {row["order"] for row in items})
            self.assertEqual({row["order"] for row in outbound["items"]}, {row["order"] for row in items})

            for route_index, (item, (route, suffix, expected_preset, qty)) in enumerate(zip(items, route_specs)):
                rack_code = rack_codes[route_index]
                destination_id = f"{delivery_date}-{suffix}"
                destination = store.get_delivery_list(destination_id)
                self.assertEqual(destination["meta"]["stagePreset"], expected_preset)
                self.assertEqual(len(destination["items"]), 1)
                self.assertEqual(destination["items"][0]["order"], item["order"])
                self.assertEqual(destination["items"][0]["qty"], qty)

                for _ in range(qty):
                    store.record_scan({
                        "listId": staging_id,
                        "barcode": item["barcode"],
                        "rackCode": rack_code,
                        "user": "admin",
                        "station": "Airport Rd",
                    })
                    store.record_scan({
                        "listId": outbound_id,
                        "barcode": item["barcode"],
                        "user": "admin",
                        "station": "Airport Rd",
                    })

                if route == "IT":
                    for _ in range(qty):
                        result = store.receive_indian_trail_scan({
                            "listId": destination_id,
                            "barcode": item["barcode"],
                            "station": "Indian Trail",
                        }, "admin")
                        self.assertTrue(result["ok"])
                else:
                    for _ in range(qty):
                        store.record_scan({
                            "listId": destination_id,
                            "barcode": item["barcode"],
                            "user": "admin",
                            "station": route,
                        })

                final_destination = store.get_delivery_list(destination_id)["items"][0]
                self.assertEqual(final_destination["scanned"], qty)
                detail = store.get_order_detail(item["order"], include_production=False)["items"][0]
                stage_by_id = {row["listId"]: row for row in detail["stages"]}
                self.assertEqual(stage_by_id[staging_id]["scanned"], qty)
                self.assertEqual(stage_by_id[outbound_id]["scanned"], qty)
                self.assertEqual(stage_by_id[destination_id]["scanned"], qty)

            # 1 + 2 + 3 + 4 = 10 physical pieces. Synchronized stage copies must not
            # multiply the production ledger or the per-glass total.
            report = store.reports_summary({
                "dateFrom": delivery_date,
                "dateTo": delivery_date,
                "detailRows": "0",
            })
            production = report["productionActivity"]["newProduction"]
            self.assertEqual(production["pieces"], 10)
            self.assertEqual(production["itemCount"], 4)
            self.assertEqual(production["orderCount"], 4)
            self.assertEqual(sum(int(row["pieces"]) for row in production["byGlass"]), 10)
            self.assertEqual(production["rows"], [])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v518_aw_fabrication_hints_batch_current_label_context(self) -> None:
        verification_root = ROOT / "_verification_aw_fabrication_v518"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            now = "2026-09-09T14:00:00+00:00"
            payload = json.dumps({
                "labelContext": {
                    # Exercise request-product fallback so a sparse A+W label row
                    # can still apply the Mirror + cutout shop rule.
                    "productDescription": "",
                    "processRows": [{"processProductDescription": "Internal Cutout Macro"}],
                }
            })
            with store.connect() as con:
                con.execute(
                    """
                    INSERT INTO aw_cutting_generations (
                        order_no, item_no, key_index, batch_job_number,
                        source_payload_json, first_seen_at, last_seen_at, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("238445", "001", 0, "6501", payload, now, now, now),
                )
                con.commit()
            key = "238445:001:JOB"
            hints = store.aw_fabrication_hints_for_requests([{
                "key": key,
                "order": "238445",
                "item": "001",
                "job": "JOB",
                "product": "1/4 Mirror",
                "lastRejectedAt": "",
            }])
            self.assertIn(key, hints)
            self.assertEqual(hints[key]["productDescription"], "1/4 Mirror")
            self.assertEqual(hints[key]["processRows"][0]["processProductDescription"], "Internal Cutout Macro")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v524_inventory_frozen_snapshot_scan_reconcile_cycle_and_history(self) -> None:
        verification_root = ROOT / "_verification_v524_inventory_flow"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        user = {"username": "admin", "displayName": "Inventory Admin", "stageAccess": ["*"]}
        try:
            store = self.make_store(verification_root)
            first = imported_item("724001", "1", 3, "v0524-inventory:clear38")
            first.update({"dimensions": '36" x 72"', "product": '3/8" Clear Tempered', "barcode": "T200724001001000"})
            second = imported_item("724002", "1", 2, "v0524-inventory:clear14")
            second.update({"dimensions": '24" x 48"', "product": '1/4" Clear Tempered', "barcode": "T200724002001000"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-10", "items": [first, second]},
                "fileName": "Delivery List 09-10-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_cutting_rows([
                {
                    "sourceRowId": "v524-cut-1", "orderNr": "724001", "itemNr": "1", "bomId": 0,
                    "keyIndex": 1, "batchJobNumber": "95241", "batchStatusCode": 500,
                    "batchCreatedAt": "2026-09-10T08:00:00", "optimizationNumber": 95241,
                    "optimizationStatusCode": 500, "quantity": 3, "cutQuantity": 3, "aggregateId": 1000,
                    "cuttingBookingAt": "2026-09-10T08:10:00", "cuttingBookingEmployee": "CUT",
                    "cuttingBookingRowId": "v524-book-1",
                },
                {
                    "sourceRowId": "v524-cut-2", "orderNr": "724002", "itemNr": "1", "bomId": 0,
                    "keyIndex": 1, "batchJobNumber": "95242", "batchStatusCode": 500,
                    "batchCreatedAt": "2026-09-10T08:00:00", "optimizationNumber": 95242,
                    "optimizationStatusCode": 500, "quantity": 2, "cutQuantity": 2, "aggregateId": 1000,
                    "cuttingBookingAt": "2026-09-10T08:11:00", "cuttingBookingEmployee": "CUT",
                    "cuttingBookingRowId": "v524-book-2",
                },
            ])

            catalog = store.inventory_catalog(user)
            self.assertEqual(len(catalog["itemMappings"]), 15)
            mapping = {row["glassLabel"]: row["itemId"] for row in catalog["itemMappings"]}
            self.assertEqual(mapping["3/8 Clear"], "G38CLR")
            self.assertEqual(mapping["1/4 Clear"], "G14CLR")

            session = store.start_inventory_session({"location": "airport_rd", "inventoryType": "full"}, user)
            self.assertEqual(session["expectedLineCount"], 2)
            self.assertEqual(session["expectedQty"], 5)
            self.assertAlmostEqual(session["expectedTotalSqft"], 70.0)

            system = store.get_inventory_session_items(session["id"], "system", user)
            by_order = {row["order"]: row for row in system["items"]}
            self.assertEqual(by_order["724001"]["itemId"], "G38CLR")
            self.assertEqual(by_order["724001"]["qty"], 3)
            self.assertAlmostEqual(by_order["724001"]["sqftEach"], 18.0)
            self.assertAlmostEqual(by_order["724001"]["totalSqft"], 54.0)
            self.assertEqual(by_order["724002"]["itemId"], "G14CLR")
            self.assertAlmostEqual(by_order["724002"]["totalSqft"], 16.0)

            # Production moves after the count begins must not change the frozen target.
            with store.connect() as con:
                con.execute(
                    "UPDATE line_items SET scanned_qty=2 WHERE list_id=? AND order_no=?",
                    ("2026-09-10-outbound-airport", "724001"),
                )
                con.commit()
            frozen = store.get_inventory_session(session["id"], user)
            self.assertEqual(frozen["expectedQty"], 5)
            with store.connect() as con:
                current_airport = store._inventory_expected_rows_con(con, "airport_rd", {})
                current_indian_trail = store._inventory_expected_rows_con(con, "indian_trail", {})
            current_airport_by_order = {row["order"]: row for row in current_airport}
            current_it_by_order = {row["order"]: row for row in current_indian_trail}
            self.assertEqual(current_airport_by_order["724001"]["qty"], 1)
            self.assertEqual(current_it_by_order["724001"]["qty"], 2)
            self.assertEqual(current_it_by_order["724001"]["sourceReason"], "Airport Outbound; in transit to Indian Trail")

            # v0.537: one scanner trigger counts one physical pane even when the
            # frozen line expects multiple identical panes. Repeating the same
            # barcode is valid until the frozen target is reached, then blocked.
            scanned = store.record_inventory_scan(session["id"], first["barcode"], user)
            self.assertTrue(scanned["ok"])
            self.assertTrue(scanned["matchedExpected"])
            self.assertEqual(scanned["scan"]["qty"], 1)
            self.assertEqual(scanned["countedQty"], 1)
            self.assertEqual(scanned["expectedQty"], 3)
            self.assertEqual(scanned["remainingQty"], 2)
            self.assertAlmostEqual(scanned["scan"]["totalSqft"], 18.0)
            partial = store.get_inventory_session_items(session["id"], "reconciliation", user)
            first_partial = next(row for row in partial["items"] if (row.get("system") or {}).get("order") == "724001")
            self.assertEqual(first_partial["status"], "partial")
            self.assertIn("Counted 1/3", first_partial["differences"][0])

            second_scan = store.record_inventory_scan(session["id"], first["barcode"], user)
            self.assertEqual(second_scan["countedQty"], 2)
            self.assertEqual(second_scan["remainingQty"], 1)
            # Scanner corrections undo one counted pane instead of deleting the
            # aggregate row for all identical pieces.
            corrected = store.remove_inventory_scan(session["id"], scanned["scan"]["id"], {"reason": "Double trigger correction"}, user)
            self.assertEqual(corrected["scannedQty"], 1)
            second_scan = store.record_inventory_scan(session["id"], first["barcode"], user)
            self.assertEqual(second_scan["countedQty"], 2)
            third_scan = store.record_inventory_scan(session["id"], first["barcode"], user)
            self.assertEqual(third_scan["countedQty"], 3)
            self.assertEqual(third_scan["remainingQty"], 0)
            self.assertTrue(third_scan["lineComplete"])
            self.assertEqual(third_scan["scan"]["qty"], 3)
            self.assertAlmostEqual(third_scan["scan"]["totalSqft"], 54.0)
            duplicate = store.record_inventory_scan(session["id"], first["barcode"], user)
            self.assertFalse(duplicate["ok"])
            self.assertTrue(duplicate["duplicate"])
            self.assertEqual(duplicate["countedQty"], 3)
            self.assertEqual(duplicate["expectedQty"], 3)

            manual = store.record_inventory_manual_entry(session["id"], {
                "order": "799999", "item": "1", "jobNr": "MANUAL-1", "customer": "MANUAL FLOOR PIECE",
                "glassType": "1/4 Clear", "dimensions": '24" x 48"', "qty": 3,
                "notes": "Found physically; not in frozen system snapshot",
            }, user)
            self.assertTrue(manual["ok"])
            self.assertFalse(manual["matchedExpected"])
            self.assertEqual(manual["scan"]["itemId"], "G14CLR")
            self.assertAlmostEqual(manual["scan"]["sqftEach"], 8.0)
            self.assertAlmostEqual(manual["scan"]["totalSqft"], 24.0)

            completed = store.complete_inventory_session(session["id"], {"notes": "Physical count complete"}, user)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["statusCounts"], {
                "matched": 1, "mismatch": 0, "partial": 0, "missingPhysical": 1, "notInSystem": 1,
            })
            reconcile = store.get_inventory_session_items(session["id"], "reconciliation", user)
            statuses = [row["status"] for row in reconcile["items"]]
            self.assertIn("matched", statuses)
            self.assertIn("missing_physical", statuses)
            self.assertIn("not_in_system", statuses)
            missing = next(row for row in reconcile["items"] if row["status"] == "missing_physical")
            self.assertEqual(missing["system"]["order"], "724002")
            unexpected = next(row for row in reconcile["items"] if row["status"] == "not_in_system")
            self.assertEqual(unexpected["physical"]["order"], "799999")

            with self.assertRaisesRegex(ValueError, "immutable"):
                store.remove_inventory_scan(session["id"], scanned["scan"]["id"], {"reason": "late edit"}, user)

            history = store.list_inventory_sessions(user, "airport_rd")
            self.assertEqual(history[0]["id"], session["id"])
            self.assertEqual(history[0]["status"], "completed")

            workbook = store.export_inventory_xlsx(session["id"], user)
            self.assertTrue(zipfile.is_zipfile(BytesIO(workbook)))
            with zipfile.ZipFile(BytesIO(workbook)) as archive:
                workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
                self.assertIn('name="Summary"', workbook_xml)
                self.assertIn('name="Physical Scans"', workbook_xml)
                self.assertIn('name="System Snapshot"', workbook_xml)
                self.assertIn('name="Reconciliation"', workbook_xml)
                physical_xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
                self.assertIn("Scanned Date/Time (ET)", physical_xml)
                self.assertIn("Total SQFT", physical_xml)
                self.assertIn("G14CLR", physical_xml)

            cycle = store.start_inventory_session({
                "location": "airport_rd", "inventoryType": "cycle",
                "cycleFilter": {"field": "item_id", "value": "G14CLR"},
            }, user)
            self.assertEqual(cycle["inventoryType"], "cycle")
            self.assertEqual(cycle["expectedQty"], 2)
            cycle_items = store.get_inventory_session_items(cycle["id"], "system", user)["items"]
            self.assertEqual({row["itemId"] for row in cycle_items}, {"G14CLR"})
            store.cancel_inventory_session(cycle["id"], {"reason": "Cycle test complete"}, user)

            indian = store.start_inventory_session({"location": "indian_trail", "inventoryType": "full"}, user)
            self.assertEqual(indian["expectedQty"], 2)
            indian_items = store.get_inventory_session_items(indian["id"], "system", user)["items"]
            self.assertEqual(indian_items[0]["order"], "724001")
            self.assertIn("in transit", indian_items[0]["sourceReason"].lower())
            store.cancel_inventory_session(indian["id"], {"reason": "Indian Trail test complete"}, user)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)



    def test_v525_inventory_count_does_not_mutate_normal_scan_progress(self) -> None:
        verification_root = ROOT / "_verification_v525_inventory_scan_isolation"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        user = {"username": "admin", "displayName": "Inventory Admin", "stageAccess": ["*"]}
        try:
            store = self.make_store(verification_root)
            item = imported_item("725001", "1", 2, "v0525-inventory-isolation:clear14")
            item.update({"dimensions": '24" x 48"', "product": '1/4" Clear Tempered', "barcode": "T200725001001000"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-10", "items": [item]},
                "fileName": "Delivery List 09-10-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_cutting_rows([{
                "sourceRowId": "v525-cut-1", "orderNr": "725001", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "batchJobNumber": "95251", "batchStatusCode": 500,
                "batchCreatedAt": "2026-09-10T08:00:00", "optimizationNumber": 95251,
                "optimizationStatusCode": 500, "quantity": 2, "cutQuantity": 2, "aggregateId": 1000,
                "cuttingBookingAt": "2026-09-10T08:10:00", "cuttingBookingEmployee": "CUT",
                "cuttingBookingRowId": "v525-book-1",
            }])

            def normal_scan_state():
                with store.connect() as con:
                    line_rows = [tuple(row) for row in con.execute(
                        "SELECT id, list_id, scanned_qty FROM line_items ORDER BY id"
                    ).fetchall()]
                    event_rows = [tuple(row) for row in con.execute(
                        "SELECT id, list_id, line_item_id, event_type, qty_delta FROM scan_events ORDER BY id"
                    ).fetchall()]
                    return line_rows, event_rows

            before_lines, before_events = normal_scan_state()
            session = store.start_inventory_session({"location": "airport_rd", "inventoryType": "full"}, user)
            counted = store.record_inventory_scan(session["id"], item["barcode"], user)
            self.assertTrue(counted["ok"])
            self.assertTrue(counted["matchedExpected"])
            manual = store.record_inventory_manual_entry(session["id"], {
                "order": "799525", "item": "1", "jobNr": "MANUAL-525", "customer": "PHYSICAL ONLY",
                "glassType": "1/4 Clear", "dimensions": '24" x 48"', "qty": 1,
            }, user)
            self.assertTrue(manual["ok"])
            store.complete_inventory_session(session["id"], {"notes": "Isolation regression"}, user)
            after_lines, after_events = normal_scan_state()

            self.assertEqual(after_lines, before_lines, "Inventory counting must not change normal delivery scanned_qty")
            self.assertEqual(after_events, before_events, "Inventory counting must not append normal delivery scan_events")
            with store.connect() as con:
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM inventory_scans WHERE session_id=?", (session["id"],)).fetchone()[0]), 2)
                self.assertGreaterEqual(int(con.execute("SELECT COUNT(*) FROM audit_events WHERE entity_type='inventory_scan'").fetchone()[0]), 2)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v528_glass_profile_persists_restart_and_rejects_duplicate_color(self) -> None:
        verification_root = ROOT / "_verification_v528_glass_persistence"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.upsert_glass_profile({
                "value": "V528 Test Glass", "label": "V528 Test Glass",
                "rate": 7.25, "color": "#3568A8",
            }, "admin")

            # Simulate an application restart by constructing a fresh store object
            # against the same SQLite file. The Lookup Manager must read the
            # durable manual rows instead of regenerating/forgetting the color.
            restarted = SQLiteDeliveryStore(store.config)
            lookups = restarted.get_manual_edit_lookups()
            products = {row["value"]: row for row in lookups["products"]}
            colors = {row["value"]: row for row in lookups["glassColors"]}
            costs = {row["value"]: row for row in lookups["glassCosts"]}
            self.assertIn("V528 Test Glass", products)
            self.assertEqual(colors["V528 Test Glass"]["color"], "#3568A8")
            self.assertAlmostEqual(float(costs["V528 Test Glass"]["rate"]), 7.25)

            with self.assertRaisesRegex(ValueError, "already used"):
                restarted.upsert_glass_profile({
                    "value": "V528 Other Glass", "label": "V528 Other Glass",
                    "color": "#3568A8",
                }, "admin")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v528_progress_and_inventory_completion_do_not_create_locations(self) -> None:
        verification_root = ROOT / "_verification_v528_completion_no_flood"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        user = {"username": "admin", "displayName": "Completion Admin", "stageAccess": ["*"]}
        try:
            store = self.make_store(verification_root)
            manual = imported_item("728001", "1", 2, "v0528-progress:1")
            manual.update({"dimensions": '24" x 48"', "product": '1/4" Clear Tempered', "barcode": "T200728001001000"})
            inventory = imported_item("728002", "1", 2, "v0528-inventory-complete:1")
            inventory.update({"dimensions": '36" x 72"', "product": '3/8" Clear Tempered', "barcode": "T200728002001000"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-18", "items": [manual, inventory]},
                "fileName": "Delivery List 09-18-2026.xlsx", "user": "admin",
            })
            store.sync_aw_cutting_rows([{
                "sourceRowId": "v528-cut-2", "orderNr": "728002", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "batchJobNumber": "95282", "batchStatusCode": 500,
                "batchCreatedAt": "2026-09-11T08:00:00", "optimizationNumber": 95282,
                "optimizationStatusCode": 500, "optimizationDate": "2026-09-11T07:45:00",
                "optimizationSheetCount": 6, "quantity": 2, "cutQuantity": 2, "aggregateId": 1000,
                "productDescription": '3/8" Clear Tempered',
                "cuttingBookingAt": "2026-09-11T08:10:00", "cuttingBookingEmployee": "CUT",
                "cuttingBookingRowId": "v528-book-2",
            }], optimization_plates=[{
                "optimizationNumber": 95282,
                "optimizationDate": "2026-09-11T07:45:00",
                "plateNumber": plate_number,
                "lengthUnits": 3072,
                "heightUnits": 4160,
                "cut": 1,
                "stockBooked": 1,
            } for plate_number in range(1, 7)])

            with store.connect() as con:
                before_rack = int(con.execute("SELECT COUNT(*) FROM rack_items").fetchone()[0])
                before_bay = int(con.execute("SELECT COUNT(*) FROM bay_assignments").fetchone()[0])

            advanced = store.advance_delivery_progress({
                "scope": "order", "target": "complete",
                "deliveryDate": "2026-09-18", "order": "728001",
            }, "admin")
            self.assertTrue(advanced["ok"])
            with store.connect() as con:
                rows = con.execute(
                    "SELECT qty, scanned_qty FROM line_items li JOIN delivery_lists dl ON dl.id=li.list_id "
                    "WHERE dl.delivery_date=? AND li.order_no=?",
                    ("2026-09-18", "728001"),
                ).fetchall()
                self.assertTrue(rows)
                self.assertTrue(all(int(row["scanned_qty"] or 0) == int(row["qty"] or 0) for row in rows))
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM rack_items").fetchone()[0]), before_rack)
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM bay_assignments").fetchone()[0]), before_bay)

            session = store.start_inventory_session({"location": "airport_rd", "inventoryType": "full"}, user)
            system_orders = {row["order"] for row in store.get_inventory_session_items(session["id"], "system", user)["items"]}
            self.assertIn("728002", system_orders)
            completed = store.complete_inventory_system_orders(session["id"], {"orders": ["728002"]}, user)
            self.assertTrue(completed["ok"])
            with store.connect() as con:
                rows = con.execute(
                    "SELECT qty, scanned_qty FROM line_items li JOIN delivery_lists dl ON dl.id=li.list_id "
                    "WHERE dl.delivery_date=? AND li.order_no=?",
                    ("2026-09-18", "728002"),
                ).fetchall()
                self.assertTrue(rows)
                self.assertTrue(all(int(row["scanned_qty"] or 0) == int(row["qty"] or 0) for row in rows))
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM rack_items").fetchone()[0]), before_rack)
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM bay_assignments").fetchone()[0]), before_bay)

            # The same retained A+W optimization should appear once in the new
            # stock-sheet statistic, including its configured stock size/email.
            store.save_sheet_usage_settings({"profiles": {
                '3/8" Clear Tempered': {"sheetSize": '96" x 130"', "emails": ["inventory@example.com"]}
            }}, "admin")
            report = store.reports_summary({"dateFrom": "2026-09-11", "dateTo": "2026-09-11", "detailRows": 1})
            self.assertEqual(report["sheetUsage"]["totalSheets"], 6)
            self.assertEqual(report["sheetUsage"]["optimizationCount"], 1)
            self.assertEqual(report["sheetUsage"]["byGlass"][0]["sheetSize"], '96" x 130"')
            self.assertEqual(report["sheetUsage"]["byGlass"][0]["emails"], ["inventory@example.com"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v540_superseded_refresh_recovers_current_exact_remake_pair_idempotently(self) -> None:
        verification_root = ROOT / "_verification_v540_superseded_refresh"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            normal = imported_item("740001", "1", 1, "v540-normal:1")
            normal.update({"job": "900100 TEST HOME", "customer": "TEST BUILDER", "product": '1/4" Clear Tempered', "dimensions": '30" x 79"'})
            remake = imported_item("740002", "1", 1, "v540-remake:1")
            remake.update({"job": "900100 TEST HOME", "customer": "TEST BUILDER", "product": '1/4" Clear Tempered', "dimensions": '30" x 79"', "processState": "External Remake New Line", "queueState": "RM"})
            unrelated = imported_item("740003", "1", 1, "v540-unrelated:1")
            unrelated.update({"job": "900100 TEST HOME", "customer": "TEST BUILDER", "product": '1/4" Clear Tempered', "dimensions": '31" x 79"', "processState": "External Remake New Line", "queueState": "RM"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-15", "items": [normal, remake, unrelated]},
                "fileName": "Delivery List 09-15-2026.xlsx", "user": "admin",
            })

            first = store.detect_superseded_order_candidates_from_scanner("2026-09-15", "admin")
            self.assertEqual(first["scannerCandidateCount"], 1)
            self.assertEqual(first["insertedCount"], 1)
            reviews = store.list_superseded_order_reviews(status="", include_inactive=True)["reviews"]
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["originalOrderNumber"], "740001")
            self.assertEqual(reviews[0]["replacementOrderNumber"], "740002")
            self.assertEqual(reviews[0]["status"], "pending")

            second = store.detect_superseded_order_candidates_from_scanner("2026-09-15", "admin")
            self.assertEqual(second["scannerCandidateCount"], 0)
            self.assertEqual(second["alreadyReviewedCount"], 1)
            self.assertEqual(second["insertedCount"], 0)

            decision = store.decide_superseded_order_review(reviews[0]["id"], "remove_both", "admin")
            self.assertEqual(decision["decision"], "approved")
            self.assertEqual(decision["approvedRemoveOrderNumber"], "__both__")
            with store.connect() as con:
                active = con.execute(
                    "SELECT COUNT(*) FROM line_items li JOIN delivery_lists dl ON dl.id=li.list_id "
                    "WHERE dl.delivery_date=? AND li.order_no IN (?,?) AND COALESCE(li.is_deleted,0)=0",
                    ("2026-09-15", "740001", "740002"),
                ).fetchone()[0]
            self.assertEqual(int(active), 0)
            excluded_orders = {
                row["orderNumber"] for row in store.approved_superseded_order_exclusion_orders()
            }
            self.assertTrue({"740001", "740002"}.issubset(excluded_orders))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v543_superseded_detects_exact_normal_duplicate_with_production_divergence(self) -> None:
        verification_root = ROOT / "_verification_v543_superseded_normal_duplicate"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            items = []
            for order, source_prefix in (("743001", "v543-uncut"), ("743002", "v543-cut")):
                first = imported_item(order, "1", 1, f"{source_prefix}:1")
                first.update({"job": "89198368 ROSELYN COMMIT 200", "customer": "LENNAR HOMES", "product": '3/8" Clear Tempered', "dimensions": '11 7/16" x 80"'})
                second = imported_item(order, "2", 1, f"{source_prefix}:2")
                second.update({"job": "89198368 ROSELYN COMMIT 200", "customer": "LENNAR HOMES", "product": '3/8" Clear Tempered', "dimensions": '28 1/4" x 79 1/2"'})
                items.extend([first, second])
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-21", "items": items},
                "fileName": "Delivery List 09-21-2026.xlsx", "user": "admin",
            })
            store.sync_aw_cutting_rows([
                {
                    "sourceRowId": "v543-cut-1", "orderNr": "743002", "itemNr": "1", "bomId": 0,
                    "keyIndex": 0, "batchJobNumber": "9801", "batchStatusCode": 460,
                    "batchCreatedAt": "2026-09-14T16:40:00", "optimizationNumber": 88001,
                    "optimizationStatusCode": 460, "optimizationStatusSource": "PROD_OPTI_STATISTICS",
                    "optimizationLastChangedAt": "2026-09-14T16:45:00", "quantity": 1, "cutQuantity": 1,
                    "aggregateId": 1000,
                },
                {
                    "sourceRowId": "v543-cut-2", "orderNr": "743002", "itemNr": "2", "bomId": 0,
                    "keyIndex": 0, "batchJobNumber": "9802", "batchStatusCode": 460,
                    "batchCreatedAt": "2026-09-14T16:40:00", "optimizationNumber": 88002,
                    "optimizationStatusCode": 460, "optimizationStatusSource": "PROD_OPTI_STATISTICS",
                    "optimizationLastChangedAt": "2026-09-14T16:45:00", "quantity": 1, "cutQuantity": 1,
                    "aggregateId": 1000,
                },
            ])

            detected = store.detect_superseded_order_candidates_from_scanner("2026-09-21", "admin")
            self.assertEqual(detected["scannerCandidateCount"], 1)
            self.assertEqual(detected["insertedCount"], 1)
            review = store.list_superseded_order_reviews(status="", include_inactive=True)["reviews"][0]
            self.assertEqual(review["originalOrderNumber"], "743001")
            self.assertEqual(review["replacementOrderNumber"], "743002")
            self.assertEqual(review["evidence"]["rule"], "v0.543-current-scanner-normal-production-divergence-1")
            self.assertFalse(review["evidence"]["originalHasProductionEvidence"])
            self.assertTrue(review["evidence"]["replacementHasProductionEvidence"])
            produced = {row["itemNumber"]: row for row in review["replacementItems"]}
            self.assertEqual(produced["001"]["batch"], "9801")
            self.assertEqual(produced["001"]["optimization"], 88001)
            self.assertEqual(produced["001"]["cuttingLabel"], "Cut")
            self.assertEqual(produced["002"]["batch"], "9802")
            self.assertEqual(produced["002"]["optimization"], 88002)
            self.assertTrue(produced["002"]["cuttingComplete"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v543_reoptimization_replaces_stale_current_optimization_in_same_batch(self) -> None:
        verification_root = ROOT / "_verification_v543_reoptimization"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            base = {
                "orderNr": "743100", "itemNr": "1", "bomId": 0, "keyIndex": 0,
                "batchJobNumber": "9810", "batchStatusCode": 200,
                "batchCreatedAt": "2026-09-17T08:00:00", "quantity": 1, "cutQuantity": 0,
                "aggregateId": 1000, "optimizationStatusSource": "PROD_OPTIMIZATION",
            }
            store.sync_aw_cutting_rows([{
                **base, "sourceRowId": "v543-opti-old", "optimizationNumber": 88100,
                "optimizationStatusCode": 100, "optimizationDate": "2026-09-17T08:05:00",
                "optimizationLastChangedAt": "2026-09-17T08:06:00",
            }])
            self.assertEqual(store.aw_cutting_state("743100", "1")["optimization"], 88100)
            store.sync_aw_cutting_rows([{
                **base, "sourceRowId": "v543-opti-new", "optimizationNumber": 88101,
                "optimizationStatusCode": 100, "optimizationDate": "2026-09-17T08:15:00",
                "optimizationLastChangedAt": "2026-09-17T08:16:00",
            }])
            current = store.aw_cutting_state("743100", "1")
            self.assertEqual(current["optimization"], 88101)
            self.assertEqual(current["state"], "optimized")
            store.sync_aw_cutting_rows([{
                **base, "sourceRowId": "v543-opti-booked", "optimizationNumber": 88101,
                "optimizationStatusCode": 460, "optimizationStatusSource": "PROD_OPTI_STATISTICS",
                "optimizationDate": "2026-09-17T08:15:00", "optimizationLastChangedAt": "2026-09-17T08:30:00",
                "cutQuantity": 1,
            }])
            booked = store.aw_cutting_state("743100", "1")
            self.assertEqual(booked["optimization"], 88101)
            self.assertTrue(booked["complete"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v524_schema20_inventory_migration_preserves_existing_rows_and_is_idempotent(self) -> None:
        verification_root = ROOT / "_verification_v524_inventory_migration"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-10", "items": [imported_item("724020", "1", 2, "v0524-migration:1")]},
                "fileName": "Delivery List 09-10-2026.xlsx", "user": "admin",
            })
            with store.connect() as con:
                existing_tables = [str(row[0]) for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()]
                inventory_tables = {"inventory_sessions", "inventory_expected_items", "inventory_scans", "inventory_item_mappings"}
                preserved_tables = [name for name in existing_tables if name not in inventory_tables and name != "schema_migrations"]
                before_counts = {name: int(con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]) for name in preserved_tables}
                con.execute("PRAGMA foreign_keys=OFF")
                for name in ("inventory_scans", "inventory_expected_items", "inventory_sessions", "inventory_item_mappings"):
                    con.execute(f'DROP TABLE IF EXISTS "{name}"')
                con.execute("DELETE FROM schema_migrations WHERE version IN (20, 21)")
                con.commit()
                con.execute("PRAGMA foreign_keys=ON")
                applied = run_sqlite_migrations(con, store)
                self.assertEqual(applied, [20, 21])
                self.assertEqual(int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]), 21)
                for name, expected in before_counts.items():
                    self.assertEqual(int(con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]), expected, name)
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM inventory_item_mappings").fetchone()[0]), 15)
                self.assertEqual(str(con.execute("PRAGMA integrity_check").fetchone()[0]).lower(), "ok")
                self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
                after_counts = {name: int(con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]) for name in preserved_tables}
                self.assertEqual(run_sqlite_migrations(con, store), [])
                self.assertEqual({name: int(con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]) for name in preserved_tables}, after_counts)
                self.assertEqual(int(con.execute("SELECT COUNT(*) FROM inventory_item_mappings").fetchone()[0]), 15)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v526_date_wide_line_flags_use_one_connection_and_preserve_stage_results(self) -> None:
        verification_root = ROOT / "_verification_v526_date_flags"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                con.execute(
                    "INSERT INTO users(username,email,display_name,password_hash,active,created_at) "
                    "VALUES(?,?,?,?,1,?)",
                    ("v526tester", "v526tester@example.com", "V526 Tester", "x", "2026-09-10T12:00:00+00:00"),
                )
                con.commit()
            item = imported_item("926001", "1", 3, "v0526-date-flags:1")
            item["route"] = "IT"
            item["sourceRoute"] = "IT"
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-16", "items": [item]},
                "fileName": "Delivery List 09-16-2026.xlsx", "user": "v526tester", "sourceHash": "first",
            })
            changed = dict(item)
            changed["qty"] = 4
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-16", "items": [changed]},
                "fileName": "Delivery List 09-16-2026.xlsx", "user": "v526tester", "sourceHash": "second",
            })
            with store.connect() as con:
                list_ids = [str(row[0]) for row in con.execute(
                    "SELECT id FROM delivery_lists WHERE delivery_date=? AND status='active' ORDER BY id",
                    ("2026-09-16",),
                ).fetchall()]
            self.assertEqual(len(list_ids), 3)
            operations = OperationsFeatureService(store, store.config, verification_root)
            with mock.patch.object(store, "connect", wraps=store.connect) as connect_spy:
                payload = operations.line_flags_many(list_ids, "v526tester")
            self.assertEqual(connect_spy.call_count, 1)
            self.assertEqual(set(payload["results"]), set(list_ids))
            for list_id in list_ids:
                result = payload["results"][list_id]
                self.assertEqual(result["listId"], list_id)
                self.assertEqual(result["totalLineCount"], 1)
                self.assertEqual(result["pendingLineCount"], 1)
                self.assertEqual(result["updatedLineCount"], 1)
                self.assertEqual(result["newLineCount"], 0)
                self.assertEqual(result["listRevision"], 2)
                self.assertEqual(result["items"][0]["order"], "926001")
                self.assertEqual(result["items"][0]["item"], "001")
                self.assertEqual(result["items"][0]["userUpdateState"], "updated")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v529_internal_reject_review_is_per_user_and_future_events_reopen_review(self) -> None:
        verification_root = ROOT / "_verification_v529_reject_review"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-21", "items": [imported_item("729101", "1", 1, "v0529-reject:1")]},
                "fileName": "Delivery List 09-21-2026.xlsx", "user": "admin",
            })
            with store.connect() as con:
                con.executemany(
                    "INSERT INTO users(username,email,display_name,password_hash,active,created_at) VALUES(?,?,?,?,1,?)",
                    [
                        ("reviewer-a", "a@example.com", "Reviewer A", "x", "2026-09-11T12:00:00+00:00"),
                        ("reviewer-b", "b@example.com", "Reviewer B", "x", "2026-09-11T12:00:00+00:00"),
                    ],
                )
                selected = con.execute(
                    "SELECT id FROM delivery_lists WHERE delivery_date=? AND status='active' ORDER BY id LIMIT 1",
                    ("2026-09-21",),
                ).fetchone()
                first = con.execute(
                    "INSERT INTO reject_events(delivery_date,order_no,item_no,qty,reason_label,location_label,rejected_at,rejected_by) VALUES(?,?,?,?,?,?,?,?)",
                    ("2026-09-21", "729101", "001", 1, "Broken", "Cutting", "2026-09-11T12:05:00+00:00", "admin"),
                ).lastrowid
                con.commit()
            list_id = str(selected["id"])
            operations = OperationsFeatureService(store, store.config, verification_root)
            self.assertEqual(operations.line_flags(list_id, "reviewer-a")["rejectIds"], [first])
            acknowledged = operations.acknowledge_internal_rejects(list_id, [first], "reviewer-a")
            self.assertEqual(acknowledged["pendingRejectCount"], 0)
            self.assertEqual(operations.line_flags(list_id, "reviewer-b")["rejectIds"], [first])
            with store.connect() as con:
                second = con.execute(
                    "INSERT INTO reject_events(delivery_date,order_no,item_no,qty,reason_label,location_label,rejected_at,rejected_by) VALUES(?,?,?,?,?,?,?,?)",
                    ("2026-09-21", "729101", "001", 1, "Remake", "Denver", "2026-09-11T13:05:00+00:00", "admin"),
                ).lastrowid
                con.commit()
            self.assertEqual(operations.line_flags(list_id, "reviewer-a")["rejectIds"], [second])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v529_manual_cut_and_machine_progress_survives_until_reject(self) -> None:
        verification_root = ROOT / "_verification_v529_manual_progress"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-22", "items": [imported_item("729201", "1", 1, "v0529-progress:1")]},
                "fileName": "Delivery List 09-22-2026.xlsx", "user": "admin",
            })
            with store.connect() as con:
                anchor = con.execute(
                    "SELECT li.id FROM line_items li JOIN delivery_lists dl ON dl.id=li.list_id WHERE dl.delivery_date=? ORDER BY li.id LIMIT 1",
                    ("2026-09-22",),
                ).fetchone()
            store.advance_delivery_progress({"scope": "item", "target": "cutting", "lineItemId": anchor["id"]}, "admin")
            store.advance_delivery_progress({"scope": "item", "target": "machine:waterjet", "lineItemId": anchor["id"]}, "admin")
            hint = store.aw_fabrication_hints_for_requests([{
                "key": "piece", "deliveryDate": "2026-09-22", "order": "729201", "item": "001",
                "job": "88729201 TEST JOB", "lastRejectedAt": "", "remake": False,
            }])["piece"]
            self.assertTrue(hint["complete"])
            self.assertTrue(hint["manualMachineComplete"])
            self.assertEqual(hint["manualMachineCode"], "waterjet")
            rejected_hint = store.aw_fabrication_hints_for_requests([{
                "key": "piece", "deliveryDate": "2026-09-22", "order": "729201", "item": "001",
                "job": "88729201 TEST JOB", "lastRejectedAt": "2026-09-11T14:00:00+00:00", "remake": False,
            }])["piece"]
            self.assertFalse(rejected_hint.get("manualProgressOverride", False))
            self.assertFalse(rejected_hint.get("manualMachineComplete", False))
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v539_inventory_manual_quantity_and_dual_location_scan_feedback(self) -> None:
        verification_root = ROOT / "_verification_v539_inventory_feedback"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        user = {"username": "admin", "displayName": "Inventory Admin", "stageAccess": ["*"]}
        try:
            store = self.make_store(verification_root)
            item = imported_item("739901", "1", 3, "v0539-inventory:clear38")
            item.update({"dimensions": '36" x 72"', "product": '3/8" Clear Tempered', "barcode": "T200739901001000"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-15", "items": [item]},
                "fileName": "Delivery List 09-15-2026.xlsx",
                "user": "admin",
            })
            store.sync_aw_cutting_rows([{
                "sourceRowId": "v539-cut-1", "orderNr": "739901", "itemNr": "1", "bomId": 0,
                "keyIndex": 1, "batchJobNumber": "95391", "batchStatusCode": 500,
                "batchCreatedAt": "2026-09-15T08:00:00", "optimizationNumber": 95391,
                "optimizationStatusCode": 500, "quantity": 3, "cutQuantity": 3, "aggregateId": 1000,
                "cuttingBookingAt": "2026-09-15T08:10:00", "cuttingBookingEmployee": "CUT",
                "cuttingBookingRowId": "v539-book-1",
            }])

            session = store.start_inventory_session({"location": "airport_rd", "inventoryType": "full"}, user)
            self.assertEqual(session["expectedQty"], 3)

            # The frozen target remains three pieces, but live system presence can
            # move while the count is open. Two pieces are now in transit to IT.
            with store.connect() as con:
                con.execute(
                    "UPDATE line_items SET scanned_qty=2 WHERE list_id=? AND order_no=?",
                    ("2026-09-15-outbound-airport", "739901"),
                )
                con.commit()

            first = store.record_inventory_scan(session["id"], item["barcode"], user)
            self.assertTrue(first["ok"])
            self.assertEqual(first["countedQty"], 1)
            self.assertEqual(first["expectedQty"], 3)
            self.assertEqual(first["systemPresence"]["airportRd"]["qty"], 1)
            self.assertTrue(first["systemPresence"]["airportRd"]["inSystem"])
            self.assertEqual(first["systemPresence"]["indianTrail"]["qty"], 2)
            self.assertTrue(first["systemPresence"]["indianTrail"]["inSystem"])

            manual = store.record_inventory_manual_entry(session["id"], {
                "order": "739901", "item": "1", "qty": 1,
            }, user)
            self.assertTrue(manual["ok"])
            self.assertTrue(manual["matchedExpected"])
            self.assertEqual(manual["countedQty"], 2)
            self.assertEqual(manual["expectedQty"], 3)
            self.assertEqual(manual["remainingQty"], 1)

            final = store.record_inventory_scan(session["id"], item["barcode"], user)
            self.assertEqual(final["countedQty"], 3)
            self.assertEqual(final["remainingQty"], 0)
            self.assertTrue(final["lineComplete"])

            with self.assertRaisesRegex(ValueError, "exceed the system quantity"):
                store.record_inventory_manual_entry(session["id"], {
                    "order": "739901", "item": "1", "qty": 1,
                }, user)

            duplicate = store.record_inventory_scan(session["id"], item["barcode"], user)
            self.assertFalse(duplicate["ok"])
            self.assertTrue(duplicate["duplicate"])
            self.assertEqual(duplicate["countedQty"], 3)
            self.assertIn("systemPresence", duplicate)

            with store.connect() as con:
                rows = con.execute(
                    "SELECT qty, total_sqft FROM inventory_scans WHERE session_id=?",
                    (session["id"],),
                ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(int(rows[0]["qty"]), 3)
            self.assertAlmostEqual(float(rows[0]["total_sqft"]), 54.0)

            # A manual-first aggregate can later receive barcode counts. Undo must
            # remove exactly one physical piece instead of deleting the whole row.
            store.cancel_inventory_session(session["id"], {"reason": "v0.539 mixed-count undo test"}, user)
            with store.connect() as con:
                con.execute(
                    "UPDATE line_items SET scanned_qty=0 WHERE list_id=? AND order_no=?",
                    ("2026-09-15-outbound-airport", "739901"),
                )
                con.commit()
            mixed_session = store.start_inventory_session({"location": "airport_rd", "inventoryType": "full"}, user)
            mixed_manual = store.record_inventory_manual_entry(mixed_session["id"], {
                "order": "739901", "item": "1", "qty": 2,
            }, user)
            self.assertEqual(mixed_manual["countedQty"], 2)
            mixed_scan = store.record_inventory_scan(mixed_session["id"], item["barcode"], user)
            self.assertEqual(mixed_scan["countedQty"], 3)
            corrected = store.remove_inventory_scan(mixed_session["id"], int(mixed_scan["scan"]["id"]), {"reason": "undo one"}, user)
            self.assertEqual(corrected["scannedQty"], 2)
            with store.connect() as con:
                mixed_rows = con.execute("SELECT qty FROM inventory_scans WHERE session_id=?", (mixed_session["id"],)).fetchall()
            self.assertEqual(len(mixed_rows), 1)
            self.assertEqual(int(mixed_rows[0]["qty"]), 2)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v529_inventory_delivery_date_and_evidence_machines_are_durable(self) -> None:
        verification_root = ROOT / "_verification_v529_inventory_machine"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        user = {"username": "admin", "displayName": "Admin", "stageAccess": ["*"]}
        try:
            store = self.make_store(verification_root)
            session = store.start_inventory_session({"location": "airport_rd", "inventoryType": "full"}, user)
            store.record_inventory_manual_entry(session["id"], {
                "order": "729301", "item": "1", "jobNr": "JOB-529", "customer": "TEST",
                "deliveryDate": "2026-09-30", "glassType": "3/8 Clear", "dimensions": '24" x 48"', "qty": 1,
            }, user)
            with store.connect() as con:
                delivery_date = con.execute("SELECT delivery_date FROM inventory_scans WHERE session_id=?", (session["id"],)).fetchone()[0]
                installed = int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
            self.assertEqual(delivery_date, "2026-09-30")
            self.assertEqual(installed, 21)
            saved = store.update_machine_configuration({"machines": [
                {"code": "waterjet", "name": "WJ", "active": False, "color": "#9865F1", "terms": ["WJ"]},
                {"code": "denver", "name": "Denver", "active": False, "color": "#5085F7", "terms": ["DENVER"]},
                {"code": "polisher", "name": "Polisher", "active": False, "color": "#118855", "terms": ["POLISH"]},
            ]}, "admin")
            by_code = {row["code"]: row for row in saved["machines"]}
            self.assertTrue(by_code["waterjet"]["active"])
            self.assertTrue(by_code["denver"]["active"])
            self.assertFalse(by_code["polisher"]["active"])
            self.assertEqual(by_code["waterjet"]["color"], "#9865F1")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v530_attention_colors_category_receipts_and_automation_summary(self) -> None:
        verification_root = ROOT / "_verification_v530_attention"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                con.execute(
                    "INSERT INTO users(username,email,display_name,password_hash,active,created_at) VALUES(?,?,?,?,1,?)",
                    ("v530-reviewer", "v530@example.com", "V530 Reviewer", "x", "2026-09-14T12:00:00+00:00"),
                )
                con.commit()

            normal = imported_item("730001", "1", 1, "v0530-normal:1")
            remake = imported_item("730002", "1", 1, "v0530-remake:1")
            remake.update({"processState": "External Remake", "queueState": "RM"})
            rush = imported_item("730003", "1", 1, "v0530-rush:1")
            # Rush/SDI remains operator-owned: pre-register the work and let the
            # authoritative A+W import match it through the maintained Priority Work flow.
            store.create_priority_intake_request({
                "priorityType": "Rush",
                "jobNumber": rush["job"],
                "reason": "V530 automated import attention regression",
                "responsible": "V530 Test",
                "emailMode": "none",
            }, "admin")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-28", "items": [normal, remake, rush]},
                "fileName": "Delivery List 09-28-2026.xlsx", "user": "admin", "sourceHash": "v530-attention-first",
            })
            with store.connect() as con:
                list_ids = [str(row[0]) for row in con.execute(
                    "SELECT id FROM delivery_lists WHERE delivery_date=? AND status='active' ORDER BY id",
                    ("2026-09-28",),
                ).fetchall()]
            self.assertTrue(list_ids)

            operations = OperationsFeatureService(store, store.config, verification_root)
            flags = operations.line_flags(list_ids[0], "v530-reviewer")
            self.assertEqual(flags["pendingOrderCount"], 1)
            self.assertEqual(flags["pendingRemakeCount"], 1)
            self.assertEqual(flags["pendingRushCount"], 1)
            self.assertTrue(flags["orderNoticeIds"])
            self.assertTrue(flags["remakeNoticeIds"])
            self.assertTrue(flags["rushNoticeIds"])

            after_order = operations.acknowledge_line_updates(
                list_ids[0], flags["orderNoticeIds"], "v530-reviewer", "order"
            )
            self.assertEqual(after_order["pendingOrderCount"], 0)
            self.assertEqual(after_order["pendingRemakeCount"], 1)
            self.assertEqual(after_order["pendingRushCount"], 1)

            colors = {row["value"]: row["color"] for row in store.get_manual_edit_lookups()["attentionColors"]}
            self.assertEqual(colors, {
                "new_order": "#1766D8",
                "internal_reject": "#F28C28",
                "external_remake": "#111111",
                "rush": "#C62828",
            })
            saved = store.add_manual_edit_lookup({
                "type": "attention_color", "value": "internal_reject", "color": "#FF8A1F"
            }, "admin")
            saved_colors = {row["value"]: row["color"] for row in saved["attentionColors"]}
            self.assertEqual(saved_colors["internal_reject"], "#FF8A1F")
            with store.connect() as con:
                installed = int(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
                notification_id = store.create_app_notification(
                    con,
                    "success",
                    "Delivery list update complete",
                    "Import completed.",
                    "sql-delivery-automation",
                    payload={
                        "source": "sql-delivery-automation",
                        "succeeded": True,
                        "affectedListIds": list_ids,
                        "awRejectSync": {"mirroredInternalRejects": 255, "newInternalRejects": 2},
                    },
                )
                row = con.execute(
                    "SELECT title,message,payload_json FROM app_notifications WHERE id=?",
                    (notification_id,),
                ).fetchone()
                con.commit()
            self.assertEqual(installed, 21)
            details = json.loads(row["payload_json"])
            self.assertEqual(details["attentionSummary"], {
                "newOrders": 1,
                "internalRejects": 2,
                "externalRemakes": 1,
                "rushes": 1,
            })
            self.assertEqual(row["title"], "A+W import update")
            self.assertIn("new order", row["message"])
            self.assertIn("new Internal Reject", row["message"])
            self.assertIn("new External Remake", row["message"])
            self.assertIn("new Rush", row["message"])

            # v0.531: an existing ordinary line that newly becomes a remake is
            # review-worthy, but old priority rows that merely remain present
            # must not be announced again in the new import summary.
            normal_as_remake = dict(normal)
            normal_as_remake.update({"processState": "External Remake", "queueState": "RM"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-09-28", "items": [normal_as_remake, remake, rush]},
                "fileName": "Delivery List 09-28-2026.xlsx", "user": "admin", "sourceHash": "v531-attention-transition",
            })
            with store.connect() as con:
                transition_id = store.create_app_notification(
                    con, "success", "Delivery list update complete", "Import completed.", "sql-delivery-automation",
                    payload={
                        "source": "sql-delivery-automation", "succeeded": True,
                        "affectedListIds": list_ids, "startedAt": "2000-01-01T00:00:00+00:00",
                        "completedAt": "2090-01-01T00:00:00+00:00",
                        "awRejectSync": {"mirroredInternalRejects": 19, "newInternalRejects": 0},
                    },
                )
                transition_row = con.execute(
                    "SELECT title,message,payload_json FROM app_notifications WHERE id=?", (transition_id,)
                ).fetchone()
                con.commit()
            transition_details = json.loads(transition_row["payload_json"])
            self.assertEqual(transition_details["attentionSummary"], {
                "newOrders": 0, "internalRejects": 0, "externalRemakes": 1, "rushes": 0,
            })
            self.assertEqual(transition_row["message"], "1 new External Remake")

            # A later successful run with no line notices in its run window must
            # not reuse the preceding batch and re-announce stale review items.
            with store.connect() as con:
                quiet_id = store.create_app_notification(
                    con, "success", "Delivery-list check complete", "No source changes.", "sql-delivery-automation",
                    payload={
                        "source": "sql-delivery-automation", "succeeded": True,
                        "affectedListIds": list_ids, "startedAt": "2099-01-01T00:00:00+00:00",
                        "completedAt": "2099-01-01T01:00:00+00:00",
                        "awRejectSync": {"mirroredInternalRejects": 255, "newInternalRejects": 0},
                    },
                )
                quiet_row = con.execute(
                    "SELECT title,message,payload_json FROM app_notifications WHERE id=?", (quiet_id,)
                ).fetchone()
                con.commit()
            quiet_details = json.loads(quiet_row["payload_json"])
            self.assertEqual(quiet_details["attentionSummary"], {
                "newOrders": 0, "internalRejects": 0, "externalRemakes": 0, "rushes": 0,
            })
            self.assertEqual(quiet_row["title"], "A+W import complete")
            self.assertEqual(quiet_row["message"], "No new review items were imported.")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v533_remake_review_reopens_only_on_priority_transition(self) -> None:
        verification_root = ROOT / "_verification_v533_remake_review"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                con.execute(
                    "INSERT INTO users(username,email,display_name,password_hash,active,created_at) VALUES(?,?,?,?,1,?)",
                    ("v533-reviewer", "v533@example.com", "V533 Reviewer", "x", "2026-09-14T18:00:00+00:00"),
                )
                con.commit()

            normal = imported_item("733101", "1", 1, "v0533-priority-transition:1")
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-01", "items": [normal]},
                "fileName": "Delivery List 10-01-2026.xlsx", "user": "admin", "sourceHash": "v533-normal-first",
            })
            with store.connect() as con:
                list_id = str(con.execute(
                    "SELECT id FROM delivery_lists WHERE delivery_date=? AND status='active' ORDER BY id LIMIT 1",
                    ("2026-10-01",),
                ).fetchone()[0])

            operations = OperationsFeatureService(store, store.config, verification_root)
            initial_flags = operations.line_flags(list_id, "v533-reviewer")
            self.assertEqual(initial_flags["pendingOrderCount"], 1)
            initial_flags = operations.acknowledge_line_updates(
                list_id, initial_flags["orderNoticeIds"], "v533-reviewer", "order"
            )
            self.assertEqual(initial_flags["pendingLineCount"], 0)

            remake = dict(normal)
            remake.update({"processState": "External Remake", "queueState": "RM"})
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-01", "items": [remake]},
                "fileName": "Delivery List 10-01-2026.xlsx", "user": "admin", "sourceHash": "v533-became-remake",
            })
            remake_flags = operations.line_flags(list_id, "v533-reviewer")
            self.assertEqual(remake_flags["pendingOrderCount"], 0)
            self.assertEqual(remake_flags["pendingRemakeCount"], 1)
            self.assertTrue(remake_flags["remakeNoticeIds"])
            remake_flags = operations.acknowledge_line_updates(
                list_id, remake_flags["remakeNoticeIds"], "v533-reviewer", "remake"
            )
            self.assertEqual(remake_flags["pendingLineCount"], 0)

            routine_remake_edit = dict(remake)
            routine_remake_edit["qty"] = 2
            store.import_delivery_list({
                "payload": {"deliveryDate": "2026-10-01", "items": [routine_remake_edit]},
                "fileName": "Delivery List 10-01-2026.xlsx", "user": "admin", "sourceHash": "v533-remake-routine-edit",
            })
            routine_flags = operations.line_flags(list_id, "v533-reviewer")
            self.assertEqual(routine_flags["pendingOrderCount"], 0)
            self.assertEqual(routine_flags["pendingRemakeCount"], 0)
            self.assertEqual(routine_flags["pendingRushCount"], 0)
            self.assertEqual(routine_flags["pendingLineCount"], 0)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v0544_cutting_requires_current_booked_optimization(self) -> None:
        verification_root = ROOT / "_verification_v0544_cutting_lifecycle"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            base = {
                "sourceRowId": "v0544-current", "orderNr": "299544", "itemNr": "1",
                "bomId": 0, "keyIndex": 0, "batchJobNumber": "9901", "batchStatusCode": 400,
                "batchCreatedAt": "2026-09-17T08:00:00", "optimizationNumber": 9544,
                "optimizationStatusSource": "PROD_OPTIMIZATION", "optimizationSequence": 1,
                "optimizationSequenceRowId": "v0544-seq", "optimizationPlateNumber": 1,
                "quantity": 1, "cutQuantity": 1, "optimizationPlateCut": 1,
                "optimizationPlateStockBooked": 1, "cuttingBookingAt": "2026-09-17T08:10:00",
                "aggregateId": 1000,
            }
            # Physical-looking fields must not promote an Optimized state to Cut.
            store.sync_aw_cutting_rows([{**base, "optimizationStatusCode": 100}])
            optimized = store.aw_cutting_state("299544", "001")
            self.assertEqual(optimized["state"], "optimized")
            self.assertFalse(optimized["complete"])

            # Released is actively being cut, but still not complete.
            store.sync_aw_cutting_rows([{**base, "optimizationStatusCode": 200}])
            released = store.aw_cutting_state("299544", "001")
            self.assertEqual(released["state"], "released")
            self.assertFalse(released["complete"])

            # Booked is the authoritative completion milestone.
            store.sync_aw_cutting_rows([{**base, "optimizationStatusCode": 500}])
            booked = store.aw_cutting_state("299544", "001")
            self.assertEqual(booked["state"], "cut")
            self.assertTrue(booked["complete"])
            self.assertEqual(booked["evidenceSource"], "optimization_status_500")

            # A newer reoptimization in the same KEYINDEX must not inherit the
            # older Booked batch's Cutting completion.
            newer = {
                **base,
                "sourceRowId": "v0544-reoptimized",
                "batchJobNumber": "9902",
                "batchCreatedAt": "2026-09-17T09:00:00",
                "optimizationNumber": 9545,
                "optimizationStatusCode": 100,
                "optimizationSequence": 2,
                "optimizationSequenceRowId": "v0544-seq-2",
                "cuttingBookingAt": "",
                "cutQuantity": 0,
                "optimizationPlateCut": 0,
                "optimizationPlateStockBooked": 0,
            }
            store.sync_aw_cutting_rows([newer])
            reoptimized = store.aw_cutting_state("299544", "001")
            self.assertEqual(reoptimized["batch"], "9902")
            self.assertEqual(reoptimized["optimization"], 9545)
            self.assertEqual(reoptimized["state"], "optimized")
            self.assertFalse(reoptimized["complete"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v546_inventory_item_id_defaults_lookup_crud_and_resolution(self) -> None:
        verification_root = ROOT / "_verification_v546_inventory_item_ids"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                # Schema 20 originally seeded these two Item IDs with older stock
                # wording. v0.546 repairs only untouched legacy labels.
                legacy = {
                    row["item_id"]: row["glass_label"]
                    for row in con.execute(
                        "SELECT item_id, glass_label FROM inventory_item_mappings WHERE item_id IN (?, ?)",
                        ("G38SATINCLR", "18CDSWG"),
                    ).fetchall()
                }
                self.assertEqual(legacy["G38SATINCLR"], "3/8 Clear Satin")
                self.assertEqual(legacy["18CDSWG"], "1/8 Clear DS B-Grade Glass")
                store.ensure_inventory_item_mapping_defaults(con)
                con.commit()

            catalog = store.inventory_catalog({"username": "admin", "stageAccess": ["*"]})
            mapping = {row["glassLabel"]: row["itemId"] for row in catalog["itemMappings"]}
            self.assertEqual(mapping["3/8 Acid Etch"], "G38SATINCLR")
            self.assertEqual(mapping["1/8 Clear"], "18CDSWG")
            self.assertEqual(len(catalog["itemMappings"]), 15)
            with store.connect() as con:
                acid = store._inventory_item_mapping(con, "3/8 Acid Etch Tempered")
                clear18 = store._inventory_item_mapping(con, "1/8 Clear Annealed")
                self.assertEqual(acid["itemId"], "G38SATINCLR")
                self.assertEqual(clear18["itemId"], "18CDSWG")

            lookups = store.get_manual_edit_lookups()
            maintained = {row["glassLabel"]: row["itemId"] for row in lookups["inventoryItemMappings"]}
            self.assertEqual(maintained["3/8 Acid Etch"], "G38SATINCLR")
            self.assertEqual(maintained["1/8 Clear"], "18CDSWG")

            created = store.add_manual_edit_lookup({
                "type": "inventory_item_id",
                "itemId": "TESTGLASSID",
                "glassLabel": "Test Inventory Glass",
                "description": "TEST INVENTORY GLASS",
                "matchTerms": "TEST INVENTORY; TEST GLASS",
            }, "admin")
            created_row = next(row for row in created["inventoryItemMappings"] if row["itemId"] == "TESTGLASSID")
            self.assertEqual(created_row["glassLabel"], "Test Inventory Glass")
            self.assertIn("TEST GLASS", created_row["matchTermsList"])

            updated = store.add_manual_edit_lookup({
                "type": "inventory_item_id",
                "originalItemId": "TESTGLASSID",
                "itemId": "TESTGLASSID2",
                "glassLabel": "Test Inventory Glass",
                "description": "UPDATED TEST INVENTORY GLASS",
                "matchTerms": ["TEST INVENTORY GLASS", "TESTGLASSID2"],
            }, "admin")
            self.assertFalse(any(row["itemId"] == "TESTGLASSID" for row in updated["inventoryItemMappings"]))
            self.assertTrue(any(row["itemId"] == "TESTGLASSID2" for row in updated["inventoryItemMappings"]))
            with store.connect() as con:
                resolved = store._inventory_item_mapping(con, "Test Inventory Glass Tempered")
                self.assertEqual(resolved["itemId"], "TESTGLASSID2")
                old_active = con.execute("SELECT active FROM inventory_item_mappings WHERE item_id='TESTGLASSID'").fetchone()[0]
                self.assertEqual(int(old_active), 0)

            removed = store.remove_manual_edit_lookup("inventory_item_id", "TESTGLASSID2", "admin")
            self.assertFalse(any(row["itemId"] == "TESTGLASSID2" for row in removed["inventoryItemMappings"]))
            with store.connect() as con:
                inactive = con.execute("SELECT active FROM inventory_item_mappings WHERE item_id='TESTGLASSID2'").fetchone()[0]
                self.assertEqual(int(inactive), 0)
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)

    def test_v546_inventory_default_repair_preserves_operator_edits(self) -> None:
        verification_root = ROOT / "_verification_v546_inventory_item_edit_preservation"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                con.execute(
                    "UPDATE inventory_item_mappings SET glass_label=?, description=? WHERE item_id=?",
                    ("Operator Acid Etch Label", "OPERATOR DESCRIPTION", "G38SATINCLR"),
                )
                store.ensure_inventory_item_mapping_defaults(con)
                con.commit()
                row = con.execute(
                    "SELECT glass_label, description FROM inventory_item_mappings WHERE item_id=?",
                    ("G38SATINCLR",),
                ).fetchone()
                self.assertEqual(row["glass_label"], "Operator Acid Etch Label")
                self.assertEqual(row["description"], "OPERATOR DESCRIPTION")
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


    def test_v547_inventory_export_uses_current_item_id_mapping_without_mutating_snapshot(self) -> None:
        verification_root = ROOT / "_verification_v547_inventory_export_item_ids"
        shutil.rmtree(verification_root, ignore_errors=True)
        verification_root.mkdir(parents=True, exist_ok=True)
        user = {"username": "admin", "displayName": "Inventory Admin", "stageAccess": ["*"]}
        try:
            store = self.make_store(verification_root)
            with store.connect() as con:
                # Simulate an inventory that started before the corrected Item ID
                # mapping existed: both frozen system and physical rows retained
                # blank/stale Item IDs. The session itself must remain immutable.
                cursor = con.execute(
                    """
                    INSERT INTO inventory_sessions
                        (session_code, location, inventory_type, status, cycle_filter_json, started_by, started_at,
                         completed_by, completed_at, expected_line_count, expected_qty, expected_total_sqft, notes, created_at, updated_at)
                    VALUES (?, 'airport_rd', 'full', 'completed', '{}', 'admin', ?, 'admin', ?, 2, 2, 20.0, '', ?, ?)
                    """,
                    ("AIR-V547-EXPORT", "2026-09-18T12:00:00+00:00", "2026-09-18T13:00:00+00:00",
                     "2026-09-18T12:00:00+00:00", "2026-09-18T13:00:00+00:00"),
                )
                session_id = int(cursor.lastrowid)
                expected_rows = [
                    ("acid", "3/8 Acid Etch Tempered", "", "930001", "001", 10.0),
                    ("clear18", "1/8 Clear Annealed", "LEGACY18", "930002", "001", 10.0),
                ]
                expected_ids = []
                for key, glass_type, item_id, order_no, item_no, total_sqft in expected_rows:
                    row = con.execute(
                        """
                        INSERT INTO inventory_expected_items
                            (session_id, snapshot_key, source_line_item_id, source_list_id, delivery_date, job_no, customer,
                             order_no, item_no, glass_type, item_id, dimensions, sqft_each, qty, total_sqft, route, bay_code,
                             cutting_key_index, cutting_state, source_reason, source_payload_json)
                        VALUES (?, ?, '', '', '2026-09-18', 'TEST JOB', 'TEST CUSTOMER', ?, ?, ?, ?, '24 x 60', ?, 1, ?, 'IT', '', 0, 'cut', '', '{}')
                        """,
                        (session_id, key, order_no, item_no, glass_type, item_id, total_sqft, total_sqft),
                    )
                    expected_ids.append(int(row.lastrowid))
                for expected_id, (key, glass_type, item_id, order_no, item_no, total_sqft) in zip(expected_ids, expected_rows):
                    con.execute(
                        """
                        INSERT INTO inventory_scans
                            (session_id, expected_item_id, source_line_item_id, barcode, entry_type, scanned_at, scanned_by,
                             delivery_date, job_no, customer, order_no, item_no, glass_type, item_id, dimensions, sqft_each, qty,
                             total_sqft, notes, manual_fields_json)
                        VALUES (?, ?, '', ?, 'scan', '2026-09-18T12:30:00+00:00', 'admin', '2026-09-18',
                                'TEST JOB', 'TEST CUSTOMER', ?, ?, ?, ?, '24 x 60', ?, 1, ?, '', '{}')
                        """,
                        (session_id, expected_id, f"BC-{key}", order_no, item_no, glass_type, item_id, total_sqft, total_sqft),
                    )
                store.ensure_inventory_item_mapping_defaults(con)
                con.commit()

            workbook = store.export_inventory_xlsx(session_id, user)
            self.assertTrue(zipfile.is_zipfile(BytesIO(workbook)))
            with zipfile.ZipFile(BytesIO(workbook)) as archive:
                for sheet_index in (1, 2, 3, 4):
                    sheet_xml = archive.read(f"xl/worksheets/sheet{sheet_index}.xml").decode("utf-8")
                    self.assertIn("G38SATINCLR", sheet_xml)
                    self.assertIn("18CDSWG", sheet_xml)
                summary_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertNotIn("LEGACY18", summary_xml)

            # XLSX normalization is presentation-only; the durable session keeps
            # the Item IDs that were frozen/scanned at count time.
            with store.connect() as con:
                frozen = con.execute(
                    "SELECT glass_type, item_id FROM inventory_expected_items WHERE session_id=? ORDER BY id",
                    (session_id,),
                ).fetchall()
                scanned = con.execute(
                    "SELECT glass_type, item_id FROM inventory_scans WHERE session_id=? ORDER BY id",
                    (session_id,),
                ).fetchall()
                self.assertEqual([row["item_id"] for row in frozen], ["", "LEGACY18"])
                self.assertEqual([row["item_id"] for row in scanned], ["", "LEGACY18"])
        finally:
            shutil.rmtree(verification_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class V534BlueXCancellationGeometryTests(unittest.TestCase):
    def test_large_blue_cross_is_detected_but_single_or_neutral_lines_are_not(self) -> None:
        width, height = 612.0, 792.0
        crossed = [
            {"x1": 45, "y1": 60, "x2": 565, "y2": 735, "width": 5.0, "color": (0.05, 0.35, 0.82)},
            {"x1": 55, "y1": 725, "x2": 555, "y2": 70, "width": 5.0, "color": (0.05, 0.35, 0.82)},
        ]
        self.assertTrue(ProductionFileService._looks_like_blue_cancellation_x_v534(crossed, width, height))
        self.assertFalse(ProductionFileService._looks_like_blue_cancellation_x_v534(crossed[:1], width, height))
        neutral = [{**row, "color": (0.2, 0.2, 0.2)} for row in crossed]
        self.assertFalse(ProductionFileService._looks_like_blue_cancellation_x_v534(neutral, width, height))
        short = [
            {"x1": 250, "y1": 300, "x2": 360, "y2": 430, "width": 5.0, "color": (0.05, 0.35, 0.82)},
            {"x1": 250, "y1": 430, "x2": 360, "y2": 300, "width": 5.0, "color": (0.05, 0.35, 0.82)},
        ]
        self.assertFalse(ProductionFileService._looks_like_blue_cancellation_x_v534(short, width, height))

    def test_flattened_pdf_blue_cross_is_detected_without_ocr(self) -> None:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject

        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        stream.set_data(
            b"0.05 0.35 0.82 RG 5 w "
            b"45 60 m 565 735 l S "
            b"55 725 m 555 70 l S"
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
        payload = BytesIO()
        writer.write(payload)
        payload.seek(0)
        parsed_page = PdfReader(payload).pages[0]
        self.assertTrue(ProductionFileService._pdf_page_has_cancellation_x_v534(parsed_page))
