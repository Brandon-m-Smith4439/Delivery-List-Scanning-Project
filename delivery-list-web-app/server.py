#!/usr/bin/env python
"""Local pilot server for the delivery-list scanner web app.

This uses only the Python standard library. It serves the static web app and
stores delivery lists, line items, scan events, and audit history in SQLite.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "delivery-scanner-pilot.db"
SAMPLE_PATH = DATA_DIR / "sample-delivery-list.json"
DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup"]
LIST_PROFILES = [
    ("staging-airport", "Staging - Airport Rd", "Airport Rd", "all"),
    ("outbound-airport", "Outbound - Airport Rd", "Airport Rd", "all"),
    ("inbound-indian-trail", "Inbound - Indian Trail", "Indian Trail", "all"),
    ("customer-pickup", "Customer Pickup", "Customer Pickup", "cpu"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_barcode(value: str) -> str:
    trimmed = str(value or "").replace("*", "").replace("\r", "").replace("\n", "").strip()
    return "".join(ch for ch in trimmed if ch.isalnum()).upper()


def digits_only(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def canonical_barcode(order_no: int, item_no: int) -> str:
    return f"T200{order_no:06d}{item_no:03d}000"


def parse_dimension_number(part: str) -> float:
    pieces = part.strip().split()
    if not pieces:
        return 0.0
    try:
        value = float(pieces[0]) if "/" not in pieces[0] else 0.0
    except ValueError:
        value = 0.0
    frac = pieces[1] if len(pieces) > 1 else pieces[0]
    if "/" in frac:
        top, bottom = frac.split("/", 1)
        try:
            denom = float(bottom)
            if denom:
                value += float(top) / denom
        except ValueError:
            pass
    return value


def suggested_bay(product: str, dimensions: str, route: str) -> str:
    if str(route).upper() == "CPU":
        return "CPU"
    if "MIRROR" in str(product).upper():
        return "Mirror"
    parts = re.findall(r"\d+(?:\s+\d+/\d+|/\d+)?", str(dimensions))
    largest = max([parse_dimension_number(part) for part in parts] or [0])
    if largest >= 96:
        return "Oversize"
    if largest >= 60:
        return "Tall"
    return "Standard"


def is_cpu_item(item: dict) -> bool:
    route = str(item.get("route", "")).strip().upper()
    text = " ".join(
        str(item.get(key, ""))
        for key in ("route", "job", "customer", "product", "processState", "queueState")
    )
    return route == "CPU" or re.search(r"\bCPU\b", text, flags=re.IGNORECASE) is not None


def items_for_profile(profile: str, base_items: list[dict]) -> list[dict]:
    if profile == "cpu":
        return [item for item in base_items if is_cpu_item(item)]
    return list(base_items)


def build_delivery_lists(sample: dict) -> list[tuple[str, str, str, str, list[dict]]]:
    delivery_date = str(sample.get("deliveryDate") or now_iso()[:10])
    base_items = sample.get("items") or []
    return [
        (
            f"{delivery_date}-{suffix}",
            f"{format_display_date(delivery_date)} - {stage}",
            stage,
            scanner,
            items_for_profile(profile, base_items),
        )
        for suffix, stage, scanner, profile in LIST_PROFILES
    ]


def format_display_date(value: str) -> str:
    parts = str(value).split("-")
    if len(parts) == 3:
        return f"{int(parts[1])}/{int(parts[2])}/{int(parts[0])}"
    return str(value)


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def create_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS delivery_lists (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            delivery_date TEXT NOT NULL,
            stage TEXT NOT NULL,
            scanner TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS line_items (
            id TEXT PRIMARY KEY,
            list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
            source_id TEXT NOT NULL,
            barcode TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL,
            scanned_qty INTEGER NOT NULL DEFAULT 0,
            dimensions TEXT NOT NULL DEFAULT '',
            customer TEXT NOT NULL DEFAULT '',
            route TEXT NOT NULL DEFAULT '',
            job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '',
            process_state TEXT NOT NULL DEFAULT '',
            queue_state TEXT NOT NULL DEFAULT '',
            suggested_bay TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS scan_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
            line_item_id TEXT REFERENCES line_items(id) ON DELETE SET NULL,
            barcode TEXT NOT NULL,
            canonical_barcode TEXT NOT NULL DEFAULT '',
            user_name TEXT NOT NULL DEFAULT '',
            station TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            qty_delta INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_scan_events_list_time
            ON scan_events(list_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS stations (
            name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        );
        """
    )
    con.commit()


def clone_item_for_list(item: dict, list_id: str, index: int) -> dict:
    order_no = str(item["order"])
    item_no = str(item["item"]).zfill(3)
    route = str(item.get("route", ""))
    product = str(item.get("product", ""))
    dimensions = str(item.get("dimensions", ""))
    return {
        "id": f"{list_id}-{index:04d}-{order_no}-{item_no}",
        "source_id": str(item.get("id") or f"{order_no}-{item_no}"),
        "barcode": canonical_barcode(int(order_no), int(item_no)),
        "order_no": order_no,
        "item_no": item_no,
        "qty": int(item.get("qty") or 0),
        "dimensions": dimensions,
        "customer": str(item.get("customer", "")),
        "route": route,
        "job": str(item.get("job", "")),
        "product": product,
        "process_state": str(item.get("processState", "")),
        "queue_state": str(item.get("queueState", "")),
        "suggested_bay": suggested_bay(product, dimensions, route),
    }


def insert_line_items(con: sqlite3.Connection, list_id: str, items: list[dict]) -> None:
    for index, item in enumerate(items, start=1):
        cloned = clone_item_for_list(item, list_id, index)
        con.execute(
            """
            INSERT INTO line_items (
                id, list_id, source_id, barcode, order_no, item_no, qty,
                dimensions, customer, route, job, product, process_state,
                queue_state, suggested_bay
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cloned["id"],
                list_id,
                cloned["source_id"],
                cloned["barcode"],
                cloned["order_no"],
                cloned["item_no"],
                cloned["qty"],
                cloned["dimensions"],
                cloned["customer"],
                cloned["route"],
                cloned["job"],
                cloned["product"],
                cloned["process_state"],
                cloned["queue_state"],
                cloned["suggested_bay"],
            ),
        )


def upsert_delivery_list(
    con: sqlite3.Connection,
    list_id: str,
    label: str,
    delivery_date: str,
    stage: str,
    scanner: str,
    items: list[dict],
    replace_items: bool,
) -> None:
    existing = con.execute("SELECT revision, created_at FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
    created = existing["created_at"] if existing else now_iso()
    revision = int(existing["revision"]) + 1 if existing and replace_items else int(existing["revision"]) if existing else 1
    con.execute(
        """
        INSERT INTO delivery_lists (id, label, delivery_date, stage, scanner, status, revision, created_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            label = excluded.label,
            delivery_date = excluded.delivery_date,
            stage = excluded.stage,
            scanner = excluded.scanner,
            revision = excluded.revision
        """,
        (list_id, label, delivery_date, stage, scanner, revision, created),
    )
    if replace_items:
        con.execute("DELETE FROM scan_events WHERE list_id = ?", (list_id,))
        con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
        insert_line_items(con, list_id, items)


def seed_demo_data(con: sqlite3.Connection) -> None:
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    for list_id, label, stage, scanner, items in build_delivery_lists(sample):
        row = con.execute("SELECT COUNT(*) AS count FROM line_items WHERE list_id = ?", (list_id,)).fetchone()
        upsert_delivery_list(
            con,
            list_id,
            label,
            str(sample["deliveryDate"]),
            stage,
            scanner,
            items,
            replace_items=row["count"] != len(items),
        )
    seed_stations(con)
    con.commit()


def seed_stations(con: sqlite3.Connection) -> None:
    created = now_iso()
    for station in DEFAULT_STATIONS:
        con.execute(
            "INSERT OR IGNORE INTO stations (name, created_at) VALUES (?, ?)",
            (station, created),
        )


def init_db() -> None:
    def remove_db_files() -> None:
        for path in (DB_PATH, Path(str(DB_PATH) + "-wal"), Path(str(DB_PATH) + "-shm")):
            if path.exists():
                path.unlink()

    rebuild = False
    if DB_PATH.exists():
        try:
            with sqlite3.connect(DB_PATH) as con:
                row = con.execute("SELECT COUNT(*) FROM line_items").fetchone()
                if row and row[0] < 100:
                    rebuild = True
        except sqlite3.Error:
            rebuild = True
    if rebuild:
        remove_db_files()
    with connect() as con:
        create_schema(con)
        seed_demo_data(con)


def item_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "barcode": row["barcode"],
        "order": row["order_no"],
        "item": row["item_no"],
        "qty": row["qty"],
        "scanned": row["scanned_qty"],
        "dimensions": row["dimensions"],
        "customer": row["customer"],
        "route": row["route"],
        "job": row["job"],
        "product": row["product"],
        "processState": row["process_state"],
        "queueState": row["queue_state"],
        "suggestedBay": row["suggested_bay"],
    }


def event_from_row(row: sqlite3.Row) -> dict:
    item = None
    if row["line_item_id"]:
        item = {
            "id": row["line_item_id"],
            "order": row["order_no"],
            "item": row["item_no"],
            "qty": row["qty"],
            "scanned": row["scanned_qty"],
            "dimensions": row["dimensions"],
            "customer": row["customer"],
            "route": row["route"],
            "job": row["job"],
            "product": row["product"],
            "suggestedBay": row["suggested_bay"],
        }
    return {
        "ok": row["event_type"] in {"scan", "undo"},
        "barcode": row["canonical_barcode"] or row["barcode"],
        "raw": row["barcode"],
        "item": item,
        "message": row["message"],
        "reason": row["reason"],
        "time": row["created_at"],
        "user": row["user_name"],
        "station": row["station"],
        "eventType": row["event_type"],
    }


def list_meta(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "label": row["label"],
        "deliveryDate": row["delivery_date"],
        "stage": row["stage"],
        "scanner": row["scanner"],
        "status": row["status"],
        "revision": row["revision"],
    }


def get_lists(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        """
        SELECT dl.*,
               COALESCE(SUM(li.qty), 0) AS total_qty,
               COALESCE(SUM(li.scanned_qty), 0) AS scanned_qty,
               COUNT(li.id) AS item_count
        FROM delivery_lists dl
        LEFT JOIN line_items li ON li.list_id = dl.id
        GROUP BY dl.id
        ORDER BY dl.delivery_date DESC, dl.label
        """
    ).fetchall()
    result = []
    for row in rows:
        meta = list_meta(row)
        meta.update(
            {
                "totalQty": row["total_qty"],
                "scannedQty": row["scanned_qty"],
                "itemCount": row["item_count"],
            }
        )
        result.append(meta)
    return result


def get_stations(con: sqlite3.Connection) -> list[str]:
    rows = con.execute("SELECT name FROM stations ORDER BY name").fetchall()
    return [str(row["name"]) for row in rows]


def add_station(name: str) -> dict:
    clean_name = " ".join(str(name or "").split())[:80]
    if not clean_name:
        raise ValueError("Station name is required")
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT OR IGNORE INTO stations (name, created_at) VALUES (?, ?)",
            (clean_name, now_iso()),
        )
        con.commit()
        return {"stations": get_stations(con), "station": clean_name}


def get_items(con: sqlite3.Connection, list_id: str) -> list[dict]:
    rows = con.execute(
        "SELECT * FROM line_items WHERE list_id = ? ORDER BY CAST(order_no AS INTEGER), CAST(item_no AS INTEGER)",
        (list_id,),
    ).fetchall()
    return [item_from_row(row) for row in rows]


def get_events(con: sqlite3.Connection, list_id: str, only_errors: bool = False) -> list[dict]:
    condition = "AND se.event_type = 'error'" if only_errors else ""
    rows = con.execute(
        f"""
        SELECT se.*, li.order_no, li.item_no, li.qty, li.scanned_qty, li.dimensions,
               li.customer, li.route, li.job, li.product, li.suggested_bay
        FROM scan_events se
        LEFT JOIN line_items li ON li.id = se.line_item_id
        WHERE se.list_id = ? {condition}
        ORDER BY se.id DESC
        LIMIT 30
        """,
        (list_id,),
    ).fetchall()
    return [event_from_row(row) for row in rows]


def get_payload(con: sqlite3.Connection, list_id: str, last_scan: dict | None = None) -> dict:
    meta_row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
    if not meta_row:
        raise KeyError("Delivery list not found")
    items = get_items(con, list_id)
    return {
        "meta": list_meta(meta_row),
        "items": items,
        "recent": get_events(con, list_id),
        "errors": get_events(con, list_id, only_errors=True),
        "lastScan": last_scan,
    }


def validate_import_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Import payload must be a JSON object")
    delivery_date = str(payload.get("deliveryDate") or "").strip()
    items = payload.get("items")
    if not delivery_date or not isinstance(items, list) or not items:
        raise ValueError("Import JSON must include deliveryDate and a non-empty items array")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each imported item must be an object")
        for key in ("order", "item", "qty"):
            if str(item.get(key, "")).strip() == "":
                raise ValueError(f"Imported items must include {key}")
    return payload


def import_delivery_lists(data: dict) -> dict:
    payload = validate_import_payload(data.get("payload") or data)
    user = request_user_name(data)
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        definitions = build_delivery_lists(payload)
        for list_id, label, stage, scanner, items in definitions:
            upsert_delivery_list(
                con,
                list_id,
                label,
                str(payload["deliveryDate"]),
                stage,
                scanner,
                items,
                replace_items=True,
            )
            insert_event(con, list_id, None, "IMPORT", "", user, scanner, "import", "Delivery list imported")
        con.commit()
        return {"lists": get_lists(con), "activeListId": definitions[0][0], "importedCount": len(definitions)}


def find_unique_suffix_item(rows: list[sqlite3.Row], suffix: str, item_no: int) -> sqlite3.Row | None:
    matches = []
    for row in rows:
        if int(row["item_no"]) == item_no and f"{int(row['order_no']):06d}".endswith(suffix):
            matches.append(row)
    return matches[0] if len(matches) == 1 else None


def recover_scan(raw_scan: str, rows: list[sqlite3.Row]) -> tuple[sqlite3.Row | None, str, str]:
    clean_text = clean_barcode(raw_scan)
    by_order_item: dict[tuple[int, int], list[sqlite3.Row]] = {}
    for row in rows:
        by_order_item.setdefault((int(row["order_no"]), int(row["item_no"])), []).append(row)

    if re.fullmatch(r"T200\d{12}", clean_text):
        order_no = int(clean_text[4:10])
        item_no = int(clean_text[10:13])
        matches = by_order_item.get((order_no, item_no), [])
        if len(matches) == 1:
            return matches[0], clean_text, "Exact label"
        if len(matches) > 1:
            return None, clean_text, "Ambiguous delivery-list match"

    numbers = digits_only(clean_text)
    for start in range(0, max(0, len(numbers) - 11)):
        window = numbers[start : start + 12]
        order_no = int(window[:6])
        item_no = int(window[6:9])
        matches = by_order_item.get((order_no, item_no), [])
        if len(matches) == 1:
            return matches[0], canonical_barcode(order_no, item_no), "Recovered order/item"
        if len(matches) > 1:
            return None, canonical_barcode(order_no, item_no), "Ambiguous delivery-list match"

    for start in range(0, max(0, len(numbers) - 8)):
        window = numbers[start : start + 9]
        suffix = window[:3]
        item_no = int(window[3:6])
        row = find_unique_suffix_item(rows, suffix, item_no)
        if row:
            return row, canonical_barcode(int(row["order_no"]), item_no), "Recovered suffix/item"

    return None, clean_text, "No unique delivery-list match"


def insert_event(
    con: sqlite3.Connection,
    list_id: str,
    line_item_id: str | None,
    barcode: str,
    canonical: str,
    user: str,
    station: str,
    event_type: str,
    message: str,
    reason: str = "",
    qty_delta: int = 0,
) -> dict:
    created = now_iso()
    cur = con.execute(
        """
        INSERT INTO scan_events (
            list_id, line_item_id, barcode, canonical_barcode, user_name,
            station, event_type, message, reason, qty_delta, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (list_id, line_item_id, barcode, canonical, user, station, event_type, message, reason, qty_delta, created),
    )
    row = con.execute(
        """
        SELECT se.*, li.order_no, li.item_no, li.qty, li.scanned_qty, li.dimensions,
               li.customer, li.route, li.job, li.product, li.suggested_bay
        FROM scan_events se
        LEFT JOIN line_items li ON li.id = se.line_item_id
        WHERE se.id = ?
        """,
        (cur.lastrowid,),
    ).fetchone()
    return event_from_row(row)


def request_user_name(data: dict) -> str:
    return str(data.get("user") or data.get("operator") or "Scanner").strip()[:80]


def request_station(data: dict) -> str:
    return str(data.get("station") or "").strip()[:80]


def process_scan(data: dict) -> dict:
    list_id = str(data.get("listId") or "")
    barcode = str(data.get("barcode") or "")
    user = request_user_name(data)
    station = request_station(data)
    if not list_id or not barcode.strip():
        raise ValueError("listId and barcode are required")

    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall()
        row, canonical, reason = recover_scan(barcode, rows)
        if row is None:
            last = insert_event(con, list_id, None, barcode, canonical, user, station, "error", "BAD SCAN format", reason)
            con.commit()
            return get_payload(con, list_id, last)

        if row["scanned_qty"] >= row["qty"]:
            last = insert_event(
                con,
                list_id,
                row["id"],
                barcode,
                canonical,
                user,
                station,
                "duplicate",
                "Item already complete",
                "Quantity already scanned",
            )
            con.commit()
            return get_payload(con, list_id, last)

        con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
        last = insert_event(con, list_id, row["id"], barcode, canonical, user, station, "scan", reason, "", 1)
        con.commit()
        return get_payload(con, list_id, last)


def reset_list(list_id: str, user: str, station: str) -> dict:
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE line_items SET scanned_qty = 0 WHERE list_id = ?", (list_id,))
        con.execute("DELETE FROM scan_events WHERE list_id = ?", (list_id,))
        last = insert_event(con, list_id, None, "RESET", "", user, station, "reset", "Scan state reset")
        con.commit()
        return get_payload(con, list_id, last)


def undo_last_scan(list_id: str, user: str, station: str) -> dict:
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            """
            SELECT * FROM scan_events
            WHERE list_id = ? AND event_type = 'scan' AND line_item_id IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (list_id,),
        ).fetchone()
        if not row:
            last = insert_event(con, list_id, None, "UNDO", "", user, station, "error", "Nothing to undo")
            con.commit()
            return get_payload(con, list_id, last)

        con.execute(
            "UPDATE line_items SET scanned_qty = MAX(scanned_qty - 1, 0) WHERE id = ?",
            (row["line_item_id"],),
        )
        last = insert_event(
            con,
            list_id,
            row["line_item_id"],
            row["barcode"],
            row["canonical_barcode"],
            user,
            station,
            "undo",
            "Last scan undone",
            "",
            -1,
        )
        con.commit()
        return get_payload(con, list_id, last)


def export_csv(list_id: str) -> str:
    with connect() as con:
        rows = get_items(con, list_id)
    output = StringIO()
    fieldnames = [
        "barcode",
        "order",
        "item",
        "qty",
        "scanned",
        "remaining",
        "dimensions",
        "customer",
        "route",
        "job",
        "product",
        "suggestedBay",
    ]
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "barcode": row["barcode"],
            "order": row["order"],
            "item": row["item"],
            "qty": row["qty"],
            "scanned": row["scanned"],
            "remaining": max(int(row["qty"]) - int(row["scanned"]), 0),
            "dimensions": row["dimensions"],
            "customer": row["customer"],
            "route": row["route"],
            "job": row["job"],
            "product": row["product"],
            "suggestedBay": row["suggestedBay"],
        })
    return output.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "mode": "sqlite", "database": str(DB_PATH)})
            return
        if parsed.path == "/api/delivery-lists":
            with connect() as con:
                self.send_json({"lists": get_lists(con)})
            return
        if parsed.path == "/api/stations":
            with connect() as con:
                self.send_json({"stations": get_stations(con)})
            return
        if parsed.path.startswith("/api/delivery-lists/"):
            list_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                with connect() as con:
                    self.send_json(get_payload(con, list_id))
            except KeyError:
                self.send_json({"error": "Delivery list not found"}, HTTPStatus.NOT_FOUND)
            return
        if parsed.path == "/api/export.csv":
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            body = export_csv(list_id).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            if parsed.path == "/api/scans":
                self.send_json(process_scan(data))
                return
            if parsed.path == "/api/reset":
                self.send_json(reset_list(str(data.get("listId") or ""), request_user_name(data), request_station(data)))
                return
            if parsed.path == "/api/undo":
                self.send_json(undo_last_scan(str(data.get("listId") or ""), request_user_name(data), request_station(data)))
                return
            if parsed.path == "/api/stations":
                self.send_json(add_station(str(data.get("name") or "")))
                return
            if parsed.path == "/api/import":
                self.send_json(import_delivery_lists(data))
                return
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> int:
    init_db()
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Delivery List Scanner running at http://{host}:{port}/")
    print(f"SQLite database: {DB_PATH}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
