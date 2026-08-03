# File: backend/store.py
#
# Delivery List Scanner data/business layer.
#
# Code map for future edits:
# - Constants and parsing helpers are near the top.
# - SQLiteDeliveryStore owns schema creation, migrations, and business workflows.
# - Keep UI-only wording in static/js and static/css; keep scanner/import/email/rack/bay rules here.
# - Prefer adding small migration/repair helpers instead of changing old data assumptions
#   in-place, because existing floor-machine databases must continue to open cleanly.

"""Data-access layer for the delivery-list scanner.

The web/API layer should call these store methods instead of issuing SQL
directly. SQLite is used for local/offline deployments, while Azure SQL uses
the same business workflows through a compatibility adapter at the connection boundary.
"""

from __future__ import annotations

import csv
import base64
import os
import smtplib
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from email.message import EmailMessage
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

from backend.config import AppConfig
from database.azure_compat import AzureSqlConnection, connect_azure_sql
from database.migrations import (
    MIGRATIONS,
    MigrationError,
    create_verified_backup,
    database_needs_upgrade,
    run_sqlite_migrations,
)


GRAPH_RESOURCE = "https://graph.microsoft.com"
GRAPH_SCOPE = f"{GRAPH_RESOURCE}/.default"
GRAPH_SEND_URL = f"{GRAPH_RESOURCE}/v1.0/users/{{sender}}/sendMail"
_GRAPH_TOKEN_LOCK = threading.Lock()
_GRAPH_TOKEN_CACHE: dict[str, Any] = {
    "cacheKey": "",
    "accessToken": "",
    "expiresAt": 0.0,
}


class ClosingSQLiteConnection(sqlite3.Connection):
    """Commit or roll back a context-managed SQLite transaction, then close it.

    Effects: Centralizes connection cleanup for every ``with self.connect()``
    workflow so database handles cannot accumulate during long-running scanner
    sessions.
    """

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool | None:
        """Purpose: Finish the closing SQLite connection context and release its resources.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup", "DTC"]
SESSION_COOKIE_NAME = "dls_session"
PASSWORD_ITERATIONS = 260000
SESSION_HOURS = 12
PASSWORD_RESET_MINUTES = 30
PERMISSIONS = [
    "view_delivery_lists",
    "scan_delivery_lists",
    "use_assigned_stations",
    "view_scan_history",
    "correct_scans",
    "reset_delivery_lists",
    "manage_scan_exceptions",
    "import_delivery_lists",
    "preview_delivery_imports",
    "preview_delivery_updates",
    "edit_delivery_lists",
    "print_export",
    "global_search",
    "view_reports",
    "view_admin",
    "manage_users",
    "manage_user_access",
    "manage_roles",
    "view_sessions",
    "manage_stations",
    "manage_route_rules",
    "manage_lookup_values",
    "manage_automation",
    "view_indian_trail",
    "receive_indian_trail",
    "view_bays",
    "assign_bay_items",
    "move_bay_items",
    "clear_bay_items",
    "manage_rush_work",
    "run_bay_checks",
    "view_bay_reports",
    "manage_bay_layout",
    "view_racks",
    "scan_racks",
    "manage_racks",
    "transfer_rack_contents",
    "view_rejects",
    "log_rejects",
    "manage_reject_settings",
    "manage_reject_records",
]

# Old route checks remain supported during the permissions cleanup. New role
# records store only the maintained names above, while signed-in users receive
# the matching legacy aliases until every historical call site is migrated.
LEGACY_PERMISSION_ALIASES = {
    "scan": "scan_delivery_lists",
    "view_lists": "view_delivery_lists",
    "view_stations": "use_assigned_stations",
    "view_own_scans": "view_scan_history",
    "undo_scan": "correct_scans",
    "reset_lists": "reset_delivery_lists",
    "resolve_exceptions": "manage_scan_exceptions",
    "manual_adjust": "manage_scan_exceptions",
    "view_exceptions": "manage_scan_exceptions",
    "preview_import": "preview_delivery_imports",
    "export_reports": "print_export",
    "view_active_sessions": "view_sessions",
    "remove_stations": "manage_stations",
    "deactivate_users": "manage_user_access",
    "reactivate_users": "manage_user_access",
    "update_user_passwords": "manage_user_access",
    "manage_customer_route_rules": "manage_route_rules",
    "indian_trail_receive": "receive_indian_trail",
    "assign_bay": "assign_bay_items",
    "move_bay": "move_bay_items",
    "clear_bay": "clear_bay_items",
    "mark_sdi": "manage_rush_work",
    "remove_sdi": "manage_rush_work",
    "bay_check": "run_bay_checks",
    "indian_trail_reports": "view_bay_reports",
}


def canonical_permission_name(value: Any) -> str:
    """Return the maintained permission name for old or current values."""
    clean = str(value or "").strip()
    return LEGACY_PERMISSION_ALIASES.get(clean, clean)


def canonical_permissions(values: Iterable[Any]) -> list[str]:
    """Normalize and de-duplicate permissions while rejecting retired names."""
    normalized = {canonical_permission_name(value) for value in (values or [])}
    return sorted(permission for permission in normalized if permission in PERMISSIONS)


def expanded_permissions(values: Iterable[Any]) -> list[str]:
    """Expose current permissions plus temporary aliases used by older routes."""
    current = set(canonical_permissions(values))
    expanded = set(current)
    for legacy, canonical in LEGACY_PERMISSION_ALIASES.items():
        if canonical in current:
            expanded.add(legacy)
    return sorted(expanded)


ROLE_PERMISSIONS = {
    "Operator": [
        "view_delivery_lists", "scan_delivery_lists", "use_assigned_stations",
        "view_scan_history", "print_export", "global_search", "view_racks", "scan_racks",
        "view_rejects", "log_rejects",
    ],
    "Supervisor": [
        "view_delivery_lists", "scan_delivery_lists", "use_assigned_stations",
        "view_scan_history", "correct_scans", "manage_scan_exceptions",
        "print_export", "global_search", "view_reports", "view_sessions",
        "view_racks", "scan_racks", "manage_racks", "transfer_rack_contents",
        "view_rejects", "log_rejects",
    ],
    "Admin": PERMISSIONS,
    "Indian Trail Operator": [
        "view_delivery_lists", "use_assigned_stations", "view_indian_trail",
        "receive_indian_trail", "view_bays", "global_search", "print_export", "view_racks",
        "view_rejects",
    ],
    "Indian Trail Lead": [
        "view_delivery_lists", "use_assigned_stations", "view_indian_trail",
        "receive_indian_trail", "view_bays", "global_search", "print_export",
        "correct_scans", "manage_scan_exceptions", "assign_bay_items",
        "move_bay_items", "clear_bay_items", "manage_rush_work", "run_bay_checks",
        "view_racks", "scan_racks", "view_rejects", "log_rejects",
    ],
    "Indian Trail Manager": [
        "view_delivery_lists", "use_assigned_stations", "view_indian_trail",
        "receive_indian_trail", "view_bays", "global_search", "print_export",
        "correct_scans", "manage_scan_exceptions", "assign_bay_items",
        "move_bay_items", "clear_bay_items", "manage_rush_work", "run_bay_checks",
        "view_bay_reports", "view_reports", "view_sessions", "view_racks",
        "scan_racks", "manage_racks", "transfer_rack_contents", "view_rejects", "log_rejects",
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
CPU_DESTINATION_ADDRESS = "1709 Airport Rd, Monroe, NC 28110"
INDIAN_TRAIL_DESTINATION_ADDRESS = "3980 Matthews Indian Trail Rd, Matthews, NC 28104"
GREENVILLE_DESTINATION_ADDRESS = "Greenville address pending"

DEFAULT_CUSTOMER_ROUTE_RULES = [
    ("Blue Color Glass", "CPU", CPU_DESTINATION_ADDRESS),
    ("ABZZ Glass", "CPU", CPU_DESTINATION_ADDRESS),
    ("Glass & Door Pro", "CPU", CPU_DESTINATION_ADDRESS),
    ("Add It Home Services", "DTC", ""),
]

# Bay auto-assigner settings are intentionally stored as simple key/value
# pairs in SQLite so future admins can tune thresholds without code changes.
DEFAULT_BAY_AUTO_ASSIGN_SETTINGS = {
    "standardMaxInches": 59.99,
    "tallMinInches": 60.0,
    "oversizeMinInches": 96.0,
    "cpuBayType": "CPU",
    "mirrorBayType": "Mirror",
    "framedMirrorBayType": "Framed Mirror",
    "standardBayType": "Standard",
    "tallBayType": "Tall",
    "oversizeBayType": "Oversize",
    "manualAssignTypes": ["Tall", "Oversize"],
}
DEFAULT_RACK_DESTINATION_OVERRIDE_MINUTES = 15
RACK_DESTINATION_OVERRIDE_METADATA_KEY = "rack_destination_override_minutes"
DEFAULT_CROSS_DATE_SCAN_MODE = "auto_unique"
DEFAULT_CROSS_DATE_SCAN_PAST_DAYS = 7
DEFAULT_CROSS_DATE_SCAN_FUTURE_DAYS = 30
CROSS_DATE_SCAN_MODE_METADATA_KEY = "cross_date_scan_mode"
CROSS_DATE_SCAN_PAST_DAYS_METADATA_KEY = "cross_date_scan_past_days"
CROSS_DATE_SCAN_FUTURE_DAYS_METADATA_KEY = "cross_date_scan_future_days"
CROSS_DATE_SCAN_MODES = {"disabled", "ask", "auto_unique"}
SUPPORTED_IMPORT_EXTENSIONS = {".json", ".xlsx", ".xlsm", ".csv"}
BAY_EVENT_RETENTION_DAYS = 7
BAY_EVENT_CLEANUP_INTERVAL_SECONDS = 60 * 60
ACTION_HISTORY_RETENTION_DAYS = 30
ACTION_HISTORY_PAGE_SIZE = 50
ACTION_HISTORY_ARCHIVE_BATCH_SIZE = 2000
XLSX_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
XLSX_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
XLSX_PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def utc_now_iso() -> str:
    """Return the canonical UTC timestamp representation used by the database."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_iso() -> str:
    """Backward-compatible alias for the canonical UTC timestamp helper.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return utc_now_iso()


def parse_utc_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to an aware UTC datetime."""
    parsed = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_iso(value: str) -> datetime:
    """Backward-compatible timestamp parser returning an aware UTC value.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    return parse_utc_timestamp(value)


def hash_password(password: str) -> str:
    """Purpose: Run the hash password workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Purpose: Run the verify password workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
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
    """Purpose: Run the session token hash workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def stage_access_for_roles(roles: list[str]) -> list[str]:
    """Purpose: Run the stage access for roles workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    access: list[str] = []
    for role in roles:
        for stage in ROLE_STAGE_ACCESS.get(role, []):
            if stage == "*":
                return ["*"]
            if stage not in access:
                access.append(stage)
    return access


def user_can_access_stage(user: dict[str, Any] | None, stage: str, scanner: str = "") -> bool:
    """Purpose: Run the user can access stage workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    if not user:
        return False
    allowed = user.get("stageAccess") or stage_access_for_roles(user.get("roles") or [])
    if "*" in allowed:
        return True
    haystack = f"{stage} {scanner}".lower()
    return any(str(value).lower() in haystack for value in allowed)


def clean_barcode(value: str) -> str:
    """Purpose: Run the clean barcode workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    trimmed = str(value or "").replace("*", "").replace("\r", "").replace("\n", "").strip()
    return "".join(ch for ch in trimmed if ch.isalnum()).upper()


def normalize_rack_code(value: str) -> str:
    """Purpose: Normalize rack code for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    text = clean_barcode(value)
    if text.startswith("RACK"):
        text = text[4:]
    if text in {"TRUCK", "NORACK"}:
        return "T"
    return text


def parse_rack_barcode(value: str) -> tuple[str, str]:
    """Purpose: Parse rack barcode for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    text = clean_barcode(value)
    if not text.startswith("RACK"):
        return "", ""
    payload = text[4:]
    if payload.startswith("TRUCK"):
        payload = "T" + payload[5:]
    if payload.startswith("NORACK"):
        payload = "T" + payload[6:]
    legacy_truck_match = re.fullmatch(r"T(20\d{6})", payload)
    if legacy_truck_match:
        date_text = legacy_truck_match.group(1)
        return "T", f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:8]}"
    match = re.match(r"^([A-Z0-9]+?)(20\d{6})$", payload)
    if match:
        date_text = match.group(2)
        return normalize_rack_code(match.group(1)), f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:8]}"
    return normalize_rack_code(payload), ""


def rack_barcode_text(rack_code: str, delivery_date: str = "") -> str:
    """Purpose: Run the rack barcode text workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    clean_rack = normalize_rack_code(rack_code)
    date_digits = digits_only(delivery_date)[:8]
    return f"RACK-{clean_rack}-{date_digits}" if date_digits else f"RACK-{clean_rack}"


def digits_only(value: str) -> str:
    """Purpose: Run the digits only workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def normalized_match_text(value: Any) -> str:
    """Purpose: Run the normalized match text workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def simplified_match_text(value: Any) -> str:
    """Purpose: Run the simplified match text workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = normalized_match_text(value)
    for token in ("AND", "THE", "INC", "LLC", "COMPANY", "CO"):
        text = text.replace(token, "")
    return text


def is_valid_email(value: str) -> bool:
    """Purpose: Validate valid email for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = str(value or "").strip()
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", text))


def fuzzy_contains(text: str, needle: str) -> bool:
    """Purpose: Run the fuzzy contains workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
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
    # Customer routing rules must match the customer field only. Job numbers can
    # legitimately contain text such as CPU even when the ROUTE column still
    # sends the glass to Indian Trail.
    """Purpose: Run the default customer route workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    customer_name = str(item.get("customer", ""))
    for customer, route, _address in DEFAULT_CUSTOMER_ROUTE_RULES:
        if fuzzy_contains(customer_name, customer):
            return route
    return ""


def canonical_barcode(order_no: int | str, item_no: int | str) -> str:
    """Purpose: Run the canonical barcode workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return f"T200{int(order_no):06d}{int(item_no):03d}000"


def format_display_date(value: str) -> str:
    """Purpose: Normalize display date for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    parts = str(value).split("-")
    if len(parts) == 3:
        return f"{int(parts[1])}/{int(parts[2])}/{int(parts[0])}"
    return str(value)


def parse_dimension_number(part: str) -> float:
    """Purpose: Parse dimension number for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
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
    """Purpose: Run the route signal text workflow for the delivery-list scanner.

    Effects: This function reads or updates shared application state.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return " ".join(
        str(item.get(key, ""))
        for key in ("route", "job", "customer", "product", "processState", "queueState")
    ).upper()


ROUTE_GREENVILLE_ALIASES = {
    "GNV",
    "GRN",
    "GRVLLE",
    "GRVILLE",
    "GRVLE",
    "GVLLE",
    "GREENVILLE",
}
ROUTE_CPU_INDIAN_TRAIL_COMPACT = {"CPUIT", "CPUINT", "ITCPU", "INTCPU"}
ROUTE_CPU_AIR_COMPACT = {"CPUAIR", "AIRCPU"}
ROUTE_STAGE_REPAIR_VERSION = "v060-customer-route-primary-1"


def cpu_job_route_hint(value: Any) -> str | None:
    """Return the only supported Job Nr. destination overrides.

    CPU-Air sends the item to Customer Pickup. CPU-IT/CPU-INT explicitly keeps
    the item on the Indian Trail route. DTC and Greenville are intentionally
    not inferred from Job Nr.; active Customer Route Rules own those routes.
    """
    text = str(value or "").strip().upper()
    if not text:
        return None
    compact = normalized_match_text(text)
    separator = r"[^A-Z0-9]*"
    token_start = r"(?:^|[^A-Z0-9])"
    token_end = r"(?![A-Z0-9])"
    cpu_indian_trail = re.compile(
        rf"(?:{token_start}CPU{separator}(?:IT|INT){token_end}|"
        rf"{token_start}(?:IT|INT){separator}CPU{token_end})"
    )
    cpu_air = re.compile(
        rf"(?:{token_start}CPU{separator}AIR{token_end}|"
        rf"{token_start}AIR{separator}CPU{token_end})"
    )
    if compact in ROUTE_CPU_INDIAN_TRAIL_COMPACT or cpu_indian_trail.search(text):
        return ""
    if compact in ROUTE_CPU_AIR_COMPACT or cpu_air.search(text):
        return "CPU"
    return None


def canonical_route_designation(value: Any, *, job_context: bool = False) -> tuple[bool, str]:
    """Resolve an operational route designation to the stored route code.

    Route values and Job Nr. suffixes are typed by people, so matching accepts
    capitalization and separator differences while retaining strict token
    boundaries. In Job Nr. context, only CPU-Air and CPU-IT/INT are treated as
    destination overrides; DTC and Greenville come from Customer Route Rules.
    """
    text = str(value or "").strip().upper()
    if not text:
        return False, ""

    compact = normalized_match_text(text)
    token_start = r"(?:^|[^A-Z0-9])"
    token_end = r"(?![A-Z0-9])"

    cpu_hint = cpu_job_route_hint(text)
    if cpu_hint is not None:
        return True, cpu_hint
    if job_context:
        return False, ""

    if compact in {"DTC", "DELIVERTOCUSTOMER"} or re.search(
        rf"{token_start}DTC{token_end}",
        text,
    ):
        return True, "DTC"

    if compact in ROUTE_GREENVILLE_ALIASES or any(
        re.search(rf"{token_start}{re.escape(alias)}{token_end}", text)
        for alias in ROUTE_GREENVILLE_ALIASES
    ):
        return True, "GNV"

    if compact in {"CUSTOMERPICKUP", "PICKUP"}:
        return True, "CPU"

    if compact == "CPU" or re.search(rf"{token_start}CPU{token_end}", text):
        return True, "CPU"
    if compact in {"INT", "IT", "INDIANTRAIL"}:
        return True, ""
    return False, ""


def normalize_route_column(value: Any) -> tuple[bool, str]:
    """Return whether ROUTE was supplied and its canonical route code."""
    route = str(value or "").strip().upper()
    if not route:
        return False, ""
    matched, canonical = canonical_route_designation(route)
    return (True, canonical) if matched else (True, route)


def job_number_route_hint(item: dict[str, Any]) -> str | None:
    """Return the supported CPU-Air/CPU-IT override from Job Nr."""
    return cpu_job_route_hint(item.get("job", ""))


def inferred_route(item: dict[str, Any]) -> str:
    """Purpose: Run the inferred route workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    raw_route = str(item.get("route", "")).strip()
    explicit, route = normalize_route_column(raw_route)
    job_hint = job_number_route_hint(item)
    if explicit:
        # Imports historically stored the fallback Indian Trail value as IT.
        # A strong DTC, Greenville, or CPU-Air Job Nr. designation repairs that
        # generated fallback while an explicitly written Indian Trail phrase or
        # CPU-IT designation remains Indian Trail.
        if normalized_match_text(raw_route) == "IT" and job_hint in {"CPU", "GNV", "DTC"}:
            return job_hint
        return route

    if job_hint is not None:
        return job_hint

    customer_route = default_customer_route(item)
    if customer_route:
        return normalize_route_column(customer_route)[1]

    # Generic CPU text in Job Nr. remains Indian Trail unless an explicit ROUTE
    # or customer-route rule says otherwise.
    return ""


def route_category(item: dict[str, Any]) -> str:
    """Purpose: Run the route category workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    route = inferred_route(item)
    if route == "CPU":
        return "cpu"
    if route == "GNV":
        return "greenville"
    if route == "DTC":
        return "dtc"
    if route:
        return f"custom:{route}"
    return "indian_trail"


def custom_route_codes(base_items: list[dict[str, Any]]) -> list[str]:
    """Purpose: Run the custom route codes workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    codes = {
        inferred_route(item)
        for item in base_items
        if route_category(item).startswith("custom:")
    }
    return sorted(code for code in codes if code)


def route_stage_label(route: str) -> str:
    """Purpose: Run the route stage label workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    clean = str(route or "").strip().upper()
    if clean == "CPU":
        return "Customer Pickup"
    if clean == "DTC":
        return "Delivery to Customer"
    if clean in {"GNV", "GRN", "GREENVILLE"}:
        return "BFS Greenville"
    return clean


def public_route_label(value: Any) -> str:
    """Return the route label that may appear on printed or exported documents.

    Effects: Does not modify the stored route. Standard Indian Trail designations are
    intentionally hidden so exception routes such as CPU, DTC, Greenville, and custom
    destinations remain visually meaningful on floor paperwork and exported files.
    Flow: Canonicalizes common operational aliases, returns an empty label for the
    standard Indian Trail route, and preserves nonstandard/custom route text.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    matched, canonical = canonical_route_designation(raw)
    if matched:
        if canonical == "":
            return ""
        return canonical
    return raw


def receiving_stage_destination(stage: Any, scanner: Any = "") -> str:
    """Purpose: Run the receiving stage destination workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = f"{stage or ''} {scanner or ''}".strip().lower()
    if "indian trail" in text or "inbound" in text:
        return "Indian Trail"
    if "customer pickup" in text or re.search(r"\bcpu\b", text):
        return "CPU"
    if "greenville" in text or re.search(r"\bgnv\b", text):
        return "Greenville"
    if "deliver to customer" in text or re.search(r"\bdtc\b", text):
        return "DTC"
    return ""


def scan_stage_category(stage: Any, scanner: Any = "") -> str:
    """Return the operational scan-stage category used for cross-date matching."""
    text = f"{stage or ''} {scanner or ''}".strip().lower()
    if "outbound" in text:
        return "outbound"
    if "dtc" in text or "deliver to customer" in text:
        return "dtc"
    if "greenville" in text or re.search(r"\bgnv\b", text):
        return "greenville"
    if "indian trail" in text or "inbound" in text:
        return "received"
    if "customer pickup" in text or re.search(r"\bcpu\b", text):
        return "pickup"
    return "staged"


def is_cpu_item(item: dict[str, Any]) -> bool:
    """Purpose: Validate CPU item for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return route_category(item) == "cpu"


def normalized_bay_auto_assign_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Purpose: Run the normalized bay auto assign settings workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    merged = dict(DEFAULT_BAY_AUTO_ASSIGN_SETTINGS)
    if isinstance(settings, dict):
        merged.update(settings)
    for key in ("standardMaxInches", "tallMinInches", "oversizeMinInches"):
        try:
            merged[key] = float(merged.get(key, DEFAULT_BAY_AUTO_ASSIGN_SETTINGS[key]))
        except (TypeError, ValueError):
            merged[key] = float(DEFAULT_BAY_AUTO_ASSIGN_SETTINGS[key])
    manual = merged.get("manualAssignTypes")
    if isinstance(manual, str):
        manual = [value.strip() for value in manual.split(",") if value.strip()]
    if not isinstance(manual, list):
        manual = list(DEFAULT_BAY_AUTO_ASSIGN_SETTINGS["manualAssignTypes"])
    merged["manualAssignTypes"] = [str(value).strip() for value in manual if str(value).strip()]
    return merged


def suggested_bay(product: str, dimensions: str, route: str, settings: dict[str, Any] | None = None) -> str:
    """Purpose: Run the suggested bay workflow for the delivery-list scanner.

    Effects: This function reads or updates shared application state.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    config = normalized_bay_auto_assign_settings(settings)
    if str(route).upper() == "CPU":
        return str(config.get("cpuBayType") or "CPU")
    product_text = str(product or "").upper()
    if "FRAMED" in product_text and "MIRROR" in product_text:
        return str(config.get("framedMirrorBayType") or "Framed Mirror")
    if "MIRROR" in product_text:
        return str(config.get("mirrorBayType") or "Mirror")
    parts = re.findall(r"\d+(?:\s+\d+/\d+|/\d+)?", str(dimensions))
    largest = max([parse_dimension_number(part) for part in parts] or [0])
    if largest >= float(config.get("oversizeMinInches") or 96):
        return str(config.get("oversizeBayType") or "Oversize")
    if largest >= float(config.get("tallMinInches") or 60):
        return str(config.get("tallBayType") or "Tall")
    return str(config.get("standardBayType") or "Standard")


def items_for_profile(profile: str, base_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Purpose: Run the items for profile workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    if profile == "cpu":
        return [item for item in base_items if is_cpu_item(item)]
    if profile == "indian_trail":
        return [item for item in base_items if route_category(item) == "indian_trail"]
    if profile == "greenville":
        return [item for item in base_items if route_category(item) == "greenville"]
    if profile == "dtc":
        return [item for item in base_items if route_category(item) == "dtc"]
    if profile.startswith("route:"):
        route = profile.split(":", 1)[1].upper()
        return [item for item in base_items if inferred_route(item) == route]
    return list(base_items)


def build_delivery_lists(sample: dict[str, Any]) -> list[tuple[str, str, str, str, list[dict[str, Any]]]]:
    """Purpose: Build delivery lists for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
    """
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
    for route in custom_route_codes(base_items):
        suffix = f"route-{re.sub(r'[^a-z0-9]+', '-', route.lower()).strip('-')}"
        stage = route_stage_label(route)
        items = items_for_profile(f"route:{route}", base_items)
        if not items:
            continue
        definitions.append(
            (
                f"{delivery_date}-{suffix}",
                f"{format_display_date(delivery_date)} - {stage}",
                stage,
                stage,
                items,
            )
        )
    return definitions


def all_profile_list_ids(delivery_date: str) -> list[str]:
    """Purpose: Run the all profile list IDs workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
    """
    return [f"{delivery_date}-{suffix}" for suffix, _, _, _ in LIST_PROFILES]


def parse_int_text(value: Any) -> int | None:
    """Purpose: Parse int text for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text.replace(",", "")))
    except ValueError:
        match = re.search(r"\d+", text)
        return int(match.group(0)) if match else None


def clean_excel_text(value: Any) -> str:
    """Purpose: Run the clean excel text workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = str(value or "")
    text = re.sub(r"_x000[dD]_", "\r", text)
    text = re.sub(r"_x000[aA]_", "\n", text)
    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def format_delivery_date(month: int, day: int, year: int) -> str:
    """Purpose: Normalize delivery date for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    if year < 100:
        year += 2000
    return f"{year:04d}-{month:02d}-{day:02d}"


def delivery_date_from_text(text: str) -> str:
    """Purpose: Run the delivery date from text workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})(?!\d)", text)
    if not match:
        return ""
    month, day, year = (int(part) for part in match.groups())
    return format_delivery_date(month, day, year)


def column_label(ref: str) -> str:
    """Purpose: Run the column label workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    match = re.match(r"([A-Z]+)", ref.upper())
    return match.group(1) if match else ""


def first_xlsx_sheet_path(archive: zipfile.ZipFile) -> str:
    """Purpose: Run the first XLSX sheet path workflow for the delivery-list scanner.

    Effects: This function reads or changes files.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
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


def read_xlsx_rows(path: Path, max_rows: int | None = None) -> list[tuple[int, dict[str, str]]]:
    """Purpose: Read XLSX rows for the delivery-list scanner workflow.

    Effects: This function reads or changes files.
    Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
    """
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
            if max_rows is not None and row_number > max_rows:
                break
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
    """Purpose: Run the delivery date from rows or name workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    for _, row in rows[:12]:
        date_text = delivery_date_from_text(" ".join(row.values()))
        if date_text:
            return date_text
    date_text = delivery_date_from_text(path.stem)
    if date_text:
        return date_text
    return now_iso()[:10]


def delivery_date_from_source_header(path: Path) -> str:
    """Purpose: Run the delivery date from source header workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        try:
            rows = read_xlsx_rows(path, max_rows=12)
            return delivery_date_from_rows_or_name(rows, path)
        except Exception:
            return delivery_date_from_text(path.stem)
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return str(payload.get("deliveryDate") or "").strip() or delivery_date_from_text(path.stem)
        except Exception:
            return delivery_date_from_text(path.stem)
    return delivery_date_from_text(path.stem)


def parse_aw_delivery_workbook(path: Path) -> dict[str, Any]:
    """Purpose: Parse aw delivery workbook for the delivery-list scanner workflow.

    Effects: This function reads or updates shared application state.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
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
        items.append(item)
    if not items:
        raise ValueError(f"No delivery-list rows found in {path.name}")
    return {"deliveryDate": delivery_date, "sourceName": path.name, "items": items}


def parse_delivery_csv(path: Path) -> dict[str, Any]:
    """Parse a delivery-list CSV while honoring an in-file delivery date.

    CSV exports may carry the delivery date in a column instead of the file
    name. The first valid row date is authoritative; the file name and current
    date are fallbacks for legacy files that omit it.
    """
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    delivery_date = ""
    for row in rows:
        date_value = (
            row.get("deliveryDate")
            or row.get("Delivery Date")
            or row.get("Delivery Date:")
            or row.get("delivery_date")
            or row.get("Date")
            or row.get("date")
            or ""
        )
        delivery_date = delivery_date_from_text(str(date_value))
        if delivery_date:
            break
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
        items.append(item)
    if not items:
        raise ValueError(f"No delivery-list rows found in {path.name}")
    return {
        "deliveryDate": delivery_date or delivery_date_from_text(path.stem) or now_iso()[:10],
        "sourceName": path.name,
        "items": items,
    }


def load_delivery_source_payload(path: Path) -> dict[str, Any]:
    """Purpose: Load delivery source payload for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix in {".xlsx", ".xlsm"}:
        return parse_aw_delivery_workbook(path)
    if suffix == ".csv":
        return parse_delivery_csv(path)
    raise ValueError(f"Unsupported import file type: {path.suffix}")


def source_file_hash(path: Path) -> str:
    """Purpose: Run the source file hash workflow for the delivery-list scanner.

    Effects: This function reads or changes files.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_remake_item(item: dict[str, Any]) -> bool:
    """Purpose: Validate remake item for the delivery-list scanner workflow.

    Effects: This function reads or updates shared application state.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = " ".join(str(item.get(key, "")) for key in ("remake", "processState", "queueState")).upper()
    return "REMAKE" in text or re.search(r"\bRM\b", text) is not None


def is_rush_item(item: dict[str, Any]) -> bool:
    """Purpose: Validate rush item for the delivery-list scanner workflow.

    Effects: This function reads or updates shared application state.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = " ".join(str(item.get(key, "")) for key in ("remake", "processState", "queueState")).upper()
    return "SDI" in text or re.search(r"\bRUSH\b", text) is not None


def is_mirror_item(item: dict[str, Any]) -> bool:
    """Purpose: Validate mirror item for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = " ".join(str(item.get(key, "")) for key in ("product", "job", "customer", "route")).upper()
    return "MIRROR" in text or re.search(r"\bMIR\b", text) is not None


def should_print_delivery_item(item: dict[str, Any], exclude_mirrors: bool = True, include_mirror_remakes: bool = True) -> bool:
    """Purpose: Run the should print delivery item workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
    """
    if not exclude_mirrors:
        return True
    if not is_mirror_item(item):
        return True
    return include_mirror_remakes and is_remake_item(item)


def print_counts_for_items(items: list[dict[str, Any]]) -> dict[str, int]:
    """Purpose: Run the print counts for items workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
    """
    printable = [item for item in items if should_print_delivery_item(item)]
    return {
        "rowCount": len(printable),
        "pieceCount": sum(int(item.get("qty") or 0) for item in printable),
        "remakeCount": sum(1 for item in printable if is_remake_item(item)),
        "excludedMirrorCount": sum(1 for item in items if is_mirror_item(item) and not should_print_delivery_item(item)),
    }


def row_value(row: Any, key: str, default: Any = "") -> Any:
    """Read a named value from sqlite3.Row, AzureSqlRow, or a dictionary."""

    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key] if key in row.keys() else default
    except (AttributeError, KeyError, TypeError, IndexError):
        return default


def item_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Purpose: Run the item from row workflow for the delivery-list scanner.

    Effects: This function reads or updates shared application state.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
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
        "priorityDeliveryDate": row_value(row, "priority_delivery_date"),
        "priorityDirectToTruck": bool(row_value(row, "priority_direct_to_truck", 0)),
        "rackCode": row["rack_code"] if "rack_code" in row.keys() else "",
        "rackName": row["rack_name"] if "rack_name" in row.keys() else "",
        "rackType": row["rack_type"] if "rack_type" in row.keys() else "",
        "bayCode": row["bay_code"] if "bay_code" in row.keys() else "",
        "lastScannedAt": row["last_scanned_at"] if "last_scanned_at" in row.keys() else "",
        "lastScannedStation": row["last_scanned_station"] if "last_scanned_station" in row.keys() else "",
        "internalRejectCount": int(row_value(row, "internal_reject_count", 0) or 0),
        "lastRejectReason": str(row_value(row, "last_reject_reason", "") or ""),
    }


def event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Purpose: Run the event from row workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
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
            "rackCode": row_value(row, "rack_code", ""),
            "rackName": row_value(row, "rack_name", ""),
            "rackStatus": row_value(row, "rack_status", ""),
            "outboundScanned": bool(row_value(row, "outbound_scanned", 0)),
            "listStage": row_value(row, "list_stage", ""),
        }
    return {
        "ok": row["event_type"] in {"scan", "manual_scan", "undo", "redo", "import", "update"},
        "isManual": row["event_type"] == "manual_scan",
        "barcode": row["canonical_barcode"] or row["barcode"],
        "raw": row["barcode"],
        "item": item,
        "message": row["message"],
        "reason": row["reason"],
        "time": row["created_at"],
        "user": row["user_name"],
        "station": row["station"],
        "eventType": row["event_type"],
        "qtyDelta": row["qty_delta"] if "qty_delta" in row.keys() else 0,
    }


def list_meta(row: sqlite3.Row) -> dict[str, Any]:
    """Purpose: Read meta for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
    """
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
    """Purpose: Run the request user name workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return str(data.get("user") or data.get("operator") or "Scanner").strip()[:80]


def request_station(data: dict[str, Any]) -> str:
    """Purpose: Run the request station workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return str(data.get("station") or "").strip()[:80]


class BaseDeliveryStore:
    database_type = "base"

    def initialize(self) -> None:
        """Purpose: Run the initialize workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def health(self) -> dict[str, Any]:
        """Purpose: Run the health workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def get_delivery_lists(self, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Purpose: Read delivery lists for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_delivery_list(self, list_id: str, last_scan: dict[str, Any] | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Read delivery list for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_line_items(self, list_id: str) -> list[dict[str, Any]]:
        """Purpose: Read line items for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def create_app_notification(
        self,
        con: sqlite3.Connection,
        notification_type: str,
        title: str,
        message: str,
        created_by: str,
        payload: dict[str, Any] | None = None,
        expires_in_hours: int = 24,
        acknowledge_creator: bool = False,
    ) -> int:
        """Purpose: Create app notification for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        created_at = now_iso()
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=max(int(expires_in_hours or 24), 1))
        ).isoformat(timespec="seconds")
        cur = con.execute(
            """
            INSERT INTO app_notifications (
                notification_type, title, message, payload_json,
                created_by, created_at, expires_at, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                str(notification_type or "notice"),
                str(title or "Notification"),
                str(message or ""),
                json.dumps(payload or {}, separators=(",", ":")),
                str(created_by or "system"),
                created_at,
                expires_at,
            ),
        )
        notification_id = int(cur.lastrowid)
        if acknowledge_creator and created_by:
            creator = con.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
                (created_by,),
            ).fetchone()
            if creator:
                con.execute(
                    """
                    INSERT OR IGNORE INTO app_notification_receipts (
                        notification_id, user_id, acknowledged_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (notification_id, creator["id"], created_at),
                )
        return notification_id

    def get_pending_notifications(self, username: str, limit: int = 5) -> list[dict[str, Any]]:
        """Purpose: Read pending notifications for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        clean_username = str(username or "").strip()
        if not clean_username:
            return []
        with self.connect() as con:
            user = con.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
                (clean_username,),
            ).fetchone()
            if not user:
                return []
            rows = con.execute(
                """
                SELECT n.*
                FROM app_notifications n
                LEFT JOIN app_notification_receipts r
                  ON r.notification_id = n.id AND r.user_id = ?
                WHERE n.active = 1
                  AND r.notification_id IS NULL
                  AND (COALESCE(n.expires_at, '') = '' OR n.expires_at > ?)
                ORDER BY n.id ASC
                LIMIT ?
                """,
                (user["id"], now_iso(), max(1, min(int(limit or 5), 20))),
            ).fetchall()
        notifications = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            notifications.append(
                {
                    "id": row["id"],
                    "type": row["notification_type"],
                    "title": row["title"],
                    "message": row["message"],
                    "details": payload,
                    "createdBy": row["created_by"],
                    "createdAt": row["created_at"],
                    "expiresAt": row["expires_at"],
                }
            )
        return notifications

    def get_notification_history(self, username: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent non-scan application notifications for the bell inbox.

        Scan events live in scan_events and are deliberately excluded. Notification
        receipts affect popup delivery only; acknowledged items remain visible here
        until their normal expiration so scanning cannot erase update history.
        """
        clean_username = str(username or "").strip()
        clean_limit = max(1, min(int(limit or 50), 200))
        if not clean_username:
            return []
        with self.connect() as con:
            user = con.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
                (clean_username,),
            ).fetchone()
            if not user:
                return []
            rows = con.execute(
                """
                SELECT n.*,
                       CASE WHEN r.notification_id IS NULL THEN 0 ELSE 1 END AS is_read
                FROM app_notifications n
                LEFT JOIN app_notification_receipts r
                  ON r.notification_id = n.id AND r.user_id = ?
                WHERE n.active = 1
                  AND (COALESCE(n.expires_at, '') = '' OR n.expires_at > ?)
                ORDER BY n.id DESC
                """,
                (user["id"], now_iso()),
            ).fetchall()
        notifications = []
        for row in list(rows)[:clean_limit]:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            notifications.append(
                {
                    "id": row["id"],
                    "type": row["notification_type"],
                    "title": row["title"],
                    "message": row["message"],
                    "details": payload,
                    "createdBy": row["created_by"],
                    "createdAt": row["created_at"],
                    "expiresAt": row["expires_at"],
                    "isRead": bool(row["is_read"]),
                }
            )
        return notifications

    def mark_all_notifications_read(self, username: str) -> dict[str, Any]:
        """Acknowledge all currently visible bell notifications for one user."""
        notifications = self.get_notification_history(username, 200)
        marked = 0
        for notification in notifications:
            if notification.get("isRead"):
                continue
            self.acknowledge_notification(int(notification.get("id") or 0), username)
            marked += 1
        return {"ok": True, "markedRead": marked}
    def acknowledge_notification(self, notification_id: int, username: str) -> dict[str, Any]:
        """Purpose: Run the acknowledge notification workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        clean_username = str(username or "").strip()
        clean_id = int(notification_id or 0)
        if not clean_id or not clean_username:
            raise ValueError("notificationId and user are required")
        with self.connect() as con:
            user = con.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
                (clean_username,),
            ).fetchone()
            notification = con.execute(
                "SELECT id FROM app_notifications WHERE id = ? AND active = 1",
                (clean_id,),
            ).fetchone()
            if not user or not notification:
                return {"ok": True, "notificationId": clean_id}
            con.execute(
                """
                INSERT OR IGNORE INTO app_notification_receipts (
                    notification_id, user_id, acknowledged_at
                )
                VALUES (?, ?, ?)
                """,
                (clean_id, user["id"], now_iso()),
            )
            con.commit()
        return {"ok": True, "notificationId": clean_id}

    def record_scan(self, scan_request: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Process scan for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        raise NotImplementedError

    def undo_last_scan(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        """Purpose: Undo last scan for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        raise NotImplementedError

    def redo_last_undo(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        """Purpose: Redo last undo for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        raise NotImplementedError

    def reset_stage(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        """Purpose: Run the reset stage workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def import_delivery_list(self, data: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Load delivery list for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def import_delivery_folder(self, data: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Load delivery folder for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        user = request_user_name(data)
        folder = Path(str(data.get("sourceFolder") or self.config.temp_delivery_lists_dir)).expanduser()
        date_from = str(data.get("dateFrom") or "").strip()
        date_to = str(data.get("dateTo") or "").strip() or "9999-12-31"
        if not date_from:
            date_from = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
        if not folder.is_absolute():
            folder = self.config.root / folder
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Temp Delivery Lists folder not found: {folder}")

        imported_files: list[dict[str, Any]] = []
        updated_files: list[dict[str, Any]] = []
        skipped_files: list[dict[str, Any]] = []
        ignored_files: list[dict[str, Any]] = []
        failed_files: list[dict[str, Any]] = []
        print_candidates: list[dict[str, Any]] = []
        active_list_id = ""

        all_paths = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_IMPORT_EXTENSIONS)
        candidate_paths: list[tuple[Path, str, str]] = []

        for path in all_paths:
            file_date = delivery_date_from_text(path.stem)
            modified_date = ""
            try:
                modified_date = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            except OSError:
                pass

            if file_date:
                if date_from and file_date < date_from:
                    ignored_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": file_date,
                            "fileNameDate": file_date,
                            "modifiedDate": modified_date,
                            "reason": f"Filename delivery date is before the import window start {date_from}",
                        }
                    )
                    continue
                if date_to and file_date > date_to:
                    ignored_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": file_date,
                            "fileNameDate": file_date,
                            "modifiedDate": modified_date,
                            "reason": f"Filename delivery date is after the import window end {date_to}",
                        }
                    )
                    continue
            elif date_from and modified_date and modified_date < date_from:
                ignored_files.append(
                    {
                        "fileName": path.name,
                        "deliveryDate": "",
                        "fileNameDate": "",
                        "modifiedDate": modified_date,
                        "reason": f"No filename date found and the file was last modified before {date_from}",
                    }
                )
                continue

            candidate_paths.append((path, file_date, modified_date))

        for path, file_date, modified_date in candidate_paths:
            try:
                header_date = delivery_date_from_source_header(path)
                if header_date and date_from and header_date < date_from:
                    ignored_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": header_date,
                            "fileNameDate": file_date,
                            "modifiedDate": modified_date,
                            "reason": f"Workbook delivery date is outside import window before {date_from}",
                        }
                    )
                    continue
                if header_date and date_to and header_date > date_to:
                    ignored_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": header_date,
                            "fileNameDate": file_date,
                            "modifiedDate": modified_date,
                            "reason": f"Workbook delivery date is outside import window after {date_to}",
                        }
                    )
                    continue

                source_path = str(path.resolve())
                file_hash = source_file_hash(path)
                payload = load_delivery_source_payload(path)
                payload_date = str(payload.get("deliveryDate") or "").strip()
                if payload_date and payload_date != header_date and date_from and payload_date < date_from:
                    ignored_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": payload_date,
                            "fileNameDate": file_date,
                            "modifiedDate": modified_date,
                            "reason": f"Workbook delivery date is outside import window before {date_from}",
                        }
                    )
                    continue
                if payload_date and payload_date != header_date and date_to and payload_date > date_to:
                    ignored_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": payload_date,
                            "fileNameDate": file_date,
                            "modifiedDate": modified_date,
                            "reason": f"Workbook delivery date is outside import window after {date_to}",
                        }
                    )
                    continue

                definitions = build_delivery_lists(payload)
                definition_ids = [definition[0] for definition in definitions]

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

                    active_definition_ids = set()
                    if definition_ids:
                        placeholders = ",".join("?" for _ in definition_ids)
                        active_definition_ids = {
                            row["id"]
                            for row in con.execute(
                                f"""
                                SELECT id
                                FROM delivery_lists
                                WHERE status = 'active'
                                  AND id IN ({placeholders})
                                """,
                                definition_ids,
                            ).fetchall()
                        }

                same_active_file = (
                    previous
                    and previous["source_hash"] == file_hash
                    and set(definition_ids).issubset(active_definition_ids)
                )

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
                    "reactivatedCount": result.get("reactivatedCount", 0),
                    "updatedCount": result["updatedCount"],
                    "listIds": result["changedListIds"],
                    "stageSummaries": result.get("stageSummaries") or [],
                    "addedPieceQty": result.get("addedPieceQty", 0),
                    "changedPieceQty": result.get("changedPieceQty", 0),
                }
                if not result["createdCount"] and not result["updatedCount"] and not result.get("changedListIds"):
                    skipped_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": payload.get("deliveryDate", header_date),
                            "reason": "No updates" if same_active_file else "No delivery-list line changes detected",
                        }
                    )
                    continue
                if result["createdCount"]:
                    imported_files.append(file_result)
                else:
                    updated_files.append(file_result)
                print_candidates.extend(result.get("printCandidates") or [])
            except Exception as exc:
                failed_files.append({"fileName": path.name, "errors": [str(exc)]})

        checked_count = len(imported_files) + len(updated_files) + len(skipped_files) + len(failed_files)

        return {
            "ok": not failed_files or bool(imported_files or updated_files or skipped_files or ignored_files),
            "sourceFolder": str(folder),
            "dateFrom": date_from,
            "dateTo": date_to,
            "totalFolderFiles": len(all_paths),
            "candidateFiles": len(candidate_paths),
            "checkedFiles": checked_count,
            "scannedFiles": checked_count,
            "ignoredFiles": ignored_files,
            "importedFiles": imported_files,
            "updatedFiles": updated_files,
            "skippedFiles": skipped_files,
            "failedFiles": failed_files,
            "printCandidates": print_candidates,
            "activeListId": active_list_id,
            "lists": self.get_delivery_lists(),
        }

    def get_print_package(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Read print package for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_scan_events(self, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
        """Purpose: Read scan events for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_exceptions(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Purpose: Read exceptions for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_stations(self) -> list[str]:
        """Purpose: Read stations for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def add_station(self, name: str) -> dict[str, Any]:
        """Purpose: Create station for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def rename_station(self, old_name: str, new_name: str) -> dict[str, Any]:
        """Purpose: Update station for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def remove_station(self, name: str) -> dict[str, Any]:
        """Purpose: Remove station for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def export_csv(self, list_id: str) -> str:
        """Purpose: Export CSV for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
        raise NotImplementedError

    def export_xlsx(self, list_id: str) -> bytes:
        """Purpose: Export XLSX for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
        raise NotImplementedError

    def export_package_xlsx(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> bytes:
        """Purpose: Export package XLSX for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
        raise NotImplementedError

    def export_package_csv(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> str:
        """Export the same filtered multi-list package as CSV."""
        raise NotImplementedError

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        """Purpose: Run the authenticate user workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def get_user_by_session(self, token: str) -> dict[str, Any] | None:
        """Purpose: Read user by session for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def delete_session(self, token: str) -> None:
        """Purpose: Remove session for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def create_user(self, data: dict[str, Any], created_by: str = "system") -> dict[str, Any]:
        """Purpose: Create user for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def list_users(self) -> list[dict[str, Any]]:
        """Purpose: Read users for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def deactivate_user(self, username: str, deactivated_by: str = "system") -> dict[str, Any]:
        """Purpose: Run the deactivate user workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def reactivate_user(self, username: str, activated_by: str = "system") -> dict[str, Any]:
        """Purpose: Run the reactivate user workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def delete_user(self, username: str, deleted_by: str = "system") -> dict[str, Any]:
        """Purpose: Remove user for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def update_user_password(self, username: str, password: str, updated_by: str = "system") -> dict[str, Any]:
        """Purpose: Update user password for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def update_user_roles(self, username: str, roles: list[str], station: str | None = None, email: str | None = None, updated_by: str = "system") -> dict[str, Any]:
        """Purpose: Update user roles for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def list_active_sessions(self) -> list[dict[str, Any]]:
        """Purpose: Read active sessions for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_permissions(self) -> list[str]:
        """Purpose: Read permissions for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def list_roles(self) -> list[dict[str, Any]]:
        """Purpose: Read roles for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def create_role(self, data: dict[str, Any], created_by: str = "system") -> dict[str, Any]:
        """Create a custom role and its initial maintained permissions."""
        name = " ".join(str(data.get("name") or "").split())[:60]
        description = " ".join(str(data.get("description") or "").split())[:240]
        requested = [str(value).strip() for value in (data.get("permissions") or []) if str(value).strip()]
        permissions = canonical_permissions(requested)
        unknown = [value for value in requested if canonical_permission_name(value) not in PERMISSIONS]
        if not name:
            raise ValueError("Role name is required")
        if unknown:
            raise ValueError(f"Unknown permission: {unknown[0]}")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if con.execute("SELECT 1 FROM roles WHERE lower(name) = lower(?)", (name,)).fetchone():
                raise ValueError("A role with that name already exists")
            cur = con.execute(
                "INSERT INTO roles (name, description) VALUES (?, ?)",
                (name, description or f"{name} role"),
            )
            for permission in permissions:
                con.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_name) VALUES (?, ?)",
                    (cur.lastrowid, permission),
                )
            self.insert_audit(
                con, "role", name, "create_role", created_by, "", "",
                {"description": description, "permissions": permissions},
            )
            con.commit()
        return {"roles": self.list_roles(), "permissions": self.get_permissions()}

    def update_role_permissions(self, role_name: str, permissions: list[str], updated_by: str = "system") -> dict[str, Any]:
        """Purpose: Update role permissions for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def preview_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Run the preview import workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def admin_summary(self) -> dict[str, Any]:
        """Purpose: Run the admin summary workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def resolve_exception(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Resolve exception for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def global_search(self, query: str, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Purpose: Run the global search workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
                       r.rack_code,
                       r.display_name AS rack_display_name,
                       r.rack_type AS rack_type,
                       r.status AS rack_status,
                       (
                           SELECT se.created_at
                           FROM scan_events se
                           WHERE se.line_item_id = li.id
                             AND se.event_type IN ('scan', 'manual_scan', 'redo')
                             AND se.qty_delta > 0
                           ORDER BY se.id DESC
                           LIMIT 1
                       ) AS last_scan_time,
                       (
                           SELECT se.user_name
                           FROM scan_events se
                           WHERE se.line_item_id = li.id
                             AND se.event_type IN ('scan', 'manual_scan', 'redo')
                             AND se.qty_delta > 0
                           ORDER BY se.id DESC
                           LIMIT 1
                       ) AS last_scan_user
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id AND ba.status NOT IN ('Cleared', 'Cancelled')
                LEFT JOIN bays b ON b.id = ba.bay_id
                LEFT JOIN rack_items ri ON ri.line_item_id = li.id AND ri.status = 'Active'
                LEFT JOIN racks r ON r.id = ri.rack_id AND r.active = 1
                WHERE li.order_no LIKE ? OR li.item_no LIKE ? OR li.source_id LIKE ? OR li.barcode LIKE ?
                   OR li.customer LIKE ? OR li.job LIKE ? OR li.route LIKE ?
                   OR li.product LIKE ? OR li.dimensions LIKE ? OR dl.stage LIKE ?
                   OR b.bay_code LIKE ? OR b.display_name LIKE ?
                ORDER BY dl.delivery_date DESC, CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER)
                LIMIT 100
                """,
                (like, like, like, like, like, like, like, like, like, like, like, like),
            ).fetchall()

        def stage_kind(row: sqlite3.Row) -> str:
            """Purpose: Run the stage kind workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            text = f"{row['stage']} {row['scanner']}".lower()
            if "outbound" in text:
                return "outbound"
            if "indian trail" in text or "inbound" in text:
                return "indian_trail"
            if "customer pickup" in text or "cpu" in text:
                return "cpu"
            if "greenville" in text or "gnv" in text:
                return "greenville"
            if "dtc" in text or "deliver to customer" in text:
                return "dtc"
            if "staging" in text:
                return "staging"
            return "other"

        def representative_rank(row: sqlite3.Row) -> tuple[int, str, int]:
            """Rank the navigation row by the actual latest scan event.

            A timestamped scan always wins, regardless of process order. Legacy
            scanned rows without event timestamps fall back to process progress.
            Completely unscanned items deliberately choose Staging.
            """
            scanned = int(row["scanned_qty"] or 0)
            kind = stage_kind(row)
            last_scan_time = str(row["last_scan_time"] or "")
            progress_rank = {
                "indian_trail": 100,
                "outbound": 90,
                "cpu": 86,
                "dtc": 84,
                "greenville": 82,
                "staging": 70,
                "other": 40,
            }.get(kind, 0)
            if last_scan_time:
                return (3, last_scan_time, progress_rank)
            if scanned:
                return (2, "", progress_rank)
            if kind == "staging":
                return (1, "", 100)
            if row["bay_code"]:
                return (1, "", 40)
            if row["rack_code"]:
                return (1, "", 30)
            return (0, "", progress_rank)

        def rack_location_label(code: Any) -> str:
            """Purpose: Run the rack location label workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            clean_code = normalize_rack_code(str(code or ""))
            if not clean_code:
                return ""
            if clean_code == "T":
                return "Truck"
            if re.fullmatch(r"T\d+", clean_code):
                return f"Truck {clean_code[1:]}"
            return f"Rack {clean_code}"

        def airport_label(scanner: Any) -> str:
            """Purpose: Run the airport label workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            return str(scanner or "Airport Rd").replace(" - ", " ").strip() or "Airport Rd"

        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            if user is not None and not user_can_access_stage(user, row["stage"], row["scanner"]):
                continue
            key = f"{row['delivery_date']}::{row['order_no']}::{row['item_no']}"
            rank = representative_rank(row)
            result = grouped.setdefault(key, {
                "lineItemId": row["id"],
                "deliveryListId": row["list_id"],
                "deliveryList": row["label"],
                "deliveryDate": row["delivery_date"],
                "stage": row["stage"],
                "scanner": row["scanner"],
                "barcode": row["barcode"],
                "sourceId": row["source_id"],
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
                "rackCode": row["rack_code"],
                "rackName": row["rack_display_name"],
                "rackType": row["rack_type"],
                "rackStatus": row["rack_status"],
                "lastScanTime": row["last_scan_time"],
                "lastScanUser": row["last_scan_user"],
                "stageLocations": [],
                "locationText": "Process Not Started",
                "_rank": (0, "", -1),
                "_representativeKind": "",
                "_representativeHasScan": False,
                "_staged": False,
                "_outbound": False,
                "_received": False,
                "_cpu": False,
                "_dtc": False,
                "_greenville": False,
                "_scanner": row["scanner"],
                "_transportCode": "",
                "_bayLabel": "",
                "_preassignedBay": "",
            })

            scanned = int(row["scanned_qty"] or 0)
            kind = stage_kind(row)
            if row["rack_code"] and not result.get("_transportCode"):
                result["_transportCode"] = row["rack_code"]
            if row["bay_code"]:
                bay_label = row["bay_display_name"] or row["bay_code"]
                result["_preassignedBay"] = bay_label
                if scanned and kind == "indian_trail":
                    result["_bayLabel"] = bay_label
            if scanned:
                if kind == "indian_trail":
                    result["_received"] = True
                elif kind == "outbound":
                    result["_outbound"] = True
                elif kind == "cpu":
                    result["_cpu"] = True
                elif kind == "dtc":
                    result["_dtc"] = True
                elif kind == "greenville":
                    result["_greenville"] = True
                elif kind == "staging":
                    result["_staged"] = True
                else:
                    result["_staged"] = True

            if rank >= tuple(result.get("_rank", (0, "", -1))):
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
                result["rackCode"] = row["rack_code"] or result.get("_transportCode")
                result["rackName"] = row["rack_display_name"]
                result["rackType"] = row["rack_type"]
                result["rackStatus"] = row["rack_status"]
                result["lastScanTime"] = row["last_scan_time"]
                result["lastScanUser"] = row["last_scan_user"]
                result["_scanner"] = row["scanner"]
                result["_representativeKind"] = kind
                result["_representativeHasScan"] = bool(row["last_scan_time"] or scanned)
                result["_rank"] = rank

        cleaned_results: list[dict[str, Any]] = []
        for result in grouped.values():
            transport_label = rack_location_label(result.get("_transportCode") or result.get("rackCode"))
            bay_label = result.get("_bayLabel") or result.get("bay") or result.get("_preassignedBay")
            representative_kind = str(result.get("_representativeKind") or "")
            representative_has_scan = bool(result.get("_representativeHasScan"))
            if not representative_has_scan:
                location = "Not Scanned Yet"
            elif representative_kind == "indian_trail":
                location = "Indian Trail Received"
                if bay_label:
                    location = f"{location} - Bay {bay_label}"
            elif representative_kind == "outbound":
                location = f"Outbound on {transport_label}" if transport_label else f"Outbound {airport_label(result.get('_scanner'))}"
            elif representative_kind == "staging":
                location = f"Staging {airport_label(result.get('_scanner'))}"
                if transport_label:
                    location = f"{location} on {transport_label}"
            elif representative_kind == "cpu":
                location = "Customer Pickup"
            elif representative_kind == "dtc":
                location = "Delivery to Customer"
            elif representative_kind == "greenville":
                location = "BFS Greenville"
            else:
                location = str(result.get("stage") or result.get("scanner") or "Last scanned stage")

            result["locationText"] = location
            result["stageLocations"] = [location]
            result["navigationDeliveryListId"] = result.get("deliveryListId")
            result["navigationStage"] = result.get("stage")
            if result.get("_transportCode") and not result.get("rackCode"):
                result["rackCode"] = result.get("_transportCode")
            for key in list(result.keys()):
                if key.startswith("_"):
                    result.pop(key, None)
            cleaned_results.append(result)
        return cleaned_results[:30]

    def update_line_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update line item for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def delete_delivery_list(self, list_id: str, user: str) -> dict[str, Any]:
        """Purpose: Remove delivery list for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def delete_delivery_date(self, delivery_date: str, user: str) -> dict[str, Any]:
        """Purpose: Remove delivery date for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def delete_line_item(self, line_item_id: str, user: str) -> dict[str, Any]:
        """Purpose: Remove line item for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def get_customer_route_rules(self) -> list[dict[str, Any]]:
        """Purpose: Read customer route rules for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def add_customer_route_rule(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Create customer route rule for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def remove_customer_route_rule(self, rule_id: int, user: str) -> dict[str, Any]:
        """Purpose: Remove customer route rule for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def get_email_transport_config(self) -> dict[str, Any]:
        """Return the active server-side email transport without exposing credentials.

        Effects: Reads environment configuration only; secrets are represented as
        booleans so the browser can show setup readiness without receiving them.
        Flow: Resolves the requested transport, checks Graph and SMTP readiness,
        and returns one normalized status object used by sending and Admin UI.
        """
        requested = str(os.environ.get("DLS_EMAIL_TRANSPORT") or "auto").strip().lower()
        if requested not in {"auto", "graph", "smtp", "disabled"}:
            requested = "auto"

        graph_sender = str(
            os.environ.get("DLS_GRAPH_SENDER")
            or os.environ.get("DLS_EMAIL_FROM")
            or os.environ.get("DLS_SMTP_FROM")
            or ""
        ).strip()
        graph_tenant_id = str(os.environ.get("DLS_GRAPH_TENANT_ID") or "").strip()
        graph_client_id = str(os.environ.get("DLS_GRAPH_CLIENT_ID") or "").strip()
        graph_client_secret = str(os.environ.get("DLS_GRAPH_CLIENT_SECRET") or "")
        graph_auth_mode = str(os.environ.get("DLS_GRAPH_AUTH_MODE") or "").strip().lower()
        if not graph_auth_mode:
            graph_auth_mode = "managed-identity" if os.environ.get("IDENTITY_ENDPOINT") else "client-secret"
        if graph_auth_mode not in {"client-secret", "managed-identity"}:
            graph_auth_mode = "client-secret"

        managed_identity_ready = bool(
            os.environ.get("IDENTITY_ENDPOINT") and os.environ.get("IDENTITY_HEADER")
        )
        graph_ready = bool(
            graph_sender
            and (
                (
                    graph_auth_mode == "client-secret"
                    and graph_tenant_id
                    and graph_client_id
                    and graph_client_secret
                )
                or (graph_auth_mode == "managed-identity" and managed_identity_ready)
            )
        )

        smtp_host = str(os.environ.get("DLS_SMTP_HOST") or "").strip()
        smtp_from = str(os.environ.get("DLS_SMTP_FROM") or "").strip()
        smtp_ready = bool(smtp_host and smtp_from)

        active = "disabled"
        if requested == "graph":
            active = "graph"
        elif requested == "smtp":
            active = "smtp"
        elif requested == "auto":
            if graph_ready:
                active = "graph"
            elif smtp_ready:
                active = "smtp"
            else:
                active = "draft"

        configured = bool(
            (active == "graph" and graph_ready)
            or (active == "smtp" and smtp_ready)
        )
        label = {
            "graph": "Microsoft Graph",
            "smtp": "SMTP",
            "draft": "Draft mode",
            "disabled": "Disabled",
        }.get(active, "Draft mode")
        return {
            "requestedTransport": requested,
            "transport": active,
            "transportLabel": label,
            "configured": configured,
            "from": graph_sender if active == "graph" else smtp_from,
            "testRecipient": str(os.environ.get("DLS_EMAIL_TEST_RECIPIENT") or "").strip(),
            "graphConfigured": graph_ready,
            "graphConfig": {
                "authMode": graph_auth_mode,
                "sender": graph_sender,
                "tenantIdSet": bool(graph_tenant_id),
                "clientId": graph_client_id,
                "clientSecretSet": bool(graph_client_secret),
                "managedIdentityAvailable": managed_identity_ready,
                "managedIdentityClientId": str(os.environ.get("DLS_GRAPH_MANAGED_IDENTITY_CLIENT_ID") or "").strip(),
                "saveToSentItems": str(os.environ.get("DLS_GRAPH_SAVE_TO_SENT_ITEMS") or "1").strip().lower() not in {"0", "false", "no"},
            },
            "smtpConfigured": smtp_ready,
            "smtpConfig": {
                "host": smtp_host,
                "port": os.environ.get("DLS_SMTP_PORT", "587"),
                "from": smtp_from,
                "user": os.environ.get("DLS_SMTP_USER", ""),
                "ssl": os.environ.get("DLS_SMTP_SSL", "").strip().lower() in {"1", "true", "yes"},
            },
        }

    def get_customer_email_settings(self) -> dict[str, Any]:
        """Purpose: Read customer email settings for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        with self.connect() as con:
            contacts = con.execute(
                """
                SELECT * FROM customer_email_contacts
                WHERE active = 1
                ORDER BY customer_pattern, email
                """
            ).fetchall()
            cc_rows = con.execute(
                """
                SELECT * FROM customer_email_cc
                WHERE active = 1
                ORDER BY email
                """
            ).fetchall()
            outbox = con.execute(
                """
                SELECT * FROM email_outbox
                ORDER BY id DESC
                LIMIT 20
                """
            ).fetchall()
        transport = self.get_email_transport_config()
        return {
            "contacts": [
                {
                    "id": row["id"],
                    "customerPattern": row["customer_pattern"],
                    "email": row["email"],
                    "active": bool(row["active"]),
                    "updatedAt": row["updated_at"] or row["created_at"],
                }
                for row in contacts
            ],
            "cc": [
                {
                    "id": row["id"],
                    "email": row["email"],
                    "active": bool(row["active"]),
                    "updatedAt": row["updated_at"] or row["created_at"],
                }
                for row in cc_rows
            ],
            "outbox": [
                {
                    "id": row["id"],
                    "emailType": row["email_type"],
                    "customerName": row["customer_name"],
                    "deliveryDate": row["delivery_date"],
                    "toEmails": json.loads(row["to_emails"] or "[]"),
                    "ccEmails": json.loads(row["cc_emails"] or "[]"),
                    "subject": row["subject"],
                    "body": row["body"],
                    "status": row["status"],
                    "createdAt": row["created_at"],
                    "sentAt": row["sent_at"],
                    "error": row["error"],
                }
                for row in outbox
            ],
            "emailConfigured": transport["configured"],
            "emailTransport": transport["transport"],
            "emailTransportLabel": transport["transportLabel"],
            "emailFrom": transport["from"],
            "emailTestRecipient": transport["testRecipient"],
            "graphConfigured": transport["graphConfigured"],
            "graphConfig": transport["graphConfig"],
            "smtpConfigured": transport["smtpConfigured"],
            "smtpConfig": transport["smtpConfig"],
        }

    def upsert_customer_email_contact(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the upsert customer email contact workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        customer = " ".join(str(data.get("customerPattern") or data.get("customer") or "").split())[:160]
        email = str(data.get("email") or "").strip().lower()
        contact_id = int(data.get("id") or 0)
        if not customer:
            raise ValueError("Customer match text is required")
        if not is_valid_email(email):
            raise ValueError("A valid customer email is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if contact_id:
                con.execute(
                    """
                    UPDATE customer_email_contacts
                    SET customer_pattern = ?, email = ?, active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (customer, email, now_iso(), contact_id),
                )
                audit_id = str(contact_id)
            else:
                con.execute(
                    """
                    INSERT INTO customer_email_contacts (customer_pattern, email, active, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?)
                    ON CONFLICT(customer_pattern, email) DO UPDATE SET active = 1, updated_at = excluded.updated_at
                    """,
                    (customer, email, now_iso(), now_iso()),
                )
                audit_id = customer
            self.insert_audit(con, "customer_email", audit_id, "upsert_customer_email", user, "", "", {"customer": customer, "email": email})
            con.commit()
        return self.get_customer_email_settings()

    def remove_customer_email_contact(self, contact_id: int, user: str) -> dict[str, Any]:
        """Purpose: Remove customer email contact for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        if not contact_id:
            raise ValueError("contact id is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM customer_email_contacts WHERE id = ?", (contact_id,)).fetchone()
            if not row:
                raise ValueError("Customer email contact not found")
            con.execute("UPDATE customer_email_contacts SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), contact_id))
            self.insert_audit(con, "customer_email", str(contact_id), "remove_customer_email", user, "", "", {"customer": row["customer_pattern"], "email": row["email"]})
            con.commit()
        return self.get_customer_email_settings()

    def upsert_customer_email_cc(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the upsert customer email cc workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        email = str(data.get("email") or "").strip().lower()
        if not is_valid_email(email):
            raise ValueError("A valid CC email is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO customer_email_cc (email, active, created_at, updated_at)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(email) DO UPDATE SET active = 1, updated_at = excluded.updated_at
                """,
                (email, now_iso(), now_iso()),
            )
            self.insert_audit(con, "customer_email_cc", email, "upsert_customer_email_cc", user, "", "", {"email": email})
            con.commit()
        return self.get_customer_email_settings()

    def remove_customer_email_cc(self, cc_id: int, user: str) -> dict[str, Any]:
        """Purpose: Remove customer email cc for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        if not cc_id:
            raise ValueError("cc id is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM customer_email_cc WHERE id = ?", (cc_id,)).fetchone()
            if not row:
                raise ValueError("CC email not found")
            con.execute("UPDATE customer_email_cc SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), cc_id))
            self.insert_audit(con, "customer_email_cc", str(cc_id), "remove_customer_email_cc", user, "", "", {"email": row["email"]})
            con.commit()
        return self.get_customer_email_settings()

    def queue_customer_email_test(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Create or send a customer-email test message.

        This deliberately writes to email_outbox even when SMTP is missing, so the
        Admin Email Drafts section can preview exactly what would have been sent.
        SMTP credentials stay server-side through DLS_SMTP_* environment variables.
        """
        to_email = str(data.get("toEmail") or data.get("email") or "").strip().lower()
        cc_text = str(data.get("ccEmails") or "").replace(";", ",")
        cc_emails = [part.strip().lower() for part in cc_text.split(",") if part.strip()]
        subject = str(data.get("subject") or "Delivery Scanner test email").strip()[:180]
        body = str(data.get("body") or "This is a test email from the Delivery List Scanner customer email system.").strip()
        if not is_valid_email(to_email):
            raise ValueError("Enter a valid recipient email for the test message")
        clean_cc = sorted({email for email in cc_emails if is_valid_email(email) and email != to_email})
        status = "queued"
        sent_at = ""
        error = ""
        transport_used = ""
        try:
            transport_used = self.try_send_email([to_email], clean_cc, subject, body)
            status = "sent"
            sent_at = now_iso()
        except RuntimeError as exc:
            status = "draft"
            error = str(exc)
        except Exception as exc:
            status = "failed"
            error = str(exc)
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO email_outbox (email_type, customer_name, customer_pattern, delivery_date, to_emails, cc_emails, subject, body, status, created_at, sent_at, error, payload_json)
                VALUES ('test', 'Email Test', 'Email Test', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_iso()[:10],
                    json.dumps([to_email]),
                    json.dumps(clean_cc),
                    subject,
                    body,
                    status,
                    now_iso(),
                    sent_at,
                    error,
                    json.dumps({
                        "user": user,
                        "transport": transport_used or self.get_email_transport_config()["transport"],
                        "emailConfigured": self.get_email_transport_config()["configured"],
                    }, separators=(",", ":")),
                ),
            )
            self.insert_audit(con, "customer_email", to_email, "send_test_email", user, "", error, {"status": status, "subject": subject})
            con.commit()
        payload = self.get_customer_email_settings()
        payload["testResult"] = {
            "status": status,
            "error": error,
            "toEmail": to_email,
            "transport": transport_used or payload.get("emailTransport") or "draft",
        }
        return payload

    def customer_email_matches(self, con: sqlite3.Connection, customer_name: str) -> list[sqlite3.Row]:
        """Purpose: Run the customer email matches workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rows = con.execute(
            """
            SELECT * FROM customer_email_contacts
            WHERE active = 1
            ORDER BY LENGTH(customer_pattern) DESC, customer_pattern
            """
        ).fetchall()
        return [row for row in rows if fuzzy_contains(customer_name, row["customer_pattern"]) or fuzzy_contains(row["customer_pattern"], customer_name)]

    def customer_cc_emails(self, con: sqlite3.Connection) -> list[str]:
        """Purpose: Run the customer cc emails workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return [row["email"] for row in con.execute("SELECT email FROM customer_email_cc WHERE active = 1 ORDER BY email").fetchall()]

    def queue_email_message(self, con: sqlite3.Connection, email_type: str, customer_name: str, customer_pattern: str, delivery_date: str, to_emails: list[str], cc_emails: list[str], subject: str, body: str, payload: dict[str, Any]) -> None:
        """Purpose: Send email message for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        clean_to = sorted({email.strip().lower() for email in to_emails if is_valid_email(email)})
        clean_cc = sorted({email.strip().lower() for email in cc_emails if is_valid_email(email) and email.strip().lower() not in clean_to})
        if not clean_to:
            return
        existing = con.execute(
            """
            SELECT * FROM email_outbox
            WHERE email_type = ? AND customer_name = ? AND delivery_date = ? AND subject = ? AND status IN ('queued', 'draft', 'sent')
            LIMIT 1
            """,
            (email_type, customer_name, delivery_date, subject),
        ).fetchone()
        if existing and existing["status"] == "sent":
            return

        status = "queued"
        sent_at = ""
        error = ""
        try:
            self.try_send_email(clean_to, clean_cc, subject, body)
            status = "sent"
            sent_at = now_iso()
        except RuntimeError as exc:
            status = "draft"
            error = str(exc)
        except Exception as exc:
            status = "failed"
            error = str(exc)

        if existing:
            # If a previous run saved a draft because SMTP was not configured, retry it
            # on the next import/ready check after SMTP is configured instead of silently
            # leaving the old draft forever. If SMTP is still unavailable, keep the draft.
            if status != "sent":
                return
            con.execute(
                """
                UPDATE email_outbox
                SET to_emails = ?, cc_emails = ?, body = ?, status = 'sent', sent_at = ?, error = '', payload_json = ?
                WHERE id = ?
                """,
                (json.dumps(clean_to), json.dumps(clean_cc), body, sent_at, json.dumps(payload, separators=(",", ":")), existing["id"]),
            )
            return

        con.execute(
            """
            INSERT INTO email_outbox (email_type, customer_name, customer_pattern, delivery_date, to_emails, cc_emails, subject, body, status, created_at, sent_at, error, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (email_type, customer_name, customer_pattern, delivery_date, json.dumps(clean_to), json.dumps(clean_cc), subject, body, status, now_iso(), sent_at, error, json.dumps(payload, separators=(",", ":"))),
        )

    def acquire_graph_access_token(self, force_refresh: bool = False) -> str:
        """Acquire and cache a Microsoft Graph app-only access token.

        Effects: Makes one HTTPS request to Microsoft Entra when the cache is empty
        or near expiry. No token or client secret is persisted to the database.
        Flow: Uses client credentials for the local Windows deployment or the App
        Service managed-identity endpoint after the Azure cutover.
        """
        config = self.get_email_transport_config()["graphConfig"]
        auth_mode = str(config.get("authMode") or "client-secret")
        tenant_id = str(os.environ.get("DLS_GRAPH_TENANT_ID") or "").strip()
        client_id = str(os.environ.get("DLS_GRAPH_CLIENT_ID") or "").strip()
        managed_client_id = str(os.environ.get("DLS_GRAPH_MANAGED_IDENTITY_CLIENT_ID") or "").strip()
        cache_key = f"{auth_mode}:{tenant_id}:{client_id}:{managed_client_id}"

        with _GRAPH_TOKEN_LOCK:
            now = time.time()
            if (
                not force_refresh
                and _GRAPH_TOKEN_CACHE.get("cacheKey") == cache_key
                and _GRAPH_TOKEN_CACHE.get("accessToken")
                and float(_GRAPH_TOKEN_CACHE.get("expiresAt") or 0) > now + 90
            ):
                return str(_GRAPH_TOKEN_CACHE["accessToken"])

            if auth_mode == "managed-identity":
                endpoint = str(os.environ.get("IDENTITY_ENDPOINT") or "").strip()
                identity_header = str(os.environ.get("IDENTITY_HEADER") or "").strip()
                if not endpoint or not identity_header:
                    raise RuntimeError("Microsoft Graph managed identity is not available on this host")
                query = {
                    "resource": GRAPH_RESOURCE,
                    "api-version": "2019-08-01",
                }
                if managed_client_id:
                    query["client_id"] = managed_client_id
                separator = "&" if "?" in endpoint else "?"
                token_url = f"{endpoint}{separator}{urllib.parse.urlencode(query)}"
                request = urllib.request.Request(
                    token_url,
                    headers={"X-IDENTITY-HEADER": identity_header, "Accept": "application/json"},
                    method="GET",
                )
            else:
                client_secret = str(os.environ.get("DLS_GRAPH_CLIENT_SECRET") or "")
                if not tenant_id or not client_id or not client_secret:
                    raise RuntimeError("Microsoft Graph client credentials are incomplete")
                token_url = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant_id, safe='')}/oauth2/v2.0/token"
                encoded = urllib.parse.urlencode({
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": GRAPH_SCOPE,
                    "grant_type": "client_credentials",
                }).encode("utf-8")
                request = urllib.request.Request(
                    token_url,
                    data=encoded,
                    headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                    method="POST",
                )

            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    token_payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                response_body = exc.read().decode("utf-8", errors="replace")
                try:
                    error_payload = json.loads(response_body)
                    nested_error = error_payload.get("error") if isinstance(error_payload, dict) else None
                    message = str(
                        (error_payload.get("error_description") if isinstance(error_payload, dict) else "")
                        or (nested_error.get("message") if isinstance(nested_error, dict) else "")
                        or nested_error
                        or response_body
                    )
                except Exception:
                    message = response_body
                raise RuntimeError(f"Microsoft Graph authentication failed ({exc.code}): {message[:500]}") from exc
            except OSError as exc:
                raise RuntimeError(f"Microsoft Graph authentication could not reach Microsoft Entra: {exc}") from exc

            access_token = str(token_payload.get("access_token") or "")
            if not access_token:
                raise RuntimeError("Microsoft Graph authentication returned no access token")
            expires_at = now + max(int(token_payload.get("expires_in") or 3600), 300)
            try:
                provided_expiry = float(token_payload.get("expires_on") or 0)
                if provided_expiry > now:
                    expires_at = provided_expiry
            except (TypeError, ValueError):
                pass
            _GRAPH_TOKEN_CACHE.update({
                "cacheKey": cache_key,
                "accessToken": access_token,
                "expiresAt": expires_at,
            })
            return access_token

    def send_graph_email(self, to_emails: list[str], cc_emails: list[str], subject: str, body: str) -> None:
        """Send one message through Microsoft Graph as the configured mailbox.

        Effects: Calls ``POST /users/{sender}/sendMail`` and saves the message in
        the sender mailbox's Sent Items unless configuration explicitly disables it.
        Flow: Uses the cached app-only token, retries once after an authorization
        failure, and returns only after Graph accepts the message with HTTP 202.
        """
        transport = self.get_email_transport_config()
        sender = str(transport.get("graphConfig", {}).get("sender") or "").strip()
        if not sender:
            raise RuntimeError("Microsoft Graph sender mailbox is not configured")
        save_to_sent = bool(transport.get("graphConfig", {}).get("saveToSentItems", True))
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": address}}
                    for address in to_emails
                ],
                "ccRecipients": [
                    {"emailAddress": {"address": address}}
                    for address in cc_emails
                ],
            },
            "saveToSentItems": save_to_sent,
        }
        endpoint = GRAPH_SEND_URL.format(sender=urllib.parse.quote(sender, safe=""))

        for attempt in range(2):
            access_token = self.acquire_graph_access_token(force_refresh=attempt > 0)
            request = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = int(response.getcode() or 0)
                    if status != 202:
                        raise RuntimeError(f"Microsoft Graph returned unexpected HTTP {status}")
                    return
            except urllib.error.HTTPError as exc:
                response_body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 401 and attempt == 0:
                    continue
                try:
                    error_payload = json.loads(response_body)
                    nested_error = error_payload.get("error") if isinstance(error_payload, dict) else None
                    message = str(
                        (nested_error.get("message") if isinstance(nested_error, dict) else "")
                        or nested_error
                        or response_body
                    )
                except Exception:
                    message = response_body
                raise RuntimeError(f"Microsoft Graph send failed ({exc.code}): {message[:500]}") from exc
            except OSError as exc:
                raise RuntimeError(f"Microsoft Graph could not send the email: {exc}") from exc
        raise RuntimeError("Microsoft Graph could not authorize the email request")

    def send_smtp_email(self, to_emails: list[str], cc_emails: list[str], subject: str, body: str) -> None:
        """Send one message through the legacy SMTP transport.

        Effects: Opens a TLS/SSL SMTP connection and may authenticate with the
        configured mailbox credentials. This remains a fallback for existing sites.
        Flow: Builds the same plain-text message used by Graph and submits it once.
        """
        smtp_host = os.environ.get("DLS_SMTP_HOST", "").strip()
        smtp_from = os.environ.get("DLS_SMTP_FROM", "").strip()
        if not smtp_host or not smtp_from:
            raise RuntimeError("SMTP is not configured")
        msg = EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = ", ".join(to_emails)
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)
        msg["Subject"] = subject
        msg.set_content(body)
        port = int(os.environ.get("DLS_SMTP_PORT", "587") or 587)
        username = os.environ.get("DLS_SMTP_USER", "").strip()
        password = os.environ.get("DLS_SMTP_PASSWORD", "")
        use_ssl = os.environ.get("DLS_SMTP_SSL", "").strip().lower() in {"1", "true", "yes"}
        with (smtplib.SMTP_SSL(smtp_host, port, timeout=20) if use_ssl else smtplib.SMTP(smtp_host, port, timeout=20)) as smtp:
            if not use_ssl:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(msg)

    def try_send_email(self, to_emails: list[str], cc_emails: list[str], subject: str, body: str) -> str:
        """Send one email through the single configured delivery transport.

        Effects: May call Microsoft Graph or SMTP. If neither transport is ready,
        raises ``RuntimeError`` so the existing outbox stores a reviewable draft.
        Flow: Resolves transport once, delegates to the matching sender, and returns
        the transport name for audit and test-result reporting.
        """
        config = self.get_email_transport_config()
        transport = str(config.get("transport") or "draft")
        if not config.get("configured"):
            if transport == "graph":
                raise RuntimeError("Microsoft Graph is not fully configured; message saved as draft")
            if transport == "smtp":
                raise RuntimeError("SMTP is not fully configured; message saved as draft")
            raise RuntimeError("Email delivery is not configured; message saved as draft")
        if transport == "graph":
            self.send_graph_email(to_emails, cc_emails, subject, body)
            return "graph"
        if transport == "smtp":
            self.send_smtp_email(to_emails, cc_emails, subject, body)
            return "smtp"
        raise RuntimeError("Email delivery is disabled; message saved as draft")

    def send_customer_manifests_for_import(self, con: sqlite3.Connection, payload: dict[str, Any], user: str) -> None:
        """Purpose: Send customer manifests for import for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        delivery_date = str(payload.get("deliveryDate") or "")
        items = [item for item in payload.get("items") or [] if isinstance(item, dict)]
        customer_map: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            customer = str(item.get("customer") or "").strip()
            if not customer:
                continue
            customer_map.setdefault(customer, []).append(item)
        cc_emails = self.customer_cc_emails(con)
        for customer, customer_items in customer_map.items():
            contacts = self.customer_email_matches(con, customer)
            if not contacts:
                continue
            to_emails = [row["email"] for row in contacts]
            manifest_items = [
                {
                    "job": item.get("job") or item.get("product") or "-",
                    "order": item.get("order") or "",
                    "item": item.get("item") or "",
                    "qty": item.get("qty") or 0,
                    "dimensions": item.get("dimensions") or "",
                    "route": item.get("route") or "",
                    "product": item.get("product") or "",
                }
                for item in customer_items
            ]
            rows = "\n".join(
                f"- Job {item['job']} | Order {item['order']}-{item['item']} | Qty {item['qty']} | {item['dimensions'] or '-'}"
                for item in manifest_items
            )
            piece_qty = sum(int(item.get("qty") or 0) for item in customer_items)
            subject = f"Delivery manifest for {customer} - {format_display_date(delivery_date)}"
            body = (
                f"Hello,\n\nAttached/available is the current order manifest for {customer}.\n"
                f"Expected ready date: {format_display_date(delivery_date)}\n"
                f"Total pieces: {piece_qty}\n"
                f"Total line items: {len(customer_items)}\n\n"
                f"Order summary:\n{rows}\n\n"
                "This is an automated manifest from Barefoot Facility Services."
            )
            self.queue_email_message(
                con,
                "manifest",
                customer,
                contacts[0]["customer_pattern"],
                delivery_date,
                to_emails,
                cc_emails,
                subject,
                body,
                {"itemCount": len(customer_items), "pieceQty": piece_qty, "items": manifest_items, "user": user},
            )

    def queue_ready_email_if_customer_complete(self, con: sqlite3.Connection, list_id: str, scanned_row: sqlite3.Row, user: str) -> None:
        """Purpose: Send ready email if customer complete for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        list_row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
        if not list_row or "staging" not in str(list_row["stage"] or "").lower():
            return
        customer = str(scanned_row["customer"] or "").strip()
        if not customer:
            return
        contacts = self.customer_email_matches(con, customer)
        if not contacts:
            return
        rows = con.execute(
            """
            SELECT * FROM line_items
            WHERE list_id = ? AND customer = ?
            ORDER BY COALESCE(NULLIF(job, ''), product, order_no), order_no, item_no
            """,
            (list_id, customer),
        ).fetchall()
        if not rows or any(int(row["scanned_qty"] or 0) < int(row["qty"] or 0) for row in rows):
            return
        delivery_date = list_row["delivery_date"]
        subject = f"Order ready - {customer} - {format_display_date(delivery_date)}"
        item_lines = "\n".join(f"- Job {row['job'] or row['product'] or '-'} | Order {row['order_no']}-{row['item_no']} | Qty {row['qty']} | {row['dimensions']}" for row in rows)
        body = (
            f"Hello,\n\nAll staging pieces for {customer} on {format_display_date(delivery_date)} have been scanned.\n"
            "Your order is ready for pickup or shipment based on the assigned route.\n\n"
            f"Pieces:\n{item_lines}\n\n"
            "This is an automated readiness notice from Barefoot Facility Services."
        )
        self.queue_email_message(con, "ready", customer, contacts[0]["customer_pattern"], delivery_date, [row["email"] for row in contacts], self.customer_cc_emails(con), subject, body, {"listId": list_id, "user": user})

    def get_manual_edit_lookups(self) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Read manual edit lookups for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def add_manual_edit_lookup(self, data: dict[str, Any], user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Create manual edit lookup for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def get_bay_scan_settings(self) -> dict[str, Any]:
        """Purpose: Read bay scan settings for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def update_bay_scan_settings(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Update shared Bay Scanner safety settings."""
        raise NotImplementedError

    def upsert_bay_manual_input_rule(self, data: dict[str, Any], user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Run the upsert bay manual input rule workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def remove_bay_manual_input_rule(self, rule_id: int, user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Remove bay manual input rule for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def upsert_bay_scan_barcode_rule(self, data: dict[str, Any], user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Run the upsert bay scan barcode rule workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        raise NotImplementedError

    def remove_bay_scan_barcode_rule(self, rule_id: int, user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Remove bay scan barcode rule for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def manual_assign_bay_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the manual assign bay item workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def reports_summary(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Run the reports summary workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def get_bays(self) -> list[dict[str, Any]]:
        """Purpose: Read bays for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_bay_job_details(self, bay_code: str) -> dict[str, Any]:
        """Purpose: Read bay job details for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_sdi_workspace(self, query: str = "", bay_code: str = "") -> dict[str, Any]:
        """Return predictive SDI lookup options, exact item status, and current priority marks.

        This read-only workspace keeps the SDI modal grounded in Indian Trail destination
        rows so the browser can distinguish physically present items from missing items.
        """
        raise NotImplementedError

    def get_bay_layout(self) -> dict[str, Any]:
        """Purpose: Read bay layout for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        raise NotImplementedError

    def get_bay_events(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """Read a bounded slice of retained physical Bay Map scan activity."""
        raise NotImplementedError

    def get_bay_events_page(self, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """Read one server-paginated page of retained Bay Map scan activity."""
        raise NotImplementedError

    def cleanup_old_bay_events(self, retention_days: int = BAY_EVENT_RETENTION_DAYS, *, force: bool = False) -> int:
        """Delete expired Bay Map activity without touching other operational histories."""
        raise NotImplementedError

    def indian_trail_summary(self, delivery_date: str = "") -> dict[str, Any]:
        """Purpose: Run the indian trail summary workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def indian_trail_in_transit(self, delivery_date: str = "") -> dict[str, Any]:
        """Purpose: Run the indian trail in transit workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def receive_indian_trail_scan(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Process indian trail scan for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        raise NotImplementedError

    def assign_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the assign bay workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def move_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the move bay assignment workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def clear_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove bay for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def mark_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the mark SDI workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def remove_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove SDI for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def bay_check(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the bay check workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def scan_out_bay_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Process out bay item for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        raise NotImplementedError

    def clear_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove bay assignment for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def restore_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the restore bay assignment workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        raise NotImplementedError

    def update_bay_layout(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update bay layout for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError

    def set_bay_group_position(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update bay group position for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        raise NotImplementedError


class SQLiteDeliveryStore(BaseDeliveryStore):
    database_type = "sqlite"

    def __init__(self, config: AppConfig):
        """Purpose: Initialize a SQLite delivery store instance and its required state.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self.config = config
        self.database_path = Path(config.database_path)
        self.sample_path = Path(config.sample_path)
        self._last_bay_event_cleanup_monotonic = 0.0

    def connect(self) -> sqlite3.Connection:
        """Purpose: Run the connect workflow for the delivery-list scanner.

        Effects: This function reads or changes database records, reads or changes files.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self.database_path.parent.mkdir(exist_ok=True)
        timeout_seconds = max(int(self.config.database_timeout_seconds or 30), 1)
        con = sqlite3.connect(
            self.database_path,
            timeout=timeout_seconds,
            factory=ClosingSQLiteConnection,
        )
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute(f"PRAGMA busy_timeout = {timeout_seconds * 1000}")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA synchronous = NORMAL")
        con.execute("PRAGMA temp_store = MEMORY")
        return con

    def health(self) -> dict[str, Any]:
        """Purpose: Run the health workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return {
            "ok": True,
            "mode": self.database_type,
            "database": str(self.database_path),
            "environment": self.config.environment,
            "authMode": self.config.auth_mode,
        }

    def initialize(self) -> None:
        """Purpose: Run the initialize workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        backup_path: Path | None = None
        if database_needs_upgrade(self.database_path):
            backup_path = create_verified_backup(self.database_path)
        try:
            with self.connect() as con:
                self.create_schema(con)
                self.ensure_rack_destination_override_columns(con)
                self.seed_customer_route_rules(con)
                if not self.config.production:
                    self.seed_demo_data(con)
                else:
                    self.seed_stations(con)
                self.seed_security_data(con)
                self.seed_bays(con)
                self.repair_manual_assign_bay_visibility(con)
                self.seed_bay_auto_assign_settings(con)
                self.seed_racks(con)
                self.repair_route_stage_memberships_if_needed(con)
            self.cleanup_old_bay_events(force=True)
        except Exception as exc:
            suffix = f" Verified backup preserved at {backup_path}." if backup_path else ""
            raise MigrationError(f"Database initialization failed.{suffix}") from exc

    def customer_route_rules_from_connection(self, con: Any) -> list[dict[str, Any]]:
        """Purpose: Run the customer route rules from connection workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rows = con.execute(
            "SELECT * FROM customer_route_rules WHERE active = 1 ORDER BY customer_pattern"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "customerPattern": row["customer_pattern"],
                "route": row["route"],
                "customerAddress": row_value(row, "customer_address", ""),
                "active": bool(row["active"]),
            }
            for row in rows
        ]

    def route_stage_repair_signature(self, con: Any) -> str:
        """Purpose: Run the route stage repair signature workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        rules = self.customer_route_rules_from_connection(con)
        route_rules = [
            {
                "customer": normalized_match_text(rule.get("customerPattern", "")),
                "route": str(rule.get("route") or "").strip().upper(),
            }
            for rule in rules
        ]
        payload = json.dumps(
            {"version": ROUTE_STAGE_REPAIR_VERSION, "rules": route_rules},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def system_metadata_value(self, con: Any, key: str) -> str:
        """Purpose: Run the system metadata value workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        row = con.execute("SELECT value FROM system_metadata WHERE metadata_key = ?", (key,)).fetchone()
        return str(row["value"] or "") if row else ""

    def set_system_metadata_value(self, con: Any, key: str, value: str) -> None:
        """Purpose: Update system metadata value for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        con.execute(
            """
            INSERT INTO system_metadata (metadata_key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(metadata_key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, now_iso()),
        )

    def ensure_rack_destination_override_columns(self, con: Any) -> None:
        """Ensure existing databases can retain a temporary rack override window."""
        self.ensure_column(con, "racks", "destination_override_until", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "racks", "destination_override_by", "TEXT NOT NULL DEFAULT ''")

    def repair_route_stage_memberships_if_needed(self, con: Any, *, force: bool = False) -> int:
        """Purpose: Reconcile route stage memberships if needed for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        signature = self.route_stage_repair_signature(con)
        metadata_key = "route_stage_repair_signature"
        if not force and self.system_metadata_value(con, metadata_key) == signature:
            return 0
        repaired = self.repair_route_stage_memberships(
            con,
            rules=self.customer_route_rules_from_connection(con),
        )
        self.set_system_metadata_value(con, metadata_key, signature)
        con.commit()
        return repaired

    def repair_route_stage_memberships(
        self,
        con: Any,
        *,
        rules: list[dict[str, Any]] | None = None,
    ) -> int:
        """Repair active route copies using customer rules without slowing every startup.

        Rows are loaded once and grouped in memory. Unchanged groups require no
        follow-up queries. The expensive repair runs only when the route logic or
        active Customer Route Rules change.
        """
        active_rules = rules if rules is not None else self.customer_route_rules_from_connection(con)
        rows = con.execute(
            """
            SELECT li.*, dl.delivery_date, dl.stage, dl.scanner
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.status = 'active'
            ORDER BY dl.delivery_date, li.source_id, li.order_no, li.item_no, dl.stage
            """
        ).fetchall()
        grouped: dict[tuple[str, str], list[Any]] = {}
        for row in rows:
            source_key = str(row["source_id"] or "").strip() or f"{row['order_no']}::{row['item_no']}"
            grouped.setdefault((str(row["delivery_date"] or ""), source_key), []).append(row)

        repaired = 0
        for (delivery_date, _source_key), siblings in grouped.items():
            representative = next(
                (row for row in siblings if str(row["stage"] or "").lower().startswith("staging")),
                next(
                    (row for row in siblings if str(row["stage"] or "").lower().startswith("outbound")),
                    siblings[0],
                ),
            )
            route_source = {
                "route": row_value(representative, "source_route", "") or representative["route"],
                "sourceRoute": row_value(representative, "source_route", ""),
                "job": representative["job"],
                "customer": representative["customer"],
                "product": representative["product"],
                "processState": representative["process_state"],
                "queueState": representative["queue_state"],
            }
            canonical_route = self.resolve_item_route(route_source, active_rules) or "IT"
            receiving_before = {
                str(row["list_id"])
                for row in siblings
                if not str(row["stage"] or "").lower().startswith("staging")
                and not str(row["stage"] or "").lower().startswith("outbound")
            }
            expected_destination = self.destination_for_line_item({**route_source, "route": canonical_route})
            expected_list_id = self.manual_route_profile(delivery_date, expected_destination)[0]
            route_changed = any(str(row["route"] or "").strip().upper() != canonical_route for row in siblings)
            membership_changed = receiving_before != {expected_list_id}
            if not route_changed and not membership_changed:
                continue

            sibling_ids = [str(row["id"]) for row in siblings]
            placeholders = ",".join("?" for _ in sibling_ids)
            affected_racks = con.execute(
                f"SELECT DISTINCT rack_id FROM rack_items WHERE line_item_id IN ({placeholders}) AND status = 'Active'",
                sibling_ids,
            ).fetchall()
            if route_changed:
                con.execute(
                    f"UPDATE line_items SET route = ? WHERE id IN ({placeholders})",
                    [canonical_route, *sibling_ids],
                )
            if membership_changed:
                refreshed = con.execute(
                    """
                    SELECT li.*, dl.delivery_date, dl.stage, dl.scanner
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE li.id = ?
                    """,
                    (representative["id"],),
                ).fetchone()
                if refreshed:
                    self.sync_manual_route_membership(con, refreshed)
            for rack_row in affected_racks:
                self.refresh_rack_destination(con, int(rack_row["rack_id"]))
            repaired += 1
        return repaired

    def create_schema(self, con: sqlite3.Connection) -> None:
        """Apply the canonical numbered SQLite migrations."""
        run_sqlite_migrations(con, self)

    def _verify_v096_baseline(self, con: sqlite3.Connection) -> None:
        """Refuse to baseline a legacy database that is missing v096 essentials."""
        required = {
            "delivery_lists": {"id", "delivery_date", "stage", "status"},
            "line_items": {"id", "list_id", "order_no", "item_no", "qty", "scanned_qty"},
            "scan_events": {"id", "list_id", "event_type", "created_at"},
            "audit_events": {"id", "entity_type", "action", "created_at"},
            "users": {"id", "username", "active"},
            "racks": {"id", "rack_code", "status"},
            "bays": {"id", "bay_code", "active"},
        }
        missing: list[str] = []
        for table, expected_columns in required.items():
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
            ).fetchone()
            if not exists:
                missing.append(table)
                continue
            actual = {str(row["name"]) for row in con.execute(f"PRAGMA table_info([{table}])").fetchall()}
            absent = sorted(expected_columns - actual)
            if absent:
                missing.append(f"{table}({', '.join(absent)})")
        if missing:
            raise MigrationError("Cannot baseline an incomplete legacy database: " + "; ".join(missing))

    def _migration_001_v096_baseline(self, con: sqlite3.Connection) -> None:
        """Create the complete v096 schema for a new empty database.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
                source_route TEXT NOT NULL DEFAULT '',
                job TEXT NOT NULL DEFAULT '',
                product TEXT NOT NULL DEFAULT '',
                process_state TEXT NOT NULL DEFAULT '',
                queue_state TEXT NOT NULL DEFAULT '',
                suggested_bay TEXT NOT NULL DEFAULT '',
                priority_delivery_date TEXT NOT NULL DEFAULT '',
                priority_direct_to_truck INTEGER NOT NULL DEFAULT 0
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
                customer_address TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS system_metadata (
                metadata_key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS admin_lookup_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                value TEXT NOT NULL,
                label TEXT NOT NULL,
                category TEXT,
                match_terms TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(type, value)
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
                email TEXT NOT NULL DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT NOT NULL DEFAULT '',
                requested_by TEXT NOT NULL DEFAULT ''
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

            CREATE TABLE IF NOT EXISTS racks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_code TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                rack_type TEXT NOT NULL DEFAULT 'Steel',
                status TEXT NOT NULL DEFAULT 'Open',
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS rack_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_id INTEGER NOT NULL REFERENCES racks(id) ON DELETE CASCADE,
                line_item_id TEXT NOT NULL REFERENCES line_items(id) ON DELETE CASCADE,
                qty INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'Active',
                added_by TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL,
                removed_by TEXT NOT NULL DEFAULT '',
                removed_at TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                destination_override TEXT NOT NULL DEFAULT '',
                UNIQUE(rack_id, line_item_id)
            );

            CREATE TABLE IF NOT EXISTS bay_stale_snoozes (
                assignment_id INTEGER PRIMARY KEY REFERENCES bay_assignments(id) ON DELETE CASCADE,
                snoozed_until TEXT NOT NULL,
                snoozed_by TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bay_manual_input_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_type TEXT NOT NULL DEFAULT 'exact',
                pattern TEXT NOT NULL,
                normalized_pattern TEXT NOT NULL DEFAULT '',
                label TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS bay_scan_barcode_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS bay_auto_assign_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_by TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS customer_email_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_pattern TEXT NOT NULL,
                email TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT '',
                UNIQUE(customer_pattern, email)
            );

            CREATE TABLE IF NOT EXISTS customer_email_cc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS email_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_type TEXT NOT NULL,
                customer_name TEXT NOT NULL DEFAULT '',
                customer_pattern TEXT NOT NULL DEFAULT '',
                delivery_date TEXT NOT NULL DEFAULT '',
                to_emails TEXT NOT NULL DEFAULT '[]',
                cc_emails TEXT NOT NULL DEFAULT '[]',
                subject TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}'
            );


            CREATE TABLE IF NOT EXISTS app_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT NOT NULL DEFAULT 'notice',
                title TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS app_notification_receipts (
                notification_id INTEGER NOT NULL REFERENCES app_notifications(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                acknowledged_at TEXT NOT NULL,
                PRIMARY KEY (notification_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_app_notifications_active_time
                ON app_notifications(active, created_at DESC, id DESC);
            """
        )
        self._upgrade_v096_columns(con)

    def _upgrade_v096_columns(self, con: Any) -> None:
        """Apply the historical pre-v097 compatibility columns to a new baseline.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self.ensure_column(con, "bays", "display_name", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "map_section", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "bay_category", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "source_cell", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "layout_row", "INTEGER")
        self.ensure_column(con, "bays", "layout_col", "INTEGER")
        self.ensure_column(con, "bays", "layout_cell", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "bays", "status", "TEXT NOT NULL DEFAULT 'Available'")
        self.ensure_column(con, "customer_route_rules", "customer_address", "TEXT NOT NULL DEFAULT ''")
        con.execute(
            """
            UPDATE customer_route_rules
            SET customer_address = ?
            WHERE active = 1
              AND UPPER(route) IN ('CPU', 'CUSTOMER PICKUP')
              AND COALESCE(customer_address, '') = ''
            """,
            (CPU_DESTINATION_ADDRESS,),
        )
        self.ensure_column(con, "users", "email", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "imports", "source_path", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "imports", "source_hash", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "imports", "import_kind", "TEXT NOT NULL DEFAULT 'manual'")
        self.ensure_column(con, "imports", "change_summary", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "users", "station", "TEXT NOT NULL DEFAULT ''")
        # Rack destination/transport lifecycle columns. Status remains the visible
        # rack state (Open, Closed, In Transit), while destination tracks where
        # a completed rack is heading so Indian Trail only sees its own inbound racks.
        self.ensure_column(con, "racks", "destination", "TEXT NOT NULL DEFAULT ''")
        self.ensure_rack_destination_override_columns(con)
        self.ensure_column(con, "racks", "completed_at", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "racks", "departed_at", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "racks", "returned_at", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "rack_items", "destination_override", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "line_items", "source_route", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "line_items", "priority_delivery_date", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, "line_items", "priority_direct_to_truck", "INTEGER NOT NULL DEFAULT 0")
        con.commit()

    def ensure_column(self, con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        """Purpose: Validate column for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _add_v097_audit_columns(self, con: sqlite3.Connection, table: str) -> None:
        """Add non-breaking UTC audit and soft-delete fields to a mutable table."""
        self.ensure_column(con, table, "created_at_utc", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, table, "created_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL")
        self.ensure_column(con, table, "updated_at_utc", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, table, "updated_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL")
        self.ensure_column(con, table, "is_deleted", "INTEGER NOT NULL DEFAULT 0")
        self.ensure_column(con, table, "deleted_at_utc", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column(con, table, "deleted_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL")

    def _migration_002_v097_production_database(self, con: sqlite3.Connection) -> None:
        """Harden v096 in place while preserving every existing business row."""
        migrated_at = now_iso()
        for table in (
            "delivery_lists",
            "line_items",
            "users",
            "bays",
            "bay_assignments",
            "racks",
            "rack_items",
            "customer_route_rules",
            "admin_lookup_values",
        ):
            self._add_v097_audit_columns(con, table)

        con.execute(
            "UPDATE delivery_lists SET created_at_utc = CASE WHEN created_at_utc = '' THEN created_at ELSE created_at_utc END, "
            "updated_at_utc = CASE WHEN updated_at_utc = '' THEN created_at ELSE updated_at_utc END"
        )
        con.execute(
            "UPDATE users SET created_at_utc = CASE WHEN created_at_utc = '' THEN created_at ELSE created_at_utc END, "
            "updated_at_utc = CASE WHEN updated_at_utc = '' THEN created_at ELSE updated_at_utc END"
        )
        con.execute(
            "UPDATE racks SET created_at_utc = CASE WHEN created_at_utc = '' THEN created_at ELSE created_at_utc END, "
            "updated_at_utc = CASE WHEN updated_at_utc = '' THEN COALESCE(NULLIF(updated_at, ''), created_at) ELSE updated_at_utc END"
        )
        con.execute(
            "UPDATE customer_route_rules SET created_at_utc = CASE WHEN created_at_utc = '' THEN created_at ELSE created_at_utc END, "
            "updated_at_utc = CASE WHEN updated_at_utc = '' THEN COALESCE(NULLIF(updated_at, ''), created_at) ELSE updated_at_utc END"
        )
        con.execute(
            "UPDATE admin_lookup_values SET created_at_utc = CASE WHEN created_at_utc = '' THEN created_at ELSE created_at_utc END, "
            "updated_at_utc = CASE WHEN updated_at_utc = '' THEN COALESCE(NULLIF(updated_at, ''), created_at) ELSE updated_at_utc END"
        )
        for table in ("line_items", "bays", "bay_assignments", "rack_items"):
            con.execute(
                f"UPDATE [{table}] SET created_at_utc = CASE WHEN created_at_utc = '' THEN ? ELSE created_at_utc END, "
                "updated_at_utc = CASE WHEN updated_at_utc = '' THEN ? ELSE updated_at_utc END",
                (migrated_at, migrated_at),
            )

        # Rebuild the quantity-bearing tables so SQLite has real CHECK
        # constraints. Foreign keys are disabled by the runner only for this
        # transaction and verified immediately after commit.
        con.execute(
            """
            CREATE TABLE line_items_v097 (
                id TEXT PRIMARY KEY,
                list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
                source_id TEXT NOT NULL,
                barcode TEXT NOT NULL,
                order_no TEXT NOT NULL,
                item_no TEXT NOT NULL,
                qty INTEGER NOT NULL CHECK (qty >= 0),
                scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (scanned_qty >= 0 AND scanned_qty <= qty),
                dimensions TEXT NOT NULL DEFAULT '',
                customer TEXT NOT NULL DEFAULT '',
                route TEXT NOT NULL DEFAULT '',
                job TEXT NOT NULL DEFAULT '',
                product TEXT NOT NULL DEFAULT '',
                process_state TEXT NOT NULL DEFAULT '',
                queue_state TEXT NOT NULL DEFAULT '',
                suggested_bay TEXT NOT NULL DEFAULT '',
                priority_delivery_date TEXT NOT NULL DEFAULT '',
                priority_direct_to_truck INTEGER NOT NULL DEFAULT 0 CHECK (priority_direct_to_truck IN (0, 1)),
                source_route TEXT NOT NULL DEFAULT '',
                created_at_utc TEXT NOT NULL DEFAULT '',
                created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_at_utc TEXT NOT NULL DEFAULT '',
                updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
                deleted_at_utc TEXT NOT NULL DEFAULT '',
                deleted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        line_columns = (
            "id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty, dimensions, customer, route, job, "
            "product, process_state, queue_state, suggested_bay, priority_delivery_date, priority_direct_to_truck, "
            "source_route, created_at_utc, created_by_user_id, updated_at_utc, updated_by_user_id, is_deleted, "
            "deleted_at_utc, deleted_by_user_id"
        )
        con.execute(f"INSERT INTO line_items_v097 ({line_columns}) SELECT {line_columns} FROM line_items")
        con.execute("DROP TABLE line_items")
        con.execute("ALTER TABLE line_items_v097 RENAME TO line_items")

        con.execute(
            """
            CREATE TABLE rack_items_v097 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_id INTEGER NOT NULL REFERENCES racks(id) ON DELETE CASCADE,
                line_item_id TEXT NOT NULL REFERENCES line_items(id) ON DELETE CASCADE,
                qty INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
                status TEXT NOT NULL DEFAULT 'Active',
                added_by TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL,
                removed_by TEXT NOT NULL DEFAULT '',
                removed_at TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                destination_override TEXT NOT NULL DEFAULT '',
                created_at_utc TEXT NOT NULL DEFAULT '',
                created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_at_utc TEXT NOT NULL DEFAULT '',
                updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
                deleted_at_utc TEXT NOT NULL DEFAULT '',
                deleted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE(rack_id, line_item_id)
            )
            """
        )
        rack_item_columns = (
            "id, rack_id, line_item_id, qty, status, added_by, added_at, removed_by, removed_at, reason, "
            "destination_override, created_at_utc, created_by_user_id, updated_at_utc, updated_by_user_id, "
            "is_deleted, deleted_at_utc, deleted_by_user_id"
        )
        con.execute(f"INSERT INTO rack_items_v097 ({rack_item_columns}) SELECT {rack_item_columns} FROM rack_items")
        con.execute("DROP TABLE rack_items")
        con.execute("ALTER TABLE rack_items_v097 RENAME TO rack_items")

        con.execute(
            """
            CREATE TABLE exceptions_v097 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
                scan_event_id INTEGER REFERENCES scan_events(id) ON DELETE SET NULL,
                exception_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                resolved_by TEXT NOT NULL DEFAULT '',
                resolved_at TEXT NOT NULL DEFAULT '',
                resolution_comment TEXT NOT NULL DEFAULT ''
            )
            """
        )
        exception_columns = (
            "id, list_id, scan_event_id, exception_type, status, reason, created_at, resolved_by, resolved_at, resolution_comment"
        )
        con.execute(f"INSERT INTO exceptions_v097 ({exception_columns}) SELECT {exception_columns} FROM exceptions")
        con.execute("DROP TABLE exceptions")
        con.execute("ALTER TABLE exceptions_v097 RENAME TO exceptions")

        # line_item_id remains a durable textual historical reference here.
        # v096 legitimately contains cleared/replaced line IDs that no longer
        # exist, so forcing a line-item FK would destroy valid bay history.
        con.execute(
            """
            CREATE TABLE bay_assignments_v097 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_list_id TEXT NOT NULL REFERENCES delivery_lists(id) ON DELETE CASCADE,
                line_item_id TEXT NOT NULL,
                bay_id INTEGER REFERENCES bays(id) ON DELETE SET NULL,
                assigned_qty INTEGER NOT NULL DEFAULT 0 CHECK (assigned_qty >= 0),
                status TEXT NOT NULL DEFAULT 'Assigned',
                assigned_by TEXT NOT NULL DEFAULT '',
                assigned_at TEXT NOT NULL,
                cleared_by TEXT NOT NULL DEFAULT '',
                cleared_at TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                created_at_utc TEXT NOT NULL DEFAULT '',
                created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_at_utc TEXT NOT NULL DEFAULT '',
                updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
                deleted_at_utc TEXT NOT NULL DEFAULT '',
                deleted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        assignment_columns = (
            "id, delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, cleared_by, "
            "cleared_at, reason, created_at_utc, created_by_user_id, updated_at_utc, updated_by_user_id, is_deleted, "
            "deleted_at_utc, deleted_by_user_id"
        )
        con.execute(
            f"INSERT INTO bay_assignments_v097 ({assignment_columns}) SELECT {assignment_columns} FROM bay_assignments"
        )
        con.execute("DROP TABLE bay_assignments")
        con.execute("ALTER TABLE bay_assignments_v097 RENAME TO bay_assignments")

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_code TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                machine_type TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
                created_at_utc TEXT NOT NULL,
                created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_at_utc TEXT NOT NULL DEFAULT '',
                updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
                deleted_at_utc TEXT NOT NULL DEFAULT '',
                deleted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS scanners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanner_code TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                station_name TEXT NOT NULL DEFAULT '',
                machine_id INTEGER REFERENCES machines(id) ON DELETE SET NULL,
                device_identifier TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                last_seen_at_utc TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
                created_at_utc TEXT NOT NULL,
                created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_at_utc TEXT NOT NULL DEFAULT '',
                updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
                deleted_at_utc TEXT NOT NULL DEFAULT '',
                deleted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS machine_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER REFERENCES machines(id) ON DELETE SET NULL,
                scanner_id INTEGER REFERENCES scanners(id) ON DELETE SET NULL,
                line_item_id TEXT REFERENCES line_items(id) ON DELETE SET NULL,
                event_type TEXT NOT NULL,
                event_status TEXT NOT NULL DEFAULT '',
                qty INTEGER NOT NULL DEFAULT 0 CHECK (qty >= 0),
                barcode TEXT NOT NULL DEFAULT '',
                order_no TEXT NOT NULL DEFAULT '',
                item_no TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
                created_at_utc TEXT NOT NULL,
                created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        index_sql = (
            "CREATE INDEX IF NOT EXISTS idx_delivery_lists_date_status_stage ON delivery_lists(delivery_date, status, stage)",
            "CREATE INDEX IF NOT EXISTS idx_line_items_list_order_item ON line_items(list_id, order_no, item_no)",
            "CREATE INDEX IF NOT EXISTS idx_line_items_source ON line_items(source_id, list_id)",
            "CREATE INDEX IF NOT EXISTS idx_line_items_barcode ON line_items(barcode, list_id)",
            "CREATE INDEX IF NOT EXISTS idx_scan_events_line_time ON scan_events(line_item_id, created_at DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_imports_date_time ON imports(delivery_date, imported_at DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_exceptions_list_status ON exceptions(list_id, status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_entity_time ON audit_events(entity_type, entity_id, created_at DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_expiry ON sessions(user_id, expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_bay_assignments_line_status ON bay_assignments(line_item_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_bay_assignments_bay_status ON bay_assignments(bay_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_bay_events_bay_time ON bay_events(bay_id, created_at DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rack_items_rack_status ON rack_items(rack_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_rack_items_line_status ON rack_items(line_item_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_machine_events_machine_time ON machine_events(machine_id, created_at_utc DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_machine_events_scanner_time ON machine_events(scanner_id, created_at_utc DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_machine_events_order_item ON machine_events(order_no, item_no, created_at_utc DESC)",
        )
        for statement in index_sql:
            con.execute(statement)

        # Existing boolean columns cannot receive a table-level CHECK without
        # rebuilding every dependent table. Equivalent constraint triggers keep
        # the upgrade low risk while enforcing all future writes.
        boolean_constraints = {
            "bays": ("active",),
            "racks": ("active",),
            "users": ("active",),
            "customer_route_rules": ("active",),
            "admin_lookup_values": ("is_active",),
            "app_notifications": ("active",),
        }
        for table, columns in boolean_constraints.items():
            for column in columns:
                for operation, reference in (("INSERT", "NEW"), ("UPDATE", "NEW")):
                    trigger = f"trg_{table}_{column}_{operation.lower()}_boolean"
                    con.execute(
                        f"CREATE TRIGGER IF NOT EXISTS [{trigger}] BEFORE {operation} ON [{table}] "
                        f"WHEN {reference}.[{column}] NOT IN (0, 1) BEGIN SELECT RAISE(ABORT, '{table}.{column} must be 0 or 1'); END"
                    )

        for table in ("scan_events", "audit_events", "machine_events"):
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS trg_{table}_immutable_update BEFORE UPDATE ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
            )
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS trg_{table}_immutable_delete BEFORE DELETE ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
            )

        for table in (
            "delivery_lists",
            "line_items",
            "users",
            "bays",
            "bay_assignments",
            "racks",
            "rack_items",
            "customer_route_rules",
            "admin_lookup_values",
        ):
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS trg_{table}_utc_insert AFTER INSERT ON [{table}] "
                f"WHEN NEW.created_at_utc = '' BEGIN UPDATE [{table}] SET "
                "created_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
                "updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE rowid = NEW.rowid; END"
            )
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS trg_{table}_utc_update AFTER UPDATE ON [{table}] "
                f"WHEN NEW.updated_at_utc = OLD.updated_at_utc BEGIN UPDATE [{table}] SET "
                "updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE rowid = NEW.rowid; END"
            )

    def _migration_003_v120_user_line_updates(self, con: sqlite3.Connection) -> None:
        """Add persistent per-user review state for current/future import changes."""
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS line_update_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_item_id TEXT NOT NULL,
                list_id TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                change_type TEXT NOT NULL CHECK (change_type IN ('new', 'updated')),
                change_token TEXT NOT NULL,
                source_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(line_item_id, change_type, change_token)
            );

            CREATE TABLE IF NOT EXISTS line_update_receipts (
                notice_id INTEGER NOT NULL REFERENCES line_update_notices(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                seen_at TEXT NOT NULL,
                PRIMARY KEY (notice_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_line_update_notices_list_date
                ON line_update_notices(list_id, delivery_date, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_line_update_receipts_user
                ON line_update_receipts(user_id, notice_id);
            """
        )
    def clone_item_for_list(self, item: dict[str, Any], list_id: str, index: int, auto_assign_settings: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Run the clone item for list workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        order_no = str(item["order"])
        item_no = str(item["item"]).zfill(3)
        explicit, canonical_route = normalize_route_column(item.get("route", ""))
        if explicit:
            route = canonical_route or "IT"
        else:
            inferred = inferred_route(item)
            route = inferred or ("IT" if job_number_route_hint(item) is not None else "")
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
            "source_route": str(item.get("sourceRoute", item.get("route", ""))),
            "job": str(item.get("job", "")),
            "product": product,
            "process_state": str(item.get("processState", "")),
            "queue_state": str(item.get("queueState", "")),
            "suggested_bay": suggested_bay(product, dimensions, route, auto_assign_settings),
        }

    def available_line_item_id(
        self,
        con: sqlite3.Connection,
        desired_id: str,
        list_id: str,
        source_id: str,
        index: int,
    ) -> str:
        """Return a stable, unused line-item ID when an older stage move owns the desired ID.

        Effects: Reads the global line-item ID namespace but does not modify database state.
        Flow: Uses the normal deterministic ID when available. If that ID belongs to another
        delivery list, derives a stable suffix from the intended list/source/index and checks
        progressively numbered fallbacks. A collision inside the same list remains an error
        because inserting it would duplicate one line within that delivery list.
        """
        existing = con.execute("SELECT list_id FROM line_items WHERE id = ?", (desired_id,)).fetchone()
        if not existing:
            return desired_id
        if str(existing["list_id"] or "") == str(list_id):
            raise sqlite3.IntegrityError(f"Duplicate line item ID within delivery list: {desired_id}")

        identity = f"{list_id}{source_id}{index}".encode("utf-8")
        suffix = hashlib.sha1(identity).hexdigest()[:10]
        candidate = f"{desired_id}-copy-{suffix}"
        attempt = 1
        while con.execute("SELECT 1 FROM line_items WHERE id = ?", (candidate,)).fetchone():
            attempt += 1
            candidate = f"{desired_id}-copy-{suffix}-{attempt}"
        return candidate

    def insert_line_items(self, con: sqlite3.Connection, list_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Purpose: Create line items for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, assigns a globally safe line-item ID, inserts each normalized
        row, and returns the inserted records to the import/update preservation workflow.
        """
        cloned_items = []
        auto_assign_settings = self.get_bay_auto_assign_settings_con(con)
        for index, item in enumerate(items, start=1):
            cloned = self.clone_item_for_list(item, list_id, index, auto_assign_settings)
            cloned["id"] = self.available_line_item_id(
                con,
                str(cloned["id"]),
                list_id,
                str(cloned["source_id"]),
                index,
            )
            cloned_items.append(cloned)
            con.execute(
                """
                INSERT INTO line_items (
                    id, list_id, source_id, barcode, order_no, item_no, qty,
                    dimensions, customer, route, source_route, job, product, process_state,
                    queue_state, suggested_bay
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    cloned["source_route"],
                    cloned["job"],
                    cloned["product"],
                    cloned["process_state"],
                    cloned["queue_state"],
                    cloned["suggested_bay"],
                ),
            )
        return cloned_items

    def import_order_item_key(self, value: Any, order_no: Any, item_no: Any) -> str:
        """Purpose: Load order item key for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        source_text = str(value or "").strip()
        parts = source_text.split(":")
        if len(parts) >= 2 and parts[-2].strip().isdigit() and parts[-1].strip().isdigit():
            return f"{parts[-2].strip()}-{parts[-1].strip().zfill(3)}"
        return f"{str(order_no or '').strip()}-{str(item_no or '').strip().zfill(3)}"

    def import_business_key(self, values: dict[str, Any]) -> str:
        """Purpose: Load business key for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        def field(name: str) -> Any:
            """Purpose: Run the field workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            if hasattr(values, "keys") and name in values.keys():
                return values[name]
            return values.get(name) if isinstance(values, dict) else ""

        parts = [
            str(field("order_no") or "").strip(),
            str(field("item_no") or "").strip().zfill(3),
            str(field("dimensions") or "").strip().upper(),
            str(field("customer") or "").strip().upper(),
            str(field("product") or "").strip().upper(),
        ]
        return "\x1f".join(parts)

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
    ) -> dict[str, Any]:
        """Purpose: Run the upsert delivery list workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        existing = con.execute("SELECT revision, created_at FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
        created = existing["created_at"] if existing else now_iso()
        revision = int(existing["revision"]) + 1 if existing and replace_items else int(existing["revision"]) if existing else 1
        con.execute(
            """
            INSERT INTO delivery_lists (
                id, label, delivery_date, stage, scanner, status, revision, created_at,
                created_at_utc, updated_at_utc, is_deleted, deleted_at_utc, deleted_by_user_id
            )
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, 0, '', NULL)
            ON CONFLICT(id) DO UPDATE SET
                label = excluded.label,
                delivery_date = excluded.delivery_date,
                stage = excluded.stage,
                scanner = excluded.scanner,
                status = 'active',
                revision = excluded.revision,
                updated_at_utc = excluded.updated_at_utc,
                is_deleted = 0,
                deleted_at_utc = '',
                deleted_by_user_id = NULL
            """,
            (list_id, label, delivery_date, stage, scanner, revision, created, created, now_iso()),
        )
        summary = {
            "listId": list_id,
            "stage": stage,
            "scanner": scanner,
            "created": not bool(existing),
            "newPieceQty": 0,
            "updatedPieceQty": 0,
            "addedPieceQty": 0,
            "changedPieceQty": 0,
            "changedLineCount": 0,
            "originalQty": 0,
            "totalQty": sum(int(item.get("qty") or 0) for item in items),
        }
        if replace_items:
            previous_by_id: dict[str, dict[str, Any]] = {}
            previous_pools: dict[str, dict[str, list[dict[str, Any]]]] = {
                "source": {},
                "order_item": {},
                "business": {},
            }
            preserved_rack_items: list[dict[str, Any]] = []
            # DLS_V135_PRESERVE_MANUAL_LINES: keep manually added orders through
            # every automatic folder/SQL refresh until the source file contains
            # the same order/item and takes ownership of it.
            preserved_manual_items: list[dict[str, Any]] = []
            original_total_qty = 0

            def add_previous_to_pool(pool_name: str, key: str, record: dict[str, Any]) -> None:
                """Purpose: Create previous to pool for the delivery-list scanner workflow.

                Effects: Performs an in-memory calculation and returns data without intentional external side effects.
                Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
                """
                if not key:
                    return
                previous_pools[pool_name].setdefault(key, []).append(record)

            for row in con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall():
                scanned_qty = int(row["scanned_qty"] or 0)
                source_key = str(row["source_id"])
                order_item_key = f"{row['order_no']}-{str(row['item_no']).zfill(3)}"
                line_key = str(row["id"])
                source_match_key = self.import_order_item_key(source_key, row["order_no"], row["item_no"])
                previous_payload = {
                    "qty": int(row["qty"] or 0),
                    "dimensions": str(row["dimensions"] or ""),
                    "customer": str(row["customer"] or ""),
                    "route": str(row["route"] or ""),
                    "source_route": str(row_value(row, "source_route", "") or ""),
                    "job": str(row["job"] or ""),
                    "product": str(row["product"] or ""),
                    "process_state": str(row["process_state"] or ""),
                    "queue_state": str(row["queue_state"] or ""),
                    "priority_delivery_date": str(row_value(row, "priority_delivery_date") or ""),
                    "priority_direct_to_truck": int(row_value(row, "priority_direct_to_truck", 0) or 0),
                }
                record = {
                    "id": line_key,
                    "source_id": source_key,
                    "order_item_key": order_item_key,
                    "source_match_key": source_match_key,
                    "business_key": self.import_business_key(row),
                    "payload": previous_payload,
                    "scanned_qty": scanned_qty,
                }
                manual_source = str(row_value(row, "manual_source", "") or "")
                manual_only = int(row_value(row, "manual_only", 0) or 0)
                if manual_source or manual_only:
                    preserved_manual_items.append(
                        {
                            "source_id": source_key,
                            "order_item_key": order_item_key,
                            "manual_only": manual_only,
                            "manual_source": manual_source,
                            "clone": {
                                "id": line_key,
                                "source_id": source_key,
                                "barcode": str(row["barcode"] or ""),
                                "order_no": str(row["order_no"] or ""),
                                "item_no": str(row["item_no"] or "").zfill(3),
                                "qty": int(row["qty"] or 0),
                                "scanned_qty": scanned_qty,
                                "dimensions": str(row["dimensions"] or ""),
                                "customer": str(row["customer"] or ""),
                                "route": str(row["route"] or ""),
                                "source_route": str(row_value(row, "source_route", "manual") or "manual"),
                                "job": str(row["job"] or ""),
                                "product": str(row["product"] or ""),
                                "process_state": str(row["process_state"] or ""),
                                "queue_state": str(row["queue_state"] or ""),
                                "suggested_bay": str(row["suggested_bay"] or ""),
                                "priority_delivery_date": str(row_value(row, "priority_delivery_date", "") or ""),
                                "priority_direct_to_truck": int(row_value(row, "priority_direct_to_truck", 0) or 0),
                                "internal_reject_count": int(row_value(row, "internal_reject_count", 0) or 0),
                                "last_reject_reason": str(row_value(row, "last_reject_reason", "") or ""),
                                "last_reject_location": str(row_value(row, "last_reject_location", "") or ""),
                                "last_rejected_at": str(row_value(row, "last_rejected_at", "") or ""),
                            },
                        }
                    )
                original_total_qty += int(row["qty"] or 0)
                previous_by_id[line_key] = record
                add_previous_to_pool("source", source_match_key, record)
                add_previous_to_pool("order_item", order_item_key, record)
                add_previous_to_pool("business", record["business_key"], record)
            preserved_rack_items = [
                {
                    "rack_id": row["rack_id"],
                    "source_id": str(row["source_id"] or ""),
                    "order_item_key": f"{row['order_no']}-{str(row['item_no']).zfill(3)}",
                    "qty": int(row["qty"] or 1),
                    "added_by": str(row["added_by"] or ""),
                    "added_at": str(row["added_at"] or now_iso()),
                    "reason": str(row["reason"] or "Preserved during delivery-list refresh"),
                }
                for row in con.execute(
                    """
                    SELECT ri.*, li.source_id, li.order_no, li.item_no
                    FROM rack_items ri
                    JOIN line_items li ON li.id = ri.line_item_id
                    WHERE li.list_id = ? AND ri.status = 'Active'
                    """,
                    (list_id,),
                ).fetchall()
            ]
            incoming_order_keys = {
                f"{str(item.get('order') or '').strip()}-{str(item.get('item') or '').strip().zfill(3)}"
                for item in items
            }
            preserved_manual_total = sum(
                int(record["clone"]["qty"] or 0)
                for record in preserved_manual_items
                if record["order_item_key"] not in incoming_order_keys
            )
            summary["totalQty"] = sum(int(item.get("qty") or 0) for item in items) + preserved_manual_total

            con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
            cloned_items = self.insert_line_items(con, list_id, items)
            for manual_record in preserved_manual_items:
                if manual_record["order_item_key"] in incoming_order_keys:
                    continue
                cloned = manual_record["clone"]
                con.execute(
                    "INSERT INTO line_items ("
                    "id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty, "
                    "dimensions, customer, route, source_route, job, product, process_state, "
                    "queue_state, suggested_bay, priority_delivery_date, priority_direct_to_truck, "
                    "manual_only, manual_source, internal_reject_count, last_reject_reason, "
                    "last_reject_location, last_rejected_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        cloned["id"], list_id, cloned["source_id"], cloned["barcode"],
                        cloned["order_no"], cloned["item_no"], cloned["qty"], cloned["scanned_qty"],
                        cloned["dimensions"], cloned["customer"], cloned["route"], cloned["source_route"],
                        cloned["job"], cloned["product"], cloned["process_state"], cloned["queue_state"],
                        cloned["suggested_bay"], cloned["priority_delivery_date"],
                        cloned["priority_direct_to_truck"], manual_record["manual_only"],
                        manual_record["manual_source"], cloned["internal_reject_count"],
                        cloned["last_reject_reason"], cloned["last_reject_location"], cloned["last_rejected_at"],
                    ),
                )
                cloned_items.append(cloned)
            summary["originalQty"] = original_total_qty
            if not existing:
                summary["newPieceQty"] = summary["totalQty"]
                summary["addedPieceQty"] = summary["totalQty"]
                summary["changedPieceQty"] = summary["totalQty"]
                summary["changedLineCount"] = len(cloned_items)
            cloned_by_key: dict[str, dict[str, Any]] = {}
            for cloned in cloned_items:
                cloned_by_key[str(cloned["source_id"])] = cloned
                cloned_by_key[f"{cloned['order_no']}-{str(cloned['item_no']).zfill(3)}"] = cloned
            used_previous_ids: set[str] = set()

            def pop_previous(pool_name: str, key: str) -> dict[str, Any] | None:
                """Purpose: Run the pop previous workflow for the delivery-list scanner.

                Effects: Performs an in-memory calculation and returns data without intentional external side effects.
                Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
                """
                pool = previous_pools[pool_name].get(key) or []
                while pool:
                    candidate = pool.pop(0)
                    if candidate["id"] not in used_previous_ids:
                        used_previous_ids.add(candidate["id"])
                        return candidate
                return None

            def match_previous(cloned: dict[str, Any]) -> dict[str, Any] | None:
                """Purpose: Resolve previous for the delivery-list scanner workflow.

                Effects: This function reads or updates shared application state.
                Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
                """
                cloned_line_key = str(cloned["id"])
                exact = previous_by_id.get(cloned_line_key)
                if exact and exact["id"] not in used_previous_ids:
                    used_previous_ids.add(exact["id"])
                    return exact
                source_match_key = self.import_order_item_key(cloned["source_id"], cloned["order_no"], cloned["item_no"])
                return (
                    pop_previous("source", source_match_key)
                    or pop_previous("business", self.import_business_key(cloned))
                    or pop_previous("order_item", f"{cloned['order_no']}-{str(cloned['item_no']).zfill(3)}")
                )

            for cloned in cloned_items:
                previous_record = match_previous(cloned) if existing else None
                previous = previous_record["payload"] if previous_record else None
                preserved = previous_record["scanned_qty"] if previous_record else 0
                if preserved:
                    con.execute(
                        "UPDATE line_items SET scanned_qty = ? WHERE id = ?",
                        (min(int(preserved), int(cloned["qty"])), cloned["id"]),
                    )
                priority_delivery_date = str(previous.get("priority_delivery_date") or "") if previous else ""
                priority_direct_to_truck = int(previous.get("priority_direct_to_truck") or 0) if previous else 0
                previous_priority_state = str(previous.get("process_state") or "") if previous else ""
                cloned_priority_state = str(cloned.get("process_state") or "")
                preserved_priority_labels: list[str] = []
                if is_rush_item({"processState": previous_priority_state}) and not is_rush_item({"processState": cloned_priority_state}):
                    preserved_priority_labels.append("Rush")
                if is_remake_item({"processState": previous_priority_state}) and not is_remake_item({"processState": cloned_priority_state}):
                    preserved_priority_labels.append("Remake")
                if preserved_priority_labels:
                    cloned_priority_state = " ".join([cloned_priority_state, *preserved_priority_labels]).strip()
                if priority_delivery_date or priority_direct_to_truck or preserved_priority_labels:
                    con.execute(
                        """
                        UPDATE line_items
                        SET process_state = ?, priority_delivery_date = ?, priority_direct_to_truck = ?
                        WHERE id = ?
                        """,
                        (cloned_priority_state, priority_delivery_date, priority_direct_to_truck, cloned["id"]),
                    )
                if existing and not previous:
                    next_state = " ".join(part for part in [cloned["process_state"], "New Line"] if part).strip()
                    con.execute("UPDATE line_items SET process_state = ? WHERE id = ?", (next_state, cloned["id"]))
                    summary["newPieceQty"] += int(cloned["qty"] or 0)
                    summary["addedPieceQty"] += int(cloned["qty"] or 0)
                    summary["changedPieceQty"] += int(cloned["qty"] or 0)
                    summary["changedLineCount"] += 1
                elif existing:
                    current = {
                        "qty": int(cloned["qty"] or 0),
                        "dimensions": str(cloned["dimensions"] or ""),
                        "customer": str(cloned["customer"] or ""),
                        "route": str(cloned["route"] or ""),
                        "source_route": str(cloned["source_route"] or ""),
                        "job": str(cloned["job"] or ""),
                        "product": str(cloned["product"] or ""),
                        "queue_state": str(cloned["queue_state"] or ""),
                    }
                    previous_comparable = {key: previous.get(key, "") for key in current} if previous else {}
                    if previous and previous_comparable != current:
                        state_text = str(cloned["process_state"] or "")
                        next_state = state_text if re.search(r"\bUpdated Line\b", state_text, flags=re.IGNORECASE) else " ".join(part for part in [state_text, "Updated Line"] if part).strip()
                        con.execute("UPDATE line_items SET process_state = ? WHERE id = ?", (next_state, cloned["id"]))
                        qty_delta = max(int(cloned["qty"] or 0) - int(previous.get("qty") or 0), 0)
                        summary["updatedPieceQty"] += int(cloned["qty"] or 0)
                        summary["addedPieceQty"] += qty_delta
                        summary["changedPieceQty"] += int(cloned["qty"] or 0)
                        summary["changedLineCount"] += 1
            for preserved_rack in preserved_rack_items:
                cloned = cloned_by_key.get(preserved_rack["source_id"]) or cloned_by_key.get(preserved_rack["order_item_key"])
                if not cloned:
                    continue
                con.execute(
                    """
                    INSERT INTO rack_items (rack_id, line_item_id, qty, status, added_by, added_at, reason)
                    VALUES (?, ?, ?, 'Active', ?, ?, ?)
                    ON CONFLICT(rack_id, line_item_id) DO UPDATE SET
                        qty = MAX(qty, excluded.qty),
                        status = 'Active',
                        removed_by = '',
                        removed_at = '',
                        reason = excluded.reason,
                        added_by = excluded.added_by,
                        added_at = excluded.added_at
                    """,
                    (
                        preserved_rack["rack_id"],
                        cloned["id"],
                        preserved_rack["qty"],
                        preserved_rack["added_by"],
                        preserved_rack["added_at"],
                        preserved_rack["reason"],
                    ),
                )
        return summary

    def seed_demo_data(self, con: sqlite3.Connection) -> None:
        """Seed the optional sample file only into a completely empty scanner database.

        Effects: May create starter delivery lists and stations on a first-run demo database.
        Flow: Returns immediately when the sample file is absent or any delivery list already
        exists. This prevents an old ``data/sample-delivery-list.json`` file from rewriting or
        colliding with production rows during every startup. Fresh empty databases retain the
        original optional demo-seeding behavior.
        """
        if not self.sample_path.exists():
            return
        if con.execute("SELECT 1 FROM delivery_lists LIMIT 1").fetchone():
            self.seed_stations(con)
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
        """Purpose: Create stations for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        created = now_iso()
        for station in DEFAULT_STATIONS:
            con.execute("INSERT OR IGNORE INTO stations (name, created_at) VALUES (?, ?)", (station, created))

    def seed_customer_route_rules(self, con: sqlite3.Connection) -> None:
        """Purpose: Create customer route rules for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        created = now_iso()
        for customer, route, address in DEFAULT_CUSTOMER_ROUTE_RULES:
            con.execute(
                """
                INSERT OR IGNORE INTO customer_route_rules (customer_pattern, route, customer_address, active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (customer, route, address, created),
            )

    def seed_security_data(self, con: sqlite3.Connection) -> None:
        """Purpose: Create security data for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        for permission in PERMISSIONS:
            con.execute(
                "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
                (permission, permission.replace("_", " ").title()),
            )

        # Upgrade legacy role-permission rows in place. This keeps production
        # users and custom roles intact while removing retired choices from the
        # Role editor.
        for legacy, canonical in LEGACY_PERMISSION_ALIASES.items():
            con.execute(
                """
                INSERT OR IGNORE INTO role_permissions (role_id, permission_name)
                SELECT role_id, ? FROM role_permissions WHERE permission_name = ?
                """,
                (canonical, legacy),
            )
        if LEGACY_PERMISSION_ALIASES:
            placeholders = ",".join("?" for _ in LEGACY_PERMISSION_ALIASES)
            con.execute(
                f"DELETE FROM role_permissions WHERE permission_name IN ({placeholders})",
                list(LEGACY_PERMISSION_ALIASES),
            )
            con.execute(
                f"DELETE FROM permissions WHERE name IN ({placeholders})",
                list(LEGACY_PERMISSION_ALIASES),
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
                INSERT INTO users (username, email, display_name, password_hash, active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    self.config.default_admin_username,
                    "",
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
        """Purpose: Create user if missing for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
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
        """Purpose: Create bays for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
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

    def seed_racks(self, con: sqlite3.Connection) -> None:
        """Purpose: Create racks for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        created = now_iso()
        rack_defs: list[tuple[str, str, str, int]] = []
        for index in range(1, 11):
            rack_defs.append((f"R{index}S", f"Rack {index} Steel", "Steel", index))
        for index in range(1, 11):
            rack_defs.append((f"R{index}W", f"Rack {index} Wood", "Wood", 10 + index))
        rack_defs.append(("T", "Truck / No Rack", "Truck", 99))
        for code, name, rack_type, sort_order in rack_defs:
            con.execute(
                """
                INSERT OR IGNORE INTO racks (rack_code, display_name, rack_type, status, active, sort_order, created_at)
                VALUES (?, ?, ?, 'Open', 1, ?, ?)
                """,
                (code, name, rack_type, sort_order, created),
            )
        con.commit()

    def layout_bay_policy_status(self, bay: dict[str, Any]) -> str:
        """Purpose: Run the layout bay policy status workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        source_status = str(bay.get("sourceStatus") or "").strip()
        normalized = source_status.replace(" ", "").replace("-", "").lower()
        if normalized in {"deleted", "inactive"}:
            return "Deleted"
        if normalized in {"scanblocked", "blockedall", "blockscan", "blockscans"}:
            return "ScanBlocked"
        if not bay.get("autoAssignable") or normalized in {"hold", "blocked", "manual", "manualassign", "manualonly", "manualhold"}:
            return "ManualAssign"
        return "Available"

    def seed_layout_bays(self, con: sqlite3.Connection, bays: list[dict[str, Any]]) -> None:
        """Purpose: Create layout bays for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
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
            status = self.layout_bay_policy_status(bay)
            active = 0 if status == "Deleted" else 1
            capacity = 1 if status == "Available" else 0
            sort_order = int(bay.get("assignmentPriority") or index)
            con.execute(
                """
                INSERT INTO bays (
                    bay_code, display_name, area, bay_type, capacity_qty, sort_order,
                    active, status, map_section, bay_category, source_cell, layout_row,
                    layout_col, layout_cell
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bay_code) DO UPDATE SET
                    display_name = excluded.display_name,
                    area = excluded.area,
                    bay_type = excluded.bay_type,
                    capacity_qty = CASE
                        WHEN bays.status = 'Deleted' THEN bays.capacity_qty
                        ELSE excluded.capacity_qty
                    END,
                    sort_order = excluded.sort_order,
                    active = CASE
                        WHEN bays.status = 'Deleted' THEN 0
                        ELSE excluded.active
                    END,
                    status = CASE
                        WHEN bays.status = 'Deleted' THEN 'Deleted'
                        ELSE excluded.status
                    END,
                    map_section = excluded.map_section,
                    bay_category = excluded.bay_category,
                    source_cell = excluded.source_cell,
                    layout_row = COALESCE(bays.layout_row, excluded.layout_row),
                    layout_col = COALESCE(bays.layout_col, excluded.layout_col),
                    layout_cell = CASE
                        WHEN COALESCE(bays.layout_cell, '') <> '' THEN bays.layout_cell
                        ELSE excluded.layout_cell
                    END
                """,
                (
                    bay_code,
                    display_name,
                    str(bay.get("mapSection") or ""),
                    bay_type,
                    capacity,
                    sort_order,
                    active,
                    status,
                    str(bay.get("mapSection") or ""),
                    str(bay.get("bayCategory") or ""),
                    str(bay.get("sourceCell") or ""),
                    bay.get("layoutRow"),
                    bay.get("layoutCol"),
                    str(bay.get("layoutCell") or ""),
                ),
            )

    def repair_manual_assign_bay_visibility(self, con: sqlite3.Connection) -> None:
        # Repair for databases touched by older Bay Map builds:
        # active=0 used to mean "manual/hold bay", but active now means "hidden/deleted".
        # Any mapped inactive bay that is not explicitly Deleted should be visible again as Manual Assign.
        """Purpose: Reconcile manual assign bay visibility for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        repaired = con.execute(
            """
            UPDATE bays
            SET active = 1,
                status = CASE
                    WHEN COALESCE(status, '') IN ('ScanBlocked', 'BlockedAll') THEN 'ScanBlocked'
                    ELSE 'ManualAssign'
                END
            WHERE COALESCE(active, 0) = 0
              AND COALESCE(status, 'Available') <> 'Deleted'
              AND (
                COALESCE(map_section, '') <> ''
                OR COALESCE(source_cell, '') <> ''
                OR COALESCE(layout_cell, '') <> ''
                OR COALESCE(layout_row, 0) <> 0
                OR COALESCE(layout_col, 0) <> 0
              )
            """
        ).rowcount
        con.execute("UPDATE bays SET active = 1, status = 'ManualAssign' WHERE status IN ('Hold', 'Blocked')")
        con.execute("UPDATE bays SET active = 1, status = 'ScanBlocked' WHERE status = 'BlockedAll'")
        con.execute("UPDATE bays SET active = 1 WHERE status IN ('ManualAssign', 'ScanBlocked')")
        if repaired:
            self.insert_audit(
                con,
                "bay",
                "manual_assign_visibility",
                "repair_manual_assign_bay_visibility",
                "system",
                "",
                f"Restored {repaired} mapped manual-assign bay(s)",
                {"repairedCount": repaired},
            )
        con.commit()

    def list_timing_metrics(self, con: sqlite3.Connection, list_id: str, delivery_date: str) -> dict[str, Any]:
        """Purpose: Read timing metrics for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        rows = con.execute(
            """
            SELECT li.id, li.qty, li.scanned_qty,
                   MAX(CASE WHEN se.qty_delta > 0 THEN se.created_at ELSE NULL END) AS last_scanned_at
            FROM line_items li
            LEFT JOIN scan_events se ON se.line_item_id = li.id AND se.list_id = li.list_id
            WHERE li.list_id = ?
            GROUP BY li.id, li.qty, li.scanned_qty
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
        """Purpose: Read delivery lists for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT dl.*,
                       COALESCE(SUM(li.qty), 0) AS total_qty,
                       COALESCE(SUM(li.scanned_qty), 0) AS scanned_qty,
                       COUNT(li.id) AS item_count
                FROM delivery_lists dl
                LEFT JOIN line_items li ON li.list_id = dl.id
                WHERE dl.status = 'active'
                GROUP BY dl.id, dl.label, dl.delivery_date, dl.stage, dl.scanner, dl.status, dl.revision, dl.created_at
                HAVING COUNT(li.id) > 0
                ORDER BY dl.delivery_date DESC, dl.label
                """
            ).fetchall()
            glass_type_rows = con.execute(
                """
                SELECT DISTINCT list_id,
                       CASE WHEN product <> '' THEN product ELSE job END AS glass_type
                FROM line_items
                WHERE product <> '' OR job <> ''
                """
            ).fetchall()
            glass_types_by_list: dict[str, list[str]] = {}
            for glass_row in glass_type_rows:
                glass_type = str(glass_row["glass_type"] or "").strip()
                if glass_type:
                    glass_types_by_list.setdefault(str(glass_row["list_id"]), []).append(glass_type)

            update_rows = con.execute(
                """
                WITH latest_notice AS (
                    SELECT list_id, MAX(id) AS latest_id
                    FROM line_update_notices
                    GROUP BY list_id
                ), latest_token AS (
                    SELECT n.list_id, n.change_token
                    FROM line_update_notices n
                    JOIN latest_notice l ON l.latest_id = n.id
                )
                SELECT n.list_id,
                       SUM(CASE WHEN lower(n.change_type) = 'new' THEN 1 ELSE 0 END) AS new_count,
                       SUM(CASE WHEN lower(n.change_type) <> 'new' THEN 1 ELSE 0 END) AS updated_count,
                       MAX(n.created_at) AS latest_update_at
                FROM line_update_notices n
                JOIN latest_token t
                  ON t.list_id = n.list_id
                 AND t.change_token = n.change_token
                GROUP BY n.list_id
                """
            ).fetchall()
            updates_by_list = {
                str(update_row["list_id"]): {
                    "newItemCount": int(update_row["new_count"] or 0),
                    "updatedItemCount": int(update_row["updated_count"] or 0),
                    "latestUpdateAt": str(update_row["latest_update_at"] or ""),
                }
                for update_row in update_rows
            }

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
                        "glassTypes": sorted(set(glass_types_by_list.get(str(row["id"]), []))),
                        "deliveryPercent": (scanned_qty / total_qty * 100) if total_qty else 0,
                        **updates_by_list.get(str(row["id"]), {
                            "newItemCount": 0,
                            "updatedItemCount": 0,
                            "latestUpdateAt": "",
                        }),
                    }
                )
                meta.update(self.list_timing_metrics(con, row["id"], row["delivery_date"]))
                if user is None or user_can_access_stage(user, meta["stage"], meta["scanner"]):
                    result.append(meta)
        return result

    def get_delivery_list_update_preview(self, list_id: str) -> dict[str, Any]:
        """Return the newest imported new/updated rows for one delivery-list stage."""
        clean_list_id = str(list_id or "").strip()
        if not clean_list_id:
            raise ValueError("listId is required")
        with self.connect() as con:
            delivery_list = con.execute(
                "SELECT id, label, delivery_date, stage, scanner, status, revision FROM delivery_lists WHERE id = ?",
                (clean_list_id,),
            ).fetchone()
            if not delivery_list:
                raise ValueError("Delivery list was not found")
            latest = con.execute(
                """
                SELECT change_token, created_at
                FROM line_update_notices
                WHERE list_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (clean_list_id,),
            ).fetchone()
            if not latest:
                return {
                    "list": list_meta(delivery_list),
                    "changeToken": "",
                    "updatedAt": "",
                    "items": [],
                    "newCount": 0,
                    "updatedCount": 0,
                }
            rows = con.execute(
                """
                SELECT n.change_type, n.created_at AS notice_created_at,
                       li.id AS line_item_id, li.order_no, li.item_no, li.qty,
                       li.scanned_qty, li.dimensions, li.customer, li.job,
                       li.product, li.route, li.process_state, li.queue_state,
                       li.source_id, li.barcode
                FROM line_update_notices n
                JOIN line_items li ON li.id = n.line_item_id
                WHERE n.list_id = ? AND n.change_token = ?
                ORDER BY CASE WHEN lower(n.change_type) = 'new' THEN 0 ELSE 1 END,
                         CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER), li.id
                """,
                (clean_list_id, latest["change_token"]),
            ).fetchall()
        items = [
            {
                "changeType": str(row["change_type"] or "updated").lower(),
                "changedAt": str(row["notice_created_at"] or ""),
                "lineItemId": str(row["line_item_id"] or ""),
                "order": str(row["order_no"] or ""),
                "item": str(row["item_no"] or ""),
                "qty": int(row["qty"] or 0),
                "scannedQty": int(row["scanned_qty"] or 0),
                "dimensions": str(row["dimensions"] or ""),
                "customer": str(row["customer"] or ""),
                "job": str(row["job"] or ""),
                "product": str(row["product"] or ""),
                "route": str(row["route"] or ""),
                "processState": str(row["process_state"] or ""),
                "queueState": str(row["queue_state"] or ""),
                "sourceId": str(row["source_id"] or ""),
                "barcode": str(row["barcode"] or ""),
            }
            for row in rows
        ]
        return {
            "list": list_meta(delivery_list),
            "changeToken": str(latest["change_token"] or ""),
            "updatedAt": str(latest["created_at"] or ""),
            "items": items,
            "newCount": sum(1 for item in items if item["changeType"] == "new"),
            "updatedCount": sum(1 for item in items if item["changeType"] != "new"),
        }

    def get_line_items(self, list_id: str) -> list[dict[str, Any]]:
        """Purpose: Read line items for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            return self._get_line_items(con, list_id)

    def _get_line_items(self, con: sqlite3.Connection, list_id: str) -> list[dict[str, Any]]:
        """Purpose: Read line items for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        list_row = con.execute(
            "SELECT id, delivery_date, stage, scanner FROM delivery_lists WHERE id = ?",
            (list_id,),
        ).fetchone()

        rows = con.execute(
            """
            SELECT li.*,
                   (
                    SELECT se.created_at
                    FROM scan_events se
                    WHERE se.line_item_id = li.id AND se.qty_delta > 0
                    ORDER BY se.created_at DESC, se.id DESC
                    LIMIT 1
                   ) AS last_scanned_at,
                   (
                    SELECT se.station
                    FROM scan_events se
                    WHERE se.line_item_id = li.id AND se.qty_delta > 0
                    ORDER BY se.created_at DESC, se.id DESC
                    LIMIT 1
                   ) AS last_scanned_station
            FROM line_items li
            WHERE li.list_id = ?
            ORDER BY CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER), li.id
            """,
            (list_id,),
        ).fetchall()

        items = [item_from_row(row) for row in rows]

        for item in items:
            item["errorType"] = ""
            item["errorReason"] = ""
            item["received"] = False
            item["receivedQty"] = 0
            item["receivedStage"] = ""

        if rows:
            rack_rows = con.execute(
                """
                SELECT target.id AS target_id, r.rack_code, r.display_name AS rack_name, r.rack_type
                FROM rack_items ri
                JOIN racks r ON r.id = ri.rack_id
                JOIN line_items src ON src.id = ri.line_item_id
                JOIN delivery_lists src_dl ON src_dl.id = src.list_id
                JOIN line_items target
                  ON (
                    target.id = src.id
                    OR (src.source_id <> '' AND target.source_id = src.source_id)
                    OR (target.order_no = src.order_no AND target.item_no = src.item_no)
                  )
                JOIN delivery_lists target_dl
                  ON target_dl.id = target.list_id
                 AND target_dl.delivery_date = src_dl.delivery_date
                WHERE target.list_id = ?
                  AND ri.status = 'Active'
                  AND r.active = 1
                """,
                (list_id,),
            ).fetchall()
            rack_by_item = {row["target_id"]: row for row in rack_rows}
            bay_rows = con.execute(
                """
                SELECT ba.line_item_id, b.bay_code
                FROM bay_assignments ba
                JOIN bays b ON b.id = ba.bay_id
                WHERE ba.delivery_list_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
                """,
                (list_id,),
            ).fetchall()
            bay_by_item = {row["line_item_id"]: row["bay_code"] for row in bay_rows}
            for item in items:
                rack = rack_by_item.get(item["id"])
                if rack:
                    item["rackCode"] = rack["rack_code"]
                    item["rackName"] = rack["rack_name"] or rack["rack_code"]
                    item["rackType"] = rack["rack_type"]
                if item["id"] in bay_by_item:
                    item["bayCode"] = bay_by_item[item["id"]]

            receipt_rows = con.execute(
                """
                SELECT target.id AS target_id, recv.scanned_qty, recv_dl.stage, recv_dl.scanner
                FROM line_items target
                JOIN delivery_lists target_dl ON target_dl.id = target.list_id
                JOIN delivery_lists recv_dl
                  ON recv_dl.delivery_date = target_dl.delivery_date
                 AND recv_dl.status = 'active'
                JOIN line_items recv
                  ON recv.list_id = recv_dl.id
                 AND (
                    (target.source_id <> '' AND recv.source_id = target.source_id)
                    OR (recv.order_no = target.order_no AND recv.item_no = target.item_no)
                 )
                WHERE target.list_id = ?
                  AND recv.scanned_qty > 0
                """,
                (list_id,),
            ).fetchall()
            received_by_item: dict[str, dict[str, Any]] = {}
            for receipt in receipt_rows:
                destination = receiving_stage_destination(receipt["stage"], receipt["scanner"])
                if not destination:
                    continue
                current = received_by_item.setdefault(
                    receipt["target_id"],
                    {"qty": 0, "stage": destination},
                )
                scanned_qty = int(receipt["scanned_qty"] or 0)
                if scanned_qty >= int(current["qty"] or 0):
                    current["qty"] = scanned_qty
                    current["stage"] = destination

            for item in items:
                receipt = received_by_item.get(item["id"])
                if not receipt:
                    continue
                item["received"] = True
                item["receivedQty"] = int(receipt["qty"] or 0)
                item["receivedStage"] = str(receipt["stage"] or "")

        latest_error_rows = con.execute(
            """
            SELECT se.line_item_id, se.event_type, se.message, se.reason
            FROM scan_events se
            JOIN (
                SELECT line_item_id, MAX(id) AS max_id
                FROM scan_events
                WHERE list_id = ? AND line_item_id IS NOT NULL
                GROUP BY line_item_id
            ) latest ON latest.max_id = se.id
            WHERE se.event_type = 'error'
              AND se.message <> 'Rack destination mismatch'
              AND se.message NOT LIKE 'Rack %'
              AND COALESCE(se.reason, '') NOT LIKE 'Rack % already assigned%'
              AND COALESCE(se.reason, '') NOT LIKE '%must go on a separate rack%'
            """,
            (list_id,),
        ).fetchall()

        latest_error_by_item = {row["line_item_id"]: row for row in latest_error_rows}

        for item in items:
            error_row = latest_error_by_item.get(item["id"])
            if not error_row:
                continue

            if int(item.get("scanned") or 0) >= int(item.get("qty") or 0):
                continue

            item["errorType"] = "scan_error"
            item["errorReason"] = error_row["reason"] or error_row["message"] or "Scan failed before this row was completed."

        if list_row:
            stage_text = f"{list_row['stage']} {list_row['scanner']}".lower()
            should_check_prior_stage = "staging" in stage_text or "outbound" in stage_text

            if should_check_prior_stage:
                inbound_list = con.execute(
                    """
                    SELECT id
                    FROM delivery_lists
                    WHERE delivery_date = ?
                      AND status = 'active'
                      AND id <> ?
                      AND (
                        LOWER(stage) LIKE '%indian trail%'
                        OR LOWER(scanner) LIKE '%indian trail%'
                        OR LOWER(stage) LIKE '%inbound%'
                      )
                    ORDER BY id
                    LIMIT 1
                    """,
                    (list_row["delivery_date"], list_id),
                ).fetchone()

                if inbound_list:
                    inbound_rows = con.execute(
                        """
                        SELECT order_no, item_no, scanned_qty
                        FROM line_items
                        WHERE list_id = ? AND scanned_qty > 0
                        """,
                        (inbound_list["id"],),
                    ).fetchall()

                    inbound_scanned = {
                        (str(row["order_no"]), str(row["item_no"])): int(row["scanned_qty"] or 0)
                        for row in inbound_rows
                    }

                    for item in items:
                        received_qty = inbound_scanned.get((str(item["order"]), str(item["item"])), 0)
                        current_qty = int(item.get("scanned") or 0)

                        if received_qty <= current_qty:
                            continue

                        item["errorType"] = "stage_sequence"
                        item["errorReason"] = f"IT received {received_qty}; Outbound {current_qty}"


        return items

    def get_scan_events(self, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
        """Purpose: Read scan events for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            return self._get_scan_events(con, list_id, only_errors=only_errors)

    def _get_scan_events(self, con: sqlite3.Connection, list_id: str, only_errors: bool = False) -> list[dict[str, Any]]:
        """Purpose: Read scan events for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        condition = "AND se.event_type = 'error'" if only_errors else ""
        rows = con.execute(
            f"""
            SELECT se.*, li.order_no, li.item_no, li.qty, li.scanned_qty, li.dimensions,
                   li.customer, li.route, li.job, li.product, li.suggested_bay,
                   dl.stage AS list_stage,
                   (
                       SELECT r.rack_code
                       FROM rack_items ri
                       JOIN racks r ON r.id = ri.rack_id
                       WHERE ri.line_item_id = li.id AND ri.status = 'Active' AND r.active = 1
                       ORDER BY ri.added_at DESC, ri.id DESC
                       LIMIT 1
                   ) AS rack_code,
                   (
                       SELECT r.display_name
                       FROM rack_items ri
                       JOIN racks r ON r.id = ri.rack_id
                       WHERE ri.line_item_id = li.id AND ri.status = 'Active' AND r.active = 1
                       ORDER BY ri.added_at DESC, ri.id DESC
                       LIMIT 1
                   ) AS rack_name,
                   (
                       SELECT r.status
                       FROM rack_items ri
                       JOIN racks r ON r.id = ri.rack_id
                       WHERE ri.line_item_id = li.id AND ri.status = 'Active' AND r.active = 1
                       ORDER BY ri.added_at DESC, ri.id DESC
                       LIMIT 1
                   ) AS rack_status,
                   EXISTS(
                       SELECT 1
                       FROM delivery_lists outbound_list
                       JOIN line_items outbound_item ON outbound_item.list_id = outbound_list.id
                       WHERE outbound_list.delivery_date = dl.delivery_date
                         AND LOWER(outbound_list.stage) LIKE '%outbound%'
                         AND outbound_item.scanned_qty > 0
                         AND (
                           (li.source_id <> '' AND outbound_item.source_id = li.source_id)
                           OR (outbound_item.order_no = li.order_no AND outbound_item.item_no = li.item_no)
                         )
                   ) AS outbound_scanned
            FROM scan_events se
            LEFT JOIN line_items li ON li.id = se.line_item_id
            LEFT JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE se.list_id = ? {condition}
            ORDER BY se.id DESC
            LIMIT 30
            """,
            (list_id,),
        ).fetchall()
        return [event_from_row(row) for row in rows]

    def get_delivery_list(self, list_id: str, last_scan: dict[str, Any] | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Read delivery list for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            return self._get_payload(con, list_id, last_scan=last_scan, user=user)

    def _get_payload(self, con: sqlite3.Connection, list_id: str, last_scan: dict[str, Any] | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Read payload for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
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
        """Purpose: Run the user can access list workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            row = con.execute("SELECT stage, scanner FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            if not row:
                return False
            return user_can_access_stage(user, row["stage"], row["scanner"])

    def get_stations(self) -> list[str]:
        """Purpose: Read stations for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            rows = con.execute("SELECT name FROM stations ORDER BY name").fetchall()
            return [str(row["name"]) for row in rows]

    def add_station(self, name: str) -> dict[str, Any]:
        """Purpose: Create station for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_name = " ".join(str(name or "").split())[:80]
        if not clean_name:
            raise ValueError("Station name is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT OR IGNORE INTO stations (name, created_at) VALUES (?, ?)", (clean_name, now_iso()))
            con.commit()
        return {"stations": self.get_stations(), "station": clean_name}

    def rename_station(self, old_name: str, new_name: str) -> dict[str, Any]:
        """Purpose: Update station for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
            self.insert_audit(con, "station", clean_new, "rename_station", "admin", clean_new, clean_old, {"oldName": clean_old})
            con.commit()
        return {"stations": self.get_stations(), "station": clean_new, "oldStation": clean_old}

    def remove_station(self, name: str) -> dict[str, Any]:
        """Purpose: Remove station for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Read permissions for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        return list(PERMISSIONS)

    def list_roles(self) -> list[dict[str, Any]]:
        """Purpose: Read roles for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            rows = con.execute("SELECT * FROM roles ORDER BY name").fetchall()
            roles: list[dict[str, Any]] = []
            for row in rows:
                permission_rows = con.execute(
                    "SELECT permission_name FROM role_permissions WHERE role_id = ? ORDER BY permission_name",
                    (row["id"],),
                ).fetchall()
                roles.append(
                    {
                        "name": row["name"],
                        "description": row["description"] or "",
                        "permissions": canonical_permissions(permission["permission_name"] for permission in permission_rows),
                    }
                )
            return roles

    def update_role_permissions(self, role_name: str, permissions: list[str], updated_by: str = "system") -> dict[str, Any]:
        """Purpose: Update role permissions for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_role = str(role_name or "").strip()
        requested_permissions = [str(permission).strip() for permission in permissions if str(permission).strip()]
        clean_permissions = canonical_permissions(requested_permissions)
        unknown = [permission for permission in requested_permissions if canonical_permission_name(permission) not in PERMISSIONS]
        if not clean_role:
            raise ValueError("role is required")
        if unknown:
            raise ValueError(f"Unknown permission: {unknown[0]}")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            role = con.execute("SELECT id FROM roles WHERE name = ?", (clean_role,)).fetchone()
            if not role:
                raise ValueError("Role not found")
            con.execute("DELETE FROM role_permissions WHERE role_id = ?", (role["id"],))
            for permission in clean_permissions:
                con.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_name) VALUES (?, ?)", (role["id"], permission))
            con.execute(
                """
                DELETE FROM sessions
                WHERE user_id IN (
                    SELECT user_id FROM user_roles WHERE role_id = ?
                )
                """,
                (role["id"],),
            )
            self.insert_audit(con, "role", clean_role, "update_role_permissions", updated_by, "", "", {"permissions": clean_permissions})
            con.commit()
        return {"roles": self.list_roles(), "permissions": self.get_permissions()}

    def user_from_row(self, con: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        """Purpose: Run the user from row workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        station_text = row["station"] if "station" in row.keys() else ""
        assigned_stations = [station.strip() for station in re.split(r"[,|]", station_text or "") if station.strip()]
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"] if "email" in row.keys() else "",
            "displayName": row["display_name"] or row["username"],
            "station": station_text,
            "assignedStations": assigned_stations,
            "active": bool(row["active"]),
            "roles": roles,
            "permissions": expanded_permissions(permission["permission_name"] for permission in permission_rows),
            "stageAccess": stage_access_for_roles(roles),
        }

    def get_user_by_username(self, con: sqlite3.Connection, username: str) -> sqlite3.Row | None:
        """Purpose: Read user by username for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        clean = username.strip()
        return con.execute(
            """
            SELECT * FROM users
            WHERE lower(username) = lower(?)
               OR (COALESCE(email, '') <> '' AND lower(email) = lower(?))
            """,
            (clean, clean),
        ).fetchone()

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        """Purpose: Run the authenticate user workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Purpose: Read user by session for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
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
        """Purpose: Remove session for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        if not token:
            return
        token_digest = session_token_hash(token, self.config.session_secret)
        with self.connect() as con:
            con.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest,))
            con.commit()

    def request_password_reset(self, identity: str, requested_by: str = "self-service") -> dict[str, Any]:
        """Purpose: Run the request password reset workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_identity = " ".join(str(identity or "").split())
        if not clean_identity:
            raise ValueError("BFS email or username is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_user_by_username(con, clean_identity)
            # Do not reveal whether an account exists unless this is local development.
            if not row or not row["active"]:
                con.commit()
                return {"ok": True, "message": "If that account exists, a reset code was created."}
            code = f"{secrets.randbelow(1000000):06d}"
            code_hash = session_token_hash(code, self.config.session_secret)
            created = now_iso()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_MINUTES)).isoformat(timespec="seconds")
            con.execute("UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at = ''", (created, row["id"]))
            con.execute(
                """
                INSERT INTO password_reset_tokens (user_id, code_hash, created_at, expires_at, requested_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["id"], code_hash, created, expires_at, requested_by),
            )
            self.insert_audit(con, "user", row["username"], "request_password_reset", requested_by, "", "", {"identity": clean_identity})
            con.commit()
        payload = {"ok": True, "message": "Reset code created. Use it within 30 minutes.", "expiresAt": expires_at}
        if not self.config.production:
            payload["resetCode"] = code
        return payload

    def confirm_password_reset(self, identity: str, reset_code: str, new_password: str) -> dict[str, Any]:
        """Purpose: Run the confirm password reset workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_identity = " ".join(str(identity or "").split())
        clean_code = re.sub(r"\D", "", str(reset_code or ""))
        if not clean_identity or not clean_code or not new_password:
            raise ValueError("Identity, reset code, and new password are required")
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_user_by_username(con, clean_identity)
            if not row or not row["active"]:
                raise ValueError("Invalid or expired reset code")
            code_hash = session_token_hash(clean_code, self.config.session_secret)
            token_row = con.execute(
                """
                SELECT * FROM password_reset_tokens
                WHERE user_id = ? AND code_hash = ? AND used_at = ''
                ORDER BY id DESC
                LIMIT 1
                """,
                (row["id"], code_hash),
            ).fetchone()
            if not token_row or parse_iso(token_row["expires_at"]) <= datetime.now(timezone.utc):
                raise ValueError("Invalid or expired reset code")
            now = now_iso()
            con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), row["id"]))
            con.execute("UPDATE password_reset_tokens SET used_at = ? WHERE id = ?", (now, token_row["id"]))
            con.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
            self.insert_audit(con, "user", row["username"], "confirm_password_reset", "self-service", "", "", {"identity": clean_identity})
            con.commit()
        return {"ok": True, "message": "Password reset. Sign in with the new password."}

    def list_users(self) -> list[dict[str, Any]]:
        """Purpose: Read users for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            rows = con.execute("SELECT * FROM users ORDER BY username").fetchall()
            return [self.user_from_row(con, row) for row in rows]

    def deactivate_user(self, username: str, deactivated_by: str = "system") -> dict[str, Any]:
        """Purpose: Run the deactivate user workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Purpose: Run the reactivate user workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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

    def delete_user(self, username: str, deleted_by: str = "system") -> dict[str, Any]:
        """Purpose: Remove user for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_username = str(username or "").strip()
        if not clean_username:
            raise ValueError("username is required")
        if clean_username.lower() == str(deleted_by or "").strip().lower():
            raise ValueError("You cannot delete the user you are currently signed in as")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_user_by_username(con, clean_username)
            if not row:
                raise ValueError("User not found")
            con.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
            con.execute("DELETE FROM user_roles WHERE user_id = ?", (row["id"],))
            con.execute("DELETE FROM users WHERE id = ?", (row["id"],))
            self.insert_audit(con, "user", clean_username, "delete_user", deleted_by, "", "")
            con.commit()
        return {"users": self.list_users(), "username": clean_username}

    def update_user_password(self, username: str, password: str, updated_by: str = "system") -> dict[str, Any]:
        """Purpose: Update user password for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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

    def update_user_roles(self, username: str, roles: list[str], station: str | None = None, email: str | None = None, updated_by: str = "system") -> dict[str, Any]:
        """Purpose: Update user roles for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_username = str(username or "").strip()
        clean_roles = [str(role).strip() for role in roles if str(role).strip()]
        station_supplied = station is not None
        email_supplied = email is not None
        clean_station = " ".join(str(station or "").split())[:240]
        clean_email = " ".join(str(email or "").split()).lower()[:160]

        if not clean_username or not clean_roles:
            raise ValueError("username and at least one role are required")
        if clean_email and not is_valid_email(clean_email):
            raise ValueError("Enter a valid BFS email address")

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

            existing_roles = [
                row["name"]
                for row in con.execute(
                    """
                    SELECT r.name
                    FROM roles r
                    JOIN user_roles ur ON ur.role_id = r.id
                    WHERE ur.user_id = ?
                    ORDER BY r.name
                    """,
                    (user_row["id"],),
                ).fetchall()
            ]

            roles_changed = sorted(existing_roles) != sorted(clean_roles)

            if roles_changed:
                con.execute("DELETE FROM user_roles WHERE user_id = ?", (user_row["id"],))
                for role_id in role_ids:
                    con.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_row["id"], role_id))
                con.execute("DELETE FROM sessions WHERE user_id = ?", (user_row["id"],))

            if station_supplied:
                con.execute("UPDATE users SET station = ? WHERE id = ?", (clean_station, user_row["id"]))

            if email_supplied:
                if clean_email:
                    duplicate_email = con.execute(
                        """
                        SELECT id
                        FROM users
                        WHERE lower(email) = lower(?) AND id <> ?
                        LIMIT 1
                        """,
                        (clean_email, user_row["id"]),
                    ).fetchone()
                    if duplicate_email:
                        raise ValueError("That BFS email is already assigned to another user")
                con.execute("UPDATE users SET email = ? WHERE id = ?", (clean_email, user_row["id"]))

            self.insert_audit(
                con,
                "user",
                clean_username,
                "update_user_profile",
                updated_by,
                clean_station,
                "",
                {"roles": clean_roles, "station": clean_station, "email": clean_email if email_supplied else None},
            )
            con.commit()

        return {"users": self.list_users(), "username": clean_username, "roles": clean_roles, "station": clean_station, "email": clean_email if email_supplied else None}

    def list_active_sessions(self) -> list[dict[str, Any]]:
        """Purpose: Read active sessions for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
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
        """Purpose: Create user for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        email = " ".join(str(data.get("email") or data.get("bfsEmail") or "").split()).lower()[:160]
        username = " ".join(str(data.get("username") or email).split())[:160]
        display_name = " ".join(str(data.get("displayName") or username).split())[:120]
        station = " ".join(str(data.get("station") or "").split())[:240]
        password = str(data.get("password") or "")
        raw_roles = data.get("roles") or ["Operator"]
        roles = [str(raw_roles)] if isinstance(raw_roles, str) else [str(role) for role in raw_roles]
        roles = [role.strip() for role in roles if role.strip()]
        if email and not is_valid_email(email):
            raise ValueError("Enter a valid BFS email address")
        if not username or not password:
            raise ValueError("BFS email/username and password are required")
        if len(password) < 8:
            raise ValueError("Temporary password must be at least 8 characters")
        if not roles:
            raise ValueError("Choose at least one role for the new user")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = self.get_user_by_username(con, username)
            email_existing = self.get_user_by_username(con, email) if email else None
            if existing or email_existing:
                raise ValueError("User already exists")
            cur = con.execute(
                """
                INSERT INTO users (username, email, display_name, station, password_hash, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (username, email, display_name, station, hash_password(password), now_iso()),
            )
            for role_name in roles:
                role = con.execute("SELECT id FROM roles WHERE name = ?", (str(role_name),)).fetchone()
                if not role:
                    raise ValueError(f"Unknown role: {role_name}")
                con.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", (cur.lastrowid, role["id"]))
            self.insert_audit(con, "user", username, "create_user", created_by, station, "", {"roles": roles, "station": station, "email": email})
            con.commit()
            user_row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self.user_from_row(con, user_row)

    def get_customer_route_rules(self) -> list[dict[str, Any]]:
        """Purpose: Read customer route rules for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            return self.customer_route_rules_from_connection(con)

    def add_customer_route_rule(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Create customer route rule for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        customer = " ".join(str(data.get("customerPattern") or data.get("customer") or "").split())[:160]
        customer_address = " ".join(str(data.get("customerAddress") or data.get("address") or "").split())[:240]
        raw_route = str(data.get("route") or "").strip().upper()
        rule_id = int(data.get("ruleId") or data.get("id") or 0)
        matched_route, canonical_route = canonical_route_designation(raw_route)
        route = (canonical_route or "IT") if matched_route else re.sub(r"[^A-Z0-9_-]+", "-", raw_route).strip("-")[:24]
        if not route:
            raise ValueError("Route is required")
        if not customer:
            raise ValueError("Customer pattern is required")
        if route == "CPU" and not customer_address:
            customer_address = CPU_DESTINATION_ADDRESS
        if route == "GNV" and not customer_address:
            customer_address = GREENVILLE_DESTINATION_ADDRESS
        if route == "DTC" and not customer_address:
            raise ValueError("DTC customer route rules require a delivery address")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if rule_id:
                existing = con.execute("SELECT id FROM customer_route_rules WHERE id = ?", (rule_id,)).fetchone()
                if not existing:
                    raise ValueError("Customer route rule not found")
                duplicate = con.execute(
                    "SELECT id FROM customer_route_rules WHERE customer_pattern = ? AND id <> ? AND active = 1",
                    (customer, rule_id),
                ).fetchone()
                if duplicate:
                    raise ValueError("Another active route rule already uses that customer pattern")
                con.execute(
                    """
                    UPDATE customer_route_rules
                    SET customer_pattern = ?,
                        route = ?,
                        customer_address = ?,
                        active = 1,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (customer, route, customer_address, now_iso(), rule_id),
                )
                audit_id = str(rule_id)
                audit_action = "update_customer_route_rule"
            else:
                con.execute(
                    """
                    INSERT INTO customer_route_rules (customer_pattern, route, customer_address, active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?)
                    ON CONFLICT(customer_pattern) DO UPDATE SET
                        route = excluded.route,
                        customer_address = excluded.customer_address,
                        active = 1,
                        updated_at = excluded.updated_at
                    """,
                    (customer, route, customer_address, now_iso(), now_iso()),
                )
                audit_id = customer
                audit_action = "upsert_customer_route_rule"
            self.insert_audit(con, "customer_route_rule", audit_id, audit_action, user, "", "", {"customer": customer, "route": route, "address": customer_address})
            repaired_items = self.repair_route_stage_memberships_if_needed(con, force=True)
            con.commit()
        return {"rules": self.get_customer_route_rules(), "repairedItems": repaired_items}

    def remove_customer_route_rule(self, rule_id: int, user: str) -> dict[str, Any]:
        """Purpose: Remove customer route rule for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        if not rule_id:
            raise ValueError("ruleId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM customer_route_rules WHERE id = ?", (rule_id,)).fetchone()
            if not row:
                raise ValueError("Customer route rule not found")
            con.execute("UPDATE customer_route_rules SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), rule_id))
            self.insert_audit(con, "customer_route_rule", str(rule_id), "remove_customer_route_rule", user, "", "", {"customer": row["customer_pattern"]})
            repaired_items = self.repair_route_stage_memberships_if_needed(con, force=True)
            con.commit()
        return {"rules": self.get_customer_route_rules(), "repairedItems": repaired_items}


    def send_customer_manifests_for_import(self, con: sqlite3.Connection, payload: dict[str, Any], user: str) -> None:
        """Purpose: Send customer manifests for import for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        delivery_date = str(payload.get("deliveryDate") or "")
        items = [item for item in payload.get("items") or [] if isinstance(item, dict)]
        customer_map: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            customer = str(item.get("customer") or "").strip()
            if not customer:
                continue
            customer_map.setdefault(customer, []).append(item)
        cc_emails = self.customer_cc_emails(con)
        for customer, customer_items in customer_map.items():
            contacts = self.customer_email_matches(con, customer)
            if not contacts:
                continue
            to_emails = [row["email"] for row in contacts]
            rows = "\n".join(
                f"- Job {item.get('job') or item.get('product') or '-'} | Order {item.get('order')}-{item.get('item')} | Qty {item.get('qty')} | {item.get('dimensions') or '-'}{f' | Route {public_route_label(item.get("route"))}' if public_route_label(item.get('route')) else ''}"
                for item in customer_items
            )
            subject = f"Delivery manifest for {customer} - {format_display_date(delivery_date)}"
            body = (
                f"Hello,\n\nHere is the current manifest for {customer}.\n"
                f"Expected ready date: {format_display_date(delivery_date)}\n\n"
                f"Pieces:\n{rows}\n\n"
                "This is an automated manifest from Barefoot Facility Services."
            )
            self.queue_email_message(con, "manifest", customer, contacts[0]["customer_pattern"], delivery_date, to_emails, cc_emails, subject, body, {"itemCount": len(customer_items), "user": user})


    def get_manual_edit_lookups(self) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Read manual edit lookups for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        buckets: dict[str, dict[str, dict[str, Any]]] = {
            "product": {},
            "route": {},
            "process": {},
        }

        def add_lookup(kind: str, value: Any, label: Any = "", category: Any = "", match_terms: Any = "", source: str = "discovered", lookup_id: int | None = None) -> None:
            """Purpose: Create lookup for the delivery-list scanner workflow.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
            """
            clean_kind = str(kind or "").strip().lower()
            clean_value = str(value or "").strip()
            if clean_kind not in buckets or not clean_value:
                return
            key = clean_value.upper() if clean_kind == "route" else clean_value.lower()
            existing = buckets[clean_kind].get(key)
            next_item = {
                "id": lookup_id,
                "type": clean_kind,
                "value": clean_value,
                "label": str(label or clean_value).strip() or clean_value,
                "category": str(category or "").strip(),
                "matchTerms": str(match_terms or "").strip(),
                "source": source,
            }
            if not existing or existing.get("source") == "discovered":
                buckets[clean_kind][key] = next_item

        with self.connect() as con:
            for row in con.execute("SELECT DISTINCT product FROM line_items WHERE TRIM(product) <> '' ORDER BY product").fetchall():
                add_lookup("product", row["product"])
            for row in con.execute("SELECT DISTINCT route FROM line_items WHERE TRIM(route) <> '' ORDER BY route").fetchall():
                add_lookup("route", row["route"])
            for row in con.execute("SELECT DISTINCT process_state FROM line_items WHERE TRIM(process_state) <> '' ORDER BY process_state").fetchall():
                add_lookup("process", row["process_state"])
            for row in con.execute(
                """
                SELECT id, type, value, label, category, match_terms, source
                FROM admin_lookup_values
                WHERE is_active = 1
                ORDER BY type, label, value
                """
            ).fetchall():
                add_lookup(row["type"], row["value"], row["label"], row["category"], row["match_terms"], row["source"] or "manual", row["id"])

        return {
            "products": sorted(buckets["product"].values(), key=lambda item: item["label"].lower()),
            "routes": sorted(buckets["route"].values(), key=lambda item: (item["category"].lower(), item["label"].lower())),
            "processes": sorted(buckets["process"].values(), key=lambda item: item["label"].lower()),
        }

    def add_manual_edit_lookup(self, data: dict[str, Any], user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Create manual edit lookup for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        lookup_type = str(data.get("type") or "").strip().lower()
        if lookup_type not in {"product", "route", "process"}:
            raise ValueError("Lookup type must be product, route, or process")
        value = str(data.get("value") or "").strip()
        label = str(data.get("label") or value).strip()
        category = str(data.get("category") or "").strip() if lookup_type == "route" else ""
        match_terms = str(data.get("matchTerms") or data.get("match_terms") or "").strip() if lookup_type == "route" else ""
        if not value:
            raise ValueError("Lookup value is required")
        if not label:
            label = value
        value = (value.upper() if lookup_type == "route" else value)[:255]
        label = label[:255]
        category = category[:80]
        match_terms = match_terms[:500]
        created = now_iso()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO admin_lookup_values (type, value, label, category, match_terms, is_active, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, 'manual', ?, ?)
                ON CONFLICT(type, value) DO UPDATE SET
                    label = excluded.label,
                    category = excluded.category,
                    match_terms = excluded.match_terms,
                    is_active = 1,
                    source = 'manual',
                    updated_at = excluded.updated_at
                """,
                (lookup_type, value, label, category, match_terms, created, created),
            )
            self.insert_audit(con, "admin_lookup_value", f"{lookup_type}:{value}", "upsert_manual_edit_lookup", user, "", "", {"label": label, "category": category})
            con.commit()
        return self.get_manual_edit_lookups()

    def seed_bay_auto_assign_settings(self, con: sqlite3.Connection) -> None:
        """Purpose: Create bay auto assign settings for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        created = now_iso()
        for key, value in DEFAULT_BAY_AUTO_ASSIGN_SETTINGS.items():
            stored = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
            con.execute(
                """
                INSERT OR IGNORE INTO bay_auto_assign_settings (key, value, updated_by, updated_at)
                VALUES (?, ?, 'system', ?)
                """,
                (key, stored, created),
            )

    def bay_auto_assign_settings_from_rows(self, rows: list[sqlite3.Row]) -> dict[str, Any]:
        """Purpose: Run the bay auto assign settings from rows workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        settings = dict(DEFAULT_BAY_AUTO_ASSIGN_SETTINGS)
        for row in rows:
            key = str(row["key"] or "")
            raw_value = str(row["value"] or "")
            if key in {"standardMaxInches", "tallMinInches", "oversizeMinInches"}:
                try:
                    settings[key] = float(raw_value)
                except ValueError:
                    settings[key] = DEFAULT_BAY_AUTO_ASSIGN_SETTINGS[key]
            elif key == "manualAssignTypes":
                try:
                    parsed = json.loads(raw_value)
                except json.JSONDecodeError:
                    parsed = [value.strip() for value in raw_value.split(",") if value.strip()]
                settings[key] = parsed if isinstance(parsed, list) else []
            elif key:
                settings[key] = raw_value
        return normalized_bay_auto_assign_settings(settings)

    def get_bay_auto_assign_settings(self) -> dict[str, Any]:
        """Purpose: Read bay auto assign settings for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        with self.connect() as con:
            self.seed_bay_auto_assign_settings(con)
            rows = con.execute("SELECT * FROM bay_auto_assign_settings").fetchall()
        return self.bay_auto_assign_settings_from_rows(rows)

    def get_bay_auto_assign_settings_con(self, con: sqlite3.Connection) -> dict[str, Any]:
        """Purpose: Read bay auto assign settings con for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        self.seed_bay_auto_assign_settings(con)
        rows = con.execute("SELECT * FROM bay_auto_assign_settings").fetchall()
        return self.bay_auto_assign_settings_from_rows(rows)

    def update_bay_auto_assign_settings(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update bay auto assign settings for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        current = normalized_bay_auto_assign_settings(data)
        if current["tallMinInches"] <= 0 or current["oversizeMinInches"] <= 0:
            raise ValueError("Bay auto-assign thresholds must be greater than zero")
        if current["oversizeMinInches"] < current["tallMinInches"]:
            raise ValueError("Oversize minimum must be greater than or equal to tall minimum")
        allowed_types = [
            current["standardBayType"],
            current["tallBayType"],
            current["oversizeBayType"],
            current["mirrorBayType"],
            current["framedMirrorBayType"],
            current["cpuBayType"],
        ]
        manual_types = [value for value in current["manualAssignTypes"] if value in allowed_types]
        current["manualAssignTypes"] = manual_types
        changed = now_iso()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self.seed_bay_auto_assign_settings(con)
            for key, value in current.items():
                stored = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
                con.execute(
                    """
                    INSERT INTO bay_auto_assign_settings (key, value, updated_by, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_by = excluded.updated_by, updated_at = excluded.updated_at
                    """,
                    (key, stored, user, changed),
                )
            self.insert_audit(con, "bay_auto_assigner", "settings", "update_bay_auto_assign_settings", user, "", "", current)
            con.commit()
        return self.get_bay_auto_assign_settings()

    def bay_type_requires_manual_assignment(self, con: sqlite3.Connection, bay_type: str) -> bool:
        """Purpose: Run the bay type requires manual assignment workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        settings = self.get_bay_auto_assign_settings_con(con)
        manual_types = {str(value).strip().lower() for value in settings.get("manualAssignTypes", [])}
        return str(bay_type or "").strip().lower() in manual_types

    def suggested_bay_from_settings(self, con: sqlite3.Connection, product: str, dimensions: str, route: str) -> str:
        """Purpose: Run the suggested bay from settings workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        return suggested_bay(product, dimensions, route, self.get_bay_auto_assign_settings_con(con))

    def bay_manual_rule_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        """Purpose: Run the bay manual rule from row workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return {
            "id": row["id"],
            "matchType": row["match_type"],
            "pattern": row["pattern"],
            "label": row["label"],
            "createdAt": row["created_at"],
        }

    def bay_barcode_rule_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        """Purpose: Run the bay barcode rule from row workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return {
            "id": row["id"],
            "pattern": row["pattern"],
            "label": row["label"],
            "createdAt": row["created_at"],
        }

    def cross_date_scan_settings_con(self, con: Any) -> dict[str, Any]:
        """Read and normalize the shared cross-delivery-date scan settings."""
        mode = self.system_metadata_value(con, CROSS_DATE_SCAN_MODE_METADATA_KEY).strip().lower()
        if mode not in CROSS_DATE_SCAN_MODES:
            mode = DEFAULT_CROSS_DATE_SCAN_MODE

        def bounded_days(key: str, default: int) -> int:
            raw_value = self.system_metadata_value(con, key)
            try:
                value = int(raw_value or default)
            except (TypeError, ValueError):
                value = default
            return max(0, min(value, 365))

        return {
            "mode": mode,
            "pastDays": bounded_days(CROSS_DATE_SCAN_PAST_DAYS_METADATA_KEY, DEFAULT_CROSS_DATE_SCAN_PAST_DAYS),
            "futureDays": bounded_days(CROSS_DATE_SCAN_FUTURE_DAYS_METADATA_KEY, DEFAULT_CROSS_DATE_SCAN_FUTURE_DAYS),
        }

    def get_cross_date_scan_settings(self) -> dict[str, Any]:
        """Return the current cross-delivery-date scan behavior for Admin and scanners."""
        with self.connect() as con:
            return self.cross_date_scan_settings_con(con)

    def update_cross_date_scan_settings(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Validate and save cross-delivery-date scan behavior in system metadata."""
        mode = str(data.get("mode") or DEFAULT_CROSS_DATE_SCAN_MODE).strip().lower()
        if mode not in CROSS_DATE_SCAN_MODES:
            raise ValueError("Cross-date scan mode must be disabled, ask, or auto_unique")
        try:
            past_days = int(data.get("pastDays", DEFAULT_CROSS_DATE_SCAN_PAST_DAYS))
            future_days = int(data.get("futureDays", DEFAULT_CROSS_DATE_SCAN_FUTURE_DAYS))
        except (TypeError, ValueError) as exc:
            raise ValueError("Cross-date scan search limits must be whole numbers") from exc
        if not 0 <= past_days <= 365 or not 0 <= future_days <= 365:
            raise ValueError("Cross-date scan search limits must be between 0 and 365 days")

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self.set_system_metadata_value(con, CROSS_DATE_SCAN_MODE_METADATA_KEY, mode)
            self.set_system_metadata_value(con, CROSS_DATE_SCAN_PAST_DAYS_METADATA_KEY, str(past_days))
            self.set_system_metadata_value(con, CROSS_DATE_SCAN_FUTURE_DAYS_METADATA_KEY, str(future_days))
            self.insert_audit(
                con,
                "cross_date_scan_settings",
                "global",
                "update_cross_date_scan_settings",
                user,
                "",
                "",
                {"mode": mode, "pastDays": past_days, "futureDays": future_days},
            )
            con.commit()
        return self.get_cross_date_scan_settings()

    def get_bay_scan_settings(self) -> dict[str, Any]:
        """Purpose: Read bay scan settings for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        with self.connect() as con:
            manual_rows = con.execute(
                """
                SELECT * FROM bay_manual_input_rules
                WHERE active = 1
                ORDER BY id DESC
                """
            ).fetchall()
            barcode_rows = con.execute(
                """
                SELECT * FROM bay_scan_barcode_rules
                WHERE active = 1
                ORDER BY id DESC
                """
            ).fetchall()
            override_minutes = self.rack_destination_override_minutes_con(con)
        return {
            "manualRules": [self.bay_manual_rule_from_row(row) for row in manual_rows],
            "barcodeRules": [self.bay_barcode_rule_from_row(row) for row in barcode_rows],
            "destinationOverrideMinutes": override_minutes,
        }

    def rack_destination_override_minutes_con(self, con: sqlite3.Connection) -> int:
        """Return the configured temporary rack-destination override window."""
        raw_value = self.system_metadata_value(con, RACK_DESTINATION_OVERRIDE_METADATA_KEY)
        try:
            minutes = int(raw_value or DEFAULT_RACK_DESTINATION_OVERRIDE_MINUTES)
        except (TypeError, ValueError):
            minutes = DEFAULT_RACK_DESTINATION_OVERRIDE_MINUTES
        return max(1, min(minutes, 120))

    def update_bay_scan_settings(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Update shared Bay Scanner safety settings without changing rule records."""
        try:
            minutes = int(data.get("destinationOverrideMinutes") or DEFAULT_RACK_DESTINATION_OVERRIDE_MINUTES)
        except (TypeError, ValueError) as exc:
            raise ValueError("Destination override time must be a whole number of minutes") from exc
        if minutes < 1 or minutes > 120:
            raise ValueError("Destination override time must be between 1 and 120 minutes")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self.set_system_metadata_value(con, RACK_DESTINATION_OVERRIDE_METADATA_KEY, str(minutes))
            self.insert_audit(
                con,
                "bay_scanner_settings",
                "rack_destination_override",
                "update_rack_destination_override_minutes",
                user,
                "",
                "",
                {"destinationOverrideMinutes": minutes},
            )
            con.commit()
        return self.get_bay_scan_settings()

    def upsert_bay_manual_input_rule(self, data: dict[str, Any], user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Run the upsert bay manual input rule workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        match_type = str(data.get("matchType") or data.get("match_type") or "exact").strip().lower()
        if match_type not in {"exact", "contains", "regex"}:
            raise ValueError("Manual input rule type must be exact, contains, or regex")
        pattern = str(data.get("pattern") or "").strip()
        label = str(data.get("label") or "").strip()
        if not pattern:
            raise ValueError("Manual input pattern is required")
        if match_type == "regex":
            re.compile(pattern)
        created = now_iso()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO bay_manual_input_rules (match_type, pattern, normalized_pattern, label, active, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (match_type, pattern[:500], normalized_match_text(pattern), label[:120], user, created, created),
            )
            self.insert_audit(con, "bay_manual_input_rule", pattern[:80], "upsert_bay_manual_input_rule", user, "", "", {"matchType": match_type, "label": label})
            con.commit()
        return self.get_bay_scan_settings()

    def remove_bay_manual_input_rule(self, rule_id: int, user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Remove bay manual input rule for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE bay_manual_input_rules SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), int(rule_id or 0)))
            self.insert_audit(con, "bay_manual_input_rule", str(rule_id), "remove_bay_manual_input_rule", user, "", "", {})
            con.commit()
        return self.get_bay_scan_settings()

    def upsert_bay_scan_barcode_rule(self, data: dict[str, Any], user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Run the upsert bay scan barcode rule workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        pattern = str(data.get("pattern") or "").strip()
        label = str(data.get("label") or "").strip()
        if not pattern:
            raise ValueError("Barcode pattern is required")
        re.compile(pattern)
        created = now_iso()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO bay_scan_barcode_rules (pattern, label, active, created_by, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?, ?)
                """,
                (pattern[:500], label[:120], user, created, created),
            )
            self.insert_audit(con, "bay_scan_barcode_rule", pattern[:80], "upsert_bay_scan_barcode_rule", user, "", "", {"label": label})
            con.commit()
        return self.get_bay_scan_settings()

    def remove_bay_scan_barcode_rule(self, rule_id: int, user: str) -> dict[str, list[dict[str, Any]]]:
        """Purpose: Remove bay scan barcode rule for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE bay_scan_barcode_rules SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), int(rule_id or 0)))
            self.insert_audit(con, "bay_scan_barcode_rule", str(rule_id), "remove_bay_scan_barcode_rule", user, "", "", {})
            con.commit()
        return self.get_bay_scan_settings()

    def bay_manual_text_is_known(self, con: sqlite3.Connection, value: str) -> bool:
        """Purpose: Run the bay manual text is known workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        text = str(value or "").strip()
        clean = normalized_match_text(text)
        if not text:
            return False
        for row in con.execute("SELECT * FROM bay_manual_input_rules WHERE active = 1").fetchall():
            pattern = str(row["pattern"] or "")
            match_type = str(row["match_type"] or "exact").lower()
            if match_type == "regex":
                try:
                    if re.search(pattern, text, flags=re.IGNORECASE):
                        return True
                except re.error:
                    continue
            elif match_type == "contains":
                if normalized_match_text(pattern) in clean:
                    return True
            else:
                if normalized_match_text(pattern) == clean:
                    return True
        for row in con.execute("SELECT * FROM bay_scan_barcode_rules WHERE active = 1").fetchall():
            try:
                if re.search(str(row["pattern"] or ""), text, flags=re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False

    def find_manual_bay_line_items(self, con: sqlite3.Connection, scan_text: str, item_no: str = "") -> list[sqlite3.Row]:
        """Purpose: Resolve manual bay line items for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        text = str(scan_text or "").strip()
        clean = clean_barcode(text)
        digits = digits_only(text)
        item_digits = digits_only(item_no).zfill(3) if digits_only(item_no) else ""
        rows: list[sqlite3.Row] = []
        base_sql = """
            SELECT li.*
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.status = 'active'
              AND (dl.stage LIKE '%Indian Trail%' OR dl.stage LIKE '%Staging%' OR dl.stage LIKE '%Outbound%')
        """
        if clean:
            rows = con.execute(base_sql + " AND UPPER(REPLACE(li.barcode, '*', '')) = ? ORDER BY dl.delivery_date DESC, li.order_no, li.item_no", (clean,)).fetchall()
            if rows:
                return rows
        if digits:
            if item_digits:
                rows = con.execute(base_sql + " AND li.order_no = ? AND li.item_no = ? ORDER BY dl.delivery_date DESC, li.order_no, li.item_no", (digits, item_digits)).fetchall()
            else:
                rows = con.execute(base_sql + " AND (li.order_no = ? OR li.job LIKE ?) ORDER BY dl.delivery_date DESC, li.job, li.order_no, li.item_no", (digits, f"%{digits}%")).fetchall()
            if rows:
                job = str(rows[0]["job"] or "").strip()
                list_id = rows[0]["list_id"]
                if job and not item_digits:
                    return con.execute("SELECT * FROM line_items WHERE list_id = ? AND COALESCE(job, '') = ? ORDER BY order_no, item_no", (list_id, job)).fetchall()
                return rows
        if text:
            like = f"%{text}%"
            rows = con.execute(base_sql + " AND (li.job LIKE ? OR li.customer LIKE ? OR li.product LIKE ?) ORDER BY dl.delivery_date DESC, li.job, li.order_no, li.item_no LIMIT 200", (like, like, like)).fetchall()
            if rows:
                job = str(rows[0]["job"] or "").strip()
                list_id = rows[0]["list_id"]
                if job:
                    return con.execute("SELECT * FROM line_items WHERE list_id = ? AND COALESCE(job, '') = ? ORDER BY order_no, item_no", (list_id, job)).fetchall()
        return []

    def find_sdi_line_items(self, con: sqlite3.Connection, lookup_text: str) -> list[sqlite3.Row]:
        """Resolve an SDI entry as a barcode, SO/order number, or complete Job Nr. label.

        The Bay Map commonly displays Job Nr. values such as
        ``88418245M LOGAN FARMS 51``. Those values contain both letters and
        digits, so reducing the input to digits loses the actual job key. Reuse
        the manual bay resolver first, then apply a normalized fallback so
        pasted job labels still match when spacing or punctuation differs.
        """
        text = str(lookup_text or "").strip()
        if not text:
            return []

        rows = self.find_manual_bay_line_items(con, text)
        if rows:
            return rows

        normalized_lookup = normalized_match_text(text)
        if not normalized_lookup:
            return []

        candidates = con.execute(
            """
            SELECT li.*
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.status = 'active'
              AND (dl.stage LIKE '%Indian Trail%' OR dl.stage LIKE '%Staging%' OR dl.stage LIKE '%Outbound%')
            ORDER BY dl.delivery_date DESC, li.job, li.order_no, li.item_no
            LIMIT 2500
            """
        ).fetchall()

        matched = None
        for row in candidates:
            job_text = normalized_match_text(row["job"])
            order_text = normalized_match_text(row["order_no"])
            customer_text = normalized_match_text(row["customer"])
            combined_text = normalized_match_text(f"{row['job']} {row['customer']} {row['order_no']}")
            if normalized_lookup == job_text:
                matched = row
                break
            if normalized_lookup == order_text or normalized_lookup in combined_text:
                matched = matched or row

        if not matched:
            return []

        job_value = str(matched["job"] or "").strip()
        if job_value:
            return con.execute(
                "SELECT * FROM line_items WHERE list_id = ? AND COALESCE(job, '') = ? ORDER BY order_no, item_no",
                (matched["list_id"], job_value),
            ).fetchall()
        return [matched]

    def sdi_destination_rows(self, con: Any) -> list[Any]:
        """Read one Indian Trail destination row per physical item with its active bay assignment.

        SDI decisions must be made from the receiving-stage copy because Staging and
        Outbound quantities do not prove that the glass is physically in a bay.
        """
        return con.execute(
            """
            SELECT li.*, dl.delivery_date AS delivery_date,
                   dl.stage AS delivery_stage, dl.scanner AS delivery_scanner,
                   ba.id AS assignment_id, ba.status AS assignment_status,
                   ba.assigned_qty AS assignment_qty, ba.bay_id AS assignment_bay_id,
                   ba.reason AS assignment_reason,
                   b.bay_code AS assignment_bay_code,
                   b.display_name AS assignment_bay_display
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            LEFT JOIN bay_assignments ba ON ba.id = (
                SELECT ba2.id
                FROM bay_assignments ba2
                WHERE ba2.line_item_id = li.id
                  AND ba2.status NOT IN ('Cleared', 'Cancelled')
                ORDER BY ba2.id DESC
                LIMIT 1
            )
            LEFT JOIN bays b ON b.id = ba.bay_id
            WHERE dl.status = 'active'
              AND (
                    LOWER(COALESCE(dl.stage, '')) LIKE '%indian trail%'
                 OR LOWER(COALESCE(dl.scanner, '')) LIKE '%indian trail%'
                 OR LOWER(COALESCE(dl.stage, '')) LIKE '%inbound%'
              )
            ORDER BY dl.delivery_date DESC, li.job, li.order_no, li.item_no
            """
        ).fetchall()

    def sdi_item_presence(self, row: Any) -> dict[str, Any]:
        """Calculate whether an Indian Trail item is physically present or still missing.

        PreAssigned rows reserve a bay but are intentionally not counted as present.
        This is the same fulfillment rule used by the selected-bay job detail panel.
        """
        qty = max(int(row_value(row, "qty", 0) or 0), 0)
        assignment_status = str(row_value(row, "assignment_status", "") or "")
        physically_in_bay = bool(row_value(row, "assignment_id", 0)) and assignment_status not in {
            "PreAssigned",
            "Cleared",
            "Cancelled",
        }
        in_bay_qty = (
            min(max(int(row_value(row, "assignment_qty", 0) or 0), 0), qty)
            if physically_in_bay
            else 0
        )
        return {
            "qty": qty,
            "inBayQty": in_bay_qty,
            "missingQty": max(qty - in_bay_qty, 0),
            "physicallyInBay": physically_in_bay,
            "complete": qty > 0 and in_bay_qty >= qty,
        }

    def resolve_sdi_destination_rows(
        self,
        con: Any,
        lookup_text: str = "",
        line_item_ids: list[str] | None = None,
        destination_rows: list[Any] | None = None,
    ) -> list[Any]:
        """Resolve exact Indian Trail item rows for an SDI/Rush/Remake action.

        Explicit line-item IDs are authoritative. Text lookups keep the legacy job/order
        behavior, but are reduced back to the Indian Trail destination copies before use.
        """
        destination_rows = destination_rows if destination_rows is not None else self.sdi_destination_rows(con)
        id_set = {str(value or "").strip() for value in (line_item_ids or []) if str(value or "").strip()}
        if id_set:
            return [row for row in destination_rows if str(row["id"]) in id_set]

        text = str(lookup_text or "").strip()
        if not text:
            return []
        normalized_lookup = normalized_match_text(text)
        digits = digits_only(text)
        item_digits = ""
        parts = re.split(r"[-./\s]+", text)
        if len(parts) >= 2 and parts[-2].isdigit() and parts[-1].isdigit():
            digits = parts[-2]
            item_digits = parts[-1]

        scored: list[tuple[int, Any]] = []
        for row in destination_rows:
            job = str(row["job"] or "").strip()
            order = str(row["order_no"] or "").strip()
            item = str(row["item_no"] or "").strip()
            barcode = str(row["barcode"] or "").strip()
            combined = normalized_match_text(f"{job} {row['customer']} {order} {item}")
            score = 0
            if text and clean_barcode(text) == clean_barcode(barcode):
                score = 100
            elif normalized_lookup and normalized_lookup == normalized_match_text(job):
                score = 95
            elif digits and item_digits and digits == order and item_digits.lstrip("0") == item.lstrip("0"):
                score = 92
            elif digits and digits == order:
                score = 88
            elif normalized_lookup and normalized_lookup == normalized_match_text(order):
                score = 86
            elif normalized_lookup and normalized_match_text(job).startswith(normalized_lookup):
                score = 74
            elif normalized_lookup and normalized_lookup in combined:
                score = 60
            if score:
                scored.append((score, row))
        if not scored:
            return []
        scored.sort(key=lambda entry: (-entry[0], str(entry[1]["job"] or ""), str(entry[1]["order_no"] or ""), str(entry[1]["item_no"] or "")))
        best = scored[0][1]
        best_job = str(best["job"] or "").strip()
        best_list = str(best["list_id"] or "")
        if best_job and not item_digits:
            return [row for row in destination_rows if str(row["list_id"] or "") == best_list and str(row["job"] or "").strip() == best_job]
        if digits and not item_digits:
            return [row for row in destination_rows if str(row["list_id"] or "") == best_list and str(row["order_no"] or "") == digits]
        return [best]

    def get_sdi_workspace(self, query: str = "", bay_code: str = "") -> dict[str, Any]:
        """Build the predictive SDI modal workspace from live Indian Trail item state.

        Missing items are flagged as the safe default selection. Current intentional Rush
        marks are grouped by job and include exact item IDs for individual clearing.
        """
        clean_query = str(query or "").strip()
        clean_bay = str(bay_code or "").strip()
        with self.connect() as con:
            rows = self.sdi_destination_rows(con)
            selected_rows = (
                self.resolve_sdi_destination_rows(con, clean_query, destination_rows=rows)
                if clean_query
                else []
            )

        def item_payload(row: Any) -> dict[str, Any]:
            """Convert one destination row into the SDI modal's item-level status payload."""
            presence = self.sdi_item_presence(row)
            process_state = str(row["process_state"] or "")
            remake = is_remake_item({"processState": process_state, "queueState": row["queue_state"]})
            rush = is_rush_item({"processState": process_state, "queueState": row["queue_state"]}) and not remake
            return {
                "lineItemId": str(row["id"]),
                "sourceId": str(row["source_id"] or ""),
                "deliveryListId": str(row["list_id"] or ""),
                "deliveryDate": str(row["delivery_date"] or ""),
                "job": str(row["job"] or ""),
                "order": str(row["order_no"] or ""),
                "item": str(row["item_no"] or ""),
                "customer": str(row["customer"] or ""),
                "product": str(row["product"] or ""),
                "dimensions": str(row["dimensions"] or ""),
                "bayCode": str(row_value(row, "assignment_bay_code", "") or ""),
                "bayDisplay": str(row_value(row, "assignment_bay_display", "") or row_value(row, "assignment_bay_code", "") or ""),
                "assignmentId": int(row_value(row, "assignment_id", 0) or 0),
                "assignmentStatus": str(row_value(row, "assignment_status", "") or ""),
                "rush": rush,
                "remake": remake,
                "marked": rush or remake,
                "priorityDeliveryDate": str(row["priority_delivery_date"] or ""),
                "priorityDirectToTruck": bool(row["priority_direct_to_truck"] or 0),
                "priorityReason": str(row_value(row, "assignment_reason", "") or ""),
                **presence,
                "eligibleByDefault": presence["missingQty"] > 0,
            }

        row_payloads = [item_payload(row) for row in rows]
        normalized_query = normalized_match_text(clean_query)
        group_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in row_payloads:
            group_value = item["job"] or f"ORDER:{item['order']}"
            group_map.setdefault((item["deliveryListId"], group_value), []).append(item)

        suggestions: list[dict[str, Any]] = []
        if normalized_query:
            for (_, group_value), items in group_map.items():
                first = items[0]
                haystack = normalized_match_text(
                    f"{first['job']} {first['order']} {first['customer']} "
                    + " ".join(f"{item['order']} {item['item']}" for item in items)
                )
                lookup = first["job"] or first["order"]
                normalized_lookup = normalized_match_text(lookup)
                if normalized_query not in haystack and normalized_query != normalized_lookup:
                    continue
                if clean_bay and not any(item["bayCode"] == clean_bay for item in items):
                    continue
                score = 100 if normalized_query == normalized_lookup else 80 if normalized_lookup.startswith(normalized_query) else 50
                suggestions.append({
                    "lookup": lookup,
                    "job": first["job"],
                    "order": first["order"],
                    "customer": first["customer"],
                    "deliveryDate": first["deliveryDate"],
                    "bayCodes": sorted({item["bayCode"] for item in items if item["bayCode"]}),
                    "itemCount": len(items),
                    "missingCount": sum(1 for item in items if item["missingQty"] > 0),
                    "score": score,
                })
            suggestions.sort(
                key=lambda item: (
                    -int(item["score"]),
                    -int(re.sub(r"\D", "", str(item["deliveryDate"] or "")) or 0),
                    str(item["lookup"]),
                )
            )

        selected_ids = {str(row["id"]) for row in selected_rows}
        selected_items = [item for item in row_payloads if item["lineItemId"] in selected_ids]
        if clean_bay and selected_items:
            bay_group_present = any(item["bayCode"] == clean_bay for item in selected_items)
            if bay_group_present:
                selected_items = [item for item in selected_items if not item["bayCode"] or item["bayCode"] == clean_bay]

        current_groups: list[dict[str, Any]] = []
        for (_, group_value), items in group_map.items():
            # Current Priority Work is intentionally Rush-only. Imported RM /
            # Remake markers remain available to the normal remake filters and
            # print workflow, but they must not flood the operator-managed Rush
            # workspace merely because they were present in an imported list.
            marked_items = [item for item in items if item["rush"] and not item["remake"]]
            if not marked_items:
                continue
            first = marked_items[0]
            current_groups.append({
                "key": f"{first['deliveryListId']}::{group_value}",
                "job": first["job"] or first["order"],
                "customer": first["customer"],
                "deliveryDate": first["priorityDeliveryDate"] or first["deliveryDate"],
                "items": marked_items,
            })
        # Priority work should surface the earliest required date first. Blank dates
        # remain visible, but sort after dated Rush/Remake jobs instead of ahead of them.
        current_groups.sort(
            key=lambda group: (
                not bool(group["deliveryDate"]),
                group["deliveryDate"] or "9999-12-31",
                group["job"],
            )
        )

        return {
            "query": clean_query,
            "bayCode": clean_bay,
            "suggestions": suggestions[:12],
            "items": selected_items,
            "currentGroups": current_groups,
        }

    def expand_priority_line_items(self, con: Any, seed_rows: list[Any]) -> list[Any]:
        """Return every active stage clone for the selected physical glass items.

        Imported Staging, Outbound, and destination rows retain the same source_id.
        Expanding by delivery date plus source_id lets Rush/Remake state follow the
        glass through only the stages generated for its actual route.
        """
        expanded: dict[str, Any] = {}
        for seed in seed_rows:
            list_context = con.execute(
                "SELECT delivery_date FROM delivery_lists WHERE id = ? AND status = 'active'",
                (str(seed["list_id"] or ""),),
            ).fetchone()
            if not list_context:
                continue
            delivery_date = str(list_context["delivery_date"] or "")
            source_id = str(seed["source_id"] or "").strip()
            if source_id:
                rows = con.execute(
                    """
                    SELECT li.*, dl.stage AS delivery_stage, dl.scanner AS delivery_scanner,
                           dl.delivery_date AS delivery_date
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active'
                      AND dl.delivery_date = ?
                      AND li.source_id = ?
                    ORDER BY dl.delivery_date, dl.id, li.order_no, li.item_no
                    """,
                    (delivery_date, source_id),
                ).fetchall()
            else:
                rows = con.execute(
                    """
                    SELECT li.*, dl.stage AS delivery_stage, dl.scanner AS delivery_scanner,
                           dl.delivery_date AS delivery_date
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active'
                      AND dl.delivery_date = ?
                      AND li.order_no = ?
                      AND li.item_no = ?
                      AND COALESCE(li.job, '') = ?
                      AND COALESCE(li.customer, '') = ?
                    ORDER BY dl.delivery_date, dl.id, li.order_no, li.item_no
                    """,
                    (
                        delivery_date,
                        str(seed["order_no"] or ""),
                        str(seed["item_no"] or ""),
                        str(seed["job"] or ""),
                        str(seed["customer"] or ""),
                    ),
                ).fetchall()
            for row in rows:
                expanded[str(row["id"])] = row

        def stage_rank(row: Any) -> tuple[int, str, str]:
            """Purpose: Run the stage rank workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            text = f"{row_value(row, 'delivery_stage')} {row_value(row, 'delivery_scanner')}".lower()
            if "staging" in text:
                rank = 1
            elif "outbound" in text:
                rank = 2
            elif "indian trail" in text or "inbound" in text:
                rank = 3
            elif "greenville" in text or re.search(r"\bgnv\b", text):
                rank = 4
            elif "customer pickup" in text or re.search(r"\bcpu\b", text):
                rank = 5
            elif "dtc" in text or "deliver to customer" in text:
                rank = 6
            else:
                rank = 7
            return rank, str(row["order_no"] or ""), str(row["item_no"] or "")

        return sorted(expanded.values(), key=stage_rank)

    def priority_list_context(self, con: Any, rows: list[Any]) -> list[dict[str, Any]]:
        """Purpose: Run the priority list context workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        contexts: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            list_id = str(row["list_id"] or "")
            if not list_id or list_id in seen:
                continue
            seen.add(list_id)
            list_row = con.execute(
                "SELECT id, label, delivery_date, stage, scanner FROM delivery_lists WHERE id = ?",
                (list_id,),
            ).fetchone()
            if not list_row:
                continue
            contexts.append(
                {
                    "id": list_row["id"],
                    "label": list_row["label"],
                    "deliveryDate": list_row["delivery_date"],
                    "stage": list_row["stage"],
                    "scanner": list_row["scanner"],
                }
            )
        return contexts

    def ensure_manual_bay_delivery_list(self, con: sqlite3.Connection) -> str:
        """Purpose: Validate manual bay delivery list for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        today = now_iso()[:10]
        list_id = f"{today}-manual-bay-assignments"
        con.execute(
            """
            INSERT INTO delivery_lists (id, label, delivery_date, stage, scanner, status, revision, created_at)
            VALUES (?, ?, ?, 'Inbound - Indian Trail', 'Indian Trail', 'active', 1, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (list_id, f"{format_display_date(today)} - Manual Bay Assignments", today, now_iso()),
        )
        return list_id

    def create_manual_bay_line_item(self, con: sqlite3.Connection, scan_text: str, bay_code: str) -> sqlite3.Row:
        """Purpose: Create manual bay line item for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        list_id = self.ensure_manual_bay_delivery_list(con)
        clean = clean_barcode(scan_text) or f"MANUAL{secrets.token_hex(4).upper()}"
        digits = digits_only(scan_text)
        order_no = digits[:6] if len(digits) >= 4 else f"MAN{secrets.token_hex(3).upper()}"
        item_no = "000"
        line_id = f"manual-bay:{now_iso()}:{secrets.token_hex(5)}"
        con.execute(
            """
            INSERT INTO line_items (id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty, dimensions, customer, route, job, product, process_state, queue_state, suggested_bay)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, '', 'Manual Assign', '', ?, 'Manual Bay Item', 'Manual Assign', ?, ?)
            """,
            (line_id, list_id, line_id, clean, order_no, item_no, str(scan_text or "Manual bay item")[:255], str(scan_text or "")[:255], bay_code),
        )
        return con.execute("SELECT * FROM line_items WHERE id = ?", (line_id,)).fetchone()

    def assign_line_items_to_bay(self, con: sqlite3.Connection, rows: list[sqlite3.Row], bay: sqlite3.Row, user: str, reason: str) -> list[int]:
        """Purpose: Run the assign line items to bay workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        assignment_ids: list[int] = []
        for row in rows:
            existing = con.execute(
                """
                SELECT * FROM bay_assignments
                WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')
                ORDER BY id DESC
                LIMIT 1
                """,
                (row["id"],),
            ).fetchone()
            if existing:
                con.execute(
                    """
                    UPDATE bay_assignments
                    SET bay_id = ?, status = 'Assigned', assigned_by = ?, assigned_at = ?, reason = ?
                    WHERE id = ?
                    """,
                    (bay["id"], user, now_iso(), reason, existing["id"]),
                )
                self.insert_bay_event(con, bay["id"], row["id"], "ManualAssignMoveBay", user, reason, old_bay_id=existing["bay_id"], new_bay_id=bay["id"])
                assignment_ids.append(int(existing["id"]))
            else:
                cur = con.execute(
                    """
                    INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
                    VALUES (?, ?, ?, ?, 'Assigned', ?, ?, ?)
                    """,
                    (row["list_id"], row["id"], bay["id"], int(row["qty"] or 1), user, now_iso(), reason),
                )
                self.insert_bay_event(con, bay["id"], row["id"], "ManualAssignBay", user, reason, new_bay_id=bay["id"])
                assignment_ids.append(int(cur.lastrowid))
        return assignment_ids

    def manual_assign_bay_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the manual assign bay item workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        scan_text = str(data.get("scanText") or data.get("barcode") or data.get("order") or "").strip()
        item_no = str(data.get("itemNo") or data.get("item") or "").strip()
        bay_code = str(data.get("bayCode") or "").strip()
        confirm = str(data.get("confirmUnrecognized") or "").lower() in {"1", "true", "yes"}
        remember = str(data.get("rememberUnrecognized") or "").lower() in {"1", "true", "yes"}
        reason = str(data.get("reason") or "Manual bay assignment").strip()
        if not scan_text:
            raise ValueError("Manual assignment text is required")
        if not bay_code:
            raise ValueError("Choose a target bay before manual assigning")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            bay = self.get_bay_by_code(con, bay_code)
            rows = self.find_manual_bay_line_items(con, scan_text, item_no)
            known = bool(rows) or self.bay_manual_text_is_known(con, scan_text)
            if not rows and not known and not confirm:
                con.rollback()
                return {
                    "ok": False,
                    "needsConfirmation": True,
                    "message": "That input does not match a known order, Job Nr., barcode, or accepted bay scanner rule. Assign it anyway?",
                }
            if not rows:
                rows = [self.create_manual_bay_line_item(con, scan_text, bay_code)]
                if remember:
                    con.execute(
                        """
                        INSERT INTO bay_manual_input_rules (match_type, pattern, normalized_pattern, label, active, created_by, created_at, updated_at)
                        VALUES ('exact', ?, ?, ?, 1, ?, ?, ?)
                        """,
                        (scan_text[:500], normalized_match_text(scan_text), "Remembered from manual assign", user, now_iso(), now_iso()),
                    )
            assignment_ids = self.assign_line_items_to_bay(con, rows, bay, user, reason)
            self.insert_audit(con, "bay_manual_assign", bay_code, "manual_bay_assign", user, "Indian Trail", reason, {"scanText": scan_text, "itemNo": item_no, "matchedRows": len(rows), "remember": remember})
            con.commit()
        return {
            "ok": True,
            "message": f"Assigned {len(rows)} item{'s' if len(rows) != 1 else ''} to {bay['display_name'] or bay_code}.",
            "bayCode": bay_code,
            "assignmentIds": assignment_ids,
            "matchedCount": len(rows),
        }


    def route_from_customer_rules(self, item: dict[str, Any], rules: list[dict[str, Any]]) -> str:
        """Purpose: Run the route from customer rules workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        customer_name = str(item.get("customer", ""))
        normalized_customer = normalized_match_text(customer_name)
        matches = [
            rule
            for rule in rules
            if fuzzy_contains(customer_name, str(rule.get("customerPattern") or ""))
        ]
        if not matches:
            return ""
        matches.sort(
            key=lambda rule: (
                normalized_match_text(rule.get("customerPattern", "")) == normalized_customer,
                len(normalized_match_text(rule.get("customerPattern", ""))),
                -int(rule.get("id") or 0),
            ),
            reverse=True,
        )
        return str(matches[0].get("route") or "").strip().upper()

    def resolve_item_route(self, item: dict[str, Any], rules: list[dict[str, Any]]) -> str:
        """Resolve one item using the authoritative route order.

        1. CPU-Air/CPU-IT Job Nr. override.
        2. Active Customer Route Rule matched against customer name.
        3. Imported ROUTE value as a fallback for custom/manual routes.
        4. Blank route, which means Indian Trail in stage generation.
        """
        job_hint = job_number_route_hint(item)
        if job_hint is not None:
            return job_hint
        ruled_route = self.route_from_customer_rules(item, rules)
        if ruled_route:
            matched, canonical = canonical_route_designation(ruled_route)
            return canonical if matched else ruled_route
        raw_route = str(item.get("sourceRoute") or item.get("route") or "").strip()
        explicit, canonical = normalize_route_column(raw_route)
        return canonical if explicit else ""

    def apply_customer_route_rules_to_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Run the apply customer route rules to payload workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rules = self.get_customer_route_rules()
        next_payload = dict(payload)
        next_items = []
        for item in payload.get("items") or []:
            next_item = dict(item)
            next_item["sourceRoute"] = str(
                next_item.get("sourceRoute", next_item.get("route", "")) or ""
            ).strip()
            resolved_route = self.resolve_item_route(next_item, rules)
            next_item["route"] = resolved_route or "IT"
            next_items.append(next_item)
        next_payload["items"] = next_items
        return next_payload

    def validate_import_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Validate import payload for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Purpose: Load delivery list for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
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
            existing_list_rows = con.execute(
                "SELECT id, status FROM delivery_lists WHERE id IN ({})".format(",".join("?" for _ in definitions)),
                definition_ids,
            ).fetchall()
            active_existing_list_ids = {
                row["id"]
                for row in existing_list_rows
                if str(row["status"] or "").strip().lower() == "active"
            }
            reactivated_list_ids = {
                row["id"]
                for row in existing_list_rows
                if str(row["status"] or "").strip().lower() != "active"
            }
            if stale_profile_ids:
                con.execute(
                    "UPDATE delivery_lists SET status = 'inactive' WHERE id IN ({})".format(",".join("?" for _ in stale_profile_ids)),
                    stale_profile_ids,
                )
            import_cur = con.execute(
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
            stage_summaries: list[dict[str, Any]] = []
            for list_id, label, stage, scanner, items in definitions:
                summary = self.upsert_delivery_list(con, list_id, label, str(payload["deliveryDate"]), stage, scanner, items, replace_items=True)
                stage_reactivated = list_id in reactivated_list_ids
                summary["reactivated"] = stage_reactivated
                stage_summaries.append(summary)
                if summary["created"] or stage_reactivated or summary["changedLineCount"] or summary["changedPieceQty"]:
                    changed_list_ids.append(list_id)
                    event_type = "import" if summary["created"] or stage_reactivated else "update"
                    event_message = "Delivery list imported" if summary["created"] else "Delivery list updated"
                    event_reason = (
                        f"{source_name or 'Delivery-list source'} | "
                        f"{summary['changedLineCount']} changed line(s) | "
                        f"{summary['addedPieceQty']} added piece(s) | "
                        f"{summary['changedPieceQty']} changed piece(s)"
                    )
                    self.insert_event(con, list_id, None, event_type.upper(), "", user, scanner, event_type, event_message, event_reason)
                    self.insert_audit(con, "delivery_list", list_id, event_type, user, scanner, event_reason, {"sourceName": source_name, "sourceHash": source_hash, "summary": summary})
            change_summary = {
                "sourceName": source_name,
                "deliveryDate": delivery_date,
                "createdCount": sum(1 for summary in stage_summaries if summary["created"] or summary.get("reactivated")),
                "reactivatedCount": sum(1 for summary in stage_summaries if summary.get("reactivated")),
                "reactivatedListIds": [summary["listId"] for summary in stage_summaries if summary.get("reactivated")],
                "updatedCount": sum(1 for summary in stage_summaries if not summary["created"] and not summary.get("reactivated") and (summary["changedLineCount"] or summary["changedPieceQty"])),
                "addedPieceQty": sum(int(summary["addedPieceQty"] or 0) for summary in stage_summaries),
                "changedPieceQty": sum(int(summary["changedPieceQty"] or 0) for summary in stage_summaries),
                "removedLineCount": sum(int(summary.get("removedLineCount") or 0) for summary in stage_summaries),
                "removedPieceQty": sum(int(summary.get("removedPieceQty") or 0) for summary in stage_summaries),
                "stages": stage_summaries,
                "changedListIds": changed_list_ids,
            }
            con.execute("UPDATE imports SET change_summary = ? WHERE id = ?", (json.dumps(change_summary, separators=(",", ":")), import_cur.lastrowid))
            # Queue customer manifests for every import/update attempt, not only when rows changed.
            # This lets newly-added customer email rules catch the next import even when the list file is unchanged.
            self.send_customer_manifests_for_import(con, payload, user)
            con.commit()
        created_count = sum(1 for definition in definitions if definition[0] not in active_existing_list_ids)
        reactivated_count = sum(1 for definition in definitions if definition[0] in reactivated_list_ids)
        updated_count = sum(1 for summary in stage_summaries if not summary["created"] and not summary.get("reactivated") and (summary["changedLineCount"] or summary["changedPieceQty"]))
        return {
            "lists": self.get_delivery_lists(),
            "activeListId": definitions[0][0],
            "importedCount": len(definitions),
            "createdCount": created_count,
            "reactivatedCount": reactivated_count,
            "reactivatedListIds": sorted(reactivated_list_ids),
            "updatedCount": updated_count,
            "changedListIds": changed_list_ids,
            "stageSummaries": stage_summaries,
            "addedPieceQty": sum(int(summary["addedPieceQty"] or 0) for summary in stage_summaries),
            "changedPieceQty": sum(int(summary["changedPieceQty"] or 0) for summary in stage_summaries),
            "removedLineCount": sum(int(summary.get("removedLineCount") or 0) for summary in stage_summaries),
            "removedPieceQty": sum(int(summary.get("removedPieceQty") or 0) for summary in stage_summaries),
            "printCandidates": self.print_candidates_from_payload(payload, changed_list_ids, source_name, stage_summaries),
        }

    def print_candidates_from_payload(self, payload: dict[str, Any], list_ids: list[str], source_name: str, stage_summaries: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """Purpose: Run the print candidates from payload workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
        counts = print_counts_for_items(payload.get("items") or [])
        stage_summaries = stage_summaries or []
        changed_piece_qty = sum(int(summary.get("changedPieceQty") or 0) for summary in stage_summaries if summary.get("listId") in set(list_ids))
        added_piece_qty = sum(int(summary.get("addedPieceQty") or 0) for summary in stage_summaries if summary.get("listId") in set(list_ids))
        if not counts["pieceCount"] or not list_ids:
            return []
        return [
            {
                "sourceName": source_name,
                "deliveryDate": str(payload.get("deliveryDate") or ""),
                "listIds": list_ids,
                "stageSummaries": [summary for summary in stage_summaries if summary.get("listId") in set(list_ids)],
                "changedPieceQty": changed_piece_qty,
                "addedPieceQty": added_piece_qty,
                **counts,
            }
        ]

    def import_delivery_folder(self, data: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Load delivery folder for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
                    try:
                        modified_date = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
                    except OSError:
                        modified_date = ""
                    if modified_date and modified_date < date_from:
                        skipped_files.append(
                            {
                                "fileName": path.name,
                                "deliveryDate": file_date,
                                "fileNameDate": file_date,
                                "reason": f"Filename date and file modified date are outside import window before {date_from}",
                            }
                        )
                        continue
                header_date = delivery_date_from_source_header(path)
                if header_date and date_from and header_date < date_from:
                    skipped_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": header_date,
                            "fileNameDate": file_date,
                            "reason": f"Workbook delivery date is outside import window before {date_from}",
                        }
                    )
                    continue
                if header_date and date_to and header_date > date_to:
                    skipped_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": header_date,
                            "fileNameDate": file_date,
                            "reason": f"Workbook delivery date is outside import window after {date_to}",
                        }
                    )
                    continue
                file_hash = source_file_hash(path)
                source_path = str(path.resolve())
                payload = load_delivery_source_payload(path)
                payload_date = str(payload.get("deliveryDate") or "").strip()
                if payload_date and payload_date != header_date and date_from and payload_date < date_from:
                    skipped_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": payload_date,
                            "fileNameDate": file_date,
                            "reason": f"Workbook delivery date is outside import window before {date_from}",
                        }
                    )
                    continue
                if payload_date and payload_date != header_date and date_to and payload_date > date_to:
                    skipped_files.append(
                        {
                            "fileName": path.name,
                            "deliveryDate": payload_date,
                            "fileNameDate": file_date,
                            "reason": f"Workbook delivery date is outside import window after {date_to}",
                        }
                    )
                    continue
                definitions = build_delivery_lists(payload)
                definition_ids = [definition[0] for definition in definitions]

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

                    active_definition_ids = set()
                    if definition_ids:
                        placeholders = ",".join("?" for _ in definition_ids)
                        active_definition_ids = {
                            row["id"]
                            for row in con.execute(
                                f"""
                                SELECT id
                                FROM delivery_lists
                                WHERE status = 'active'
                                  AND id IN ({placeholders})
                                """,
                                definition_ids,
                            ).fetchall()
                        }

                same_active_file = (
                    previous
                    and previous["source_hash"] == file_hash
                    and set(definition_ids).issubset(active_definition_ids)
                )

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
                    "reactivatedCount": result.get("reactivatedCount", 0),
                    "updatedCount": result["updatedCount"],
                    "listIds": result["changedListIds"],
                    "stageSummaries": result.get("stageSummaries") or [],
                    "addedPieceQty": result.get("addedPieceQty", 0),
                    "changedPieceQty": result.get("changedPieceQty", 0),
                }
                if not result["createdCount"] and not result["updatedCount"] and not result.get("changedListIds"):
                    skipped_files.append({
                        "fileName": path.name,
                        "reason": "No updates" if same_active_file else "No delivery-list line changes detected",
                    })
                    continue
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
        """Purpose: Read print package for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        filters = filters or {}
        rush_only = str(filters.get("rushOnly") or "").lower() in {"1", "true", "yes"}
        remake_only = str(filters.get("remakeOnly") or "").lower() in {"1", "true", "yes"}
        cpu_only = str(filters.get("cpuOnly") or "").lower() in {"1", "true", "yes"}
        dtc_only = str(filters.get("dtcOnly") or "").lower() in {"1", "true", "yes"}
        updated_only = str(filters.get("updatedOnly") or "").lower() in {"1", "true", "yes"}
        glass_types = [term.strip().lower() for term in re.split(r"[,;\n]+", str(filters.get("glassType") or "")) if term.strip()]
        mirror_mode = str(filters.get("mirrorMode") or "exclude").strip().lower()
        include_mirror_remakes = str(filters.get("includeMirrorRemakes") or "").lower() in {"1", "true", "yes"}
        customer_filter = str(filters.get("customers") or "").strip().lower()
        order_filter = str(filters.get("orders") or "").strip()
        source_id_filter = str(filters.get("sourceIds") or "").strip()
        search_query = str(filters.get("searchQuery") or "").strip().lower()
        search_digits = digits_only(search_query)
        customer_terms = [term.strip() for term in re.split(r"[,;\n]+", customer_filter) if term.strip()]
        order_terms = [digits_only(term) for term in re.split(r"[,;\s\n]+", order_filter) if digits_only(term)]
        source_id_terms = {term.strip() for term in re.split(r"[,;\n]+", source_id_filter) if term.strip()}

        def exact_filter_values(key: str) -> list[str]:
            raw_value = filters.get(key)
            if not raw_value:
                return []
            try:
                parsed_value = json.loads(str(raw_value))
            except (TypeError, ValueError, json.JSONDecodeError):
                return []
            if not isinstance(parsed_value, list):
                return []
            return [str(value).strip() for value in parsed_value if str(value).strip()]

        exact_glass_types = {value.lower() for value in exact_filter_values("glassTypesExact")}
        exact_customers = {value.lower() for value in exact_filter_values("customersExact")}
        exact_orders = {digits_only(value) for value in exact_filter_values("ordersExact") if digits_only(value)}
        exact_order_items = {
            str(value).strip()
            for value in exact_filter_values("orderItemsExact")
            if str(value).strip()
        }
        exact_line_item_ids = {
            str(value).strip()
            for value in exact_filter_values("lineItemIdsExact")
            if str(value).strip()
        }
        exact_row_keys = {
            str(value).strip()
            for value in exact_filter_values("rowKeysExact")
            if str(value).strip()
        }
        exact_routes = {value.lower() for value in exact_filter_values("routesExact")}
        exact_route_groups = {value.lower() for value in exact_filter_values("routeGroupsExact")}
        exact_statuses = {value.lower() for value in exact_filter_values("statusesExact")}
        exact_attention = {value.lower() for value in exact_filter_values("attentionExact")}
        selected_mirror_glass = any(
            re.search(r"mirror|mirr|\bmir\b", glass_type)
            for glass_type in [*glass_types, *exact_glass_types]
        )

        def has_update_marker(item: dict[str, Any]) -> bool:
            """Purpose: Validate update marker for the delivery-list scanner workflow.

            Effects: This function reads or updates shared application state.
            Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
            """
            text = f"{item.get('processState', '')} {item.get('queueState', '')}"
            return re.search(r"\b(update|updated|new|change|changed|added|add)\b", text, flags=re.IGNORECASE) is not None

        def route_matches(item: dict[str, Any]) -> bool:
            """Purpose: Run the route matches workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            if cpu_only and not is_cpu_item(item):
                return False
            if dtc_only and route_category(item) != "dtc":
                return False
            return True

        def glass_filter_matches(item: dict[str, Any]) -> bool:
            """Purpose: Run the glass filter matches workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            if exact_glass_types:
                glass_value = str(
                    item.get("product")
                    or item.get("job")
                    or item.get("suggestedBay")
                    or "Other Glass"
                ).strip().lower()
                if glass_value in exact_glass_types:
                    return True
                return include_mirror_remakes and not selected_mirror_glass and is_mirror_item(item) and is_remake_item(item)
            if not glass_types:
                return True
            glass_signal = f"{item.get('product', '')} {item.get('job', '')}".lower()
            if any(glass_type in glass_signal for glass_type in glass_types):
                return True
            return include_mirror_remakes and not selected_mirror_glass and is_mirror_item(item) and is_remake_item(item)

        def item_status_key(item: dict[str, Any]) -> str:
            qty = max(int(item.get("qty") or 0), 0)
            scanned = max(int(item.get("scanned") or 0), 0)
            if qty > 0 and scanned >= qty:
                return "complete"
            if scanned > 0:
                return "partial"
            return "not-scanned"

        def item_attention_keys(item: dict[str, Any]) -> set[str]:
            keys: set[str] = set()
            if is_remake_item(item):
                keys.add("remake")
            if is_rush_item(item):
                keys.add("rush")
            if int(item.get("internalRejectCount") or 0) > 0:
                keys.add("reject")
            if has_update_marker(item):
                keys.add("updated")
            if str(item.get("errorType") or "").strip() or str(item.get("errorReason") or "").strip():
                keys.add("error")
            return keys

        def search_filters_match(item: dict[str, Any], list_id: str = "") -> bool:
            """Purpose: Run the search filters match workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            order_value = digits_only(str(item.get("order", "")))
            item_value = digits_only(str(item.get("item", "")))
            line_item_id = str(item.get("id") or "").strip()
            row_key = f"{str(list_id or '').strip()}|{order_value}|{item_value}"
            order_item_key = f"{order_value}|{item_value}"

            # The browser's live preview sends exact authoritative line-item IDs
            # after applying every visible filter. When present, use those IDs as
            # the source of truth so preview, print, PDF, XLSX, and CSV cannot
            # disagree because two implementations interpreted a label differently.
            if exact_line_item_ids or exact_row_keys:
                return (
                    bool(line_item_id and line_item_id in exact_line_item_ids)
                    or row_key in exact_row_keys
                )

            if not glass_filter_matches(item):
                return False
            customer_value = str(item.get("customer", "")).strip().lower()
            job_value = f"{item.get('job', '')} {item.get('product', '')} {item.get('sourceId', '')}".strip().lower()
            route_value = str(item.get("route") or "Unassigned").strip().lower() or "unassigned"
            route_group_value = route_category(item)
            if route_group_value.startswith("custom:"):
                route_group_value = "indian_trail"
            if search_query:
                search_matches_customer = search_query in customer_value
                search_matches_order = bool(search_digits and search_digits in order_value)
                search_matches_job = search_query in job_value
                if not search_matches_customer and not search_matches_order and not search_matches_job:
                    return False
            if exact_route_groups and "airport" not in exact_route_groups and route_group_value not in exact_route_groups:
                return False
            if exact_routes and route_value not in exact_routes:
                return False
            if exact_statuses and item_status_key(item) not in exact_statuses:
                return False
            if exact_attention and not (item_attention_keys(item) & exact_attention):
                return False
            if exact_customers and customer_value not in exact_customers:
                return False
            if not exact_customers and customer_terms and not any(term in customer_value for term in customer_terms):
                return False
            if exact_orders or exact_order_items:
                if order_value not in exact_orders and order_item_key not in exact_order_items:
                    return False
            elif order_terms and order_value not in order_terms:
                return False
            if source_id_terms and str(item.get("sourceId") or "").strip() not in source_id_terms:
                return False
            return True

        def normal_printable(item: dict[str, Any]) -> bool:
            """Purpose: Run the normal printable workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
            """
            if is_remake_item(item):
                return False
            if mirror_mode == "only":
                return is_mirror_item(item)
            if mirror_mode == "include":
                return True
            return should_print_delivery_item(item, exclude_mirrors=True, include_mirror_remakes=False)

        def stage_sheet_kind(meta: dict[str, Any]) -> str:
            """Purpose: Run the stage sheet kind workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            text = f"{meta.get('stage', '')} {meta.get('scanner', '')} {meta.get('label', '')}".lower()
            if "customer pickup" in text or " cpu" in f" {text}" or "cpu" in text:
                return "cpu"
            if "dtc" in text or "deliver to customer" in text:
                return "dtc"
            if "indian trail" in text or "inbound" in text:
                return "indian-trail"
            if "greenville" in text or "gnv" in text:
                return "greenville"
            if "outbound" in text:
                return "outbound"
            if "staging" in text:
                return "staging"
            return "regular"

        package_lists: list[dict[str, Any]] = []
        seen_list_ids: set[str] = set()

        for list_id in list_ids:
            if list_id in seen_list_ids:
                continue
            seen_list_ids.add(list_id)
            try:
                payload = self.get_delivery_list(list_id, user=user)
            except (KeyError, PermissionError):
                continue

            meta = payload["meta"]
            source_items = list(payload.get("items") or [])
            filtered_source = [
                item
                for item in source_items
                if route_matches(item) and search_filters_match(item, list_id)
            ]
            remakes = [item for item in filtered_source if is_remake_item(item)]
            rushes = [item for item in filtered_source if is_rush_item(item) and not is_remake_item(item)]
            updated_remakes = [item for item in remakes if has_update_marker(item)]

            # Updated-list printing should only print remake rows that were new/changed by the
            # latest import. Regular remakes still print when printing a whole list or remake-only
            # list, but they should not be pulled onto an updated remake sheet just because they
            # already existed on the delivery list.
            if rush_only:
                normal_items: list[dict[str, Any]] = []
                remake_items: list[dict[str, Any]] = []
                rush_items = rushes if not updated_only else [item for item in rushes if has_update_marker(item)]
            elif remake_only:
                normal_items = []
                remake_items = updated_remakes if updated_only else remakes
                rush_items = []
            else:
                normal_items = [
                    item
                    for item in filtered_source
                    if normal_printable(item)
                    and not is_rush_item(item)
                    and (not updated_only or has_update_marker(item))
                ]
                remake_items = updated_remakes if updated_only else remakes
                rush_items = rushes if not updated_only else [item for item in rushes if has_update_marker(item)]

            package_items = sorted(
                [*normal_items, *remake_items, *rush_items],
                key=lambda item: (str(item.get("product") or item.get("job") or ""), int(item.get("order") or 0), int(item.get("item") or 0)),
            )
            if not package_items:
                continue

            excluded_regular_mirrors = [] if mirror_mode == "include" else [
                item
                for item in source_items
                if is_mirror_item(item) and not is_remake_item(item) and route_matches(item) and search_filters_match(item, list_id)
            ]

            stage_kind = stage_sheet_kind(meta)
            original_delivery_date = str(meta["deliveryDate"] or "")
            rush_delivery_dates = sorted({
                str(item.get("priorityDeliveryDate") or "").strip()
                for item in rush_items
                if str(item.get("priorityDeliveryDate") or "").strip()
            })
            effective_delivery_date = rush_delivery_dates[0] if rush_only and len(rush_delivery_dates) == 1 else original_delivery_date
            package_lists.append(
                {
                    "id": meta["id"],
                    "label": meta["label"],
                    "stage": meta["stage"],
                    "scanner": meta.get("scanner", ""),
                    "stages": [meta["stage"]],
                    "deliveryDate": effective_delivery_date,
                    "originalDeliveryDate": original_delivery_date,
                    "priorityDirectToTruck": any(bool(item.get("priorityDirectToTruck")) for item in rush_items),
                    "items": package_items,
                    "normalItems": normal_items,
                    "remakes": remake_items,
                    "rushes": rush_items,
                    "sheetKind": "updated" if updated_only else stage_kind,
                    "stageKind": stage_kind,
                    "excludedMirrorCount": len(excluded_regular_mirrors),
                }
            )

        return {"lists": package_lists, "generatedAt": now_iso(), "filters": filters}

    def find_unique_suffix_item(self, rows: list[sqlite3.Row], suffix: str, item_no: int) -> sqlite3.Row | None:
        """Purpose: Resolve unique suffix item for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        matches = []
        for row in rows:
            if int(row["item_no"]) == item_no and f"{int(row['order_no']):06d}".endswith(suffix):
                matches.append(row)
        return matches[0] if len(matches) == 1 else None

    def find_unique_order(self, rows: list[sqlite3.Row], order_no: int) -> sqlite3.Row | None:
        """Purpose: Resolve unique order for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        matches = [row for row in rows if int(row["order_no"]) == order_no]
        return matches[0] if len(matches) == 1 else None

    def recover_bay_external_scan(self, raw_scan: str, rows: list[Any]) -> tuple[Any | None, str, str]:
        """Resolve alternate product labels used by Bay Map Add and Remove.

        Effects: Performs a read-only comparison against the rows already loaded by
        the caller. It accepts an exact stored barcode/source/job value and labels
        such as ``43273429.30`` where the left side identifies the job/source and
        the right side identifies the line item.
        Flow: Scores exact matches ahead of contains-style recovery, returns only a
        unique highest-confidence row, and reports ambiguity instead of guessing.
        """
        text = str(raw_scan or "").strip()
        normalized = normalized_match_text(text)
        clean = clean_barcode(text)
        if not normalized:
            return None, clean, "No unique delivery-list match"

        separated = re.fullmatch(r"\s*(\d{4,12})\s*[./\\\-\s]+\s*(\d{1,4})\s*", text)
        reference_base = normalized_match_text(separated.group(1)) if separated else ""
        reference_item = int(separated.group(2)) if separated else None
        scored: list[tuple[int, Any]] = []

        for row in rows:
            barcode_text = normalized_match_text(row_value(row, "barcode", ""))
            source_text = normalized_match_text(row_value(row, "source_id", ""))
            job_text = normalized_match_text(row_value(row, "job", ""))
            order_text = normalized_match_text(row_value(row, "order_no", ""))
            item_text = digits_only(row_value(row, "item_no", ""))
            score = 0

            if barcode_text and normalized == barcode_text:
                score = max(score, 500)
            if source_text and normalized == source_text:
                score = max(score, 480)
            if job_text and normalized == job_text:
                score = max(score, 450)
            if order_text and normalized == order_text:
                score = max(score, 440)

            if reference_base and reference_item is not None:
                try:
                    row_item = int(item_text or 0)
                except ValueError:
                    row_item = -1
                if row_item == reference_item:
                    if order_text and reference_base == order_text:
                        score = max(score, 530)
                    elif order_text and reference_base in order_text:
                        score = max(score, 485)
                    if job_text and reference_base == job_text:
                        score = max(score, 510)
                    elif job_text and reference_base in job_text:
                        score = max(score, 470)
                    if source_text and reference_base == source_text:
                        score = max(score, 500)
                    elif source_text and reference_base in source_text:
                        score = max(score, 460)
                    if barcode_text and reference_base in barcode_text:
                        score = max(score, 455)

            if len(normalized) >= 8:
                if job_text and normalized in job_text:
                    score = max(score, 410)
                if source_text and normalized in source_text:
                    score = max(score, 400)

            if score:
                scored.append((score, row))

        if not scored:
            return None, clean, "No unique delivery-list match"

        best_score = max(score for score, _row in scored)
        best_rows = [row for score, row in scored if score == best_score]
        unique: dict[str, Any] = {}
        for row in best_rows:
            identity = str(row_value(row, "line_item_id", "") or row_value(row, "id", "") or id(row))
            unique[identity] = row
        if len(unique) != 1:
            return None, clean, "Ambiguous external Bay barcode"

        matched = next(iter(unique.values()))
        order_text = digits_only(row_value(matched, "order_no", ""))
        item_text = digits_only(row_value(matched, "item_no", ""))
        canonical = (
            canonical_barcode(order_text, item_text)
            if order_text and item_text and len(order_text) <= 6
            else clean
        )
        return matched, canonical, "Matched external Bay barcode"

    def recover_scan(
        self,
        raw_scan: str,
        rows: list[sqlite3.Row],
        *,
        strict_order_item: bool = False,
    ) -> tuple[sqlite3.Row | None, str, str]:
        """Resolve one scan without allowing manual entries to degrade into suffix matches.

        Physical labels retain the maintained recovery behavior for damaged or
        alternate barcode formats. Manual scans are exact six-digit order and
        item lookups so an entry such as 235804 can never resolve to 236804 just
        because both orders end in 804.
        """
        clean_text = clean_barcode(raw_scan)
        by_order_item: dict[tuple[int, int], list[sqlite3.Row]] = {}
        for row in rows:
            by_order_item.setdefault((int(row["order_no"]), int(row["item_no"])), []).append(row)

        exact_order_item: tuple[int, int] | None = None
        exact_canonical = clean_text
        if re.fullmatch(r"T200\d{12}", clean_text):
            exact_order_item = (int(clean_text[4:10]), int(clean_text[10:13]))
        elif strict_order_item:
            manual_digits = digits_only(raw_scan)
            if 7 <= len(manual_digits) <= 9:
                exact_order_item = (int(manual_digits[:6]), int(manual_digits[6:]))
                exact_canonical = canonical_barcode(*exact_order_item)

        if exact_order_item is not None:
            matches = by_order_item.get(exact_order_item, [])
            if len(matches) == 1:
                return matches[0], exact_canonical, "Exact manual order/item" if strict_order_item else "Exact label"
            if len(matches) > 1:
                return None, exact_canonical, "Ambiguous delivery-list match"
            if strict_order_item:
                return None, exact_canonical, "No exact order/item match"
        elif strict_order_item:
            return None, clean_text, "Manual scans require an exact six-digit order and one-to-three-digit item"

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

    def cross_date_line_location(self, con: Any, line_item_id: str) -> str:
        """Return the active Bay or Rack location for one cross-date candidate."""
        bay_row = con.execute(
            """
            SELECT b.bay_code
            FROM bay_assignments ba
            JOIN bays b ON b.id = ba.bay_id
            WHERE ba.line_item_id = ?
              AND ba.status NOT IN ('Cleared', 'Cancelled')
            ORDER BY ba.id DESC
            LIMIT 1
            """,
            (line_item_id,),
        ).fetchone()
        if bay_row and str(bay_row["bay_code"] or "").strip():
            return str(bay_row["bay_code"] or "").strip()

        rack_row = con.execute(
            """
            SELECT r.rack_code
            FROM rack_items ri
            JOIN racks r ON r.id = ri.rack_id
            WHERE ri.line_item_id = ?
              AND ri.status = 'Active'
              AND r.active = 1
            ORDER BY ri.id DESC
            LIMIT 1
            """,
            (line_item_id,),
        ).fetchone()
        return str(rack_row["rack_code"] or "").strip() if rack_row else ""

    def cross_date_candidate_safety(
        self,
        con: Any,
        list_row: Any,
        row: Any,
        scan_request: dict[str, Any],
    ) -> dict[str, Any]:
        """Preflight the safeguards that must prevent a silent date switch."""
        reasons: list[str] = []
        clear_rack = False
        rack_code = normalize_rack_code(str(scan_request.get("rackCode") or ""))
        bay_code = str(scan_request.get("bayCode") or "").strip()
        destination_override = str(scan_request.get("destinationOverride") or "").lower() in {"1", "true", "yes"}
        outbound_override = str(scan_request.get("outboundOverride") or "").lower() in {"1", "true", "yes"}
        category = scan_stage_category(list_row["stage"], list_row["scanner"])
        complete = int(row["scanned_qty"] or 0) >= int(row["qty"] or 0)
        rack_preserved = not bool(rack_code)
        bay_preserved = not bool(bay_code)

        if complete:
            reasons.append("This line is already fully scanned on that delivery date.")

        if category == "staged" and rack_code:
            rack = con.execute(
                "SELECT * FROM racks WHERE UPPER(rack_code) = UPPER(?) AND active = 1 LIMIT 1",
                (rack_code,),
            ).fetchone()
            if not rack:
                reasons.append(f"Selected rack {rack_code} is no longer available.")
                clear_rack = True
            else:
                rack_status = str(rack["status"] or "Open").strip().lower()
                if rack_status != "open":
                    reasons.append(f"Selected rack {rack_code} is {rack['status']} and cannot be preserved.")
                    clear_rack = True
                else:
                    item_destination = self.destination_for_line_item(row)
                    rack_destinations = self.rack_destinations_from_items(con, int(rack["id"]))
                    mismatch = bool(rack_destinations and rack_destinations != [item_destination])
                    override_active = bool(mismatch and self.rack_destination_override_active(rack))
                    if mismatch and not destination_override and not override_active:
                        reasons.append(
                            f"Rack {rack_code} contains {', '.join(rack_destinations)} pieces and cannot be preserved for {item_destination}. The rack selection will be cleared."
                        )
                        clear_rack = True
                    else:
                        rack_preserved = True
        elif rack_code:
            rack_preserved = False

        if category == "outbound":
            staging_row = self.matching_staging_row_for_outbound(con, list_row, row)
            staged = bool(staging_row and int(staging_row["scanned_qty"] or 0) > 0)
            transportation = self.transportation_for_staging_row(con, staging_row["id"]) if staging_row else None
            if (not staged or not transportation) and not outbound_override:
                missing = []
                if not staged:
                    missing.append("staging scan")
                if not transportation:
                    missing.append("rack/truck transportation")
                reasons.append(f"This outbound line still requires {' and '.join(missing)}.")

        if category == "received":
            outbound_row = con.execute(
                """
                SELECT COALESCE(MAX(out_li.scanned_qty), 0) AS scanned_qty
                FROM delivery_lists out_dl
                JOIN line_items out_li ON out_li.list_id = out_dl.id
                WHERE out_dl.delivery_date = ?
                  AND out_dl.status = 'active'
                  AND LOWER(out_dl.stage) LIKE '%outbound%'
                  AND out_li.order_no = ?
                  AND out_li.item_no = ?
                """,
                (list_row["delivery_date"], row["order_no"], row["item_no"]),
            ).fetchone()
            if int(outbound_row["scanned_qty"] or 0) <= 0 and not outbound_override:
                reasons.append("This Indian Trail receive still requires an Outbound scan or supervisor override.")

        if bay_code:
            bay_preserved = True
            reasons.append(f"Manual Bay {bay_code} is selected and must be confirmed for the other delivery date.")

        return {
            "complete": complete,
            "selectable": not complete,
            "requiresConfirmation": bool(reasons),
            "safetyReasons": reasons,
            "safetyReason": " ".join(reasons),
            "rackPreserved": rack_preserved,
            "bayPreserved": bay_preserved,
            "clearRack": clear_rack,
            "originalRackCode": rack_code,
            "originalBayCode": bay_code,
        }

    def cross_date_scan_candidates(
        self,
        con: Any,
        current_list: Any,
        raw_scan: str,
        scan_request: dict[str, Any],
        user_context: dict[str, Any] | None,
        settings: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Find unique matches on active lists in the configured date window and same stage."""
        try:
            current_date = datetime.strptime(str(current_list["delivery_date"] or ""), "%Y-%m-%d")
        except ValueError:
            return []
        start_date = (current_date - timedelta(days=int(settings["pastDays"]))).strftime("%Y-%m-%d")
        end_date = (current_date + timedelta(days=int(settings["futureDays"]))).strftime("%Y-%m-%d")
        category = scan_stage_category(current_list["stage"], current_list["scanner"])
        list_rows = con.execute(
            """
            SELECT *
            FROM delivery_lists
            WHERE id <> ?
              AND status = 'active'
              AND delivery_date BETWEEN ? AND ?
            ORDER BY delivery_date, stage, id
            """,
            (current_list["id"], start_date, end_date),
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for list_row in list_rows:
            if scan_stage_category(list_row["stage"], list_row["scanner"]) != category:
                continue
            if user_context and not user_can_access_stage(user_context, list_row["stage"], list_row["scanner"]):
                continue
            rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_row["id"],)).fetchall()
            if not rows:
                continue
            is_manual = str(scan_request.get("isManual") or "").lower() in {"1", "true", "yes"}
            matched_row, canonical, match_reason = self.recover_scan(
                raw_scan,
                rows,
                strict_order_item=is_manual,
            )
            if matched_row is None and category == "received" and not is_manual:
                external_row, external_canonical, external_reason = self.recover_bay_external_scan(raw_scan, rows)
                if external_row is not None:
                    matched_row, canonical, match_reason = external_row, external_canonical, external_reason
            if matched_row is None:
                continue
            safety = self.cross_date_candidate_safety(con, list_row, matched_row, scan_request)
            candidates.append(
                {
                    "listId": str(list_row["id"] or ""),
                    "label": str(list_row["label"] or ""),
                    "deliveryDate": str(list_row["delivery_date"] or ""),
                    "stage": str(list_row["stage"] or ""),
                    "scanner": str(list_row["scanner"] or ""),
                    "lineItemId": str(matched_row["id"] or ""),
                    "canonicalBarcode": canonical,
                    "matchReason": match_reason,
                    "order": str(matched_row["order_no"] or ""),
                    "item": str(matched_row["item_no"] or ""),
                    "qty": int(matched_row["qty"] or 0),
                    "scannedQty": int(matched_row["scanned_qty"] or 0),
                    "route": str(matched_row["route"] or ""),
                    "customer": str(matched_row["customer"] or ""),
                    "location": self.cross_date_line_location(con, str(matched_row["id"] or "")),
                    **safety,
                }
            )

        candidates.sort(
            key=lambda candidate: (
                abs((datetime.strptime(candidate["deliveryDate"], "%Y-%m-%d") - current_date).days),
                candidate["deliveryDate"],
                candidate["stage"],
                candidate["listId"],
            )
        )
        return candidates

    def resolve_cross_date_scan(self, scan_request: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve a failed current-list match into a safe target or a user choice payload."""
        current_list_id = str(scan_request.get("listId") or "").strip()
        raw_scan = str(scan_request.get("barcode") or "").strip()
        if not current_list_id or not raw_scan or scan_request.get("_crossDateResolved"):
            return None
        explicit_target_id = str(scan_request.get("crossDateListId") or "").strip()
        confirmed = str(scan_request.get("crossDateConfirmed") or "").lower() in {"1", "true", "yes"}
        user_context = scan_request.get("_userContext") if isinstance(scan_request.get("_userContext"), dict) else None
        user_name = request_user_name(scan_request)
        station = request_station(scan_request)

        with self.connect() as con:
            current_list = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (current_list_id,)).fetchone()
            if not current_list or str(current_list["status"] or "").strip().lower() != "active":
                return None
            current_rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (current_list_id,)).fetchall()
            is_manual = str(scan_request.get("isManual") or "").lower() in {"1", "true", "yes"}
            current_row, _canonical, current_reason = self.recover_scan(
                raw_scan,
                current_rows,
                strict_order_item=is_manual,
            )
            if current_row is None and scan_stage_category(current_list["stage"], current_list["scanner"]) == "received" and not is_manual:
                external_row, _external_canonical, external_reason = self.recover_bay_external_scan(raw_scan, current_rows)
                if external_row is not None:
                    current_row = external_row
                elif external_reason.startswith("Ambiguous"):
                    current_reason = external_reason
            if current_row is not None or current_reason.startswith("Ambiguous"):
                return None

            settings = self.cross_date_scan_settings_con(con)
            if settings["mode"] == "disabled":
                return None
            candidates = self.cross_date_scan_candidates(
                con,
                current_list,
                raw_scan,
                scan_request,
                user_context,
                settings,
            )
            if not candidates:
                return None

            self.insert_audit(
                con,
                "scan",
                current_list_id,
                "cross_date_scan_match_found",
                user_name,
                station,
                "",
                {
                    "barcode": raw_scan,
                    "originalDeliveryDate": current_list["delivery_date"],
                    "originalStage": current_list["stage"],
                    "mode": settings["mode"],
                    "candidateListIds": [candidate["listId"] for candidate in candidates],
                    "candidateDates": [candidate["deliveryDate"] for candidate in candidates],
                },
            )
            con.commit()

        original = {
            "listId": str(current_list["id"] or ""),
            "deliveryDate": str(current_list["delivery_date"] or ""),
            "stage": str(current_list["stage"] or ""),
            "scanner": str(current_list["scanner"] or ""),
        }
        if confirmed and explicit_target_id:
            selected = next((candidate for candidate in candidates if candidate["listId"] == explicit_target_id), None)
            if not selected:
                raise ValueError("The selected cross-date delivery list is no longer available")
            if not selected["selectable"]:
                raise ValueError(selected["safetyReason"] or "The selected line cannot be scanned")
            return {"candidate": selected, "original": original, "automatic": False, "settings": settings}

        automatic = settings["mode"] == "auto_unique"
        if len(candidates) == 1 and automatic and not candidates[0]["requiresConfirmation"]:
            return {"candidate": candidates[0], "original": original, "automatic": True, "settings": settings}

        return {
            "selection": {
                "ok": False,
                "crossDateSelectionRequired": True,
                "message": (
                    "This item was found on another delivery date. Confirm the correct list before scanning."
                    if len(candidates) == 1
                    else "This item was found on multiple delivery dates. Select the correct list before scanning."
                ),
                "originalListId": original["listId"],
                "originalDeliveryDate": original["deliveryDate"],
                "originalStage": original["stage"],
                "mode": settings["mode"],
                "pastDays": settings["pastDays"],
                "futureDays": settings["futureDays"],
                "candidates": candidates,
            }
        }

    def attach_cross_date_result(
        self,
        payload: dict[str, Any],
        resolved: dict[str, Any],
        scan_request: dict[str, Any],
        operation: str,
    ) -> dict[str, Any]:
        """Attach switch metadata and record the immutable cross-date audit event."""
        candidate = resolved["candidate"]
        original = resolved["original"]
        user = request_user_name(scan_request)
        station = request_station(scan_request)
        last_scan = payload.get("lastScan") if isinstance(payload.get("lastScan"), dict) else {}
        outcome = "accepted" if last_scan.get("ok") or payload.get("ok") else str(last_scan.get("eventType") or "review")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self.insert_audit(
                con,
                "line_item",
                candidate["lineItemId"],
                "cross_date_scan_switch",
                user,
                station,
                "",
                {
                    "operation": operation,
                    "automatic": bool(resolved.get("automatic")),
                    "originalListId": original["listId"],
                    "originalDeliveryDate": original["deliveryDate"],
                    "originalStage": original["stage"],
                    "matchedListId": candidate["listId"],
                    "matchedDeliveryDate": candidate["deliveryDate"],
                    "matchedStage": candidate["stage"],
                    "order": candidate["order"],
                    "item": candidate["item"],
                    "rackCode": candidate.get("originalRackCode", ""),
                    "bayCode": candidate.get("originalBayCode", ""),
                    "outcome": outcome,
                },
            )
            con.commit()
        payload.update(
            {
                "crossDateSwitched": True,
                "crossDateAutomatic": bool(resolved.get("automatic")),
                "originalListId": original["listId"],
                "originalDeliveryDate": original["deliveryDate"],
                "originalStage": original["stage"],
                "matchedListId": candidate["listId"],
                "matchedDeliveryDate": candidate["deliveryDate"],
                "matchedStage": candidate["stage"],
                "crossDateRackPreserved": bool(candidate.get("rackPreserved")),
                "crossDateBayPreserved": bool(candidate.get("bayPreserved")),
                "crossDateClearRack": bool(candidate.get("clearRack")),
                "originalRackCode": candidate.get("originalRackCode", ""),
                "originalBayCode": candidate.get("originalBayCode", ""),
                "crossDateSafetyReason": candidate.get("safetyReason", ""),
                "crossDateMessage": (
                    f"Delivery date changed from {format_display_date(original['deliveryDate'])} "
                    f"to {format_display_date(candidate['deliveryDate'])} for Order {candidate['order']} / Item {candidate['item']}."
                ),
            }
        )
        return payload

    def scan_other_list_hint(
        self,
        con: sqlite3.Connection,
        current_list_id: str,
        raw_scan: str,
        *,
        strict_order_item: bool = False,
    ) -> tuple[str, str]:
        """Purpose: Process other list hint for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        list_rows = con.execute(
            """
            SELECT id, label, delivery_date, stage, scanner
            FROM delivery_lists
            WHERE id <> ? AND status = 'active'
            ORDER BY delivery_date DESC, stage, id
            """,
            (current_list_id,),
        ).fetchall()
        matches: list[tuple[sqlite3.Row, sqlite3.Row, str]] = []
        for list_row in list_rows:
            rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_row["id"],)).fetchall()
            if not rows:
                continue
            matched_row, canonical, _reason = self.recover_scan(
                raw_scan,
                rows,
                strict_order_item=strict_order_item,
            )
            if matched_row is not None:
                matches.append((list_row, matched_row, canonical))
                if len(matches) >= 12:
                    break

        if matches:
            # The same item normally appears in several stages for one delivery
            # date. Keep the scanner guidance focused on that date instead of
            # dumping every matching stage into a floor-facing error message.
            dates = []
            for list_row, _matched_row, _canonical in matches:
                delivery_date = str(list_row["delivery_date"] or "").strip()
                if delivery_date and delivery_date not in dates:
                    dates.append(delivery_date)
            primary_list, primary_item, primary_canonical = matches[0]
            primary_date = dates[0] if dates else str(primary_list["delivery_date"] or "").strip()
            display_date = format_display_date(primary_date) if primary_date else "another date"
            if len(dates) <= 1:
                reason = (
                    f"Order {primary_item['order_no']} / Item {primary_item['item_no']} is not on this delivery list. "
                    f"Check delivery list date {display_date}."
                )
            else:
                date_list = ", ".join(format_display_date(value) for value in dates[:3])
                reason = (
                    f"Order {primary_item['order_no']} / Item {primary_item['item_no']} is not on this delivery list. "
                    f"Check delivery list date {date_list}."
                )
            return primary_canonical, reason

        return clean_barcode(raw_scan), (
            "This item is not on the selected delivery list. Check the delivery list date for the scanned item."
        )

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
        """Purpose: Create event for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Create exception for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Create audit for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        con.execute(
            """
            INSERT INTO audit_events (entity_type, entity_id, action, user_name, station, reason, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (entity_type, entity_id, action, user, station, reason, json.dumps(payload or {}, separators=(",", ":")), now_iso()),
        )

    def record_scan(self, scan_request: dict[str, Any]) -> dict[str, Any]:
        """Resolve cross-date matches before running the maintained scan workflow."""
        resolved = self.resolve_cross_date_scan(scan_request)
        if resolved and resolved.get("selection"):
            return resolved["selection"]
        effective_request = dict(scan_request)
        if resolved and resolved.get("candidate"):
            effective_request["listId"] = resolved["candidate"]["listId"]
            effective_request["_crossDateResolved"] = True
            if resolved["candidate"].get("clearRack"):
                effective_request["rackCode"] = ""
        payload = self._record_scan_for_list(effective_request)
        if resolved and resolved.get("candidate"):
            return self.attach_cross_date_result(payload, resolved, effective_request, "scan")
        return payload

    def _record_scan_for_list(self, scan_request: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Process scan for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        list_id = str(scan_request.get("listId") or "")
        barcode = str(scan_request.get("barcode") or "")
        user = request_user_name(scan_request)
        station = request_station(scan_request)
        is_manual = str(scan_request.get("isManual") or "").lower() in {"1", "true", "yes"}
        if not list_id or not barcode.strip():
            raise ValueError("listId and barcode are required")
        rack_code, _rack_delivery_date = parse_rack_barcode(barcode)
        if rack_code:
            return self.scan_rack_outbound(scan_request, rack_code)

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall()
            row, canonical, reason = self.recover_scan(
                barcode,
                rows,
                strict_order_item=is_manual,
            )
            if row is None:
                if reason in {"No unique delivery-list match", "No exact order/item match"}:
                    canonical, reason = self.scan_other_list_hint(
                        con,
                        list_id,
                        barcode,
                        strict_order_item=is_manual,
                    )
                    message = "Item is not on this delivery list"
                elif reason == "Ambiguous delivery-list match":
                    message = "Multiple items match this scan"
                    reason = "The scan matched more than one item on this delivery list. Use the full barcode or enter the order and item manually."
                else:
                    message = "Unable to match this scan"
                last = self.insert_event(con, list_id, None, barcode, canonical, user, station, "error", message, reason)
                self.insert_audit(con, "scan", list_id, "scan_error", user, station, reason, {"barcode": barcode, "canonical": canonical, "message": message})
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

            outbound_gate_payload = self.outbound_scan_gate(con, list_id, row, barcode, canonical, user, station, scan_request)
            if outbound_gate_payload is not None:
                con.commit()
                return outbound_gate_payload

            rack_code_for_scan = normalize_rack_code(str(scan_request.get("rackCode") or ""))
            destination_override_requested = str(scan_request.get("destinationOverride") or "").lower() in {"1", "true", "yes"}
            list_row_for_rack = con.execute("SELECT stage FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            rack_for_scan = None
            destination_override = ""
            override_active = False
            override_until = ""
            override_minutes = self.rack_destination_override_minutes_con(con)
            if rack_code_for_scan and list_row_for_rack and "staging" in str(list_row_for_rack["stage"]).lower():
                rack_for_scan = self.get_rack_by_code(con, rack_code_for_scan)
                if str(rack_for_scan["status"] or "").lower() == "closed":
                    last = self.insert_event(
                        con,
                        list_id,
                        row["id"],
                        barcode,
                        canonical,
                        user,
                        station,
                        "error",
                        f"Rack {rack_for_scan['rack_code']} is closed",
                        "Uncomplete or clear this rack before scanning more pieces into it.",
                    )
                    con.commit()
                    payload = self._get_payload(con, list_id, last)
                    racks_payload = self.get_racks()
                    payload["racks"] = racks_payload.get("racks", [])
                    payload["rackSummary"] = racks_payload.get("summary")
                    return payload

                item_destination = self.destination_for_line_item(row)
                rack_destinations = self.rack_destinations_from_items(con, int(rack_for_scan["id"]))
                rack_destination = rack_destinations[0] if len(rack_destinations) == 1 else self.rack_destination_value(rack_for_scan["destination"])
                mismatch = bool(rack_destinations and rack_destinations != [item_destination])
                override_active, override_until, override_minutes = self.apply_rack_destination_override_window(
                    con,
                    rack_for_scan,
                    mismatch=mismatch,
                    override_requested=destination_override_requested,
                    rack_destination=rack_destination,
                    item_destination=item_destination,
                    user=user,
                    station=station,
                )
                if mismatch and not destination_override_requested and not override_active:
                    reason_text = (
                        f"Rack {rack_for_scan['rack_code']} is assigned to {rack_destination}. "
                        f"This item is marked for {item_destination}."
                    )
                    last = self.insert_event(
                        con,
                        list_id,
                        row["id"],
                        barcode,
                        canonical,
                        user,
                        station,
                        "notice",
                        "Rack destination mismatch",
                        reason_text,
                    )
                    con.commit()
                    payload = self._get_payload(con, list_id, last)
                    racks_payload = self.get_racks()
                    payload["racks"] = racks_payload.get("racks", [])
                    payload["rackSummary"] = racks_payload.get("summary")
                    payload.update(
                        {
                            "destinationOverrideRequired": True,
                            "destinationOverrideMinutes": override_minutes,
                            "destinationMismatch": {
                                "rackCode": rack_for_scan["rack_code"],
                                "rackDestination": rack_destination,
                                "itemDestination": item_destination,
                                "order": row["order_no"],
                                "item": row["item_no"],
                                "customer": row["customer"],
                            },
                        }
                    )
                    return payload
                if mismatch:
                    destination_override = rack_destination

            con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
            if rack_for_scan:
                con.execute(
                    """
                    INSERT INTO rack_items (
                        rack_id, line_item_id, qty, status, added_by, added_at,
                        reason, destination_override
                    )
                    VALUES (?, ?, 1, 'Active', ?, ?, ?, ?)
                    ON CONFLICT(rack_id, line_item_id) DO UPDATE SET
                        qty = CASE
                            WHEN rack_items.status = 'Active' THEN MIN(rack_items.qty + 1, (SELECT qty FROM line_items WHERE id = excluded.line_item_id))
                            ELSE excluded.qty
                        END,
                        status = 'Active',
                        removed_by = '',
                        removed_at = '',
                        reason = excluded.reason,
                        destination_override = excluded.destination_override,
                        added_by = excluded.added_by,
                        added_at = excluded.added_at
                    """,
                    (
                        rack_for_scan["id"],
                        row["id"],
                        user,
                        now_iso(),
                        "Scanned on staging with destination override" if destination_override else "Scanned on staging",
                        destination_override,
                    ),
                )
                self.refresh_rack_destination(con, rack_for_scan["id"])
            preassigned_bay = self.preassign_bay_for_outbound(con, list_id, row, user, station)
            last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "manual_scan" if is_manual else "scan", reason, "", 1)
            if preassigned_bay:
                self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "notice", "Indian Trail bay preassigned", f"Preassigned to Bay {preassigned_bay}")
            self.insert_audit(
                con,
                "line_item",
                row["id"],
                "manual_scan" if is_manual else "scan",
                user,
                station,
                reason,
                {"barcode": barcode, "canonical": canonical, "manual": is_manual},
            )
            self.queue_ready_email_if_customer_complete(con, list_id, row, user)
            con.commit()
            payload = self._get_payload(con, list_id, last)
            if rack_code_for_scan:
                racks_payload = self.get_racks()
                payload["racks"] = racks_payload.get("racks", [])
                payload["rackSummary"] = racks_payload.get("summary")
                payload["destinationOverrideActive"] = bool(destination_override and override_active)
                payload["destinationOverrideUntil"] = override_until if destination_override and override_active else ""
                payload["destinationOverrideMinutes"] = override_minutes
            return payload

    def matching_staging_row_for_outbound(self, con: sqlite3.Connection, current_list: sqlite3.Row, outbound_row: sqlite3.Row) -> sqlite3.Row | None:
        """Purpose: Run the matching staging row for outbound workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
            (current_list["delivery_date"], current_list["scanner"], current_list["id"]),
        ).fetchone()
        if not staging_list:
            return None
        return con.execute(
            """
            SELECT * FROM line_items
            WHERE list_id = ?
              AND (source_id = ? OR (order_no = ? AND item_no = ?))
            ORDER BY id
            LIMIT 1
            """,
            (staging_list["id"], outbound_row["source_id"], outbound_row["order_no"], outbound_row["item_no"]),
        ).fetchone()

    def transportation_for_staging_row(self, con: sqlite3.Connection, staging_line_item_id: str) -> sqlite3.Row | None:
        """Purpose: Run the transportation for staging row workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return con.execute(
            """
            SELECT r.*
            FROM rack_items ri
            JOIN racks r ON r.id = ri.rack_id
            WHERE ri.line_item_id = ?
              AND ri.status = 'Active'
              AND r.active = 1
            ORDER BY CASE WHEN r.rack_code = 'T' THEN 0 ELSE 1 END, r.sort_order, r.rack_code
            LIMIT 1
            """,
            (staging_line_item_id,),
        ).fetchone()

    def assign_transportation_from_outbound_override(
        self,
        con: sqlite3.Connection,
        staging_row: sqlite3.Row,
        rack_code: str,
        user: str,
        station: str,
    ) -> str:
        """Purpose: Run the assign transportation from outbound override workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        clean_rack_code = normalize_rack_code(rack_code)
        if not clean_rack_code:
            raise ValueError("Choose a transportation method before overriding outbound scan safety.")
        rack = self.get_rack_by_code(con, clean_rack_code)
        if str(rack["status"] or "").lower() in {"closed", "complete", "completed", "in transit"}:
            raise ValueError(f"Rack {rack['rack_code']} is {rack['status']}. Choose an open rack or the truck before overriding outbound scan safety.")
        con.execute(
            """
            INSERT INTO rack_items (rack_id, line_item_id, qty, status, added_by, added_at, reason)
            VALUES (?, ?, 1, 'Active', ?, ?, 'Outbound override transportation assignment')
            ON CONFLICT(rack_id, line_item_id) DO UPDATE SET
                qty = CASE
                    WHEN rack_items.status = 'Active' THEN MAX(rack_items.qty, 1)
                    ELSE excluded.qty
                END,
                status = 'Active',
                removed_by = '',
                removed_at = '',
                reason = 'Outbound override transportation assignment',
                added_by = excluded.added_by,
                added_at = excluded.added_at
            """,
            (rack["id"], staging_row["id"], user, now_iso()),
        )
        self.insert_audit(
            con,
            "rack_item",
            staging_row["id"],
            "outbound_override_transportation",
            user,
            station,
            "Transportation method selected during outbound safety override.",
            {"rackCode": rack["rack_code"], "order": staging_row["order_no"], "item": staging_row["item_no"]},
        )
        return str(rack["rack_code"])

    def outbound_scan_gate(
        self,
        con: sqlite3.Connection,
        list_id: str,
        outbound_row: sqlite3.Row,
        barcode: str,
        canonical: str,
        user: str,
        station: str,
        scan_request: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Enforce outbound safety before a piece is scanned out.

        Outbound scans should not silently auto-stage pieces anymore. The floor
        gets a clear popup in the UI when staging was skipped or no rack/truck
        transportation method exists. Supervisors can override from that popup
        and choose the transportation method at the same time.
        """
        current_list = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
        if not current_list or "outbound" not in str(current_list["stage"]).lower():
            return None

        staging_row = self.matching_staging_row_for_outbound(con, current_list, outbound_row)
        staging_scanned = bool(staging_row and int(staging_row["scanned_qty"] or 0) > 0)
        transportation = self.transportation_for_staging_row(con, staging_row["id"]) if staging_row else None
        has_transportation = transportation is not None
        override_requested = str(scan_request.get("outboundOverride") or "").lower() in {"1", "true", "yes"}
        requested_rack_code = normalize_rack_code(str(scan_request.get("rackCode") or ""))

        needs_staging = not staging_scanned
        needs_transportation = not has_transportation
        if not needs_staging and not needs_transportation:
            return None

        if not override_requested:
            if needs_staging and needs_transportation:
                message = "Staging scan and transportation method required"
                reason = "This piece has not been scanned on staging and has no rack/truck assigned."
            elif needs_staging:
                message = "Staging scan required before outbound"
                reason = "This piece has not been scanned on staging."
            else:
                message = "Transportation method required"
                reason = "This piece was staged but has no rack/truck assigned."
            last = self.insert_event(con, list_id, outbound_row["id"], barcode, canonical, user, station, "error", message, reason)
            self.insert_audit(
                con,
                "line_item",
                outbound_row["id"],
                "outbound_scan_blocked",
                user,
                station,
                reason,
                {"barcode": barcode, "canonical": canonical, "needsStaging": needs_staging, "needsTransportation": needs_transportation},
            )
            payload = self._get_payload(con, list_id, last)
            payload.update(
                {
                    "outboundOverrideRequired": True,
                    "outboundOverrideReason": reason,
                    "outboundOverrideMessage": message,
                    "outboundNeedsStaging": needs_staging,
                    "outboundNeedsTransportation": needs_transportation,
                    "outboundItem": {
                        "order": outbound_row["order_no"],
                        "item": outbound_row["item_no"],
                        "customer": outbound_row["customer"],
                        "dimensions": outbound_row["dimensions"],
                    },
                }
            )
            return payload

        if needs_transportation and not requested_rack_code:
            last = self.insert_event(
                con,
                list_id,
                outbound_row["id"],
                barcode,
                canonical,
                user,
                station,
                "error",
                "Choose transportation method",
                "Outbound override requires a rack or truck assignment.",
            )
            payload = self._get_payload(con, list_id, last)
            payload.update({"outboundOverrideRequired": True, "outboundNeedsTransportation": True, "outboundOverrideMessage": "Choose transportation method"})
            return payload

        if requested_rack_code:
            requested_rack = self.get_rack_by_code(con, requested_rack_code)
            if str(requested_rack["status"] or "").lower() in {"closed", "complete", "completed", "in transit"}:
                reason = f"Rack {requested_rack['rack_code']} is {requested_rack['status']} and cannot accept outbound override pieces."
                last = self.insert_event(
                    con,
                    list_id,
                    outbound_row["id"],
                    barcode,
                    canonical,
                    user,
                    station,
                    "error",
                    "Choose an open rack or truck",
                    reason,
                )
                payload = self._get_payload(con, list_id, last)
                payload.update(
                    {
                        "outboundOverrideRequired": True,
                        "outboundOverrideReason": reason,
                        "outboundOverrideMessage": "Choose an open rack or truck",
                        "outboundNeedsStaging": needs_staging,
                        "outboundNeedsTransportation": True,
                        "outboundItem": {
                            "order": outbound_row["order_no"],
                            "item": outbound_row["item_no"],
                            "customer": outbound_row["customer"],
                            "dimensions": outbound_row["dimensions"],
                        },
                    }
                )
                return payload

        if needs_staging and staging_row:
            self.auto_stage_for_outbound(con, list_id, outbound_row, barcode, canonical, user, station)
        if staging_row and requested_rack_code and needs_transportation:
            assigned_code = self.assign_transportation_from_outbound_override(con, staging_row, requested_rack_code, user, station)
        else:
            assigned_code = str(transportation["rack_code"] if transportation else requested_rack_code)
        self.insert_audit(
            con,
            "line_item",
            outbound_row["id"],
            "outbound_scan_override",
            user,
            station,
            "Outbound safety warning was overridden.",
            {
                "barcode": barcode,
                "canonical": canonical,
                "needsStaging": needs_staging,
                "needsTransportation": needs_transportation,
                "rackCode": assigned_code,
            },
        )
        return None

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
        """Purpose: Run the auto stage for outbound workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Purpose: Run the preassign bay for outbound workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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

        # Indian Trail bay assignment is job-based. One Job Nr. may contain multiple line items;
        # every item in that job should live in one physical bay so the floor can pull the whole job together.
        job_key = str(inbound["job"] or "").strip()
        if job_key:
            group_rows = con.execute(
                """
                SELECT * FROM line_items
                WHERE list_id = ? AND COALESCE(job, '') = ?
                ORDER BY order_no, item_no, id
                """,
                (inbound["list_id"], job_key),
            ).fetchall()
        else:
            group_rows = con.execute(
                """
                SELECT * FROM line_items
                WHERE list_id = ? AND order_no = ?
                ORDER BY order_no, item_no, id
                """,
                (inbound["list_id"], inbound["order_no"]),
            ).fetchall()
        group_rows = group_rows or [inbound]
        group_ids = [row["id"] for row in group_rows]
        placeholders = ",".join("?" for _ in group_ids)

        existing = con.execute(
            f"""
            SELECT ba.*, b.bay_code
            FROM bay_assignments ba
            JOIN bays b ON b.id = ba.bay_id
            WHERE ba.status NOT IN ('Cleared', 'Cancelled')
              AND ba.line_item_id IN ({placeholders})
            ORDER BY ba.id DESC
            LIMIT 1
            """,
            group_ids,
        ).fetchone()
        if existing:
            bay = con.execute("SELECT * FROM bays WHERE id = ?", (existing["bay_id"],)).fetchone()
        else:
            bay_type = self.suggested_bay_from_settings(con, inbound["product"], inbound["dimensions"], inbound["route"])
            if self.bay_type_requires_manual_assignment(con, bay_type):
                self.insert_exception(con, inbound["list_id"], None, "manual_bay_assignment_required", f"{bay_type} is configured for manual bay assignment")
                return ""
            bay = self.find_bay_for_assignment(con, bay_type) or self.find_bay_for_assignment(con, "Standard")
        if not bay:
            self.insert_exception(con, inbound["list_id"], None, "bay_assignment_conflict", "No safe bay available during outbound job preassign")
            return ""

        assigned_count = 0
        for group_row in group_rows:
            active = con.execute(
                "SELECT 1 FROM bay_assignments WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled') LIMIT 1",
                (group_row["id"],),
            ).fetchone()
            if active:
                continue
            con.execute(
                """
                INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
                VALUES (?, ?, ?, ?, 'PreAssigned', ?, ?, 'Job preassigned from outbound scan')
                """,
                (inbound["list_id"], group_row["id"], bay["id"], int(group_row["qty"] or 1), user, now_iso()),
            )
            self.insert_bay_event(con, bay["id"], group_row["id"], "PreAssignBay", user, "Job preassigned from outbound scan", new_bay_id=bay["id"])
            assigned_count += 1
        self.insert_audit(con, "bay_assignment", inbound["id"], "preassign_job_bay_from_outbound", user, station, "", {"bayCode": bay["bay_code"], "job": job_key, "itemsAssigned": assigned_count})
        return str(bay["bay_code"])

    def reset_stage(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        """Purpose: Run the reset stage workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE line_items SET scanned_qty = 0 WHERE list_id = ?", (list_id,))
            con.execute(
                """
                UPDATE rack_items
                SET status = 'Removed',
                    removed_by = ?,
                    removed_at = ?,
                    reason = 'Removed by delivery-list scan reset'
                WHERE status = 'Active'
                  AND line_item_id IN (SELECT id FROM line_items WHERE list_id = ?)
                """,
                (user, now_iso(), list_id),
            )
            last = self.insert_event(con, list_id, None, "RESET", "", user, station, "reset", "Scan state reset")
            self.insert_audit(con, "delivery_list", list_id, "reset_scans", user, station, "Scan state and rack assignments reset")
            con.commit()
            return self._get_payload(con, list_id, last)

    def undo_last_scan(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        """Purpose: Undo last scan for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute(
                """
                SELECT *
                FROM scan_events
                WHERE list_id = ?
                  AND event_type IN ('scan', 'manual_scan', 'undo', 'redo')
                  AND line_item_id IS NOT NULL
                  AND qty_delta <> 0
                ORDER BY id
                """,
                (list_id,),
            ).fetchall()

            # Replay the append-only event stream so an older positive event
            # cannot be undone repeatedly. Legacy quantity-one undo events can
            # also partially consume newer multi-piece scan events safely.
            active_events: list[dict[str, Any]] = []
            for event_row in rows:
                event_type = str(event_row["event_type"] or "").lower()
                delta = int(event_row["qty_delta"] or 0)
                if event_type in {"scan", "manual_scan", "redo"} and delta > 0:
                    active_events.append({"row": event_row, "remaining": delta})
                    continue
                if event_type != "undo" or delta >= 0:
                    continue
                quantity_to_reverse = abs(delta)
                for active in reversed(active_events):
                    if quantity_to_reverse <= 0:
                        break
                    available = int(active["remaining"] or 0)
                    if available <= 0:
                        continue
                    consumed = min(available, quantity_to_reverse)
                    active["remaining"] = available - consumed
                    quantity_to_reverse -= consumed

            candidate = next((active for active in reversed(active_events) if int(active["remaining"] or 0) > 0), None)
            if not candidate:
                last = self.insert_event(con, list_id, None, "UNDO", "", user, station, "error", "Nothing to undo")
                con.commit()
                return self._get_payload(con, list_id, last)

            row = candidate["row"]
            item_row = con.execute(
                """
                SELECT li.*, dl.stage
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE li.id = ?
                """,
                (row["line_item_id"],),
            ).fetchone()
            current_scanned = int(item_row["scanned_qty"] or 0) if item_row else 0
            decrement = min(int(candidate["remaining"] or 0), current_scanned)
            if decrement <= 0:
                last = self.insert_event(con, list_id, None, "UNDO", "", user, station, "error", "Nothing to undo")
                con.commit()
                return self._get_payload(con, list_id, last)

            rack_allocations: list[dict[str, Any]] = []
            if item_row and "staging" in str(item_row["stage"] or "").lower():
                rack_rows = con.execute(
                    """
                    SELECT ri.*, r.rack_code, r.status AS rack_status
                    FROM rack_items ri
                    JOIN racks r ON r.id = ri.rack_id
                    WHERE ri.line_item_id = ? AND ri.status = 'Active' AND ri.qty > 0
                    ORDER BY ri.added_at DESC, ri.id DESC
                    """,
                    (row["line_item_id"],),
                ).fetchall()
                locked = next(
                    (
                        rack_row for rack_row in rack_rows
                        if str(rack_row["rack_status"] or "").lower()
                        in {"closed", "complete", "completed", "in transit", "on the way"}
                    ),
                    None,
                )
                if locked:
                    last = self.insert_event(
                        con,
                        list_id,
                        row["line_item_id"],
                        row["barcode"],
                        row["canonical_barcode"],
                        user,
                        station,
                        "error",
                        "Undo blocked",
                        f"Rack {locked['rack_code']} must be reopened before undoing this staging scan.",
                    )
                    con.commit()
                    return self._get_payload(con, list_id, last)

                remaining_rack_qty = decrement
                for rack_row in rack_rows:
                    if remaining_rack_qty <= 0:
                        break
                    rack_qty = int(rack_row["qty"] or 0)
                    removed_qty = min(rack_qty, remaining_rack_qty)
                    if removed_qty <= 0:
                        continue
                    new_qty = rack_qty - removed_qty
                    con.execute(
                        """
                        UPDATE rack_items
                        SET qty = ?, status = ?, removed_by = ?, removed_at = ?, reason = ?
                        WHERE id = ?
                        """,
                        (
                            new_qty if new_qty > 0 else rack_qty,
                            "Active" if new_qty > 0 else "Removed",
                            "" if new_qty > 0 else user,
                            "" if new_qty > 0 else now_iso(),
                            "Quantity reduced by scan undo",
                            rack_row["id"],
                        ),
                    )
                    self.refresh_rack_destination(con, int(rack_row["rack_id"]))
                    rack_allocations.append({"rackCode": str(rack_row["rack_code"]), "qty": removed_qty})
                    remaining_rack_qty -= removed_qty

            con.execute(
                "UPDATE line_items SET scanned_qty = MAX(scanned_qty - ?, 0) WHERE id = ?",
                (decrement, row["line_item_id"]),
            )
            undo_metadata = json.dumps(
                {"sourceEventId": int(row["id"]), "rackAllocations": rack_allocations},
                separators=(",", ":"),
            )
            last = self.insert_event(
                con,
                list_id,
                row["line_item_id"],
                row["barcode"],
                row["canonical_barcode"],
                user,
                station,
                "undo",
                f"Last scan undone ({decrement} piece{'s' if decrement != 1 else ''})",
                f"UNDO_META:{undo_metadata}",
                -decrement,
            )
            self.insert_audit(
                con,
                "line_item",
                row["line_item_id"],
                "undo_scan",
                user,
                station,
                "Last scan undone",
                {"sourceEventId": int(row["id"]), "qty": decrement, "rackAllocations": rack_allocations},
            )
            con.commit()
            return self._get_payload(con, list_id, last)

    def redo_last_undo(self, list_id: str, user: str, station: str) -> dict[str, Any]:
        """Purpose: Redo last undo for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                """
                SELECT se.*, li.qty, li.scanned_qty
                FROM scan_events se
                JOIN line_items li ON li.id = se.line_item_id
                WHERE se.list_id = ?
                  AND se.event_type IN ('undo', 'scan', 'manual_scan', 'redo')
                  AND se.line_item_id IS NOT NULL
                ORDER BY se.id DESC
                LIMIT 1
                """,
                (list_id,),
            ).fetchone()
            if not row or row["event_type"] != "undo":
                last = self.insert_event(con, list_id, None, "REDO", "", user, station, "error", "Nothing to redo")
                con.commit()
                return self._get_payload(con, list_id, last)
            remaining_qty = max(int(row["qty"] or 0) - int(row["scanned_qty"] or 0), 0)
            increment = min(abs(int(row["qty_delta"] or -1)), remaining_qty)
            if increment <= 0:
                last = self.insert_event(con, list_id, row["line_item_id"], row["barcode"], row["canonical_barcode"], user, station, "duplicate", "Redo blocked", "Quantity already scanned")
                con.commit()
                return self._get_payload(con, list_id, last)

            rack_allocations: list[dict[str, Any]] = []
            reason = str(row["reason"] or "")
            if reason.startswith("UNDO_META:"):
                try:
                    rack_allocations = list(json.loads(reason[len("UNDO_META:"):]).get("rackAllocations") or [])
                except (TypeError, ValueError, json.JSONDecodeError):
                    rack_allocations = []
            restored_qty = 0
            for allocation in rack_allocations:
                if restored_qty >= increment:
                    break
                rack_code = normalize_rack_code(str(allocation.get("rackCode") or ""))
                allocation_qty = min(max(int(allocation.get("qty") or 0), 0), increment - restored_qty)
                if not rack_code or allocation_qty <= 0:
                    continue
                rack = self.get_rack_by_code(con, rack_code)
                rack_status = str(rack["status"] or "").lower()
                if rack_status in {"closed", "complete", "completed", "in transit", "on the way"}:
                    last = self.insert_event(
                        con,
                        list_id,
                        row["line_item_id"],
                        row["barcode"],
                        row["canonical_barcode"],
                        user,
                        station,
                        "error",
                        "Redo blocked",
                        f"Rack {rack_code} must be reopened before redoing this staging scan.",
                    )
                    con.commit()
                    return self._get_payload(con, list_id, last)
                con.execute(
                    """
                    INSERT INTO rack_items (rack_id, line_item_id, qty, status, added_by, added_at, reason)
                    VALUES (?, ?, ?, 'Active', ?, ?, 'Restored by scan redo')
                    ON CONFLICT(rack_id, line_item_id) DO UPDATE SET
                        qty = CASE
                            WHEN rack_items.status = 'Active' THEN rack_items.qty + excluded.qty
                            ELSE excluded.qty
                        END,
                        status = 'Active',
                        removed_by = '',
                        removed_at = '',
                        reason = 'Restored by scan redo'
                    """,
                    (rack["id"], row["line_item_id"], allocation_qty, user, now_iso()),
                )
                self.refresh_rack_destination(con, int(rack["id"]))
                restored_qty += allocation_qty

            con.execute("UPDATE line_items SET scanned_qty = scanned_qty + ? WHERE id = ?", (increment, row["line_item_id"]))
            last = self.insert_event(
                con,
                list_id,
                row["line_item_id"],
                row["barcode"],
                row["canonical_barcode"],
                user,
                station,
                "redo",
                f"Undo redone ({increment} piece{'s' if increment != 1 else ''})",
                "Last undo was re-applied",
                increment,
            )
            self.insert_audit(
                con,
                "line_item",
                row["line_item_id"],
                "redo_scan",
                user,
                station,
                "Last undo was re-applied",
                {"qty": increment, "rackAllocations": rack_allocations},
            )
            con.commit()
            return self._get_payload(con, list_id, last)

    def get_exceptions(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Purpose: Read exceptions for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
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
        """Purpose: Run the preview import workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Purpose: Run the admin summary workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        with self.connect() as con:
            list_count = con.execute(
                "SELECT COUNT(*) FROM delivery_lists dl WHERE dl.status = 'active' AND EXISTS (SELECT 1 FROM line_items li WHERE li.list_id = dl.id)"
            ).fetchone()[0]
            date_count = con.execute(
                "SELECT COUNT(DISTINCT dl.delivery_date) FROM delivery_lists dl WHERE dl.status = 'active' AND EXISTS (SELECT 1 FROM line_items li WHERE li.list_id = dl.id)"
            ).fetchone()[0]
            item_count = con.execute("SELECT COUNT(*) FROM line_items").fetchone()[0]
            today = datetime.now().date().isoformat()
            scan_count = con.execute("SELECT COUNT(*) FROM scan_events WHERE event_type = 'scan' AND substr(created_at, 1, 10) = ?", (today,)).fetchone()[0]
            open_exceptions = con.execute("SELECT COUNT(*) FROM exceptions WHERE status = 'Open'").fetchone()[0]
            user_count = con.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE expires_at > ?", (now_iso(),)).fetchone()[0]
            assigned_station_count = con.execute(
                "SELECT COUNT(DISTINCT station) FROM users WHERE active = 1 AND station <> ''"
            ).fetchone()[0]
            bay_count = con.execute("SELECT COUNT(*) FROM bays WHERE active = 1").fetchone()[0]
            import_rows = con.execute(
                "SELECT * FROM imports ORDER BY id DESC LIMIT 50"
            ).fetchall()
            recent_imports: list[dict[str, Any]] = []
            for row in import_rows:
                try:
                    change_summary = json.loads(row["change_summary"] or "{}")
                except Exception:
                    change_summary = {}
                stage_summaries = change_summary.get("stages") if isinstance(change_summary, dict) else []
                changed_list_ids = change_summary.get("changedListIds") if isinstance(change_summary, dict) else []

                # Normalize historical import summaries created by older builds.
                # Some no-change rows stored originalQty=0 even though totalQty
                # already contained the stage's existing pieces. That made an
                # unchanged DTC stage look like 0 -> 10 with no recorded change.
                normalized_stage_summaries: list[dict[str, Any]] = []
                for stage_summary in stage_summaries if isinstance(stage_summaries, list) else []:
                    if not isinstance(stage_summary, dict):
                        continue
                    normalized = dict(stage_summary)
                    total_qty = int(normalized.get("totalQty") or normalized.get("updatedQty") or 0)
                    original_qty = int(normalized.get("originalQty") or 0)
                    added_qty = int(normalized.get("addedPieceQty") or 0)
                    changed_qty = int(normalized.get("changedPieceQty") or 0)
                    changed_lines = int(normalized.get("changedLineCount") or 0)
                    created_stage = bool(normalized.get("created"))

                    if not created_stage and original_qty <= 0 and total_qty > 0:
                        if not added_qty and not changed_qty and not changed_lines:
                            normalized["originalQty"] = total_qty
                        elif added_qty > 0:
                            normalized["originalQty"] = max(total_qty - added_qty, 0)

                    normalized_stage_summaries.append(normalized)

                recent_imports.append(
                    {
                        "id": row["id"],
                        "batchId": row["id"],
                        "deliveryDate": row["delivery_date"],
                        "sourceName": row["source_name"],
                        "sourcePath": row["source_path"],
                        "importKind": row["import_kind"],
                        "rowCount": row["row_count"],
                        "totalQty": row["total_qty"],
                        "importedBy": row["imported_by"],
                        "importedAt": row["imported_at"],
                        "createdCount": change_summary.get("createdCount", 0) if isinstance(change_summary, dict) else 0,
                        "updatedCount": change_summary.get("updatedCount", 0) if isinstance(change_summary, dict) else 0,
                        "addedPieceQty": change_summary.get("addedPieceQty", 0) if isinstance(change_summary, dict) else 0,
                        "changedPieceQty": change_summary.get("changedPieceQty", 0) if isinstance(change_summary, dict) else 0,
                        "stageSummaries": normalized_stage_summaries,
                        "listIds": changed_list_ids if isinstance(changed_list_ids, list) and changed_list_ids else [f"{row['delivery_date']}-{suffix}" for suffix, _, _, _ in LIST_PROFILES],
                    }
                )
        return {
            "activeDeliveryLists": list_count,
            "activeDeliveryDates": date_count,
            "lineItems": item_count,
            "scanEventsToday": scan_count,
            "scanEvents": scan_count,
            "openExceptions": open_exceptions,
            "activeUsers": user_count,
            "assignedStations": assigned_station_count,
            "activeBays": bay_count,
            "databaseType": self.database_type,
            "databasePath": str(self.database_path),
            "tempDeliveryListsDir": str(self.config.temp_delivery_lists_dir),
            "authMode": self.config.auth_mode,
            "environment": self.config.environment,
            "recentImports": recent_imports,
        }

    def resolve_exception(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Resolve exception for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
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
        """Purpose: Run the global search workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
                       r.rack_code,
                       r.display_name AS rack_display_name,
                       r.rack_type AS rack_type,
                       r.status AS rack_status,
                       (
                           SELECT se.created_at
                           FROM scan_events se
                           WHERE se.line_item_id = li.id
                             AND se.event_type IN ('scan', 'manual_scan', 'redo')
                             AND se.qty_delta > 0
                           ORDER BY se.id DESC
                           LIMIT 1
                       ) AS last_scan_time,
                       (
                           SELECT se.user_name
                           FROM scan_events se
                           WHERE se.line_item_id = li.id
                             AND se.event_type IN ('scan', 'manual_scan', 'redo')
                             AND se.qty_delta > 0
                           ORDER BY se.id DESC
                           LIMIT 1
                       ) AS last_scan_user
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id AND ba.status NOT IN ('Cleared', 'Cancelled')
                LEFT JOIN bays b ON b.id = ba.bay_id
                LEFT JOIN rack_items ri ON ri.line_item_id = li.id AND ri.status = 'Active'
                LEFT JOIN racks r ON r.id = ri.rack_id AND r.active = 1
                WHERE li.order_no LIKE ? OR li.item_no LIKE ? OR li.source_id LIKE ? OR li.barcode LIKE ?
                   OR li.customer LIKE ? OR li.job LIKE ? OR li.route LIKE ?
                   OR li.product LIKE ? OR li.dimensions LIKE ? OR dl.stage LIKE ?
                   OR b.bay_code LIKE ? OR b.display_name LIKE ?
                ORDER BY dl.delivery_date DESC, CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER)
                LIMIT 160
                """,
                (like, like, like, like, like, like, like, like, like, like, like, like),
            ).fetchall()

        def stage_kind(row: sqlite3.Row) -> str:
            """Purpose: Run the stage kind workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            text = f"{row['stage']} {row['scanner']}".lower()
            if "outbound" in text:
                return "outbound"
            if "indian trail" in text or "inbound" in text:
                return "indian_trail"
            if "customer pickup" in text or "cpu" in text:
                return "cpu"
            if "greenville" in text or "gnv" in text:
                return "greenville"
            if "dtc" in text or "deliver to customer" in text:
                return "dtc"
            if "staging" in text:
                return "staging"
            return "other"

        def representative_rank(row: sqlite3.Row) -> tuple[int, str, int]:
            """Rank the navigation row by the actual latest scan event.

            A timestamped scan always wins, regardless of process order. Legacy
            scanned rows without event timestamps fall back to process progress.
            Completely unscanned items deliberately choose Staging.
            """
            scanned = int(row["scanned_qty"] or 0)
            kind = stage_kind(row)
            last_scan_time = str(row["last_scan_time"] or "")
            progress_rank = {
                "indian_trail": 100,
                "outbound": 90,
                "cpu": 86,
                "dtc": 84,
                "greenville": 82,
                "staging": 70,
                "other": 40,
            }.get(kind, 0)
            if last_scan_time:
                return (3, last_scan_time, progress_rank)
            if scanned:
                return (2, "", progress_rank)
            if kind == "staging":
                return (1, "", 100)
            if row["bay_code"]:
                return (1, "", 40)
            if row["rack_code"]:
                return (1, "", 30)
            return (0, "", progress_rank)

        def rack_location_label(code: Any) -> str:
            """Purpose: Run the rack location label workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            clean_code = normalize_rack_code(str(code or ""))
            if not clean_code:
                return ""
            if clean_code == "T":
                return "Truck"
            if re.fullmatch(r"T\d+", clean_code):
                return f"Truck {clean_code[1:]}"
            return f"Rack {clean_code}"

        def airport_label(scanner: Any) -> str:
            """Purpose: Run the airport label workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            return str(scanner or "Airport Rd").replace(" - ", " ").strip() or "Airport Rd"

        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            if user is not None and not user_can_access_stage(user, row["stage"], row["scanner"]):
                continue
            key = f"{row['delivery_date']}::{row['order_no']}::{row['item_no']}"
            rank = representative_rank(row)
            result = grouped.setdefault(key, {
                "lineItemId": row["id"],
                "deliveryListId": row["list_id"],
                "deliveryList": row["label"],
                "deliveryDate": row["delivery_date"],
                "stage": row["stage"],
                "scanner": row["scanner"],
                "barcode": row["barcode"],
                "sourceId": row["source_id"],
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
                "rackCode": row["rack_code"],
                "rackName": row["rack_display_name"],
                "rackType": row["rack_type"],
                "rackStatus": row["rack_status"],
                "lastScanTime": row["last_scan_time"],
                "lastScanUser": row["last_scan_user"],
                "stageLocations": [],
                "locationText": "Not Scanned Yet",
                "_rank": (0, "", -1),
                "_representativeKind": "",
                "_representativeHasScan": False,
                "_staged": False,
                "_outbound": False,
                "_received": False,
                "_cpu": False,
                "_dtc": False,
                "_greenville": False,
                "_scanner": row["scanner"],
                "_transportCode": "",
                "_bayLabel": "",
                "_preassignedBay": "",
            })

            scanned = int(row["scanned_qty"] or 0)
            kind = stage_kind(row)
            if row["rack_code"] and not result.get("_transportCode"):
                result["_transportCode"] = row["rack_code"]
            if row["bay_code"]:
                bay_label = row["bay_display_name"] or row["bay_code"]
                result["_preassignedBay"] = bay_label
                if scanned and kind == "indian_trail":
                    result["_bayLabel"] = bay_label
            if scanned:
                if kind == "indian_trail":
                    result["_received"] = True
                elif kind == "outbound":
                    result["_outbound"] = True
                elif kind == "cpu":
                    result["_cpu"] = True
                elif kind == "dtc":
                    result["_dtc"] = True
                elif kind == "greenville":
                    result["_greenville"] = True
                elif kind == "staging":
                    result["_staged"] = True
                else:
                    result["_staged"] = True

            if rank >= tuple(result.get("_rank", (0, "", -1))):
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
                result["rackCode"] = row["rack_code"] or result.get("_transportCode")
                result["rackName"] = row["rack_display_name"]
                result["rackType"] = row["rack_type"]
                result["rackStatus"] = row["rack_status"]
                result["lastScanTime"] = row["last_scan_time"]
                result["lastScanUser"] = row["last_scan_user"]
                result["_scanner"] = row["scanner"]
                result["_representativeKind"] = kind
                result["_representativeHasScan"] = bool(row["last_scan_time"] or scanned)
                result["_rank"] = rank

        cleaned_results: list[dict[str, Any]] = []
        for result in grouped.values():
            transport_label = rack_location_label(result.get("_transportCode") or result.get("rackCode"))
            bay_label = result.get("_bayLabel") or result.get("bay") or result.get("_preassignedBay")
            representative_kind = str(result.get("_representativeKind") or "")
            representative_has_scan = bool(result.get("_representativeHasScan"))
            if not representative_has_scan:
                location = "Not Scanned Yet"
            elif representative_kind == "indian_trail":
                location = "Indian Trail Received"
                if bay_label:
                    location = f"{location} - Bay {bay_label}"
            elif representative_kind == "outbound":
                location = f"Outbound on {transport_label}" if transport_label else f"Outbound {airport_label(result.get('_scanner'))}"
            elif representative_kind == "staging":
                location = f"Staging {airport_label(result.get('_scanner'))}"
                if transport_label:
                    location = f"{location} on {transport_label}"
            elif representative_kind == "cpu":
                location = "Customer Pickup"
            elif representative_kind == "dtc":
                location = "Delivery to Customer"
            elif representative_kind == "greenville":
                location = "BFS Greenville"
            else:
                location = str(result.get("stage") or result.get("scanner") or "Last scanned stage")

            result["locationText"] = location
            result["stageLocations"] = [location]
            result["navigationDeliveryListId"] = result.get("deliveryListId")
            result["navigationStage"] = result.get("stage")
            if result.get("_transportCode") and not result.get("rackCode"):
                result["rackCode"] = result.get("_transportCode")
            for key in list(result.keys()):
                if key.startswith("_"):
                    result.pop(key, None)
            cleaned_results.append(result)
        return cleaned_results[:30]

    def manual_edit_sibling_rows(self, con: sqlite3.Connection, row: sqlite3.Row) -> list[sqlite3.Row]:
        """Purpose: Run the manual edit sibling rows workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        context = con.execute(
            "SELECT delivery_date FROM delivery_lists WHERE id = ?",
            (row["list_id"],),
        ).fetchone()
        if not context:
            return [row]
        if str(row["source_id"] or "").strip():
            return con.execute(
                """
                SELECT li.*, dl.delivery_date, dl.stage, dl.scanner
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE dl.delivery_date = ? AND li.source_id = ?
                ORDER BY dl.stage, li.id
                """,
                (context["delivery_date"], row["source_id"]),
            ).fetchall()
        return con.execute(
            """
            SELECT li.*, dl.delivery_date, dl.stage, dl.scanner
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.delivery_date = ? AND li.order_no = ? AND li.item_no = ?
            ORDER BY dl.stage, li.id
            """,
            (context["delivery_date"], row["order_no"], row["item_no"]),
        ).fetchall()

    def manual_route_profile(self, delivery_date: str, destination: str) -> tuple[str, str, str]:
        """Purpose: Run the manual route profile workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        profiles = {
            "Indian Trail": ("inbound-indian-trail", "Inbound - Indian Trail", "Indian Trail"),
            "CPU": ("customer-pickup", "Customer Pickup", "Customer Pickup"),
            "Greenville": ("bfs-greenville", "BFS Greenville", "Greenville"),
            "DTC": ("dtc", "DTC - Deliver to Customer", "DTC"),
        }
        if destination in profiles:
            suffix, stage, scanner = profiles[destination]
        else:
            route_code = re.sub(r"[^a-z0-9]+", "-", str(destination or "route").lower()).strip("-") or "route"
            suffix, stage, scanner = f"route-{route_code}", str(destination or "Route"), str(destination or "Route")
        return f"{delivery_date}-{suffix}", stage, scanner

    def ensure_manual_route_list(self, con: sqlite3.Connection, delivery_date: str, destination: str) -> str:
        """Purpose: Validate manual route list for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        list_id, stage, scanner = self.manual_route_profile(delivery_date, destination)
        con.execute(
            """
            INSERT INTO delivery_lists (id, label, delivery_date, stage, scanner, status, revision, created_at)
            VALUES (?, ?, ?, ?, ?, 'active', 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                label = excluded.label,
                delivery_date = excluded.delivery_date,
                stage = excluded.stage,
                scanner = excluded.scanner,
                status = 'active'
            """,
            (list_id, f"{format_display_date(delivery_date)} - {stage}", delivery_date, stage, scanner, now_iso()),
        )
        return list_id

    def merge_manual_receiving_row(
        self,
        con: sqlite3.Connection,
        source_id: str,
        target_id: str,
        target_list_id: str,
    ) -> None:
        """Purpose: Run the merge manual receiving row workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        if source_id == target_id:
            return
        source = con.execute("SELECT * FROM line_items WHERE id = ?", (source_id,)).fetchone()
        target = con.execute("SELECT * FROM line_items WHERE id = ?", (target_id,)).fetchone()
        if not source or not target:
            return
        con.execute(
            "UPDATE line_items SET scanned_qty = MAX(scanned_qty, ?), qty = MAX(qty, ?) WHERE id = ?",
            (int(source["scanned_qty"] or 0), int(source["qty"] or 0), target_id),
        )
        self.insert_audit(
            con,
            "line_item",
            target_id,
            "merge_line_item_reference",
            "system",
            "",
            "Historical scan and bay events remain linked to their original immutable identifiers",
            {"sourceLineItemId": source_id, "targetListId": target_list_id},
        )
        con.execute(
            "UPDATE bay_assignments SET line_item_id = ?, delivery_list_id = ? WHERE line_item_id = ?",
            (target_id, target_list_id, source_id),
        )
        rack_rows = con.execute("SELECT * FROM rack_items WHERE line_item_id = ?", (source_id,)).fetchall()
        for rack_row in rack_rows:
            existing = con.execute(
                "SELECT * FROM rack_items WHERE rack_id = ? AND line_item_id = ?",
                (rack_row["rack_id"], target_id),
            ).fetchone()
            if existing:
                status = "Active" if "Active" in {str(existing["status"]), str(rack_row["status"])} else str(existing["status"])
                con.execute(
                    "UPDATE rack_items SET qty = MAX(qty, ?), status = ? WHERE id = ?",
                    (int(rack_row["qty"] or 0), status, existing["id"]),
                )
                con.execute("DELETE FROM rack_items WHERE id = ?", (rack_row["id"],))
            else:
                con.execute("UPDATE rack_items SET line_item_id = ? WHERE id = ?", (target_id, rack_row["id"]))
        con.execute("DELETE FROM line_items WHERE id = ?", (source_id,))

    def sync_manual_route_membership(self, con: sqlite3.Connection, row: sqlite3.Row) -> str:
        """Purpose: Run the sync manual route membership workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        siblings = self.manual_edit_sibling_rows(con, row)
        if not siblings:
            return ""
        delivery_date = str(siblings[0]["delivery_date"] or "")
        destination = self.destination_for_line_item(row)
        target_list_id = self.ensure_manual_route_list(con, delivery_date, destination)
        receiving_rows = [
            sibling
            for sibling in siblings
            if not str(sibling["stage"] or "").lower().startswith("staging")
            and not str(sibling["stage"] or "").lower().startswith("outbound")
        ]
        target_row = next((item for item in receiving_rows if item["list_id"] == target_list_id), None)
        if not target_row:
            if receiving_rows:
                target_row = receiving_rows[0]
                con.execute("UPDATE line_items SET list_id = ? WHERE id = ?", (target_list_id, target_row["id"]))
                con.execute("UPDATE bay_assignments SET delivery_list_id = ? WHERE line_item_id = ?", (target_list_id, target_row["id"]))
            else:
                source = next(
                    (item for item in siblings if str(item["stage"] or "").lower().startswith("staging")),
                    siblings[0],
                )
                new_id = f"{target_list_id}-manual-{secrets.token_hex(6)}"
                con.execute(
                    """
                    INSERT INTO line_items (
                        id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty,
                        dimensions, customer, route, source_route, job, product, process_state, queue_state, suggested_bay
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        target_list_id,
                        source["source_id"],
                        source["barcode"],
                        source["order_no"],
                        source["item_no"],
                        source["qty"],
                        source["dimensions"],
                        source["customer"],
                        source["route"],
                        row_value(source, "source_route", ""),
                        source["job"],
                        source["product"],
                        source["process_state"],
                        source["queue_state"],
                        source["suggested_bay"],
                    ),
                )
                target_row = con.execute(
                    """
                    SELECT li.*, dl.delivery_date, dl.stage, dl.scanner
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE li.id = ?
                    """,
                    (new_id,),
                ).fetchone()
        if target_row:
            for other in receiving_rows:
                if other["id"] != target_row["id"]:
                    self.merge_manual_receiving_row(con, other["id"], target_row["id"], target_list_id)
        return target_list_id

    def update_line_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Update one logical delivery-list item and keep its workflow stage copies synchronized."""
        data = dict(data or {})
        if "routeOverride" in data:
            data["route"] = data.get("routeOverride")
        line_item_id = str(data.get("lineItemId") or "").strip()
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
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM line_items WHERE id = ?", (line_item_id,)).fetchone()
            if not row:
                raise ValueError("Line item not found")
            original_list_id = str(row["list_id"])
            siblings = self.manual_edit_sibling_rows(con, row)
            sibling_ids = [str(item["id"]) for item in siblings] or [line_item_id]
            affected_list_ids = sorted({str(item["list_id"]) for item in siblings} or {original_list_id})
            next_qty = int(data.get("qty", row["qty"]) or 0)
            next_scanned = int(data.get("scanned", row["scanned_qty"]) or 0)
            max_existing_scanned = max((int(item["scanned_qty"] or 0) for item in siblings), default=0)
            if next_qty < 0 or next_scanned < 0 or next_scanned > next_qty:
                raise ValueError("Scanned quantity must be between 0 and total quantity")
            if "qty" in data and max_existing_scanned > next_qty:
                raise ValueError("Qty cannot be lower than a scanned quantity on another stage for this item")

            business_updates: dict[str, Any] = {}
            current_updates: dict[str, Any] = {}
            changed_fields: list[str] = []
            before_values: dict[str, Any] = {}
            after_values: dict[str, Any] = {}

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
                    elif column == "route":
                        raw_route = str(value or "").strip()
                        explicit, canonical = normalize_route_column(raw_route)
                        # Manual route edits are destination overrides, not import
                        # fallbacks. Store Indian Trail as the full phrase so a CPU
                        # Job Nr. or customer rule cannot immediately infer CPU again.
                        if explicit:
                            value = canonical or "INDIAN TRAIL"
                        else:
                            value = "INDIAN TRAIL"

                if column == "scanned_qty":
                    previous = int(row[column] or 0)
                    if value != previous:
                        current_updates[column] = value
                        changed_fields.append(input_key)
                        before_values[input_key] = previous
                        after_values[input_key] = value
                    continue

                sibling_values = [item[column] for item in siblings] if siblings else [row[column]]
                if column == "route":
                    normalized_existing = []
                    for existing in sibling_values:
                        existing_explicit, existing_canonical = normalize_route_column(existing)
                        normalized_existing.append(existing_canonical or "INDIAN TRAIL" if existing_explicit else "INDIAN TRAIL")
                    normalized_value = str(value or "")
                else:
                    normalized_existing = [int(existing or 0) if column == "qty" else str(existing or "") for existing in sibling_values]
                    normalized_value = int(value or 0) if column == "qty" else str(value or "")
                if any(existing != normalized_value for existing in normalized_existing):
                    business_updates[column] = value
                    changed_fields.append(input_key)
                    before_values[input_key] = normalized_existing[0] if normalized_existing else ""
                    after_values[input_key] = value

            if ("order" in changed_fields or "item" in changed_fields) and "barcode" not in data:
                next_order = str(parse_int_text(data.get("order", row["order_no"])) or row["order_no"])
                next_item = str(parse_int_text(data.get("item", row["item_no"])) or row["item_no"]).zfill(3)
                next_barcode = canonical_barcode(next_order, next_item)
                if any(str(item["barcode"] or "") != next_barcode for item in siblings):
                    business_updates["barcode"] = next_barcode

            location_changed = False
            requested_location = str(data.get("location") or "").strip()
            if "location" in data:
                rack_row = con.execute(
                    """
                    SELECT r.rack_code AS location
                    FROM rack_items ri JOIN racks r ON r.id = ri.rack_id
                    WHERE ri.line_item_id = ? AND ri.status = 'Active' AND r.active = 1
                    ORDER BY ri.id DESC LIMIT 1
                    """,
                    (line_item_id,),
                ).fetchone()
                bay_row = con.execute(
                    """
                    SELECT b.bay_code AS location
                    FROM bay_assignments ba JOIN bays b ON b.id = ba.bay_id
                    WHERE ba.line_item_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
                    ORDER BY ba.id DESC LIMIT 1
                    """,
                    (line_item_id,),
                ).fetchone()
                existing_location = str(row_value(bay_row, "location", row_value(rack_row, "location", "")) or "").strip()
                location_changed = existing_location.upper() != requested_location.upper()
                if location_changed:
                    changed_fields.append("location")
                    before_values["location"] = existing_location
                    after_values["location"] = requested_location

            if business_updates:
                assignments = ", ".join(f"{column} = ?" for column in business_updates)
                placeholders = ",".join("?" for _ in sibling_ids)
                con.execute(
                    f"UPDATE line_items SET {assignments}, updated_at_utc = ? WHERE id IN ({placeholders})",
                    [*business_updates.values(), now_iso(), *sibling_ids],
                )
            if current_updates:
                assignments = ", ".join(f"{column} = ?" for column in current_updates)
                con.execute(
                    f"UPDATE line_items SET {assignments}, updated_at_utc = ? WHERE id = ?",
                    [*current_updates.values(), now_iso(), line_item_id],
                )

            updated_row = con.execute("SELECT * FROM line_items WHERE id = ?", (line_item_id,)).fetchone()
            if updated_row and location_changed:
                self.update_line_item_location(con, updated_row, requested_location, user)
                updated_row = con.execute("SELECT * FROM line_items WHERE id = ?", (line_item_id,)).fetchone()

            target_list_id = ""
            if updated_row and any(key in changed_fields for key in ("route", "job", "customer")):
                target_list_id = self.sync_manual_route_membership(con, updated_row)
                if target_list_id and target_list_id not in affected_list_ids:
                    affected_list_ids.append(target_list_id)
                    affected_list_ids.sort()

            affected_racks = con.execute(
                f"SELECT DISTINCT rack_id FROM rack_items WHERE line_item_id IN ({','.join('?' for _ in sibling_ids)}) AND status = 'Active'",
                sibling_ids,
            ).fetchall()
            for rack_row in affected_racks:
                self.refresh_rack_destination(con, int(rack_row["rack_id"]))

            if changed_fields:
                self.insert_audit(
                    con,
                    "line_item",
                    line_item_id,
                    "manual_edit",
                    user,
                    "",
                    "",
                    {
                        "changedFields": changed_fields,
                        "before": before_values,
                        "after": after_values,
                        "stageRecordCount": len(sibling_ids),
                        "affectedListIds": affected_list_ids,
                        "destinationListId": target_list_id,
                    },
                )
            con.commit()
            payload = self._get_payload(con, original_list_id)
            logical_label = f"{after_values.get('order', row['order_no'])}-{after_values.get('item', row['item_no'])}"
            if changed_fields:
                stage_text = f" across {len(sibling_ids)} workflow stages" if len(sibling_ids) > 1 else ""
                payload["message"] = f"Updated line item {logical_label}{stage_text}."
            else:
                payload["message"] = f"No changes were needed for line item {logical_label}."
            payload["logicalUpdatedCount"] = 1 if changed_fields else 0
            payload["stageRecordCount"] = len(sibling_ids)
            payload["affectedListIds"] = affected_list_ids
            payload["changedFields"] = changed_fields
            payload["destinationListId"] = target_list_id
            payload["routeApplied"] = str(after_values.get("route", updated_row["route"] if updated_row else row["route"]) or "")

            updated_order = str(after_values.get("order", row["order_no"]) or "")
            updated_item_no = str(after_values.get("item", row["item_no"]) or "").zfill(3)
            updated_results = self.admin_search_line_items(updated_order, "", 100, 0, {}).get("results", [])
            exact_matches = [
                item
                for item in updated_results
                if str(item.get("order") or "") == updated_order
                and str(item.get("item") or "").zfill(3) == updated_item_no
            ]
            updated_item = next(
                (
                    item
                    for item in exact_matches
                    if target_list_id and str(item.get("listId") or "") == target_list_id
                ),
                None,
            )
            if updated_item is None:
                updated_item = next(
                    (
                        item
                        for item in exact_matches
                        if str(item.get("lineItemId") or "") == line_item_id
                    ),
                    exact_matches[0] if exact_matches else None,
                )
            payload["updatedItem"] = updated_item or {}
            return payload

    def update_line_item_location(self, con: sqlite3.Connection, row: sqlite3.Row, location: str, user: str) -> None:
        """Purpose: Update line item location for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean = str(location or "").strip()
        line_item_id = row["id"]
        if not clean:
            previous_rack_ids = [item["rack_id"] for item in con.execute("SELECT DISTINCT rack_id FROM rack_items WHERE line_item_id = ? AND status = 'Active'", (line_item_id,)).fetchall()]
            con.execute(
                "UPDATE rack_items SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Manual location cleared' WHERE line_item_id = ? AND status = 'Active'",
                (user, now_iso(), line_item_id),
            )
            for rack_id in previous_rack_ids:
                self.refresh_rack_destination(con, rack_id)
            con.execute(
                "UPDATE bay_assignments SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = 'Manual location cleared' WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')",
                (user, now_iso(), line_item_id),
            )
            self.insert_audit(con, "line_item", line_item_id, "manual_location_clear", user, "", "", {})
            return
        rack = con.execute("SELECT * FROM racks WHERE UPPER(rack_code) = UPPER(?) AND active = 1", (clean,)).fetchone()
        if rack:
            self.validate_rack_destination_for_item(con, rack, row)
            previous_rack_ids = [item["rack_id"] for item in con.execute("SELECT DISTINCT rack_id FROM rack_items WHERE line_item_id = ? AND rack_id <> ? AND status = 'Active'", (line_item_id, rack["id"])).fetchall()]
            con.execute(
                "UPDATE bay_assignments SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = 'Moved to rack from manual edit' WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')",
                (user, now_iso(), line_item_id),
            )
            qty = max(1, min(int(row["qty"] or 1), int(row["scanned_qty"] or row["qty"] or 1)))
            con.execute(
                """
                INSERT INTO rack_items (rack_id, line_item_id, qty, status, added_by, added_at, reason)
                VALUES (?, ?, ?, 'Active', ?, ?, 'Manual location edit')
                ON CONFLICT(rack_id, line_item_id) DO UPDATE SET
                    qty = excluded.qty,
                    status = 'Active',
                    removed_by = '',
                    removed_at = '',
                    reason = 'Manual location edit',
                    added_by = excluded.added_by,
                    added_at = excluded.added_at
                """,
                (rack["id"], line_item_id, qty, user, now_iso()),
            )
            con.execute(
                "UPDATE rack_items SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Moved to another rack from manual edit' WHERE line_item_id = ? AND rack_id <> ? AND status = 'Active'",
                (user, now_iso(), line_item_id, rack["id"]),
            )
            for rack_id in previous_rack_ids:
                self.refresh_rack_destination(con, rack_id)
            self.refresh_rack_destination(con, rack["id"])
            self.insert_audit(con, "line_item", line_item_id, "manual_location_rack", user, "", "", {"rackCode": rack["rack_code"]})
            return
        bay = con.execute("SELECT * FROM bays WHERE UPPER(bay_code) = UPPER(?) AND active = 1", (clean,)).fetchone()
        if not bay:
            bay = con.execute("SELECT * FROM bays WHERE UPPER(display_name) = UPPER(?) AND active = 1", (clean,)).fetchone()
        if bay:
            previous_rack_ids = [item["rack_id"] for item in con.execute("SELECT DISTINCT rack_id FROM rack_items WHERE line_item_id = ? AND status = 'Active'", (line_item_id,)).fetchall()]
            con.execute(
                "UPDATE rack_items SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Moved to bay from manual edit' WHERE line_item_id = ? AND status = 'Active'",
                (user, now_iso(), line_item_id),
            )
            for rack_id in previous_rack_ids:
                self.refresh_rack_destination(con, rack_id)
            con.execute(
                "UPDATE bay_assignments SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = 'Moved to another bay from manual edit' WHERE line_item_id = ? AND bay_id <> ? AND status NOT IN ('Cleared', 'Cancelled')",
                (user, now_iso(), line_item_id, bay["id"]),
            )
            existing = con.execute("SELECT id FROM bay_assignments WHERE line_item_id = ? AND bay_id = ? AND status NOT IN ('Cleared', 'Cancelled')", (line_item_id, bay["id"])).fetchone()
            if existing:
                con.execute("UPDATE bay_assignments SET assigned_qty = ?, reason = 'Manual location edit' WHERE id = ?", (int(row["qty"] or 1), existing["id"]))
            else:
                con.execute(
                    """
                    INSERT INTO bay_assignments (delivery_list_id, line_item_id, bay_id, assigned_qty, status, assigned_by, assigned_at, reason)
                    VALUES (?, ?, ?, ?, 'Assigned', ?, ?, 'Manual location edit')
                    """,
                    (row["list_id"], line_item_id, bay["id"], int(row["qty"] or 1), user, now_iso()),
                )
            self.insert_audit(con, "line_item", line_item_id, "manual_location_bay", user, "", "", {"bayCode": bay["bay_code"]})
            return
        raise ValueError(f"Location '{clean}' was not found as an active rack or bay")

    def delete_line_item(self, line_item_id: str, user: str) -> dict[str, Any]:
        """Purpose: Remove line item for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Remove delivery list for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_id = str(list_id or "").strip()
        if not clean_id:
            raise ValueError("listId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (clean_id,)).fetchone()
            if not row:
                raise ValueError("Delivery list not found")
            user_row = con.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()
            user_id = int(user_row["id"]) if user_row else None
            deleted_at = now_iso()
            con.execute("UPDATE bay_assignments SET status = 'Cancelled', reason = 'Delivery list deleted' WHERE delivery_list_id = ?", (clean_id,))
            con.execute(
                "UPDATE delivery_lists SET status = 'deleted', is_deleted = 1, deleted_at_utc = ?, "
                "deleted_by_user_id = ?, updated_at_utc = ?, updated_by_user_id = ? WHERE id = ?",
                (deleted_at, user_id, deleted_at, user_id, clean_id),
            )
            con.execute(
                "UPDATE line_items SET is_deleted = 1, deleted_at_utc = ?, deleted_by_user_id = ?, "
                "updated_at_utc = ?, updated_by_user_id = ? WHERE list_id = ?",
                (deleted_at, user_id, deleted_at, user_id, clean_id),
            )
            self.insert_audit(con, "delivery_list", clean_id, "delete_delivery_list", user, row["scanner"], "Deleted from admin page")
            con.commit()
        return {"ok": True, "deletedListId": clean_id, "lists": self.get_delivery_lists()}

    def delete_delivery_date(self, delivery_date: str, user: str) -> dict[str, Any]:
        """Purpose: Remove delivery date for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        clean_date = str(delivery_date or "").strip()
        if not clean_date:
            raise ValueError("deliveryDate is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT id FROM delivery_lists WHERE delivery_date = ? AND status = 'active'", (clean_date,)).fetchall()
            list_ids = [row["id"] for row in rows]
            if not list_ids:
                raise ValueError("No delivery lists found for that date")
            placeholders = ",".join("?" for _ in list_ids)
            user_row = con.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()
            user_id = int(user_row["id"]) if user_row else None
            deleted_at = now_iso()
            con.execute(f"UPDATE bay_assignments SET status = 'Cancelled', reason = 'Delivery date deleted' WHERE delivery_list_id IN ({placeholders})", list_ids)
            con.execute(
                f"UPDATE delivery_lists SET status = 'deleted', is_deleted = 1, deleted_at_utc = ?, "
                f"deleted_by_user_id = ?, updated_at_utc = ?, updated_by_user_id = ? WHERE id IN ({placeholders})",
                [deleted_at, user_id, deleted_at, user_id, *list_ids],
            )
            con.execute(
                f"UPDATE line_items SET is_deleted = 1, deleted_at_utc = ?, deleted_by_user_id = ?, "
                f"updated_at_utc = ?, updated_by_user_id = ? WHERE list_id IN ({placeholders})",
                [deleted_at, user_id, deleted_at, user_id, *list_ids],
            )
            self.insert_audit(con, "delivery_date", clean_date, "delete_delivery_date", user, "", "Deleted from admin page", {"listIds": list_ids})
            con.commit()
        return {"ok": True, "deliveryDate": clean_date, "deletedCount": len(list_ids), "lists": self.get_delivery_lists()}

    def reports_summary(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Purpose: Run the reports summary workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        filters = filters or {}
        date_from = str(filters.get("dateFrom") or "").strip()
        date_to = str(filters.get("dateTo") or "").strip()

        def date_clause(alias: str = "") -> tuple[str, list[str]]:
            """Purpose: Run the date clause workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            column = f"{alias}.created_at" if alias else "created_at"
            parts: list[str] = []
            params: list[str] = []
            if date_from:
                parts.append(f"substr({column}, 1, 10) >= ?")
                params.append(date_from)
            if date_to:
                parts.append(f"substr({column}, 1, 10) <= ?")
                params.append(date_to)
            return (" AND " + " AND ".join(parts), params) if parts else ("", [])

        def delivery_list_date_clause(alias: str = "dl") -> tuple[str, list[str]]:
            # Dashboard inventory stats are based on delivery-list dates, not scan timestamps.
            """Purpose: Run the delivery list date clause workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
            """
            column = f"{alias}.delivery_date" if alias else "delivery_date"
            parts: list[str] = []
            params: list[str] = []
            if date_from:
                parts.append(f"{column} >= ?")
                params.append(date_from)
            if date_to:
                parts.append(f"{column} <= ?")
                params.append(date_to)
            return (" AND " + " AND ".join(parts), params) if parts else ("", [])

        scan_date_sql, scan_params = date_clause()
        audit_date_sql, audit_params = date_clause()
        list_date_sql, list_date_params = delivery_list_date_clause("dl")
        current_month = datetime.now(timezone.utc).date().replace(day=1)
        next_month = (current_month.replace(year=current_month.year + 1, month=1) if current_month.month == 12 else current_month.replace(month=current_month.month + 1))
        remake_sql = """
            (UPPER(li.process_state) LIKE '%REMAKE%' OR UPPER(li.queue_state) LIKE '%REMAKE%'
             OR (' ' || UPPER(li.process_state) || ' ') LIKE '% RM %'
             OR (' ' || UPPER(li.queue_state) || ' ') LIKE '% RM %')
        """
        with self.connect() as con:
            scans_by_user = con.execute(
                f"""
                SELECT user_name, COUNT(*) AS scans
                FROM scan_events
                WHERE event_type = 'scan'{scan_date_sql}
                GROUP BY user_name
                ORDER BY scans DESC
                """,
                scan_params,
            ).fetchall()
            incomplete = con.execute(
                """
                SELECT dl.label, COUNT(*) AS item_count, SUM(li.qty - li.scanned_qty) AS remaining_qty
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE li.scanned_qty < li.qty
                GROUP BY dl.id, dl.label, dl.delivery_date
                ORDER BY dl.delivery_date DESC, dl.label
                """
            ).fetchall()
            bad_scans = con.execute(
                f"SELECT COUNT(*) FROM scan_events WHERE event_type = 'error'{scan_date_sql}",
                scan_params,
            ).fetchone()[0]
            duplicates = con.execute(
                f"SELECT COUNT(*) FROM scan_events WHERE event_type = 'duplicate'{scan_date_sql}",
                scan_params,
            ).fetchone()[0]
            manual_scans = con.execute(
                f"SELECT COUNT(*) FROM audit_events WHERE action = 'manual_scan'{audit_date_sql}",
                audit_params,
            ).fetchone()[0]
            action_rows = con.execute(
                f"""
                SELECT action, COUNT(*) AS count
                FROM audit_events
                WHERE 1 = 1{audit_date_sql}
                GROUP BY action
                ORDER BY count DESC, action
                """,
                audit_params,
            ).fetchall()
            rack_actions = con.execute(
                f"""
                SELECT COUNT(*)
                FROM audit_events
                WHERE (entity_type IN ('rack', 'rack_item') OR action LIKE '%rack%'){audit_date_sql}
                """,
                audit_params,
            ).fetchone()[0]
            bay_actions = con.execute(
                f"""
                SELECT COUNT(*)
                FROM audit_events
                WHERE (entity_type IN ('bay', 'bay_assignment') OR action LIKE '%bay%' OR action LIKE '%sdi%' OR action = 'indian_trail_receive'){audit_date_sql}
                """,
                audit_params,
            ).fetchone()[0]
            user_actions = con.execute(
                f"""
                SELECT COUNT(*)
                FROM audit_events
                WHERE (entity_type = 'user' OR action LIKE '%user%'){audit_date_sql}
                """,
                audit_params,
            ).fetchone()[0]
            manual_edits = con.execute(
                f"""
                SELECT COUNT(*)
                FROM audit_events
                WHERE (action = 'manual_edit' OR action LIKE 'manual_location_%'){audit_date_sql}
                """,
                audit_params,
            ).fetchone()[0]
            bay_overrides = con.execute(
                f"SELECT COUNT(*) FROM audit_events WHERE action = 'indian_trail_receive_bay_override'{audit_date_sql}",
                audit_params,
            ).fetchone()[0]
            sdi_count = con.execute("SELECT COUNT(*) FROM bay_assignments WHERE status = 'SDIOverride'").fetchone()[0]
            glass_rows = con.execute(
                f"""
                SELECT glass_type, SUM(qty) AS qty, COUNT(*) AS row_count
                FROM (
                    SELECT
                        dl.delivery_date,
                        li.source_id,
                        COALESCE(NULLIF(MAX(li.product), ''), NULLIF(MAX(li.job), ''), 'Other Glass') AS glass_type,
                        MAX(li.qty) AS qty
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active'{list_date_sql}
                    GROUP BY dl.delivery_date, li.source_id
                ) unique_items
                GROUP BY glass_type
                HAVING SUM(qty) > 0
                ORDER BY qty DESC, glass_type
                """,
                list_date_params,
            ).fetchall()
            monthly_remake_row = con.execute(
                f"""
                SELECT COUNT(*) AS row_count, COALESCE(SUM(qty), 0) AS qty
                FROM (
                    SELECT dl.delivery_date, li.source_id, MAX(li.qty) AS qty
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active'
                      AND dl.delivery_date >= ?
                      AND dl.delivery_date < ?
                      AND {remake_sql}
                    GROUP BY dl.delivery_date, li.source_id
                ) unique_remakes
                """,
                (current_month.isoformat(), next_month.isoformat()),
            ).fetchone()
            range_remake_row = con.execute(
                f"""
                SELECT COUNT(*) AS row_count, COALESCE(SUM(qty), 0) AS qty
                FROM (
                    SELECT dl.delivery_date, li.source_id, MAX(li.qty) AS qty
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active'{list_date_sql}
                      AND {remake_sql}
                    GROUP BY dl.delivery_date, li.source_id
                ) unique_remakes
                """,
                list_date_params,
            ).fetchone()
        return {
            "dateFrom": date_from,
            "dateTo": date_to,
            "scansByOperator": [{"user": row["user_name"], "scans": row["scans"]} for row in scans_by_user],
            "incompleteByDeliveryList": [
                {"deliveryList": row["label"], "itemCount": row["item_count"], "remainingQty": row["remaining_qty"] or 0}
                for row in incomplete
            ],
            "badScanCount": bad_scans,
            "duplicateScanCount": duplicates,
            "manualScanCount": manual_scans,
            "manualEditCount": manual_edits,
            "bayOverrideCount": bay_overrides,
            "rackActionCount": rack_actions,
            "bayActionCount": bay_actions,
            "userActionCount": user_actions,
            "sdiCount": sdi_count,
            "glassQuantityByType": [
                {"glassType": row["glass_type"], "qty": int(row["qty"] or 0), "rowCount": int(row["row_count"] or 0)}
                for row in glass_rows
            ],
            "monthlyRemakeCount": int(monthly_remake_row["row_count"] or 0),
            "monthlyRemakeQty": int(monthly_remake_row["qty"] or 0),
            "monthlyRemakeMonth": current_month.strftime("%B %Y"),
            "rangeRemakeCount": int(range_remake_row["row_count"] or 0),
            "rangeRemakeQty": int(range_remake_row["qty"] or 0),
            "actionCounts": {row["action"]: row["count"] for row in action_rows},
        }

    @staticmethod
    def _audit_event_dict(row: Any) -> dict[str, Any]:
        """Normalize one active or archived audit row for browser action-history views."""
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        return {
            "id": int(row["id"] if "id" in row.keys() else row["source_event_id"]),
            "entityType": str(row["entity_type"] or ""),
            "entityId": str(row["entity_id"] or ""),
            "action": str(row["action"] or ""),
            "user": str(row["user_name"] or ""),
            "station": str(row["station"] or ""),
            "reason": str(row["reason"] or ""),
            "payload": payload if isinstance(payload, dict) else {},
            "createdAt": str(row["created_at"] or ""),
        }

    def _archive_old_audit_events(self, con: Any, cutoff: str) -> int:
        """Copy action history older than the active window into the immutable archive.

        The primary audit table remains append-only. Active GUI queries are limited to
        the last 30 days, while the archive preserves older records without weakening
        the existing immutable audit triggers.
        """
        database_type = str(getattr(self, "database_type", "sqlite") or "sqlite").lower()
        if database_type != "sqlite":
            return 0
        table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'audit_events_archive'"
        ).fetchone()
        if not table:
            return 0
        rows = con.execute(
            """
            SELECT ae.id, ae.entity_type, ae.entity_id, ae.action, ae.user_name,
                   ae.station, ae.reason, ae.payload_json, ae.created_at
            FROM audit_events ae
            LEFT JOIN audit_events_archive aa ON aa.source_event_id = ae.id
            WHERE ae.created_at < ? AND aa.source_event_id IS NULL
            ORDER BY ae.id
            LIMIT ?
            """,
            (cutoff, ACTION_HISTORY_ARCHIVE_BATCH_SIZE),
        ).fetchall()
        if not rows:
            return 0
        archived_at = utc_now_iso()
        con.executemany(
            """
            INSERT OR IGNORE INTO audit_events_archive (
                source_event_id, entity_type, entity_id, action, user_name,
                station, reason, payload_json, created_at, archived_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"], row["entity_type"], row["entity_id"], row["action"],
                    row["user_name"], row["station"], row["reason"], row["payload_json"],
                    row["created_at"], archived_at,
                )
                for row in rows
            ],
        )
        con.commit()
        return len(rows)

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the newest active audit events inside the 30-day investigation window."""
        clean_limit = max(1, min(int(limit or 100), 5000))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=ACTION_HISTORY_RETENTION_DAYS)).isoformat(timespec="seconds")
        with self.connect() as con:
            self._archive_old_audit_events(con, cutoff)
            rows = con.execute(
                """
                SELECT id, entity_type, entity_id, action, user_name, station, reason, payload_json, created_at
                FROM audit_events
                WHERE created_at >= ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (cutoff, clean_limit),
            ).fetchall()
        return [self._audit_event_dict(row) for row in rows]

    @staticmethod
    def _gui_action_history_rules(context_key: str) -> tuple[set[str], tuple[str, ...], set[str] | None]:
        context_rules: dict[str, tuple[set[str], tuple[str, ...]]] = {
            "deliveryLists": ({"delivery_list", "delivery_date", "delivery_list_updates"}, ("delivery_list", "import", "reset", "delete_delivery")),
            "deliveryActions": ({"delivery_list", "delivery_date"}, ("delivery_list", "reset", "delete_delivery")),
            "manualEdit": ({"line_item", "manual_delivery_entry", "admin_lookup_value"}, ("manual_edit", "manual_location", "create_manual", "delete_line_item")),
            "users": ({"user", "session"}, ("user", "password", "session")),
            "roles": ({"role", "permission"}, ("role", "permission")),
            "sessions": ({"session", "user"}, ("session", "login", "logout")),
            "stations": ({"station"}, ("station",)),
            "customerRoutes": ({"customer_route_rule"}, ("customer_route",)),
            "customerEmails": ({"customer_email", "email_outbox", "email_cc"}, ("customer_email", "email_", "smtp")),
            "lookups": ({"admin_lookup_value"}, ("lookup",)),
            "rejectSettings": ({"reject_catalog"}, ("reject_catalog",)),
            "bayScannerRules": ({"bay_manual_input_rule", "bay_scan_barcode_rule", "bay_scanner_settings"}, ("bay_manual", "bay_scan_barcode", "rack_destination_override")),
            "crossDateScanning": ({"cross_date_scan_settings", "scan", "line_item"}, ("cross_date_scan_", "update_cross_date_scan_settings")),
            "bayAutoAssigner": ({"bay_auto_assigner"}, ("bay_auto_assign",)),
            "racks": ({"rack", "rack_set"}, ("rack",)),
            "rackForm": ({"rack"}, ("rack",)),
            "rackSetForm": ({"rack_set", "rack"}, ("rack_set",)),
            "recentScans": ({"scan", "line_item", "rack", "bay"}, ("scan", "manual_location")),
            "rack-details": ({"rack", "rack_item", "packing_list_print"}, ("rack", "packing_list", "outbound_override_transportation")),
            "racks-history": ({"rack", "rack_item", "rack_set", "packing_list_print"}, ("rack", "packing_list", "outbound_override_transportation")),
            "packing-history": ({"packing_list_print"}, ("packing_list",)),
            "oldBays": ({"bay_assignment", "bay"}, ("snooze_stale_bay", "bay_check_")),
            "rush": ({"line_item", "bay_assignment"}, ("mark_rush", "clear_rush_priority", "remove_rush_preassign", "remove_sdi")),
            "manageBayItems": ({"bay_assignment", "bay"}, ("move_bay", "clear_bay_assignment", "restore_bay_assignment", "assign_bay")),
            "editBays": ({"bay", "bay_group"}, ("create_bays", "delete_bay", "delete_bay_group", "move_bay_group", "set_bay_", "update_bay_layout")),
        }
        exact_action_contexts: dict[str, set[str]] = {
            "oldBays": {"snooze_stale_bay", "bay_check_empty", "bay_check_needs_review", "bay_check_still_occupied"},
            "manageBayItems": {"move_bay", "clear_bay_assignment", "restore_bay_assignment", "assign_bay"},
            "racks": {"upsert_rack", "create_rack_set", "delete_rack"},
            "rackForm": {"upsert_rack", "delete_rack"},
            "rackSetForm": {"create_rack_set"},
        }
        entity_types, action_prefixes = context_rules.get(context_key, (set(), tuple()))
        return entity_types, action_prefixes, exact_action_contexts.get(context_key)

    @staticmethod
    def _gui_history_event_rack_codes(event: dict[str, Any]) -> set[str]:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        values: list[Any] = []
        if str(event.get("entityType") or "") == "rack":
            values.extend(re.split(r"[;,|]+", str(event.get("entityId") or "")))
        for key in ("rackCode", "sourceRackCode", "targetRackCode", "oldCode"):
            if payload.get(key):
                values.append(payload.get(key))
        for key in ("rackCodes", "createdRackCodes", "affectedRackCodes"):
            value = payload.get(key)
            if isinstance(value, list):
                values.extend(value)
        return {
            normalize_rack_code(str(value or ""))
            for value in values
            if normalize_rack_code(str(value or ""))
        }

    def _gui_history_context_matches(
        self,
        event: dict[str, Any],
        context_key: str,
        requested_rack_code: str = "",
        allowed_rack_codes: set[str] | None = None,
    ) -> bool:
        entity_types, action_prefixes, exact_actions = self._gui_action_history_rules(context_key)
        entity_type = str(event.get("entityType") or "")
        action = str(event.get("action") or "")
        action_matches = action in exact_actions if exact_actions is not None else bool(
            action_prefixes and any(prefix in action for prefix in action_prefixes)
        )
        entity_matches = bool(not action_prefixes and entity_types and entity_type in entity_types)
        if not (action_matches or entity_matches):
            return False
        event_racks = self._gui_history_event_rack_codes(event)
        if context_key == "rack-details" and requested_rack_code and requested_rack_code not in event_racks:
            return False
        if allowed_rack_codes is not None and not (event_racks & allowed_rack_codes):
            return False
        return True

    @staticmethod
    def _gui_history_filter_matches(
        event: dict[str, Any],
        query: str = "",
        user: str = "",
        action: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> bool:
        event_user = str(event.get("user") or "system")
        event_action = str(event.get("action") or "")
        event_date = str(event.get("createdAt") or "")[:10]
        if user and event_user != user:
            return False
        if action and event_action != action:
            return False
        if date_from and (not event_date or event_date < date_from):
            return False
        if date_to and (not event_date or event_date > date_to):
            return False
        clean_query = str(query or "").strip().lower()
        if not clean_query:
            return True
        searchable = " ".join(
            [
                event_action,
                event_user,
                str(event.get("entityType") or ""),
                str(event.get("entityId") or ""),
                str(event.get("station") or ""),
                str(event.get("reason") or ""),
                json.dumps(event.get("payload") or {}, sort_keys=True),
                str(event.get("createdAt") or ""),
            ]
        ).lower()
        return clean_query in searchable

    def list_gui_action_history_page(
        self,
        context: str,
        page: int = 1,
        page_size: int = ACTION_HISTORY_PAGE_SIZE,
        rack_code: str = "",
        query: str = "",
        user: str = "",
        action: str = "",
        date_from: str = "",
        date_to: str = "",
        rack_codes: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Return one filtered page of active action history for a maintained GUI."""
        context_key = str(context or "").strip()
        clean_page = max(1, int(page or 1))
        clean_page_size = max(1, min(int(page_size or ACTION_HISTORY_PAGE_SIZE), ACTION_HISTORY_PAGE_SIZE))
        requested_rack_code = normalize_rack_code(rack_code) if rack_code else ""
        allowed_rack_codes = None
        if rack_codes is not None:
            allowed_rack_codes = {
                normalize_rack_code(str(value or ""))
                for value in rack_codes
                if normalize_rack_code(str(value or ""))
            }
        cutoff = (datetime.now(timezone.utc) - timedelta(days=ACTION_HISTORY_RETENTION_DAYS)).isoformat(timespec="seconds")
        start_index = (clean_page - 1) * clean_page_size
        stop_index = start_index + clean_page_size
        matched_events: list[dict[str, Any]] = []
        total_count = 0
        users: set[str] = set()
        actions: set[str] = set()
        batch_size = 500
        offset = 0

        with self.connect() as con:
            self._archive_old_audit_events(con, cutoff)
            while True:
                rows = con.execute(
                    """
                    SELECT id, entity_type, entity_id, action, user_name, station, reason, payload_json, created_at
                    FROM audit_events
                    WHERE created_at >= ?
                    ORDER BY id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (cutoff, batch_size, offset),
                ).fetchall()
                if not rows:
                    break
                for row in rows:
                    event = self._audit_event_dict(row)
                    if not self._gui_history_context_matches(
                        event,
                        context_key,
                        requested_rack_code=requested_rack_code,
                        allowed_rack_codes=allowed_rack_codes,
                    ):
                        continue
                    users.add(str(event.get("user") or "system"))
                    actions.add(str(event.get("action") or ""))
                    if not self._gui_history_filter_matches(
                        event,
                        query=query,
                        user=user,
                        action=action,
                        date_from=date_from,
                        date_to=date_to,
                    ):
                        continue
                    if start_index <= total_count < stop_index:
                        matched_events.append(event)
                    total_count += 1
                if len(rows) < batch_size:
                    break
                offset += batch_size

        total_pages = max(1, (total_count + clean_page_size - 1) // clean_page_size)
        if clean_page > total_pages:
            return self.list_gui_action_history_page(
                context=context_key,
                page=total_pages,
                page_size=clean_page_size,
                rack_code=requested_rack_code,
                query=query,
                user=user,
                action=action,
                date_from=date_from,
                date_to=date_to,
                rack_codes=allowed_rack_codes,
            )
        return {
            "context": context_key,
            "rackCode": requested_rack_code,
            "events": matched_events,
            "page": clean_page,
            "pageSize": clean_page_size,
            "totalCount": total_count,
            "totalPages": total_pages,
            "users": sorted(users, key=lambda value: value.lower()),
            "actions": sorted((value for value in actions if value), key=lambda value: value.lower()),
            "retentionDays": ACTION_HISTORY_RETENTION_DAYS,
            "archivedBefore": cutoff[:10],
        }

    def list_gui_action_history(
        self,
        context: str,
        limit: int = 20,
        rack_code: str = "",
    ) -> list[dict[str, Any]]:
        """Backward-compatible first-page action-history reader."""
        payload = self.list_gui_action_history_page(
            context=context,
            page=1,
            page_size=min(max(int(limit or 20), 1), ACTION_HISTORY_PAGE_SIZE),
            rack_code=rack_code,
        )
        return list(payload.get("events") or [])

    def get_email_outbox_item(self, email_id: int) -> dict[str, Any]:
        """Purpose: Read email outbox item for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            row = con.execute("SELECT * FROM email_outbox WHERE id = ?", (int(email_id),)).fetchone()
        if not row:
            raise ValueError("Email draft not found")
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        return {
            "id": row["id"],
            "emailType": row["email_type"],
            "customerName": row["customer_name"],
            "customerPattern": row["customer_pattern"],
            "deliveryDate": row["delivery_date"],
            "toEmails": json.loads(row["to_emails"] or "[]"),
            "ccEmails": json.loads(row["cc_emails"] or "[]"),
            "subject": row["subject"],
            "body": row["body"],
            "status": row["status"],
            "createdAt": row["created_at"],
            "sentAt": row["sent_at"],
            "error": row["error"],
            "payload": payload,
        }

    def bay_from_row(self, con: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        """Purpose: Run the bay from row workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        assignments = con.execute(
            """
            SELECT ba.*, li.order_no, li.item_no, li.qty, li.scanned_qty, li.customer,
                   li.dimensions, li.product, li.job, li.process_state, li.queue_state,
                   li.priority_delivery_date, li.priority_direct_to_truck,
                   dl.delivery_date, dl.stage, bss.snoozed_until,
                   (
                    SELECT se.created_at
                    FROM scan_events se
                    WHERE se.line_item_id = li.id AND se.qty_delta > 0
                    ORDER BY se.created_at DESC, se.id DESC
                    LIMIT 1
                   ) AS last_scanned_at,
                   (
                    SELECT se.station
                    FROM scan_events se
                    WHERE se.line_item_id = li.id AND se.qty_delta > 0
                    ORDER BY se.created_at DESC, se.id DESC
                    LIMIT 1
                   ) AS last_scanned_station
            FROM bay_assignments ba
            JOIN line_items li ON li.id = ba.line_item_id
            JOIN delivery_lists dl ON dl.id = li.list_id
            LEFT JOIN bay_stale_snoozes bss ON bss.assignment_id = ba.id
            WHERE ba.bay_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
            ORDER BY ba.assigned_at DESC
            """,
            (row["id"],),
        ).fetchall()
        assigned_qty = sum(int(item["assigned_qty"] or 0) for item in assignments)
        has_physical_assignment = any(str(item["status"] or "") not in {"PreAssigned"} for item in assignments)
        all_preassigned = bool(assignments) and not has_physical_assignment
        bay_status = str(row["status"] or "Available")
        if bay_status in {"Hold", "ManualAssign", "Blocked"}:
            status = "ManualAssign"
        elif bay_status in {"ScanBlocked", "BlockedAll"}:
            status = "ScanBlocked"
        elif any(item["status"] == "SDIOverride" for item in assignments):
            status = "SDI"
        elif assigned_qty == 0:
            status = "Empty"
        elif all_preassigned:
            status = "PreAssigned"
        elif row["capacity_qty"] and assigned_qty >= row["capacity_qty"]:
            status = "Full"
        elif len(assignments) > 1:
            status = "Partial"
        else:
            status = "Occupied"
        now = datetime.now(timezone.utc)
        today_key = now.date().isoformat()
        assignment_payload = []
        max_stale_days = 0
        any_new_today = False
        for item in assignments:
            assigned_at = str(item["assigned_at"] or "")
            try:
                assigned_dt = parse_iso(assigned_at)
                if assigned_dt.tzinfo is None:
                    assigned_dt = assigned_dt.replace(tzinfo=timezone.utc)
            except Exception:
                assigned_dt = now
            days_in_bay = max((now - assigned_dt).days, 0)
            snoozed_until = str(item["snoozed_until"] or "")
            snoozed = False
            if snoozed_until:
                try:
                    snooze_dt = parse_iso(snoozed_until)
                    if snooze_dt.tzinfo is None:
                        snooze_dt = snooze_dt.replace(tzinfo=timezone.utc)
                    snoozed = snooze_dt > now
                except Exception:
                    snoozed = False
            is_stale = days_in_bay > 10 and not snoozed
            is_new_today = assigned_at[:10] == today_key
            if is_stale:
                max_stale_days = max(max_stale_days, days_in_bay)
            any_new_today = any_new_today or is_new_today
            assignment_payload.append(
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
                    "deliveryDate": row_value(item, "priority_delivery_date") or item["delivery_date"],
                    "originalDeliveryDate": item["delivery_date"],
                    "priorityDirectToTruck": bool(row_value(item, "priority_direct_to_truck", 0)),
                    "lastStage": item["stage"],
                    "lastScannedAt": item["last_scanned_at"],
                    "lastScannedStation": item["last_scanned_station"],
                    "assignedAt": assigned_at,
                    "daysInBay": days_in_bay,
                    "isStale": is_stale,
                    "snoozedUntil": snoozed_until,
                    "isNewToday": is_new_today,
                    "status": item["status"],
                }
            )
        # `active` is a soft-delete flag for live-map visibility, not an assign-policy flag.
        # Older builds used active=0 for Hold/Blocked/Manual bays, which made those bays
        # disappear after the live-map filter was tightened. Keep Manual/Blocked policy bays
        # visible and only hide rows that were actually deleted.
        visible_policy_statuses = {"Hold", "ManualAssign", "Blocked", "ScanBlocked", "BlockedAll"}
        is_visible_live_bay = bool(row["active"]) or bay_status in visible_policy_statuses
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
            "active": is_visible_live_bay,
            "staleDays": max_stale_days,
            "isNewToday": any_new_today,
            "assignments": assignment_payload,
        }

    def get_bays(self) -> list[dict[str, Any]]:
        """Purpose: Read bays for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            # Deleted bays are soft-deactivated so old bay events remain intact.
            # Manual/blocked policy bays must still render on the live map even if
            # an older build stored them with active=0.
            rows = con.execute(
                """
                SELECT *
                FROM bays
                WHERE active = 1
                   OR COALESCE(status, '') IN ('Hold', 'ManualAssign', 'Blocked', 'ScanBlocked', 'BlockedAll')
                ORDER BY COALESCE(layout_col, 9999), COALESCE(layout_row, 9999), sort_order, bay_code
                """
            ).fetchall()
            return [self.bay_from_row(con, row) for row in rows]


    def get_bay_job_details(self, bay_code: str) -> dict[str, Any]:
        """Return live job fulfillment for one bay, including scan-in timestamps.

        Fulfillment is based on physical bay assignments, not the delivery-list
        received quantity. That distinction matters when a received item is
        scanned out and later returned to a bay.
        """
        clean_code = str(bay_code or "").strip()
        if not clean_code:
            raise ValueError("bayCode is required")

        with self.connect() as con:
            bay = con.execute("SELECT * FROM bays WHERE bay_code = ?", (clean_code,)).fetchone()
            if not bay:
                raise ValueError(f"Bay {clean_code} was not found")

            assignments = con.execute(
                """
                SELECT ba.*, li.order_no, li.item_no, li.qty, li.scanned_qty, li.customer,
                       li.dimensions, li.product, li.job, dl.delivery_date
                FROM bay_assignments ba
                JOIN line_items li ON li.id = ba.line_item_id
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE ba.bay_id = ? AND ba.status NOT IN ('Cleared', 'Cancelled')
                ORDER BY ba.assigned_at DESC, ba.id DESC
                """,
                (bay["id"],),
            ).fetchall()

            assignment_by_line: dict[str, sqlite3.Row] = {}
            for assignment in assignments:
                assignment_by_line.setdefault(str(assignment["line_item_id"]), assignment)

            job_details: list[dict[str, Any]] = []
            seen_job_keys: set[tuple[str, str]] = set()

            for assignment in assignments:
                delivery_list_id = str(assignment["delivery_list_id"] or "")
                job_value = str(assignment["job"] or "").strip()
                order_value = str(assignment["order_no"] or "").strip()
                group_value = job_value if job_value else f"ORDER:{order_value}"
                group_key = (delivery_list_id, group_value.lower())
                if group_key in seen_job_keys:
                    continue
                seen_job_keys.add(group_key)

                if job_value:
                    group_rows = con.execute(
                        """
                        SELECT * FROM line_items
                        WHERE list_id = ? AND TRIM(COALESCE(job, '')) = ?
                        ORDER BY CAST(order_no AS INTEGER), CAST(item_no AS INTEGER), id
                        """,
                        (delivery_list_id, job_value),
                    ).fetchall()
                else:
                    group_rows = con.execute(
                        """
                        SELECT * FROM line_items
                        WHERE list_id = ? AND order_no = ?
                        ORDER BY CAST(order_no AS INTEGER), CAST(item_no AS INTEGER), id
                        """,
                        (delivery_list_id, order_value),
                    ).fetchall()

                required_qty = sum(max(int(row["qty"] or 0), 0) for row in group_rows)
                in_bay_qty = 0
                latest_scan_in = ""
                all_items: list[dict[str, Any]] = []
                missing_items: list[dict[str, Any]] = []

                for row in group_rows:
                    needed_qty = max(int(row["qty"] or 0), 0)
                    current_assignment = assignment_by_line.get(str(row["id"]))
                    assignment_status = str(current_assignment["status"] or "") if current_assignment else ""
                    physically_in_bay = bool(current_assignment) and assignment_status not in {
                        "PreAssigned",
                        "Cancelled",
                        "Cleared",
                    }
                    present_qty = (
                        min(max(int(current_assignment["assigned_qty"] or 0), 0), needed_qty)
                        if physically_in_bay
                        else 0
                    )
                    missing_qty = max(needed_qty - present_qty, 0)
                    scanned_into_bay_at = (
                        str(current_assignment["assigned_at"] or "") if physically_in_bay else ""
                    )
                    if scanned_into_bay_at and scanned_into_bay_at > latest_scan_in:
                        latest_scan_in = scanned_into_bay_at
                    in_bay_qty += present_qty

                    item_payload = {
                        "lineItemId": row["id"],
                        "assignmentId": int(current_assignment["id"]) if current_assignment else 0,
                        "order": row["order_no"],
                        "item": row["item_no"],
                        "qty": needed_qty,
                        "inBayQty": present_qty,
                        "missingQty": missing_qty,
                        "dimensions": row["dimensions"],
                        "product": row["product"],
                        "customer": row["customer"],
                        "bayStatus": assignment_status,
                        "scannedIntoBayAt": scanned_into_bay_at,
                        "complete": missing_qty == 0,
                    }
                    all_items.append(item_payload)
                    if missing_qty > 0:
                        missing_items.append(item_payload)

                job_details.append(
                    {
                        "key": f"job:{job_value.lower()}" if job_value else f"order:{order_value}",
                        "job": job_value or order_value,
                        "customer": str(assignment["customer"] or ""),
                        "deliveryListId": delivery_list_id,
                        "deliveryDate": str(assignment["delivery_date"] or ""),
                        "requiredQty": required_qty,
                        "inBayQty": in_bay_qty,
                        "missingQty": max(required_qty - in_bay_qty, 0),
                        "complete": required_qty > 0 and in_bay_qty >= required_qty,
                        "lastScannedIntoBayAt": latest_scan_in,
                        "items": all_items,
                        "missingItems": missing_items,
                    }
                )

        return {"bayCode": clean_code, "jobDetails": job_details}
    def get_bay_layout(self) -> dict[str, Any]:
        """Purpose: Read bay layout for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        layout_path = self.config.root / "data" / "indian-trail-bay-layout.json"
        if not layout_path.exists():
            return {"bays": [], "cells": [], "sections": [], "grid": {"minRow": 1, "maxRow": 1, "minCol": 1, "maxCol": 1}}
        return json.loads(layout_path.read_text(encoding="utf-8"))


    def _bay_event_retention_cutoff(self, retention_days: int = BAY_EVENT_RETENTION_DAYS) -> str:
        """Return the UTC cutoff used by Bay Map history cleanup and reads."""
        safe_days = max(int(retention_days or BAY_EVENT_RETENTION_DAYS), 1)
        return (datetime.now(timezone.utc) - timedelta(days=safe_days)).isoformat(timespec="seconds")

    def cleanup_old_bay_events(
        self,
        retention_days: int = BAY_EVENT_RETENTION_DAYS,
        *,
        force: bool = False,
    ) -> int:
        """Delete only expired Bay Map movement activity.

        Scan events, audit events, rack history, reject history, and import history
        are intentionally unaffected. Cleanup is throttled during normal requests
        and forced once at application startup.
        """
        now_tick = time.monotonic()
        last_cleanup = float(getattr(self, "_last_bay_event_cleanup_monotonic", 0.0) or 0.0)
        if not force and now_tick - last_cleanup < BAY_EVENT_CLEANUP_INTERVAL_SECONDS:
            return 0
        cutoff = self._bay_event_retention_cutoff(retention_days)
        with self.connect() as con:
            cursor = con.execute("DELETE FROM bay_events WHERE created_at < ?", (cutoff,))
            con.commit()
            deleted = max(int(getattr(cursor, "rowcount", 0) or 0), 0)
        self._last_bay_event_cleanup_monotonic = now_tick
        return deleted

    def _select_bay_event_rows(self, con: Any, cutoff: str, limit: int) -> list[Any]:
        """Read the newest retained physical movement rows with current location data."""
        return con.execute(
            """
            SELECT be.*,
                   b.bay_code AS bay_code,
                   b.display_name AS bay_display,
                   old_bay.bay_code AS old_bay_code,
                   old_bay.display_name AS old_bay_display,
                   new_bay.bay_code AS new_bay_code,
                   new_bay.display_name AS new_bay_display,
                   li.order_no, li.item_no, li.customer, li.dimensions, li.product, li.job,
                   current_ba.id AS current_assignment_id,
                   current_bay.bay_code AS current_bay_code,
                   current_bay.display_name AS current_bay_display
            FROM bay_events be
            LEFT JOIN bays b ON b.id = be.bay_id
            LEFT JOIN bays old_bay ON old_bay.id = be.old_bay_id
            LEFT JOIN bays new_bay ON new_bay.id = be.new_bay_id
            LEFT JOIN line_items li ON li.id = be.line_item_id
            LEFT JOIN bay_assignments current_ba ON current_ba.id = (
                SELECT ba2.id
                FROM bay_assignments ba2
                WHERE ba2.line_item_id = be.line_item_id
                  AND ba2.status NOT IN ('Cleared', 'Cancelled')
                ORDER BY ba2.id DESC
                LIMIT 1
            )
            LEFT JOIN bays current_bay ON current_bay.id = current_ba.bay_id
            WHERE COALESCE(be.line_item_id, '') <> ''
              AND be.event_type NOT IN ('UpdateBayLayout', 'CreateBay', 'DeleteBay', 'DeleteBayGroup')
              AND be.created_at >= ?
            ORDER BY be.id DESC
            LIMIT ?
            """,
            (cutoff, max(int(limit or 1), 1)),
        ).fetchall()

    def _serialize_bay_event_rows(self, rows: list[Any]) -> list[dict[str, Any]]:
        """Convert retained Bay Map rows into the existing browser payload shape."""
        return [
            {
                "id": row["id"],
                "lineItemId": row["line_item_id"] or "",
                "eventType": row["event_type"],
                "bayCode": row["bay_code"] or "",
                "bayDisplay": row["bay_display"] or row["bay_code"] or "",
                "oldBayCode": row["old_bay_code"] or "",
                "oldBayDisplay": row["old_bay_display"] or row["old_bay_code"] or "",
                "newBayCode": row["new_bay_code"] or "",
                "newBayDisplay": row["new_bay_display"] or row["new_bay_code"] or "",
                "assignmentId": int(row["current_assignment_id"] or 0),
                "currentBayCode": row["current_bay_code"] or "",
                "currentBayDisplay": row["current_bay_display"] or row["current_bay_code"] or "",
                "order": row["order_no"] or "",
                "item": row["item_no"] or "",
                "job": row["job"] or "",
                "customer": row["customer"] or "",
                "dimensions": row["dimensions"] or "",
                "product": row["product"] or "",
                "reason": row["reason"] or "",
                "user": row["user_name"] or "",
                "time": row["created_at"],
            }
            for row in rows
        ]

    def get_bay_events(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """Return a bounded retained Bay Map history slice for compact scanner views."""
        self.cleanup_old_bay_events()
        safe_limit = max(1, min(int(limit or 20), 250))
        safe_offset = max(int(offset or 0), 0)
        cutoff = self._bay_event_retention_cutoff()
        with self.connect() as con:
            rows = self._select_bay_event_rows(con, cutoff, safe_offset + safe_limit)
        return self._serialize_bay_event_rows(list(rows)[safe_offset:safe_offset + safe_limit])

    def get_bay_events_page(self, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """Return one fast server-side page of Bay Map activity.

        The browser never receives more than 25 rows. Only the retained seven-day
        window is counted or rendered, so opening All Scans remains predictable.
        """
        deleted = self.cleanup_old_bay_events()
        safe_page_size = max(1, min(int(page_size or 25), 25))
        safe_page = max(int(page or 1), 1)
        cutoff = self._bay_event_retention_cutoff()
        with self.connect() as con:
            total_row = con.execute(
                """
                SELECT COUNT(*) AS total
                FROM bay_events be
                WHERE COALESCE(be.line_item_id, '') <> ''
                  AND be.event_type NOT IN ('UpdateBayLayout', 'CreateBay', 'DeleteBay', 'DeleteBayGroup')
                  AND be.created_at >= ?
                """,
                (cutoff,),
            ).fetchone()
            total = int(row_value(total_row, "total", 0) or 0)
            total_pages = max((total + safe_page_size - 1) // safe_page_size, 1)
            safe_page = min(safe_page, total_pages)
            offset = (safe_page - 1) * safe_page_size
            rows = self._select_bay_event_rows(con, cutoff, offset + safe_page_size)
        events = self._serialize_bay_event_rows(list(rows)[offset:offset + safe_page_size])
        return {
            "events": events,
            "page": safe_page,
            "pageSize": safe_page_size,
            "total": total,
            "totalPages": total_pages,
            "retentionDays": BAY_EVENT_RETENTION_DAYS,
            "deletedExpired": deleted,
        }

    def claim_stale_bay_alert(self, username: str, order_count: int, interval_hours: int = 6) -> dict[str, Any]:
        """Atomically claim the old-bay attention notice window for one signed-in user.

        Effects: Stores only the last-shown UTC timestamp in existing system metadata.
        Flow: Returns ``shouldNotify`` only when old orders exist and the user's prior
        notice is absent or at least the requested interval old. No schema change is needed.
        """
        clean_username = re.sub(r"[^a-z0-9_.@-]+", "-", str(username or "user").strip().lower()).strip("-") or "user"
        safe_count = max(int(order_count or 0), 0)
        safe_hours = max(1, min(int(interval_hours or 6), 168))
        now = datetime.now(timezone.utc)
        metadata_key = f"stale_bay_alert_last_shown:{clean_username}"
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            previous_text = self.system_metadata_value(con, metadata_key)
            previous = None
            if previous_text:
                try:
                    previous = parse_utc_timestamp(previous_text)
                except Exception:
                    previous = None
            should_notify = bool(safe_count) and (
                previous is None or now - previous >= timedelta(hours=safe_hours)
            )
            shown_at = previous_text
            if should_notify:
                shown_at = now.isoformat(timespec="seconds")
                self.set_system_metadata_value(con, metadata_key, shown_at)
            con.commit()
        return {
            "shouldNotify": should_notify,
            "orderCount": safe_count,
            "intervalHours": safe_hours,
            "lastShownAt": shown_at or "",
        }

    def get_stale_bay_orders(self, include_snoozed: bool = False) -> list[dict[str, Any]]:
        """Purpose: Read stale bay orders for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        now = datetime.now(timezone.utc)
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT ba.id AS assignment_id, ba.assigned_at, ba.assigned_qty, ba.status AS assignment_status,
                       b.bay_code, b.display_name AS bay_display, b.map_section, b.bay_category,
                       li.order_no, li.item_no, li.customer, li.dimensions, li.product, li.job,
                       dl.delivery_date, dl.stage,
                       bss.snoozed_until,
                       (
                        SELECT se.created_at
                        FROM scan_events se
                        WHERE se.line_item_id = li.id AND se.qty_delta > 0
                        ORDER BY se.created_at DESC, se.id DESC
                        LIMIT 1
                       ) AS last_scanned_at
                FROM bay_assignments ba
                JOIN bays b ON b.id = ba.bay_id
                JOIN line_items li ON li.id = ba.line_item_id
                JOIN delivery_lists dl ON dl.id = li.list_id
                LEFT JOIN bay_stale_snoozes bss ON bss.assignment_id = ba.id
                WHERE ba.status NOT IN ('Cleared', 'Cancelled')
                ORDER BY ba.assigned_at ASC, b.bay_code
                """
            ).fetchall()
        result = []
        for row in rows:
            assigned_at = str(row["assigned_at"] or "")
            try:
                assigned_dt = parse_iso(assigned_at)
                if assigned_dt.tzinfo is None:
                    assigned_dt = assigned_dt.replace(tzinfo=timezone.utc)
            except Exception:
                assigned_dt = now
            days_old = max((now - assigned_dt).days, 0)
            if days_old <= 10:
                continue
            snoozed_until = str(row["snoozed_until"] or "")
            if snoozed_until and not include_snoozed:
                try:
                    snooze_dt = parse_iso(snoozed_until)
                    if snooze_dt.tzinfo is None:
                        snooze_dt = snooze_dt.replace(tzinfo=timezone.utc)
                    if snooze_dt > now:
                        continue
                except Exception:
                    pass
            result.append(
                {
                    "assignmentId": row["assignment_id"],
                    "bayCode": row["bay_code"],
                    "bayDisplay": row["bay_display"] or row["bay_code"],
                    "mapSection": row["map_section"],
                    "bayCategory": row["bay_category"],
                    "order": row["order_no"],
                    "item": row["item_no"],
                    "customer": row["customer"],
                    "dimensions": row["dimensions"],
                    "product": row["product"],
                    "job": row["job"],
                    "qty": row["assigned_qty"],
                    "deliveryDate": row["delivery_date"],
                    "stage": row["stage"],
                    "assignedAt": assigned_at,
                    "lastScannedAt": row["last_scanned_at"],
                    "daysOld": days_old,
                    "snoozedUntil": snoozed_until,
                    "status": row["assignment_status"],
                }
            )
        return result

    def snooze_stale_bay_orders(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the snooze stale bay orders workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        ids = data.get("assignmentIds")
        if ids is None:
            ids = [data.get("assignmentId")]
        assignment_ids = [int(value) for value in ids if str(value or "").strip()]
        days = max(1, min(int(data.get("days") or 1), 365))
        snoozed_until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
        if not assignment_ids:
            raise ValueError("At least one stale bay assignment is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            for assignment_id in assignment_ids:
                con.execute(
                    """
                    INSERT INTO bay_stale_snoozes (assignment_id, snoozed_until, snoozed_by, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(assignment_id) DO UPDATE SET
                        snoozed_until = excluded.snoozed_until,
                        snoozed_by = excluded.snoozed_by,
                        updated_at = excluded.updated_at
                    """,
                    (assignment_id, snoozed_until, user, now_iso()),
                )
            self.insert_audit(con, "bay_assignment", ",".join(str(value) for value in assignment_ids), "snooze_stale_bay", user, "", f"Snoozed {days} day(s)", {"days": days})
            con.commit()
        return {"ok": True, "snoozedUntil": snoozed_until, "orders": self.get_stale_bay_orders()}

    def received_qty_for_rack_item(
        self,
        con: sqlite3.Connection,
        row: sqlite3.Row,
        destination: str,
    ) -> int:
        """Purpose: Run the received qty for rack item workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        clean_destination = self.rack_destination_value(destination)
        if clean_destination not in {"Indian Trail", "CPU", "Greenville", "DTC"}:
            return 0
        receipt_rows = con.execute(
            """
            SELECT recv.scanned_qty, recv_dl.stage, recv_dl.scanner
            FROM delivery_lists recv_dl
            JOIN line_items recv ON recv.list_id = recv_dl.id
            WHERE recv_dl.delivery_date = ?
              AND recv_dl.status = 'active'
              AND recv.scanned_qty > 0
              AND (
                (? <> '' AND recv.source_id = ?)
                OR (recv.order_no = ? AND recv.item_no = ?)
              )
            """,
            (
                row["delivery_date"],
                row["source_id"],
                row["source_id"],
                row["order_no"],
                row["item_no"],
            ),
        ).fetchall()
        received_qty = 0
        for receipt in receipt_rows:
            if receiving_stage_destination(receipt["stage"], receipt["scanner"]) != clean_destination:
                continue
            received_qty = max(received_qty, int(receipt["scanned_qty"] or 0))
        return min(max(int(row["rack_qty"] or 0), 0), received_qty)

    def rack_from_row(self, con: sqlite3.Connection, rack: sqlite3.Row) -> dict[str, Any]:
        """Purpose: Run the rack from row workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rows = con.execute(
            """
            SELECT ri.id AS rack_item_id, ri.qty AS rack_qty, ri.status AS rack_item_status,
                   ri.added_at, ri.added_by, li.*, dl.label AS delivery_label,
                   dl.delivery_date, dl.stage, dl.scanner
            FROM rack_items ri
            JOIN line_items li ON li.id = ri.line_item_id
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE ri.rack_id = ? AND ri.status = 'Active'
            ORDER BY ri.added_at DESC, CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER)
            """,
            (rack["id"],),
        ).fetchall()
        destination = (
            rack["destination"]
            if "destination" in rack.keys() and rack["destination"]
            else self.computed_rack_destination(con, rack["id"])
        )
        items = []
        received_qty = 0
        for row in rows:
            item_received_qty = self.received_qty_for_rack_item(con, row, destination)
            received_qty += item_received_qty
            item = item_from_row(row)
            item.update(
                {
                    "rackItemId": row["rack_item_id"],
                    "rackQty": row["rack_qty"],
                    "rackItemStatus": row["rack_item_status"],
                    "rackAddedAt": row["added_at"],
                    "rackAddedBy": row["added_by"],
                    "deliveryLabel": row["delivery_label"],
                    "deliveryDate": row["delivery_date"],
                    "stage": row["stage"],
                    "scanner": row["scanner"],
                    "receivedQty": item_received_qty,
                    "received": item_received_qty >= int(row["rack_qty"] or 0) and int(row["rack_qty"] or 0) > 0,
                }
            )
            items.append(item)
        qty = sum(int(item.get("rackQty") or item.get("qty") or 0) for item in items)
        is_received = (
            str(rack["status"] or "").strip().lower() == "in transit"
            and qty > 0
            and received_qty >= qty
        )
        return {
            "id": rack["id"],
            "code": rack["rack_code"],
            "barcode": f"RACK-{rack['rack_code']}",
            "name": rack["display_name"] or rack["rack_code"],
            "type": rack["rack_type"],
            "status": rack["status"],
            "destination": destination,
            "completedAt": rack["completed_at"] if "completed_at" in rack.keys() else "",
            "departedAt": rack["departed_at"] if "departed_at" in rack.keys() else "",
            "returnedAt": rack["returned_at"] if "returned_at" in rack.keys() else "",
            "active": bool(rack["active"]),
            "sortOrder": rack["sort_order"],
            "qty": qty,
            "receivedQty": received_qty,
            "received": is_received,
            "items": items,
        }

    def rack_summary(self, con: sqlite3.Connection) -> dict[str, Any]:
        """Purpose: Run the rack summary workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        row = con.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN r.rack_code = 'T' OR UPPER(COALESCE(r.rack_type, '')) = 'TRUCK' THEN ri.qty ELSE 0 END),0) AS truck_qty,
              COALESCE(SUM(CASE WHEN r.rack_code <> 'T' AND UPPER(COALESCE(r.rack_type, '')) <> 'TRUCK' THEN ri.qty ELSE 0 END),0) AS rack_qty,
              COUNT(DISTINCT CASE WHEN r.rack_code <> 'T' AND UPPER(COALESCE(r.rack_type, '')) <> 'TRUCK' AND ri.status = 'Active' THEN r.id END) AS rack_count
            FROM racks r
            LEFT JOIN rack_items ri ON ri.rack_id = r.id AND ri.status = 'Active'
            WHERE r.active = 1
            """
        ).fetchone()
        return {"truckQty": row["truck_qty"], "rackQty": row["rack_qty"], "rackCount": row["rack_count"]}

    def get_racks(self) -> dict[str, Any]:
        """Purpose: Read racks for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            self.seed_racks(con)
            racks = [self.rack_from_row(con, row) for row in con.execute("SELECT * FROM racks WHERE active = 1 ORDER BY sort_order, rack_code").fetchall()]
            return {"racks": racks, "summary": self.rack_summary(con)}

    def get_rack_by_code(self, con: sqlite3.Connection, code: str) -> sqlite3.Row:
        """Purpose: Read rack by code for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        rack_code = normalize_rack_code(code)
        row = con.execute("SELECT * FROM racks WHERE rack_code = ? AND active = 1", (rack_code,)).fetchone()
        if not row:
            raise ValueError(f"Rack {code} was not found")
        return row

    def apply_rack_destination_override_window(
        self,
        con: sqlite3.Connection,
        rack: sqlite3.Row,
        *,
        mismatch: bool,
        override_requested: bool,
        rack_destination: str,
        item_destination: str,
        user: str,
        station: str,
    ) -> tuple[bool, str, int]:
        """Start or reuse one rack's temporary mixed-destination scan window."""
        override_minutes = self.rack_destination_override_minutes_con(con)
        override_until = str(row_value(rack, "destination_override_until", "") or "")
        override_active = bool(mismatch and self.rack_destination_override_active(rack))
        if mismatch and override_requested:
            override_until = (datetime.now(timezone.utc) + timedelta(minutes=override_minutes)).isoformat(timespec="seconds")
            con.execute(
                "UPDATE racks SET destination_override_until = ?, destination_override_by = ?, updated_at = ? WHERE id = ?",
                (override_until, user, now_iso(), rack["id"]),
            )
            self.insert_audit(
                con,
                "rack",
                rack["rack_code"],
                "start_rack_destination_override_window",
                user,
                station,
                "",
                {
                    "minutes": override_minutes,
                    "expiresAt": override_until,
                    "rackDestination": rack_destination,
                    "itemDestination": item_destination,
                },
            )
            override_active = True
        return override_active, override_until, override_minutes

    def scan_item_to_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Process item to rack for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        list_id = str(data.get("listId") or "")
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        barcode = str(data.get("barcode") or "")
        station = request_station(data)
        if not list_id or not rack_code or not barcode.strip():
            raise ValueError("listId, rackCode, and barcode are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            list_row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            if not list_row or "staging" not in str(list_row["stage"]).lower():
                raise ValueError("Rack scans must be made from a staging delivery list")
            rack = self.get_rack_by_code(con, rack_code)
            rack_status = str(rack["status"] or "").lower()
            if rack_status == "closed":
                raise ValueError(f"Rack {rack['rack_code']} is closed. Uncomplete or clear it before scanning more pieces.")
            if rack_status == "in transit":
                raise ValueError(f"Rack {rack['rack_code']} is marked on the way. Mark it Not On The Way before scanning more pieces into it.")
            rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall()
            row, canonical, reason = self.recover_scan(barcode, rows)
            if row is None:
                last = self.insert_event(con, list_id, None, barcode, canonical, user, station, "error", "BAD RACK SCAN format", reason)
                con.commit()
                payload = self.get_racks()
                payload.update({"ok": False, "message": reason, "lastScan": last})
                return payload
            destination_override_requested = str(data.get("destinationOverride") or "").lower() in {"1", "true", "yes"}
            item_destination = self.destination_for_line_item(row)
            rack_destinations = self.rack_destinations_from_items(con, int(rack["id"]))
            rack_destination = rack_destinations[0] if len(rack_destinations) == 1 else self.rack_destination_value(rack["destination"])
            mismatch = bool(rack_destinations and rack_destinations != [item_destination])
            override_active, override_until, override_minutes = self.apply_rack_destination_override_window(
                con,
                rack,
                mismatch=mismatch,
                override_requested=destination_override_requested,
                rack_destination=rack_destination,
                item_destination=item_destination,
                user=user,
                station=station,
            )
            if mismatch and not destination_override_requested and not override_active:
                reason_text = (
                    f"Rack {rack['rack_code']} is assigned to {rack_destination}. "
                    f"This item is marked for {item_destination}."
                )
                last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "notice", "Rack destination mismatch", reason_text)
                con.commit()
                payload = self.get_racks()
                payload.update(
                    {
                        "ok": False,
                        "message": reason_text,
                        "lastScan": last,
                        "destinationOverrideRequired": True,
                        "destinationOverrideMinutes": override_minutes,
                        "destinationMismatch": {
                            "rackCode": rack["rack_code"],
                            "rackDestination": rack_destination,
                            "itemDestination": item_destination,
                            "order": row["order_no"],
                            "item": row["item_no"],
                            "customer": row["customer"],
                        },
                    }
                )
                return payload
            destination_override = rack_destination if mismatch else ""
            if row["scanned_qty"] < row["qty"]:
                con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
            con.execute(
                """
                INSERT INTO rack_items (
                    rack_id, line_item_id, qty, status, added_by, added_at,
                    reason, destination_override
                )
                VALUES (?, ?, 1, 'Active', ?, ?, ?, ?)
                ON CONFLICT(rack_id, line_item_id) DO UPDATE SET
                    qty = CASE
                        WHEN rack_items.status = 'Active' THEN MIN(rack_items.qty + 1, (SELECT qty FROM line_items WHERE id = excluded.line_item_id))
                        ELSE excluded.qty
                    END,
                    status = 'Active',
                    removed_by = '',
                    removed_at = '',
                    reason = excluded.reason,
                    destination_override = excluded.destination_override,
                    added_by = excluded.added_by,
                    added_at = excluded.added_at
                """,
                (
                    rack["id"],
                    row["id"],
                    user,
                    now_iso(),
                    "Scanned into rack with destination override" if destination_override else "Scanned into rack",
                    destination_override,
                ),
            )
            destination = self.refresh_rack_destination(con, rack["id"])
            last = self.insert_event(con, list_id, row["id"], barcode, canonical, user, station, "scan", f"Added to {rack['rack_code']}", f"{reason} Destination: {destination}".strip(), 1)
            self.insert_audit(con, "rack", rack["rack_code"], "rack_scan_in", user, station, reason, {"lineItemId": row["id"]})
            con.commit()
        payload = self.get_racks()
        message = f"Added {row['order_no']}-{row['item_no']} to {rack['rack_code']}"
        if mismatch and override_active:
            message += f". Mixed-destination override is active for {override_minutes} minutes"
        payload.update(
            {
                "ok": True,
                "message": message,
                "lastScan": last,
                "destinationOverrideActive": bool(mismatch and override_active),
                "destinationOverrideUntil": override_until if mismatch and override_active else "",
                "destinationOverrideMinutes": override_minutes,
            }
        )
        return payload

    def move_rack_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the move rack item workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rack_item_id = int(data.get("rackItemId") or 0)
        target_code = normalize_rack_code(str(data.get("targetRackCode") or data.get("rackCode") or ""))
        if not rack_item_id or not target_code:
            raise ValueError("rackItemId and targetRackCode are required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            target = self.get_rack_by_code(con, target_code)
            item = con.execute("SELECT * FROM rack_items WHERE id = ? AND status = 'Active'", (rack_item_id,)).fetchone()
            if not item:
                raise ValueError("Rack item not found")
            line_item = con.execute("SELECT * FROM line_items WHERE id = ?", (item["line_item_id"],)).fetchone()
            if not line_item:
                raise ValueError("Rack line item not found")
            self.validate_rack_destination_for_item(con, target, line_item)
            old_rack_id = item["rack_id"]
            source = con.execute("SELECT rack_code FROM racks WHERE id = ?", (old_rack_id,)).fetchone()
            source_rack_code = str(source["rack_code"] or "") if source else ""
            con.execute("UPDATE rack_items SET rack_id = ?, reason = 'Moved between racks' WHERE id = ?", (target["id"], rack_item_id))
            self.refresh_rack_destination(con, old_rack_id)
            self.refresh_rack_destination(con, target["id"])
            self.insert_audit(
                con,
                "rack_item",
                str(rack_item_id),
                "move_rack_item",
                user,
                "",
                "Moved between racks",
                {
                    "sourceRackCode": source_rack_code,
                    "targetRackCode": target["rack_code"],
                    "order": line_item["order_no"],
                    "item": line_item["item_no"],
                    "pieceQty": int(item["qty"] or 0),
                },
            )
            con.commit()
        return self.get_racks()

    def move_rack_contents(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Move every active item, or one complete delivery-date group, to another rack.

        The complete transfer is validated before the first row changes. Existing
        target rows for the same line item are merged safely instead of violating
        the rack-item uniqueness rule or creating duplicate active quantities.
        """
        source_code = normalize_rack_code(str(data.get("sourceRackCode") or ""))
        target_code = normalize_rack_code(str(data.get("targetRackCode") or ""))
        delivery_date = str(data.get("deliveryDate") or "").strip()
        if not source_code or not target_code:
            raise ValueError("sourceRackCode and targetRackCode are required")
        if source_code == target_code:
            raise ValueError("Choose a different destination rack")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            source = self.get_rack_by_code(con, source_code)
            target = self.get_rack_by_code(con, target_code)
            if str(source["status"] or "").strip().lower() == "in transit":
                raise ValueError("Return or mark the source rack Not On The Way before moving its contents")
            target_status = str(target["status"] or "Open").strip().lower()
            if target_status != "open":
                raise ValueError("Choose an open destination rack before moving contents")

            clauses = ["ri.rack_id = ?", "ri.status = 'Active'"]
            params: list[Any] = [source["id"]]
            if delivery_date:
                clauses.append("dl.delivery_date = ?")
                params.append(delivery_date)
            rows = con.execute(
                f"""
                SELECT ri.id AS rack_item_id, ri.line_item_id, ri.qty AS rack_qty,
                       ri.destination_override AS rack_destination_override,
                       li.*, dl.delivery_date
                FROM rack_items ri
                JOIN line_items li ON li.id = ri.line_item_id
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE {' AND '.join(clauses)}
                ORDER BY ri.id
                """,
                params,
            ).fetchall()
            if not rows:
                scope = f" for {delivery_date}" if delivery_date else ""
                raise ValueError(f"No active rack contents were found{scope}")

            transfer_plan: list[tuple[Any, Any | None, int]] = []
            for row in rows:
                self.validate_rack_destination_for_item(con, target, row)
                existing = con.execute(
                    """
                    SELECT id, qty, status
                    FROM rack_items
                    WHERE rack_id = ? AND line_item_id = ? AND id <> ?
                    """,
                    (target["id"], row["line_item_id"], row["rack_item_id"]),
                ).fetchone()
                source_qty = max(int(row["rack_qty"] or 0), 0)
                target_qty = (
                    max(int(existing["qty"] or 0), 0)
                    if existing and str(existing["status"] or "").lower() == "active"
                    else 0
                )
                combined_qty = source_qty + target_qty
                line_qty = max(int(row["qty"] or 0), 0)
                if line_qty and combined_qty > line_qty:
                    raise ValueError(
                        f"Order {row['order_no']} item {row['item_no']} would exceed its line quantity "
                        f"({combined_qty} of {line_qty}) on rack {target_code}."
                    )
                transfer_plan.append((row, existing, combined_qty))

            reason = f"Moved delivery date {delivery_date} between racks" if delivery_date else "Moved all contents between racks"
            moved_at = now_iso()
            merged_lines = 0
            for row, existing, combined_qty in transfer_plan:
                if existing:
                    merged_lines += 1
                    con.execute(
                        """
                        UPDATE rack_items
                        SET qty = ?, status = 'Active', added_by = ?, added_at = ?,
                            removed_by = '', removed_at = '', reason = ?, destination_override = ?
                        WHERE id = ?
                        """,
                        (
                            combined_qty,
                            user,
                            moved_at,
                            reason,
                            str(row["rack_destination_override"] or ""),
                            existing["id"],
                        ),
                    )
                    con.execute(
                        """
                        UPDATE rack_items
                        SET status = 'Removed', removed_by = ?, removed_at = ?, reason = ?
                        WHERE id = ?
                        """,
                        (user, moved_at, reason, row["rack_item_id"]),
                    )
                else:
                    con.execute(
                        "UPDATE rack_items SET rack_id = ?, reason = ? WHERE id = ?",
                        (target["id"], reason, row["rack_item_id"]),
                    )

            self.refresh_rack_destination(con, source["id"])
            self.refresh_rack_destination(con, target["id"])
            remaining = int(con.execute(
                "SELECT COUNT(*) FROM rack_items WHERE rack_id = ? AND status = 'Active'",
                (source["id"],),
            ).fetchone()[0] or 0)
            if remaining == 0:
                con.execute(
                    """
                    UPDATE racks
                    SET status = 'Open', completed_at = '', completed_by = '',
                        departed_at = '', departed_by = '', returned_at = '', returned_by = '',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (moved_at, source["id"]),
                )
            piece_qty = sum(int(row["rack_qty"] or 0) for row in rows)
            self.insert_audit(
                con, "rack", source_code, "move_rack_contents", user, "", reason,
                {
                    "sourceRackCode": source_code,
                    "targetRackCode": target_code,
                    "deliveryDate": delivery_date,
                    "lineCount": len(rows),
                    "pieceQty": piece_qty,
                    "mergedLineCount": merged_lines,
                },
            )
            con.commit()
        payload = self.get_racks()
        payload.update({
            "ok": True,
            "message": (
                f"Moved {piece_qty} piece{'s' if piece_qty != 1 else ''} across "
                f"{len(rows)} line{'s' if len(rows) != 1 else ''} from {source_code} to {target_code}."
            ),
            "movedCount": len(rows),
            "movedPieceQty": piece_qty,
            "mergedLineCount": merged_lines,
        })
        return payload

    def clear_rack_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove rack item for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        rack_item_id = int(data.get("rackItemId") or 0)
        if not rack_item_id:
            raise ValueError("rackItemId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            item = con.execute(
                """
                SELECT ri.*, r.rack_code, li.order_no, li.item_no
                FROM rack_items ri
                JOIN racks r ON r.id = ri.rack_id
                JOIN line_items li ON li.id = ri.line_item_id
                WHERE ri.id = ? AND ri.status = 'Active'
                """,
                (rack_item_id,),
            ).fetchone()
            if not item:
                raise ValueError("Rack item not found")
            con.execute(
                "UPDATE rack_items SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Individually cleared from rack' WHERE id = ?",
                (user, now_iso(), rack_item_id),
            )
            self.refresh_rack_destination(con, item["rack_id"])
            self.insert_audit(
                con,
                "rack_item",
                str(rack_item_id),
                "clear_rack_item",
                user,
                "",
                "Individually cleared from rack",
                {"rackCode": item["rack_code"], "order": item["order_no"], "item": item["item_no"]},
            )
            con.commit()
        return self.get_racks()

    def clear_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove rack for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, rack_code)
            con.execute("UPDATE rack_items SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Rack cleared' WHERE rack_id = ? AND status = 'Active'", (user, now_iso(), rack["id"]))
            con.execute("UPDATE racks SET status = 'Open', destination = '', completed_at = '', departed_at = '', returned_at = ?, updated_at = ? WHERE id = ?", (now_iso(), now_iso(), rack["id"]))
            self.insert_audit(con, "rack", rack["rack_code"], "clear_rack", user, "", "", {})
            con.commit()
        return self.get_racks()

    def rack_destination_value(self, value: Any) -> str:
        """Purpose: Run the rack destination value workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        text = str(value or "").strip()
        aliases = {
            "": "Indian Trail",
            "INDIAN TRAIL": "Indian Trail",
            "IT": "Indian Trail",
            "CPU": "CPU",
            "CUSTOMER PICKUP": "CPU",
            "GREENVILLE": "Greenville",
            "GNV": "Greenville",
            "DTC": "DTC",
            "DELIVER TO CUSTOMER": "DTC",
        }
        return aliases.get(text.upper(), text[:40] or "Indian Trail")

    def destination_for_line_item(self, item: Any) -> str:
        """Purpose: Run the destination for line item workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        source = {
            "route": row_value(item, "route"),
            "job": row_value(item, "job"),
            "customer": row_value(item, "customer"),
            "product": row_value(item, "product"),
            "processState": row_value(item, "processState") or row_value(item, "process_state"),
            "queueState": row_value(item, "queueState") or row_value(item, "queue_state"),
        }
        category = route_category(source)
        if category == "cpu":
            return "CPU"
        if category == "greenville":
            return "Greenville"
        if category == "dtc":
            return "DTC"
        if category.startswith("custom:"):
            return route_stage_label(category.split(":", 1)[1])
        return "Indian Trail"

    def rack_destinations_from_items(self, con: sqlite3.Connection, rack_id: int, extra_item: sqlite3.Row | dict[str, Any] | None = None) -> list[str]:
        """Purpose: Run the rack destinations from items workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rows = con.execute(
            """
            SELECT li.*, COALESCE(ri.destination_override, '') AS rack_destination_override
            FROM rack_items ri
            JOIN line_items li ON li.id = ri.line_item_id
            WHERE ri.rack_id = ?
              AND ri.status = 'Active'
            """,
            (rack_id,),
        ).fetchall()
        destinations = {
            self.rack_destination_value(row["rack_destination_override"])
            if str(row["rack_destination_override"] or "").strip()
            else self.destination_for_line_item(row)
            for row in rows
        }
        if extra_item is not None:
            destinations.add(self.destination_for_line_item(extra_item))
        return sorted(destination for destination in destinations if destination)

    def computed_rack_destination(self, con: sqlite3.Connection, rack_id: int) -> str:
        """Purpose: Run the computed rack destination workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        destinations = self.rack_destinations_from_items(con, rack_id)
        return destinations[0] if len(destinations) == 1 else ""

    def refresh_rack_destination(self, con: sqlite3.Connection, rack_id: int) -> str:
        """Refresh the rack destination and clear stale override windows on empty racks."""
        destination = self.computed_rack_destination(con, rack_id)
        if destination:
            con.execute("UPDATE racks SET destination = ?, updated_at = ? WHERE id = ?", (destination, now_iso(), rack_id))
        else:
            con.execute(
                "UPDATE racks SET destination = '', destination_override_until = '', destination_override_by = '', updated_at = ? WHERE id = ?",
                (now_iso(), rack_id),
            )
        return destination

    def rack_destination_override_active(self, rack: sqlite3.Row) -> bool:
        """Return True while a confirmed mixed-destination rack window remains active."""
        raw_until = str(row_value(rack, "destination_override_until", "") or "").strip()
        if not raw_until:
            return False
        try:
            return parse_utc_timestamp(raw_until) > datetime.now(timezone.utc)
        except (TypeError, ValueError):
            return False

    def validate_rack_destination_for_item(self, con: sqlite3.Connection, rack: sqlite3.Row, item: sqlite3.Row | dict[str, Any]) -> str:
        """Purpose: Validate rack destination for item for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        destination = self.destination_for_line_item(item)
        current_destinations = self.rack_destinations_from_items(con, int(rack["id"]))
        if current_destinations and current_destinations != [destination]:
            existing = ", ".join(current_destinations)
            raise ValueError(
                f"Rack {rack['rack_code']} is already assigned to {existing}. "
                f"This item is marked for {destination} and must go on a separate rack."
            )
        return destination

    def complete_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the complete rack workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, rack_code)
            active_count = con.execute("SELECT COUNT(*) FROM rack_items WHERE rack_id = ? AND status = 'Active'", (rack["id"],)).fetchone()[0]
            if not active_count:
                raise ValueError("Rack must have active pieces before it can be completed")
            destinations = self.rack_destinations_from_items(con, rack["id"])
            if len(destinations) != 1:
                raise ValueError("Rack destination could not be determined safely. Clear or split this rack before completing it.")
            destination = destinations[0]
            con.execute(
                "UPDATE racks SET status = 'Closed', destination = ?, completed_at = ?, departed_at = '', returned_at = '', updated_at = ? WHERE id = ?",
                (destination, now_iso(), now_iso(), rack["id"]),
            )
            self.insert_audit(con, "rack", rack["rack_code"], "complete_rack", user, "", "Rack closed with automatic destination from contents", {"destination": destination})
            con.commit()
        payload = self.get_racks()
        payload["message"] = f"Rack {rack_code} completed for {destination}."
        return payload

    def uncomplete_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the uncomplete rack workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, rack_code)
            con.execute("UPDATE racks SET status = 'Open', destination = '', completed_at = '', departed_at = '', updated_at = ? WHERE id = ?", (now_iso(), rack["id"]))
            self.insert_audit(con, "rack", rack["rack_code"], "uncomplete_rack", user, "", "Rack reopened for staging scans", {})
            con.commit()
        return self.get_racks()

    def return_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the return rack workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, rack_code)
            con.execute("UPDATE rack_items SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Rack returned and cleared' WHERE rack_id = ? AND status = 'Active'", (user, now_iso(), rack["id"]))
            con.execute("UPDATE racks SET status = 'Open', destination = '', completed_at = '', departed_at = '', returned_at = ?, updated_at = ? WHERE id = ?", (now_iso(), now_iso(), rack["id"]))
            self.insert_audit(con, "rack", rack["rack_code"], "return_rack", user, "", "Rack returned and reset for staging", {})
            con.commit()
        return self.get_racks()

    def not_on_way_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the not on way rack workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, rack_code)
            if str(rack["status"] or "").lower() != "in transit":
                raise ValueError("Only racks marked on the way can be marked Not On The Way")

            canonical = f"RACK-{rack['rack_code']}"
            outbound_rows = con.execute(
                """
                WITH rack_targets AS (
                    SELECT DISTINCT
                        out_li.id AS outbound_line_item_id,
                        out_li.list_id AS outbound_list_id
                    FROM rack_items ri
                    JOIN line_items src_li ON src_li.id = ri.line_item_id
                    JOIN delivery_lists src_dl ON src_dl.id = src_li.list_id
                    JOIN delivery_lists out_dl
                      ON out_dl.delivery_date = src_dl.delivery_date
                     AND out_dl.status = 'active'
                     AND LOWER(out_dl.stage) LIKE '%outbound%'
                    JOIN line_items out_li
                      ON out_li.list_id = out_dl.id
                     AND (
                        (src_li.source_id <> '' AND out_li.source_id = src_li.source_id)
                        OR (out_li.order_no = src_li.order_no AND out_li.item_no = src_li.item_no)
                     )
                    WHERE ri.rack_id = ?
                      AND ri.status = 'Active'
                )
                SELECT
                    rt.outbound_line_item_id,
                    rt.outbound_list_id,
                    li.scanned_qty AS scanned_qty,
                    COALESCE(SUM(se.qty_delta), 0) AS rack_outbound_qty
                FROM rack_targets rt
                JOIN line_items li ON li.id = rt.outbound_line_item_id
                LEFT JOIN scan_events se
                  ON se.line_item_id = rt.outbound_line_item_id
                 AND se.canonical_barcode = ?
                 AND se.qty_delta <> 0
                GROUP BY rt.outbound_line_item_id, rt.outbound_list_id, li.scanned_qty
                HAVING COALESCE(SUM(se.qty_delta), 0) > 0
                """,
                (rack["id"], canonical),
            ).fetchall()

            undone_piece_qty = 0
            undone_row_count = 0
            timestamp = now_iso()
            for row in outbound_rows:
                decrement = min(max(int(row["rack_outbound_qty"] or 0), 0), max(int(row["scanned_qty"] or 0), 0))
                if decrement <= 0:
                    continue
                con.execute(
                    "UPDATE line_items SET scanned_qty = MAX(scanned_qty - ?, 0) WHERE id = ?",
                    (decrement, row["outbound_line_item_id"]),
                )
                self.insert_event(
                    con,
                    row["outbound_list_id"],
                    row["outbound_line_item_id"],
                    canonical,
                    canonical,
                    user,
                    "",
                    "undo",
                    f"Rack {rack['rack_code']} marked Not On The Way",
                    "Outbound rack scan quantity was reversed so the rack can be reopened.",
                    -decrement,
                )
                undone_piece_qty += decrement
                undone_row_count += 1

            con.execute(
                "UPDATE racks SET status = 'Open', destination = '', completed_at = '', departed_at = '', updated_at = ? WHERE id = ?",
                (timestamp, rack["id"]),
            )
            self.insert_audit(
                con,
                "rack",
                rack["rack_code"],
                "rack_not_on_way",
                user,
                "",
                "Rack reopened and outbound rack scans reversed",
                {"undonePieceQty": undone_piece_qty, "undoneRowCount": undone_row_count},
            )
            con.commit()

        payload = self.get_racks()
        payload.update(
            {
                "ok": True,
                "message": f"Rack {rack['rack_code']} is open again. Reversed {undone_piece_qty} outbound piece scan{'s' if undone_piece_qty != 1 else ''}.",
                "undonePieceQty": undone_piece_qty,
                "undoneRowCount": undone_row_count,
            }
        )
        return payload

    def assign_line_item_to_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the assign line item to rack workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        line_item_id = str(data.get("lineItemId") or "").strip()
        rack_code = normalize_rack_code(str(data.get("rackCode") or ""))
        if not line_item_id:
            raise ValueError("lineItemId is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                """
                SELECT li.*, dl.delivery_date, dl.stage
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE li.id = ?
                """,
                (line_item_id,),
            ).fetchone()
            if not row:
                raise ValueError("Line item not found")
            target_row = row
            if "staging" not in str(row["stage"] or "").lower():
                mapped = con.execute(
                    """
                    SELECT li.*, dl.delivery_date, dl.stage
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.delivery_date = ?
                      AND LOWER(dl.stage) LIKE '%staging%'
                      AND (
                        li.source_id = ?
                        OR (li.order_no = ? AND li.item_no = ?)
                      )
                    ORDER BY dl.id
                    LIMIT 1
                    """,
                    (row["delivery_date"], row["source_id"], row["order_no"], row["item_no"]),
                ).fetchone()
                if mapped:
                    target_row = mapped
            if int(target_row["scanned_qty"] or 0) <= 0:
                raise ValueError("Only line items already scanned at Staging can be assigned to a rack")

            outbound_scan = con.execute(
                """
                SELECT outbound_item.id
                FROM delivery_lists outbound_list
                JOIN line_items outbound_item ON outbound_item.list_id = outbound_list.id
                WHERE outbound_list.delivery_date = ?
                  AND LOWER(outbound_list.stage) LIKE '%outbound%'
                  AND outbound_item.scanned_qty > 0
                  AND (
                    (? <> '' AND outbound_item.source_id = ?)
                    OR (outbound_item.order_no = ? AND outbound_item.item_no = ?)
                  )
                LIMIT 1
                """,
                (
                    target_row["delivery_date"],
                    target_row["source_id"],
                    target_row["source_id"],
                    target_row["order_no"],
                    target_row["item_no"],
                ),
            ).fetchone()
            if outbound_scan:
                raise ValueError("Rack location cannot be changed after this item has been scanned Outbound")

            current_rack = con.execute(
                """
                SELECT r.*
                FROM rack_items ri
                JOIN racks r ON r.id = ri.rack_id
                WHERE ri.line_item_id = ?
                  AND ri.status = 'Active'
                  AND r.active = 1
                ORDER BY CASE WHEN r.rack_code = 'T' THEN 9999 ELSE r.sort_order END, r.rack_code
                LIMIT 1
                """,
                (target_row["id"],),
            ).fetchone()
            if current_rack:
                current_status = str(current_rack["status"] or "").lower()
                if current_status in {"closed", "complete", "completed", "in transit", "on the way"}:
                    raise ValueError(f"Rack {current_rack['rack_code']} is {current_rack['status']} and cannot be changed from the scan table")

            if rack_code:
                rack = self.get_rack_by_code(con, rack_code)
                rack_status = str(rack["status"] or "").lower()
                if rack_status in {"closed", "complete", "completed", "in transit", "on the way"}:
                    raise ValueError(f"Rack {rack['rack_code']} must be open before assigning a line item to it")
            self.update_line_item_location(con, target_row, rack_code, user)
            payload = self._get_payload(con, target_row["list_id"])
            self.insert_audit(
                con,
                "line_item",
                target_row["id"],
                "rack_location_recovery",
                user,
                "",
                "Supervisor/Admin rack location assignment from scan table",
                {"rackCode": rack_code},
            )
            con.commit()
        racks_payload = self.get_racks()
        payload["racks"] = racks_payload.get("racks", [])
        payload["rackSummary"] = racks_payload.get("summary")
        return payload

    def update_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update rack for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        code = normalize_rack_code(str(data.get("rackCode") or data.get("code") or ""))
        old_code = normalize_rack_code(str(data.get("oldRackCode") or data.get("oldCode") or code))
        name = str(data.get("name") or data.get("displayName") or code).strip()[:80]
        rack_type = str(data.get("type") or data.get("rackType") or "Steel").strip()[:40]
        if not code:
            raise ValueError("Rack code is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute("SELECT id, rack_code FROM racks WHERE rack_code = ?", (old_code,)).fetchone() if old_code else None
            if existing:
                if old_code == "T" and code != "T":
                    raise ValueError("Truck rack code cannot be changed")
                if code != old_code:
                    conflict = con.execute("SELECT id FROM racks WHERE rack_code = ? AND id <> ?", (code, existing["id"])).fetchone()
                    if conflict:
                        raise ValueError(f"Rack code {code} already exists")
                con.execute(
                    "UPDATE racks SET rack_code = ?, display_name = ?, rack_type = ?, active = 1, updated_at = ? WHERE id = ?",
                    (code, name, rack_type, now_iso(), existing["id"]),
                )
            else:
                conflict = con.execute("SELECT id FROM racks WHERE rack_code = ?", (code,)).fetchone()
                if conflict:
                    con.execute("UPDATE racks SET display_name = ?, rack_type = ?, active = 1, updated_at = ? WHERE rack_code = ?", (name, rack_type, now_iso(), code))
                else:
                    sort_order = con.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM racks").fetchone()[0]
                    con.execute("INSERT INTO racks (rack_code, display_name, rack_type, status, active, sort_order, created_at) VALUES (?, ?, ?, 'Open', 1, ?, ?)", (code, name, rack_type, sort_order, now_iso()))
            self.insert_audit(con, "rack", code, "upsert_rack", user, old_code if old_code != code else "", "", {"name": name, "type": rack_type, "oldCode": old_code})
            con.commit()
        payload = self.get_racks()
        payload["rack"] = next((rack for rack in payload.get("racks", []) if rack.get("code") == code), None)
        return payload

    def create_rack_set(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Create rack set for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        prefix = re.sub(r"[^A-Za-z0-9]", "", str(data.get("prefix") or "")).upper()[:8]
        rack_type = str(data.get("type") or data.get("rackType") or prefix or "Rack").strip()[:40]
        name_root = str(data.get("nameRoot") or rack_type or prefix or "Rack").strip()[:60]
        count = max(1, min(int(data.get("count") or 1), 100))
        start = max(1, min(int(data.get("start") or 1), 999))
        if not prefix:
            raise ValueError("Rack set prefix is required")
        created_codes: list[str] = []
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            sort_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM racks").fetchone()[0] or 1)
            for offset in range(count):
                number = start + offset
                code = f"R{number}{prefix}" if len(prefix) <= 3 else f"{prefix}{number}"
                display = f"{name_root} {number}"
                existing = con.execute("SELECT id FROM racks WHERE rack_code = ?", (code,)).fetchone()
                if existing:
                    con.execute("UPDATE racks SET display_name = ?, rack_type = ?, active = 1, updated_at = ? WHERE rack_code = ?", (display, rack_type, now_iso(), code))
                else:
                    con.execute(
                        "INSERT INTO racks (rack_code, display_name, rack_type, status, active, sort_order, created_at) VALUES (?, ?, ?, 'Open', 1, ?, ?)",
                        (code, display, rack_type, sort_order + offset, now_iso()),
                    )
                created_codes.append(code)
            self.insert_audit(con, "rack", ",".join(created_codes), "create_rack_set", user, "", "", {"prefix": prefix, "type": rack_type, "count": count, "start": start})
            con.commit()
        payload = self.get_racks()
        payload["created"] = created_codes
        return payload

    def delete_rack(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove rack for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        code = normalize_rack_code(str(data.get("rackCode") or ""))
        if code == "T":
            raise ValueError("Truck cannot be deleted")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, code)
            active = con.execute("SELECT COUNT(*) FROM rack_items WHERE rack_id = ? AND status = 'Active'", (rack["id"],)).fetchone()[0]
            if active:
                raise ValueError("Clear or move the rack contents before deleting this rack")
            con.execute("UPDATE racks SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), rack["id"]))
            self.insert_audit(con, "rack", rack["rack_code"], "delete_rack", user, "", "", {})
            con.commit()
        return self.get_racks()

    def destination_address_for_rack(self, con: sqlite3.Connection, rack_payload: dict[str, Any]) -> dict[str, Any]:
        """Purpose: Run the destination address for rack workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        destination = self.rack_destination_value(rack_payload.get("destination") or "Indian Trail")

        if destination == "Indian Trail":
            return {"destination": destination, "address": INDIAN_TRAIL_DESTINATION_ADDRESS, "stops": []}
        if destination == "CPU":
            return {"destination": destination, "address": CPU_DESTINATION_ADDRESS, "stops": []}
        if destination == "Greenville":
            return {"destination": destination, "address": GREENVILLE_DESTINATION_ADDRESS, "stops": []}

        rules = con.execute(
            """
            SELECT customer_pattern, route, customer_address
            FROM customer_route_rules
            WHERE active = 1
              AND COALESCE(customer_address, '') <> ''
            ORDER BY route, customer_pattern
            """
        ).fetchall()
        stops: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for item in rack_payload.get("items") or []:
            signal = " ".join(str(item.get(key, "")) for key in ("customer", "job", "product", "route"))
            for rule in rules:
                if destination == "DTC" and self.rack_destination_value(rule["route"]) != "DTC":
                    continue
                if fuzzy_contains(signal, rule["customer_pattern"]):
                    key = (str(rule["customer_pattern"]), str(rule["customer_address"]))
                    if key not in seen:
                        seen.add(key)
                        stops.append(
                            {
                                "customer": str(rule["customer_pattern"]),
                                "address": str(rule["customer_address"]),
                            }
                        )
                    break

        if destination == "DTC":
            if len(stops) == 1:
                return {"destination": destination, "address": stops[0]["address"], "stops": stops}
            if len(stops) > 1:
                return {"destination": destination, "address": "Multiple DTC stops - see customer addresses below", "stops": stops}
            return {"destination": destination, "address": "No DTC customer address on file", "stops": []}

        return {"destination": destination, "address": "Address not configured", "stops": []}

    def rack_packing_list(self, rack_code: str, delivery_date: str = "") -> dict[str, Any]:
        """Purpose: Run the rack packing list workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        with self.connect() as con:
            rack = self.get_rack_by_code(con, rack_code)
            rack_payload = self.rack_from_row(con, rack)
            clean_date = str(delivery_date or "").strip()
            if clean_date:
                rack_payload["items"] = [item for item in rack_payload["items"] if str(item.get("deliveryDate") or "") == clean_date]
                rack_payload["qty"] = sum(int(item.get("rackQty") or item.get("qty") or 0) for item in rack_payload["items"])
                rack_payload["deliveryDate"] = clean_date
                rack_payload["deliveryLabel"] = format_display_date(clean_date)
                rack_payload["barcode"] = rack_barcode_text(rack_payload["code"], clean_date)
            rack_payload["destinationAddress"] = self.destination_address_for_rack(con, rack_payload)
            if self.rack_destination_value(rack_payload.get("destination")) == "DTC":
                rules = con.execute(
                    """
                    SELECT customer_pattern, customer_address
                    FROM customer_route_rules
                    WHERE active = 1
                      AND UPPER(route) IN ('DTC', 'DELIVER TO CUSTOMER')
                      AND COALESCE(customer_address, '') <> ''
                    ORDER BY customer_pattern
                    """
                ).fetchall()
                for item in rack_payload.get("items") or []:
                    signal = " ".join(str(item.get(key, "")) for key in ("customer", "job", "product", "route"))
                    item["destinationAddress"] = "No DTC customer address on file"
                    for rule in rules:
                        if fuzzy_contains(signal, rule["customer_pattern"]):
                            item["destinationAddress"] = str(rule["customer_address"])
                            item["destinationCustomerPattern"] = str(rule["customer_pattern"])
                            break
            return {"rack": rack_payload}

    def scan_rack_outbound(self, scan_request: dict[str, Any], rack_code: str) -> dict[str, Any]:
        """Purpose: Process rack outbound for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates the operation, applies scanner safety rules, updates quantities/history, and returns UI-ready feedback.
        """
        list_id = str(scan_request.get("listId") or "")
        barcode = str(scan_request.get("barcode") or "")
        parsed_rack_code, barcode_delivery_date = parse_rack_barcode(barcode)
        if parsed_rack_code:
            rack_code = parsed_rack_code
        requested_delivery_date = str(scan_request.get("deliveryDate") or barcode_delivery_date or "").strip()
        user = request_user_name(scan_request)
        station = request_station(scan_request)
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rack = self.get_rack_by_code(con, rack_code)
            list_row = con.execute("SELECT * FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            if requested_delivery_date or not list_row or "outbound" not in str(list_row["stage"]).lower():
                rack_date = con.execute(
                    """
                    SELECT src_dl.delivery_date
                    FROM rack_items ri
                    JOIN line_items src ON src.id = ri.line_item_id
                    JOIN delivery_lists src_dl ON src_dl.id = src.list_id
                    WHERE ri.rack_id = ? AND ri.status = 'Active'
                      AND (? = '' OR src_dl.delivery_date = ?)
                    ORDER BY src_dl.delivery_date DESC
                    LIMIT 1
                    """,
                    (rack["id"], requested_delivery_date, requested_delivery_date),
                ).fetchone()
                if not rack_date:
                    raise ValueError("Rack has no active pieces to scan outbound")
                list_row = con.execute(
                    """
                    SELECT *
                    FROM delivery_lists
                    WHERE delivery_date = ?
                      AND status = 'active'
                      AND LOWER(stage) LIKE '%outbound%'
                    ORDER BY id
                    LIMIT 1
                    """,
                    (requested_delivery_date or rack_date["delivery_date"],),
                ).fetchone()
                if not list_row:
                    raise ValueError("No outbound delivery list was found for this rack")
                list_id = list_row["id"]
            rows = con.execute(
                """
                SELECT out_li.*, ri.qty AS rack_qty
                FROM rack_items ri
                JOIN line_items src ON src.id = ri.line_item_id
                JOIN delivery_lists src_dl ON src_dl.id = src.list_id
                JOIN line_items out_li
                  ON out_li.list_id = ?
                 AND out_li.order_no = src.order_no
                 AND out_li.item_no = src.item_no
                WHERE ri.rack_id = ?
                  AND ri.status = 'Active'
                  AND src_dl.delivery_date = ?
                """,
                (list_id, rack["id"], list_row["delivery_date"]),
            ).fetchall()
            if not rows:
                last = self.insert_event(con, list_id, None, barcode, f"RACK-{rack['rack_code']}", user, station, "error", "Rack has no outbound items", "No active rack items matched this outbound list")
                con.commit()
                return self._get_payload(con, list_id, last)
            last = None
            scanned_count = 0
            capped_count = 0
            departure_timestamp = now_iso()
            effective_departure_timestamp = departure_timestamp
            for row in rows:
                remaining_qty = max(int(row["qty"] or 0) - int(row["scanned_qty"] or 0), 0)
                if remaining_qty <= 0:
                    continue
                rack_qty = max(int(row["rack_qty"] or 1), 1)
                delta = min(rack_qty, remaining_qty)
                if delta < rack_qty:
                    capped_count += 1
                con.execute("UPDATE line_items SET scanned_qty = scanned_qty + ? WHERE id = ?", (delta, row["id"]))
                self.preassign_bay_for_outbound(con, list_id, row, user, station)
                reason = "Rack barcode scanned"
                message = f"Outbound rack scan {rack['rack_code']}"
                if delta < rack_qty:
                    message = f"Partial outbound rack scan {rack['rack_code']}"
                    reason = f"Rack row quantity {rack_qty} capped to remaining quantity {remaining_qty}"
                last = self.insert_event(con, list_id, row["id"], barcode, f"RACK-{rack['rack_code']}", user, station, "scan", message, reason, delta)
                scanned_count += delta
            if scanned_count == 0:
                last = self.insert_event(con, list_id, None, barcode, f"RACK-{rack['rack_code']}", user, station, "duplicate", "Rack already scanned outbound", "All rack items were already complete")
                effective_departure_timestamp = str(rack["departed_at"] or departure_timestamp)
                con.execute(
                    "UPDATE racks SET status = 'In Transit', departed_at = ?, updated_at = ? WHERE id = ?",
                    (effective_departure_timestamp, departure_timestamp, rack["id"]),
                )
            else:
                con.execute(
                    "UPDATE racks SET status = 'In Transit', departed_at = ?, returned_at = '', updated_at = ? WHERE id = ?",
                    (departure_timestamp, departure_timestamp, rack["id"]),
                )
            self.insert_audit(
                con,
                "rack",
                rack["rack_code"],
                "rack_outbound_scan",
                user,
                station,
                "Rack barcode applied Outbound quantity, preassignment, and departure timestamp.",
                {"scannedCount": scanned_count, "cappedRows": capped_count, "departedAt": effective_departure_timestamp},
            )
            rack_snapshot = self.rack_from_row(con, self.get_rack_by_code(con, rack["rack_code"]))
            con.commit()
            payload = self._get_payload(con, list_id, last)
            payload["redirectListId"] = list_id
            cap_message = f" {capped_count} row{'s' if capped_count != 1 else ''} capped at remaining quantity." if capped_count else ""
            payload["message"] = f"Rack {rack['rack_code']} scanned outbound for {scanned_count} piece{'s' if scanned_count != 1 else ''}.{cap_message}"
            payload["rackDepartureAt"] = effective_departure_timestamp
            payload["rackCode"] = rack["rack_code"]
            payload["rackDestination"] = self.rack_destination_value(rack_snapshot.get("destination"))
            payload["rackPieceCount"] = int(rack_snapshot.get("qty") or 0)
            payload["outboundScannedQty"] = scanned_count
            return payload


    def active_indian_trail_list(self, con: sqlite3.Connection, delivery_date: str = "") -> sqlite3.Row | None:
        """Resolve the active Indian Trail list for one explicit dashboard date.

        Effects: Reads delivery-list metadata only.
        Flow: Uses the requested date when supplied; otherwise prefers today, then the nearest future list, then the latest past list.
        """
        clean_date = str(delivery_date or "").strip()
        if clean_date:
            return con.execute(
                """
                SELECT id, delivery_date, label, stage
                FROM delivery_lists
                WHERE delivery_date = ?
                  AND stage LIKE '%Indian Trail%'
                  AND status = 'active'
                ORDER BY id
                LIMIT 1
                """,
                (clean_date,),
            ).fetchone()
        today = datetime.now(timezone.utc).date().isoformat()
        return con.execute(
            """
            SELECT id, delivery_date, label, stage
            FROM delivery_lists
            WHERE stage LIKE '%Indian Trail%' AND status = 'active'
            ORDER BY
                CASE
                    WHEN delivery_date = ? THEN 0
                    WHEN delivery_date > ? THEN 1
                    ELSE 2
                END,
                CASE WHEN delivery_date >= ? THEN delivery_date END ASC,
                delivery_date DESC,
                id
            LIMIT 1
            """,
            (today, today, today),
        ).fetchone()

    def active_indian_trail_lists(self, con: sqlite3.Connection, delivery_date: str = "") -> tuple[str, list[sqlite3.Row]]:
        """Return every active Indian Trail list for one resolved delivery date.

        Effects: Reads delivery-list metadata only.
        Flow: Resolves the requested/current dashboard date through the existing primary-list
        selector, then returns every active Indian Trail list for that same date. Keeping all
        matching lists prevents updated or split delivery-list files from hiding physical glass
        that belongs to the same day.
        """
        primary = self.active_indian_trail_list(con, delivery_date)
        if not primary:
            return "", []
        resolved_date = str(primary["delivery_date"] or "")
        rows = con.execute(
            """
            SELECT id, delivery_date, label, stage
            FROM delivery_lists
            WHERE delivery_date = ?
              AND stage LIKE '%Indian Trail%'
              AND status = 'active'
            ORDER BY id
            """,
            (resolved_date,),
        ).fetchall()
        return resolved_date, list(rows)

    def indian_trail_physical_inventory(self, con: sqlite3.Connection, delivery_date: str) -> dict[tuple[str, str], dict[str, Any]]:
        """Aggregate all active Indian Trail copies into one physical item inventory.

        Effects: Reads active Indian Trail line items only.
        Flow: Uses Order Nr./Item Nr. as the stable physical identity, takes the largest expected
        and received quantities across duplicate/update copies, and retains representative item
        metadata for the Bay Map and in-transit manifest.
        """
        rows = con.execute(
            """
            SELECT li.*, dl.id AS delivery_list_id
            FROM delivery_lists dl
            JOIN line_items li ON li.list_id = dl.id
            WHERE dl.delivery_date = ?
              AND dl.status = 'active'
              AND dl.stage LIKE '%Indian Trail%'
            ORDER BY dl.id, li.order_no, li.item_no
            """,
            (delivery_date,),
        ).fetchall()
        inventory: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (
                str(row["order_no"] or "").strip(),
                str(row["item_no"] or "").strip().zfill(3),
            )
            current = inventory.get(key)
            qty = max(int(row["qty"] or 0), 0)
            received_qty = max(int(row["scanned_qty"] or 0), 0)
            if current is None:
                inventory[key] = {
                    "key": key,
                    "source_id": str(row["source_id"] or "").strip(),
                    "inbound_line_id": str(row["id"] or ""),
                    "list_id": str(row["delivery_list_id"] or ""),
                    "order_no": key[0],
                    "item_no": key[1],
                    "qty": qty,
                    "received_qty": min(received_qty, qty) if qty else received_qty,
                    "dimensions": str(row["dimensions"] or ""),
                    "customer": str(row["customer"] or ""),
                    "route": str(row["route"] or ""),
                    "job": str(row["job"] or ""),
                    "product": str(row["product"] or ""),
                    "process_state": str(row["process_state"] or ""),
                    "queue_state": str(row["queue_state"] or ""),
                }
                continue
            current["qty"] = max(int(current["qty"] or 0), qty)
            current["received_qty"] = max(int(current["received_qty"] or 0), min(received_qty, qty) if qty else received_qty)
            if not current["source_id"] and row["source_id"]:
                current["source_id"] = str(row["source_id"])
            for field in ("dimensions", "customer", "route", "job", "product", "process_state", "queue_state"):
                if not current[field] and row[field]:
                    current[field] = str(row[field])
        return inventory

    def indian_trail_in_transit(self, delivery_date: str = "") -> dict[str, Any]:
        """Return the departed-rack manifest for the requested Indian Trail delivery date.

        Effects: Reads live rack, Outbound, and Indian Trail state.
        Flow: Resolves the date-specific inbound list and returns only transportation methods that were actually scanned In Transit.
        """
        with self.connect() as con:
            return self._indian_trail_in_transit_payload(con, delivery_date)

    def _indian_trail_in_transit_payload(self, con: sqlite3.Connection, delivery_date: str = "") -> dict[str, Any]:
        """Return only glass on transportation methods that actually departed for Indian Trail.

        Effects: Reads active Indian Trail, Outbound, rack, and rack-item records.
        Flow: Aggregates all Indian Trail list copies for the resolved date, finds rack assignments
        whose rack was scanned Outbound and is still In Transit, subtracts received quantities once
        per physical Order/Item, and groups the remaining pieces by Job Nr. and rack for the existing
        manifest UI. Pieces merely assigned to a rack are intentionally excluded until departure.
        """
        resolved_date, inbound_lists = self.active_indian_trail_lists(con, delivery_date)
        if not inbound_lists:
            return {
                "deliveryDate": "",
                "outboundListId": "",
                "inboundListId": "",
                "inboundListIds": [],
                "totalQty": 0,
                "jobs": [],
                "rows": [],
            }

        inventory = self.indian_trail_physical_inventory(con, resolved_date)
        primary_inbound = inbound_lists[0]
        outbound_lists = con.execute(
            """
            SELECT id, label, stage
            FROM delivery_lists
            WHERE delivery_date = ?
              AND status = 'active'
              AND stage LIKE '%Outbound%'
            ORDER BY id
            """,
            (resolved_date,),
        ).fetchall()
        outbound_ids = [str(row["id"] or "") for row in outbound_lists]

        outbound_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        if outbound_ids:
            placeholders = ",".join("?" for _ in outbound_ids)
            outbound_rows = con.execute(
                f"""
                SELECT id, source_id, order_no, item_no, scanned_qty
                FROM line_items
                WHERE list_id IN ({placeholders})
                ORDER BY scanned_qty DESC, id
                """,
                tuple(outbound_ids),
            ).fetchall()
            for row in outbound_rows:
                key = (
                    str(row["order_no"] or "").strip(),
                    str(row["item_no"] or "").strip().zfill(3),
                )
                scanned_qty = max(int(row["scanned_qty"] or 0), 0)
                current = outbound_by_key.get(key)
                if current is None or scanned_qty > int(current["scanned_qty"] or 0):
                    outbound_by_key[key] = {
                        "line_id": str(row["id"] or ""),
                        "source_id": str(row["source_id"] or ""),
                        "scanned_qty": scanned_qty,
                    }

        rack_rows = con.execute(
            """
            SELECT
                ri.id AS rack_item_id,
                ri.qty AS rack_qty,
                src_li.id AS source_line_id,
                src_li.source_id,
                src_li.order_no,
                src_li.item_no,
                src_li.dimensions,
                src_li.customer,
                src_li.route,
                src_li.job,
                src_li.product,
                src_li.process_state,
                src_li.queue_state,
                r.rack_code,
                COALESCE(NULLIF(r.display_name, ''), r.rack_code) AS rack_name,
                COALESCE(NULLIF(r.rack_type, ''), CASE WHEN r.rack_code = 'T' THEN 'Truck' ELSE 'Rack' END) AS rack_type,
                COALESCE(r.departed_at, '') AS rack_departed_at,
                COALESCE(r.sort_order, 9999) AS rack_sort_order
            FROM rack_items ri
            JOIN racks r ON r.id = ri.rack_id AND r.active = 1
            JOIN line_items src_li ON src_li.id = ri.line_item_id
            JOIN delivery_lists src_dl ON src_dl.id = src_li.list_id AND src_dl.status = 'active'
            WHERE ri.status = 'Active'
              AND src_dl.delivery_date = ?
              AND LOWER(REPLACE(COALESCE(r.status, ''), ' ', '')) = 'intransit'
              AND COALESCE(r.departed_at, '') <> ''
              AND COALESCE(NULLIF(r.destination, ''), 'Indian Trail') = 'Indian Trail'
            ORDER BY r.sort_order, r.rack_code, src_li.order_no, src_li.item_no, ri.id
            """,
            (resolved_date,),
        ).fetchall()

        rack_map_by_item: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        for row in rack_rows:
            key = (
                str(row["order_no"] or "").strip(),
                str(row["item_no"] or "").strip().zfill(3),
            )
            if key not in inventory:
                continue
            rack_code = str(row["rack_code"] or "").strip()
            if not rack_code:
                continue
            item_racks = rack_map_by_item.setdefault(key, {})
            current = item_racks.get(rack_code)
            rack_qty = max(int(row["rack_qty"] or 0), 0)
            # Reimports can leave equivalent active assignment records pointing at different
            # stage copies. Use the largest quantity for the same physical item/rack rather
            # than summing those duplicates, while still allowing one item to span two racks.
            if current is None or rack_qty > int(current["rack_qty"] or 0):
                item_racks[rack_code] = {
                    "rack_qty": rack_qty,
                    "rack_code": rack_code,
                    "rack_name": str(row["rack_name"] or rack_code),
                    "rack_type": str(row["rack_type"] or "Rack"),
                    "rack_departed_at": str(row["rack_departed_at"] or ""),
                    "rack_sort_order": int(row["rack_sort_order"] or 9999),
                    "source_line_id": str(row["source_line_id"] or ""),
                    "source_id": str(row["source_id"] or ""),
                    "dimensions": str(row["dimensions"] or ""),
                    "customer": str(row["customer"] or ""),
                    "route": str(row["route"] or ""),
                    "job": str(row["job"] or ""),
                    "product": str(row["product"] or ""),
                    "process_state": str(row["process_state"] or ""),
                    "queue_state": str(row["queue_state"] or ""),
                }

        flat_rows: list[dict[str, Any]] = []
        for key, item in inventory.items():
            racks = sorted(
                rack_map_by_item.get(key, {}).values(),
                key=lambda row: (int(row["rack_sort_order"]), str(row["rack_code"])),
            )
            if not racks:
                continue
            item_qty = max(int(item["qty"] or 0), 0)
            received_qty = min(max(int(item["received_qty"] or 0), 0), item_qty)
            departed_qty = min(sum(max(int(row["rack_qty"] or 0), 0) for row in racks), item_qty)
            remaining_qty = max(departed_qty - received_qty, 0)
            if remaining_qty <= 0:
                continue
            outbound = outbound_by_key.get(key, {})
            outbound_scanned_qty = min(
                max(int(outbound.get("scanned_qty") or 0), received_qty + remaining_qty),
                item_qty,
            )
            qty_to_allocate = remaining_qty
            for rack in racks:
                if qty_to_allocate <= 0:
                    break
                rack_qty = min(max(int(rack["rack_qty"] or 0), 0), qty_to_allocate)
                if rack_qty <= 0:
                    continue
                qty_to_allocate -= rack_qty
                rack_code = str(rack["rack_code"] or "").strip()
                rack_type = str(rack["rack_type"] or "").strip() or "Rack"
                rack_name = str(rack["rack_name"] or rack_code).strip() or rack_code
                if rack_code == "T" or re.fullmatch(r"T\d+", rack_code) or "TRUCK" in rack_type.upper():
                    rack_name = rack_name or ("Truck" if rack_code == "T" else f"Truck {rack_code[1:]}")
                    rack_type = rack_type or "Truck"
                flat_rows.append(
                    {
                        "inboundLineId": item["inbound_line_id"],
                        "outboundLineId": str(outbound.get("line_id") or ""),
                        "order": item["order_no"],
                        "item": item["item_no"],
                        "qty": rack_qty,
                        "outboundScannedQty": outbound_scanned_qty,
                        "receivedQty": received_qty,
                        "dimensions": item["dimensions"] or rack["dimensions"],
                        "customer": item["customer"] or rack["customer"],
                        "route": item["route"] or rack["route"],
                        "job": item["job"] or rack["job"],
                        "product": item["product"] or rack["product"],
                        "processState": item["process_state"] or rack["process_state"],
                        "queueState": item["queue_state"] or rack["queue_state"],
                        "rackCode": rack_code,
                        "rackName": rack_name,
                        "rackType": rack_type,
                        "rackDepartedAt": rack["rack_departed_at"],
                    }
                )

        job_map: dict[str, dict[str, Any]] = {}
        total_qty = 0
        for item in flat_rows:
            qty = max(int(item["qty"] or 0), 0)
            total_qty += qty
            job_label = str(item["job"] or item["product"] or item["order"] or "No Job Nr.")
            job_key = normalized_match_text(job_label) or f"ORDER{item['order']}"
            job = job_map.setdefault(
                job_key,
                {
                    "key": job_key,
                    "job": job_label,
                    "customer": item["customer"] or "",
                    "product": item["product"] or "",
                    "totalQty": 0,
                    "rackMap": {},
                },
            )
            job["totalQty"] += qty
            rack_key = str(item["rackCode"] or "")
            rack = job["rackMap"].setdefault(
                rack_key,
                {
                    "code": rack_key,
                    "name": item["rackName"],
                    "type": item["rackType"],
                    "totalQty": 0,
                    "items": [],
                },
            )
            rack["totalQty"] += qty
            rack["items"].append(item)

        jobs: list[dict[str, Any]] = []
        for job in job_map.values():
            racks = sorted(
                job["rackMap"].values(),
                key=lambda rack: (str(rack["code"]) == "T", str(rack["code"])),
            )
            for rack in racks:
                rack["items"].sort(key=lambda item: (str(item["order"]), str(item["item"])))
            jobs.append({key: value for key, value in job.items() if key != "rackMap"} | {"racks": racks})
        jobs.sort(key=lambda job: (str(job.get("job") or ""), str(job.get("customer") or "")))

        primary_outbound = outbound_lists[0] if outbound_lists else None
        return {
            "deliveryDate": resolved_date,
            "outboundListId": str(primary_outbound["id"] or "") if primary_outbound else "",
            "outboundListIds": outbound_ids,
            "outboundLabel": str(primary_outbound["label"] or "") if primary_outbound else "",
            "inboundListId": str(primary_inbound["id"] or ""),
            "inboundListIds": [str(row["id"] or "") for row in inbound_lists],
            "inboundLabel": str(primary_inbound["label"] or ""),
            "totalQty": total_qty,
            "jobCount": len(jobs),
            "rowCount": len(flat_rows),
            "jobs": jobs,
            "rows": flat_rows,
        }

    def indian_trail_outbound_totals(
        self,
        con: sqlite3.Connection,
        inbound_list_id: str,
        delivery_date: str,
    ) -> dict[str, int]:
        """Return date-wide physical Indian Trail quantities that reached Outbound.

        Effects: Reads all active Indian Trail and Outbound copies plus departed rack assignments.
        Flow: Aggregates each Order Nr./Item Nr. once across updated/split lists, takes the highest
        stored Outbound scan quantity, adds a floor for actually departed rack quantities, and
        finally applies the downstream Received floor. The result cannot under-report a piece that
        is already physically at Indian Trail and cannot double-count duplicate list copies.
        """
        inventory = self.indian_trail_physical_inventory(con, delivery_date)
        if not inventory:
            return {"totalQty": 0, "scannedQty": 0}

        outbound_rows = con.execute(
            """
            SELECT li.order_no, li.item_no, li.scanned_qty
            FROM delivery_lists dl
            JOIN line_items li ON li.list_id = dl.id
            WHERE dl.delivery_date = ?
              AND dl.status = 'active'
              AND dl.stage LIKE '%Outbound%'
            """,
            (delivery_date,),
        ).fetchall()
        outbound_by_key: dict[tuple[str, str], int] = {}
        for row in outbound_rows:
            key = (
                str(row["order_no"] or "").strip(),
                str(row["item_no"] or "").strip().zfill(3),
            )
            outbound_by_key[key] = max(
                outbound_by_key.get(key, 0),
                max(int(row["scanned_qty"] or 0), 0),
            )

        departed_rows = con.execute(
            """
            SELECT src.order_no, src.item_no, r.rack_code, ri.qty
            FROM rack_items ri
            JOIN racks r ON r.id = ri.rack_id AND r.active = 1
            JOIN line_items src ON src.id = ri.line_item_id
            JOIN delivery_lists src_dl ON src_dl.id = src.list_id AND src_dl.status = 'active'
            WHERE ri.status = 'Active'
              AND src_dl.delivery_date = ?
              AND LOWER(REPLACE(COALESCE(r.status, ''), ' ', '')) = 'intransit'
              AND COALESCE(r.departed_at, '') <> ''
              AND COALESCE(NULLIF(r.destination, ''), 'Indian Trail') = 'Indian Trail'
            """,
            (delivery_date,),
        ).fetchall()
        departed_by_key_and_rack: dict[tuple[tuple[str, str], str], int] = {}
        for row in departed_rows:
            key = (
                str(row["order_no"] or "").strip(),
                str(row["item_no"] or "").strip().zfill(3),
            )
            rack_key = (key, str(row["rack_code"] or "").strip())
            departed_by_key_and_rack[rack_key] = max(
                departed_by_key_and_rack.get(rack_key, 0),
                max(int(row["qty"] or 0), 0),
            )
        departed_by_key: dict[tuple[str, str], int] = {}
        for (key, _rack_code), qty in departed_by_key_and_rack.items():
            departed_by_key[key] = departed_by_key.get(key, 0) + qty

        total_qty = 0
        sent_qty = 0
        for key, item in inventory.items():
            item_qty = max(int(item["qty"] or 0), 0)
            received_qty = min(max(int(item["received_qty"] or 0), 0), item_qty)
            total_qty += item_qty
            sent_qty += min(
                max(
                    outbound_by_key.get(key, 0),
                    departed_by_key.get(key, 0),
                    received_qty,
                ),
                item_qty,
            )
        return {"totalQty": total_qty, "scannedQty": sent_qty}

    def indian_trail_summary(self, delivery_date: str = "") -> dict[str, Any]:
        """Purpose: Return date-specific Indian Trail route totals for the Bay Map.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        with self.connect() as con:
            resolved_date, inbound_lists = self.active_indian_trail_lists(con, delivery_date)
            inbound = inbound_lists[0] if inbound_lists else None
            list_id = str(inbound["id"] or "") if inbound else ""
            totals = {"totalQty": 0, "receivedQty": 0, "unassignedQty": 0}
            outbound_totals = {"totalQty": 0, "scannedQty": 0}
            if inbound_lists:
                inventory = self.indian_trail_physical_inventory(con, resolved_date)
                assigned_rows = con.execute(
                    """
                    SELECT DISTINCT li.order_no, li.item_no
                    FROM delivery_lists dl
                    JOIN line_items li ON li.list_id = dl.id
                    JOIN bay_assignments ba
                      ON ba.line_item_id = li.id
                     AND ba.status NOT IN ('Cleared', 'Cancelled')
                    WHERE dl.delivery_date = ?
                      AND dl.status = 'active'
                      AND dl.stage LIKE '%Indian Trail%'
                    """,
                    (resolved_date,),
                ).fetchall()
                assigned_keys = {
                    (
                        str(row["order_no"] or "").strip(),
                        str(row["item_no"] or "").strip().zfill(3),
                    )
                    for row in assigned_rows
                }
                totals = {
                    "totalQty": sum(max(int(item["qty"] or 0), 0) for item in inventory.values()),
                    "receivedQty": sum(
                        min(max(int(item["received_qty"] or 0), 0), max(int(item["qty"] or 0), 0))
                        for item in inventory.values()
                    ),
                    "unassignedQty": sum(
                        max(int(item["qty"] or 0), 0)
                        for key, item in inventory.items()
                        if key not in assigned_keys
                    ),
                }
                outbound_totals = self.indian_trail_outbound_totals(
                    con,
                    list_id,
                    resolved_date,
                )
            assigned = con.execute("SELECT COALESCE(SUM(assigned_qty),0) FROM bay_assignments WHERE status NOT IN ('Cleared', 'Cancelled')").fetchone()[0]
            sdi = con.execute("SELECT COUNT(*) FROM bay_assignments WHERE status = 'SDIOverride'").fetchone()[0]
            conflicts = con.execute("SELECT COUNT(*) FROM exceptions WHERE exception_type LIKE '%bay%' AND status = 'Open'").fetchone()[0]
            today_start = datetime.now(timezone.utc).date().isoformat()
            cleared_today = con.execute(
                "SELECT COUNT(*) FROM bay_events WHERE event_type = 'ClearBay' AND created_at >= ?",
                (today_start,),
            ).fetchone()[0]
            needs_check = con.execute(
                "SELECT COUNT(*) FROM bay_events WHERE event_type = 'NeedsReview' AND created_at >= ?",
                (today_start,),
            ).fetchone()[0]
            rack_summary = self.rack_summary(con)
            in_transit_payload = self._indian_trail_in_transit_payload(con, resolved_date or delivery_date)
            transit_rows = in_transit_payload.get("rows", []) if isinstance(in_transit_payload, dict) else []

            def transit_row_is_truck(row: dict[str, Any]) -> bool:
                """Purpose: Run the transit row is truck workflow for the delivery-list scanner.

                Effects: Performs an in-memory calculation and returns data without intentional external side effects.
                Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
                """
                rack_code = str(row.get("rackCode") or "").upper()
                rack_type = str(row.get("rackType") or "").upper()
                return rack_code == "T" or re.fullmatch(r"T\d+", rack_code) is not None or "TRUCK" in rack_type

            indian_trail_truck_qty = sum(int(row.get("qty") or 0) for row in transit_rows if transit_row_is_truck(row))
            indian_trail_rack_qty = sum(
                int(row.get("qty") or 0)
                for row in transit_rows
                if str(row.get("rackCode") or "").upper() not in {"", "UNASSIGNED"} and not transit_row_is_truck(row)
            )
            rack_sort_rows = con.execute(
                "SELECT rack_code, status, sort_order FROM racks WHERE active = 1"
            ).fetchall()
            rack_sort = {
                str(row["rack_code"]): {
                    "status": row["status"],
                    "sortOrder": int(row["sort_order"] or 0),
                }
                for row in rack_sort_rows
            }
            transit_rack_map: dict[str, dict[str, Any]] = {}
            for row in transit_rows:
                rack_code = str(row.get("rackCode") or "").strip()
                if not rack_code or rack_code.upper() == "UNASSIGNED":
                    continue
                rack_entry = transit_rack_map.setdefault(
                    rack_code,
                    {
                        "code": rack_code,
                        "name": str(row.get("rackName") or rack_code),
                        "type": str(row.get("rackType") or ("Truck" if transit_row_is_truck(row) else "Rack")),
                        "status": rack_sort.get(rack_code, {}).get("status", "In Transit"),
                        "sortOrder": rack_sort.get(rack_code, {}).get("sortOrder", 9999),
                        "qty": 0,
                    },
                )
                rack_entry["qty"] += int(row.get("qty") or 0)
            racks_in_transit = sorted(
                transit_rack_map.values(),
                key=lambda row: (int(row.get("sortOrder") or 9999), str(row.get("code") or "")),
            )
        return {
            "activeInboundListId": list_id,
            "activeInboundListIds": [str(row["id"] or "") for row in inbound_lists],
            "deliveryDate": resolved_date,
            "indianTrailOutboundTotal": outbound_totals["totalQty"],
            "indianTrailOutboundScanned": outbound_totals["scannedQty"],
            "inboundToday": totals["totalQty"],
            "receivedQty": totals["receivedQty"],
            "assignedToBays": assigned,
            "unassignedQty": totals["unassignedQty"],
            "sdiCount": sdi,
            "bayConflicts": conflicts,
            "clearedToday": cleared_today,
            "needsCheck": needs_check,
            "inTransitQty": in_transit_payload.get("totalQty", 0),
            "inTransitJobCount": in_transit_payload.get("jobCount", 0),
            "rackInTransitQty": indian_trail_rack_qty,
            "truckInTransitQty": indian_trail_truck_qty,
            "racksInTransit": [
                {key: value for key, value in row.items() if key != "sortOrder"}
                for row in racks_in_transit
            ],
        }

    def admin_search_line_items(
        self,
        query: str,
        stage_filter: str = "",
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Purpose: Run the admin search line items workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        clean = str(query or "").strip()
        stage_filter = str(stage_filter or "").strip()
        filters = filters or {}
        progress_filter = str(filters.get("progress") or "all").strip().lower()
        route_filter = str(filters.get("route") or "all").strip().upper()
        location_filter = str(filters.get("location") or "all").strip().lower()
        attention_filters = {str(value).strip().lower() for value in (filters.get("attention") or []) if str(value).strip()}
        glass_types = []
        seen_glass_types: set[str] = set()
        for raw_glass_type in filters.get("glassTypes") or []:
            label = str(raw_glass_type or "").strip()
            key = label.casefold()
            if label and key not in seen_glass_types:
                seen_glass_types.add(key)
                glass_types.append(label)
        limit = max(1, min(int(limit or 20), 100))
        offset = max(int(offset or 0), 0)
        has_active_filters = (
            progress_filter != "all"
            or route_filter not in {"", "ALL"}
            or location_filter != "all"
            or bool(attention_filters)
            or bool(glass_types)
        )
        if len(clean) < 2 and not stage_filter and not has_active_filters:
            return {"results": [], "total": 0, "limit": limit, "offset": offset}
        like = f"%{clean}%"
        stage_clause = ""
        search_clause = ""
        params: list[Any] = []
        if clean:
            search_clause = """
                AND (
                    li.order_no LIKE ? OR li.item_no LIKE ? OR li.source_id LIKE ? OR li.barcode LIKE ?
                    OR li.customer LIKE ? OR li.job LIKE ? OR li.route LIKE ? OR li.product LIKE ?
                    OR li.dimensions LIKE ? OR dl.stage LIKE ?
                )
            """
            params.extend([like, like, like, like, like, like, like, like, like, like])
        if stage_filter:
            stage_clause = " AND dl.id = ?"
            params.append(stage_filter)

        filter_clauses: list[str] = []
        if progress_filter == "not-scanned":
            filter_clauses.append("COALESCE(li.scanned_qty, 0) = 0")
        elif progress_filter == "partial":
            filter_clauses.append("COALESCE(li.scanned_qty, 0) > 0 AND COALESCE(li.scanned_qty, 0) < COALESCE(li.qty, 0)")
        elif progress_filter == "complete":
            filter_clauses.append("COALESCE(li.qty, 0) > 0 AND COALESCE(li.scanned_qty, 0) >= COALESCE(li.qty, 0)")
        if route_filter not in {"", "ALL"}:
            route_aliases = {
                "IT": ("", "IT", "INT", "INDIAN TRAIL"),
                "CPU": ("CPU", "CUSTOMER PICKUP", "PICKUP"),
                "GNV": ("GNV", "GREENVILLE", "BFS GREENVILLE"),
                "DTC": ("DTC", "DELIVER TO CUSTOMER"),
            }.get(route_filter)
            if route_aliases:
                placeholders = ",".join("?" for _ in route_aliases)
                filter_clauses.append(f"UPPER(TRIM(COALESCE(li.route, ''))) IN ({placeholders})")
                params.extend(route_aliases)
            else:
                filter_clauses.append("UPPER(TRIM(COALESCE(li.route, ''))) = ?")
                params.append(route_filter)
        if location_filter == "unassigned":
            filter_clauses.append("r.id IS NULL AND b.id IS NULL")
        elif location_filter == "rack":
            filter_clauses.append("r.id IS NOT NULL")
        elif location_filter == "bay":
            filter_clauses.append("b.id IS NOT NULL")
        glass_type_expression = "COALESCE(NULLIF(TRIM(li.product), ''), NULLIF(TRIM(li.job), ''), 'Other Glass')"
        if glass_types:
            placeholders = ",".join("?" for _ in glass_types)
            filter_clauses.append(f"UPPER({glass_type_expression}) IN ({placeholders})")
            params.extend(label.upper() for label in glass_types)
        if attention_filters:
            attention_clauses: list[str] = []
            if "remake" in attention_filters:
                attention_clauses.append(
                    "(" 
                    "UPPER(COALESCE(li.process_state, '') || ' ' || COALESCE(li.queue_state, '')) LIKE '%REMAKE%' "
                    "OR (' ' || UPPER(COALESCE(li.process_state, '') || ' ' || COALESCE(li.queue_state, '')) || ' ') LIKE '% RM %'"
                    ")"
                )
            if "rush" in attention_filters:
                attention_clauses.append("UPPER(COALESCE(li.process_state, '') || ' ' || COALESCE(li.queue_state, '')) LIKE '%RUSH%'")
            if "updated" in attention_filters:
                attention_clauses.append("EXISTS (SELECT 1 FROM line_update_notices lun WHERE lun.line_item_id = li.id)")
            if "reject" in attention_filters:
                attention_clauses.append("COALESCE(li.internal_reject_count, 0) > 0")
            if "manual" in attention_filters:
                attention_clauses.append("COALESCE(li.manual_only, 0) = 1 OR COALESCE(li.manual_source, '') <> ''")
            if attention_clauses:
                filter_clauses.append("(" + " OR ".join(attention_clauses) + ")")
        filter_sql = " AND " + " AND ".join(filter_clauses) if filter_clauses else ""
        with self.connect() as con:
            glass_option_where = "WHERE dl.id = ?" if stage_filter else "WHERE dl.status = 'active'"
            glass_option_params: list[Any] = [stage_filter] if stage_filter else []
            glass_option_rows = con.execute(
                f"""
                SELECT {glass_type_expression} AS glass_type,
                       COUNT(DISTINCT li.id) AS row_count,
                       COALESCE(SUM(li.qty), 0) AS piece_qty
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                {glass_option_where}
                GROUP BY {glass_type_expression}
                ORDER BY glass_type COLLATE NOCASE
                """,
                glass_option_params,
            ).fetchall()
            total = int(
                con.execute(
                    f"""
                    SELECT COUNT(DISTINCT li.id)
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    LEFT JOIN rack_items ri ON ri.line_item_id = li.id AND ri.status = 'Active'
                    LEFT JOIN racks r ON r.id = ri.rack_id AND r.active = 1
                    LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id AND ba.status NOT IN ('Cleared', 'Cancelled')
                    LEFT JOIN bays b ON b.id = ba.bay_id
                    WHERE 1 = 1
                    {search_clause}
                    {stage_clause}
                    {filter_sql}
                    """,
                    params,
                ).fetchone()[0]
                or 0
            )
            rows = con.execute(
                f"""
                SELECT li.*, dl.label, dl.delivery_date, dl.stage, dl.scanner,
                       r.rack_code, r.display_name AS rack_name,
                       b.bay_code, b.display_name AS bay_name
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                LEFT JOIN rack_items ri ON ri.line_item_id = li.id AND ri.status = 'Active'
                LEFT JOIN racks r ON r.id = ri.rack_id AND r.active = 1
                LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id AND ba.status NOT IN ('Cleared', 'Cancelled')
                LEFT JOIN bays b ON b.id = ba.bay_id
                WHERE 1 = 1
                {search_clause}
                {stage_clause}
                {filter_sql}
                ORDER BY dl.delivery_date DESC, dl.stage, CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER)
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        results = []
        for row in rows:
            item = item_from_row(row)
            item.update(
                {
                    "lineItemId": row["id"],
                    "listId": row["list_id"],
                    "deliveryLabel": row["label"],
                    "deliveryDate": row["delivery_date"],
                    "stage": row["stage"],
                    "scanner": row["scanner"],
                    "location": row["bay_code"] or row["rack_code"] or "",
                    "locationDisplay": row["bay_name"] or row["rack_name"] or row["bay_code"] or row["rack_code"] or "",
                }
            )
            results.append(item)
        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filterOptions": {
                "glassTypes": [
                    {
                        "label": str(row["glass_type"] or "Other Glass"),
                        "rowCount": int(row["row_count"] or 0),
                        "pieceQty": int(row["piece_qty"] or 0),
                    }
                    for row in glass_option_rows
                ],
            },
        }

    def find_bay_for_assignment(self, con: sqlite3.Connection, bay_type: str) -> sqlite3.Row | None:
        """Purpose: Resolve bay for assignment for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        rows = con.execute(
            """
            SELECT candidate.*
            FROM (
                SELECT b.*,
                       COALESCE((
                           SELECT SUM(ba.assigned_qty)
                           FROM bay_assignments ba
                           WHERE ba.bay_id = b.id
                             AND ba.status NOT IN ('Cleared', 'Cancelled')
                       ), 0) AS used_qty
                FROM bays b
                WHERE b.active = 1
                  AND b.bay_type = ?
                  AND COALESCE(b.status, 'Available') = 'Available'
            ) candidate
            WHERE candidate.used_qty < candidate.capacity_qty OR candidate.capacity_qty = 0
            ORDER BY candidate.used_qty, candidate.sort_order
            LIMIT 1
            """,
            (bay_type,),
        ).fetchone()
        return rows

    def get_bay_by_code(self, con: sqlite3.Connection, bay_code: str) -> sqlite3.Row:
        """Purpose: Read bay by code for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        row = con.execute("SELECT * FROM bays WHERE bay_code = ?", (bay_code,)).fetchone()
        if not row or str(row["status"] or "") in {"ScanBlocked", "BlockedAll"}:
            raise ValueError(f"Unknown or blocked bay: {bay_code}")
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
        """Create one item movement event while excluding structural map edits."""
        # DLS_V148_BAY_SCAN_HISTORY_FILTER
        clean_event_type = str(event_type or "").strip()
        if not str(line_item_id or "").strip() or clean_event_type in {
            "UpdateBayLayout",
            "CreateBay",
            "DeleteBay",
            "DeleteBayGroup",
        }:
            return
        con.execute(
            """
            INSERT INTO bay_events (bay_id, line_item_id, event_type, old_bay_id, new_bay_id, reason, user_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bay_id, line_item_id, clean_event_type, old_bay_id, new_bay_id, reason, user, now_iso()),
        )

    def assign_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the assign bay workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Resolve a selected-date mismatch before the maintained Indian Trail receive."""
        if not str(data.get("listId") or "").strip():
            return self._receive_indian_trail_scan_for_list(data, user)
        resolved = self.resolve_cross_date_scan(data)
        if resolved and resolved.get("selection"):
            return resolved["selection"]
        effective_data = dict(data)
        if resolved and resolved.get("candidate"):
            effective_data["listId"] = resolved["candidate"]["listId"]
            effective_data["_crossDateResolved"] = True
        payload = self._receive_indian_trail_scan_for_list(effective_data, user)
        if resolved and resolved.get("candidate"):
            return self.attach_cross_date_result(payload, resolved, effective_data, "indian_trail_receive")
        return payload

    def _receive_indian_trail_scan_for_list(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Receive or return an item into an Indian Trail bay.

        Regular receiving requires an Outbound scan. Bay Map Add mode may return
        an already-received item to a bay without increasing received quantity.
        """
        list_id = str(data.get("listId") or "").strip()
        station = request_station(data) or "Indian Trail"
        barcode = str(data.get("barcode") or "").strip()
        requested_bay_code = str(data.get("bayCode") or "").strip()
        is_manual = str(data.get("isManual") or "").lower() in {"1", "true", "yes"}
        outbound_override = str(data.get("outboundOverride") or "").lower() in {"1", "true", "yes"}
        allow_received_override = str(data.get("allowReceivedOverride") or "").lower() in {"1", "true", "yes"}

        if not barcode:
            raise ValueError("Scan barcode is required")

        search_all_inbound_lists = not bool(list_id)

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")

            if search_all_inbound_lists:
                inbound_lists = con.execute(
                    """
                    SELECT *
                    FROM delivery_lists
                    WHERE stage LIKE '%Indian Trail%' AND status = 'active'
                    ORDER BY delivery_date DESC, id DESC
                    """
                ).fetchall()
                if not inbound_lists:
                    raise ValueError("No active Indian Trail inbound list")
                # Bay Map has no delivery-date selector. Search every active Indian
                # Trail destination row, then bind the scan to the uniquely matched
                # row's actual list instead of silently using only the newest date.
                list_row = inbound_lists[0]
                list_id = str(list_row["id"] or "")
                rows = con.execute(
                    """
                    SELECT li.*, dl.delivery_date AS scan_delivery_date, dl.label AS scan_list_label
                    FROM line_items li
                    JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active'
                      AND dl.stage LIKE '%Indian Trail%'
                    ORDER BY dl.delivery_date DESC, li.order_no, li.item_no, li.id
                    """
                ).fetchall()
            else:
                list_row = con.execute(
                    "SELECT * FROM delivery_lists WHERE id = ?",
                    (list_id,),
                ).fetchone()
                if not list_row:
                    raise ValueError("Indian Trail delivery list was not found")
                rows = con.execute("SELECT * FROM line_items WHERE list_id = ?", (list_id,)).fetchall()

            row, canonical, reason = self.recover_scan(
                barcode,
                rows,
                strict_order_item=is_manual,
            )
            if row is None and not is_manual:
                external_row, external_canonical, external_reason = self.recover_bay_external_scan(barcode, rows)
                if external_row is not None:
                    row, canonical, reason = external_row, external_canonical, external_reason
                elif external_reason.startswith("Ambiguous"):
                    canonical, reason = external_canonical, external_reason

            if row is not None and search_all_inbound_lists:
                list_id = str(row["list_id"] or "")
                list_row = con.execute(
                    "SELECT * FROM delivery_lists WHERE id = ?",
                    (list_id,),
                ).fetchone()
                if not list_row:
                    raise ValueError("The matched Indian Trail delivery list is no longer available")
            if row is None:
                if requested_bay_code and self.bay_manual_text_is_known(con, barcode):
                    target_bay = self.get_bay_by_code(con, requested_bay_code)
                    manual_row = self.create_manual_bay_line_item(con, barcode, requested_bay_code)
                    assignment_ids = self.assign_line_items_to_bay(
                        con,
                        [manual_row],
                        target_bay,
                        user,
                        "Accepted Bay Map barcode rule",
                    )
                    last = self.insert_event(
                        con,
                        list_id,
                        manual_row["id"],
                        barcode,
                        barcode,
                        user,
                        station,
                        "manual_scan",
                        "Manual bay barcode accepted",
                        "Bay Map accepted barcode rule",
                        1,
                    )
                    self.insert_audit(
                        con,
                        "bay_manual_assign",
                        requested_bay_code,
                        "bay_scanner_rule_assign",
                        user,
                        station,
                        "Accepted Bay Map barcode rule",
                        {"barcode": barcode, "assignmentIds": assignment_ids},
                    )
                    con.commit()
                    return {
                        "ok": True,
                        "message": f"Accepted Bay Map barcode and assigned it to {target_bay['display_name'] or requested_bay_code}.",
                        "bayCode": requested_bay_code,
                        "assignmentId": assignment_ids[0] if assignment_ids else 0,
                        "assignmentIds": assignment_ids,
                        "lastScan": last,
                    }

                if reason.startswith("Ambiguous") and search_all_inbound_lists:
                    reason = (
                        "More than one active Indian Trail item matched that entry. "
                        "Use the complete printed barcode or confirm the delivery date before scanning again."
                    )
                elif reason in {"No unique delivery-list match", "No exact order/item match"}:
                    canonical, reason = self.scan_other_list_hint(
                        con,
                        list_id,
                        barcode,
                        strict_order_item=is_manual,
                    )
                last = self.insert_event(
                    con,
                    list_id,
                    None,
                    barcode,
                    canonical,
                    user,
                    station,
                    "error",
                    "Item is not on this delivery list",
                    reason,
                )
                con.commit()
                return {"ok": False, "message": reason, "lastScan": last}

            job_key = str(row["job"] or "").strip()
            if job_key:
                group_rows = con.execute(
                    """
                    SELECT * FROM line_items
                    WHERE list_id = ? AND COALESCE(job, '') = ?
                    ORDER BY order_no, item_no, id
                    """,
                    (list_id, job_key),
                ).fetchall()
            else:
                group_rows = con.execute(
                    """
                    SELECT * FROM line_items
                    WHERE list_id = ? AND order_no = ?
                    ORDER BY order_no, item_no, id
                    """,
                    (list_id, row["order_no"]),
                ).fetchall()
            group_rows = group_rows or [row]
            group_ids = [item["id"] for item in group_rows]
            placeholders = ",".join("?" for _ in group_ids)

            existing_group_assignment = con.execute(
                f"""
                SELECT ba.*, b.bay_code
                FROM bay_assignments ba
                JOIN bays b ON b.id = ba.bay_id
                WHERE ba.status NOT IN ('Cleared', 'Cancelled')
                  AND ba.line_item_id IN ({placeholders})
                ORDER BY CASE WHEN ba.line_item_id = ? THEN 0 ELSE 1 END, ba.id DESC
                LIMIT 1
                """,
                [*group_ids, row["id"]],
            ).fetchone()

            override_bay = self.get_bay_by_code(con, requested_bay_code) if requested_bay_code else None
            row_item = {
                "route": row["route"],
                "job": row["job"],
                "customer": row["customer"],
                "product": row["product"],
                "processState": row["process_state"],
                "queueState": row["queue_state"],
            }
            rush_item = is_rush_item(row_item)
            rush_direct_to_truck = rush_item and bool(row_value(row, "priority_direct_to_truck", 0))
            priority_delivery_date = str(row_value(row, "priority_delivery_date") or list_row["delivery_date"] or "")
            suggested_bay_type = (
                "CPU"
                if is_cpu_item(row_item)
                else self.suggested_bay_from_settings(con, row["product"], row["dimensions"], row["route"])
            )

            if rush_direct_to_truck:
                target_bay = None
                receive_reason = "Rush received at Indian Trail; send straight to installer truck"
            elif override_bay:
                target_bay = override_bay
                receive_reason = "Received at Indian Trail with bay override"
            elif existing_group_assignment:
                target_bay = con.execute(
                    "SELECT * FROM bays WHERE id = ?",
                    (existing_group_assignment["bay_id"],),
                ).fetchone()
                receive_reason = "Received at Indian Trail with existing job bay"
            elif self.bay_type_requires_manual_assignment(con, suggested_bay_type):
                # Tall and oversize pieces still receive a concrete suggested bay so
                # the timed placement popup can tell the operator where to put them.
                # The operator can override that suggestion before the popup closes.
                target_bay = (
                    self.find_bay_for_assignment(con, suggested_bay_type)
                    or self.find_bay_for_assignment(con, "Standard")
                )
                receive_reason = f"{suggested_bay_type} suggested during receive; verify placement"
            else:
                target_bay = (
                    self.find_bay_for_assignment(con, suggested_bay_type)
                    or self.find_bay_for_assignment(con, "Standard")
                )
                receive_reason = "Auto suggested during receive"

            preassigned_bay_code = str(target_bay["bay_code"] or "") if target_bay else ""
            already_received = int(row["scanned_qty"] or 0) >= int(row["qty"] or 0)
            returned_to_bay = already_received and allow_received_override

            if already_received and not returned_to_bay:
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
                    "Quantity already received",
                )
                con.commit()
                return {
                    "ok": False,
                    "message": "Quantity already received. Send to supervisor.",
                    "lastScan": last,
                }

            outbound_scanned_qty = int(
                con.execute(
                    """
                    SELECT COALESCE(MAX(out_li.scanned_qty), 0) AS scanned_qty
                    FROM delivery_lists out_dl
                    JOIN line_items out_li ON out_li.list_id = out_dl.id
                    WHERE out_dl.delivery_date = ?
                      AND out_dl.status = 'active'
                      AND out_dl.stage LIKE '%Outbound%'
                      AND out_li.order_no = ?
                      AND out_li.item_no = ?
                    """,
                    (list_row["delivery_date"], row["order_no"], row["item_no"]),
                ).fetchone()["scanned_qty"]
                or 0
            )

            if not returned_to_bay and outbound_scanned_qty <= 0 and not outbound_override:
                override_reason = (
                    f"Order {row['order_no']} / Item {row['item_no']} has not been scanned Outbound. "
                    "Choose whether to cancel or override and receive it anyway."
                )
                last = self.insert_event(
                    con,
                    list_id,
                    row["id"],
                    barcode,
                    canonical,
                    user,
                    station,
                    "notice",
                    "Outbound scan required",
                    override_reason,
                    0,
                )
                con.commit()
                return {
                    "ok": False,
                    "outboundOverrideRequired": True,
                    "message": override_reason,
                    "preassignedBayCode": requested_bay_code or preassigned_bay_code,
                    "suggestedBayType": suggested_bay_type,
                    "oversize": "oversize" in suggested_bay_type.lower(),
                    "item": {
                        "order": row["order_no"],
                        "item": row["item_no"],
                        "customer": row["customer"],
                        "dimensions": row["dimensions"],
                        "job": row["job"],
                    },
                    "lastScan": last,
                }

            timestamp = now_iso()
            qty_delta = 0 if returned_to_bay else 1
            if qty_delta:
                con.execute("UPDATE line_items SET scanned_qty = scanned_qty + 1 WHERE id = ?", (row["id"],))
                con.execute(
                    """
                    UPDATE rack_items
                    SET status = 'Removed', removed_by = ?, removed_at = ?, reason = 'Received at Indian Trail'
                    WHERE id IN (
                        SELECT ri.id
                        FROM rack_items ri
                        JOIN line_items src ON src.id = ri.line_item_id
                        JOIN delivery_lists src_dl ON src_dl.id = src.list_id
                        WHERE ri.status = 'Active'
                          AND src_dl.delivery_date = ?
                          AND src.order_no = ?
                          AND src.item_no = ?
                        LIMIT 1
                    )
                    """,
                    (user, timestamp, list_row["delivery_date"], row["order_no"], row["item_no"]),
                )

            event_type = "manual_scan" if is_manual else "scan"
            event_message = (
                "Rush received - direct to installer truck"
                if rush_direct_to_truck
                else "Rush received - priority bay"
                if rush_item
                else "Manual item returned to bay"
                if returned_to_bay and is_manual
                else "Item returned to bay"
                if returned_to_bay
                else "Manual Indian Trail received"
                if is_manual
                else "Indian Trail received"
            )
            event_reason = (
                receive_reason
                if rush_item
                else "Returned received item to Bay Map without changing received quantity"
                if returned_to_bay
                else reason
            )
            last = self.insert_event(
                con,
                list_id,
                row["id"],
                barcode,
                canonical,
                user,
                station,
                event_type,
                event_message,
                event_reason,
                qty_delta,
            )

            assignment_ids: list[int] = []
            scanned_assignment_id = 0
            bay_code = ""
            if rush_direct_to_truck:
                direct_to_truck_item_ids = [
                    group_row["id"]
                    for group_row in group_rows
                    if bool(row_value(group_row, "priority_direct_to_truck", 0))
                    and is_rush_item(
                        {
                            "processState": row_value(group_row, "process_state", ""),
                            "queueState": row_value(group_row, "queue_state", ""),
                        }
                    )
                ]
                if not direct_to_truck_item_ids:
                    direct_to_truck_item_ids = [row["id"]]
                direct_placeholders = ",".join("?" for _ in direct_to_truck_item_ids)
                active_assignments = con.execute(
                    f"""
                    SELECT * FROM bay_assignments
                    WHERE line_item_id IN ({direct_placeholders})
                      AND status NOT IN ('Cleared', 'Cancelled')
                    ORDER BY id
                    """,
                    direct_to_truck_item_ids,
                ).fetchall()
                for active_assignment in active_assignments:
                    con.execute(
                        """
                        UPDATE bay_assignments
                        SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ?
                        WHERE id = ?
                        """,
                        (user, timestamp, receive_reason, active_assignment["id"]),
                    )
                    self.insert_bay_event(
                        con,
                        active_assignment["bay_id"],
                        active_assignment["line_item_id"],
                        "RushDirectToTruck",
                        user,
                        receive_reason,
                        old_bay_id=active_assignment["bay_id"],
                    )
            elif not target_bay:
                self.insert_exception(con, list_id, None, "bay_assignment_conflict", "No safe bay available")
            else:
                bay_code = str(target_bay["bay_code"] or "")
                # Keep the actual scanned item as the newest Bay Map event so
                # Last Scan and Recent Scans describe the operator's scan, not
                # a companion line that was only preassigned with the same job.
                assignment_rows = [item for item in group_rows if item["id"] != row["id"]] + [row]
                for group_row in assignment_rows:
                    active_assignment = con.execute(
                        """
                        SELECT * FROM bay_assignments
                        WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (group_row["id"],),
                    ).fetchone()
                    cleared_assignment = None
                    if not active_assignment:
                        cleared_assignment = con.execute(
                            """
                            SELECT * FROM bay_assignments
                            WHERE line_item_id = ? AND status IN ('Cleared', 'Cancelled')
                            ORDER BY id DESC
                            LIMIT 1
                            """,
                            (group_row["id"],),
                        ).fetchone()

                    is_scanned_row = group_row["id"] == row["id"]
                    next_status = (
                        "Received"
                        if is_scanned_row
                        else str(active_assignment["status"] or "PreAssigned")
                        if active_assignment
                        else "PreAssigned"
                    )
                    if next_status == "SDIOverride" and not is_scanned_row:
                        continue

                    assignment = active_assignment or cleared_assignment
                    if assignment:
                        old_bay_id = assignment["bay_id"]
                        con.execute(
                            """
                            UPDATE bay_assignments
                            SET bay_id = ?, assigned_qty = ?, status = ?, reason = ?,
                                assigned_by = ?, assigned_at = ?, cleared_by = '', cleared_at = ''
                            WHERE id = ?
                            """,
                            (
                                target_bay["id"],
                                max(int(group_row["qty"] or 1), 1),
                                next_status,
                                receive_reason,
                                user,
                                timestamp,
                                assignment["id"],
                            ),
                        )
                        event_name = (
                            "ReturnToBay"
                            if returned_to_bay and is_scanned_row
                            else "ReceiveOverrideBay"
                            if old_bay_id != target_bay["id"]
                            else "ReceiveBay"
                        )
                        self.insert_bay_event(
                            con,
                            target_bay["id"],
                            group_row["id"],
                            event_name,
                            user,
                            receive_reason,
                            old_bay_id=old_bay_id,
                            new_bay_id=target_bay["id"],
                        )
                        assignment_id = int(assignment["id"])
                    else:
                        cur = con.execute(
                            """
                            INSERT INTO bay_assignments (
                                delivery_list_id, line_item_id, bay_id, assigned_qty,
                                status, assigned_by, assigned_at, reason
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                list_id,
                                group_row["id"],
                                target_bay["id"],
                                max(int(group_row["qty"] or 1), 1),
                                next_status,
                                user,
                                timestamp,
                                receive_reason,
                            ),
                        )
                        assignment_id = int(cur.lastrowid)
                        self.insert_bay_event(
                            con,
                            target_bay["id"],
                            group_row["id"],
                            "ReturnToBay" if returned_to_bay and is_scanned_row else "ReceiveAssignBay",
                            user,
                            receive_reason,
                            new_bay_id=target_bay["id"],
                        )

                    assignment_ids.append(assignment_id)
                    if is_scanned_row:
                        scanned_assignment_id = assignment_id

            used_override = bool(override_bay)
            audit_action = (
                "indian_trail_receive_rush_direct_to_truck"
                if rush_direct_to_truck
                else "indian_trail_receive_rush_priority_bay"
                if rush_item
                else "manual_return_to_bay"
                if returned_to_bay and is_manual
                else "return_to_bay"
                if returned_to_bay
                else "indian_trail_receive_job_bay_override"
                if used_override
                else "indian_trail_receive_job_bay"
            )
            self.insert_audit(
                con,
                "line_item",
                row["id"],
                audit_action,
                user,
                station,
                event_reason,
                {
                    "bayCode": bay_code,
                    "requestedBayCode": requested_bay_code,
                    "manual": is_manual,
                    "job": job_key,
                    "groupItemCount": len(group_rows),
                    "outboundOverride": outbound_override,
                    "returnedToBay": returned_to_bay,
                    "qtyDelta": qty_delta,
                    "rush": rush_item,
                    "rushDirectToTruck": rush_direct_to_truck,
                    "priorityDeliveryDate": priority_delivery_date,
                },
            )
            con.commit()

            scanned_after = int(row["scanned_qty"] or 0) + qty_delta

        if rush_direct_to_truck:
            message = (
                f"Rush order {row['order_no']} / Item {row['item_no']} received at Indian Trail. "
                "Send this glass straight to the installer truck and do not place it in a bay."
            )
        elif returned_to_bay:
            message = (
                f"Order {row['order_no']} / Item {row['item_no']} returned to Bay {bay_code}. "
                "Received quantity was not changed."
            )
        elif used_override:
            message = (
                f"Order {row['order_no']} / Item {row['item_no']} received with override into Bay {bay_code}. "
                f"Qty Received: {scanned_after}/{row['qty']}."
            )
        elif existing_group_assignment:
            message = (
                f"Order {row['order_no']} / Item {row['item_no']} received into existing Job Bay {bay_code}."
            )
        else:
            message = (
                f"Order {row['order_no']} / Item {row['item_no']} received. Suggested Bay: {bay_code}. "
                f"Qty Received: {scanned_after}/{row['qty']}."
            )

        return {
            "ok": True,
            "message": message,
            "bayCode": bay_code,
            "preassignedBayCode": preassigned_bay_code,
            "existingBay": bool(existing_group_assignment),
            "assignmentId": scanned_assignment_id,
            "assignmentIds": assignment_ids,
            "returnedToBay": returned_to_bay,
            "outboundOverrideUsed": outbound_override,
            "suggestedBayType": suggested_bay_type,
            "oversize": "oversize" in suggested_bay_type.lower(),
            "rush": rush_item,
            "rushDirectToTruck": rush_direct_to_truck,
            "priorityDeliveryDate": priority_delivery_date,
            "lastScan": last,
        }
    def move_bay_assignment(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the move bay assignment workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
            previous_status = str(assignment["status"] or "Assigned")
            # A PreAssigned row reserves a destination but does not prove that the
            # glass was physically scanned into a bay. Preserve that distinction
            # when its destination is corrected; converting it to Moved would make
            # the Bay Map fulfillment view incorrectly mark a missing item present.
            next_status = "PreAssigned" if previous_status == "PreAssigned" else "Moved"
            con.execute(
                "UPDATE bay_assignments SET bay_id = ?, status = ?, reason = ? WHERE id = ?",
                (new_bay["id"], next_status, reason, assignment_id),
            )
            self.insert_bay_event(con, new_bay["id"], assignment["line_item_id"], "MoveBay", user, reason, assignment["bay_id"], new_bay["id"])
            self.insert_audit(
                con,
                "bay_assignment",
                str(assignment_id),
                "move_bay",
                user,
                "",
                reason,
                {
                    "newBayCode": new_bay_code,
                    "previousStatus": previous_status,
                    "status": next_status,
                },
            )
            con.commit()
        return {
            "ok": True,
            "assignmentId": assignment_id,
            "bayCode": new_bay_code,
            "status": next_status,
        }

    def clear_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove bay for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Remove bay assignment for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Run the restore bay assignment workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
                "UPDATE bay_assignments SET status = 'Assigned', cleared_by = '', cleared_at = '', reason = ? WHERE id = ?",
                (reason, assignment_id),
            )
            self.insert_bay_event(con, row["bay_id"], row["line_item_id"], "RestoreAssignment", user, reason, new_bay_id=row["bay_id"])
            self.insert_audit(con, "bay_assignment", str(assignment_id), "restore_bay_assignment", user, "", reason)
            con.commit()
        return {"ok": True, "assignmentId": assignment_id, "bayCode": bay["bay_code"]}

    def set_bay_status(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update bay status for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        bay_code = str(data.get("bayCode") or "").strip()
        raw_status = str(data.get("status") or "Available").strip()
        status_lookup = {
            "available": "Available",
            "autoassign": "Available",
            "hold": "ManualAssign",
            "manualhold": "ManualAssign",
            "manualassign": "ManualAssign",
            "blocked": "ManualAssign",
            "scanblocked": "ScanBlocked",
            "blockedall": "ScanBlocked",
        }
        status = status_lookup.get(raw_status.lower().replace(" ", ""), raw_status)
        reason = str(data.get("reason") or f"Bay set to {status}").strip()
        if status not in {"Available", "ManualAssign", "ScanBlocked"}:
            raise ValueError("Bay status must be Available, ManualAssign, or ScanBlocked")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            bay = self.get_bay_by_code(con, bay_code) if status != "Available" else con.execute("SELECT * FROM bays WHERE bay_code = ?", (bay_code,)).fetchone()
            if not bay:
                raise ValueError(f"Unknown bay: {bay_code}")
            # Keep policy/status changes visible on the bay map. `active=0` is now reserved
            # for true soft deletion, not Manual Assign or Blocked Scans status.
            con.execute("UPDATE bays SET status = ?, active = 1 WHERE id = ?", (status, bay["id"]))
            self.insert_bay_event(con, bay["id"], "", f"{status}Bay", user, reason)
            self.insert_audit(con, "bay", bay_code, f"set_bay_{status.lower()}", user, "", reason)
            con.commit()
        return {"ok": True, "bayCode": bay_code, "status": status, "bays": self.get_bays()}


    def scan_out_bay_item(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Scan an item out of its current bay and preserve a dated movement log."""
        barcode = str(data.get("barcode") or data.get("scan") or "").strip()
        bay_code_filter = str(data.get("bayCode") or "").strip()
        is_manual = str(data.get("isManual") or "").lower() in {"1", "true", "yes"}
        reason = str(data.get("reason") or ("Manual scan out from bay map" if is_manual else "Scanned out from bay map")).strip()
        if not barcode:
            raise ValueError("Scan barcode is required")

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            assignments = con.execute(
                """
                SELECT ba.*, li.barcode, li.source_id, li.order_no, li.item_no,
                       li.job, li.product, li.customer, b.bay_code, b.display_name
                FROM bay_assignments ba
                JOIN line_items li ON li.id = ba.line_item_id
                JOIN bays b ON b.id = ba.bay_id
                WHERE ba.status NOT IN ('Cleared', 'Cancelled', 'PreAssigned')
                  AND (? = '' OR b.bay_code = ? OR b.display_name = ?)
                ORDER BY ba.id DESC
                """,
                (bay_code_filter, bay_code_filter, bay_code_filter),
            ).fetchall()

            matched, _canonical, external_reason = self.recover_bay_external_scan(barcode, assignments)
            clean = clean_barcode(barcode)
            digits = digits_only(clean)
            if matched is None:
                for assignment in assignments:
                    if clean and clean == clean_barcode(assignment["barcode"]):
                        matched = assignment
                        break
                    order_text = str(assignment["order_no"] or "")
                    item_text = str(assignment["item_no"] or "").lstrip("0") or "0"
                    if order_text and order_text in barcode and item_text in digits:
                        matched = assignment
                        break

            if not matched:
                if external_reason.startswith("Ambiguous"):
                    raise ValueError("More than one item in a bay matched that barcode. Use the order and item reference instead.")
                raise ValueError("No item currently in a bay matched that scan")

            timestamp = now_iso()
            con.execute(
                """
                UPDATE bay_assignments
                SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ?
                WHERE id = ?
                """,
                (user, timestamp, reason, matched["id"]),
            )
            event_type = "ManualScanOutBay" if is_manual else "ScanOutBay"
            self.insert_bay_event(
                con,
                matched["bay_id"],
                matched["line_item_id"],
                event_type,
                user,
                reason,
                old_bay_id=matched["bay_id"],
            )
            self.insert_audit(
                con,
                "bay_assignment",
                str(matched["id"]),
                "manual_scan_out_bay" if is_manual else "scan_out_bay",
                user,
                request_station(data),
                reason,
                {"barcode": barcode, "bayCode": matched["bay_code"], "manual": is_manual},
            )
            con.commit()

        return {
            "ok": True,
            "assignmentId": int(matched["id"]),
            "bayCode": matched["bay_code"],
            "bayDisplay": matched["display_name"] or matched["bay_code"],
            "order": matched["order_no"],
            "item": matched["item_no"],
            "customer": matched["customer"],
            "manual": is_manual,
            "time": timestamp,
        }
    def update_bay_layout(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Update bay layout for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        bay_code = str(data.get("bayCode") or "").strip()
        if not bay_code:
            raise ValueError("bayCode is required")
        display_name = " ".join(str(data.get("displayName") or bay_code).split())[:120]
        map_section = " ".join(str(data.get("mapSection") or "").split())[:120]
        bay_category = " ".join(str(data.get("bayCategory") or "").split())[:120]
        layout_row = int(data.get("layoutRow") or 0) or None
        layout_col = int(data.get("layoutCol") or 0) or None
        capacity = int(data.get("capacityQty") or 0)
        active_value = data.get("active", None)
        insert_before = str(data.get("insertBeforeBayCode") or "").strip()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM bays WHERE bay_code = ?", (bay_code,)).fetchone()
            if not row:
                raise ValueError(f"Unknown bay: {bay_code}")
            if active_value is None:
                active = 1 if row["active"] or str(row["status"] or "") in {"Hold", "ManualAssign", "Blocked", "ScanBlocked", "BlockedAll"} else 0
            else:
                active = 1 if active_value in {True, "1", "true", "yes", 1} else 0
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
        """Purpose: Update bay group position for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
        """Purpose: Create bays for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        map_section = " ".join(str(data.get("mapSection") or data.get("group") or "").split())[:120]
        bay_category = " ".join(str(data.get("bayCategory") or data.get("category") or "Standard").split())[:120]
        prefix = " ".join(str(data.get("prefix") or map_section or bay_category or "BAY").split())[:60]
        count = max(1, min(int(data.get("count") or 1), 100))
        layout_row = int(data.get("layoutRow") or 0) or None
        layout_col = int(data.get("layoutCol") or 0) or None
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
                        layout_row if layout_row is not None else next_number,
                        layout_col if layout_col is not None else next_number,
                    ),
                )
                bay_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                self.insert_bay_event(con, bay_id, "", "CreateBay", user, "Bay created")
                created.append(bay_code)
            self.insert_audit(con, "bay", map_section, "create_bays", user, "", "", {"created": created, "category": bay_category})
            con.commit()
        return {"ok": True, "created": created, "bays": self.get_bays()}

    def delete_bay(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove bay for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
            con.execute("UPDATE bays SET active = 0, status = 'Deleted' WHERE id = ?", (row["id"],))
            self.insert_bay_event(con, row["id"], "", "DeleteBay", user, "Bay deleted")
            self.insert_audit(con, "bay", bay_code, "delete_bay", user, "", "", {})
            con.commit()
        return {"ok": True, "bayCode": bay_code, "bays": self.get_bays()}

    def delete_bay_group(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Remove bay group for the delivery-list scanner workflow.

        Effects: This function reads or changes database records.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
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
            con.execute("UPDATE bays SET active = 0, status = 'Deleted' WHERE map_section = ?", (map_section,))
            for row in rows:
                self.insert_bay_event(con, row["id"], "", "DeleteBayGroup", user, "Bay group deleted")
            self.insert_audit(con, "bay_group", map_section, "delete_bay_group", user, "", "", {"count": len(rows)})
            con.commit()
        return {"ok": True, "mapSection": map_section, "deletedCount": len(rows), "bays": self.get_bays()}

    def move_bay_group(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the move bay group workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Mark exact missing items, or an explicitly selected broken item, as Rush/Remake.

        Job-level actions intentionally skip pieces already physically fulfilled in a bay.
        Explicit item selections remain available for a broken in-bay piece; a Remake clears
        that exact physical assignment so the Bay Map immediately reports the piece missing.
        """
        assignment_id = int(data.get("assignmentId") or 0)
        lookup_text = str(data.get("orderNo") or data.get("order") or data.get("job") or "").strip()
        bay_code = str(data.get("bayCode") or "").strip()
        truck_exempt = bool(data.get("truckExempt"))
        raw_type = str(data.get("orderType") or data.get("type") or "").strip()
        raw_reason = str(data.get("reason") or "Same-day install").strip()
        requested_delivery_date = str(data.get("deliveryDate") or "").strip()
        raw_ids = data.get("lineItemIds") or data.get("lineItemId") or []
        if isinstance(raw_ids, (str, int)):
            raw_ids = [raw_ids]
        line_item_ids = [str(value or "").strip() for value in raw_ids if str(value or "").strip()]
        if requested_delivery_date:
            try:
                datetime.strptime(requested_delivery_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("Delivery date must use YYYY-MM-DD format") from exc

        normalized_type = normalized_match_text(raw_type)
        if normalized_type in {"RUSH", "SDI", "URGENT", "URGENTE"}:
            order_type = "Rush"
        elif normalized_type in {"REMAKE", "RM", "REHECHO", "REHACER"}:
            order_type = "Remake"
        else:
            reason_prefix = normalized_match_text(raw_reason.split("-", 1)[0])
            if reason_prefix in {"RUSH", "SDI", "URGENT", "URGENTE"}:
                order_type = "Rush"
                raw_reason = raw_reason.split("-", 1)[1].strip() if "-" in raw_reason else "Same-day install"
            elif reason_prefix in {"REMAKE", "RM", "REHECHO", "REHACER"}:
                order_type = "Remake"
                raw_reason = raw_reason.split("-", 1)[1].strip() if "-" in raw_reason else "Remake"
            else:
                raise ValueError("Select Rush or Remake before marking the item")

        reason = f"{order_type} - {raw_reason or ('Same-day install' if order_type == 'Rush' else 'Remake')}"
        if not assignment_id and not lookup_text and not line_item_ids:
            raise ValueError("Select one or more items, or enter a Job Nr., SO number, or order number")

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            explicit_selection = bool(line_item_ids or assignment_id)
            seed_rows: list[Any] = []
            if assignment_id:
                assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
                if not assignment:
                    raise ValueError("Assignment not found")
                row = con.execute("SELECT * FROM line_items WHERE id = ?", (assignment["line_item_id"],)).fetchone()
                if row:
                    seed_rows = self.resolve_sdi_destination_rows(con, line_item_ids=[str(row["id"])])
            elif line_item_ids:
                seed_rows = self.resolve_sdi_destination_rows(con, line_item_ids=line_item_ids)
            else:
                seed_rows = self.resolve_sdi_destination_rows(con, lookup_text=lookup_text)

            if not seed_rows:
                raise ValueError("No matching Indian Trail item was found on active delivery lists")

            if not explicit_selection:
                seed_rows = [row for row in seed_rows if self.sdi_item_presence(row)["missingQty"] > 0]
                if not seed_rows:
                    raise ValueError("Every matching item is already fulfilled in a bay. Select the exact broken item to mark a Remake.")

            affected_rows = self.expand_priority_line_items(con, seed_rows) or seed_rows
            affected_lists = self.priority_list_context(con, affected_rows)
            affected_list_ids = [str(item["id"]) for item in affected_lists]
            source_ids = sorted({str(row["source_id"] or "") for row in affected_rows if str(row["source_id"] or "")})
            logical_item_keys = {
                str(row["source_id"] or "") or f"{row['order_no']}::{row['item_no']}"
                for row in affected_rows
            }
            has_indian_trail_destination = bool(seed_rows)
            direct_to_truck_value = 1 if order_type == "Rush" and truck_exempt and has_indian_trail_destination else 0
            target_bay = self.get_bay_by_code(con, bay_code) if bay_code and not direct_to_truck_value else None
            removed_from_bay = 0
            created_preassignments = 0
            primary_assignment_id = assignment_id

            for row in seed_rows:
                active_assignments = con.execute(
                    """
                    SELECT * FROM bay_assignments
                    WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')
                    ORDER BY id
                    """,
                    (row["id"],),
                ).fetchall()

                if order_type == "Remake":
                    for current in active_assignments:
                        current_status = str(current["status"] or "")
                        if current_status == "PreAssigned":
                            self.insert_bay_event(
                                con,
                                current["bay_id"],
                                row["id"],
                                "MarkRemakePreAssigned",
                                user,
                                reason,
                            )
                            primary_assignment_id = primary_assignment_id or int(current["id"])
                            continue
                        con.execute(
                            """
                            UPDATE bay_assignments
                            SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ?
                            WHERE id = ?
                            """,
                            (user, now_iso(), reason, current["id"]),
                        )
                        removed_from_bay += 1
                        self.insert_bay_event(
                            con,
                            current["bay_id"],
                            row["id"],
                            "MarkRemakeMissing",
                            user,
                            reason,
                            old_bay_id=current["bay_id"],
                        )
                        self.insert_audit(
                            con,
                            "bay_assignment",
                            str(current["id"]),
                            "mark_remake_remove_from_bay",
                            user,
                            "",
                            reason,
                            {"lineItemId": row["id"], "lookup": lookup_text},
                        )
                        primary_assignment_id = primary_assignment_id or int(current["id"])
                else:
                    if active_assignments:
                        for current in active_assignments:
                            self.insert_bay_event(
                                con,
                                current["bay_id"],
                                row["id"],
                                "MarkRush",
                                user,
                                reason,
                            )
                            primary_assignment_id = primary_assignment_id or int(current["id"])
                    elif target_bay:
                        cur = con.execute(
                            """
                            INSERT INTO bay_assignments (
                                delivery_list_id, line_item_id, bay_id, assigned_qty,
                                status, assigned_by, assigned_at, reason
                            )
                            VALUES (?, ?, ?, ?, 'PreAssigned', ?, ?, ?)
                            """,
                            (
                                row["list_id"],
                                row["id"],
                                target_bay["id"],
                                max(int(row["qty"] or 1), 1),
                                user,
                                now_iso(),
                                reason,
                            ),
                        )
                        new_assignment_id = int(cur.lastrowid)
                        primary_assignment_id = primary_assignment_id or new_assignment_id
                        created_preassignments += 1
                        self.insert_audit(
                            con,
                            "bay_assignment",
                            str(new_assignment_id),
                            "mark_rush_preassign",
                            user,
                            "",
                            reason,
                            {"lineItemId": row["id"], "bayCode": bay_code, "lookup": lookup_text},
                        )
                        self.insert_bay_event(
                            con,
                            target_bay["id"],
                            row["id"],
                            "MarkRushPreAssign",
                            user,
                            reason,
                            new_bay_id=target_bay["id"],
                        )

            special_pattern = r"\b(?:Rush|SDI|Remake|RM)\b"
            for row in affected_rows:
                process_state = re.sub(special_pattern, "", str(row["process_state"] or ""), flags=re.IGNORECASE)
                process_state = re.sub(r"\s{2,}", " ", process_state).strip(" -|,")
                next_state = " ".join(part for part in [process_state, order_type] if part).strip()
                con.execute(
                    "UPDATE line_items SET process_state = ?, priority_direct_to_truck = ? WHERE id = ?",
                    (next_state, direct_to_truck_value, row["id"]),
                )
                message = "Rush order marked" if order_type == "Rush" else "Remake marked"
                self.insert_event(
                    con,
                    row["list_id"],
                    row["id"],
                    "SDI" if order_type == "Rush" else "REMAKE",
                    row["barcode"],
                    user,
                    "",
                    "notice",
                    message,
                    reason,
                )
                self.insert_audit(
                    con,
                    "line_item",
                    row["id"],
                    "mark_rush_sdi" if order_type == "Rush" else "mark_remake_sdi",
                    user,
                    "",
                    reason,
                    {
                        "orderType": order_type,
                        "truckExempt": bool(direct_to_truck_value),
                        "bayCode": bay_code,
                        "assignmentId": primary_assignment_id,
                        "lookup": lookup_text,
                        "explicitItemSelection": explicit_selection,
                        "affectedListIds": affected_list_ids,
                    },
                )

            first_notice_row = affected_rows[0] if affected_rows else None
            original_delivery_date = ""
            previous_delivery_date = ""
            effective_delivery_date = requested_delivery_date
            if first_notice_row:
                original_delivery_date = str(row_value(first_notice_row, "delivery_date") or "")
                if not original_delivery_date:
                    notice_date_row = con.execute(
                        "SELECT delivery_date FROM delivery_lists WHERE id = ?",
                        (str(first_notice_row["list_id"] or ""),),
                    ).fetchone()
                    original_delivery_date = str(notice_date_row["delivery_date"] or "") if notice_date_row else ""
                previous_delivery_date = str(row_value(first_notice_row, "priority_delivery_date") or original_delivery_date)
                effective_delivery_date = requested_delivery_date or previous_delivery_date or original_delivery_date

            if requested_delivery_date:
                for row in affected_rows:
                    row_original_date = str(row_value(row, "delivery_date") or original_delivery_date)
                    row_previous_date = str(row_value(row, "priority_delivery_date") or row_original_date)
                    if row_previous_date == requested_delivery_date:
                        continue
                    con.execute("UPDATE line_items SET priority_delivery_date = ? WHERE id = ?", (requested_delivery_date, row["id"]))
                    self.insert_audit(
                        con,
                        "line_item",
                        row["id"],
                        "change_priority_delivery_date",
                        user,
                        "",
                        reason,
                        {"previousDeliveryDate": row_previous_date, "deliveryDate": requested_delivery_date, "orderType": order_type},
                    )

            notification_id = 0
            if order_type == "Rush" and affected_rows:
                first_notice_row = affected_rows[0]
                notice_job = str(first_notice_row["job"] or "").strip()
                notice_customer = str(first_notice_row["customer"] or "").strip()
                notice_order = str(first_notice_row["order_no"] or "").strip()
                notice_route = str(first_notice_row["route"] or "").strip()
                item_pairs = sorted({(str(row["order_no"] or "").strip(), str(row["item_no"] or "").strip()) for row in affected_rows})
                item_labels = [f"{order}-{item}" if order else item for order, item in item_pairs]
                products: list[str] = []
                for row in affected_rows:
                    product_label = " - ".join(value for value in [str(row["product"] or "").strip(), str(row["dimensions"] or "").strip()] if value)
                    if product_label and product_label not in products:
                        products.append(product_label)
                notice_target = notice_job or notice_order or lookup_text
                notice_message = (
                    f"{notice_target} was marked as Rush"
                    f"{f' for {notice_customer}' if notice_customer else ''}"
                    f"{f' for the new delivery date {effective_delivery_date}' if effective_delivery_date else ''}. Prioritize this work."
                )
                notification_id = self.create_app_notification(
                    con,
                    "rush",
                    "New Rush Submitted",
                    notice_message,
                    user,
                    {
                        "job": notice_job,
                        "order": notice_order,
                        "customer": notice_customer,
                        "route": notice_route,
                        "deliveryDate": effective_delivery_date,
                        "previousDeliveryDate": previous_delivery_date if previous_delivery_date != effective_delivery_date else "",
                        "items": len(item_pairs),
                        "itemLabels": item_labels,
                        "products": products[:12],
                        "reason": raw_reason,
                        "lookup": lookup_text,
                        "listId": affected_list_ids[0] if affected_list_ids else "",
                        "affectedListIds": affected_list_ids,
                        "affectedLists": affected_lists,
                        "sourceIds": source_ids,
                        "directToTruck": bool(direct_to_truck_value),
                        "submittedBy": user,
                    },
                    expires_in_hours=24,
                    acknowledge_creator=False,
                )

            con.commit()

        first_row = affected_rows[0] if affected_rows else None
        matched_job = str(first_row["job"] or "").strip() if first_row else ""
        matched_customer = str(first_row["customer"] or "").strip() if first_row else ""
        matched_order = str(first_row["order_no"] or "").strip() if first_row else ""
        matched_delivery_date = effective_delivery_date if first_row else ""
        target_label = f"Job Nr. {matched_job}" if matched_job else f"order {matched_order or lookup_text}"
        is_rush = order_type == "Rush"
        return {
            "ok": True,
            "assignmentId": primary_assignment_id,
            "listId": affected_list_ids[0] if affected_list_ids else "",
            "affectedListIds": affected_list_ids,
            "affectedLists": affected_lists,
            "affectedSourceIds": source_ids,
            "status": "PriorityMarked",
            "orderType": order_type,
            "rush": is_rush,
            "remake": not is_rush,
            "directToTruck": bool(direct_to_truck_value),
            "affectedItems": len(logical_item_keys),
            "affectedStageRows": len(affected_rows),
            "removedFromBay": removed_from_bay,
            "createdPreassignments": created_preassignments,
            "matchedJob": matched_job,
            "matchedCustomer": matched_customer,
            "matchedOrder": matched_order,
            "matchedDeliveryDate": matched_delivery_date,
            "previousDeliveryDate": previous_delivery_date if first_row else "",
            "lookup": lookup_text,
            "notificationId": notification_id,
            "message": f"{order_type} marked for {target_label} across {len(affected_lists)} applicable stage(s).",
        }

    def remove_sdi(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Clear Rush/Remake from an exact item selection or a resolved job/order group."""
        assignment_id = int(data.get("assignmentId") or 0)
        lookup_text = str(data.get("orderNo") or data.get("order") or data.get("job") or "").strip()
        raw_ids = data.get("lineItemIds") or data.get("lineItemId") or []
        if isinstance(raw_ids, (str, int)):
            raw_ids = [raw_ids]
        line_item_ids = [str(value or "").strip() for value in raw_ids if str(value or "").strip()]
        rush_only = bool(data.get("rushOnly"))
        reason = str(data.get("reason") or ("Rush cleared" if rush_only else "Rush / Remake cleared")).strip()
        if not assignment_id and not lookup_text and not line_item_ids:
            raise ValueError("Select one or more marked items, or enter a Job Nr., SO number, or order number")

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            seed_rows: list[Any] = []
            if assignment_id:
                assignment = con.execute("SELECT * FROM bay_assignments WHERE id = ?", (assignment_id,)).fetchone()
                if not assignment:
                    raise ValueError("Assignment not found")
                seed_rows = self.resolve_sdi_destination_rows(con, line_item_ids=[str(assignment["line_item_id"])])
            elif line_item_ids:
                seed_rows = self.resolve_sdi_destination_rows(con, line_item_ids=line_item_ids)
            else:
                seed_rows = self.resolve_sdi_destination_rows(con, lookup_text=lookup_text)
            if not seed_rows:
                raise ValueError("No matching marked Indian Trail items were found")

            rows = self.expand_priority_line_items(con, seed_rows) or seed_rows
            affected_lists = self.priority_list_context(con, rows)
            logical_item_keys = {str(row["source_id"] or "") or f"{row['order_no']}::{row['item_no']}" for row in rows}

            for row in rows:
                preassignments = con.execute(
                    "SELECT * FROM bay_assignments WHERE line_item_id = ? AND status = 'PreAssigned' ORDER BY id",
                    (row["id"],),
                ).fetchall()
                for assignment in preassignments:
                    created_by_priority = con.execute(
                        """
                        SELECT 1 FROM audit_events
                        WHERE entity_type = 'bay_assignment'
                          AND entity_id = ?
                          AND action = 'mark_rush_preassign'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (str(assignment["id"]),),
                    ).fetchone()
                    if not created_by_priority:
                        continue
                    con.execute(
                        """
                        UPDATE bay_assignments
                        SET status = 'Cleared', cleared_by = ?, cleared_at = ?, reason = ?
                        WHERE id = ?
                        """,
                        (user, now_iso(), reason, assignment["id"]),
                    )
                    self.insert_bay_event(
                        con,
                        assignment["bay_id"],
                        row["id"],
                        "RemoveRushPreAssign",
                        user,
                        reason,
                        old_bay_id=assignment["bay_id"],
                    )
                    self.insert_audit(
                        con,
                        "bay_assignment",
                        str(assignment["id"]),
                        "remove_rush_preassign",
                        user,
                        "",
                        reason,
                    )

                assignments = con.execute(
                    "SELECT * FROM bay_assignments WHERE line_item_id = ? AND status = 'SDIOverride' ORDER BY id",
                    (row["id"],),
                ).fetchall()
                for assignment in assignments:
                    con.execute("UPDATE bay_assignments SET status = 'Assigned', reason = ? WHERE id = ?", (reason, assignment["id"]))
                    self.insert_bay_event(con, assignment["bay_id"], row["id"], "RemoveSDI", user, reason)
                    self.insert_audit(con, "bay_assignment", str(assignment["id"]), "remove_sdi", user, "", reason)

                clear_pattern = r"\b(?:Rush|SDI)\b" if rush_only else r"\b(?:Rush|SDI|Remake|RM)\b"
                next_state = re.sub(clear_pattern, "", str(row["process_state"] or ""), flags=re.IGNORECASE).strip(" -|,")
                next_state = re.sub(r"\s{2,}", " ", next_state)
                con.execute(
                    "UPDATE line_items SET process_state = ?, priority_delivery_date = '', priority_direct_to_truck = 0 WHERE id = ?",
                    (next_state, row["id"]),
                )
                self.insert_audit(
                    con,
                    "line_item",
                    row["id"],
                    "clear_rush_priority" if rush_only else "clear_rush_remake_sdi",
                    user,
                    "",
                    reason,
                    {
                        "lookup": lookup_text,
                        "lineItemIds": line_item_ids,
                        "affectedListIds": [item["id"] for item in affected_lists],
                        "rushOnly": rush_only,
                    },
                )
            con.commit()

        first_row = rows[0] if rows else None
        matched_job = str(first_row["job"] or "").strip() if first_row else ""
        matched_customer = str(first_row["customer"] or "").strip() if first_row else ""
        matched_order = str(first_row["order_no"] or "").strip() if first_row else ""
        return {
            "ok": True,
            "assignmentId": assignment_id,
            "status": "Cleared",
            "affectedItems": len(logical_item_keys),
            "affectedStageRows": len(rows),
            "affectedListIds": [item["id"] for item in affected_lists],
            "affectedLists": affected_lists,
            "matchedJob": matched_job,
            "matchedCustomer": matched_customer,
            "matchedOrder": matched_order,
            "lookup": lookup_text,
            "message": (
                "Rush mark cleared from the selected item(s) across every applicable stage."
                if rush_only
                else "Rush / Remake mark cleared from the selected item(s) across every applicable stage."
            ),
        }

    def bay_check(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        """Purpose: Run the bay check workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
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
        """Purpose: Export CSV for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
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
                    "route": public_route_label(row["route"]),
                    "job": row["job"],
                    "product": row["product"],
                    "suggestedBay": row["suggestedBay"],
                }
            )
        return output.getvalue()

    def export_package_csv(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> str:
        """Export the exact filtered print package as a portable CSV file."""
        package = self.get_print_package(list_ids, user=user, filters=filters)
        output = StringIO()
        fieldnames = [
            "Delivery Date", "Stage", "Scanner", "Barcode", "Order Nr.", "Item Nr.",
            "Qty.", "Scanned", "Remaining", "Dimensions", "Customer", "Route",
            "Job Nr.", "Product", "Suggested Bay",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for package_list in package.get("lists", []):
            for item in package_list.get("items") or []:
                qty = max(int(item.get("qty") or 0), 0)
                scanned = max(int(item.get("scanned") or 0), 0)
                writer.writerow({
                    "Delivery Date": package_list.get("deliveryDate", ""),
                    "Stage": package_list.get("stage", ""),
                    "Scanner": package_list.get("scanner", ""),
                    "Barcode": item.get("barcode", ""),
                    "Order Nr.": item.get("order", ""),
                    "Item Nr.": item.get("item", ""),
                    "Qty.": qty,
                    "Scanned": scanned,
                    "Remaining": max(qty - scanned, 0),
                    "Dimensions": item.get("dimensions", ""),
                    "Customer": item.get("customer", ""),
                    "Route": public_route_label(item.get("route", "")),
                    "Job Nr.": item.get("job", ""),
                    "Product": item.get("product", ""),
                    "Suggested Bay": item.get("suggestedBay", ""),
                })
        return output.getvalue()

    def export_package_xlsx(self, list_ids: list[str], user: dict[str, Any] | None = None, filters: dict[str, Any] | None = None) -> bytes:
        """Purpose: Export package XLSX for the delivery-list scanner workflow.

        Effects: This function reads or changes files.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
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
                    public_route_label(item.get("route", "")),
                    item.get("job", ""),
                    item.get("product", ""),
                    item.get("suggestedBay", ""),
                ])

        def cell_ref(col: int, row: int) -> str:
            """Purpose: Run the cell ref workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            letters = ""
            value = col
            while value:
                value, remainder = divmod(value - 1, 26)
                letters = chr(65 + remainder) + letters
            return f"{letters}{row}"

        def inline_cell(col: int, row: int, value: Any) -> str:
            """Purpose: Run the inline cell workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
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
        """Purpose: Export XLSX for the delivery-list scanner workflow.

        Effects: This function reads or changes files.
        Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
        """
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
            """Purpose: Run the cell ref workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
            letters = ""
            value = col
            while value:
                value, remainder = divmod(value - 1, 26)
                letters = chr(65 + remainder) + letters
            return f"{letters}{row}"

        def inline_cell(col: int, row: int, value: Any) -> str:
            """Purpose: Run the inline cell workflow for the delivery-list scanner.

            Effects: Performs an in-memory calculation and returns data without intentional external side effects.
            Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
            """
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
                public_route_label(item["route"]),
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



class AzureSqlDeliveryStore(SQLiteDeliveryStore):
    """Azure SQL implementation that reuses the shared scanner business workflows."""

    database_type = "azure-sql"

    def __init__(self, config: AppConfig):
        """Purpose: Initialize a Azure SQL delivery store instance and its required state.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self.config = config
        self.database_path = Path(config.database_path)
        self.sample_path = Path(config.sample_path)
        self.connection_string = str(config.database_connection_string or "").strip()
        self._last_bay_event_cleanup_monotonic = 0.0

    def connect(self) -> AzureSqlConnection:
        """Purpose: Run the connect workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return connect_azure_sql(
            self.connection_string,
            timeout_seconds=self.config.database_timeout_seconds,
        )

    def initialize(self) -> None:
        """Purpose: Run the initialize workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        with self.connect() as con:
            if self.config.database_auto_schema:
                self.create_schema(con)
            else:
                required_tables = {"delivery_lists", "line_items", "users", "roles", "racks", "bays", "system_metadata"}
                rows = con.execute_tsql(
                    "SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo')"
                ).fetchall()
                existing_tables = {str(row["name"]) for row in rows}
                missing = sorted(required_tables - existing_tables)
                if missing:
                    raise RuntimeError(
                        "Azure SQL schema initialization is disabled, but required tables are missing: "
                        + ", ".join(missing)
                    )
            self.ensure_rack_destination_override_columns(con)
            self.seed_customer_route_rules(con)
            self.seed_demo_data(con)
            self.seed_security_data(con)
            self.seed_bays(con)
            self.repair_manual_assign_bay_visibility(con)
            self.seed_bay_auto_assign_settings(con)
            self.seed_racks(con)
            self.repair_route_stage_memberships_if_needed(con)
        self.cleanup_old_bay_events(force=True)

    def health(self) -> dict[str, Any]:
        """Purpose: Run the health workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        with self.connect() as con:
            row = con.execute_tsql(
                "SELECT DB_NAME() AS database_name, CAST(SERVERPROPERTY('ServerName') AS nvarchar(256)) AS server_name"
            ).fetchone()
        return {
            "ok": True,
            "mode": self.database_type,
            "database": row["database_name"] if row else "Azure SQL",
            "server": row["server_name"] if row else "",
            "environment": self.config.environment,
            "authMode": self.config.auth_mode,
        }

    def create_schema(self, con: AzureSqlConnection) -> None:
        """Purpose: Create schema for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        schema_path = self.config.root / "database" / "azure_schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Azure SQL schema file was not found: {schema_path}")
        script = schema_path.read_text(encoding="utf-8")
        batches = re.split(r"^\s*GO\s*$", script, flags=re.IGNORECASE | re.MULTILINE)
        for batch in batches:
            if batch.strip():
                con.execute_tsql(batch)
        self._upgrade_v096_columns(con)
        for migration in MIGRATIONS:
            con.execute_tsql(
                """
                MERGE dbo.schema_migrations AS target
                USING (SELECT ? AS version, ? AS name, ? AS checksum, ? AS app_version) AS source
                ON target.version = source.version
                WHEN NOT MATCHED THEN
                    INSERT (version, name, checksum, applied_at_utc, execution_ms, app_version)
                    VALUES (source.version, source.name, source.checksum, SYSUTCDATETIME(), 0, source.app_version);
                """,
                (migration.version, migration.name, migration.checksum, "097"),
            )
            installed = con.execute_tsql(
                "SELECT checksum FROM dbo.schema_migrations WHERE version = ?", (migration.version,)
            ).fetchone()
            if not installed or str(installed["checksum"]) != migration.checksum:
                raise MigrationError(f"Azure SQL migration {migration.version:03d} checksum mismatch")

    def ensure_column(self, con: AzureSqlConnection, table: str, column: str, definition: str) -> None:
        """Purpose: Validate column for the delivery-list scanner workflow.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Inspects current state, applies only missing or outdated changes, and leaves repeated runs safe and idempotent.
        """
        exists = con.execute_tsql(
            """
            SELECT 1 AS present
            FROM sys.columns
            WHERE object_id = OBJECT_ID(?) AND name = ?
            """,
            (f"dbo.{table}", column),
        ).fetchone()
        if exists:
            return

        clean_definition = " ".join(str(definition or "").split())
        clean_definition = re.sub(r"^TEXT\b", "nvarchar(max)", clean_definition, flags=re.IGNORECASE)
        clean_definition = re.sub(r"^INTEGER\b", "int", clean_definition, flags=re.IGNORECASE)
        clean_definition = re.sub(r"^REAL\b", "float", clean_definition, flags=re.IGNORECASE)
        clean_definition = re.sub(
            r"DEFAULT\s+'([^']*)'",
            lambda match: f"DEFAULT (N'{match.group(1)}')",
            clean_definition,
            flags=re.IGNORECASE,
        )
        clean_definition = re.sub(
            r"DEFAULT\s+(\d+)",
            lambda match: f"DEFAULT ({match.group(1)})",
            clean_definition,
            flags=re.IGNORECASE,
        )
        con.execute_tsql(f"ALTER TABLE dbo.[{table}] ADD [{column}] {clean_definition}")

def create_store(config: AppConfig) -> BaseDeliveryStore:
    """Purpose: Create store for the delivery-list scanner workflow.

    Effects: This function reads or updates shared application state.
    Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
    """
    database_type = str(config.database_type or "sqlite").strip().lower()
    if database_type == "sqlite":
        return SQLiteDeliveryStore(config)
    if database_type in {"azure-sql", "azure_sql", "sqlserver", "sql-server", "mssql"}:
        return AzureSqlDeliveryStore(config)
    raise NotImplementedError(
        f"Database type {config.database_type!r} is not supported. "
        "Use 'sqlite' for local development or 'azure-sql' for Microsoft Azure SQL."
    )
