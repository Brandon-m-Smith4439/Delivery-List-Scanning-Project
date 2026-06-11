"""Data-access layer for the delivery-list scanner.

The web/API layer should call these store methods instead of issuing SQL
directly. SQLite is the current implementation; SQL Server/PostgreSQL can be
added later by implementing the same method contract.
"""

from __future__ import annotations

import csv
import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from scanner_config import AppConfig


DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup"]
SESSION_COOKIE_NAME = "dls_session"
PASSWORD_ITERATIONS = 260000
SESSION_HOURS = 12
PERMISSIONS = [
    "scan",
    "view_lists",
    "view_stations",
    "view_own_scans",
    "undo_scan",
    "reset_lists",
    "resolve_exceptions",
    "manual_adjust",
    "view_exceptions",
    "import_delivery_lists",
    "preview_import",
    "manage_users",
    "manage_roles",
    "manage_stations",
    "remove_stations",
    "deactivate_users",
    "edit_delivery_lists",
    "export_reports",
    "view_admin",
    "view_active_sessions",
    "global_search",
    "view_reports",
    "view_indian_trail",
    "indian_trail_receive",
    "view_bays",
    "assign_bay",
    "move_bay",
    "clear_bay",
    "mark_sdi",
    "remove_sdi",
    "bay_check",
    "indian_trail_reports",
]
ROLE_PERMISSIONS = {
    "Operator": ["scan", "view_lists", "view_stations", "view_own_scans", "export_reports", "global_search"],
    "Supervisor": [
        "scan",
        "view_lists",
        "view_stations",
        "view_own_scans",
        "undo_scan",
        "resolve_exceptions",
        "manual_adjust",
        "view_exceptions",
        "export_reports",
        "global_search",
        "view_reports",
        "view_active_sessions",
    ],
    "Admin": PERMISSIONS,
    "Indian Trail Operator": [
        "view_lists",
        "view_stations",
        "view_indian_trail",
        "indian_trail_receive",
        "view_bays",
        "global_search",
        "export_reports",
    ],
    "Indian Trail Lead": [
        "view_lists",
        "view_stations",
        "view_indian_trail",
        "indian_trail_receive",
        "view_bays",
        "global_search",
        "export_reports",
        "undo_scan",
        "resolve_exceptions",
        "view_exceptions",
        "assign_bay",
        "move_bay",
        "clear_bay",
        "mark_sdi",
        "remove_sdi",
        "bay_check",
    ],
    "Indian Trail Manager": [
        "view_lists",
        "view_stations",
        "view_indian_trail",
        "indian_trail_receive",
        "view_bays",
        "global_search",
        "export_reports",
        "undo_scan",
        "resolve_exceptions",
        "view_exceptions",
        "assign_bay",
        "move_bay",
        "clear_bay",
        "mark_sdi",
        "remove_sdi",
        "bay_check",
        "indian_trail_reports",
        "view_reports",
        "view_active_sessions",
    ],
}
ROLE_STAGE_ACCESS = {
    "Admin": ["*"],
    "Supervisor": ["*"],
    "Operator": ["Airport Rd", "Customer Pickup"],
    "Indian Trail Operator": ["Indian Trail"],
    "Indian Trail Lead": ["Indian Trail"],
    "Indian Trail Manager": ["Indian Trail"],
}
DUMMY_USERS = [
    ("operator", "Operator", "Operator123!", ["Operator"]),
    ("supervisor", "Supervisor", "Supervisor123!", ["Supervisor"]),
    ("itoperator", "Indian Trail Operator", "Trail123!", ["Indian Trail Operator"]),
    ("itlead", "Indian Trail Lead", "TrailLead123!", ["Indian Trail Lead"]),
    ("itmanager", "Indian Trail Manager", "TrailManager123!", ["Indian Trail Manager"]),
]
LIST_PROFILES = [
    ("staging-airport", "Staging - Airport Rd", "Airport Rd", "all"),
    ("outbound-airport", "Outbound - Airport Rd", "Airport Rd", "all"),
    ("inbound-indian-trail", "Inbound - Indian Trail", "Indian Trail", "all"),
    ("customer-pickup", "Customer Pickup", "Customer Pickup", "cpu"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_text.encode("ascii"))
        expected = base64.b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def session_token_hash(token: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def stage_access_for_roles(roles: list[str]) -> list[str]:
    access: list[str] = []
    for role in roles:
        for stage in ROLE_STAGE_ACCESS.get(role, []):
            if stage == "*":
                return ["*"]
            if stage not in access:
                access.append(stage)
    return access


def user_can_access_stage(user: dict[str, Any] | None, stage: str, scanner: str = "") -> bool:
    if not user:
        return False
    allowed = user.get("stageAccess") or stage_access_for_roles(user.get("roles") or [])
    if "*" in allowed:
        return True
    haystack = f"{stage} {scanner}".lower()
    return any(str(value).lower() in haystack for value in allowed)


def clean_barcode(value: str) -> str:
    trimmed = str(value or "").replace("*", "").replace("\r", "").replace("\n", "").strip()
    return "".join(ch for ch in trimmed if ch.isalnum()).upper()


def digits_only(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def canonical_barcode(order_no: int | str, item_no: int | str) -> str:
    return f"T200{int(order_no):06d}{int(item_no):03d}000"


def format_display_date(value: str) -> str:
    parts = str(value).split("-")
    if len(parts) == 3:
        return f"{int(parts[1])}/{int(parts[2])}/{int(parts[0])}"
    return str(value)


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


def is_cpu_item(item: dict[str, Any]) -> bool:
    route = str(item.get("route", "")).strip().upper()
    text = " ".join(str(item.get(key, "")) for key in ("route", "job", "customer", "product", "processState", "queueState"))
    return route == "CPU" or re.search(r"\bCPU\b", text, flags=re.IGNORECASE) is not None


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


def items_for_profile(profile: str, base_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if profile == "cpu":
        return [item for item in base_items if is_cpu_item(item)]
    return list(base_items)


def build_delivery_lists(sample: dict[str, Any]) -> list[tuple[str, str, str, str, list[dict[str, Any]]]]:
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


def item_from_row(row: sqlite3.Row) -> dict[str, Any]:
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


def event_from_row(row: sqlite3.Row) -> dict[str, Any]:
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


def list_meta(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "label": row["label"],
        "deliveryDate": row["delivery_date"],
        "stage": row["stage"],
        "scanner": row["scanner"],
        "status": row["status"],
        "revision": row["revision"],
    }


def request_user_name(data: dict[str, Any]) -> str:
    return str(data.get("user") or data.get("operator") or "Scanner").strip()[:80]


def request_station(data: dict[str, Any]) -> str:
    return str(data.get("station") or "").strip()[:80]


class BaseDeliveryStore:
    database_type = "base"

    def initialize(self) -> None:
        raise NotImplementedError

    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_delivery_lists(self, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_delivery_list(self, list_id: str, last_scan: dict[str, Any] | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def get_line_items(self, list_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def record_scan(self, scan_request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def undo_last_scan(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        raise NotImplementedError

    def reset_stage(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        raise NotImplementedError

    def import_delivery_list(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_scan_events(self, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_exceptions(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_stations(self) -> list[str]:
        raise NotImplementedError

    def add_station(self, name: str) -> dict[str, Any]:
        raise NotImplementedError

    def remove_station(self, name: str) -> dict[str, Any]:
        raise NotImplementedError

    def export_csv(self, list_id: str) -> str:
        raise NotImplementedError

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        raise NotImplementedError

    def get_user_by_session(self, token: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def delete_session(self, token: str) -> None:
        raise NotImplementedError

    def create_user(self, data: dict[str, Any], created_by: str = "system") -> dict[str, Any]:
        raise NotImplementedError

    def list_users(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def deactivate_user(self, username: str, deactivated_by: str = "system") -> dict[str, Any]:
        raise NotImplementedError

    def list_active_sessions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_permissions(self) -> list[str]:
        raise NotImplementedError

    def preview_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def admin_summary(self) -> dict[str, Any]:
        raise NotImplementedError

    def resolve_exception(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def global_search(self, query: str, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def update_line_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def reports_summary(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_bays(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_bay_layout(self) -> dict[str, Any]:
        raise NotImplementedError

    def indian_trail_summary(self) -> dict[str, Any]:
        raise NotImplementedError

    def receive_indian_trail_scan(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def assign_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def move_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def clear_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def mark_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def remove_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def bay_check(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError


class SQLiteDeliveryStore(BaseDeliveryStore):
    database_type = "sqlite"

    def __init__(self, config: AppConfig):
        self.config = config
        self.database_path = Path(config.database_path)
        self.sample_path = Path(config.sample_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(exist_ok=True)
        con = sqlite3.connect(self.database_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        return con

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": self.database_type,
            "database": str(self.database_path),
            "environment": self.config.environment,
            "authMode": self.config.auth_mode,
        }

    def initialize(self) -> None:
        with self.connect() as con:
            self.create_schema(con)
            self.seed_demo_data(con)
            self.seed_security_data(con)
            self.seed_bays(con)

    def create_schema(self, con: sqlite3.Connection) -> None:
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

            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_date TEXT NOT NULL,
                source_name TEXT NOT NULL DEFAULT '',
                row_count INTEGER NOT NULL DEFAULT 0,
                total_qty INTEGER NOT NULL DEFAULT 0,
                cpu_count INTEGER NOT NULL DEFAULT 0,
                mirror_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'published',
                imported_by TEXT NOT NULL DEFAULT '',
                imported_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id TEXT NOT NULL,
                scan_event_id INTEGER REFERENCES scan_events(id) ON DELETE SET NULL,
                exception_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                resolved_by TEXT NOT NULL DEFAULT '',
                resolved_at TEXT NOT NULL DEFAULT '',
                resolution_comment TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_name TEXT NOT NULL DEFAULT '',
                station TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS permissions (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_name TEXT NOT NULL REFERENCES permissions(name) ON DELETE CASCADE,
                PRIMARY KEY (role_id, permission_name)
            );

            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                user_agent TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS bays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bay_code TEXT NOT NULL UNIQUE,
                area TEXT NOT NULL DEFAULT '',
                bay_type TEXT NOT NULL DEFAULT 'Standard',
                capacity_qty INTEGER NOT NULL DEFAULT 0,
                max_width REAL NOT NULL DEFAULT 0,
                max_height REAL NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bay_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_list_id TEXT NOT NULL,
                line_item_id TEXT NOT NULL,
                bay_id INTEGER REFERENCES bays(id) ON DELETE SET NULL,
                assigned_qty INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Assigned',
                assigned_by TEXT NOT NULL DEFAULT '',
                assigned_at TEXT NOT NULL,
                cleared_by TEXT NOT NULL DEFAULT '',
                cleared_at TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS bay_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bay_id INTEGER REFERENCES bays(id) ON DELETE SET NULL,
                line_item_id TEXT NOT NULL DEFAULT '',
                event_type TEXT NOT NULL,
                old_bay_id INTEGER,
                new_bay_id INTEGER,
                reason TEXT NOT NULL DEFAULT '',
                user_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        self.ensure_column(con, "bays", "display_name", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "map_section", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "bay_category", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "source_cell", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "layout_row", "INTEGER")
        self.ensure_column(con, "bays", "layout_col", "INTEGER")
        self.ensure_column(con, "bays", "layout_cell", "TEXT NOT NULL DEFAULT ''")
        con.commit()

    def ensure_column(self, con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def clone_item_for_list(self, item: dict[str, Any], list_id: str, index: int) -> dict[str, Any]:
        order_no = str(item["order"])
        item_no = str(item["item"]).zfill(3)
        route = str(item.get("route", ""))
        product = str(item.get("product", ""))
        dimensions = str(item.get("dimensions", ""))
        return {
            "id": f"{list_id}-{index:04d}-{order_no}-{item_no}",
            "source_id": str(item.get("id") or f"{order_no}-{item_no}"),
            "barcode": canonical_barcode(order_no, item_no),
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

    def insert_line_items(self, con: sqlite3.Connection, list_id: str, items: list[dict[str, Any]]) -> None:
        for index, item in enumerate(items, start=1):
            cloned = self.clone_item_for_list(item, list_id, index)
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
        self,
        con: sqlite3.Connection,
        list_id: str,
        label: str,
        delivery_date: str,
        stage: str,
        scanner: str,
        items: list[dict[str, Any]],
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
            con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
            self.insert_line_items(con, list_id, items)

    def seed_demo_data(self, con: sqlite3.Connection) -> None:
        if not self.sample_path.exists():
            return
        sample = json.loads(self.sample_path.read_text(encoding="utf-8"))
        for list_id, label, stage, scanner, items in build_delivery_lists(sample):
            row = con.execute("SELECT COUNT(*) AS count FROM line_items WHERE list_id = ?", (list_id,)).fetchone()
            self.upsert_delivery_list(
                con,
                list_id,
                label,
                str(sample["deliveryDate"]),
                stage,
                scanner,
                items,
                replace_items=row["count"] != len(items),
            )
        self.seed_stations(con)
        con.commit()

    def seed_stations(self, con: sqlite3.Connection) -> None:
        created = now_iso()
        for station in DEFAULT_STATIONS:
            con.execute("INSERT OR IGNORE INTO stations (name, created_at) VALUES (?, ?)", (station, created))

    def seed_security_data(self, con: sqlite3.Connection) -> None:
        for permission in PERMISSIONS:
            con.execute(
                "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
                (permission, permission.replace("_", " ").title()),
            )

        for role_name, permissions in ROLE_PERMISSIONS.items():
            con.execute(
                "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
                (role_name, f"{role_name} role"),
            )
            role_id = con.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()["id"]
            for permission in permissions:
                con.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_name) VALUES (?, ?)",
                    (role_id, permission),
                )

        row = con.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if row["count"] == 0:
            created = now_iso()
            cur = con.execute(
                """
                INSERT INTO users (username, display_name, password_hash, active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    self.config.default_admin_username,
                    "Default Admin",
                    hash_password(self.config.default_admin_password),
                    created,
                ),
            )
            admin_role = con.execute("SELECT id FROM roles WHERE name = 'Admin'").fetchone()["id"]
            con.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (cur.lastrowid, admin_role))
            self.insert_audit(
                con,
                "user",
                self.config.default_admin_username,
                "bootstrap_admin",
                "system",
                "",
                "Initial local admin created",
            )

        for username, display_name, password, roles in DUMMY_USERS:
            self.seed_user_if_missing(con, username, display_name, password, roles)

        con.commit()

    def seed_user_if_missing(self, con: sqlite3.Connection, username: str, display_name: str, password: str, roles: list[str]) -> None:
        existing = self.get_user_by_username(con, username)
        if existing:
            return
        cur = con.execute(
            """
            INSERT INTO users (username, display_name, password_hash, active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (username, display_name, hash_password(password), now_iso()),
        )
        for role_name in roles:
            role = con.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            if role:
                con.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", (cur.lastrowid, role["id"]))
        self.insert_audit(con, "user", username, "seed_demo_user", "system", "", "", {"roles": roles})

    def seed_bays(self, con: sqlite3.Connection) -> None:
        layout = self.get_bay_layout()
        if layout.get("bays"):
            self.seed_layout_bays(con, layout["bays"])
            con.commit()
            return

        bay_defs = []
        sort_order = 1
        for area, bay_type, prefix, count, capacity in [
            ("Standard", "Standard", "STD", 12, 8),
            ("Tall", "Tall", "TALL", 8, 6),
            ("Oversize", "Oversize", "OVER", 6, 4),
            ("Mirror", "Mirror", "MIR", 8, 8),
            ("CPU", "CPU", "CPU", 4, 6),
            ("SDI", "SDI", "SDI", 4, 4),
        ]:
            for index in range(1, count + 1):
                bay_defs.append((f"{prefix}-{index:02d}", area, bay_type, capacity, sort_order))
                sort_order += 1
        for bay_code, area, bay_type, capacity, order in bay_defs:
            con.execute(
                """
                INSERT OR IGNORE INTO bays (bay_code, area, bay_type, capacity_qty, sort_order, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (bay_code, area, bay_type, capacity, order),
            )
        con.commit()

    def seed_layout_bays(self, con: sqlite3.Connection, bays: list[dict[str, Any]]) -> None:
        con.execute(
            """
            UPDATE bays
            SET active = 0
            WHERE bay_code LIKE 'STD-%' OR bay_code LIKE 'TALL-%' OR bay_code LIKE 'OVER-%'
               OR bay_code LIKE 'MIR-%' OR bay_code LIKE 'CPU-%' OR bay_code LIKE 'SDI-%'
            """
        )
        for index, bay in enumerate(bays, start=1):
            bay_code = str(bay.get("bayCode") or "").strip()
            if not bay_code:
                continue
            display_name = str(bay.get("displayName") or bay_code).strip()
            bay_type = str(bay.get("bayType") or "Other").strip()
            active = 1 if bay.get("autoAssignable") and str(bay.get("sourceStatus") or "") == "Available" else 0
            capacity = 1 if active else 0
            sort_order = int(bay.get("assignmentPriority") or index)
            con.execute(
                """
                INSERT INTO bays (
                    bay_code, display_name, area, bay_type, capacity_qty, sort_order,
                    active, map_section, bay_category, source_cell, layout_row,
                    layout_col, layout_cell
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bay_code) DO UPDATE SET
                    display_name = excluded.display_name,
                    area = excluded.area,
                    bay_type = excluded.bay_type,
                    capacity_qty = excluded.capacity_qty,
                    sort_order = excluded.sort_order,
                    active = excluded.active,
                    map_section = excluded.map_section,
                    bay_category = excluded.bay_category,
                    source_cell = excluded.source_cell,
                    layout_row = excluded.layout_row,
                    layout_col = excluded.layout_col,
                    layout_cell = excluded.layout_cell
                """,
                (
                    bay_code,
                    display_name,
                    str(bay.get("mapSection") or ""),
                    bay_type,
                    capacity,
                    sort_order,
                    active,
                    str(bay.get("mapSection") or ""),
                    str(bay.get("bayCategory") or ""),
                    str(bay.get("sourceCell") or ""),
                    bay.get("layoutRow"),
                    bay.get("layoutCol"),
                    str(bay.get("layoutCell") or ""),
                ),
            )

    def get_delivery_lists(self, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.connect() as con:
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
            meta.update({"totalQty": row["total_qty"], "scannedQty": row["scanned_qty"], "itemCount": row["item_count"]})
            if user is None or user_can_access_stage(user, meta["stage"], meta["scanner"]):
                result.append(meta)
        return result

    def get_line_items(self, list_id: str) -> list[dict[str, Any]]:
        with self.connect() as con:
            return self._get_line_items(con, list_id)

    def _get_line_items(self, con: sqlite3.Connection, list_id: str) -> list[dict[str, Any]]:
        rows = con.execute(
            "SELECT * FROM line_items WHERE list_id = ? ORDER BY CAST(order_no AS INTEGER), CAST(item_no AS INTEGER), id",
            (list_id,),
        ).fetchall()
        return [item_from_row(row) for row in rows]

    def get_scan_events(self, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
        with self.connect() as con:
            return self._get_scan_events(con, list_id, only_errors=only_errors)

    def _get_scan_events(self, con: sqlite3.Connection, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
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

    def get_delivery_list(self, list_id: str, last_scan: dict[str, Any] | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.connect() as con:
            return self._get_payload(con, list_id, last_scan=last_scan, user=user)

    def _get_payload(self, con: sqlite3.Connection, list_id: str, last_scan: dict[str, Any] | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        meta_row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
        if not meta_row:
            raise KeyError("Delivery list not found")
        meta = list_meta(meta_row)
        if user is not None and not user_can_access_stage(user, meta["stage"], meta["scanner"]):
            raise PermissionError("You do not have access to this delivery-list stage")
        return {
            "meta": meta,
            "items": self._get_line_items(con, list_id),
            "recent": self._get_scan_events(con, list_id),
            "errors": self._get_scan_events(con, list_id, only_errors=True),
            "lastScan": last_scan,
        }

    def user_can_access_list(self, user: dict[str, Any], list_id: str) -> bool:
        with self.connect() as con:
            row = con.execute("SELECT stage, scanner FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            if not row:
                return False
            return user_can_access_stage(user, row["stage"], row["scanner"])

    def get_stations(self) -> list[str]:
        with self.connect() as con:
            rows = con.execute("SELECT name FROM stations ORDER BY name").fetchall()
            return [str(row["name"]) for row in rows]

    def add_station(self, name: str) -> dict[str, Any]:
        clean_name = " ".join(str(name or "").split())[:80]
        if not clean_name:
            raise ValueError("Station name is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT OR IGNORE INTO stations (name, created_at) VALUES (?, ?)", (clean_name, now_iso()))
            con.commit()
        return {"stations": self.get_stations(), "station": clean_name}

    def remove_station(self, name: str) -> dict[str, Any]:
        clean_name = " ".join(str(name or "").split())[:80]
        if not clean_name:
            raise ValueError("Station name is required")
        if clean_name in DEFAULT_STATIONS:
            raise ValueError("Default stations cannot be removed")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM stations WHERE name = ?", (clean_name,))
            con.commit()
        return {"stations": self.get_stations(), "station": clean_name}

    def get_permissions(self) -> list[str]:
        return list(PERMISSIONS)

    def user_from_row(self, con: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        role_rows = con.execute(
            """
            SELECT r.name
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
            ORDER BY r.name
            """,
            (row["id"],),
        ).fetchall()
        roles = [role["name"] for role in role_rows]
        permission_rows = con.execute(
            """
            SELECT DISTINCT rp.permission_name
            FROM role_permissions rp
            JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ?
            ORDER BY rp.permission_name
            """,
            (row["id"],),
        ).fetchall()
        return {
            "id": row["id"],
            "username": row["username"],
            "displayName": row["display_name"] or row["username"],
            "active": bool(row["active"]),
            "roles": roles,
            "permissions": [permission["permission_name"] for permission in permission_rows],
            "stageAccess": stage_access_for_roles(roles),
        }

    def get_user_by_username(self, con: sqlite3.Connection, username: str) -> sqlite3.Row | None:
        return con.execute(
            "SELECT * FROM users WHERE lower(username) = lower(?)",
            (username.strip(),),
        ).fetchone()

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        clean_username = str(username or "").strip()
        if not clean_username or not password:
            raise ValueError("Username and password are required")
        with self.connect() as con:
            row = self.get_user_by_username(con, clean_username)
            if not row or not row["active"] or not verify_password(password, row["password_hash"]):
                raise PermissionError("Invalid username or password")

            token = secrets.token_urlsafe(32)
            token_digest = session_token_hash(token, self.config.session_secret)
            created = now_iso()
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
            con.execute(
                """
                INSERT INTO sessions (user_id, token_hash, created_at, expires_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["id"], token_digest, created, expires_at, created),
            )
            self.insert_audit(con, "user", str(row["id"]), "login", row["username"], "", "")
            con.commit()
            return {"token": token, "expiresAt": expires_at, "user": self.user_from_row(con, row)}

    def get_user_by_session(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        token_digest = session_token_hash(token, self.config.session_secret)
        with self.connect() as con:
            row = con.execute(
                """
                SELECT s.id AS session_id, s.expires_at, u.*
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ? AND u.active = 1
                """,
                (token_digest,),
            ).fetchone()
            if not row:
                return None
            if parse_iso(row["expires_at"]) <= datetime.now(timezone.utc):
                con.execute("DELETE FROM sessions WHERE id = ?", (row["session_id"],))
                con.commit()
                return None
            con.execute("UPDATE sessions SET last_seen_at = ? WHERE id = ?", (now_iso(), row["session_id"]))
            con.commit()
            return self.user_from_row(con, row)

    def delete_session(self, token: str) -> None:
        if not token:
            return
        token_digest = session_token_hash(token, self.config.session_secret)
        with self.connect() as con:
            con.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest,))
            con.commit()

    def list_users(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM users ORDER BY username").fetchall()
            return [self.user_from_row(con, row) for row in rows]

    def deactivate_user(self, username: str, deactivated_by: str = "system") -> dict[str, Any]:
        clean_username = str(username or "").strip()
        if not clean_username:
            raise ValueError("username is required")
        if clean_username.lower() == self.config.default_admin_username.lower():
            raise ValueError("The default admin user cannot be deactivated")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_user_by_username(con, clean_username)
            if not row:
                raise ValueError("User not found")
            con.execute("UPDATE users SET active = 0 WHERE id = ?", (row["id"],))
            con.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
            self.insert_audit(con, "user", clean_username, "deactivate_user", deactivated_by, "", "")
            con.commit()
        return {"users": self.list_users(), "username": clean_username}

    def list_active_sessions(self) -> list[dict[str, Any]]:
        now = now_iso()
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT s.id, s.created_at, s.expires_at, s.last_seen_at,
                       u.username, u.display_name
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.expires_at > ? AND u.active = 1
                ORDER BY s.last_seen_at DESC
                LIMIT 100
                """,
                (now,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "displayName": row["display_name"] or row["username"],
                "createdAt": row["created_at"],
                "lastSeenAt": row["last_seen_at"],
                "expiresAt": row["expires_at"],
            }
            for row in rows
        ]

    def create_user(self, data: dict[str, Any], created_by: str = "system") -> dict[str, Any]:
        username = " ".join(str(data.get("username") or "").split())[:80]
        display_name = " ".join(str(data.get("displayName") or username).split())[:120]
        password = str(data.get("password") or "")
        roles = data.get("roles") or ["Operator"]
        if not username or not password:
            raise ValueError("username and password are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = self.get_user_by_username(con, username)
            if existing:
                raise ValueError("User already exists")
            cur = con.execute(
                """
                INSERT INTO users (username, display_name, password_hash, active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (username, display_name, hash_password(password), now_iso()),
            )
            for role_name in roles:
                role = con.execute("SELECT id FROM roles WHERE name = ?", (str(role_name),)).fetchone()
                if not role:
                    raise ValueError(f"Unknown role: {role_name}")
                con.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", (cur.lastrowid, role["id"]))
            self.insert_audit(con, "user", username, "create_user", created_by, "", "", {"roles": roles})
            con.commit()
            user_row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self.user_from_row(con, user_row)

    def validate_import_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
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

    def import_delivery_list(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = self.validate_import_payload(data.get("payload") or data)
        user = request_user_name(data)
        source_name = str(data.get("fileName") or data.get("sourceName") or "").strip()[:255]
        definitions = build_delivery_lists(payload)
        base_items = payload.get("items") or []
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO imports (
                    delivery_date, source_name, row_count, total_qty, cpu_count,
                    mirror_count, status, imported_by, imported_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?)
                """,
                (
                    str(payload["deliveryDate"]),
                    source_name,
                    len(base_items),
                    sum(int(item.get("qty") or 0) for item in base_items),
                    sum(1 for item in base_items if is_cpu_item(item)),
                    sum(1 for item in base_items if "MIRROR" in str(item.get("product", "")).upper()),
                    user,
                    now_iso(),
                ),
            )
            for list_id, label, stage, scanner, items in definitions:
                self.upsert_delivery_list(con, list_id, label, str(payload["deliveryDate"]), stage, scanner, items, replace_items=True)
                self.insert_event(con, list_id, None, "IMPORT", "", user, scanner, "import", "Delivery list imported")
                self.insert_audit(con, "delivery_list", list_id, "import", user, scanner, "", {"sourceName": source_name})
            con.commit()
        return {"lists": self.get_delivery_lists(), "activeListId": definitions[0][0], "importedCount": len(definitions)}

    def find_unique_suffix_item(self, rows: list[sqlite3.Row], suffix: str, item_no: int) -> sqlite3.Row | None:
        matches = []
        for row in rows:
            if int(row["item_no"]) == item_no and f"{int(row['order_no']):06d}".endswith(suffix):
                matches.append(row)
        return matches[0] if len(matches) == 1 else None

    def recover_scan(self, raw_scan: str, rows: list[sqlite3.Row]) -> tuple[sqlite3.Row | None, str, str]:
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
            row = self.find_unique_suffix_item(rows, suffix, item_no)
            if row:
                return row, canonical_barcode(int(row["order_no"]), item_no), "Recovered suffix/item"

        return None, clean_text, "No unique delivery-list match"

    def insert_event(
        self,
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
    ) -> dict[str, Any]:
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
        if event_type == "error":
            self.insert_exception(con, list_id, cur.lastrowid, event_type, reason or message)
        return event_from_row(row)

    def insert_exception(self, con: sqlite3.Connection, list_id: str, event_id: int | None, exception_type: str, reason: str) -> None:
        con.execute(
            """
            INSERT INTO exceptions (list_id, scan_event_id, exception_type, status, reason, created_at)
            VALUES (?, ?, ?, 'Open', ?, ?)
            """,
            (list_id, event_id, exception_type, reason, now_iso()),
        )

    def insert_audit(
        self,
        con: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        action: str,
        user: str,
        station: str,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        con.execute(
            """
            INSERT INTO audit_events (entity_type, entity_id, action, user_name, station, reason, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (entity_type, entity_id, action, user, station, reason, json.dumps(payload or {}, separators=(",", ":")), now_iso()),
        )

    def record_scan(self, scan_request: dict[str, Any]) -> dict[str, Any]:
        list_id = str(scan_request.get("listId") or "")
        barcode = str(scan_request.get("barcode") or "")
        user = request_user_name(scan_request)
        station = request_station(scan_request)
        if not list_id or not barcode.strip():
            raise ValueError("listId and barcode are required")

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall()
            row, canonical, reason = self.recover_scan(barcode, rows)
            if row is None:
                last = self.insert_event(con, list_id, None, barcode, canonical, user, station, "error", "BAD SCAN format", reason)
                self.insert_audit(con, "scan", list_id, "scan_error", user, station, reason, {"barcode": barcode, "canonical": canonical})
                con.commit()
                return self._get_payload(con, list_id, last)

            if row["scanned_qty"] >= row["qty"]:
                last = self.insert_event(
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
                self.insert_audit(con, "line_item", row["id"], "duplicate_scan", user, station, "Quantity already scanned", {"barcode": barcode})
                con.commit()
                return self._get_payload(con, list_id, last)

            con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
            last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "scan", reason, "", 1)
            self.insert_audit(con, "line_item", row["id"], "scan", user, station, reason, {"barcode": barcode, "canonical": canonical})
            con.commit()
            return self._get_payload(con, list_id, last)

    def reset_stage(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE line_items SET scanned_qty = 0 WHERE list_id = ?", (list_id,))
            last = self.insert_event(con, list_id, None, "RESET", "", user, station, "reset", "Scan state reset")
            self.insert_audit(con, "delivery_list", list_id, "reset_scans", user, station, "Scan state reset")
            con.commit()
            return self._get_payload(con, list_id, last)

    def undo_last_scan(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        with self.connect() as con:
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
                last = self.insert_event(con, list_id, None, "UNDO", "", user, station, "error", "Nothing to undo")
                con.commit()
                return self._get_payload(con, list_id, last)

            con.execute("UPDATE line_items SET scanned_qty = MAX(scanned_qty - 1, 0) WHERE id = ?", (row["line_item_id"],))
            last = self.insert_event(
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
            self.insert_audit(con, "line_item", row["line_item_id"], "undo_scan", user, station, "Last scan undone")
            con.commit()
            return self._get_payload(con, list_id, last)

    def get_exceptions(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        list_id = str(filters.get("listId") or "")
        params: list[Any] = []
        where = "WHERE 1 = 1"
        if list_id:
            where += " AND ex.list_id = ?"
            params.append(list_id)
        with self.connect() as con:
            rows = con.execute(
                f"""
                SELECT ex.*, se.barcode, se.canonical_barcode, se.user_name, se.station, se.message
                FROM exceptions ex
                LEFT JOIN scan_events se ON se.id = ex.scan_event_id
                {where}
                ORDER BY ex.id DESC
                LIMIT 100
                """,
                params,
            ).fetchall()
        return [
            {
                "id": row["id"],
                "listId": row["list_id"],
                "eventId": row["scan_event_id"],
                "type": row["exception_type"],
                "status": row["status"],
                "reason": row["reason"],
                "barcode": row["canonical_barcode"] or row["barcode"],
                "message": row["message"],
                "user": row["user_name"],
                "station": row["station"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def preview_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        items = payload.get("items") if isinstance(payload, dict) else None
        errors = []
        warnings = []
        if not isinstance(payload, dict):
            errors.append("Import payload must be a JSON object")
            items = []
        if not payload.get("deliveryDate"):
            errors.append("Missing deliveryDate")
        if not isinstance(items, list) or not items:
            errors.append("Missing non-empty items array")
            items = []

        seen: dict[str, int] = {}
        missing_rows = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                missing_rows.append(index)
                continue
            missing = [key for key in ("order", "item", "qty") if str(item.get(key, "")).strip() == ""]
            if missing:
                missing_rows.append(index)
            key = f"{item.get('order', '')}-{item.get('item', '')}"
            seen[key] = seen.get(key, 0) + 1
        duplicates = [key for key, count in seen.items() if key != "-" and count > 1]
        if duplicates:
            warnings.append(f"Duplicate order/item combinations: {', '.join(duplicates[:10])}")
        if missing_rows:
            warnings.append(f"Rows with missing required fields: {', '.join(map(str, missing_rows[:20]))}")

        total_qty = sum(int(item.get("qty") or 0) for item in items if isinstance(item, dict) and str(item.get("qty", "")).isdigit())
        mirror_count = sum(1 for item in items if isinstance(item, dict) and "MIRROR" in str(item.get("product", "")).upper())
        cpu_count = sum(1 for item in items if isinstance(item, dict) and is_cpu_item(item))
        tall_count = 0
        oversize_count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            bay = suggested_bay(str(item.get("product", "")), str(item.get("dimensions", "")), str(item.get("route", "")))
            if bay == "Tall":
                tall_count += 1
            if bay == "Oversize":
                oversize_count += 1
        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "deliveryDate": payload.get("deliveryDate") if isinstance(payload, dict) else "",
            "rowCount": len(items),
            "totalQty": total_qty,
            "duplicateCount": len(duplicates),
            "duplicates": duplicates[:50],
            "cpuCount": cpu_count,
            "mirrorCount": mirror_count,
            "tallCount": tall_count,
            "oversizeCount": oversize_count,
            "indianTrailEligibleCount": len(items),
        }

    def admin_summary(self) -> dict[str, Any]:
        with self.connect() as con:
            list_count = con.execute("SELECT COUNT(*) FROM delivery_lists WHERE status = 'active'").fetchone()[0]
            item_count = con.execute("SELECT COUNT(*) FROM line_items").fetchone()[0]
            scan_count = con.execute("SELECT COUNT(*) FROM scan_events").fetchone()[0]
            open_exceptions = con.execute("SELECT COUNT(*) FROM exceptions WHERE status = 'Open'").fetchone()[0]
            user_count = con.execute("SELECT COUNT(*) FROM users WHERE active = 1").fetchone()[0]
            bay_count = con.execute("SELECT COUNT(*) FROM bays WHERE active = 1").fetchone()[0]
            import_rows = con.execute(
                "SELECT * FROM imports ORDER BY id DESC LIMIT 5"
            ).fetchall()
        return {
            "activeDeliveryLists": list_count,
            "lineItems": item_count,
            "scanEvents": scan_count,
            "openExceptions": open_exceptions,
            "activeUsers": user_count,
            "activeBays": bay_count,
            "databaseType": self.database_type,
            "databasePath": str(self.database_path),
            "authMode": self.config.auth_mode,
            "environment": self.config.environment,
            "recentImports": [
                {
                    "id": row["id"],
                    "deliveryDate": row["delivery_date"],
                    "sourceName": row["source_name"],
                    "rowCount": row["row_count"],
                    "totalQty": row["total_qty"],
                    "importedBy": row["imported_by"],
                    "importedAt": row["imported_at"],
                }
                for row in import_rows
            ],
        }

    def resolve_exception(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        exception_id = int(data.get("id") or 0)
        status = str(data.get("status") or "Resolved").strip()
        comment = str(data.get("comment") or data.get("reason") or "").strip()
        if status not in {"Reviewed", "Resolved", "Ignored", "Escalated"}:
            raise ValueError("Invalid exception status")
        if not exception_id or not comment:
            raise ValueError("Exception id and comment are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                UPDATE exceptions
                SET status = ?, resolved_by = ?, resolved_at = ?, resolution_comment = ?
                WHERE id = ?
                """,
                (status, user, now_iso(), comment, exception_id),
            )
            self.insert_audit(con, "exception", str(exception_id), f"exception_{status.lower()}", user, "", comment)
            con.commit()
        return {"ok": True, "id": exception_id, "status": status}

    def global_search(self, query: str, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        clean = str(query or "").strip()
        if len(clean) < 2:
            return []
        like = f"%{clean}%"
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT li.*, dl.stage, dl.label,
                       b.bay_code,
                       b.display_name AS bay_display_name,
                       ba.status AS bay_status,
                       (
                           SELECT se.created_at
                           FROM scan_events se
                           WHERE se.line_item_id = li.id
                           ORDER BY se.id DESC
                           LIMIT 1
                       ) AS last_scan_time,
                       (
                           SELECT se.user_name
                           FROM scan_events se
                           WHERE se.line_item_id = li.id
                           ORDER BY se.id DESC
                           LIMIT 1
                       ) AS last_scan_user
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id AND ba.status NOT IN ('Cleared', 'Cancelled')
                LEFT JOIN bays b ON b.id = ba.bay_id
                WHERE li.order_no LIKE ? OR li.item_no LIKE ? OR li.barcode LIKE ?
                   OR li.customer LIKE ? OR li.job LIKE ? OR li.route LIKE ?
                   OR li.product LIKE ? OR li.dimensions LIKE ? OR dl.stage LIKE ?
                   OR b.bay_code LIKE ? OR b.display_name LIKE ?
                ORDER BY dl.delivery_date DESC, CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER)
                LIMIT 100
                """,
                (like, like, like, like, like, like, like, like, like, like, like),
            ).fetchall()
        results = []
        for row in rows:
            if user is not None and not user_can_access_stage(user, row["stage"], ""):
                continue
            results.append({
                "lineItemId": row["id"],
                "deliveryListId": row["list_id"],
                "deliveryList": row["label"],
                "stage": row["stage"],
                "barcode": row["barcode"],
                "order": row["order_no"],
                "item": row["item_no"],
                "qty": row["qty"],
                "scanned": row["scanned_qty"],
                "dimensions": row["dimensions"],
                "customer": row["customer"],
                "job": row["job"],
                "route": row["route"],
                "product": row["product"],
                "bay": row["bay_display_name"] or row["bay_code"],
                "bayCode": row["bay_code"],
                "bayStatus": row["bay_status"],
                "lastScanTime": row["last_scan_time"],
                "lastScanUser": row["last_scan_user"],
            })
        return results

    def update_line_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        line_item_id = str(data.get("lineItemId") or "")
        if not line_item_id:
            raise ValueError("lineItemId is required")
        allowed_fields = {
            "qty": "qty",
            "scanned": "scanned_qty",
            "dimensions": "dimensions",
            "customer": "customer",
            "route": "route",
            "job": "job",
            "product": "product",
            "processState": "process_state",
        }
        updates = []
        params: list[Any] = []
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM line_items WHERE id = ?", (line_item_id,)).fetchone()
            if not row:
                raise ValueError("Line item not found")
            next_qty = int(data.get("qty", row["qty"]) or 0)
            next_scanned = int(data.get("scanned", row["scanned_qty"]) or 0)
            if next_qty < 0 or next_scanned < 0 or next_scanned > next_qty:
                raise ValueError("Scanned quantity must be between 0 and total quantity")
            for input_key, column in allowed_fields.items():
                if input_key not in data:
                    continue
                value = data.get(input_key)
                if column in {"qty", "scanned_qty"}:
                    value = int(value or 0)
                else:
                    value = str(value or "")[:255]
                updates.append(f"{column} = ?")
                params.append(value)
            if updates:
                params.append(line_item_id)
                con.execute(f"UPDATE line_items SET {', '.join(updates)} WHERE id = ?", params)
                self.insert_audit(con, "line_item", line_item_id, "manual_edit", user, "", "", {"fields": list(data.keys())})
            con.commit()
            return self._get_payload(con, row["list_id"])

    def reports_summary(self) -> dict[str, Any]:
        with self.connect() as con:
            scans_by_user = con.execute(
                """
                SELECT user_name, COUNT(*) AS scans
                FROM scan_events
                WHERE event_type = 'scan'
                GROUP BY user_name
                ORDER BY scans DESC
                """
            ).fetchall()
            incomplete = con.execute(
                """
                SELECT dl.label, COUNT(*) AS item_count, SUM(li.qty - li.scanned_qty) AS remaining_qty
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE li.scanned_qty < li.qty
                GROUP BY dl.id
                ORDER BY dl.delivery_date DESC, dl.label
                """
            ).fetchall()
            bad_scans = con.execute("SELECT COUNT(*) FROM scan_events WHERE event_type = 'error'").fetchone()[0]
            duplicates = con.execute("SELECT COUNT(*) FROM scan_events WHERE event_type = 'duplicate'").fetchone()[0]
            sdi_count = con.execute("SELECT COUNT(*) FROM bay_assignments WHERE status = 'SDIOverride'").fetchone()[0]
        return {
            "scansByOperator": [{"user": row["user_name"], "scans": row["scans"]} for row in scans_by_user],
            "incompleteByDeliveryList": [
                {"deliveryList": row["label"], "itemCount": row["item_count"], "remainingQty": row["remaining_qty"] or 0}
                for row in incomplete
            ],
            "badScanCount": bad_scans,
            "duplicateScanCount": duplicates,
            "sdiCount": sdi_count,
        }

    def bay_from_row(self, con: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        assignments = con.execute(
            """
            SELECT ba.*, li.order_no, li.item_no, li.qty, li.scanned_qty, li.customer,
                   li.dimensions, li.product, li.job
            FROM bay_assignments ba
            JOIN line_items li ON li.id = ba.line_item_id
            WHERE ba.bay_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
            ORDER BY ba.assigned_at DESC
            """,
            (row["id"],),
        ).fetchall()
        assigned_qty = sum(int(item["assigned_qty"] or 0) for item in assignments)
        if any(item["status"] == "SDIOverride" for item in assignments):
            status = "SDI"
        elif assigned_qty == 0:
            status = "Empty"
        elif row["capacity_qty"] and assigned_qty >= row["capacity_qty"]:
            status = "Full"
        elif len(assignments) > 1:
            status = "Partial"
        else:
            status = "Occupied"
        return {
            "id": row["id"],
            "bayCode": row["bay_code"],
            "displayName": row["display_name"] or row["bay_code"],
            "area": row["area"],
            "bayType": row["bay_type"],
            "mapSection": row["map_section"],
            "bayCategory": row["bay_category"],
            "layoutRow": row["layout_row"],
            "layoutCol": row["layout_col"],
            "layoutCell": row["layout_cell"],
            "capacityQty": row["capacity_qty"],
            "assignedQty": assigned_qty,
            "status": status,
            "active": bool(row["active"]),
            "assignments": [
                {
                    "id": item["id"],
                    "lineItemId": item["line_item_id"],
                    "order": item["order_no"],
                    "item": item["item_no"],
                    "qty": item["qty"],
                    "scanned": item["scanned_qty"],
                    "assignedQty": item["assigned_qty"],
                    "customer": item["customer"],
                    "dimensions": item["dimensions"],
                    "product": item["product"],
                    "job": item["job"],
                    "status": item["status"],
                }
                for item in assignments
            ],
        }

    def get_bays(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM bays ORDER BY COALESCE(layout_row, 9999), COALESCE(layout_col, 9999), sort_order, bay_code").fetchall()
            return [self.bay_from_row(con, row) for row in rows]

    def get_bay_layout(self) -> dict[str, Any]:
        layout_path = self.config.root / "data" / "indian-trail-bay-layout.json"
        if not layout_path.exists():
            return {"bays": [], "cells": [], "sections": [], "grid": {"minRow": 1, "maxRow": 1, "minCol": 1, "maxCol": 1}}
        return json.loads(layout_path.read_text(encoding="utf-8"))

    def indian_trail_summary(self) -> dict[str, Any]:
        with self.connect() as con:
            inbound = con.execute(
                "SELECT id FROM delivery_lists WHERE stage LIKE '%Indian Trail%' AND status = 'active' ORDER BY delivery_date DESC LIMIT 1"
            ).fetchone()
            list_id = inbound["id"] if inbound else ""
            totals = {"totalQty": 0, "receivedQty": 0, "unassignedQty": 0}
            if list_id:
                row = con.execute(
                    "SELECT COALESCE(SUM(qty),0) AS total_qty, COALESCE(SUM(scanned_qty),0) AS received_qty FROM line_items WHERE list_id = ?",
                    (list_id,),
                ).fetchone()
                unassigned = con.execute(
                    """
                    SELECT COALESCE(SUM(li.qty), 0)
                    FROM line_items li
                    LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id AND ba.status NOT IN ('Cleared', 'Cancelled')
                    WHERE li.list_id = ? AND ba.id IS NULL
                    """,
                    (list_id,),
                ).fetchone()[0]
                totals = {"totalQty": row["total_qty"], "receivedQty": row["received_qty"], "unassignedQty": unassigned}
            assigned = con.execute("SELECT COALESCE(SUM(assigned_qty),0) FROM bay_assignments WHERE status NOT IN ('Cleared', 'Cancelled')").fetchone()[0]
            sdi = con.execute("SELECT COUNT(*) FROM bay_assignments WHERE status = 'SDIOverride'").fetchone()[0]
            conflicts = con.execute("SELECT COUNT(*) FROM exceptions WHERE exception_type LIKE '%bay%' AND status = 'Open'").fetchone()[0]
            cleared_today = con.execute("SELECT COUNT(*) FROM bay_events WHERE event_type = 'ClearBay' AND created_at >= date('now')").fetchone()[0]
            needs_check = con.execute("SELECT COUNT(*) FROM bay_events WHERE event_type = 'NeedsReview' AND created_at >= date('now')").fetchone()[0]
        return {
            "activeInboundListId": list_id,
            "inboundToday": totals["totalQty"],
            "receivedQty": totals["receivedQty"],
            "assignedToBays": assigned,
            "unassignedQty": totals["unassignedQty"],
            "sdiCount": sdi,
            "bayConflicts": conflicts,
            "clearedToday": cleared_today,
            "needsCheck": needs_check,
        }

    def find_bay_for_assignment(self, con: sqlite3.Connection, bay_type: str) -> sqlite3.Row | None:
        rows = con.execute(
            """
            SELECT b.*,
                   COALESCE(SUM(CASE WHEN ba.status NOT IN ('Cleared', 'Cancelled') THEN ba.assigned_qty ELSE 0 END), 0) AS used_qty
            FROM bays b
            LEFT JOIN bay_assignments ba ON ba.bay_id = b.id
            WHERE b.active = 1 AND b.bay_type = ?
            GROUP BY b.id
            HAVING used_qty < b.capacity_qty OR b.capacity_qty = 0
            ORDER BY used_qty, b.sort_order
            LIMIT 1
            """,
            (bay_type,),
        ).fetchone()
        return rows

    def get_bay_by_code(self, con: sqlite3.Connection, bay_code: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM bays WHERE bay_code = ? AND active = 1", (bay_code,)).fetchone()
        if not row:
            raise ValueError(f"Unknown or inactive bay: {bay_code}")
        return row

    def insert_bay_event(
        self,
        con: sqlite3.Connection,
        bay_id: int | None,
        line_item_id: str,
        event_type: str,
        user: str,
        reason: str = "",
        old_bay_id: int | None = None,
        new_bay_id: int | None = None,
    ) -> None:
        con.execute(
            """
            INSERT INTO bay_events (bay_id, line_item_id, event_type, old_bay_id, new_bay_id, reason, user_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bay_id, line_item_id, event_type, old_bay_id, new_bay_id, reason, user, now_iso()),
        )

    def assign_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        line_item_id = str(data.get("lineItemId") or "")
        bay_code = str(data.get("bayCode") or "")
        reason = str(data.get("reason") or "").strip()
        assigned_qty = int(data.get("assignedQty") or 1)
        if not line_item_id or not bay_code:
            raise ValueError("lineItemId and bayCode are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            item = con.execute("SELECT * FROM line_items WHERE id = ?", (line_item_id,)).fetchone()
            if not item:
                raise ValueError("Line item not found")
            bay = self.get_bay_by_code(con, bay_code)
            cur = con.execute(
                """
                INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
                VALUES (?, ?, ?, ?, 'Assigned', ?, ?, ?)
                """,
                (item["list_id"], line_item_id, bay["id"], assigned_qty, user, now_iso(), reason),
            )
            self.insert_bay_event(con, bay["id"], line_item_id, "AssignBay", user, reason, new_bay_id=bay["id"])
            self.insert_audit(con, "bay_assignment", str(cur.lastrowid), "assign_bay", user, "", reason, {"bayCode": bay_code})
            con.commit()
        return {"ok": True, "assignmentId": cur.lastrowid, "bayCode": bay_code}

    def receive_indian_trail_scan(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        list_id = str(data.get("listId") or "")
        station = request_station(data) or "Indian Trail"
        barcode = str(data.get("barcode") or "")
        with self.connect() as con:
            if not list_id:
                inbound = con.execute(
                    "SELECT id FROM delivery_lists WHERE stage LIKE '%Indian Trail%' AND status = 'active' ORDER BY delivery_date DESC LIMIT 1"
                ).fetchone()
                list_id = inbound["id"] if inbound else ""
            if not list_id:
                raise ValueError("No active Indian Trail inbound list")
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall()
            row, canonical, reason = self.recover_scan(barcode, rows)
            if row is None:
                last = self.insert_event(con, list_id, None, barcode, canonical, user, station, "error", "Not on active Indian Trail inbound list", reason)
                con.commit()
                return {"ok": False, "message": "Not on active Indian Trail inbound list. Send to supervisor.", "lastScan": last}
            if row["scanned_qty"] >= row["qty"]:
                last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "duplicate", "Item already complete", "Quantity already received")
                con.commit()
                return {"ok": False, "message": "Quantity already received. Send to supervisor.", "lastScan": last}
            con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
            last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "scan", "Indian Trail received", reason, 1)
            assignment = con.execute(
                """
                SELECT ba.*, b.bay_code
                FROM bay_assignments ba
                JOIN bays b ON b.id = ba.bay_id
                WHERE ba.line_item_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
                ORDER BY ba.id DESC
                LIMIT 1
                """,
                (row["id"],),
            ).fetchone()
            existing = bool(assignment)
            if assignment:
                bay_code = assignment["bay_code"]
            else:
                row_item = {
                    "route": row["route"],
                    "job": row["job"],
                    "customer": row["customer"],
                    "product": row["product"],
                    "processState": row["process_state"],
                    "queueState": row["queue_state"],
                }
                bay_type = "CPU" if is_cpu_item(row_item) else suggested_bay(row["product"], row["dimensions"], row["route"])
                bay = self.find_bay_for_assignment(con, bay_type) or self.find_bay_for_assignment(con, "Standard")
                if not bay:
                    self.insert_exception(con, list_id, None, "bay_assignment_conflict", "No safe bay available")
                    bay_code = ""
                else:
                    bay_code = bay["bay_code"]
                    con.execute(
                        """
                        INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
                        VALUES (?, ?, ?, 1, 'Received', ?, ?, 'Auto suggested during receive')
                        """,
                        (list_id, row["id"], bay["id"], user, now_iso()),
                    )
                    self.insert_bay_event(con, bay["id"], row["id"], "ReceiveAssignBay", user, "Auto suggested during receive", new_bay_id=bay["id"])
            self.insert_audit(con, "line_item", row["id"], "indian_trail_receive", user, station, reason, {"bayCode": bay_code})
            con.commit()
            scanned_after = int(row["scanned_qty"]) + 1
        message = (
            f"Order {row['order_no']} / Item {row['item_no']} received. Existing Bay: {bay_code}. Place with existing order."
            if existing
            else f"Order {row['order_no']} / Item {row['item_no']} received. Suggested Bay: {bay_code}. Qty Received: {scanned_after}/{row['qty']}. Place in Bay {bay_code}."
        )
        return {"ok": True, "message": message, "bayCode": bay_code, "existingBay": existing, "lastScan": last}

    def move_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        new_bay_code = str(data.get("newBayCode") or data.get("bayCode") or "")
        reason = str(data.get("reason") or "").strip()
        if not assignment_id or not new_bay_code or not reason:
            raise ValueError("assignmentId, newBayCode, and reason are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not assignment:
                raise ValueError("Assignment not found")
            new_bay = self.get_bay_by_code(con, new_bay_code)
            con.execute("UPDATE bay_assignments SET bay_id = ?, status = 'Moved', reason = ? WHERE id = ?", (new_bay["id"], reason, assignment_id))
            self.insert_bay_event(con, new_bay["id"], assignment["line_item_id"], "MoveBay", user, reason, assignment["bay_id"], new_bay["id"])
            self.insert_audit(con, "bay_assignment", str(assignment_id), "move_bay", user, "", reason, {"newBayCode": new_bay_code})
            con.commit()
        return {"ok": True, "assignmentId": assignment_id, "bayCode": new_bay_code}

    def clear_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        bay_code = str(data.get("bayCode") or "")
        reason = str(data.get("reason") or "Bay cleared").strip()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            bay = self.get_bay_by_code(con, bay_code)
            rows = con.execute("SELECT * FROM bay_assignments WHERE bay_id = ? AND status NOT IN ('Cleared', 'Cancelled')", (bay["id"],)).fetchall()
            for row in rows:
                con.execute(
                    "UPDATE bay_assignments SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ? WHERE id = ?",
                    (user, now_iso(), reason, row["id"]),
                )
                self.insert_bay_event(con, bay["id"], row["line_item_id"], "ClearBay", user, reason, old_bay_id=bay["id"])
            self.insert_audit(con, "bay", bay_code, "clear_bay", user, "", reason, {"clearedAssignments": len(rows)})
            con.commit()
        return {"ok": True, "bayCode": bay_code, "clearedAssignments": len(rows)}

    def mark_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        reason = str(data.get("reason") or "").strip()
        if not assignment_id or not reason:
            raise ValueError("assignmentId and reason are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not assignment:
                raise ValueError("Assignment not found")
            con.execute("UPDATE bay_assignments SET status = 'SDIOverride', reason = ? WHERE id = ?", (reason, assignment_id))
            self.insert_bay_event(con, assignment["bay_id"], assignment["line_item_id"], "MarkSDI", user, reason)
            self.insert_audit(con, "bay_assignment", str(assignment_id), "mark_sdi", user, "", reason)
            con.commit()
        return {"ok": True, "assignmentId": assignment_id, "status": "SDIOverride"}

    def remove_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        reason = str(data.get("reason") or "").strip()
        if not assignment_id or not reason:
            raise ValueError("assignmentId and reason are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not assignment:
                raise ValueError("Assignment not found")
            con.execute("UPDATE bay_assignments SET status = 'Assigned', reason = ? WHERE id = ?", (reason, assignment_id))
            self.insert_bay_event(con, assignment["bay_id"], assignment["line_item_id"], "RemoveSDI", user, reason)
            self.insert_audit(con, "bay_assignment", str(assignment_id), "remove_sdi", user, "", reason)
            con.commit()
        return {"ok": True, "assignmentId": assignment_id, "status": "Assigned"}

    def bay_check(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        bay_code = str(data.get("bayCode") or "")
        action = str(data.get("action") or "").strip()
        reason = str(data.get("reason") or action or "Bay check").strip()
        if action == "empty":
            return self.clear_bay({"bayCode": bay_code, "reason": reason}, user)
        event_type = "NeedsReview" if action == "needs_review" else "StillOccupied"
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            bay = self.get_bay_by_code(con, bay_code)
            self.insert_bay_event(con, bay["id"], "", event_type, user, reason)
            self.insert_audit(con, "bay", bay_code, f"bay_check_{action}", user, "", reason)
            con.commit()
        return {"ok": True, "bayCode": bay_code, "action": action}

    def export_csv(self, list_id: str) -> str:
        rows = self.get_line_items(list_id)
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
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
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
                }
            )
        return output.getvalue()


def create_store(config: AppConfig) -> BaseDeliveryStore:
    if config.database_type == "sqlite":
        return SQLiteDeliveryStore(config)
    raise NotImplementedError(
        f"Database type {config.database_type!r} is not implemented yet. "
        "Add a store adapter that implements BaseDeliveryStore."
    )
