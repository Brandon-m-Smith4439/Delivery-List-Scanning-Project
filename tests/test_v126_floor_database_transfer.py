"""Safety tests for the v128 floor database transfer utility."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "upgrade_floor_database.py"
BAT = ROOT / "Transfer-Floor-Database-To-Current-Version.bat"


CORE_TABLES = (
    "delivery_lists",
    "line_items",
    "scan_events",
    "audit_events",
    "users",
    "racks",
    "bays",
)


def create_floor_database(path: Path, marker: str = "floor") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(
            """
            CREATE TABLE delivery_lists (id TEXT PRIMARY KEY, delivery_date TEXT, stage TEXT, status TEXT);
            CREATE TABLE line_items (id TEXT PRIMARY KEY, list_id TEXT, order_no TEXT, item_no TEXT, qty INTEGER, scanned_qty INTEGER);
            CREATE TABLE scan_events (id INTEGER PRIMARY KEY, list_id TEXT, event_type TEXT, created_at TEXT);
            CREATE TABLE audit_events (id INTEGER PRIMARY KEY, entity_type TEXT, action TEXT, created_at TEXT);
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, active INTEGER);
            CREATE TABLE racks (id INTEGER PRIMARY KEY, rack_code TEXT, status TEXT);
            CREATE TABLE bays (id INTEGER PRIMARY KEY, bay_code TEXT, active INTEGER);
            """
        )
        con.execute("INSERT INTO delivery_lists VALUES (?, '2026-07-29', 'Staging', 'active')", (f"{marker}-list",))
        con.execute("INSERT INTO line_items VALUES (?, ?, '235000', '001', 3, 2)", (f"{marker}-line", f"{marker}-list"))
        con.execute("INSERT INTO scan_events VALUES (1, ?, 'scan', '2026-07-23T12:00:00+00:00')", (f"{marker}-list",))
        con.execute("INSERT INTO audit_events VALUES (1, 'delivery_list', 'import', '2026-07-23T12:00:00+00:00')")
        con.execute("INSERT INTO users VALUES (1, 'operator', 1)")
        con.execute("INSERT INTO racks VALUES (1, 'T1', 'Open')")
        con.execute("INSERT INTO bays VALUES (1, 'A1', 1)")
        con.commit()
    finally:
        con.close()


def create_fake_project(project: Path, fail_initialize: bool = False) -> Path:
    (project / "data").mkdir(parents=True, exist_ok=True)
    (project / "scanner_config.py").write_text(
        """from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class Config:
    database_type: str
    database_path: Path

def load_config(root):
    root = Path(root)
    path = Path(os.environ.get("DLS_DATABASE_PATH", root / "data" / "delivery-scanner-pilot.db"))
    return Config(os.environ.get("DLS_DATABASE_TYPE", "sqlite"), path)
""",
        encoding="utf-8",
    )
    (project / "database_contract.py").write_text("CURRENT_SCHEMA_VERSION = 3\n", encoding="utf-8")
    if fail_initialize:
        store_text = """def create_store(config):\n    return Store(config)\nclass Store:\n    def __init__(self, config): self.config = config\n    def initialize(self): raise RuntimeError('simulated migration failure')\n"""
    else:
        store_text = """import sqlite3\ndef create_store(config):\n    return Store(config)\nclass Store:\n    def __init__(self, config): self.config = config\n    def initialize(self):\n        con = sqlite3.connect(self.config.database_path)\n        try:\n            con.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT, checksum TEXT, applied_at_utc TEXT, execution_ms INTEGER, app_version TEXT)')\n            for version in (1, 2, 3):\n                con.execute('INSERT OR IGNORE INTO schema_migrations VALUES (?, ?, ?, ?, 0, ?)', (version, f'migration-{version}', f'checksum-{version}', '2026-07-23T12:00:00+00:00', '126'))\n            con.execute('CREATE TABLE IF NOT EXISTS v126_feature (id INTEGER PRIMARY KEY, value TEXT)')\n            con.commit()\n        finally:\n            con.close()\n"""
    (project / "delivery_store.py").write_text(store_text, encoding="utf-8")
    return project / "data" / "delivery-scanner-pilot.db"


class FloorDatabaseTransferTests(unittest.TestCase):
    def test_package_files_and_bat_safety_prompts_exist(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(BAT.is_file())
        text = BAT.read_text(encoding="ascii")
        self.assertIn("Close the web app/server", text)
        self.assertIn("upgrade_floor_database.py", text)
        self.assertIn("--project-root", text)
        self.assertIn("--interactive", text)
        self.assertIn("pause >nul", text)
        self.assertIn("floor-database-transfer-launch.log", text)
        self.assertIn('for %%I in ("%PROJECT_ROOT%.") do set "PROJECT_ROOT=%%~fI"', text)
        self.assertIn('set "SCRIPT=%PROJECT_ROOT%\\tools\\upgrade_floor_database.py"', text)
        self.assertNotIn('set "SCRIPT=%PROJECT_ROOT%tools\\upgrade_floor_database.py"', text)
        self.assertNotIn("set /p", text.lower())

    def test_legacy_merged_project_root_argument_is_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "current-project"
            target = create_fake_project(project)
            old_project = temp / "old-floor-project"
            source = old_project / "data" / "delivery-scanner-pilot.db"
            create_floor_database(source)

            merged_project_argument = f'{project}" --interactive'
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    merged_project_argument,
                    "--yes",
                ],
                input=str(old_project) + "\n",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Old floor project/database path:", result.stdout)
            con = sqlite3.connect(target)
            try:
                self.assertEqual(con.execute("SELECT id FROM delivery_lists").fetchone()[0], "floor-list")
            finally:
                con.close()

    def test_interactive_source_prompt_accepts_a_folder_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "current-project"
            target = create_fake_project(project)
            old_project = temp / "old & floor project"
            source = old_project / "data" / "delivery-scanner-pilot.db"
            create_floor_database(source)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(project),
                    "--interactive",
                    "--yes",
                ],
                input=str(old_project) + "\n",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Old floor project/database path:", result.stdout)
            con = sqlite3.connect(target)
            try:
                self.assertEqual(con.execute("SELECT id FROM delivery_lists").fetchone()[0], "floor-list")
            finally:
                con.close()

    def test_successful_transfer_preserves_floor_rows_and_upgrades_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "current-project"
            target = create_fake_project(project)
            con = sqlite3.connect(target)
            con.execute("CREATE TABLE target_only (value TEXT)")
            con.execute("INSERT INTO target_only VALUES ('current-target')")
            con.commit()
            con.close()

            old_project = temp / "old-floor-project"
            source = old_project / "data" / "delivery-scanner-pilot.db"
            create_floor_database(source)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(project),
                    "--source",
                    str(old_project),
                    "--yes",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            con = sqlite3.connect(target)
            try:
                self.assertEqual(con.execute("SELECT id FROM delivery_lists").fetchone()[0], "floor-list")
                self.assertEqual(con.execute("SELECT scanned_qty FROM line_items").fetchone()[0], 2)
                self.assertEqual(con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 3)
                self.assertIsNotNone(con.execute("SELECT name FROM sqlite_master WHERE name = 'v126_feature'").fetchone())
                self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE name = 'target_only'").fetchone())
            finally:
                con.close()

            backup_folders = list((project / "data" / "backups").glob("floor-database-transfer-*"))
            self.assertEqual(len(backup_folders), 1)
            backup = backup_folders[0]
            self.assertTrue((backup / "old-floor-database-original.db").is_file())
            self.assertTrue((backup / "current-target-before-transfer.db").is_file())
            report = json.loads((backup / "transfer-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["expected_schema_version"], 3)
            self.assertEqual(report["preserved_table_counts"]["scan_events"], {"before": 1, "after": 1})

            backup_con = sqlite3.connect(backup / "current-target-before-transfer.db")
            try:
                self.assertEqual(backup_con.execute("SELECT value FROM target_only").fetchone()[0], "current-target")
            finally:
                backup_con.close()

    def test_failed_migration_restores_the_prior_current_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "current-project"
            target = create_fake_project(project, fail_initialize=True)
            con = sqlite3.connect(target)
            con.execute("CREATE TABLE target_only (value TEXT)")
            con.execute("INSERT INTO target_only VALUES ('restore-me')")
            con.commit()
            con.close()

            source = temp / "old.db"
            create_floor_database(source)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(project),
                    "--source",
                    str(source),
                    "--yes",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)

            con = sqlite3.connect(target)
            try:
                self.assertEqual(con.execute("SELECT value FROM target_only").fetchone()[0], "restore-me")
                self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE name = 'delivery_lists'").fetchone())
            finally:
                con.close()

            backup_folders = list((project / "data" / "backups").glob("floor-database-transfer-*"))
            self.assertEqual(len(backup_folders), 1)
            report = json.loads((backup_folders[0] / "transfer-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertIn("restored", report["message"].lower())
            self.assertTrue((backup_folders[0] / "old-floor-database-original.db").is_file())

    def test_incomplete_source_is_rejected_before_target_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "current-project"
            target = create_fake_project(project)
            con = sqlite3.connect(target)
            con.execute("CREATE TABLE target_only (value TEXT)")
            con.execute("INSERT INTO target_only VALUES ('unchanged')")
            con.commit()
            con.close()

            source = temp / "not-scanner.db"
            con = sqlite3.connect(source)
            con.execute("CREATE TABLE delivery_lists (id TEXT)")
            con.commit()
            con.close()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(project),
                    "--source",
                    str(source),
                    "--yes",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required tables", (result.stdout + result.stderr).lower())
            con = sqlite3.connect(target)
            try:
                self.assertEqual(con.execute("SELECT value FROM target_only").fetchone()[0], "unchanged")
            finally:
                con.close()
            self.assertFalse((project / "data" / "backups").exists())


if __name__ == "__main__":
    unittest.main()
