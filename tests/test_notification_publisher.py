"""End-to-end test for publishing through a scanner-compatible store API."""

from __future__ import annotations

import base64
import json
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "automation" / "sql_delivery_export" / "publish_automation_notification.py"


class ClosingTestConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class NotificationPublisherTests(unittest.TestCase):
    """Verify the helper writes through create_app_notification, not a new schema."""

    def test_publishes_notification_through_fake_scanner_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            database = project / "scanner.db"
            (project / "scanner_config.py").write_text(
                textwrap.dedent(
                    f"""
                    from types import SimpleNamespace
                    def load_config(root):
                        return SimpleNamespace(database_path=r"{database}")
                    """
                ),
                encoding="utf-8",
            )
            (project / "delivery_store.py").write_text(
                textwrap.dedent(
                    """
                    import sqlite3

                    class ClosingConnection(sqlite3.Connection):
                        def __exit__(self, exc_type, exc_value, traceback):
                            try:
                                return super().__exit__(exc_type, exc_value, traceback)
                            finally:
                                self.close()

                    class Store:
                        def __init__(self, config):
                            self.config = config

                        def initialize(self):
                            pass

                        def connect(self):
                            connection = sqlite3.connect(self.config.database_path, factory=ClosingConnection)
                            connection.execute(
                                "CREATE TABLE IF NOT EXISTS app_notifications ("
                                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                                "notification_type TEXT, title TEXT, message TEXT, "
                                "payload_json TEXT, created_by TEXT, expires_hours INTEGER)"
                            )
                            return connection

                        def create_app_notification(self, con, notification_type, title, message, created_by, payload=None, expires_in_hours=24, acknowledge_creator=False):
                            cursor = con.execute(
                                "INSERT INTO app_notifications (notification_type, title, message, payload_json, created_by, expires_hours) VALUES (?, ?, ?, ?, ?, ?)",
                                (notification_type, title, message, __import__('json').dumps(payload or {}), created_by, expires_in_hours),
                            )
                            return cursor.lastrowid

                    def create_store(config):
                        return Store(config)
                    """
                ),
                encoding="utf-8",
            )
            payload = {"mode": "Incremental", "importedDates": ["2026-07-15"]}
            encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--project-root",
                    str(project),
                    "--type",
                    "success",
                    "--title",
                    "Delivery lists updated",
                    "--message",
                    "Automatic update completed.",
                    "--payload-base64",
                    encoded,
                    "--expires-hours",
                    "12",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with sqlite3.connect(database, factory=ClosingTestConnection) as connection:
                row = connection.execute(
                    "SELECT notification_type, title, message, payload_json, expires_hours FROM app_notifications"
                ).fetchone()
            self.assertEqual(row[0], "success")
            self.assertEqual(row[1], "Delivery lists updated")
            self.assertEqual(row[2], "Automatic update completed.")
            self.assertEqual(json.loads(row[3]), payload)
            self.assertEqual(row[4], 12)


    def test_publishes_notification_from_request_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            database = project / "scanner.db"
            (project / "scanner_config.py").write_text(
                textwrap.dedent(
                    f"""
                    from types import SimpleNamespace
                    def load_config(root):
                        return SimpleNamespace(database_path=r"{database}")
                    """
                ),
                encoding="utf-8",
            )
            (project / "delivery_store.py").write_text(
                textwrap.dedent(
                    """
                    import sqlite3

                    class ClosingConnection(sqlite3.Connection):
                        def __exit__(self, exc_type, exc_value, traceback):
                            try:
                                return super().__exit__(exc_type, exc_value, traceback)
                            finally:
                                self.close()

                    class Store:
                        def __init__(self, config):
                            self.config = config

                        def connect(self):
                            connection = sqlite3.connect(self.config.database_path, factory=ClosingConnection)
                            connection.execute(
                                "CREATE TABLE IF NOT EXISTS app_notifications ("
                                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                                "notification_type TEXT, title TEXT, message TEXT, "
                                "payload_json TEXT, created_by TEXT, expires_hours INTEGER)"
                            )
                            return connection

                        def create_app_notification(self, con, notification_type, title, message, created_by, payload=None, expires_in_hours=24, acknowledge_creator=False):
                            cursor = con.execute(
                                "INSERT INTO app_notifications (notification_type, title, message, payload_json, created_by, expires_hours) VALUES (?, ?, ?, ?, ?, ?)",
                                (notification_type, title, message, __import__('json').dumps(payload or {}), created_by, expires_in_hours),
                            )
                            return cursor.lastrowid

                    def create_store(config):
                        return Store(config)
                    """
                ),
                encoding="utf-8",
            )
            request_path = project / "request.json"
            request_path.write_text(
                json.dumps(
                    {
                        "projectRoot": str(project),
                        "notificationType": "error",
                        "title": "Delivery-list update failed",
                        "message": "The full failure is available in the run log.",
                        "createdBy": "sql-delivery-automation",
                        "payload": {"version": "v115", "logPath": r"C:\DeliveryListAutomation\Logs\run.log"},
                        "expiresHours": 24,
                        "initializeStore": False,
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(PUBLISHER), "--request-file", str(request_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with sqlite3.connect(database, factory=ClosingTestConnection) as connection:
                row = connection.execute(
                    "SELECT notification_type, title, payload_json, expires_hours FROM app_notifications"
                ).fetchone()
            self.assertEqual(row[0], "error")
            self.assertEqual(row[1], "Delivery-list update failed")
            self.assertEqual(json.loads(row[2])["version"], "v115")
            self.assertEqual(row[3], 24)


if __name__ == "__main__":
    unittest.main()
