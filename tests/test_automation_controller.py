"""Unit tests for the v121 web automation control plane."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "automation" / "sql_delivery_export" / "delivery_automation_control.py"
SPEC = importlib.util.spec_from_file_location("delivery_automation_control", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ClosingTestConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class FakeScannerStore:
    database_type = "sqlite"

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def connect(self):
        connection = sqlite3.connect(self.database_path, factory=ClosingTestConnection)
        connection.row_factory = sqlite3.Row
        return connection

    def get_delivery_lists(self):
        return [{"id": "2026-07-15-staging", "deliveryDate": "2026-07-15"}]


class AutomationControllerTests(unittest.TestCase):
    def make_controller(self, temp_dir: str, scanner_store=None):
        project = Path(temp_dir) / "project"
        runtime = Path(temp_dir) / "runtime"
        scripts = runtime / "Scripts"
        scripts.mkdir(parents=True)
        project.mkdir()
        config = {
            "Version": "v121",
            "ProjectRoot": str(project),
            "WorkingRoot": str(runtime),
            "DestinationFolder": str(Path(temp_dir) / "delivery-lists"),
            "Database": {"Server": "SQLAWGLASS", "Database": "BFSMAIN", "AuthenticationMode": "Windows"},
            "Runtime": {"PowerShellPath": "powershell.exe"},
            "Schedule": {
                "IncrementalIntervalMinutes": 60,
                "IncrementalPastDays": 2,
                "IncrementalFutureDays": 14,
                "FullPastDays": 7,
                "FullFutureDays": 90,
                "FullRefreshTime": "17:00",
            },
            "Import": {"Mode": "direct-store"},
            "Notifications": {"Enabled": True, "NotifyOnNoChanges": True},
            "Automation": {"Mode": "folder-import-only", "ScheduleEnabled": False, "AllowWebGuiControl": True},
        }
        config_path = scripts / "sql-export.config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        (scripts / "Run-DeliveryListSqlAutomation.ps1").write_text("# runner", encoding="utf-8")
        env = mock.patch.dict(os.environ, {"DLS_SQL_EXPORT_CONFIG": str(config_path)})
        env.start()
        self.addCleanup(env.stop)
        controller = module.DeliveryAutomationController(project, SimpleNamespace(), scanner_store)
        return controller, config_path

    def test_dashboard_exposes_safe_settings_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, _ = self.make_controller(temp_dir)
            with mock.patch.object(controller, "_schedule_installed", return_value=False):
                dashboard = controller.get_dashboard()
            self.assertTrue(dashboard["installed"])
            self.assertEqual(dashboard["settings"]["automationMode"], "folder-import-only")
            self.assertEqual(dashboard["source"]["server"], "SQLAWGLASS")
            self.assertNotIn("password", json.dumps(dashboard).lower())

    def test_save_settings_validates_and_persists_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, config_path = self.make_controller(temp_dir)
            with mock.patch.object(controller, "_schedule_installed", return_value=False):
                result = controller.save_settings(
                    {
                        "automationMode": "sql-export-and-import",
                        "intervalMinutes": 30,
                        "incrementalPastDays": 3,
                        "incrementalFutureDays": 21,
                        "fullPastDays": 8,
                        "fullFutureDays": 100,
                        "fullRefreshTime": "18:30",
                        "destinationFolder": str(Path(temp_dir) / "delivery-lists"),
                        "notificationsEnabled": True,
                        "notifyOnNoChanges": False,
                    },
                    "admin",
                )
            stored = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["Version"], "v121")
            self.assertEqual(stored["Automation"]["Mode"], "sql-export-and-import")
            self.assertEqual(stored["Schedule"]["IncrementalIntervalMinutes"], 30)
            self.assertFalse(stored["Notifications"]["NotifyOnNoChanges"])
            self.assertIn("saved by admin", result["message"])

    def test_invalid_action_is_rejected_before_process_start(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, _ = self.make_controller(temp_dir)
            with self.assertRaisesRegex(ValueError, "Choose folder import"):
                controller.start_run({"action": "arbitrary-command", "rangeMode": "one-date", "dateFrom": "2026-07-15"}, "admin")

    def test_date_window_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "Through date"):
            module.clean_date("2026/07/15", "Through date", required=True)
        self.assertEqual(module.clean_date("2026-07-15", "From date", required=True), "2026-07-15")

    def test_recent_imports_use_authoritative_change_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "scanner.db"
            with sqlite3.connect(database, factory=ClosingTestConnection) as connection:
                connection.execute(
                    """
                    CREATE TABLE imports (
                        id INTEGER PRIMARY KEY,
                        delivery_date TEXT,
                        source_name TEXT,
                        row_count INTEGER,
                        total_qty INTEGER,
                        status TEXT,
                        imported_by TEXT,
                        imported_at TEXT,
                        source_path TEXT,
                        source_hash TEXT,
                        import_kind TEXT,
                        change_summary TEXT
                    )
                    """
                )
                rows = [
                    (1, "2026-07-15", "new.xlsx", 10, 12, "published", "auto", "2026-07-22T10:00:00+00:00", "", "a", "temp_folder", {"createdCount": 4, "updatedCount": 0, "changedListIds": ["a"]}),
                    (2, "2026-07-16", "updated.xlsx", 8, 8, "published", "auto", "2026-07-22T11:00:00+00:00", "", "b", "temp_folder", {"createdCount": 0, "updatedCount": 3, "changedListIds": ["b"]}),
                    (3, "2026-07-17", "both.xlsx", 9, 9, "published", "auto", "2026-07-22T12:00:00+00:00", "", "c", "temp_folder", {"createdCount": 1, "updatedCount": 2, "changedListIds": ["c"]}),
                    (4, "2026-07-18", "same.xlsx", 9, 9, "published", "auto", "2026-07-22T13:00:00+00:00", "", "d", "temp_folder", {"createdCount": 0, "updatedCount": 0, "changedListIds": []}),
                    (5, "2026-07-19", "failed.xlsx", 0, 0, "failed", "auto", "2026-07-22T14:00:00+00:00", "", "e", "temp_folder", {}),
                ]
                connection.executemany(
                    "INSERT INTO imports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(*row[:-1], json.dumps(row[-1])) for row in rows],
                )
            store = FakeScannerStore(database)
            controller, config_path = self.make_controller(temp_dir, scanner_store=store)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            paths = controller._runtime_paths(config)
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            paths["last_run"].write_text(json.dumps({
                "completedAt": "2026-07-22T15:00:00+00:00",
                "importResults": [
                    {"fileName": "new.xlsx", "deliveryDate": "2026-07-15", "classification": "no_changes", "reason": "SQL data and workbook were unchanged."},
                    {"fileName": "skipped.xlsx", "deliveryDate": "2026-07-20", "classification": "no_changes"},
                    {"fileName": "broken.xlsx", "deliveryDate": "2026-07-21", "classification": "failed", "errors": ["bad file"]},
                ],
            }), encoding="utf-8")
            payload = controller.get_recent_imports(20)
            classifications = [item["classification"] for item in payload["recentImports"]]
            self.assertEqual(classifications[:3], ["no_changes", "no_changes", "failed"])
            self.assertEqual(classifications[3:], ["failed", "no_changes", "new_updated", "updated"])
            self.assertEqual(payload["recentImports"][5]["classificationLabel"], "New + Updated")
            self.assertEqual(payload["lists"][0]["deliveryDate"], "2026-07-15")
            self.assertEqual(payload["lastCheckedAt"], "2026-07-22T15:00:00+00:00")
            self.assertTrue(
                any(
                    item["deliveryDate"] == "2026-07-15" and item["classification"] == "no_changes"
                    for item in payload["recentImports"]
                )
            )
            self.assertFalse(
                any(
                    item["deliveryDate"] == "2026-07-15" and item["classification"] == "new"
                    for item in payload["recentImports"]
                )
            )

    def test_latest_no_change_result_uses_current_run_check_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "scanner.db"
            store = FakeScannerStore(database)
            controller, config_path = self.make_controller(temp_dir, scanner_store=store)
            paths = controller._runtime_paths(json.loads(config_path.read_text(encoding="utf-8")))
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            completed_at = "2026-07-23T14:45:00+00:00"
            paths["last_run"].write_text(
                json.dumps({
                    "completedAt": completed_at,
                    "startedBy": "scheduled-task",
                    "runAction": "SqlExportAndImport",
                    "succeeded": True,
                    "importResults": [{
                        "fileName": "Delivery List 07-29-2026.xlsx",
                        "deliveryDate": "2026-07-29",
                        "classification": "no_changes",
                        "stageSummaries": [{
                            "listId": "2026-07-29-staging-airport",
                            "label": "Staging - Airport Rd",
                            "created": False,
                            "changedLineCount": 0,
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            payload = controller.get_latest_import_result()
            result = payload["latestImportResults"][0]
            self.assertEqual(payload["lastCheckedAt"], completed_at)
            self.assertEqual(result["classification"], "no_changes")
            self.assertEqual(result["importedAt"], completed_at)
            self.assertEqual(result["checkedAt"], completed_at)
            self.assertEqual(result["updatedAt"], completed_at)
            self.assertEqual(result["stageSummaries"][0]["checkedAt"], completed_at)
            self.assertEqual(result["stageSummaries"][0]["updatedAt"], completed_at)

    def test_latest_restored_stage_result_is_new_and_keeps_stage_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "scanner.db"
            with sqlite3.connect(database, factory=ClosingTestConnection) as connection:
                connection.execute(
                    """
                    CREATE TABLE imports (
                        id INTEGER PRIMARY KEY,
                        delivery_date TEXT,
                        source_name TEXT,
                        row_count INTEGER,
                        total_qty INTEGER,
                        status TEXT,
                        imported_by TEXT,
                        imported_at TEXT,
                        source_path TEXT,
                        source_hash TEXT,
                        import_kind TEXT,
                        change_summary TEXT
                    )
                    """
                )
                connection.execute(
                    "INSERT INTO imports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        1,
                        "2026-07-28",
                        "Delivery List 07-28-2026.xlsx",
                        62,
                        73,
                        "published",
                        "sql-auto-import",
                        "2026-07-23T11:20:00+00:00",
                        "",
                        "hash",
                        "temp_folder",
                        json.dumps({
                            "createdCount": 1,
                            "reactivatedCount": 1,
                            "updatedCount": 0,
                            "changedListIds": ["2026-07-28-staging-airport"],
                            "stages": [{
                                "listId": "2026-07-28-staging-airport",
                                "label": "Staging - Airport Rd",
                                "created": False,
                                "reactivated": True,
                                "changedLineCount": 0,
                                "changedPieceQty": 0,
                            }],
                        }),
                    ),
                )
            store = FakeScannerStore(database)
            controller, config_path = self.make_controller(temp_dir, scanner_store=store)
            paths = controller._runtime_paths(json.loads(config_path.read_text(encoding="utf-8")))
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            paths["last_run"].write_text(
                json.dumps({
                    "completedAt": "2026-07-23T11:21:00+00:00",
                    "startedBy": "admin",
                    "importResults": [{
                        "fileName": "Delivery List 07-28-2026.xlsx",
                        "deliveryDate": "2026-07-28",
                        "classification": "new",
                        "createdCount": 1,
                        "reactivatedCount": 1,
                        "reactivatedListIds": ["2026-07-28-staging-airport"],
                        "changedListIds": ["2026-07-28-staging-airport"],
                        "stageSummaries": [{
                            "listId": "2026-07-28-staging-airport",
                            "label": "Staging - Airport Rd",
                            "created": False,
                            "reactivated": True,
                            "changedLineCount": 0,
                            "changedPieceQty": 0,
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            item = controller.get_recent_imports(20)["recentImports"][0]
            self.assertEqual(item["classification"], "new")
            self.assertEqual(item["classificationLabel"], "New")
            self.assertEqual(item["reactivatedCount"], 1)
            self.assertTrue(item["stageSummaries"][0]["reactivated"])
            self.assertEqual(item["stageSummaries"][0]["label"], "Staging - Airport Rd")

    def test_latest_import_result_returns_complete_newest_run_and_current_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, config_path = self.make_controller(temp_dir, scanner_store=SimpleNamespace(get_delivery_lists=lambda: [
                {"id": "list-a", "deliveryDate": "2026-07-24"},
                {"id": "list-b", "deliveryDate": "2026-07-29"},
            ]))
            paths = controller._runtime_paths(json.loads(config_path.read_text(encoding="utf-8")))
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            paths["last_run"].write_text(json.dumps({
                "completedAt": "2026-07-23T14:32:00+00:00",
                "startedBy": "admin",
                "runAction": "SqlExportAndImport",
                "succeeded": True,
                "importResults": [
                    {"fileName": "Delivery List 07-24-2026.xlsx", "deliveryDate": "2026-07-24", "classification": "updated", "updatedCount": 2},
                    {"fileName": "Delivery List 07-29-2026.xlsx", "deliveryDate": "2026-07-29", "classification": "no_changes", "reason": "No delivery-list line changes detected"},
                ],
            }), encoding="utf-8")
            payload = controller.get_latest_import_result()
            self.assertEqual(len(payload["latestImportResults"]), 2)
            self.assertEqual(payload["recentImports"], payload["latestImportResults"])
            self.assertEqual(payload["lastCheckedAt"], "2026-07-23T14:32:00+00:00")
            self.assertEqual(payload["latestRun"]["resultCount"], 2)
            self.assertEqual(payload["latestImportResults"][0]["importedAt"], "2026-07-23T14:32:00+00:00")
            self.assertEqual(len(payload["lists"]), 2)
            self.assertIn("SqlExportAndImport", payload["latestRunKey"])

    def test_latest_import_result_exposes_run_failure_without_file_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, config_path = self.make_controller(temp_dir)
            paths = controller._runtime_paths(json.loads(config_path.read_text(encoding="utf-8")))
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            paths["last_run"].write_text(json.dumps({
                "completedAt": "2026-07-23T14:40:00+00:00",
                "runAction": "SqlExportAndImport",
                "succeeded": False,
                "error": "A+W connection failed",
                "importResults": [],
            }), encoding="utf-8")
            payload = controller.get_latest_import_result()
            self.assertEqual(len(payload["latestImportResults"]), 1)
            item = payload["latestImportResults"][0]
            self.assertEqual(item["classification"], "failed")
            self.assertIn("A+W connection failed", item["errors"][0])
            self.assertEqual(item["importedAt"], "2026-07-23T14:40:00+00:00")

    def test_latest_import_result_prefers_import_run_over_newer_export_only_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, config_path = self.make_controller(temp_dir)
            paths = controller._runtime_paths(json.loads(config_path.read_text(encoding="utf-8")))
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            paths["last_run"].write_text(json.dumps({
                "completedAt": "2026-07-23T14:30:00+00:00",
                "runAction": "SqlExportAndImport",
                "succeeded": True,
                "importResults": [{"fileName": "Delivery List 07-24-2026.xlsx", "deliveryDate": "2026-07-24", "classification": "updated"}],
            }), encoding="utf-8")
            paths["gui_run"].write_text(json.dumps({
                "completedAt": "2026-07-23T14:35:00+00:00",
                "runAction": "SqlExportOnly",
                "succeeded": True,
                "importResults": [],
            }), encoding="utf-8")
            payload = controller.get_latest_import_result()
            self.assertEqual(payload["lastCheckedAt"], "2026-07-23T14:30:00+00:00")
            self.assertEqual(payload["latestImportResults"][0]["classification"], "updated")

    def test_dashboard_reads_complete_per_run_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, config_path = self.make_controller(temp_dir)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            paths = controller._runtime_paths(config)
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            log_path = paths["working_root"] / "Logs" / "sql-export-test.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"line {index}" for index in range(1, 121)]
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            paths["last_run"].write_text(
                json.dumps({
                    "completedAt": "2026-07-22T15:00:00+00:00",
                    "succeeded": False,
                    "logPath": str(log_path),
                    "error": "failure",
                }),
                encoding="utf-8",
            )
            with mock.patch.object(controller, "_schedule_installed", return_value=False):
                dashboard = controller.get_dashboard()
            output = dashboard["lastRun"]["commandOutput"]
            self.assertIn("line 1", output)
            self.assertIn("line 120", output)
            self.assertEqual(dashboard["lastRun"]["outputLineCount"], 120)

    def test_finish_run_merges_authoritative_runtime_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, config_path = self.make_controller(temp_dir)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            paths = controller._runtime_paths(config)
            paths["last_run"].parent.mkdir(parents=True, exist_ok=True)
            paths["last_run"].write_text(json.dumps({
                "completedAt": "2026-07-22T15:00:00+00:00",
                "importResults": [{"classification": "updated", "deliveryDate": "2026-07-15"}],
                "importedDates": ["2026-07-15"],
            }), encoding="utf-8")
            process = mock.Mock()
            process.stdout = None
            process.communicate.return_value = ("done", "")
            process.returncode = 0
            controller._finish_run(config, process, {"taskId": "abc", "running": True})
            saved = json.loads(paths["gui_run"].read_text(encoding="utf-8"))
            self.assertEqual(saved["importResults"][0]["classification"], "updated")
            self.assertEqual(saved["importedDates"], ["2026-07-15"])
            self.assertTrue(saved["succeeded"])

    def test_import_history_is_paginated_newest_first_and_filterable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "scanner.db"
            with sqlite3.connect(database, factory=ClosingTestConnection) as connection:
                connection.execute(
                    """
                    CREATE TABLE imports (
                        id INTEGER PRIMARY KEY,
                        delivery_date TEXT,
                        source_name TEXT,
                        row_count INTEGER,
                        total_qty INTEGER,
                        status TEXT,
                        imported_by TEXT,
                        imported_at TEXT,
                        source_path TEXT,
                        source_hash TEXT,
                        import_kind TEXT,
                        change_summary TEXT
                    )
                    """
                )
                rows = []
                for index in range(1, 46):
                    classification = "new" if index % 3 == 0 else "updated"
                    change = {
                        "createdCount": 1 if classification == "new" else 0,
                        "updatedCount": 1 if classification == "updated" else 0,
                        "changedListIds": [f"list-{index}"],
                        "stages": [{"listId": f"list-{index}", "label": f"Stage {index}"}],
                    }
                    rows.append((
                        index,
                        f"2026-08-{((index - 1) % 28) + 1:02d}",
                        f"Delivery List {index:02d}.xlsx",
                        10,
                        12,
                        "published",
                        "automation",
                        f"2026-07-23T{index % 24:02d}:{index % 60:02d}:00+00:00",
                        "",
                        str(index),
                        "temp_folder",
                        json.dumps(change),
                    ))
                connection.executemany("INSERT INTO imports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
            controller, _ = self.make_controller(temp_dir, scanner_store=FakeScannerStore(database))
            page_one = controller.get_import_history(page=1, page_size=20)
            page_three = controller.get_import_history(page=3, page_size=20)
            self.assertEqual(page_one["pageSize"], 20)
            self.assertEqual(page_one["totalCount"], 45)
            self.assertEqual(page_one["totalPages"], 3)
            self.assertEqual(len(page_one["imports"]), 20)
            self.assertEqual(len(page_three["imports"]), 5)
            self.assertGreater(page_one["imports"][0]["id"], page_one["imports"][-1]["id"])

            new_only = controller.get_import_history(page=1, page_size=50, classification="new")
            self.assertTrue(new_only["imports"])
            self.assertTrue(all(item["classification"] == "new" for item in new_only["imports"]))

            searched = controller.get_import_history(page=1, page_size=20, query="Stage 44")
            self.assertEqual(searched["totalCount"], 1)
            self.assertEqual(searched["imports"][0]["sourceName"], "Delivery List 44.xlsx")


if __name__ == "__main__":
    unittest.main()
