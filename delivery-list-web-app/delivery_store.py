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
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

from scanner_config import AppConfig


DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup", "DTC"]
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
    "reactivate_users",
    "update_user_passwords",
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
    "manage_bay_layout",
    "manage_customer_route_rules",
    "check_updates",
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
    "Operator": ["Airport Rd", "Customer Pickup", "DTC", "Greenville"],
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
    ("inbound-indian-trail", "Inbound - Indian Trail", "Indian Trail", "indian_trail"),
    ("bfs-greenville", "BFS Greenville", "Greenville", "greenville"),
    ("customer-pickup", "Customer Pickup", "Customer Pickup", "cpu"),
    ("dtc", "DTC - Deliver to Customer", "DTC", "dtc"),
]
DEFAULT_CUSTOMER_ROUTE_RULES = [
    ("Blue Color Glass", "CPU"),
    ("ABZZ Glass", "CPU"),
    ("Glass & Door Pro", "CPU"),
    ("Add It Home Services", "DTC"),
]
SUPPORTED_IMPORT_EXTENSIONS = {".json", ".xlsx", ".xlsm", ".csv"}
XLSX_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
XLSX_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
XLSX_PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


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


def normalized_match_text(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def simplified_match_text(value: Any) -> str:
    text = normalized_match_text(value)
    for token in ("AND", "THE", "INC", "LLC", "COMPANY", "CO"):
        text = text.replace(token, "")
    return text


def fuzzy_contains(text: str, needle: str) -> bool:
    haystack = normalized_match_text(text)
    clean_needle = normalized_match_text(needle)
    if not clean_needle:
        return False
    if clean_needle in haystack:
        return True
    loose_haystack = simplified_match_text(text)
    loose_needle = simplified_match_text(needle)
    return bool(loose_needle) and loose_needle in loose_haystack


def default_customer_route(item: dict[str, Any]) -> str:
    signal = " ".join(str(item.get(key, "")) for key in ("customer", "job", "product", "route"))
    for customer, route in DEFAULT_CUSTOMER_ROUTE_RULES:
        if fuzzy_contains(signal, customer):
            return route
    return ""


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


def route_signal_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key, ""))
        for key in ("route", "job", "customer", "product", "processState", "queueState")
    ).upper()


def inferred_route(item: dict[str, Any]) -> str:
    route = str(item.get("route", "")).strip().upper()
    text = route_signal_text(item)
    compact = normalized_match_text(text)
    if re.search(r"\bCPU[-\s]*(IT|INT)\b", text) or re.search(r"\bIT[-\s]*CPU\b", text):
        return ""
    if re.search(r"\bCPU[-\s]*AIR\b", text) or "CPUAIR" in compact:
        return "CPU"
    if re.search(r"\b(GNV|GREENVILLE)\b", text):
        return "GNV"
    if re.search(r"\b(DTC|DELIVER\s+TO\s+CUSTOMER)\b", text):
        return "DTC"
    if re.search(r"\b(INT|INDIAN\s+TRAIL)\b", text):
        return ""
    if route == "CPU" or re.search(r"\bCPU\b", text):
        return "CPU"
    if route in {"INT", "IT", "INDIAN TRAIL"}:
        return ""
    return route or default_customer_route(item)


def route_category(item: dict[str, Any]) -> str:
    route = inferred_route(item)
    if route == "CPU":
        return "cpu"
    if route == "GNV":
        return "greenville"
    if route == "DTC":
        return "dtc"
    return "indian_trail"


def is_cpu_item(item: dict[str, Any]) -> bool:
    return route_category(item) == "cpu"


def suggested_bay(product: str, dimensions: str, route: str) -> str:
    if str(route).upper() == "CPU":
        return "CPU"
    if "FRAMED" in str(product).upper() and "MIRROR" in str(product).upper():
        return "Framed Mirror"
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
    if profile == "indian_trail":
        return [item for item in base_items if route_category(item) == "indian_trail"]
    if profile == "greenville":
        return [item for item in base_items if route_category(item) == "greenville"]
    if profile == "dtc":
        return [item for item in base_items if route_category(item) == "dtc"]
    return list(base_items)


def build_delivery_lists(sample: dict[str, Any]) -> list[tuple[str, str, str, str, list[dict[str, Any]]]]:
    delivery_date = str(sample.get("deliveryDate") or now_iso()[:10])
    base_items = sample.get("items") or []
    definitions: list[tuple[str, str, str, str, list[dict[str, Any]]]] = []
    for suffix, stage, scanner, profile in LIST_PROFILES:
        items = items_for_profile(profile, base_items)
        if profile != "all" and not items:
            continue
        definitions.append(
            (
                f"{delivery_date}-{suffix}",
                f"{format_display_date(delivery_date)} - {stage}",
                stage,
                scanner,
                items,
            )
        )
    return definitions


def all_profile_list_ids(delivery_date: str) -> list[str]:
    return [f"{delivery_date}-{suffix}" for suffix, _, _, _ in LIST_PROFILES]


def parse_int_text(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text.replace(",", "")))
    except ValueError:
        match = re.search(r"\d+", text)
        return int(match.group(0)) if match else None


def clean_excel_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"_x000[dD]_", "\r", text)
    text = re.sub(r"_x000[aA]_", "\n", text)
    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def format_delivery_date(month: int, day: int, year: int) -> str:
    if year < 100:
        year += 2000
    return f"{year:04d}-{month:02d}-{day:02d}"


def delivery_date_from_text(text: str) -> str:
    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})(?!\d)", text)
    if not match:
        return ""
    month, day, year = (int(part) for part in match.groups())
    return format_delivery_date(month, day, year)


def column_label(ref: str) -> str:
    match = re.match(r"([A-Z]+)", ref.upper())
    return match.group(1) if match else ""


def first_xlsx_sheet_path(archive: zipfile.ZipFile) -> str:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        first_sheet = workbook.find(f"{XLSX_MAIN_NS}sheets/{XLSX_MAIN_NS}sheet")
        rel_id = first_sheet.attrib.get(f"{XLSX_REL_NS}id") if first_sheet is not None else ""
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        for rel in relationships.findall(f"{XLSX_PACKAGE_REL_NS}Relationship"):
            if rel.attrib.get("Id") == rel_id:
                target = rel.attrib.get("Target", "").lstrip("/")
                return target if target.startswith("xl/") else f"xl/{target}"
    except Exception:
        pass
    for name in archive.namelist():
        if name.startswith("xl/worksheets/") and name.endswith(".xml") and "/_rels/" not in name:
            return name
    raise ValueError("Workbook does not contain a worksheet XML file")


def read_xlsx_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{XLSX_MAIN_NS}si"):
                shared_strings.append(clean_excel_text("".join(node.text or "" for node in item.iter(f"{XLSX_MAIN_NS}t"))))
        sheet = ET.fromstring(archive.read(first_xlsx_sheet_path(archive)))
        rows: list[tuple[int, dict[str, str]]] = []
        for row in sheet.findall(f"{XLSX_MAIN_NS}sheetData/{XLSX_MAIN_NS}row"):
            row_number = int(row.attrib.get("r") or len(rows) + 1)
            values: dict[str, str] = {}
            for cell in row.findall(f"{XLSX_MAIN_NS}c"):
                col = column_label(cell.attrib.get("r", ""))
                if not col:
                    continue
                cell_type = cell.attrib.get("t")
                raw_value = ""
                if cell_type == "inlineStr":
                    raw_value = "".join(node.text or "" for node in cell.iter(f"{XLSX_MAIN_NS}t"))
                else:
                    value_node = cell.find(f"{XLSX_MAIN_NS}v")
                    raw_value = value_node.text if value_node is not None and value_node.text is not None else ""
                    if cell_type == "s" and raw_value.isdigit():
                        index = int(raw_value)
                        raw_value = shared_strings[index] if index < len(shared_strings) else ""
                value = clean_excel_text(raw_value)
                if value:
                    values[col] = value
            if values:
                rows.append((row_number, values))
        return rows


def delivery_date_from_rows_or_name(rows: list[tuple[int, dict[str, str]]], path: Path) -> str:
    for _, row in rows[:12]:
        date_text = delivery_date_from_text(" ".join(row.values()))
        if date_text:
            return date_text
    date_text = delivery_date_from_text(path.stem)
    if date_text:
        return date_text
    return now_iso()[:10]


def parse_aw_delivery_workbook(path: Path) -> dict[str, Any]:
    rows = read_xlsx_rows(path)
    delivery_date = delivery_date_from_rows_or_name(rows, path)
    current_product = ""
    items: list[dict[str, Any]] = []
    for row_number, row in rows:
        a_value = row.get("A", "")
        order_col = item_col = qty_col = dims_col = customer_col = remake_col = route_col = ""
        if parse_int_text(row.get("F")) is not None and parse_int_text(row.get("G")) is not None and parse_int_text(row.get("J")) is not None:
            order_col, item_col, qty_col, dims_col, customer_col, remake_col, route_col = "F", "G", "J", "L", "N", "V", "X"
        elif parse_int_text(row.get("E")) is not None and parse_int_text(row.get("F")) is not None and parse_int_text(row.get("G")) is not None:
            order_col, item_col, qty_col, dims_col, customer_col, remake_col, route_col = "E", "F", "G", "H", "I", "J", "L"
        else:
            header_text = " ".join(row.values()).lower()
            if a_value and "delivery list" not in header_text and "job nr" not in header_text:
                current_product = a_value
            continue

        order_no = parse_int_text(row.get(order_col))
        item_no = parse_int_text(row.get(item_col))
        qty = parse_int_text(row.get(qty_col))
        if order_no is None or item_no is None or qty is None:
            continue
        remake = row.get(remake_col, "")
        is_remake = is_remake_item({"processState": remake, "queueState": remake})
        item = {
            "id": f"{path.stem}:{row_number}:{order_no}:{item_no}",
            "order": str(order_no),
            "item": str(item_no).zfill(3),
            "qty": qty,
            "dimensions": row.get(dims_col, ""),
            "customer": row.get(customer_col, ""),
            "route": row.get(route_col, ""),
            "job": a_value,
            "product": current_product,
            "processState": "Remake" if is_remake else "",
            "queueState": remake,
            "sourceRow": row_number,
        }
        item["route"] = inferred_route(item)
        items.append(item)
    if not items:
        raise ValueError(f"No delivery-list rows found in {path.name}")
    return {"deliveryDate": delivery_date, "sourceName": path.name, "items": items}


def parse_delivery_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    items = []
    for index, row in enumerate(rows, start=1):
        order_no = row.get("order") or row.get("Order Nr.") or row.get("Order Nr") or row.get("Order")
        item_no = row.get("item") or row.get("Item Nr.") or row.get("Item Nr") or row.get("Item")
        qty = row.get("qty") or row.get("Qty.") or row.get("Qty") or "1"
        if not order_no or not item_no:
            continue
        item = {
            "id": f"{path.stem}:{index}:{order_no}:{item_no}",
            "order": str(parse_int_text(order_no) or order_no),
            "item": str(parse_int_text(item_no) or item_no).zfill(3),
            "qty": parse_int_text(qty) or 1,
            "dimensions": row.get("dimensions") or row.get("Dimensions") or "",
            "customer": row.get("customer") or row.get("Customer") or "",
            "route": row.get("route") or row.get("Route") or "",
            "job": row.get("job") or row.get("Job Nr.") or row.get("Job Nr") or "",
            "product": row.get("product") or row.get("Product") or "",
            "processState": row.get("processState") or row.get("Process State") or "",
            "queueState": row.get("queueState") or row.get("Queue State") or "",
        }
        item["route"] = inferred_route(item)
        items.append(item)
    if not items:
        raise ValueError(f"No delivery-list rows found in {path.name}")
    return {"deliveryDate": delivery_date_from_text(path.stem) or now_iso()[:10], "sourceName": path.name, "items": items}


def load_delivery_source_payload(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix in {".xlsx", ".xlsm"}:
        return parse_aw_delivery_workbook(path)
    if suffix == ".csv":
        return parse_delivery_csv(path)
    raise ValueError(f"Unsupported import file type: {path.suffix}")


def source_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_remake_item(item: dict[str, Any]) -> bool:
    text = " ".join(str(item.get(key, "")) for key in ("remake", "processState", "queueState")).upper()
    return "REMAKE" in text or re.search(r"\bRM\b", text) is not None


def is_mirror_item(item: dict[str, Any]) -> bool:
    text = " ".join(str(item.get(key, "")) for key in ("product", "job", "customer", "route")).upper()
    return "MIRROR" in text or re.search(r"\bMIR\b", text) is not None


def should_print_delivery_item(item: dict[str, Any], exclude_mirrors: bool = True, include_mirror_remakes: bool = True) -> bool:
    if not exclude_mirrors:
        return True
    if not is_mirror_item(item):
        return True
    return include_mirror_remakes and is_remake_item(item)


def print_counts_for_items(items: list[dict[str, Any]]) -> dict[str, int]:
    printable = [item for item in items if should_print_delivery_item(item)]
    return {
        "rowCount": len(printable),
        "pieceCount": sum(int(item.get("qty") or 0) for item in printable),
        "remakeCount": sum(1 for item in printable if is_remake_item(item)),
        "excludedMirrorCount": sum(1 for item in items if is_mirror_item(item) and not should_print_delivery_item(item)),
    }


def item_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sourceId": row["source_id"],
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

    def redo_last_undo(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        raise NotImplementedError

    def reset_stage(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        raise NotImplementedError

    def import_delivery_list(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def import_delivery_folder(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_print_package(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def get_scan_events(self, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_exceptions(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_stations(self) -> list[str]:
        raise NotImplementedError

    def add_station(self, name: str) -> dict[str, Any]:
        raise NotImplementedError

    def rename_station(self, old_name: str, new_name: str) -> dict[str, Any]:
        raise NotImplementedError

    def remove_station(self, name: str) -> dict[str, Any]:
        raise NotImplementedError

    def export_csv(self, list_id: str) -> str:
        raise NotImplementedError

    def export_xlsx(self, list_id: str) -> bytes:
        raise NotImplementedError

    def export_package_xlsx(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> bytes:
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

    def reactivate_user(self, username: str, activated_by: str = "system") -> dict[str, Any]:
        raise NotImplementedError

    def update_user_password(self, username: str, password: str, updated_by: str = "system") -> dict[str, Any]:
        raise NotImplementedError

    def update_user_roles(self, username: str, roles: list[str], updated_by: str = "system") -> dict[str, Any]:
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

    def delete_delivery_list(self, list_id: str, user: str) -> dict[str, Any]:
        raise NotImplementedError

    def delete_delivery_date(self, delivery_date: str, user: str) -> dict[str, Any]:
        raise NotImplementedError

    def delete_line_item(self, line_item_id: str, user: str) -> dict[str, Any]:
        raise NotImplementedError

    def get_customer_route_rules(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def add_customer_route_rule(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def remove_customer_route_rule(self, rule_id: int, user: str) -> dict[str, Any]:
        raise NotImplementedError

    def reports_summary(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_bays(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_bay_layout(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_bay_events(self, limit: int = 20) -> list[dict[str, Any]]:
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

    def scan_out_bay_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def clear_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def restore_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def update_bay_layout(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        raise NotImplementedError

    def set_bay_group_position(self, data: dict[str, Any], user: str) -> dict[str, Any]:
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
            self.seed_customer_route_rules(con)
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

            CREATE TABLE IF NOT EXISTS customer_route_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_pattern TEXT NOT NULL UNIQUE,
                route TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
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
        self.ensure_column(con, "bays", "status", "TEXT NOT NULL DEFAULT 'Available'")
        self.ensure_column(con, "imports", "source_path", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "imports", "source_hash", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "imports", "import_kind", "TEXT NOT NULL DEFAULT 'manual'")
        con.commit()

    def ensure_column(self, con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def clone_item_for_list(self, item: dict[str, Any], list_id: str, index: int) -> dict[str, Any]:
        order_no = str(item["order"])
        item_no = str(item["item"]).zfill(3)
        route = inferred_route(item)
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

    def insert_line_items(self, con: sqlite3.Connection, list_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cloned_items = []
        for index, item in enumerate(items, start=1):
            cloned = self.clone_item_for_list(item, list_id, index)
            cloned_items.append(cloned)
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
        return cloned_items

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
            preserved_scans: dict[str, int] = {}
            existing_keys: set[str] = set()
            for row in con.execute("SELECT source_id, order_no, item_no, scanned_qty FROM line_items WHERE list_id = ?", (list_id,)).fetchall():
                scanned_qty = int(row["scanned_qty"] or 0)
                source_key = str(row["source_id"])
                order_item_key = f"{row['order_no']}-{str(row['item_no']).zfill(3)}"
                existing_keys.update({source_key, order_item_key})
                preserved_scans[source_key] = max(preserved_scans.get(source_key, 0), scanned_qty)
                preserved_scans[order_item_key] = max(
                    preserved_scans.get(order_item_key, 0),
                    scanned_qty,
                )
            con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
            cloned_items = self.insert_line_items(con, list_id, items)
            for cloned in cloned_items:
                order_item_key = f"{cloned['order_no']}-{cloned['item_no']}"
                preserved = preserved_scans.get(cloned["source_id"], preserved_scans.get(order_item_key, 0))
                if preserved:
                    con.execute(
                        "UPDATE line_items SET scanned_qty = ? WHERE id = ?",
                        (min(int(preserved), int(cloned["qty"])), cloned["id"]),
                    )
                elif existing and cloned["source_id"] not in existing_keys and order_item_key not in existing_keys:
                    next_state = " ".join(part for part in [cloned["process_state"], "New Line"] if part).strip()
                    con.execute("UPDATE line_items SET process_state = ? WHERE id = ?", (next_state, cloned["id"]))

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

    def seed_customer_route_rules(self, con: sqlite3.Connection) -> None:
        created = now_iso()
        for customer, route in DEFAULT_CUSTOMER_ROUTE_RULES:
            con.execute(
                """
                INSERT OR IGNORE INTO customer_route_rules (customer_pattern, route, active, created_at)
                VALUES (?, ?, 1, ?)
                """,
                (customer, route, created),
            )

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

    def list_timing_metrics(self, con: sqlite3.Connection, list_id: str, delivery_date: str) -> dict[str, Any]:
        rows = con.execute(
            """
            SELECT li.id, li.qty, li.scanned_qty,
                   MAX(CASE WHEN se.qty_delta > 0 THEN se.created_at ELSE NULL END) AS last_scanned_at
            FROM line_items li
            LEFT JOIN scan_events se ON se.line_item_id = li.id AND se.list_id = li.list_id
            WHERE li.list_id = ?
            GROUP BY li.id
            """,
            (list_id,),
        ).fetchall()
        on_time_qty = 0
        late_qty = 0
        delivery_key = str(delivery_date or "")
        for row in rows:
            scanned = max(0, min(int(row["scanned_qty"] or 0), int(row["qty"] or 0)))
            if not scanned:
                continue
            scan_key = str(row["last_scanned_at"] or "")[:10]
            if scan_key and delivery_key and scan_key <= delivery_key:
                on_time_qty += scanned
            else:
                late_qty += scanned
        scanned_qty = on_time_qty + late_qty
        return {
            "onTimeQty": on_time_qty,
            "lateQty": late_qty,
            "onTimePercent": (on_time_qty / scanned_qty * 100) if scanned_qty else 0,
        }

    def get_delivery_lists(self, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT dl.*,
                       COALESCE(SUM(li.qty), 0) AS total_qty,
                       COALESCE(SUM(li.scanned_qty), 0) AS scanned_qty,
                       COUNT(li.id) AS item_count,
                       GROUP_CONCAT(DISTINCT CASE WHEN li.product <> '' THEN li.product ELSE li.job END) AS glass_types
                FROM delivery_lists dl
                LEFT JOIN line_items li ON li.list_id = dl.id
                WHERE dl.status = 'active'
                GROUP BY dl.id
                HAVING COUNT(li.id) > 0
                ORDER BY dl.delivery_date DESC, dl.label
                """
            ).fetchall()
            result = []
            for row in rows:
                meta = list_meta(row)
                total_qty = int(row["total_qty"] or 0)
                scanned_qty = int(row["scanned_qty"] or 0)
                meta.update(
                    {
                        "totalQty": total_qty,
                        "scannedQty": scanned_qty,
                        "itemCount": row["item_count"],
                        "glassTypes": [value for value in str(row["glass_types"] or "").split(",") if value],
                        "deliveryPercent": (scanned_qty / total_qty * 100) if total_qty else 0,
                    }
                )
                meta.update(self.list_timing_metrics(con, row["id"], row["delivery_date"]))
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

    def rename_station(self, old_name: str, new_name: str) -> dict[str, Any]:
        clean_old = " ".join(str(old_name or "").split())[:80]
        clean_new = " ".join(str(new_name or "").split())[:80]
        if not clean_old or not clean_new:
            raise ValueError("Old and new station names are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute("SELECT name FROM stations WHERE name = ?", (clean_old,)).fetchone()
            if not existing:
                raise ValueError("Station not found")
            con.execute("UPDATE stations SET name = ? WHERE name = ?", (clean_new, clean_old))
            con.execute("UPDATE scan_events SET station = ? WHERE station = ?", (clean_new, clean_old))
            con.execute("UPDATE audit_events SET station = ? WHERE station = ?", (clean_new, clean_old))
            self.insert_audit(con, "station", clean_new, "rename_station", "admin", clean_new, clean_old, {"oldName": clean_old})
            con.commit()
        return {"stations": self.get_stations(), "station": clean_new, "oldStation": clean_old}

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

    def reactivate_user(self, username: str, activated_by: str = "system") -> dict[str, Any]:
        clean_username = str(username or "").strip()
        if not clean_username:
            raise ValueError("username is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_user_by_username(con, clean_username)
            if not row:
                raise ValueError("User not found")
            con.execute("UPDATE users SET active = 1 WHERE id = ?", (row["id"],))
            self.insert_audit(con, "user", clean_username, "reactivate_user", activated_by, "", "")
            con.commit()
        return {"users": self.list_users(), "username": clean_username}

    def update_user_password(self, username: str, password: str, updated_by: str = "system") -> dict[str, Any]:
        clean_username = str(username or "").strip()
        if not clean_username or not password:
            raise ValueError("username and password are required")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_user_by_username(con, clean_username)
            if not row:
                raise ValueError("User not found")
            con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), row["id"]))
            con.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
            self.insert_audit(con, "user", clean_username, "update_user_password", updated_by, "", "")
            con.commit()
        return {"users": self.list_users(), "username": clean_username}

    def update_user_roles(self, username: str, roles: list[str], updated_by: str = "system") -> dict[str, Any]:
        clean_username = str(username or "").strip()
        clean_roles = [str(role).strip() for role in roles if str(role).strip()]
        if not clean_username or not clean_roles:
            raise ValueError("username and at least one role are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            user_row = self.get_user_by_username(con, clean_username)
            if not user_row:
                raise ValueError("User not found")
            role_ids = []
            for role_name in clean_roles:
                role = con.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
                if not role:
                    raise ValueError(f"Unknown role: {role_name}")
                role_ids.append(role["id"])
            con.execute("DELETE FROM user_roles WHERE user_id = ?", (user_row["id"],))
            for role_id in role_ids:
                con.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_row["id"], role_id))
            con.execute("DELETE FROM sessions WHERE user_id = ?", (user_row["id"],))
            self.insert_audit(con, "user", clean_username, "update_user_roles", updated_by, "", "", {"roles": clean_roles})
            con.commit()
        return {"users": self.list_users(), "username": clean_username, "roles": clean_roles}

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

    def get_customer_route_rules(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM customer_route_rules WHERE active = 1 ORDER BY route, customer_pattern"
            ).fetchall()
        return [
            {
                "id": row["id"],
                "customerPattern": row["customer_pattern"],
                "route": row["route"],
                "active": bool(row["active"]),
            }
            for row in rows
        ]

    def add_customer_route_rule(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        customer = " ".join(str(data.get("customerPattern") or data.get("customer") or "").split())[:160]
        route = str(data.get("route") or "").strip().upper()[:12]
        if route == "CUSTOMER PICKUP":
            route = "CPU"
        if route not in {"CPU", "DTC", "GNV"}:
            raise ValueError("Route rule must be CPU, DTC, or GNV")
        if not customer:
            raise ValueError("Customer pattern is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO customer_route_rules (customer_pattern, route, active, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(customer_pattern) DO UPDATE SET
                    route = excluded.route,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (customer, route, now_iso(), now_iso()),
            )
            self.insert_audit(con, "customer_route_rule", customer, "upsert_customer_route_rule", user, "", "", {"route": route})
            con.commit()
        return {"rules": self.get_customer_route_rules()}

    def remove_customer_route_rule(self, rule_id: int, user: str) -> dict[str, Any]:
        if not rule_id:
            raise ValueError("ruleId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM customer_route_rules WHERE id = ?", (rule_id,)).fetchone()
            if not row:
                raise ValueError("Customer route rule not found")
            con.execute("UPDATE customer_route_rules SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), rule_id))
            self.insert_audit(con, "customer_route_rule", str(rule_id), "remove_customer_route_rule", user, "", "", {"customer": row["customer_pattern"]})
            con.commit()
        return {"rules": self.get_customer_route_rules()}

    def route_from_customer_rules(self, item: dict[str, Any], rules: list[dict[str, Any]]) -> str:
        signal = " ".join(str(item.get(key, "")) for key in ("customer", "job", "product", "route"))
        for rule in rules:
            if fuzzy_contains(signal, rule.get("customerPattern", "")):
                return str(rule.get("route") or "").strip().upper()
        return ""

    def apply_customer_route_rules_to_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        rules = self.get_customer_route_rules()
        if not rules:
            return payload
        next_payload = dict(payload)
        next_items = []
        for item in payload.get("items") or []:
            next_item = dict(item)
            explicit = inferred_route(next_item)
            if not explicit:
                ruled_route = self.route_from_customer_rules(next_item, rules)
                if ruled_route:
                    next_item["route"] = ruled_route
            else:
                next_item["route"] = explicit
            next_items.append(next_item)
        next_payload["items"] = next_items
        return next_payload

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
        payload = self.apply_customer_route_rules_to_payload(payload)
        user = request_user_name(data)
        source_name = str(data.get("fileName") or data.get("sourceName") or "").strip()[:255]
        source_path = str(data.get("sourcePath") or "").strip()
        source_hash = str(data.get("sourceHash") or "").strip()
        import_kind = str(data.get("importKind") or "manual").strip()[:40]
        definitions = build_delivery_lists(payload)
        base_items = payload.get("items") or []
        delivery_date = str(payload["deliveryDate"])
        definition_ids = [definition[0] for definition in definitions]
        stale_profile_ids = [list_id for list_id in all_profile_list_ids(delivery_date) if list_id not in definition_ids]
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing_list_ids = {
                row["id"]
                for row in con.execute(
                    "SELECT id FROM delivery_lists WHERE id IN ({})".format(",".join("?" for _ in definitions)),
                    definition_ids,
                ).fetchall()
            }
            if stale_profile_ids:
                con.execute(
                    "UPDATE delivery_lists SET status = 'inactive' WHERE id IN ({})".format(",".join("?" for _ in stale_profile_ids)),
                    stale_profile_ids,
                )
            con.execute(
                """
                INSERT INTO imports (
                    delivery_date, source_name, row_count, total_qty, cpu_count,
                    mirror_count, status, imported_by, imported_at, source_path,
                    source_hash, import_kind
                )
                VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?, ?, ?, ?)
                """,
                (
                    delivery_date,
                    source_name,
                    len(base_items),
                    sum(int(item.get("qty") or 0) for item in base_items),
                    sum(1 for item in base_items if is_cpu_item(item)),
                    sum(1 for item in base_items if "MIRROR" in str(item.get("product", "")).upper()),
                    user,
                    now_iso(),
                    source_path,
                    source_hash,
                    import_kind,
                ),
            )
            changed_list_ids: list[str] = []
            for list_id, label, stage, scanner, items in definitions:
                self.upsert_delivery_list(con, list_id, label, str(payload["deliveryDate"]), stage, scanner, items, replace_items=True)
                changed_list_ids.append(list_id)
                self.insert_event(con, list_id, None, "IMPORT", "", user, scanner, "import", "Delivery list imported")
                self.insert_audit(con, "delivery_list", list_id, "import", user, scanner, "", {"sourceName": source_name, "sourceHash": source_hash})
            con.commit()
        created_count = sum(1 for definition in definitions if definition[0] not in existing_list_ids)
        updated_count = len(definitions) - created_count
        return {
            "lists": self.get_delivery_lists(),
            "activeListId": definitions[0][0],
            "importedCount": len(definitions),
            "createdCount": created_count,
            "updatedCount": updated_count,
            "changedListIds": changed_list_ids,
            "printCandidates": self.print_candidates_from_payload(payload, changed_list_ids, source_name),
        }

    def print_candidates_from_payload(self, payload: dict[str, Any], list_ids: list[str], source_name: str) -> list[dict[str, Any]]:
        counts = print_counts_for_items(payload.get("items") or [])
        if not counts["pieceCount"]:
            return []
        return [
            {
                "sourceName": source_name,
                "deliveryDate": str(payload.get("deliveryDate") or ""),
                "listIds": list_ids,
                **counts,
            }
        ]

    def import_delivery_folder(self, data: dict[str, Any]) -> dict[str, Any]:
        user = request_user_name(data)
        folder = Path(str(data.get("sourceFolder") or self.config.temp_delivery_lists_dir)).expanduser()
        date_from = str(data.get("dateFrom") or "").strip()
        date_to = str(data.get("dateTo") or "").strip()
        if not folder.is_absolute():
            folder = self.config.root / folder
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Temp Delivery Lists folder not found: {folder}")

        imported_files: list[dict[str, Any]] = []
        updated_files: list[dict[str, Any]] = []
        skipped_files: list[dict[str, Any]] = []
        failed_files: list[dict[str, Any]] = []
        print_candidates: list[dict[str, Any]] = []
        active_list_id = ""

        for path in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_IMPORT_EXTENSIONS):
            try:
                file_date = delivery_date_from_text(path.stem)
                if file_date and date_from and file_date < date_from:
                    skipped_files.append({"fileName": path.name, "reason": f"Outside import window before {date_from}"})
                    continue
                if file_date and date_to and file_date > date_to:
                    skipped_files.append({"fileName": path.name, "reason": f"Outside import window after {date_to}"})
                    continue
                file_hash = source_file_hash(path)
                source_path = str(path.resolve())
                with self.connect() as con:
                    previous = con.execute(
                        """
                        SELECT source_hash FROM imports
                        WHERE source_path = ? OR source_name = ?
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (source_path, path.name),
                    ).fetchone()
                if previous and previous["source_hash"] == file_hash:
                    skipped_files.append({"fileName": path.name, "reason": "No changes detected"})
                    continue

                payload = load_delivery_source_payload(path)
                preview = self.preview_import(payload)
                if not preview["valid"]:
                    failed_files.append({"fileName": path.name, "errors": preview["errors"]})
                    continue

                result = self.import_delivery_list(
                    {
                        "payload": payload,
                        "fileName": path.name,
                        "sourcePath": source_path,
                        "sourceHash": file_hash,
                        "importKind": "temp_folder",
                        "user": user,
                    }
                )
                active_list_id = active_list_id or result.get("activeListId", "")
                file_result = {
                    "fileName": path.name,
                    "deliveryDate": payload["deliveryDate"],
                    "rowCount": preview["rowCount"],
                    "totalQty": preview["totalQty"],
                    "createdCount": result["createdCount"],
                    "updatedCount": result["updatedCount"],
                    "listIds": result["changedListIds"],
                }
                if result["createdCount"]:
                    imported_files.append(file_result)
                else:
                    updated_files.append(file_result)
                print_candidates.extend(result.get("printCandidates") or [])
            except Exception as exc:
                failed_files.append({"fileName": path.name, "errors": [str(exc)]})

        return {
            "ok": not failed_files or bool(imported_files or updated_files or skipped_files),
            "sourceFolder": str(folder),
            "scannedFiles": len(imported_files) + len(updated_files) + len(skipped_files) + len(failed_files),
            "importedFiles": imported_files,
            "updatedFiles": updated_files,
            "skippedFiles": skipped_files,
            "failedFiles": failed_files,
            "printCandidates": print_candidates,
            "activeListId": active_list_id,
            "lists": self.get_delivery_lists(),
        }

    def get_print_package(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        filters = filters or {}
        rush_only = str(filters.get("rushOnly") or "").lower() in {"1", "true", "yes"}
        remake_only = str(filters.get("remakeOnly") or "").lower() in {"1", "true", "yes"}
        cpu_only = str(filters.get("cpuOnly") or "").lower() in {"1", "true", "yes"}
        dtc_only = str(filters.get("dtcOnly") or "").lower() in {"1", "true", "yes"}
        updated_only = str(filters.get("updatedOnly") or "").lower() in {"1", "true", "yes"}
        glass_type = str(filters.get("glassType") or "").strip().lower()
        mirror_mode = str(filters.get("mirrorMode") or "exclude").strip().lower()
        customer_filter = str(filters.get("customers") or "").strip().lower()
        order_filter = str(filters.get("orders") or "").strip()
        customer_terms = [term.strip() for term in re.split(r"[,;\n]+", customer_filter) if term.strip()]
        order_terms = [digits_only(term) for term in re.split(r"[,;\s\n]+", order_filter) if digits_only(term)]
        package_by_date: dict[str, dict[str, Any]] = {}
        for list_id in list_ids:
            try:
                payload = self.get_delivery_list(list_id, user=user)
            except (KeyError, PermissionError):
                continue
            date_key = payload["meta"]["deliveryDate"]
            bucket = package_by_date.setdefault(
                date_key,
                {
                    "id": date_key,
                    "label": f"Delivery List for {format_display_date(date_key)}",
                    "stage": "All stages",
                    "deliveryDate": date_key,
                    "itemsByKey": {},
                    "stages": [],
                    "excludedMirrorCount": 0,
                },
            )
            if payload["meta"]["stage"] not in bucket["stages"]:
                bucket["stages"].append(payload["meta"]["stage"])
            source_items = payload["items"]
            if mirror_mode == "include":
                printable_items = list(source_items)
            elif mirror_mode == "only":
                printable_items = [item for item in source_items if is_mirror_item(item)]
            else:
                printable_items = [item for item in source_items if should_print_delivery_item(item)]
            if rush_only:
                printable_items = [item for item in printable_items if re.search(r"\bRush\b", str(item.get("processState", "")), flags=re.IGNORECASE)]
            if remake_only:
                printable_items = [item for item in printable_items if is_remake_item(item)]
            if cpu_only:
                printable_items = [item for item in printable_items if is_cpu_item(item)]
            if dtc_only:
                printable_items = [item for item in printable_items if route_category(item) == "dtc"]
            if updated_only:
                printable_items = [
                    item
                    for item in printable_items
                    if re.search(r"\b(update|updated|new|change|changed)\b", f"{item.get('processState', '')} {item.get('queueState', '')}", flags=re.IGNORECASE)
                ]
            if glass_type:
                printable_items = [
                    item
                    for item in printable_items
                    if glass_type in f"{item.get('product', '')} {item.get('job', '')}".lower()
                ]
            if customer_terms:
                printable_items = [
                    item
                    for item in printable_items
                    if any(term in str(item.get("customer", "")).lower() for term in customer_terms)
                ]
            if order_terms:
                printable_items = [
                    item
                    for item in printable_items
                    if digits_only(str(item.get("order", ""))) in order_terms
                ]
            if not printable_items and not source_items:
                continue
            bucket["excludedMirrorCount"] += len([item for item in source_items if is_mirror_item(item) and not should_print_delivery_item(item)])
            for item in printable_items:
                key = str(item.get("sourceId") or f"{item.get('order')}-{item.get('item')}-{item.get('dimensions')}")
                bucket["itemsByKey"].setdefault(key, item)

        package_lists = []
        for bucket in package_by_date.values():
            items = sorted(
                bucket["itemsByKey"].values(),
                key=lambda item: (str(item.get("product") or item.get("job") or ""), int(item.get("order") or 0), int(item.get("item") or 0)),
            )
            if not items:
                continue
            package_lists.append(
                {
                    "id": bucket["id"],
                    "label": bucket["label"],
                    "stage": bucket["stage"],
                    "stages": bucket["stages"],
                    "deliveryDate": bucket["deliveryDate"],
                    "items": items,
                    "remakes": [item for item in items if is_remake_item(item)],
                    "rushes": [item for item in items if re.search(r"\bRush\b", str(item.get("processState", "")), flags=re.IGNORECASE)],
                    "excludedMirrorCount": bucket["excludedMirrorCount"],
                }
            )
        return {"lists": package_lists, "generatedAt": now_iso(), "filters": filters}

    def find_unique_suffix_item(self, rows: list[sqlite3.Row], suffix: str, item_no: int) -> sqlite3.Row | None:
        matches = []
        for row in rows:
            if int(row["item_no"]) == item_no and f"{int(row['order_no']):06d}".endswith(suffix):
                matches.append(row)
        return matches[0] if len(matches) == 1 else None

    def find_unique_order(self, rows: list[sqlite3.Row], order_no: int) -> sqlite3.Row | None:
        matches = [row for row in rows if int(row["order_no"]) == order_no]
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

        if clean_text.startswith("T200"):
            order_text = digits_only(clean_text[4:])
            order_candidates = []
            if len(order_text) >= 6:
                order_candidates.append(order_text[:6])
            if len(order_text) >= 7 and order_text.startswith("0"):
                order_candidates.append(order_text[1:7])
            for order_candidate in dict.fromkeys(order_candidates):
                row = self.find_unique_order(rows, int(order_candidate))
                if row:
                    return row, canonical_barcode(int(row["order_no"]), int(row["item_no"])), "Recovered order-only scan"

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

            auto_staged = self.auto_stage_for_outbound(con, list_id, row, barcode, canonical, user, station)
            if auto_staged:
                self.insert_event(
                    con,
                    list_id,
                    row["id"],
                    barcode,
                    canonical,
                    user,
                    station,
                    "notice",
                    "Auto-staged before outbound",
                    "This item was not scanned on staging, so it was auto-scanned for convenience.",
                )

            con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
            preassigned_bay = self.preassign_bay_for_outbound(con, list_id, row, user, station)
            last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "scan", reason, "", 1)
            if preassigned_bay:
                self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "notice", "Indian Trail bay preassigned", f"Preassigned to Bay {preassigned_bay}")
            self.insert_audit(con, "line_item", row["id"], "scan", user, station, reason, {"barcode": barcode, "canonical": canonical})
            con.commit()
            return self._get_payload(con, list_id, last)

    def auto_stage_for_outbound(
        self,
        con: sqlite3.Connection,
        list_id: str,
        outbound_row: sqlite3.Row,
        barcode: str,
        canonical: str,
        user: str,
        station: str,
    ) -> bool:
        current_list = con.execute("SELECT delivery_date, stage, scanner FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
        if not current_list or "outbound" not in str(current_list["stage"]).lower():
            return False
        staging_list = con.execute(
            """
            SELECT id FROM delivery_lists
            WHERE delivery_date = ?
              AND scanner = ?
              AND LOWER(stage) LIKE '%staging%'
              AND id <> ?
            ORDER BY id
            LIMIT 1
            """,
            (current_list["delivery_date"], current_list["scanner"], list_id),
        ).fetchone()
        if not staging_list:
            return False
        staging_row = con.execute(
            """
            SELECT * FROM line_items
            WHERE list_id = ?
              AND (
                source_id = ?
                OR (order_no = ? AND item_no = ?)
              )
            ORDER BY id
            LIMIT 1
            """,
            (staging_list["id"], outbound_row["source_id"], outbound_row["order_no"], outbound_row["item_no"]),
        ).fetchone()
        if not staging_row:
            return False

        target_qty = min(int(outbound_row["scanned_qty"]) + 1, int(outbound_row["qty"]))
        delta = min(target_qty - int(staging_row["scanned_qty"]), int(staging_row["qty"]) - int(staging_row["scanned_qty"]))
        if delta <= 0:
            return False

        con.execute("UPDATE line_items SET scanned_qty = scanned_qty + ? WHERE id = ?", (delta, staging_row["id"]))
        self.insert_event(
            con,
            staging_list["id"],
            staging_row["id"],
            barcode,
            canonical,
            user,
            station,
            "scan",
            "Auto-staged from outbound scan",
            "Outbound scan advanced staging automatically.",
            delta,
        )
        self.insert_audit(
            con,
            "line_item",
            staging_row["id"],
            "auto_stage_from_outbound",
            user,
            station,
            "Outbound scan advanced staging automatically.",
            {"outboundListId": list_id, "barcode": barcode, "canonical": canonical, "qtyDelta": delta},
        )
        return True

    def preassign_bay_for_outbound(self, con: sqlite3.Connection, list_id: str, outbound_row: sqlite3.Row, user: str, station: str) -> str:
        current_list = con.execute("SELECT delivery_date, stage FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
        if not current_list or "outbound" not in str(current_list["stage"]).lower():
            return ""
        row_item = {
            "route": outbound_row["route"],
            "job": outbound_row["job"],
            "customer": outbound_row["customer"],
            "product": outbound_row["product"],
            "processState": outbound_row["process_state"],
            "queueState": outbound_row["queue_state"],
        }
        if route_category(row_item) != "indian_trail":
            return ""
        inbound = con.execute(
            """
            SELECT li.*
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.delivery_date = ?
              AND dl.stage LIKE '%Indian Trail%'
              AND (li.source_id = ? OR (li.order_no = ? AND li.item_no = ?))
            ORDER BY li.id
            LIMIT 1
            """,
            (current_list["delivery_date"], outbound_row["source_id"], outbound_row["order_no"], outbound_row["item_no"]),
        ).fetchone()
        if not inbound:
            return ""
        existing = con.execute(
            "SELECT 1 FROM bay_assignments WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled') LIMIT 1",
            (inbound["id"],),
        ).fetchone()
        if existing:
            return ""
        bay_type = suggested_bay(inbound["product"], inbound["dimensions"], inbound["route"])
        bay = self.find_bay_for_assignment(con, bay_type) or self.find_bay_for_assignment(con, "Standard")
        if not bay:
            self.insert_exception(con, inbound["list_id"], None, "bay_assignment_conflict", "No safe bay available during outbound preassign")
            return ""
        con.execute(
            """
            INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
            VALUES (?, ?, ?, 1, 'PreAssigned', ?, ?, 'Preassigned from outbound scan')
            """,
            (inbound["list_id"], inbound["id"], bay["id"], user, now_iso()),
        )
        self.insert_bay_event(con, bay["id"], inbound["id"], "PreAssignBay", user, "Preassigned from outbound scan", new_bay_id=bay["id"])
        self.insert_audit(con, "bay_assignment", inbound["id"], "preassign_bay_from_outbound", user, station, "", {"bayCode": bay["bay_code"]})
        return str(bay["bay_code"])

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

    def redo_last_undo(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                """
                SELECT se.*, li.qty, li.scanned_qty
                FROM scan_events se
                JOIN line_items li ON li.id = se.line_item_id
                WHERE se.list_id = ? AND se.event_type IN ('undo', 'scan') AND se.line_item_id IS NOT NULL
                ORDER BY se.id DESC
                LIMIT 1
                """,
                (list_id,),
            ).fetchone()
            if not row or row["event_type"] != "undo":
                last = self.insert_event(con, list_id, None, "REDO", "", user, station, "error", "Nothing to redo")
                con.commit()
                return self._get_payload(con, list_id, last)
            if int(row["scanned_qty"] or 0) >= int(row["qty"] or 0):
                last = self.insert_event(con, list_id, row["line_item_id"], row["barcode"], row["canonical_barcode"], user, station, "duplicate", "Redo blocked", "Quantity already scanned")
                con.commit()
                return self._get_payload(con, list_id, last)
            con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["line_item_id"],))
            last = self.insert_event(
                con,
                list_id,
                row["line_item_id"],
                row["barcode"],
                row["canonical_barcode"],
                user,
                station,
                "scan",
                "Undo redone",
                "Last undo was re-applied",
                1,
            )
            self.insert_audit(con, "line_item", row["line_item_id"], "redo_scan", user, station, "Last undo was re-applied")
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
        if isinstance(payload, dict):
            payload = self.apply_customer_route_rules_to_payload(payload)
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
            list_count = con.execute(
                "SELECT COUNT(*) FROM delivery_lists dl WHERE dl.status = 'active' AND EXISTS (SELECT 1 FROM line_items li WHERE li.list_id = dl.id)"
            ).fetchone()[0]
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
            "tempDeliveryListsDir": str(self.config.temp_delivery_lists_dir),
            "authMode": self.config.auth_mode,
            "environment": self.config.environment,
            "recentImports": [
                {
                    "id": row["id"],
                    "deliveryDate": row["delivery_date"],
                    "sourceName": row["source_name"],
                    "sourcePath": row["source_path"],
                    "importKind": row["import_kind"],
                    "rowCount": row["row_count"],
                    "totalQty": row["total_qty"],
                    "importedBy": row["imported_by"],
                    "importedAt": row["imported_at"],
                    "listIds": [f"{row['delivery_date']}-{suffix}" for suffix, _, _, _ in LIST_PROFILES],
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
                SELECT li.*, dl.stage, dl.scanner, dl.label, dl.delivery_date,
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
        def stage_location_rank(row: sqlite3.Row) -> int:
            scanned = int(row["scanned_qty"] or 0)
            stage = f"{row['stage']} {row['scanner']}".lower()
            if row["bay_code"]:
                return 100
            if not scanned:
                return 0
            if "indian trail" in stage or "inbound" in stage:
                return 90
            if "dtc" in stage or "deliver to customer" in stage:
                return 86
            if "customer pickup" in stage:
                return 84
            if "greenville" in stage:
                return 82
            if "outbound" in stage:
                return 70
            if "staging" in stage:
                return 60
            return 50

        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            if user is not None and not user_can_access_stage(user, row["stage"], row["scanner"]):
                continue
            key = f"{row['delivery_date']}::{row['order_no']}::{row['item_no']}"
            rank = stage_location_rank(row)
            result = grouped.setdefault(key, {
                "lineItemId": row["id"],
                "deliveryListId": row["list_id"],
                "deliveryList": row["label"],
                "deliveryDate": row["delivery_date"],
                "stage": row["stage"],
                "scanner": row["scanner"],
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
                "processState": row["process_state"],
                "queueState": row["queue_state"],
                "bay": row["bay_display_name"] or row["bay_code"],
                "bayCode": row["bay_code"],
                "bayStatus": row["bay_status"],
                "lastScanTime": row["last_scan_time"],
                "lastScanUser": row["last_scan_user"],
                "stageLocations": [],
                "locationText": "",
                "_rank": -1,
            })
            if rank >= int(result.get("_rank", -1)):
                result["deliveryListId"] = row["list_id"]
                result["deliveryList"] = row["label"]
                result["lineItemId"] = row["id"]
                result["stage"] = row["stage"]
                result["scanner"] = row["scanner"]
                result["scanned"] = row["scanned_qty"]
                result["processState"] = row["process_state"]
                result["queueState"] = row["queue_state"]
                result["bay"] = row["bay_display_name"] or row["bay_code"]
                result["bayCode"] = row["bay_code"]
                result["bayStatus"] = row["bay_status"]
                result["_rank"] = rank
            scanned = int(row["scanned_qty"] or 0)
            qty = int(row["qty"] or 0)
            if row["bay_code"]:
                location = f"{row['stage']}: Bay {row['bay_display_name'] or row['bay_code']}"
            elif scanned >= qty and qty:
                location = f"{row['stage']}: complete"
            elif scanned:
                location = f"{row['stage']}: {scanned}/{qty}"
            else:
                location = f"{row['stage']}: not scanned"
            if rank >= int(result.get("_rank", -1)):
                result["locationText"] = location
            if location not in result["stageLocations"]:
                result["stageLocations"].append(location)
        for result in grouped.values():
            if int(result.get("_rank", 0)) == 0:
                result["locationText"] = "Process Not Started"
            result.pop("_rank", None)
        return list(grouped.values())[:30]

    def update_line_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        line_item_id = str(data.get("lineItemId") or "")
        if not line_item_id:
            raise ValueError("lineItemId is required")
        allowed_fields = {
            "order": "order_no",
            "item": "item_no",
            "barcode": "barcode",
            "qty": "qty",
            "scanned": "scanned_qty",
            "dimensions": "dimensions",
            "customer": "customer",
            "route": "route",
            "job": "job",
            "product": "product",
            "processState": "process_state",
            "queueState": "queue_state",
            "suggestedBay": "suggested_bay",
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
                    if column == "item_no":
                        value = str(parse_int_text(value) or value).zfill(3)
                    elif column == "order_no":
                        value = str(parse_int_text(value) or value)
                updates.append(f"{column} = ?")
                params.append(value)
            if ("order" in data or "item" in data) and "barcode" not in data:
                next_order = str(parse_int_text(data.get("order", row["order_no"])) or row["order_no"])
                next_item = str(parse_int_text(data.get("item", row["item_no"])) or row["item_no"]).zfill(3)
                updates.append("barcode = ?")
                params.append(canonical_barcode(next_order, next_item))
            if updates:
                params.append(line_item_id)
                con.execute(f"UPDATE line_items SET {', '.join(updates)} WHERE id = ?", params)
                self.insert_audit(con, "line_item", line_item_id, "manual_edit", user, "", "", {"fields": list(data.keys())})
            con.commit()
            return self._get_payload(con, row["list_id"])

    def delete_line_item(self, line_item_id: str, user: str) -> dict[str, Any]:
        clean_id = str(line_item_id or "").strip()
        if not clean_id:
            raise ValueError("lineItemId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM line_items WHERE id = ?", (clean_id,)).fetchone()
            if not row:
                raise ValueError("Line item not found")
            con.execute("UPDATE bay_assignments SET status = 'Cancelled', reason = 'Line item deleted' WHERE line_item_id = ?", (clean_id,))
            con.execute("DELETE FROM line_items WHERE id = ?", (clean_id,))
            self.insert_audit(con, "line_item", clean_id, "delete_line_item", user, "", "Deleted from admin page")
            con.commit()
            return self._get_payload(con, row["list_id"])

    def delete_delivery_list(self, list_id: str, user: str) -> dict[str, Any]:
        clean_id = str(list_id or "").strip()
        if not clean_id:
            raise ValueError("listId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (clean_id,)).fetchone()
            if not row:
                raise ValueError("Delivery list not found")
            con.execute("UPDATE bay_assignments SET status = 'Cancelled', reason = 'Delivery list deleted' WHERE delivery_list_id = ?", (clean_id,))
            con.execute("DELETE FROM delivery_lists WHERE id = ?", (clean_id,))
            self.insert_audit(con, "delivery_list", clean_id, "delete_delivery_list", user, row["scanner"], "Deleted from admin page")
            con.commit()
        return {"ok": True, "deletedListId": clean_id, "lists": self.get_delivery_lists()}

    def delete_delivery_date(self, delivery_date: str, user: str) -> dict[str, Any]:
        clean_date = str(delivery_date or "").strip()
        if not clean_date:
            raise ValueError("deliveryDate is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT id FROM delivery_lists WHERE delivery_date = ?", (clean_date,)).fetchall()
            list_ids = [row["id"] for row in rows]
            if not list_ids:
                raise ValueError("No delivery lists found for that date")
            placeholders = ",".join("?" for _ in list_ids)
            con.execute(f"UPDATE bay_assignments SET status = 'Cancelled', reason = 'Delivery date deleted' WHERE delivery_list_id IN ({placeholders})", list_ids)
            con.execute(f"DELETE FROM delivery_lists WHERE id IN ({placeholders})", list_ids)
            self.insert_audit(con, "delivery_date", clean_date, "delete_delivery_date", user, "", "Deleted from admin page", {"listIds": list_ids})
            con.commit()
        return {"ok": True, "deliveryDate": clean_date, "deletedCount": len(list_ids), "lists": self.get_delivery_lists()}

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
                   li.dimensions, li.product, li.job, li.process_state, li.queue_state
            FROM bay_assignments ba
            JOIN line_items li ON li.id = ba.line_item_id
            WHERE ba.bay_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
            ORDER BY ba.assigned_at DESC
            """,
            (row["id"],),
        ).fetchall()
        assigned_qty = sum(int(item["assigned_qty"] or 0) for item in assignments)
        bay_status = str(row["status"] or "Available")
        if bay_status in {"Blocked", "Hold"}:
            status = bay_status
        elif any(item["status"] == "SDIOverride" for item in assignments):
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
            "sourceStatus": bay_status,
            "active": bool(row["active"]),
            "assignments": [
                {
                    "id": item["id"],
                    "deliveryListId": item["delivery_list_id"],
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
                    "processState": item["process_state"],
                    "queueState": item["queue_state"],
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

    def get_bay_events(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 20), 100))
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT be.*,
                       b.bay_code AS bay_code,
                       b.display_name AS bay_display,
                       old_bay.bay_code AS old_bay_code,
                       old_bay.display_name AS old_bay_display,
                       new_bay.bay_code AS new_bay_code,
                       new_bay.display_name AS new_bay_display,
                       li.order_no, li.item_no, li.customer, li.dimensions, li.product
                FROM bay_events be
                LEFT JOIN bays b ON b.id = be.bay_id
                LEFT JOIN bays old_bay ON old_bay.id = be.old_bay_id
                LEFT JOIN bays new_bay ON new_bay.id = be.new_bay_id
                LEFT JOIN line_items li ON li.id = be.line_item_id
                ORDER BY be.id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "eventType": row["event_type"],
                "bayCode": row["bay_code"] or "",
                "bayDisplay": row["bay_display"] or row["bay_code"] or "",
                "oldBayCode": row["old_bay_code"] or "",
                "oldBayDisplay": row["old_bay_display"] or row["old_bay_code"] or "",
                "newBayCode": row["new_bay_code"] or "",
                "newBayDisplay": row["new_bay_display"] or row["new_bay_code"] or "",
                "order": row["order_no"] or "",
                "item": row["item_no"] or "",
                "customer": row["customer"] or "",
                "dimensions": row["dimensions"] or "",
                "product": row["product"] or "",
                "reason": row["reason"] or "",
                "user": row["user_name"] or "",
                "time": row["created_at"],
            }
            for row in rows
        ]

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
            WHERE b.active = 1 AND b.bay_type = ? AND COALESCE(b.status, 'Available') = 'Available'
            GROUP BY b.id
            HAVING used_qty < b.capacity_qty OR b.capacity_qty = 0
            ORDER BY used_qty, b.sort_order
            LIMIT 1
            """,
            (bay_type,),
        ).fetchone()
        return rows

    def get_bay_by_code(self, con: sqlite3.Connection, bay_code: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM bays WHERE bay_code = ? AND active = 1 AND COALESCE(status, 'Available') != 'Blocked'", (bay_code,)).fetchone()
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
        requested_bay_code = str(data.get("bayCode") or "").strip()
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
                bay = self.get_bay_by_code(con, requested_bay_code) if requested_bay_code else (self.find_bay_for_assignment(con, bay_type) or self.find_bay_for_assignment(con, "Standard"))
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

    def clear_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        reason = str(data.get("reason") or "Assignment cleared").strip()
        if not assignment_id:
            raise ValueError("assignmentId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not row:
                raise ValueError("Assignment not found")
            con.execute(
                "UPDATE bay_assignments SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ? WHERE id = ?",
                (user, now_iso(), reason, assignment_id),
            )
            self.insert_bay_event(con, row["bay_id"], row["line_item_id"], "ClearAssignment", user, reason, old_bay_id=row["bay_id"])
            self.insert_audit(con, "bay_assignment", str(assignment_id), "clear_bay_assignment", user, "", reason)
            con.commit()
        return {"ok": True, "assignmentId": assignment_id}

    def restore_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        reason = str(data.get("reason") or "Assignment restored").strip()
        if not assignment_id:
            raise ValueError("assignmentId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not row:
                raise ValueError("Assignment not found")
            bay = con.execute("SELECT * FROM bays WHERE id = ?", (row["bay_id"],)).fetchone()
            if not bay:
                raise ValueError("Assignment bay not found")
            con.execute(
                "UPDATE bay_assignments SET status = 'Assigned', cleared_by = NULL, cleared_at = NULL, reason = ? WHERE id = ?",
                (reason, assignment_id),
            )
            self.insert_bay_event(con, row["bay_id"], row["line_item_id"], "RestoreAssignment", user, reason, new_bay_id=row["bay_id"])
            self.insert_audit(con, "bay_assignment", str(assignment_id), "restore_bay_assignment", user, "", reason)
            con.commit()
        return {"ok": True, "assignmentId": assignment_id, "bayCode": bay["bay_code"]}

    def set_bay_status(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        bay_code = str(data.get("bayCode") or "").strip()
        status = str(data.get("status") or "Available").strip().title()
        reason = str(data.get("reason") or f"Bay set to {status}").strip()
        if status not in {"Available", "Hold", "Blocked"}:
            raise ValueError("Bay status must be Available, Hold, or Blocked")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            bay = self.get_bay_by_code(con, bay_code) if status != "Available" else con.execute("SELECT * FROM bays WHERE bay_code = ?", (bay_code,)).fetchone()
            if not bay:
                raise ValueError(f"Unknown bay: {bay_code}")
            active = 0 if status == "Blocked" else 1
            con.execute("UPDATE bays SET status = ?, active = ? WHERE id = ?", (status, active, bay["id"]))
            self.insert_bay_event(con, bay["id"], "", f"{status}Bay", user, reason)
            self.insert_audit(con, "bay", bay_code, f"set_bay_{status.lower()}", user, "", reason)
            con.commit()
        return {"ok": True, "bayCode": bay_code, "status": status, "bays": self.get_bays()}

    def scan_out_bay_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        barcode = str(data.get("barcode") or data.get("scan") or "").strip()
        bay_code_filter = str(data.get("bayCode") or "").strip()
        if not barcode:
            raise ValueError("Scan barcode is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            assignments = con.execute(
                """
                SELECT ba.*, li.barcode, li.order_no, li.item_no, li.customer, b.bay_code, b.display_name
                FROM bay_assignments ba
                JOIN line_items li ON li.id = ba.line_item_id
                JOIN bays b ON b.id = ba.bay_id
                WHERE ba.status NOT IN ('Cleared', 'Cancelled')
                  AND (? = '' OR b.bay_code = ? OR b.display_name = ?)
                """
                ,
                (bay_code_filter, bay_code_filter, bay_code_filter),
            ).fetchall()
            row = None
            clean = clean_barcode(barcode)
            digits = digits_only(clean)
            for assignment in assignments:
                if clean and clean == clean_barcode(assignment["barcode"]):
                    row = assignment
                    break
                if assignment["order_no"] in barcode and assignment["item_no"].lstrip("0") in digits:
                    row = assignment
                    break
            if not row:
                raise ValueError("No active bay assignment matched that scan")
            con.execute(
                "UPDATE bay_assignments SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ? WHERE id = ?",
                (user, now_iso(), "Scanned out from bay map", row["id"]),
            )
            self.insert_bay_event(con, row["bay_id"], row["line_item_id"], "ScanOutBay", user, "Scanned out from bay map", old_bay_id=row["bay_id"])
            self.insert_audit(con, "bay_assignment", str(row["id"]), "scan_out_bay", user, "", "Scanned out from bay map")
            con.commit()
        return {
            "ok": True,
            "assignmentId": row["id"],
            "bayCode": row["bay_code"],
            "bayDisplay": row["display_name"] or row["bay_code"],
            "order": row["order_no"],
            "item": row["item_no"],
            "customer": row["customer"],
        }

    def update_bay_layout(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        bay_code = str(data.get("bayCode") or "").strip()
        if not bay_code:
            raise ValueError("bayCode is required")
        display_name = " ".join(str(data.get("displayName") or bay_code).split())[:120]
        map_section = " ".join(str(data.get("mapSection") or "").split())[:120]
        bay_category = " ".join(str(data.get("bayCategory") or "").split())[:120]
        layout_row = int(data.get("layoutRow") or 0) or None
        layout_col = int(data.get("layoutCol") or 0) or None
        capacity = int(data.get("capacityQty") or 0)
        active = 1 if data.get("active") in {True, "1", "true", "yes", 1} else 0
        insert_before = str(data.get("insertBeforeBayCode") or "").strip()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM bays WHERE bay_code = ?", (bay_code,)).fetchone()
            if not row:
                raise ValueError(f"Unknown bay: {bay_code}")
            if insert_before:
                target = con.execute("SELECT * FROM bays WHERE bay_code = ?", (insert_before,)).fetchone()
                if target:
                    layout_row = int(target["layout_row"] or layout_row or 1)
                    layout_col = int(target["layout_col"] or layout_col or 1)
                    con.execute(
                        """
                        UPDATE bays
                        SET layout_col = COALESCE(layout_col, 0) + 1
                        WHERE id <> ?
                          AND map_section = ?
                          AND COALESCE(layout_row, 0) = ?
                          AND COALESCE(layout_col, 0) >= ?
                        """,
                        (row["id"], map_section, layout_row, layout_col),
                    )
            con.execute(
                """
                UPDATE bays
                SET display_name = ?, map_section = ?, bay_category = ?,
                    layout_row = ?, layout_col = ?, capacity_qty = ?, active = ?
                WHERE id = ?
                """,
                (display_name, map_section, bay_category, layout_row, layout_col, capacity, active, row["id"]),
            )
            self.insert_bay_event(con, row["id"], "", "UpdateBayLayout", user, "Bay layout updated")
            self.insert_audit(con, "bay", bay_code, "update_bay_layout", user, "", "", data)
            con.commit()
        return {"ok": True, "bayCode": bay_code, "bays": self.get_bays()}

    def set_bay_group_position(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        map_section = " ".join(str(data.get("mapSection") or "").split())[:120]
        layout_row = int(data.get("layoutRow") or 0)
        layout_col = int(data.get("layoutCol") or 0)
        if not map_section or not layout_row or not layout_col:
            raise ValueError("mapSection, layoutRow, and layoutCol are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT * FROM bays WHERE map_section = ?", (map_section,)).fetchall()
            if not rows:
                raise ValueError("Bay group not found")
            con.execute("UPDATE bays SET layout_row = ?, layout_col = ? WHERE map_section = ?", (layout_row, layout_col, map_section))
            for row in rows:
                self.insert_bay_event(con, row["id"], "", "UpdateBayLayout", user, "Bay group layout updated")
            self.insert_audit(con, "bay_group", map_section, "set_bay_group_position", user, "", "", {"layoutRow": layout_row, "layoutCol": layout_col})
            con.commit()
        return {"ok": True, "mapSection": map_section, "bays": self.get_bays()}

    def create_bays(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        map_section = " ".join(str(data.get("mapSection") or data.get("group") or "").split())[:120]
        bay_category = " ".join(str(data.get("bayCategory") or data.get("category") or "Standard").split())[:120]
        prefix = " ".join(str(data.get("prefix") or map_section or bay_category or "BAY").split())[:60]
        count = max(1, min(int(data.get("count") or 1), 100))
        spacer = bool(data.get("spacer"))
        if not map_section:
            raise ValueError("Bay group is required")
        safe_prefix = re.sub(r"[^A-Z0-9]+", "-", prefix.upper()).strip("-") or "BAY"
        created: list[str] = []
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing_codes = {row["bay_code"] for row in con.execute("SELECT bay_code FROM bays").fetchall()}
            existing_in_group = con.execute("SELECT COALESCE(MAX(sort_order), 0) FROM bays WHERE map_section = ?", (map_section,)).fetchone()[0]
            for index in range(1, count + 1):
                next_number = int(existing_in_group or 0) + index
                bay_code = f"{safe_prefix}-{next_number:02d}"
                while bay_code in existing_codes:
                    next_number += 1
                    bay_code = f"{safe_prefix}-{next_number:02d}"
                existing_codes.add(bay_code)
                con.execute(
                    """
                    INSERT INTO bays (
                        bay_code, area, bay_type, capacity_qty, sort_order, active,
                        display_name, map_section, bay_category, layout_row, layout_col
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bay_code,
                        map_section,
                        "Spacer" if spacer else "Standard",
                        0 if spacer else 1,
                        next_number,
                        0 if spacer else 1,
                        "Spacer" if spacer else bay_code,
                        map_section,
                        "Spacer" if spacer else bay_category,
                        next_number,
                        next_number,
                    ),
                )
                bay_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                self.insert_bay_event(con, bay_id, "", "CreateBay", user, "Bay created")
                created.append(bay_code)
            self.insert_audit(con, "bay", map_section, "create_bays", user, "", "", {"created": created, "category": bay_category})
            con.commit()
        return {"ok": True, "created": created, "bays": self.get_bays()}

    def delete_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        bay_code = str(data.get("bayCode") or "").strip()
        if not bay_code:
            raise ValueError("bayCode is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM bays WHERE bay_code = ?", (bay_code,)).fetchone()
            if not row:
                raise ValueError("Bay not found")
            active_assignment = con.execute(
                "SELECT 1 FROM bay_assignments WHERE bay_id = ? AND status NOT IN ('Cleared', 'Cancelled') LIMIT 1",
                (row["id"],),
            ).fetchone()
            if active_assignment:
                raise ValueError("Clear or move active assignments before deleting this bay")
            con.execute("UPDATE bays SET active = 0 WHERE id = ?", (row["id"],))
            self.insert_bay_event(con, row["id"], "", "DeleteBay", user, "Bay deleted")
            self.insert_audit(con, "bay", bay_code, "delete_bay", user, "", "", {})
            con.commit()
        return {"ok": True, "bayCode": bay_code, "bays": self.get_bays()}

    def delete_bay_group(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        map_section = " ".join(str(data.get("mapSection") or data.get("group") or "").split())[:120]
        if not map_section:
            raise ValueError("Bay group is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            active_assignment = con.execute(
                """
                SELECT 1
                FROM bay_assignments ba
                JOIN bays b ON b.id = ba.bay_id
                WHERE b.map_section = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
                LIMIT 1
                """,
                (map_section,),
            ).fetchone()
            if active_assignment:
                raise ValueError("Clear or move active assignments before deleting this group")
            rows = con.execute("SELECT id, bay_code FROM bays WHERE map_section = ? AND active = 1", (map_section,)).fetchall()
            con.execute("UPDATE bays SET active = 0 WHERE map_section = ?", (map_section,))
            for row in rows:
                self.insert_bay_event(con, row["id"], "", "DeleteBayGroup", user, "Bay group deleted")
            self.insert_audit(con, "bay_group", map_section, "delete_bay_group", user, "", "", {"count": len(rows)})
            con.commit()
        return {"ok": True, "mapSection": map_section, "deletedCount": len(rows), "bays": self.get_bays()}

    def move_bay_group(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        map_section = " ".join(str(data.get("mapSection") or "").split())[:120]
        target_section = " ".join(str(data.get("targetMapSection") or "").split())[:120]
        row_delta = int(data.get("rowDelta") or 0)
        col_delta = int(data.get("colDelta") or 0)
        if not map_section:
            raise ValueError("mapSection is required")
        if target_section and target_section == map_section:
            return {"ok": True, "mapSection": map_section, "moved": 0, "bays": self.get_bays()}
        if not target_section and not row_delta and not col_delta:
            raise ValueError("Move amount is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT * FROM bays WHERE map_section = ?", (map_section,)).fetchall()
            if target_section:
                target_rows = con.execute("SELECT * FROM bays WHERE map_section = ?", (target_section,)).fetchall()
                if not rows or not target_rows:
                    raise ValueError("Both bay groups must exist")
                row_avg = sum(float(row["layout_row"] or 0) for row in rows) / len(rows)
                col_avg = sum(float(row["layout_col"] or 0) for row in rows) / len(rows)
                target_row_avg = sum(float(row["layout_row"] or 0) for row in target_rows) / len(target_rows)
                target_col_avg = sum(float(row["layout_col"] or 0) for row in target_rows) / len(target_rows)
                for row in rows:
                    con.execute(
                        "UPDATE bays SET layout_row = COALESCE(layout_row, 0) + ?, layout_col = COALESCE(layout_col, 0) + ? WHERE id = ?",
                        (target_row_avg - row_avg, target_col_avg - col_avg, row["id"]),
                    )
                for row in target_rows:
                    con.execute(
                        "UPDATE bays SET layout_row = COALESCE(layout_row, 0) + ?, layout_col = COALESCE(layout_col, 0) + ? WHERE id = ?",
                        (row_avg - target_row_avg, col_avg - target_col_avg, row["id"]),
                    )
                self.insert_audit(con, "bay_group", map_section, "swap_bay_group", user, "", "", {"targetMapSection": target_section})
            else:
                for row in rows:
                    con.execute(
                        "UPDATE bays SET layout_row = COALESCE(layout_row, 0) + ?, layout_col = COALESCE(layout_col, 0) + ? WHERE id = ?",
                        (row_delta, col_delta, row["id"]),
                    )
                self.insert_audit(con, "bay_group", map_section, "move_bay_group", user, "", "", {"rowDelta": row_delta, "colDelta": col_delta})
            con.commit()
        return {"ok": True, "mapSection": map_section, "moved": len(rows), "bays": self.get_bays()}

    def mark_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        order_no = digits_only(str(data.get("orderNo") or data.get("order") or ""))
        bay_code = str(data.get("bayCode") or "").strip()
        truck_exempt = bool(data.get("truckExempt"))
        reason = str(data.get("reason") or "Same-day install").strip()
        if not assignment_id and not order_no:
            raise ValueError("Select a bay assignment or enter an order number")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            affected_rows: list[sqlite3.Row] = []
            assignment = None
            if assignment_id:
                assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
                if not assignment:
                    raise ValueError("Assignment not found")
                row = con.execute("SELECT * FROM line_items WHERE id = ?", (assignment["line_item_id"],)).fetchone()
                if row:
                    affected_rows.append(row)
                con.execute("UPDATE bay_assignments SET status = 'SDIOverride', reason = ? WHERE id = ?", (reason, assignment_id))
                self.insert_bay_event(con, assignment["bay_id"], assignment["line_item_id"], "MarkSDI", user, reason)
            elif order_no:
                affected_rows = con.execute(
                    """
                    SELECT li.*
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE li.order_no = ? AND dl.status = 'active'
                    ORDER BY dl.delivery_date DESC, li.id
                    """,
                    (order_no,),
                ).fetchall()
                if not affected_rows:
                    raise ValueError("Order number was not found on active delivery lists")
                if bay_code and not truck_exempt:
                    bay = self.get_bay_by_code(con, bay_code)
                    row = affected_rows[0]
                    cur = con.execute(
                        """
                        INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
                        VALUES (?, ?, ?, 1, 'SDIOverride', ?, ?, ?)
                        """,
                        (row["list_id"], row["id"], bay["id"], user, now_iso(), reason),
                    )
                    assignment_id = int(cur.lastrowid)
                    self.insert_bay_event(con, bay["id"], row["id"], "MarkSDI", user, reason, new_bay_id=bay["id"])

            for row in affected_rows:
                process_state = str(row["process_state"] or "")
                next_state = process_state if re.search(r"\bRush\b", process_state, flags=re.IGNORECASE) else " ".join(part for part in [process_state, "Rush"] if part).strip()
                con.execute("UPDATE line_items SET process_state = ? WHERE id = ?", (next_state, row["id"]))
                self.insert_event(con, row["list_id"], row["id"], "SDI", row["barcode"], user, "", "notice", "Rush order marked", reason)
                self.insert_audit(
                    con,
                    "line_item",
                    row["id"],
                    "mark_rush_sdi",
                    user,
                    "",
                    reason,
                    {"truckExempt": truck_exempt, "bayCode": bay_code, "assignmentId": assignment_id},
                )
            if assignment_id:
                self.insert_audit(con, "bay_assignment", str(assignment_id), "mark_sdi", user, "", reason)
            con.commit()
        return {
            "ok": True,
            "assignmentId": assignment_id,
            "status": "SDIOverride",
            "rush": True,
            "affectedItems": len(affected_rows),
            "message": "A Rush order has been marked. Print rush order?",
        }

    def remove_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        assignment_id = int(data.get("assignmentId") or 0)
        order_no = digits_only(str(data.get("orderNo") or data.get("order") or ""))
        reason = str(data.get("reason") or "SDI cleared").strip()
        if not assignment_id and not order_no:
            raise ValueError("Select a bay assignment or enter an order number")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows: list[sqlite3.Row] = []
            if assignment_id:
                assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
                if not assignment:
                    raise ValueError("Assignment not found")
                con.execute("UPDATE bay_assignments SET status = 'Assigned', reason = ? WHERE id = ?", (reason, assignment_id))
                self.insert_bay_event(con, assignment["bay_id"], assignment["line_item_id"], "RemoveSDI", user, reason)
                row = con.execute("SELECT * FROM line_items WHERE id = ?", (assignment["line_item_id"],)).fetchone()
                if row:
                    rows.append(row)
                self.insert_audit(con, "bay_assignment", str(assignment_id), "remove_sdi", user, "", reason)
            elif order_no:
                rows = con.execute(
                    """
                    SELECT li.*
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE li.order_no = ? AND dl.status = 'active'
                    """,
                    (order_no,),
                ).fetchall()
                if not rows:
                    raise ValueError("Order number was not found on active delivery lists")
            for row in rows:
                next_state = re.sub(r"\bRush\b", "", str(row["process_state"] or ""), flags=re.IGNORECASE).strip()
                next_state = re.sub(r"\s{2,}", " ", next_state)
                con.execute("UPDATE line_items SET process_state = ? WHERE id = ?", (next_state, row["id"]))
                self.insert_audit(con, "line_item", row["id"], "clear_rush_sdi", user, "", reason)
            con.commit()
        return {"ok": True, "assignmentId": assignment_id, "status": "Assigned", "affectedItems": len(rows)}

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

    def export_package_xlsx(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> bytes:
        package = self.get_print_package(list_ids, user=user, filters=filters)
        headers = [
            "Delivery Date",
            "Stages",
            "Barcode",
            "Order Nr.",
            "Item Nr.",
            "Qty.",
            "Scanned",
            "Remaining",
            "Dimensions",
            "Customer",
            "Route",
            "Job Nr.",
            "Product",
            "Suggested Bay",
        ]
        rows: list[list[Any]] = []
        for package_list in package.get("lists", []):
            stages = ", ".join(package_list.get("stages") or [])
            for item in package_list.get("items") or []:
                rows.append([
                    package_list.get("deliveryDate", ""),
                    stages,
                    item.get("barcode", ""),
                    item.get("order", ""),
                    item.get("item", ""),
                    item.get("qty", 0),
                    item.get("scanned", 0),
                    max(int(item.get("qty") or 0) - int(item.get("scanned") or 0), 0),
                    item.get("dimensions", ""),
                    item.get("customer", ""),
                    item.get("route", ""),
                    item.get("job", ""),
                    item.get("product", ""),
                    item.get("suggestedBay", ""),
                ])

        def cell_ref(col: int, row: int) -> str:
            letters = ""
            value = col
            while value:
                value, remainder = divmod(value - 1, 26)
                letters = chr(65 + remainder) + letters
            return f"{letters}{row}"

        def inline_cell(col: int, row: int, value: Any) -> str:
            text = xml_escape(str(value if value is not None else ""))
            return f'<c r="{cell_ref(col, row)}" t="inlineStr"><is><t>{text}</t></is></c>'

        sheet_rows = [
            f'<row r="1">{"".join(inline_cell(index, 1, header) for index, header in enumerate(headers, start=1))}</row>'
        ]
        for row_index, values in enumerate(rows, start=2):
            sheet_rows.append(f'<row r="{row_index}">{"".join(inline_cell(index, row_index, value) for index, value in enumerate(values, start=1))}</row>')

        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "[Content_Types].xml",
                """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
            )
            archive.writestr(
                "_rels/.rels",
                """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
            )
            archive.writestr(
                "xl/workbook.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Delivery Export" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
            )
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>""",
            )
        return output.getvalue()

    def export_xlsx(self, list_id: str) -> bytes:
        rows = self.get_line_items(list_id)
        headers = [
            "Barcode",
            "Order Nr.",
            "Item Nr.",
            "Qty.",
            "Scanned",
            "Remaining",
            "Dimensions",
            "Customer",
            "Route",
            "Job Nr.",
            "Product",
            "Suggested Bay",
        ]

        def cell_ref(col: int, row: int) -> str:
            letters = ""
            value = col
            while value:
                value, remainder = divmod(value - 1, 26)
                letters = chr(65 + remainder) + letters
            return f"{letters}{row}"

        def inline_cell(col: int, row: int, value: Any) -> str:
            text = xml_escape(str(value if value is not None else ""))
            return f'<c r="{cell_ref(col, row)}" t="inlineStr"><is><t>{text}</t></is></c>'

        sheet_rows = [
            f'<row r="1">{"".join(inline_cell(index, 1, header) for index, header in enumerate(headers, start=1))}</row>'
        ]
        for row_index, item in enumerate(rows, start=2):
            values = [
                item["barcode"],
                item["order"],
                item["item"],
                item["qty"],
                item["scanned"],
                max(int(item["qty"]) - int(item["scanned"]), 0),
                item["dimensions"],
                item["customer"],
                item["route"],
                item["job"],
                item["product"],
                item["suggestedBay"],
            ]
            sheet_rows.append(f'<row r="{row_index}">{"".join(inline_cell(index, row_index, value) for index, value in enumerate(values, start=1))}</row>')

        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "[Content_Types].xml",
                """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
            )
            archive.writestr(
                "_rels/.rels",
                """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
            )
            archive.writestr(
                "xl/workbook.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Delivery List" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
            )
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>""",
            )
        return output.getvalue()


def create_store(config: AppConfig) -> BaseDeliveryStore:
    if config.database_type == "sqlite":
        return SQLiteDeliveryStore(config)
    raise NotImplementedError(
        f"Database type {config.database_type!r} is not implemented yet. "
        "Add a store adapter that implements BaseDeliveryStore."
    )
