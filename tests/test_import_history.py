"""Regression tests for v121 maintained import-result normalization and recovery."""

from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py"
SPEC = importlib.util.spec_from_file_location("import_delivery_folder", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ImportHistoryTests(unittest.TestCase):
    def test_normalizes_maintained_folder_result_and_classifications(self) -> None:
        raw = {
            "ok": True,
            "sourceFolder": "Temp",
            "dateFrom": "2026-07-15",
            "dateTo": "2026-07-19",
            "importedFiles": [
                {
                    "fileName": "new.xlsx",
                    "deliveryDate": "2026-07-15",
                    "createdCount": 4,
                    "reactivatedCount": 1,
                    "reactivatedListIds": ["restored-stage"],
                    "updatedCount": 0,
                    "rowCount": 10,
                    "totalQty": 12,
                    "stageSummaries": [{
                        "listId": "restored-stage",
                        "label": "Staging - Airport Rd",
                        "created": False,
                        "reactivated": True,
                    }],
                },
                {"fileName": "both.xlsx", "deliveryDate": "2026-07-16", "createdCount": 1, "updatedCount": 2, "listIds": ["a", "b"]},
            ],
            "updatedFiles": [
                {"fileName": "updated.xlsx", "deliveryDate": "2026-07-17", "createdCount": 0, "updatedCount": 3, "changedPieceQty": 5},
            ],
            "skippedFiles": [
                {"fileName": "same.xlsx", "deliveryDate": "2026-07-18", "reason": "No updates"},
            ],
            "failedFiles": [
                {"fileName": "failed.xlsx", "deliveryDate": "2026-07-19", "errors": ["bad workbook"]},
            ],
        }
        result = module.normalize_result(raw)
        self.assertEqual([item["classification"] for item in result["files"]], [
            "new", "new_updated", "updated", "no_changes", "failed"
        ])
        self.assertEqual(result["newFileCount"], 2)
        self.assertEqual(result["updatedFileCount"], 1)
        self.assertEqual(result["noChangeFileCount"], 1)
        self.assertEqual(result["failedFileCount"], 1)
        self.assertEqual(result["importedDates"], ["2026-07-15", "2026-07-16", "2026-07-17", "2026-07-18"])
        self.assertEqual(result["changedDates"], ["2026-07-15", "2026-07-16", "2026-07-17"])
        self.assertEqual(result["failedDates"], ["2026-07-19"])
        self.assertEqual(result["reactivatedCount"], 1)
        self.assertEqual(result["files"][0]["reactivatedListIds"], ["restored-stage"])
        self.assertTrue(result["files"][0]["stageSummaries"][0]["reactivated"])

    def test_skipped_result_derives_date_from_filename(self) -> None:
        result = module.normalize_result({
            "ok": True,
            "updatedFiles": [],
            "skippedFiles": [{"fileName": "Delivery List 07-28-2026.xlsx", "reason": "No updates"}],
        }, "2026-07-28", "2026-07-28")
        self.assertEqual(result["updatedFileCount"], 0)
        self.assertEqual(result["noChangeFileCount"], 1)
        self.assertEqual(result["files"][0]["deliveryDate"], "2026-07-28")
        self.assertEqual(result["files"][0]["classificationLabel"], "No Changes")

    def test_normalization_excludes_files_outside_requested_window(self) -> None:
        raw = {
            "ok": True,
            "updatedFiles": [
                {"fileName": "Delivery List 07-28-2026.xlsx", "deliveryDate": "2026-07-28", "updatedCount": 1},
            ],
            "skippedFiles": [
                {"fileName": "Delivery List 07-20-2026.xlsx"},
                {"fileName": "Delivery List 07-28-2026.xlsx"},
            ],
        }
        summary = module.normalize_result(raw, "2026-07-28", "2026-07-28")
        self.assertEqual(summary["importedDates"], ["2026-07-28"])
        self.assertEqual(len(summary["files"]), 2)
        self.assertNotIn("2026-07-20", summary["importedDates"])

    def test_selective_sync_reports_unchanged_without_reimporting(self) -> None:
        class FakeStore:
            def __init__(self) -> None:
                self.ids = {"2026-07-28-staging", "2026-07-28-outbound"}
                self.folder_import_calls = []

            def get_delivery_lists(self):
                return [{"id": value} for value in sorted(self.ids)]

            def import_delivery_folder(self, payload):
                self.folder_import_calls.append(payload)
                raise AssertionError("Unchanged complete dates must not be reimported")

        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            workbook = folder / "Delivery List 07-28-2026.xlsx"
            workbook.write_bytes(b"placeholder")
            store = FakeStore()
            result = module.selective_sql_sync(
                store=store,
                folder=folder,
                target_dates=["2026-07-28"],
                force_import_dates=set(),
                user="sql-auto-import",
                date_reader=lambda path: "2026-07-28",
                payload_loader=lambda path: {
                    "deliveryDate": "2026-07-28",
                    "sourceName": path.name,
                    "items": [{"qty": 2}],
                },
                list_builder=lambda payload: [
                    ("2026-07-28-staging", "Staging", "Staging", "Airport", []),
                    ("2026-07-28-outbound", "Outbound", "Outbound", "Airport", []),
                ],
            )
            self.assertEqual(store.folder_import_calls, [])
            self.assertEqual(result["noChangeFileCount"], 1)
            self.assertEqual(result["importedDates"], ["2026-07-28"])
            self.assertIn("all expected scanner stage lists are present", result["files"][0]["reason"])

    def test_selective_sync_applies_customer_routes_before_stage_verification(self) -> None:
        """An all-Greenville date must not falsely require Indian Trail."""

        class FakeStore:
            def __init__(self) -> None:
                self.ids = {
                    "2026-07-31-staging-airport",
                    "2026-07-31-outbound-airport",
                    "2026-07-31-bfs-greenville",
                }
                self.folder_import_calls = []
                self.route_resolution_calls = 0

            def get_delivery_lists(self):
                return [{"id": value} for value in sorted(self.ids)]

            def apply_customer_route_rules_to_payload(self, payload):
                self.route_resolution_calls += 1
                routed = dict(payload)
                routed["items"] = [
                    {**item, "route": "GNV"}
                    for item in payload.get("items") or []
                ]
                return routed

            def import_delivery_folder(self, payload):
                self.folder_import_calls.append(payload)
                raise AssertionError("Correctly routed complete dates must not be reimported")

        def list_builder(payload):
            delivery_date = payload["deliveryDate"]
            definitions = [
                (f"{delivery_date}-staging-airport", "Staging", "Staging", "Airport", []),
                (f"{delivery_date}-outbound-airport", "Outbound", "Outbound", "Airport", []),
            ]
            routes = {str(item.get("route") or "") for item in payload.get("items") or []}
            if "GNV" in routes:
                definitions.append(
                    (f"{delivery_date}-bfs-greenville", "Greenville", "Greenville", "Greenville", [])
                )
            else:
                definitions.append(
                    (f"{delivery_date}-inbound-indian-trail", "Inbound", "Inbound", "Indian Trail", [])
                )
            return definitions

        folder = ROOT / "_verification"
        workbook = folder / "Delivery List 07-31-2026.xlsx"
        with mock.patch.object(
            module,
            "delivery_workbooks_by_date",
            return_value={"2026-07-31": workbook},
        ):
            store = FakeStore()
            result = module.selective_sql_sync(
                store=store,
                folder=folder,
                target_dates=["2026-07-31"],
                force_import_dates=set(),
                user="sql-auto-import",
                date_reader=lambda path: "2026-07-31",
                payload_loader=lambda path: {
                    "deliveryDate": "2026-07-31",
                    "sourceName": path.name,
                    "items": [
                        {
                            "qty": 1,
                            "customer": "BFS East Greenville SC MW",
                            "route": "",
                        }
                    ],
                },
                list_builder=list_builder,
            )

            self.assertEqual(store.route_resolution_calls, 1)
            self.assertEqual(store.folder_import_calls, [])
            self.assertTrue(result["ok"])
            self.assertEqual(result["noChangeFileCount"], 1)
            self.assertEqual(result["failedFileCount"], 0)

    def test_selective_sync_recovers_deleted_stage_via_maintained_folder_import(self) -> None:
        class FakeStore:
            def __init__(self) -> None:
                self.ids = {"2026-07-28-staging"}
                self.folder_import_calls = []

            def get_delivery_lists(self):
                return [{"id": value} for value in sorted(self.ids)]

            def import_delivery_folder(self, payload):
                self.folder_import_calls.append(payload)
                self.ids.update({"2026-07-28-staging", "2026-07-28-outbound"})
                return {
                    "ok": True,
                    "sourceFolder": payload["sourceFolder"],
                    "importedFiles": [{
                        "fileName": "Delivery List 07-28-2026.xlsx",
                        "deliveryDate": "2026-07-28",
                        "createdCount": 1,
                        "reactivatedCount": 1,
                        "reactivatedListIds": ["2026-07-28-outbound"],
                        "updatedCount": 0,
                        "rowCount": 1,
                        "totalQty": 2,
                        "stageSummaries": [{
                            "listId": "2026-07-28-outbound",
                            "label": "Outbound - Airport Rd",
                            "created": False,
                            "reactivated": True,
                        }],
                    }],
                    "updatedFiles": [],
                    "skippedFiles": [],
                    "failedFiles": [],
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            workbook = folder / "Delivery List 07-28-2026.xlsx"
            workbook.write_bytes(b"placeholder")
            store = FakeStore()
            result = module.selective_sql_sync(
                store=store,
                folder=folder,
                target_dates=["2026-07-28"],
                force_import_dates=set(),
                user="sql-auto-import",
                date_reader=lambda path: "2026-07-28",
                payload_loader=lambda path: {
                    "deliveryDate": "2026-07-28",
                    "sourceName": path.name,
                    "items": [{"qty": 2}],
                },
                list_builder=lambda payload: [
                    ("2026-07-28-staging", "Staging", "Staging", "Airport", []),
                    ("2026-07-28-outbound", "Outbound", "Outbound", "Airport", []),
                ],
            )

            self.assertEqual(len(store.folder_import_calls), 1)
            self.assertEqual(store.folder_import_calls[0]["dateFrom"], "2026-07-28")
            self.assertEqual(store.folder_import_calls[0]["dateTo"], "2026-07-28")
            self.assertEqual(result["recoveredFileCount"], 1)
            self.assertEqual(result["recoveredDates"], ["2026-07-28"])
            self.assertEqual(result["newFileCount"], 1)
            self.assertEqual(result["reactivatedCount"], 1)
            self.assertEqual(result["files"][0]["classificationLabel"], "New")
            self.assertTrue(result["files"][0]["stageSummaries"][0]["reactivated"])
            self.assertIn("Recovered missing scanner stage list", result["files"][0]["reason"])
            self.assertIn("2026-07-28-outbound", store.ids)


if __name__ == "__main__":
    unittest.main()

class ImportConcurrencyRetryTests(unittest.TestCase):
    """Keep temporary database contention from failing a safe importer run."""

    def test_database_busy_is_retried_until_success(self) -> None:
        calls = {"count": 0}

        def action():
            calls["count"] += 1
            if calls["count"] < 3:
                raise sqlite3.OperationalError("database is locked")
            return {"ok": True}

        with mock.patch.object(module.time, "sleep", return_value=None):
            result = module.run_with_database_retry(action, "testing", attempts=4)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["count"], 3)

    def test_non_lock_error_is_not_retried(self) -> None:
        calls = {"count": 0}

        def action():
            calls["count"] += 1
            raise ValueError("bad workbook")

        with self.assertRaisesRegex(ValueError, "bad workbook"):
            module.run_with_database_retry(action, "testing", attempts=4)

        self.assertEqual(calls["count"], 1)
