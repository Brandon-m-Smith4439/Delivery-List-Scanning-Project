from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database_migrations import _migration_004_v135_operations_workflows
from operations_features import OperationsFeatureService


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class FakeStore:
    database_type = "sqlite"

    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        con = sqlite3.connect(self.path, factory=ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def insert_line_items(self, con, list_id, items):
        inserted = []
        for index, item in enumerate(items, start=1):
            order = str(item["order"])
            item_no = str(item["item"]).zfill(3)
            line_id = f"{list_id}-manual-{order}-{item_no}-{index}"
            row = {
                "id": line_id,
                "source_id": str(item.get("id") or f"{order}-{item_no}"),
                "barcode": f"T200{order.zfill(6)}{item_no}",
                "order_no": order,
                "item_no": item_no,
                "qty": int(item.get("qty") or 0),
                "dimensions": str(item.get("dimensions") or ""),
                "customer": str(item.get("customer") or ""),
                "route": str(item.get("route") or ""),
                "source_route": str(item.get("sourceRoute") or ""),
                "job": str(item.get("job") or ""),
                "product": str(item.get("product") or ""),
                "process_state": str(item.get("processState") or ""),
                "queue_state": str(item.get("queueState") or ""),
                "suggested_bay": "",
            }
            con.execute(
                """
                INSERT INTO line_items (
                    id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty,
                    dimensions, customer, route, source_route, job, product, process_state,
                    queue_state, suggested_bay, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')
                """,
                (
                    row["id"], list_id, row["source_id"], row["barcode"], row["order_no"],
                    row["item_no"], row["qty"], row["dimensions"], row["customer"], row["route"],
                    row["source_route"], row["job"], row["product"], row["process_state"],
                    row["queue_state"], row["suggested_bay"],
                ),
            )
            inserted.append(row)
        return inserted


@pytest.fixture()
def database(tmp_path: Path):
    path = tmp_path / "scanner.db"
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE delivery_lists (
            id TEXT PRIMARY KEY, delivery_date TEXT NOT NULL, stage TEXT NOT NULL,
            scanner TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE line_items (
            id TEXT PRIMARY KEY, list_id TEXT NOT NULL, source_id TEXT NOT NULL DEFAULT '',
            barcode TEXT NOT NULL DEFAULT '', order_no TEXT NOT NULL, item_no TEXT NOT NULL,
            qty INTEGER NOT NULL, scanned_qty INTEGER NOT NULL DEFAULT 0,
            dimensions TEXT NOT NULL DEFAULT '', customer TEXT NOT NULL DEFAULT '',
            route TEXT NOT NULL DEFAULT '', source_route TEXT NOT NULL DEFAULT '', job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '', process_state TEXT NOT NULL DEFAULT '', queue_state TEXT NOT NULL DEFAULT '',
            suggested_bay TEXT NOT NULL DEFAULT '', priority_delivery_date TEXT NOT NULL DEFAULT '',
            priority_direct_to_truck INTEGER NOT NULL DEFAULT 0, manual_only INTEGER NOT NULL DEFAULT 0,
            manual_source TEXT NOT NULL DEFAULT '', internal_reject_count INTEGER NOT NULL DEFAULT 0,
            last_reject_reason TEXT NOT NULL DEFAULT '', last_reject_location TEXT NOT NULL DEFAULT '',
            last_rejected_at TEXT NOT NULL DEFAULT '', updated_at_utc TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE line_update_notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT, line_item_id TEXT NOT NULL, list_id TEXT NOT NULL,
            delivery_date TEXT NOT NULL, change_type TEXT NOT NULL, change_token TEXT NOT NULL,
            source_hash TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            UNIQUE(line_item_id, change_type, change_token)
        );
        CREATE TABLE line_update_receipts (
            notice_id INTEGER NOT NULL, user_id INTEGER NOT NULL, seen_at TEXT NOT NULL,
            PRIMARY KEY(notice_id, user_id)
        );
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
            action TEXT NOT NULL, user_name TEXT NOT NULL DEFAULT '', station TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '', payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE TABLE scan_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, list_id TEXT NOT NULL, line_item_id TEXT,
            barcode TEXT NOT NULL DEFAULT '', canonical_barcode TEXT NOT NULL DEFAULT '',
            user_name TEXT NOT NULL DEFAULT '', station TEXT NOT NULL DEFAULT '', event_type TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '', qty_delta INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE racks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rack_code TEXT UNIQUE, display_name TEXT NOT NULL DEFAULT '',
            rack_type TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Open', active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE rack_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rack_id INTEGER NOT NULL, line_item_id TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'Active', added_by TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL DEFAULT '', removed_by TEXT NOT NULL DEFAULT '', removed_at TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '', updated_at_utc TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE bay_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, line_item_id TEXT NOT NULL, assigned_qty INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Assigned', cleared_by TEXT NOT NULL DEFAULT '', cleared_at TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '', updated_at_utc TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE reject_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT UNIQUE, active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0, created_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE reject_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT UNIQUE, active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0, created_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE reject_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, delivery_date TEXT NOT NULL, order_no TEXT NOT NULL,
            item_no TEXT NOT NULL, qty INTEGER NOT NULL, customer TEXT NOT NULL DEFAULT '', job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '', reason_label TEXT NOT NULL, location_label TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '', rejected_at TEXT NOT NULL, rejected_by TEXT NOT NULL DEFAULT '',
            source_list_id TEXT NOT NULL DEFAULT '', source_line_item_id TEXT NOT NULL DEFAULT '',
            affected_list_ids_json TEXT NOT NULL DEFAULT '[]', scan_qty_reduced INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE packing_list_prints (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rack_code TEXT NOT NULL, rack_name TEXT NOT NULL DEFAULT '',
            delivery_date TEXT NOT NULL DEFAULT '', printed_at TEXT NOT NULL, printed_by TEXT NOT NULL DEFAULT '',
            piece_qty INTEGER NOT NULL DEFAULT 0, line_count INTEGER NOT NULL DEFAULT 0,
            snapshot_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE manual_delivery_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, delivery_date TEXT NOT NULL, order_no TEXT NOT NULL,
            item_no TEXT NOT NULL, qty INTEGER NOT NULL, route TEXT NOT NULL, customer TEXT NOT NULL DEFAULT '',
            job TEXT NOT NULL DEFAULT '', product TEXT NOT NULL DEFAULT '', dimensions TEXT NOT NULL DEFAULT '',
            manual_only INTEGER NOT NULL DEFAULT 0, created_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            target_list_ids_json TEXT NOT NULL DEFAULT '[]'
        );
        """
    )
    con.executemany("INSERT INTO users(id, username, active) VALUES (?, ?, 1)", [(1, "alice"), (2, "bob")])
    con.execute("INSERT INTO reject_reasons(label, created_at) VALUES ('Damaged / broken', '2026-07-24T12:00:00+00:00')")
    con.execute("INSERT INTO reject_locations(label, created_at) VALUES ('Tempering', '2026-07-24T12:00:00+00:00')")
    con.commit()
    con.close()
    return path, FakeStore(path)


def add_list(con, list_id, stage, date="2026-07-29", scanner="Airport Rd"):
    con.execute(
        "INSERT INTO delivery_lists(id, delivery_date, stage, scanner, status) VALUES (?, ?, ?, ?, 'active')",
        (list_id, date, stage, scanner),
    )


def add_line(con, line_id, list_id, order="123456", item="001", qty=4, scanned=0):
    con.execute(
        """
        INSERT INTO line_items (
            id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty,
            customer, job, product, dimensions, route
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Customer', 'Job 1', 'Clear Tempered', '24 x 36', 'IT')
        """,
        (line_id, list_id, f"source-{order}-{item}", f"T200{order}{item}", order, item, qty, scanned),
    )


def service(database):
    path, store = database
    return OperationsFeatureService(store, object(), ROOT), path


def test_line_updates_are_personal_and_clear_only_after_explicit_ack(database):
    ops, path = service(database)
    con = sqlite3.connect(path)
    add_list(con, "list-stage", "Staging")
    add_line(con, "line-1", "list-stage")
    con.execute(
        "INSERT INTO line_update_notices(line_item_id, list_id, delivery_date, change_type, change_token, created_at) VALUES ('line-1', 'list-stage', '2026-07-29', 'new', 'token-1', '2026-07-24T12:00:00+00:00')"
    )
    con.commit()
    con.close()

    alice = ops.line_flags("list-stage", "alice")
    bob = ops.line_flags("list-stage", "bob")
    assert alice["pendingLineCount"] == 1
    assert bob["pendingLineCount"] == 1
    notice_id = alice["noticeIds"][0]

    cleared = ops.acknowledge_line_updates("list-stage", [notice_id], "alice")
    assert cleared["pendingLineCount"] == 0
    assert ops.line_flags("list-stage", "bob")["pendingLineCount"] == 1


def test_line_update_ack_rejects_stale_or_wrong_notice_ids(database):
    ops, path = service(database)
    con = sqlite3.connect(path)
    add_list(con, "list-stage", "Staging")
    add_line(con, "line-1", "list-stage")
    con.execute(
        "INSERT INTO line_update_notices(line_item_id, list_id, delivery_date, change_type, change_token, created_at) VALUES ('line-1', 'list-stage', '2026-07-29', 'updated', 'token-2', '2026-07-24T12:00:00+00:00')"
    )
    con.commit()
    con.close()
    with pytest.raises(ValueError, match="changed before"):
        ops.acknowledge_line_updates("list-stage", [999], "alice")


def test_internal_reject_resets_scan_rack_and_bay_quantities(database):
    ops, path = service(database)
    con = sqlite3.connect(path)
    add_list(con, "staging", "Staging")
    add_list(con, "outbound", "Outbound")
    add_line(con, "line-stage", "staging", scanned=2)
    add_line(con, "line-out", "outbound", scanned=1)
    con.execute("INSERT INTO racks(rack_code, display_name, rack_type, status) VALUES ('R1S', 'Rack 1 Steel', 'Steel', 'Open')")
    rack_id = con.execute("SELECT id FROM racks WHERE rack_code='R1S'").fetchone()[0]
    con.execute("INSERT INTO rack_items(rack_id, line_item_id, qty, status, added_at) VALUES (?, 'line-stage', 2, 'Active', '2026-07-24T12:00:00+00:00')", (rack_id,))
    con.execute("INSERT INTO bay_assignments(line_item_id, assigned_qty, status) VALUES ('line-out', 1, 'Assigned')")
    con.commit()
    con.close()

    result = ops.create_reject(
        {"order": "123456", "item": "1", "deliveryDate": "2026-07-29", "qty": 1, "reason": "Damaged / broken", "location": "Tempering"},
        "alice",
    )
    assert result["ok"] is True

    con = sqlite3.connect(path)
    assert con.execute("SELECT scanned_qty FROM line_items WHERE id='line-stage'").fetchone()[0] == 1
    assert con.execute("SELECT scanned_qty FROM line_items WHERE id='line-out'").fetchone()[0] == 0
    assert con.execute("SELECT qty FROM rack_items WHERE line_item_id='line-stage'").fetchone()[0] == 1
    bay = con.execute("SELECT assigned_qty, status FROM bay_assignments WHERE line_item_id='line-out'").fetchone()
    assert bay == (0, "Cleared")
    assert con.execute("SELECT COUNT(*) FROM scan_events WHERE event_type='reject_reset'").fetchone()[0] == 2
    assert con.execute("SELECT COUNT(*) FROM reject_events").fetchone()[0] == 1
    con.close()


def test_manual_order_requires_unique_order_item_and_populates_route_stages(database, monkeypatch):
    ops, path = service(database)
    monkeypatch.setattr(ops, "_automation_window", lambda: ("2026-07-01", "2026-10-31"))
    con = sqlite3.connect(path)
    add_list(con, "stage", "Staging")
    add_list(con, "out", "Outbound")
    add_list(con, "it", "Inbound - Indian Trail", scanner="Indian Trail")
    add_list(con, "cpu", "Customer Pickup", scanner="Customer Pickup")
    con.commit()
    con.close()

    result = ops.create_manual_order(
        {
            "listId": "stage", "order": "998877", "item": "2", "qty": 2,
            "route": "IT", "customer": "Manual Customer", "product": "Clear Tempered",
            "dimensions": "30 x 40", "job": "Manual Job", "manualOnly": True,
        },
        "alice",
    )
    assert set(result["listIds"]) == {"stage", "out", "it"}

    con = sqlite3.connect(path)
    rows = con.execute("SELECT list_id, manual_only, barcode FROM line_items WHERE order_no='998877'").fetchall()
    assert {row[0] for row in rows} == {"stage", "out", "it"}
    assert all(row[1] == 1 and row[2] == "MANUAL-998877-002" for row in rows)
    assert con.execute("SELECT COUNT(*) FROM line_update_notices WHERE change_type='new'").fetchone()[0] == 3
    con.close()

    with pytest.raises(ValueError, match="already exists"):
        ops.create_manual_order(
            {
                "listId": "stage", "order": "998877", "item": "2", "qty": 1,
                "route": "IT", "customer": "Manual Customer", "product": "Clear Tempered",
                "dimensions": "30 x 40", "manualOnly": False,
            },
            "alice",
        )


def test_packing_print_history_is_an_immutable_snapshot(database):
    ops, path = service(database)
    con = sqlite3.connect(path)
    add_list(con, "stage", "Staging")
    add_line(con, "line-1", "stage", qty=3)
    con.execute("INSERT INTO racks(rack_code, display_name, rack_type, status) VALUES ('R2W', 'Rack 2 Wood', 'Wood', 'Closed')")
    rack_id = con.execute("SELECT id FROM racks WHERE rack_code='R2W'").fetchone()[0]
    con.execute("INSERT INTO rack_items(rack_id, line_item_id, qty, status, added_at) VALUES (?, 'line-1', 2, 'Active', '2026-07-24T12:00:00+00:00')", (rack_id,))
    con.commit()
    con.close()

    recorded = ops.record_packing_print({"rackCode": "R2W", "deliveryDate": "2026-07-29"}, "alice")
    history = ops.packing_history()
    assert recorded["historyId"] == history["history"][0]["id"]
    assert history["history"][0]["piece_qty"] == 2
    html = ops.packing_history_print_html(recorded["historyId"])
    assert "Historical Packing List" in html
    assert "123456" in html


def test_migration_004_adds_columns_tables_and_default_catalogs(tmp_path: Path):
    path = tmp_path / "migration.db"
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE line_items (id TEXT PRIMARY KEY)")
    _migration_004_v135_operations_workflows(con)
    con.commit()
    columns = {row["name"] for row in con.execute("PRAGMA table_info(line_items)")}
    assert {"manual_only", "manual_source", "internal_reject_count", "last_rejected_at"}.issubset(columns)
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"reject_reasons", "reject_locations", "reject_events", "packing_list_prints", "manual_delivery_entries"}.issubset(tables)
    assert con.execute("SELECT COUNT(*) FROM reject_reasons WHERE active=1").fetchone()[0] >= 5
    assert con.execute("SELECT COUNT(*) FROM reject_locations WHERE active=1").fetchone()[0] >= 8
    con.close()


def test_delivery_store_patch_replaces_blocks_instead_of_duplicating_them():
    patch_path = ROOT / "Apply-v135-OperationsPatch.py"
    spec = importlib.util.spec_from_file_location("v135_patch", patch_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    source = f'''from typing import Any

def row_value(row, key, default=None):
    return default

class Store:
    def insert_line_items(self, con, list_id, items):
        return []

    def method(self, con, list_id, items):
        summary = {{"totalQty": 0}}
        previous_by_id = {{}}
        previous_pools = {{"source": {{}}, "order_item": {{}}, "business": {{}}}}
        if True:
            preserved_rack_items: list[dict[str, Any]] = []
            original_total_qty = 0
            for row in []:
                scanned_qty = 0
                source_key = ""
                order_item_key = ""
                line_key = ""
                record = {{"id": ""}}
                original_total_qty += int(row["qty"] or 0)
                previous_by_id[line_key] = record
                previous_pools["source"].setdefault("", []).append(record)
            con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
            cloned_items = self.insert_line_items(con, list_id, items)
            summary["originalQty"] = original_total_qty
        return summary
'''
    patched = module.patch_delivery_store(source)
    compile(patched, "delivery_store.py", "exec")
    assert patched.count("preserved_rack_items: list[dict[str, Any]] = []") == 1
    assert patched.count('con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))') == 1
    assert patched.count('cloned_items = self.insert_line_items(con, list_id, items)') == 1
    assert module.patch_delivery_store(patched) == patched
