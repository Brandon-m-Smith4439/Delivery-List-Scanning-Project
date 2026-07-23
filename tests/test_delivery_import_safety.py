"""Regression tests for append-only history-safe delivery-list imports."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from automation.sql_delivery_export.delivery_import_safety import install_safe_delivery_import


class FakeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.native_replace_calls = 0

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def now_iso(self) -> str:
        return "2026-07-23T15:00:00+00:00"

    def get_bay_auto_assign_settings_con(self, _connection):
        return {}

    def clone_item_for_list(self, item, list_id, index, _settings=None):
        order = str(item["order"])
        number = str(item["item"]).zfill(3)
        return {
            "id": f"{list_id}-{index:04d}-{order}-{number}",
            "source_id": str(item.get("id") or f"{order}-{number}"),
            "barcode": f"T200{int(order):06d}{int(number):03d}000",
            "order_no": order,
            "item_no": number,
            "qty": int(item.get("qty") or 0),
            "dimensions": str(item.get("dimensions") or ""),
            "customer": str(item.get("customer") or ""),
            "route": str(item.get("route") or ""),
            "source_route": str(item.get("sourceRoute") or item.get("route") or ""),
            "job": str(item.get("job") or ""),
            "product": str(item.get("product") or ""),
            "process_state": str(item.get("processState") or ""),
            "queue_state": str(item.get("queueState") or ""),
            "suggested_bay": "Standard",
        }

    def available_line_item_id(self, connection, desired_id, _list_id, _source_id, _index):
        if not connection.execute("SELECT 1 FROM line_items WHERE id = ?", (desired_id,)).fetchone():
            return desired_id
        suffix = 2
        while connection.execute("SELECT 1 FROM line_items WHERE id = ?", (f"{desired_id}-{suffix}",)).fetchone():
            suffix += 1
        return f"{desired_id}-{suffix}"

    def import_order_item_key(self, value, order_no, item_no):
        text = str(value or "")
        parts = text.split(":")
        if len(parts) >= 2 and parts[-2].isdigit() and parts[-1].isdigit():
            return f"{parts[-2]}-{parts[-1].zfill(3)}"
        return f"{str(order_no)}-{str(item_no).zfill(3)}"

    def import_business_key(self, values):
        def field(name):
            if hasattr(values, "keys") and name in values.keys():
                return values[name]
            return values.get(name, "")

        return "\x1f".join([
            str(field("order_no") or ""),
            str(field("item_no") or "").zfill(3),
            str(field("dimensions") or "").upper(),
            str(field("customer") or "").upper(),
            str(field("product") or "").upper(),
        ])

    def upsert_delivery_list(self, connection, list_id, label, delivery_date, stage, scanner, items, replace_items):
        if replace_items:
            self.native_replace_calls += 1
            connection.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
        connection.execute(
            """
            INSERT INTO delivery_lists (id, label, delivery_date, stage, scanner, status, revision, created_at)
            VALUES (?, ?, ?, ?, ?, 'active', 1, '2026-07-01')
            ON CONFLICT(id) DO UPDATE SET
              label=excluded.label, delivery_date=excluded.delivery_date,
              stage=excluded.stage, scanner=excluded.scanner, status='active'
            """,
            (list_id, label, delivery_date, stage, scanner),
        )
        return {
            "listId": list_id,
            "stage": stage,
            "scanner": scanner,
            "created": False,
            "newPieceQty": 0,
            "updatedPieceQty": 0,
            "addedPieceQty": 0,
            "changedPieceQty": 0,
            "changedLineCount": 0,
            "originalQty": 0,
            "totalQty": sum(int(item.get("qty") or 0) for item in items),
        }


def initialize_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE delivery_lists (
          id TEXT PRIMARY KEY, label TEXT, delivery_date TEXT, stage TEXT, scanner TEXT,
          status TEXT DEFAULT 'active', revision INTEGER DEFAULT 1, created_at TEXT
        );
        CREATE TABLE line_items (
          id TEXT PRIMARY KEY,
          list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
          source_id TEXT, barcode TEXT, order_no TEXT, item_no TEXT,
          qty INTEGER NOT NULL CHECK(qty >= 0),
          scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK(scanned_qty >= 0 AND scanned_qty <= qty),
          dimensions TEXT, customer TEXT, route TEXT, source_route TEXT,
          job TEXT, product TEXT, process_state TEXT, queue_state TEXT, suggested_bay TEXT,
          priority_delivery_date TEXT DEFAULT '', priority_direct_to_truck INTEGER DEFAULT 0,
          created_at_utc TEXT DEFAULT '', updated_at_utc TEXT DEFAULT '',
          is_deleted INTEGER DEFAULT 0, deleted_at_utc TEXT DEFAULT '', deleted_by_user_id INTEGER
        );
        CREATE TABLE scan_events (
          id INTEGER PRIMARY KEY,
          list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
          line_item_id TEXT REFERENCES line_items(id) ON DELETE SET NULL,
          event_type TEXT
        );
        CREATE TRIGGER trg_scan_events_immutable_update BEFORE UPDATE ON scan_events
        BEGIN SELECT RAISE(ABORT, 'scan_events is append-only'); END;
        CREATE TRIGGER trg_scan_events_immutable_delete BEFORE DELETE ON scan_events
        BEGIN SELECT RAISE(ABORT, 'scan_events is append-only'); END;
        CREATE TABLE rack_items (id INTEGER PRIMARY KEY, line_item_id TEXT, status TEXT);
        CREATE TABLE bay_assignments (id INTEGER PRIMARY KEY, line_item_id TEXT, status TEXT);
        """
    )
    connection.commit()
    connection.close()


class SafeDeliveryImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "scanner.db"
        initialize_database(self.path)
        self.store = FakeStore(self.path)
        self.assertTrue(install_safe_delivery_import(self.store))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def seed_history_line(self, *, scanned_qty: int = 2) -> str:
        list_id = "2026-07-24-staging-airport"
        line_id = f"{list_id}-0001-123456-001"
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO delivery_lists VALUES (?, 'Staging', '2026-07-24', 'Staging', 'Airport', 'active', 1, '2026-07-01')",
                (list_id,),
            )
            connection.execute(
                """
                INSERT INTO line_items (
                  id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty,
                  dimensions, customer, route, source_route, job, product, process_state,
                  queue_state, suggested_bay
                ) VALUES (?, ?, 'source:123456:001', 'OLD', '123456', '001', 3, ?,
                  '10 x 20', 'Old Customer', 'IT', 'IT', 'JOB-1', 'Glass', 'Rush', '', 'Standard')
                """,
                (line_id, list_id, scanned_qty),
            )
            connection.execute(
                "INSERT INTO scan_events (id, list_id, line_item_id, event_type) VALUES (1, ?, ?, 'scan')",
                (list_id, line_id),
            )
            connection.commit()
        return line_id

    def test_updates_history_linked_line_in_place_and_inserts_new_line(self) -> None:
        line_id = self.seed_history_line()
        items = [
            {
                "id": "source:123456:001", "order": "123456", "item": "001", "qty": 4,
                "dimensions": "10 x 20", "customer": "New Customer", "route": "IT",
                "job": "JOB-1", "product": "Glass", "processState": "",
            },
            {
                "id": "source:123456:002", "order": "123456", "item": "002", "qty": 1,
                "dimensions": "8 x 12", "customer": "New Customer", "route": "IT",
                "job": "JOB-1", "product": "Glass",
            },
        ]
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            result = self.store.upsert_delivery_list(
                connection, "2026-07-24-staging-airport", "Staging", "2026-07-24",
                "Staging", "Airport", items, True,
            )
            connection.commit()

            event = connection.execute("SELECT line_item_id FROM scan_events WHERE id = 1").fetchone()
            updated = connection.execute("SELECT * FROM line_items WHERE id = ?", (line_id,)).fetchone()
            rows = connection.execute("SELECT * FROM line_items ORDER BY item_no").fetchall()

        self.assertEqual(event["line_item_id"], line_id)
        self.assertEqual(updated["customer"], "New Customer")
        self.assertEqual(updated["qty"], 4)
        self.assertEqual(updated["scanned_qty"], 2)
        self.assertIn("Rush", updated["process_state"])
        self.assertIn("Updated Line", updated["process_state"])
        self.assertEqual(len(rows), 2)
        self.assertIn("New Line", rows[1]["process_state"])
        self.assertEqual(result["updatedPieceQty"], 4)
        self.assertEqual(result["newPieceQty"], 1)
        self.assertTrue(result["safeInPlaceUpdate"])
        self.assertEqual(self.store.native_replace_calls, 0)

    def test_removed_history_line_is_retired_without_mutating_event(self) -> None:
        line_id = self.seed_history_line(scanned_qty=2)
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            result = self.store.upsert_delivery_list(
                connection, "2026-07-24-staging-airport", "Staging", "2026-07-24",
                "Staging", "Airport", [], True,
            )
            connection.commit()
            event = connection.execute("SELECT line_item_id FROM scan_events WHERE id = 1").fetchone()
            retired = connection.execute("SELECT * FROM line_items WHERE id = ?", (line_id,)).fetchone()

        self.assertEqual(event["line_item_id"], line_id)
        self.assertEqual(retired["qty"], 2)
        self.assertEqual(retired["scanned_qty"], 2)
        self.assertIn("Removed Line", retired["process_state"])
        self.assertIn("Removed from latest import", retired["queue_state"])
        self.assertEqual(result["removedLineCount"], 1)
        self.assertEqual(result["removedPieceQty"], 3)

    def test_removed_unreferenced_line_is_deleted(self) -> None:
        list_id = "2026-07-24-staging-airport"
        line_id = f"{list_id}-0001-123456-001"
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO delivery_lists VALUES (?, 'Staging', '2026-07-24', 'Staging', 'Airport', 'active', 1, '2026-07-01')",
                (list_id,),
            )
            connection.execute(
                """
                INSERT INTO line_items (
                  id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty,
                  dimensions, customer, route, source_route, job, product, process_state,
                  queue_state, suggested_bay
                ) VALUES (?, ?, 'source:123456:001', 'OLD', '123456', '001', 3, 0,
                  '10 x 20', 'Old Customer', 'IT', 'IT', 'JOB-1', 'Glass', '', '', 'Standard')
                """,
                (line_id, list_id),
            )
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
            self.store.upsert_delivery_list(
                connection, list_id, "Staging", "2026-07-24", "Staging", "Airport", [], True,
            )
            connection.commit()
            remaining = connection.execute("SELECT 1 FROM line_items WHERE id = ?", (line_id,)).fetchone()

        self.assertIsNone(remaining)


if __name__ == "__main__":
    unittest.main()

class PerUserStore(FakeStore):
    def import_delivery_list(self, data):
        payload = data.get("payload") or data
        list_id = f"{payload['deliveryDate']}-staging-airport"
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            summary = self.upsert_delivery_list(
                connection,
                list_id,
                "Staging - Airport Rd",
                payload["deliveryDate"],
                "Staging",
                "Airport Rd",
                list(payload.get("items") or []),
                True,
            )
            connection.commit()
        return {
            "activeListId": list_id,
            "createdCount": 0,
            "updatedCount": 1 if summary.get("changedLineCount") else 0,
            "changedListIds": [list_id] if summary.get("changedLineCount") else [],
            "stageSummaries": [summary],
            "reactivatedListIds": [],
        }

    def get_delivery_list(self, list_id, last_scan=None, user=None):
        with self.connect() as connection:
            list_row = connection.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            rows = connection.execute("SELECT * FROM line_items WHERE list_id = ? ORDER BY item_no", (list_id,)).fetchall()
        return {
            "id": list_id,
            "deliveryDate": list_row["delivery_date"],
            "items": [
                {
                    "id": row["id"],
                    "order": row["order_no"],
                    "item": row["item_no"],
                    "qty": row["qty"],
                    "processState": row["process_state"],
                }
                for row in rows
            ],
        }

    def get_delivery_lists(self, user=None):
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM delivery_lists WHERE status = 'active' ORDER BY id").fetchall()
        return [
            {"id": row["id"], "deliveryDate": row["delivery_date"], "label": row["label"]}
            for row in rows
        ]

    def get_pending_notifications(self, username, limit=5):
        return [
            {"id": 1, "title": "Rush", "details": {"source": "rush"}},
            {"id": 2, "title": "Automation", "details": {"source": "sql-delivery-automation"}},
            {"id": 3, "title": "System", "details": {"source": "system"}},
        ][:limit]


class PerUserLineUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "scanner.db"
        initialize_database(self.path)
        with sqlite3.connect(self.path) as connection:
            connection.executescript(
                """
                CREATE TABLE users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL UNIQUE,
                  display_name TEXT DEFAULT '',
                  active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE line_update_notices (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  line_item_id TEXT NOT NULL,
                  list_id TEXT NOT NULL,
                  delivery_date TEXT NOT NULL,
                  change_type TEXT NOT NULL,
                  change_token TEXT NOT NULL,
                  source_hash TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  UNIQUE(line_item_id, change_type, change_token)
                );
                CREATE TABLE line_update_receipts (
                  notice_id INTEGER NOT NULL REFERENCES line_update_notices(id) ON DELETE CASCADE,
                  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                  seen_at TEXT NOT NULL,
                  PRIMARY KEY (notice_id, user_id)
                );
                INSERT INTO users (username, display_name) VALUES ('alice', 'Alice'), ('bob', 'Bob');
                """
            )
            connection.commit()
        self.store = PerUserStore(self.path)
        self.assertTrue(install_safe_delivery_import(self.store))
        self.list_id = "2026-07-24-staging-airport"
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO delivery_lists VALUES (?, 'Staging', '2026-07-24', 'Staging', 'Airport', 'active', 1, '2026-07-01')",
                (self.list_id,),
            )
            connection.execute(
                """
                INSERT INTO line_items (
                  id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty,
                  dimensions, customer, route, source_route, job, product, process_state,
                  queue_state, suggested_bay
                ) VALUES (?, ?, 'source:123456:001', 'OLD', '123456', '001', 3, 1,
                  '10 x 20', 'Customer', 'IT', 'IT', 'JOB-1', 'Glass', '', '', 'Standard')
                """,
                (f"{self.list_id}-0001-123456-001", self.list_id),
            )
            connection.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def import_update(self, qty=4, include_new=True, source_hash="hash-a"):
        items = [
            {
                "id": "source:123456:001", "order": "123456", "item": "001", "qty": qty,
                "dimensions": "10 x 20", "customer": "Customer", "route": "IT",
                "job": "JOB-1", "product": "Glass",
            }
        ]
        if include_new:
            items.append(
                {
                    "id": "source:123456:002", "order": "123456", "item": "002", "qty": 1,
                    "dimensions": "8 x 12", "customer": "Customer", "route": "IT",
                    "job": "JOB-1", "product": "Glass",
                }
            )
        return self.store.import_delivery_list(
            {"payload": {"deliveryDate": "2026-07-24", "items": items}, "sourceHash": source_hash}
        )

    def test_updates_persist_per_user_until_explicit_review(self):
        self.import_update()
        alice = self.store.get_user_line_update_summary("alice", self.list_id)
        bob = self.store.get_user_line_update_summary("bob", self.list_id)
        self.assertEqual(alice["pendingLineCount"], 2)
        self.assertEqual(alice["newLineCount"], 1)
        self.assertEqual(alice["updatedLineCount"], 1)
        self.assertEqual(bob["pendingLineCount"], 2)

        payload = self.store.get_delivery_list(self.list_id, user={"username": "alice"})
        states = {item["item"]: item["processState"] for item in payload["items"]}
        self.assertIn("Updated Line", states["001"])
        self.assertIn("New Line", states["002"])

        self.store.acknowledge_user_line_updates("alice", self.list_id)
        self.assertEqual(self.store.get_user_line_update_summary("alice", self.list_id)["pendingLineCount"], 0)
        self.assertEqual(self.store.get_user_line_update_summary("bob", self.list_id)["pendingLineCount"], 2)
        alice_payload = self.store.get_delivery_list(self.list_id, user={"username": "alice"})
        self.assertTrue(all("New Line" not in item["processState"] and "Updated Line" not in item["processState"] for item in alice_payload["items"]))

    def test_acknowledging_exact_notice_ids_clears_only_the_reviewed_snapshot(self):
        self.import_update()
        before = self.store.get_user_line_update_summary("alice", self.list_id)
        notice_ids = sorted(notice["id"] for notice in before["notices"])
        self.assertEqual(len(notice_ids), 2)

        partial = self.store.acknowledge_user_line_updates("alice", self.list_id, [notice_ids[0]])
        self.assertEqual(partial["acknowledgedCount"], 1)
        self.assertEqual(partial["pendingLineCount"], 1)
        self.assertEqual({notice["id"] for notice in partial["notices"]}, {notice_ids[1]})

        complete = self.store.acknowledge_user_line_updates("alice", self.list_id, [notice_ids[1]])
        self.assertEqual(complete["acknowledgedCount"], 1)
        self.assertEqual(complete["pendingLineCount"], 0)
        payload = self.store.get_delivery_list(self.list_id, user={"username": "alice"})
        self.assertTrue(all("New Line" not in item["processState"] and "Updated Line" not in item["processState"] for item in payload["items"]))

    def test_no_change_reimport_does_not_clear_or_duplicate_unseen_updates(self):
        self.import_update()
        first = self.store.get_user_line_update_summary("alice", self.list_id)
        self.import_update()
        second = self.store.get_user_line_update_summary("alice", self.list_id)
        self.assertEqual(first["pendingNoticeCount"], second["pendingNoticeCount"])
        self.assertEqual(second["pendingLineCount"], 2)

    def test_later_change_creates_a_new_notice_after_review(self):
        self.import_update()
        self.store.acknowledge_user_line_updates("alice", self.list_id)
        self.import_update(qty=5, source_hash="hash-b")
        summary = self.store.get_user_line_update_summary("alice", self.list_id)
        self.assertEqual(summary["pendingLineCount"], 1)
        self.assertEqual(summary["updatedLineCount"], 1)

    def test_removed_line_is_not_left_in_new_updated_review_queue(self):
        self.import_update()
        before = self.store.get_user_line_update_summary("alice", self.list_id)
        self.assertEqual(before["pendingLineCount"], 2)

        self.import_update(qty=4, include_new=False, source_hash="hash-remove")
        after = self.store.get_user_line_update_summary("alice", self.list_id)
        self.assertEqual(after["pendingLineCount"], 1)
        self.assertEqual({notice["lineItemId"] for notice in after["notices"]}, {
            f"{self.list_id}-0001-123456-001"
        })

    def test_automation_notifications_are_removed_from_rush_popup_queue(self):
        pending = self.store.get_pending_notifications("alice", 5)
        self.assertEqual([item["id"] for item in pending], [1, 3])

    def test_many_automation_notices_cannot_crow_out_rush_popup(self):
        with self.store.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE app_notifications (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  notification_type TEXT NOT NULL DEFAULT 'notice',
                  title TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '',
                  payload_json TEXT NOT NULL DEFAULT '{}', created_by TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL, expires_at TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE app_notification_receipts (
                  notification_id INTEGER NOT NULL,
                  user_id INTEGER NOT NULL,
                  acknowledged_at TEXT NOT NULL,
                  PRIMARY KEY (notification_id, user_id)
                );
                """
            )
            for index in range(25):
                connection.execute(
                    """
                    INSERT INTO app_notifications (
                      notification_type, title, message, payload_json, created_by, created_at, expires_at, active
                    ) VALUES ('notice', ?, 'Automation', '{"source":"sql-delivery-automation"}', 'system',
                              '2026-07-23T12:00:00+00:00', '2099-01-01T00:00:00+00:00', 1)
                    """,
                    (f"Automation {index + 1}",),
                )
            connection.execute(
                """
                INSERT INTO app_notifications (
                  notification_type, title, message, payload_json, created_by, created_at, expires_at, active
                ) VALUES ('warning', 'Rush', 'Rush order', '{"source":"rush"}', 'system',
                          '2026-07-23T12:01:00+00:00', '2099-01-01T00:00:00+00:00', 1)
                """
            )
            connection.commit()
        pending = self.store.get_pending_notifications("alice", 5)
        self.assertEqual([item["title"] for item in pending], ["Rush"])
