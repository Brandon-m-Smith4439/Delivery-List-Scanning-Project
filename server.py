#!/usr/bin/env python
# File: server.py
# Delivery List Scanner local web/API server.
#
# Code map for future edits:
# - Render helpers at the top generate printable delivery/rack reports.
# - Handler.do_GET and Handler.do_POST route HTTP requests to backend/store.py.
# - Keep business rules in backend/store.py where possible; this file should mainly
#   translate HTTP requests/responses and render printable HTML.

"""Local pilot server for the delivery-list scanner web app."""

from __future__ import annotations

import json
import html
import gzip
import io
import os
import re
import secrets
import threading
import time
import traceback
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from backend.automation_control import DeliveryAutomationController
from backend.config import load_config
from backend.import_safety import install_safe_delivery_import
from backend.operations import OperationsFeatureService
from backend.store import (
    SESSION_COOKIE_NAME,
    canonical_clear_glass_label,
    canonical_permission_name,
    create_store,
    public_route_label,
    request_station,
    request_user_name,
)


ROOT = Path(__file__).resolve().parent
CONFIG = load_config(ROOT)
STORE = create_store(CONFIG)
install_safe_delivery_import(STORE)
OPERATIONS = OperationsFeatureService(STORE, CONFIG, ROOT)
DELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG, STORE)

# v0.340: the Admin shell may be opened by a purpose-built role without the
# broad view_admin permission. Keep dashboard access aligned with every current
# Admin tool while each endpoint below still enforces its own narrower action.
ADMIN_DASHBOARD_PERMISSIONS = (
    "view_admin",
    "reset_delivery_lists",
    "import_delivery_lists",
    "edit_delivery_list_items",
    "create_delivery_list_orders",
    "delete_delivery_list_items",
    "delete_delivery_lists",
    "review_superseded_orders",
    "manage_users",
    "manage_user_access",
    "manage_user_assignments",
    "manage_roles",
    "view_sessions",
    "manage_stations",
    "manage_route_rules",
    "manage_customer_emails",
    "manage_lookup_values",
    "manage_automation",
    "manage_cross_date_scanning",
    "manage_reject_settings",
    "manage_bay_layout",
    "manage_bay_scanner_rules",
    "manage_bay_auto_assigner",
    "manage_racks",
)

# Action History is not one global security capability. Each GUI history endpoint
# must be readable only by a role that can legitimately access that GUI. This
# closes the old avenue where any single Admin-like permission could query a
# different workspace's audit records by changing the context query string.
ACTION_HISTORY_CONTEXT_PERMISSIONS = {
    "deliveryLists": ("edit_delivery_list_items", "create_delivery_list_orders", "delete_delivery_list_items", "delete_delivery_lists", "reset_delivery_lists", "import_delivery_lists"),
    "deliveryActions": ("reset_delivery_lists", "delete_delivery_lists"),
    "supersededOrders": ("view_admin", "review_superseded_orders"),
    "manualEdit": ("edit_delivery_list_items", "create_delivery_list_orders", "delete_delivery_list_items"),
    "users": ("manage_users", "manage_user_access", "manage_user_assignments"),
    "roles": ("manage_roles",),
    "sessions": ("view_sessions",),
    "stations": ("manage_stations",),
    "customerRoutes": ("manage_route_rules",),
    "customerEmails": ("manage_customer_emails",),
    "lookups": ("manage_lookup_values",),
    "rejectSettings": ("manage_reject_settings",),
    "bayScannerRules": ("manage_bay_scanner_rules", "manage_bay_auto_assigner"),
    "crossDateScanning": ("manage_cross_date_scanning", "manage_bay_scanner_rules"),
    "bayAutoAssigner": ("manage_bay_auto_assigner",),
    "racks": ("view_racks", "scan_racks", "manage_racks", "transfer_rack_contents"),
    "rackForm": ("manage_racks",),
    "rackSetForm": ("manage_racks",),
    "recentScans": ("view_scan_history", "correct_scans"),
    "rack-details": ("view_racks", "scan_racks", "manage_racks", "transfer_rack_contents"),
    "racks-history": ("view_racks", "scan_racks", "manage_racks", "transfer_rack_contents"),
    "packing-history": ("view_racks", "print_export"),
    "oldBays": ("view_bays", "run_bay_checks", "clear_bay_items"),
    "rush": ("view_bays", "manage_rush_work"),
    "manageBayItems": ("view_bays", "assign_bay_items", "move_bay_items", "clear_bay_items"),
    "editBays": ("manage_bay_layout",),
}


PRINT_PACKAGE_SESSION_TTL_SECONDS = 15 * 60
PRINT_PACKAGE_SESSIONS: dict[str, dict] = {}
PRINT_PACKAGE_SESSION_LOCK = threading.Lock()


def print_package_user_key(user: dict | None) -> str:
    """Return a stable identity key for one authenticated print-session owner."""
    user = user or {}
    return str(user.get("id") or user.get("username") or user.get("name") or "").strip().lower()


def normalize_print_package_request(payload: dict) -> tuple[list[str], dict, int, str]:
    """Normalize the browser's exact preview/output selection contract."""
    raw_ids = payload.get("listIds") or payload.get("listId") or []
    if isinstance(raw_ids, str):
        raw_ids = [part for part in raw_ids.split(",") if part]
    list_ids = list(dict.fromkeys(str(value).strip() for value in raw_ids if str(value).strip()))

    raw_filters = payload.get("filters") or {}
    filters = {str(key): str(value) for key, value in raw_filters.items() if value not in (None, "", [], {})}

    line_item_ids = [str(value).strip() for value in payload.get("lineItemIds") or [] if str(value).strip()]
    row_keys = [str(value).strip() for value in payload.get("rowKeys") or [] if str(value).strip()]
    if line_item_ids:
        filters["lineItemIdsExact"] = json.dumps(list(dict.fromkeys(line_item_ids)))
    if row_keys:
        filters["rowKeysExact"] = json.dumps(list(dict.fromkeys(row_keys)))

    try:
        copies = max(1, min(int(payload.get("copies") or 1), 10))
    except (TypeError, ValueError):
        copies = 1
    orientation = str(payload.get("orientation") or "portrait").strip().lower()
    if orientation not in {"portrait", "landscape"}:
        orientation = "portrait"
    filters["copies"] = str(copies)
    filters["orientation"] = orientation
    return list_ids, filters, copies, orientation


def create_print_package_session(user: dict, list_ids: list[str], filters: dict) -> str:
    """Create a short-lived same-user token for print/export GET windows."""
    now = time.time()
    token = secrets.token_urlsafe(24)
    owner = print_package_user_key(user)
    with PRINT_PACKAGE_SESSION_LOCK:
        expired = [
            key
            for key, value in PRINT_PACKAGE_SESSIONS.items()
            if now - float(value.get("createdAt") or 0) > PRINT_PACKAGE_SESSION_TTL_SECONDS
        ]
        for key in expired:
            PRINT_PACKAGE_SESSIONS.pop(key, None)
        PRINT_PACKAGE_SESSIONS[token] = {
            "createdAt": now,
            "owner": owner,
            "listIds": list(list_ids),
            "filters": dict(filters),
        }
    return token


def read_print_package_session(token: str, user: dict) -> dict | None:
    """Return one unexpired print/export session only to its creating user."""
    clean_token = str(token or "").strip()
    if not clean_token:
        return None
    now = time.time()
    owner = print_package_user_key(user)
    with PRINT_PACKAGE_SESSION_LOCK:
        record = PRINT_PACKAGE_SESSIONS.get(clean_token)
        if not record:
            return None
        if now - float(record.get("createdAt") or 0) > PRINT_PACKAGE_SESSION_TTL_SECONDS:
            PRINT_PACKAGE_SESSIONS.pop(clean_token, None)
            return None
        if not owner or str(record.get("owner") or "") != owner:
            return None
        return {"listIds": list(record.get("listIds") or []), "filters": dict(record.get("filters") or {})}


def esc(value: object) -> str:
    """Purpose: Run the esc workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return html.escape(str(value if value is not None else ""))


def print_lifecycle_script(delay_ms: int = 300) -> str:
    """Notify the app after print preview closes and close script-opened print windows."""
    delay = max(int(delay_ms or 0), 0)
    return f"""
    <script>
      (function() {{
        let completed = false;
        function notifyComplete() {{
          if (completed) return;
          completed = true;
          const target = window.opener && !window.opener.closed
            ? window.opener
            : (window.parent && window.parent !== window ? window.parent : null);
          if (target) target.postMessage({{ type: 'delivery-print-complete' }}, window.location.origin);
          if (window.opener && !window.opener.closed) setTimeout(function() {{ window.close(); }}, 120);
        }}
        window.addEventListener('afterprint', notifyComplete);
        window.addEventListener('pagehide', notifyComplete);
        window.addEventListener('beforeunload', notifyComplete);
        window.addEventListener('load', function() {{ setTimeout(function() {{ window.print(); }}, {delay}); }});
      }})();
    </script>
    """


def print_display_date(value: object) -> str:
    """Return a plain M/D/YYYY date for printed sheets and packing lists.

    Keep print headers simple: the stage belongs in the title, and the date
    belongs in one obvious place. Future print changes should use this helper
    instead of rebuilding stage/date labels in multiple spots.
    """
    text = str(value or "").strip()
    parts = text.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        year, month, day = (int(part) for part in parts)
        return f"{month}/{day}/{year}"
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text)
    if match:
        month, day, year = match.groups()
        year_text = str(int(year) + 2000) if len(year) == 2 else str(int(year))
        return f"{int(month)}/{int(day)}/{year_text}"
    return text


def enrich_reject_match_details(payload: dict) -> dict:
    """Add display-safe piece details to the maintained reject match response.

    The operations service continues to own match identity and delivery-date
    grouping. This helper only enriches those verified matches with fields the
    reject review GUI needs, avoiding a second client-side lookup or guess.
    """
    matches = payload.get("matches") if isinstance(payload, dict) else None
    if not isinstance(matches, list) or not matches:
        return payload

    with STORE.connect() as con:
        for match in matches:
            if not isinstance(match, dict):
                continue
            delivery_date = str(match.get("delivery_date") or "").strip()
            order_no = str(match.get("order_no") or "").strip()
            item_no = str(match.get("item_no") or "").strip()
            if not delivery_date or not order_no or not item_no:
                continue
            row = con.execute(
                """
                SELECT
                    MAX(li.dimensions) AS dimensions,
                    MAX(li.product) AS product,
                    MAX(li.route) AS route,
                    MAX(li.scanned_qty) AS scanned_qty,
                    MAX(li.process_state) AS process_state,
                    MAX(li.queue_state) AS queue_state,
                    MAX(li.suggested_bay) AS suggested_bay,
                    MAX(
                        CASE
                            WHEN ba.status NOT IN ('Cleared', 'Cancelled') THEN COALESCE(b.bay_code, '')
                            ELSE ''
                        END
                    ) AS current_bay
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                LEFT JOIN bay_assignments ba ON ba.line_item_id = li.id
                LEFT JOIN bays b ON b.id = ba.bay_id
                WHERE dl.status = 'active'
                  AND dl.delivery_date = ?
                  AND li.order_no = ?
                  AND li.item_no = ?
                """,
                (delivery_date, order_no, item_no),
            ).fetchone()
            if row:
                match.update({
                    "dimensions": str(row["dimensions"] or ""),
                    "product": str(row["product"] or match.get("product") or ""),
                    "route": str(row["route"] or ""),
                    "scanned_qty": int(row["scanned_qty"] or 0),
                    "process_state": str(row["process_state"] or ""),
                    "queue_state": str(row["queue_state"] or ""),
                    "suggested_bay": str(row["suggested_bay"] or ""),
                    "current_bay": str(row["current_bay"] or ""),
                })
    return payload


CODE39 = {
    "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn", "4": "nnnwwnnnw",
    "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw", "8": "wnnwnnwnn", "9": "nnwwnnwnn",
    "A": "wnnnnwnnw", "B": "nnwnnwnnw", "C": "wnwnnwnnn", "D": "nnnnwwnnw", "E": "wnnnwwnnn",
    "F": "nnwnwwnnn", "G": "nnnnnwwnw", "H": "wnnnnwwnn", "I": "nnwnnwwnn", "J": "nnnnwwwnn",
    "K": "wnnnnnnww", "L": "nnwnnnnww", "M": "wnwnnnnwn", "N": "nnnnwnnww", "O": "wnnnwnnwn",
    "P": "nnwnwnnwn", "Q": "nnnnnnwww", "R": "wnnnnnwwn", "S": "nnwnnnwwn", "T": "nnnnwnwwn",
    "U": "wwnnnnnnw", "V": "nwwnnnnnw", "W": "wwwnnnnnn", "X": "nwnnwnnnw", "Y": "wwnnwnnnn",
    "Z": "nwwnwnnnn", "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "$": "nwnwnwnnn",
    "/": "nwnwnnnwn", "+": "nwnnnwnwn", "%": "nnnwnwnwn", "*": "nwnnwnwnn",
}


def code39_svg(value: str) -> str:
    """Purpose: Run the code39 SVG workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    text = "".join(ch for ch in str(value or "").upper() if ch in CODE39 and ch != "*")
    encoded = f"*{text}*"
    narrow, wide, gap, height = 2, 5, 2, 72
    x = 0
    rects = []
    for char in encoded:
        pattern = CODE39[char]
        for index, mark in enumerate(pattern):
            width = wide if mark == "w" else narrow
            if index % 2 == 0:
                rects.append(f'<rect x="{x}" y="0" width="{width}" height="{height}"/>')
            x += width
        x += gap
    return f'<svg class="rack-barcode" viewBox="0 0 {x} {height}" role="img" aria-label="{esc(text)}" preserveAspectRatio="none">{"".join(rects)}</svg>'


def render_item_row(item: dict) -> str:
    """Purpose: Render item row for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
    """
    job_text = item.get("job") or item.get("product")
    customer_text = item.get("customer")
    # Keep printed list rows to one visual line per item. Long job/customer names
    # were wrapping, which made the browser spill one logical page onto an extra
    # physical sheet and broke the list page count.
    return f"""
            <tr>
              <td class="print-truncate job-cell" title="{esc(job_text)}">{esc(job_text)}</td>
              <td class="print-nowrap order-cell">{esc(item.get("order"))}</td>
              <td class="print-nowrap item-cell">{esc(item.get("item"))}</td>
              <td class="print-nowrap qty-cell">{esc(item.get("qty"))}</td>
              <td class="print-truncate dimensions-cell" title="{esc(item.get("dimensions"))}">{esc(item.get("dimensions"))}</td>
              <td class="print-truncate customer-cell" title="{esc(customer_text)}">{esc(customer_text)}</td>
              <td class="print-nowrap route-cell">{esc(public_route_label(item.get("route")))}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """


def paginate_item_rows(items: list[dict], rows_per_page: int = 23, first_page_rows: int | None = None) -> list[str]:
    """Build explicit one-paper-page chunks for printed delivery lists.

    Important for future edits: the browser print preview only understands the
    sections we give it. If this number is too high, Chrome/Edge may split one
    logical list page across two physical pieces of paper, which makes the page
    label wrong. Continuation pages use a compact title and can safely hold the
    normal row count. Page 1 has a taller title/header, so it gets a smaller row
    allowance to keep the Notes section on the same physical sheet.
    """
    if not items:
        return ['<tr><td colspan="8">No printable rows.</td></tr>']

    first_page_limit = max(1, first_page_rows if first_page_rows is not None else rows_per_page - 2)
    continuation_limit = max(1, rows_per_page)

    pages: list[str] = []
    current_rows: list[str] = []
    current_count = 0
    current_product = object()

    def current_row_limit() -> int:
        """Purpose: Run the current row limit workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return first_page_limit if not pages else continuation_limit

    def flush_page() -> None:
        """Purpose: Run the flush page workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        nonlocal current_rows, current_count, current_product
        if current_rows:
            pages.append("".join(current_rows))
        current_rows = []
        current_count = 0
        current_product = object()

    sorted_items = sorted(
        items,
        key=lambda row: (
            str(row.get("product") or row.get("job") or ""),
            int(row.get("order") or 0),
            int(row.get("item") or 0),
        ),
    )
    for item in sorted_items:
        product = item.get("product") or item.get("job") or "Unspecified Glass"
        needs_group_row = product != current_product
        needed_rows = 1 + (1 if needs_group_row else 0)
        if current_rows and current_count + needed_rows > current_row_limit():
            flush_page()
            needs_group_row = True

        if needs_group_row:
            current_product = product
            current_rows.append(f'<tr class="glass-group"><td colspan="8">{esc(product)}</td></tr>')
            current_count += 1

        if current_count >= current_row_limit() and current_rows:
            flush_page()
            current_product = product
            current_rows.append(f'<tr class="glass-group"><td colspan="8">{esc(product)}</td></tr>')
            current_count += 1

        current_rows.append(render_item_row(item))
        current_count += 1

    flush_page()
    return pages


def render_sheet(
    title: str,
    subtitle: str,
    items: list[dict],
    sheet_class: str = "",
    badge: str = "",
    printed_at: str = "",
) -> str:
    """Purpose: Render sheet for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
    """
    badge_html = f'<span class="sheet-badge">{esc(badge)}</span>' if badge else ""
    printed_at_html = f'<p class="printed-at">Printed at: {esc(printed_at)}</p>' if printed_at else ""
    item_pages = paginate_item_rows(items)
    page_total = len(item_pages)
    sections = []
    for page_number, rows_html in enumerate(item_pages, start=1):
        continuation = page_number > 1
        # This is the list page count only. It intentionally does not count duplicate physical copies.
        page_label = f"List page {page_number} of {page_total}"
        if continuation:
            header_html = f"""
      <div class="sheet-page-top">{esc(page_label)}</div>
      <header class="sheet-header sheet-header-compact">
        <div>
          {badge_html}
          <h2>{esc(title)}</h2>
          <p>Continuation sheet - {esc(page_label)}</p>
          {printed_at_html}
        </div>
        <div class="copy-box"><span>Checked By: <i class="write-line checked-line"></i></span><span>Date: <i class="write-line date-line"></i></span></div>
      </header>
            """
        else:
            subtitle_html = f'<p>{esc(subtitle)}</p>' if subtitle else ""
            header_html = f"""
      <div class="sheet-page-top">{esc(page_label)}</div>
      <header class="sheet-header">
        <div>
          {badge_html}
          <h1>{esc(title)}</h1>
          {printed_at_html}
          {subtitle_html}
        </div>
        <div class="copy-box"><span>Checked By: <i class="write-line checked-line"></i></span><span>Date: <i class="write-line date-line"></i></span></div>
      </header>
            """
        sections.append(
            f"""
    <section class="sheet {sheet_class}">
      {header_html}
      <table class="delivery-print-table">
        <colgroup>
          <col class="job-col">
          <col class="order-col">
          <col class="item-col">
          <col class="qty-col">
          <col class="dimensions-col">
          <col class="customer-col">
          <col class="route-col">
          <col class="check-col">
        </colgroup>
        <thead>
          <tr><th>Job Nr.</th><th>Order Nr.</th><th>Item Nr.</th><th>Qty.</th><th>Dimensions</th><th>Customer</th><th>Route</th><th>Check</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <div class="notes"><strong>Notes:</strong><span></span></div>
    </section>
            """
        )
    return "".join(sections)


def printed_item_is_remake(item: dict) -> bool:
    """Return True when a printed row should be marked as a remake/RM.

    Packing lists are used on the floor away from the screen, so remake pieces
    need a visible RM flag even when the route/stage context is not obvious.
    """
    text = " ".join(str(item.get(key, "")) for key in ("remake", "processState", "queueState", "process_state", "queue_state")).upper()
    return "REMAKE" in text or re.search(r"\bRM\b", text) is not None

def render_rack_packing_list(payload: dict) -> str:
    """Purpose: Render rack packing list for the delivery-list scanner workflow.

    Effects: This function reads or updates shared application state.
    Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
    """
    rack = payload.get("rack") or {}
    barcode = rack.get("barcode") or f"RACK-{rack.get('code', '')}"
    destination = rack.get("destination") or "Indian Trail"
    is_dtc = str(destination).strip().upper() == "DTC"
    all_items = rack.get("items") or []

    destination_payload = rack.get("destinationAddress") or {}
    default_address = destination_payload.get("address") or "Address not configured"

    def customer_date_groups() -> list[dict]:
        """Purpose: Run the customer date groups workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        if not is_dtc:
            return [
                {
                    "title": rack.get("name") or rack.get("code"),
                    "deliveryDate": rack.get("deliveryDate") or "",
                    "deliveryLabel": rack.get("deliveryLabel") or "",
                    "customer": "",
                    "address": default_address,
                    "items": all_items,
                }
            ]

        groups: dict[tuple[str, str, str], dict] = {}
        for item in all_items:
            customer = str(item.get("customer") or "DTC Customer").strip() or "DTC Customer"
            delivery_date = str(item.get("deliveryDate") or rack.get("deliveryDate") or "").strip()
            address = str(item.get("destinationAddress") or default_address or "No DTC customer address on file").strip()
            key = (customer.lower(), delivery_date, address.lower())
            if key not in groups:
                groups[key] = {
                    "title": f"{rack.get('name') or rack.get('code')} - {customer}",
                    "deliveryDate": delivery_date,
                    "deliveryLabel": print_display_date(delivery_date) if delivery_date else rack.get("deliveryLabel") or "",
                    "customer": customer,
                    "address": address,
                    "items": [],
                }
            groups[key]["items"].append(item)
        return list(groups.values()) or [
            {
                "title": rack.get("name") or rack.get("code"),
                "deliveryDate": rack.get("deliveryDate") or "",
                "deliveryLabel": rack.get("deliveryLabel") or "",
                "customer": "DTC Customer",
                "address": default_address,
                "items": [],
            }
        ]

    def rows_for_items(items: list[dict]) -> str:
        """Purpose: Run the rows for items workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        # v0.460: packing/report grouping uses the same explicit Clear
        # Annealed/Tempered identity as Scan and Statistics while preserving the
        # imported product field shown in the detail row.
        def item_glass_type(row: dict) -> str:
            raw = row.get("glassType") or row.get("product") or row.get("job") or "Other Glass"
            return canonical_clear_glass_label(raw) or "Other Glass"

        rows = []
        sorted_items = sorted(
            items or [],
            key=lambda item: (
                item_glass_type(item).lower(),
                str(item.get("job") or ""),
                str(item.get("order") or ""),
                str(item.get("item") or ""),
            ),
        )
        current_glass = None
        for item in sorted_items:
            glass_type = item_glass_type(item)
            if glass_type != current_glass:
                current_glass = glass_type
                group_qty = sum(
                    int(row.get("rackQty") or row.get("qty") or 0)
                    for row in sorted_items
                    if item_glass_type(row) == glass_type
                )
                rows.append(
                    f'<tr class="packing-glass-group"><td colspan="10"><strong>{esc(glass_type)}</strong><span>{esc(group_qty)} pcs</span></td></tr>'
                )
            rows.append(
                f"""
                <tr>
                  <td>{esc(print_display_date(item.get("deliveryDate") or item.get("deliveryLabel")))}</td>
                  <td>{esc(item.get("job") or item.get("product"))}</td>
                  <td>{esc(item.get("order"))}</td>
                  <td>{esc(item.get("item"))}</td>
                  <td>{esc(item.get("rackQty") or item.get("qty"))}</td>
                  <td>{esc(item.get("dimensions"))}</td>
                  <td>{esc(item.get("customer"))}</td>
                  <td>{esc(public_route_label(item.get("route")))}</td>
                  <td class="flag-cell">{'RM' if printed_item_is_remake(item) else ''}</td>
                  <td class="check-cell">&#9744;</td>
                </tr>
                """
            )
        return "".join(rows) or '<tr><td colspan="10">No pieces are currently assigned to this rack.</td></tr>'

    groups = customer_date_groups()
    group_count = len(groups)

    def sheet_html(group: dict, index: int) -> str:
        """Purpose: Run the sheet HTML workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        delivery_label = group.get("deliveryLabel") or rack.get("deliveryLabel") or ""
        delivery_suffix = f" - {esc(delivery_label)}" if delivery_label else ""
        title = group.get("title") or rack.get("name") or rack.get("code")
        customer_html = ""
        if is_dtc:
            customer_html = f"""
            <div class="destination-stop primary-stop">
              <strong>{esc(group.get("customer") or "DTC Customer")}</strong>
              <span>{esc(group.get("address") or default_address)}</span>
            </div>
            """
        signature_html = """
        <section class="signature-section">
          <div><strong>Customer Signature</strong><span></span></div>
          <div><strong>Date</strong><span></span></div>
        </section>
        """ if is_dtc else ""
        page_note = f"DTC customer slip {index} of {group_count}" if is_dtc and group_count > 1 else "Packing List"
        qty = sum(int(item.get("rackQty") or item.get("qty") or 0) for item in group.get("items") or [])
        destination_card_html = f"""
        <section class="destination-card destination-card-single">
          <div class="destination-card-main">
            <small>Destination Address</small>
            <strong>{esc(group.get("customer") or destination if is_dtc else destination)}</strong>
            <span>{esc(group.get("address") or default_address)}</span>
          </div>
        </section>
        """
        return f"""
      <section class="packing-sheet">
        <div class="packing-document-accent"></div>
        <header class="packing-header">
          <div class="packing-logo-box">
            <img class="packing-logo" src="/static/images/barefoot-company-builders-firstsource-print-logo.png?v=20260825-v0.385" alt="Barefoot & Company" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <span class="packing-logo-fallback" style="display:none;">Barefoot &amp; Company</span>
          </div>
          <div class="packing-title">
            <small>{esc(page_note)}</small>
            <h1>{esc(title)}{delivery_suffix}</h1>
            <div class="rack-meta">
              <span><b>Rack Type</b>{esc(rack.get("type"))}</span>
              <span><b>Destination</b>{esc(destination)}</span>
              <span><b>Status</b>{esc(rack.get("status"))}</span>
              <span><b>Total Pieces</b>{esc(qty or rack.get("qty"))}</span>
            </div>
            <div class="packing-checkoff"><span>Checked By <i></i></span><span>Date <i></i></span></div>
          </div>
          <div class="barcode-box">
            {code39_svg(str(barcode))}
            <div class="barcode-text">*{esc(barcode)}*</div>
          </div>
        </header>
        {destination_card_html}
        <table>
          <thead><tr><th>Delivery Date</th><th>Job Nr.</th><th>Order Nr.</th><th>Item Nr.</th><th>Qty</th><th>Dimensions</th><th>Customer</th><th>Route</th><th>Flags</th><th>Check</th></tr></thead>
          <tbody>{rows_for_items(group.get("items") or [])}</tbody>
        </table>
        {signature_html}
      </section>
        """

    sheets = "".join(sheet_html(group, index) for index, group in enumerate(groups, start=1))

    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{esc(rack.get("name") or rack.get("code"))} Packing List</title>
      <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; color: #07122f; font-family: "Segoe UI", Arial, sans-serif; background: #f6f8fb; }}
        button {{ margin: 12px 18px 0; border: 0; border-radius: 7px; background: #072a63; color: #fff; padding: 9px 16px; font-weight: 900; cursor: pointer; }}
        .packing-sheet {{ width: min(1460px, calc(100% - 32px)); margin: 16px auto; padding: 18px 20px 14px; background: #fff; border: 1px solid #444; break-inside: avoid; page-break-inside: avoid; }}
        .packing-sheet:last-child {{ page-break-after: auto; }}
        .packing-document-accent {{ height: 4px; margin: -18px -20px 14px; background: #072a63; }}
        .packing-header {{ display: grid; grid-template-columns: 190px minmax(320px, 1fr) 285px; gap: 18px; align-items: center; border-bottom: 3px solid #072a63; padding-bottom: 10px; margin-bottom: 10px; }}
        .packing-logo-box {{ min-height: 90px; display: grid; align-content: center; }}
        .packing-logo {{ width: 176px; max-width: 100%; max-height: 82px; object-fit: contain; object-position: left center; display: block; }}
        .packing-logo-fallback {{ color: #071633; font-size: 15px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }}
        .packing-title small {{ display: block; color: #526078; font-size: 10px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }}
        h1 {{ margin: 4px 0 8px; color: #041a3d; font-size: 26px; line-height: 1.12; text-transform: uppercase; overflow-wrap: anywhere; }}
        .rack-meta {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin-top: 7px; }}
        .rack-meta span {{ min-width: 0; border: 1px solid #d9e1ee; background: #f8fafc; padding: 6px 7px; color: #263550; font-size: 11px; font-weight: 800; }}
        .rack-meta b {{ display: block; color: #526078; font-size: 8.5px; text-transform: uppercase; letter-spacing: .04em; }}
        .packing-checkoff {{ display: flex; gap: 12px; margin-top: 7px; color: #41506c; font-size: 9px; font-weight: 850; }}
        .packing-checkoff span {{ display: inline-flex; align-items: end; gap: 5px; }}
        .packing-checkoff i {{ width: 88px; height: 12px; border-bottom: 1px solid #56647a; }}
        .barcode-box {{ width: 100%; text-align: center; border: 1px solid #aebccc; background: #fff; padding: 8px 10px; }}
        .rack-barcode {{ width: 100%; height: 65px; display: block; }}
        .barcode-text {{ margin-top: 4px; font-size: 15px; font-weight: 900; letter-spacing: 1px; }}
        .destination-card {{ margin: 10px 0 0; border: 1px solid #c6d1df; border-left: 4px solid #2f7ab5; background: #f8fbfd; padding: 8px 10px; }}
        .destination-card small {{ display: block; color: #526078; font-size: 8.5px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; }}
        .destination-card strong {{ display: block; color: #173b65; font-size: 15px; margin-top: 2px; }}
        .destination-card span {{ display: block; color: #526078; font-size: 11px; font-weight: 750; margin-top: 1px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11.5px; line-height: 1.22; table-layout: fixed; }}
        th, td {{ border: 1px solid #d9e1ee; padding: 6px 7px; text-align: left; vertical-align: top; overflow: hidden; text-overflow: ellipsis; }}
        th {{ background: #f1f1f1; color: #041a3d; font-size: 10.5px; font-weight: 900; }}
        tr, td, th {{ break-inside: avoid; page-break-inside: avoid; }}
        .packing-glass-group td {{ background: #e9e9e9 !important; color: #173b65; padding-top: 6px; padding-bottom: 6px; font-size: 10.5px; font-weight: 900; text-transform: uppercase; }}
        .packing-glass-group td {{ display: table-cell; }}
        .packing-glass-group strong {{ float: left; }}
        .packing-glass-group span {{ float: right; color: #526078; font-size: 9px; }}
        tbody tr:nth-child(even):not(.packing-glass-group) td {{ background: #fbfcfd; }}
        th:nth-child(1), td:nth-child(1) {{ width: 11%; white-space: nowrap; }}
        th:nth-child(2), td:nth-child(2) {{ width: 16%; }}
        th:nth-child(3), td:nth-child(3) {{ width: 9%; }}
        th:nth-child(4), td:nth-child(4) {{ width: 7%; }}
        th:nth-child(5), td:nth-child(5) {{ width: 5%; text-align: center; }}
        th:nth-child(6), td:nth-child(6) {{ width: 14%; }}
        th:nth-child(7), td:nth-child(7) {{ width: 18%; }}
        th:nth-child(8), td:nth-child(8) {{ width: 8%; }}
        th:nth-child(9), td:nth-child(9) {{ width: 5%; text-align: center; }}
        th:nth-child(10), td:nth-child(10) {{ width: 5%; text-align: center; }}
        .check-cell {{ text-align: center; font-size: 17px; }}
        .signature-section {{ margin-top: 12px; display: grid; grid-template-columns: 2fr 1fr; gap: 14px; }}
        .signature-section div {{ min-height: 52px; border: 1px solid #444; padding: 7px; font-size: 10px; }}
        .signature-section span {{ display: block; height: 25px; border-bottom: 1px solid #444; margin-top: 9px; }}
        @page {{ size: letter landscape; margin: 0.25in; }}
        @media print {{
          body {{ background: #fff; }}
          button {{ display: none; }}
          .packing-sheet {{ width: auto; margin: 0; padding: .04in .06in .03in; border: 0; page-break-after: always; }}
          .packing-sheet:last-child {{ page-break-after: auto; }}
          .packing-document-accent {{ margin: -.04in -.06in 10px; }}
          .packing-header {{ grid-template-columns: 165px minmax(300px, 1fr) 250px; gap: 10px; }}
          .packing-logo {{ width: 158px; max-height: 72px; }}
          .rack-barcode {{ height: 58px; }}
        }}
      </style>
    </head>
    <body>
      <button onclick="window.print()">Print</button>
      {sheets}
      {print_lifecycle_script(350)}
    </body>
    </html>
    """

def render_customer_email_manifest_pdf_page(email: dict) -> str:
    """Purpose: Render customer email manifest PDF page for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
    """
    payload = email.get("payload") or {}
    items = payload.get("items") or []
    customer = email.get("customerName") or "Customer"
    delivery_date = email.get("deliveryDate") or ""
    piece_qty = payload.get("pieceQty") or sum(int(item.get("qty") or 0) for item in items)
    item_count = payload.get("itemCount") or len(items)

    if not items:
        rows_html = '<tr><td colspan="6">No detailed manifest rows were saved for this older draft. Open the text draft for the original message body.</td></tr>'
    else:
        rows_html = "".join(
            f"""
            <tr>
              <td>{esc(item.get('job') or item.get('product') or '-')}</td>
              <td>{esc(item.get('order'))}</td>
              <td>{esc(item.get('item'))}</td>
              <td>{esc(item.get('qty'))}</td>
              <td>{esc(item.get('dimensions') or '-')}</td>
              <td>{esc(public_route_label(item.get('route')))}</td>
            </tr>
            """
            for item in items
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{esc(customer)} Order Manifest</title>
  <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 24px; color: #071633; font-family: Arial, sans-serif; background: #fff; }}
    .print-button {{ margin-bottom: 14px; border: 1px solid #071633; border-radius: 8px; background: #071633; color: #fff; font-weight: 800; padding: 8px 12px; }}
    .manifest-sheet {{ border: 1px solid #d8e2ef; border-radius: 14px; padding: 24px; box-shadow: 0 16px 34px rgba(8, 38, 90, 0.10); }}
    header {{ display: grid; grid-template-columns: 190px minmax(0, 1fr); gap: 18px; align-items: start; border-bottom: 3px solid #071633; padding-bottom: 18px; }}
    .manifest-logo {{ width: 170px; max-height: 86px; object-fit: contain; object-position: left top; filter: drop-shadow(0 4px 7px rgba(7, 22, 51, 0.14)); }}
    .fallback-logo {{ display: none; font-weight: 950; letter-spacing: .08em; text-transform: uppercase; }}
    .manifest-title small {{ color: #526078; font-size: 11px; font-weight: 950; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ margin: 4px 0 8px; font-size: 32px; line-height: 1.05; }}
    .manifest-title p {{ margin: 0; color: #41506c; font-weight: 750; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 18px 0; }}
    .summary-grid span {{ border: 1px solid #d7e1ef; border-radius: 10px; background: #f8fbff; padding: 10px 12px; }}
    .summary-grid small {{ display: block; color: #526078; font-size: 10px; font-weight: 950; text-transform: uppercase; }}
    .summary-grid strong {{ display: block; margin-top: 3px; font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }}
    th, td {{ border: 1px solid #1f2937; padding: 7px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f9; color: #071633; font-size: 11px; text-transform: uppercase; }}
    th:nth-child(1), td:nth-child(1) {{ width: 28%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 12%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 9%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 7%; text-align: center; }}
    th:nth-child(5), td:nth-child(5) {{ width: 26%; }}
    th:nth-child(6), td:nth-child(6) {{ width: 18%; }}
    footer {{ margin-top: 18px; color: #526078; font-size: 11px; font-weight: 750; }}
    @media print {{ body {{ margin: .25in; }} .print-button {{ display: none; }} .manifest-sheet {{ border: 0; box-shadow: none; padding: 0; }} }}
  </style>
</head>
<body>
  <button class="print-button" onclick="window.print()">Print / Save as PDF</button>
  <section class="manifest-sheet">
    <header>
      <div>
        <img class="manifest-logo" src="/assets/barefoot-logo.jpg" alt="Barefoot & Company" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <span class="fallback-logo">Barefoot &amp; Company</span>
      </div>
      <div class="manifest-title">
        <small>Customer order manifest</small>
        <h1>{esc(customer)}</h1>
        <p>Professional order manifest generated from the Delivery List Scanner.</p>
      </div>
    </header>

    <section class="summary-grid">
      <span><small>Delivery date</small><strong>{esc(print_display_date(delivery_date))}</strong></span>
      <span><small>Total pieces</small><strong>{esc(piece_qty)}</strong></span>
      <span><small>Line items</small><strong>{esc(item_count)}</strong></span>
      <span><small>Status</small><strong>{esc(email.get('status') or 'Draft')}</strong></span>
    </section>

    <table>
      <thead><tr><th>Job Nr.</th><th>Order Nr.</th><th>Item Nr.</th><th>Qty</th><th>Dimensions</th><th>Route</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <footer>This automated manifest includes order information relevant to the customer only. Internal scanner notes, scan history, and plant workflow details are not included.</footer>
  </section>
  {print_lifecycle_script(350)}
</body>
</html>"""

def filter_stale_bay_report_rows(rows: list[dict], params: dict[str, list[str]]) -> list[dict]:
    """Apply the same Old Bays status/search/age/sort controls used by the browser."""
    now = datetime.now().astimezone()
    status = str((params.get("status") or ["all"])[0] or "all").strip().lower()
    if status not in {"all", "live", "snoozed"}:
        status = "all"
    age_text = str((params.get("age") or ["all"])[0] or "all").strip().lower()
    minimum_age = int(age_text) if age_text.isdigit() else 0
    sort_key = str((params.get("sort") or ["age-desc"])[0] or "age-desc").strip().lower()
    if sort_key not in {"age-desc", "age-asc", "bay"}:
        sort_key = "age-desc"
    query = " ".join(str((params.get("q") or [""])[0] or "").split()).casefold()

    def snoozed(row: dict) -> bool:
        text = str(row.get("snoozedUntil") or "").strip()
        if not text:
            return False
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return False
        if value.tzinfo is None:
            value = value.replace(tzinfo=now.tzinfo)
        return value.astimezone(now.tzinfo) > now

    filtered: list[dict] = []
    for row in rows:
        is_snoozed = snoozed(row)
        if status == "live" and is_snoozed:
            continue
        if status == "snoozed" and not is_snoozed:
            continue
        if minimum_age and int(row.get("daysOld") or 0) < minimum_age:
            continue
        if query:
            haystack = " ".join(
                str(row.get(name) or "")
                for name in (
                    "order", "item", "customer", "bayCode", "bayDisplay", "job",
                    "product", "dimensions", "deliveryDate",
                )
            ).casefold()
            if query not in haystack:
                continue
        filtered.append(row)

    def key(row: dict):
        snooze_rank = 1 if snoozed(row) else 0
        if sort_key == "age-asc":
            return (snooze_rank, int(row.get("daysOld") or 0), str(row.get("bayDisplay") or row.get("bayCode") or ""))
        if sort_key == "bay":
            return (snooze_rank, tuple(int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(row.get("bayDisplay") or row.get("bayCode") or ""))), -int(row.get("daysOld") or 0))
        return (snooze_rank, -int(row.get("daysOld") or 0), str(row.get("bayDisplay") or row.get("bayCode") or ""))

    return sorted(filtered, key=key)


def render_stale_bay_report(rows: list[dict]) -> str:
    """Render a print-first mirror of the normalized Old Bays review workspace."""
    now = datetime.now().astimezone()

    def parse_datetime(value: object) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=now.tzinfo)
        return parsed.astimezone(now.tzinfo)

    def friendly_datetime(value: datetime | None) -> str:
        if value is None:
            return "Not scanned"
        return f"{value.month}/{value.day}/{value.year} {value.strftime('%I:%M %p').lstrip('0')}"

    def compact_duration(seconds: float) -> str:
        minutes = max(int(seconds // 60), 0)
        days, remainder = divmod(minutes, 1440)
        hours, minutes = divmod(remainder, 60)
        if days:
            return f"{days}d" + (f" {hours}h" if hours else "")
        if hours:
            return f"{hours}h" + (f" {minutes}m" if minutes else "")
        return f"{max(minutes, 1)}m"

    def snooze_meta(row: dict) -> dict:
        until = parse_datetime(row.get("snoozedUntil"))
        started = parse_datetime(row.get("snoozedAt"))
        active = bool(until and until > now)
        return {
            "active": active,
            "remaining": compact_duration((until - now).total_seconds()) if active and until else "",
            "started": friendly_datetime(started) if started else "Unknown time",
        }

    def age_accent(days_old: int) -> str:
        days = max(int(days_old or 0), 0)
        progress = max(0.0, min((days - 11) / 19, 1.0))
        hue = round(30 * (1 - progress))
        lightness = round(50 - (progress * 18))
        return f"hsl({hue} 86% {lightness}%)"

    # Preserve the exact filter/sort order supplied by filter_stale_bay_report_rows,
    # while grouping contiguous rows into the same hierarchy operators see on screen.
    bay_groups: dict[str, dict] = {}
    for row in rows:
        bay_key = str(row.get("bayCode") or row.get("bayDisplay") or "Unknown bay")
        bay = bay_groups.setdefault(
            bay_key,
            {
                "display": row.get("bayDisplay") or row.get("bayCode") or "Unknown bay",
                "orders": {},
            },
        )
        order_key = str(row.get("order") or row.get("assignmentId") or "Unknown order")
        bay["orders"].setdefault(order_key, []).append(row)

    live_count = 0
    snoozed_count = 0
    oldest_days = 0
    printed_order_count = 0
    bay_sections: list[str] = []

    for bay in bay_groups.values():
        order_cards: list[str] = []
        bay_pieces = 0
        bay_missing = 0
        for order_key, order_rows in bay["orders"].items():
            first = order_rows[0] if order_rows else {}
            snooze = snooze_meta(first)
            days_old = max((int(row.get("daysOld") or 0) for row in order_rows), default=0)
            oldest_days = max(oldest_days, days_old)
            printed_order_count += 1
            if snooze["active"]:
                snoozed_count += 1
            else:
                live_count += 1

            source_items = first.get("orderItems") if isinstance(first.get("orderItems"), list) else None
            items = source_items or [
                {
                    "item": row.get("item"),
                    "job": row.get("job"),
                    "product": row.get("product"),
                    "dimensions": row.get("dimensions"),
                    "qty": row.get("qty"),
                    "inBayQty": row.get("qty"),
                    "missingQty": 0,
                    "lastScannedAt": row.get("lastScannedAt"),
                }
                for row in order_rows
            ]
            order_pieces = sum(max(int(item.get("inBayQty") or 0), 0) for item in items)
            missing_pieces = sum(max(int(item.get("missingQty") or 0), 0) for item in items)
            bay_pieces += order_pieces
            bay_missing += missing_pieces
            job_number = first.get("job") or next((item.get("job") for item in items if item.get("job")), "-")
            scan_times = [
                parsed
                for parsed in (parse_datetime(item.get("lastScannedAt")) for item in items if item.get("lastScannedAt"))
                if parsed is not None
            ]
            fallback_scan = parse_datetime(first.get("lastScannedAt"))
            if fallback_scan is not None:
                scan_times.append(fallback_scan)
            last_scanned = max(scan_times) if scan_times else None

            item_rows = []
            for item in items:
                expected = max(int(item.get("qty") or 0), 0)
                in_bay = max(int(item.get("inBayQty") or 0), 0)
                missing = max(int(item.get("missingQty") or 0), 0)
                item_rows.append(
                    f"""
                    <div class="glass-line {'is-missing' if missing else 'is-accounted'}">
                      <span><small>Item</small><strong>{esc(item.get('item') or '-')}</strong></span>
                      <span class="glass-description"><small>Glass / size</small><strong>{esc(item.get('product') or 'Glass')}</strong><b>{esc(item.get('dimensions') or 'Size not listed')}</b></span>
                      <span><small>In bay</small><strong>{esc(in_bay)} / {esc(expected)}</strong></span>
                      <span class="missing-qty"><small>Missing</small><strong>{esc(missing)}</strong></span>
                      <span class="line-status">{esc('MISSING' if missing else 'ACCOUNTED')}</span>
                    </div>
                    """
                )

            state_strip = (
                f"""
                <div class="order-state is-snoozed">
                  <span class="age-chip"><b>{esc(days_old)}</b> days old</span>
                  <span class="snooze-chip">SNOOZED</span>
                  <span class="snooze-left"><b>{esc(snooze['remaining'])}</b> left</span>
                  <span class="snoozed-at"><small>Snoozed</small><strong>{esc(snooze['started'])}</strong></span>
                </div>
                """
                if snooze["active"]
                else f"""
                <div class="order-state">
                  <span class="age-chip"><b>{esc(days_old)}</b> days old</span>
                  <span class="review-chip">NEEDS REVIEW</span>
                </div>
                """
            )
            order_class = "order-card is-snoozed" if snooze["active"] else "order-card"
            order_cards.append(
                f"""
                <article class="{order_class}" style="--age-accent:{age_accent(days_old)}">
                  {state_strip}
                  <header class="order-header">
                    <div class="order-id"><span><small>Job Nr.</small><strong>{esc(job_number)}</strong></span><span><small>Order</small><strong>{esc(order_key)}</strong></span><b>{esc(first.get('customer') or 'No customer')}</b></div>
                    <span class="bay-pill">{esc(bay['display'])}</span>
                  </header>
                  <section class="glass-ledger">
                    <div class="glass-heading"><span>Item</span><span>Glass / size</span><span>In bay</span><span>Missing</span><span>Status</span></div>
                    {''.join(item_rows)}
                  </section>
                  <div class="order-summary">
                    <span><small>Last physical scan</small><strong>{esc(friendly_datetime(last_scanned))}</strong></span>
                    <span><small>Pieces in bay</small><strong>{esc(order_pieces)}</strong></span>
                    <span class="{'has-missing' if missing_pieces else ''}"><small>Missing pieces</small><strong>{esc(missing_pieces)}</strong></span>
                  </div>
                  <footer class="investigation-row"><span class="verify-box"></span><strong>Physically verified</strong><span class="notes-rule"><small>Investigation notes</small></span></footer>
                </article>
                """
            )

        bay_sections.append(
            f"""
            <section class="bay-section">
              <header class="bay-header"><div><small>Physical bay</small><strong>{esc(bay['display'])}</strong></div><div class="bay-metrics"><span><b>{esc(len(bay['orders']))}</b> old order{'s' if len(bay['orders']) != 1 else ''}</span><span><b>{esc(bay_pieces)}</b> pcs</span><span class="{'has-missing' if bay_missing else ''}"><b>{esc(bay_missing)}</b> missing</span></div></header>
              <div class="bay-orders">{''.join(order_cards)}</div>
            </section>
            """
        )

    if not bay_sections:
        bay_sections.append('<div class="empty-state"><strong>No matching Old Bay orders.</strong><span>The current investigation filters returned no work.</span></div>')

    printed_at = friendly_datetime(now)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Old Bay Investigation List</title>
  <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
  <style>
    @page {{ size: letter landscape; margin: .30in; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #edf3f8; color: #17344e; font-family: "Segoe UI", Arial, sans-serif; }}
    .toolbar {{ width: min(1380px, calc(100% - 28px)); margin: 12px auto 0; text-align: right; }}
    .toolbar button {{ min-height: 38px; border: 1px solid #123f73; border-radius: 9px; background: #123f73; color: #fff; padding: 0 16px; font-weight: 850; cursor: pointer; }}
    .sheet {{ width: min(1380px, calc(100% - 28px)); margin: 10px auto 18px; padding: 16px; border: 1px solid #bacbd9; border-radius: 15px; background: #fff; box-shadow: 0 16px 42px rgba(12,43,76,.11); }}
    .report-header {{ display: grid; grid-template-columns: 190px minmax(0,1fr) 285px; gap: 17px; align-items: center; padding-bottom: 12px; border-bottom: 4px solid #0b3c70; }}
    .logo-box img {{ width: 178px; max-height: 84px; object-fit: contain; object-position: left center; }}
    .logo-fallback {{ display: none; color: #0b315a; font-weight: 950; }}
    .title-block small {{ color: #af6507; font-size: 9px; font-weight: 950; letter-spacing: .12em; text-transform: uppercase; }}
    .title-block h1 {{ margin: 4px 0; color: #082d58; font-size: 27px; line-height: 1.05; }}
    .title-block p {{ margin: 0; color: #61758a; font-size: 11px; font-weight: 700; line-height: 1.4; }}
    .inspection-box {{ display: grid; gap: 7px; padding: 10px 11px; border: 1px solid #ccd7e2; border-radius: 11px; background: #f7fafc; }}
    .inspection-box strong {{ color: #214965; font-size: 10px; }}
    .inspection-line {{ display: grid; grid-template-columns: auto minmax(80px,1fr); gap: 7px; align-items: end; color: #64788b; font-size: 9px; font-weight: 850; }}
    .inspection-line i {{ min-height: 15px; border-bottom: 1px solid #718496; }}
    .report-meta {{ margin-top: 6px; color: #748699; font-size: 8.5px; text-align: right; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 7px; margin: 10px 0 12px; }}
    .summary-card {{ min-height: 53px; display: grid; grid-template-columns: auto minmax(0,1fr); gap: 2px 8px; align-items: center; padding: 8px 10px; border: 1px solid #d3dee7; border-radius: 9px; background: #f8fbfd; }}
    .summary-card b {{ grid-row: 1 / span 2; color: #0c467f; font-size: 21px; }}
    .summary-card strong {{ color: #355771; font-size: 9px; text-transform: uppercase; }}
    .summary-card span {{ color: #758596; font-size: 8px; }}
    .summary-card.is-snoozed b {{ color: #7157a6; }}
    .bay-section {{ margin-top: 10px; break-inside: auto; }}
    .bay-header {{ min-height: 44px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 7px 10px; border: 1px solid #c4d4e1; border-bottom: 0; border-radius: 10px 10px 0 0; background: #eaf2f8; }}
    .bay-header > div:first-child {{ display: grid; gap: 0; }}
    .bay-header small {{ color: #708496; font-size: 7.5px; font-weight: 950; letter-spacing: .08em; text-transform: uppercase; }}
    .bay-header strong {{ color: #123e63; font-size: 15px; }}
    .bay-metrics {{ display: flex; gap: 5px; }}
    .bay-metrics span {{ min-height: 25px; display: inline-flex; align-items: center; gap: 3px; border: 1px solid #cbd9e4; border-radius: 999px; background: #fff; color: #61788b; padding: 0 8px; font-size: 8px; font-weight: 850; }}
    .bay-metrics b {{ color: #294f6d; font-size: 10px; }}
    .bay-metrics .has-missing {{ border-color: #dfb572; background: #fff7e7; color: #865807; }}
    .bay-orders {{ display: grid; gap: 7px; padding: 7px; border: 1px solid #c4d4e1; border-radius: 0 0 10px 10px; background: #f5f8fb; }}
    .order-card {{ --age-accent:#d88920; overflow: hidden; border: 1px solid #d1dce5; border-left: 5px solid var(--age-accent); border-radius: 9px; background: #fff; break-inside: avoid; }}
    .order-card.is-snoozed {{ border-left-color: #7258a8; background: #fbf9ff; }}
    .order-state {{ min-height: 30px; display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-bottom: 1px solid #e1e7ed; background: color-mix(in srgb, var(--age-accent) 9%, #fff); }}
    .order-state.is-snoozed {{ background: #f0eafb; }}
    .age-chip,.review-chip,.snooze-chip,.snooze-left {{ min-height: 21px; display: inline-flex; align-items: center; gap: 3px; border-radius: 999px; padding: 0 7px; font-size: 8px; font-weight: 950; }}
    .age-chip {{ border: 1px solid color-mix(in srgb,var(--age-accent) 55%,#d8e0e7); color: var(--age-accent); background: #fff; }}
    .review-chip {{ color: #8e5007; background: #fff2d9; }}
    .snooze-chip,.snooze-left {{ color: #624694; background: #fff; border: 1px solid #cfbee7; }}
    .snoozed-at {{ margin-left: auto; display: grid; justify-items: end; gap: 0; }}
    .snoozed-at small {{ color: #826eaa; font-size: 7px; font-weight: 900; text-transform: uppercase; }}
    .snoozed-at strong {{ color: #5e478b; font-size: 8.5px; }}
    .order-header {{ min-height: 43px; display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 6px 9px; border-bottom: 1px solid #e1e7ed; }}
    .order-id {{ min-width: 0; display: flex; align-items: center; gap: 10px; }}
    .order-id > span {{ display: grid; gap: 0; }}
    .order-id small {{ color: #738697; font-size: 7px; font-weight: 950; text-transform: uppercase; }}
    .order-id strong {{ color: #173e5e; font-size: 12px; }}
    .order-id > b {{ min-width: 0; overflow: hidden; color: #617789; font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }}
    .bay-pill {{ flex: 0 0 auto; border: 1px solid #bfd0dd; border-radius: 999px; background: #f3f8fb; color: #355e7a; padding: 4px 8px; font-size: 8px; font-weight: 950; }}
    .glass-ledger {{ padding: 6px 8px; }}
    .glass-heading,.glass-line {{ display: grid; grid-template-columns: 62px minmax(210px,1fr) 78px 68px 78px; gap: 6px; align-items: center; }}
    .glass-heading {{ min-height: 22px; padding: 3px 5px; color: #718393; font-size: 7px; font-weight: 950; letter-spacing: .05em; text-transform: uppercase; }}
    .glass-line {{ min-height: 34px; padding: 4px 5px; border-top: 1px solid #e7edf2; }}
    .glass-line > span {{ min-width: 0; display: grid; gap: 0; }}
    .glass-line small {{ color: #7a8b99; font-size: 6.8px; font-weight: 900; text-transform: uppercase; }}
    .glass-line strong {{ overflow: hidden; color: #294e68; font-size: 9px; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; }}
    .glass-description b {{ overflow: hidden; color: #748695; font-size: 8px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; }}
    .missing-qty strong {{ color: #526a7d; }}
    .glass-line.is-missing .missing-qty strong {{ color: #a44d16; }}
    .line-status {{ width: fit-content; display: inline-flex !important; align-items: center; border: 1px solid #bcd8c4; border-radius: 999px; background: #eef8f1; color: #39714a !important; padding: 3px 6px; font-size: 7px !important; font-weight: 950 !important; }}
    .glass-line.is-missing .line-status {{ border-color: #e0b5a9; background: #fff0ed; color: #a33e28 !important; }}
    .order-summary {{ display: grid; grid-template-columns: minmax(170px,1fr) 92px 92px; gap: 6px; padding: 6px 8px; border-top: 1px solid #e1e7ed; background: #fafcfd; }}
    .order-summary > span {{ display: grid; gap: 1px; }}
    .order-summary small {{ color: #788998; font-size: 7px; font-weight: 900; text-transform: uppercase; }}
    .order-summary strong {{ color: #294e68; font-size: 9px; }}
    .order-summary .has-missing strong {{ color: #a44d16; }}
    .investigation-row {{ min-height: 31px; display: grid; grid-template-columns: 18px auto minmax(150px,1fr); align-items: center; gap: 6px; padding: 5px 8px; border-top: 1px solid #e1e7ed; }}
    .verify-box {{ width: 16px; height: 16px; border: 2px solid #567087; border-radius: 4px; background: #fff; }}
    .investigation-row > strong {{ color: #526b7e; font-size: 8px; }}
    .notes-rule {{ min-height: 18px; border-bottom: 1px solid #8294a4; }}
    .notes-rule small {{ color: #8a99a7; font-size: 7px; }}
    .empty-state {{ min-height: 150px; display: grid; place-items: center; align-content: center; gap: 4px; color: #718597; text-align: center; }}
    .empty-state strong {{ color: #345873; font-size: 14px; }}
    .footer-note {{ display: flex; justify-content: space-between; gap: 14px; margin-top: 8px; color: #7b8c9b; font-size: 8px; font-weight: 750; }}
    @media print {{ body {{ background: #fff; }} .toolbar {{ display:none; }} .sheet {{ width:100%; margin:0; padding:0; border:0; border-radius:0; box-shadow:none; }} }}
  </style>
</head>
<body>
  <div class="toolbar"><button type="button" onclick="window.print()">Print Investigation List</button></div>
  <main class="sheet">
    <header class="report-header">
      <div class="logo-box"><img src="/static/images/barefoot-company-builders-firstsource-print-logo.png?v=20260825-v0.385" alt="Barefoot & Company / Builders FirstSource" onerror="this.style.display='none';this.nextElementSibling.style.display='block';"><span class="logo-fallback">Barefoot &amp; Company</span></div>
      <div class="title-block"><small>Indian Trail inventory control</small><h1>Old Bay Investigation List</h1><p>Print mirror of the Old Bays Control Center. Review each physical bay, verify the complete order, then record investigation notes before moving, clearing, or extending a snooze.</p></div>
      <div><div class="inspection-box"><strong>Walkthrough verification</strong><span class="inspection-line"><span>Checked by</span><i></i></span><span class="inspection-line"><span>Date</span><i></i></span><span class="inspection-line"><span>Area / shift</span><i></i></span></div><div class="report-meta">Generated {esc(printed_at)}</div></div>
    </header>
    <section class="summary-grid">
      <article class="summary-card"><b>{live_count}</b><strong>Live stale</strong><span>Needs review now</span></article>
      <article class="summary-card is-snoozed"><b>{snoozed_count}</b><strong>Snoozed</strong><span>Temporarily paused</span></article>
      <article class="summary-card"><b>{len(bay_groups)}</b><strong>Bays affected</strong><span>Physical locations</span></article>
      <article class="summary-card"><b>{oldest_days}</b><strong>Oldest age</strong><span>{printed_order_count} old orders</span></article>
    </section>
    {''.join(bay_sections)}
    <div class="footer-note"><span>Age colors deepen from orange to dark red; purple identifies an active snooze.</span><span>Delivery List Scanner · Old Bay Control Center</span></div>
  </main>
  {print_lifecycle_script(250)}
</body>
</html>"""


def render_print_package(package: dict) -> str:
    """Purpose: Render print package for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Converts normalized records into the requested presentation or export format and returns the completed output.
    """
    sections = []
    printed_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    filters = package.get("filters", {}) or {}
    try:
        copies = max(1, min(int(filters.get("copies") or 1), 10))
    except (TypeError, ValueError):
        copies = 1
    orientation = str(filters.get("orientation") or "portrait").strip().lower()
    if orientation not in {"portrait", "landscape"}:
        orientation = "portrait"
    rush_only = str(filters.get("rushOnly") or "").lower() in {"1", "true", "yes"}
    remake_only = str(filters.get("remakeOnly") or "").lower() in {"1", "true", "yes"}
    updated_only = str(filters.get("updatedOnly") or "").lower() in {"1", "true", "yes"}
    special_only = rush_only or remake_only

    def stage_print_name(delivery_list: dict) -> str:
        """Short, human print name. Avoid repeating the stage in badges/subtitles."""
        kind = str(delivery_list.get("stageKind") or delivery_list.get("sheetKind") or "").lower()
        stage = str(delivery_list.get("stage") or "Delivery List")
        mapped = {
            "outbound": "Outbound",
            "staging": "Staging",
            "indian-trail": "Indian Trail",
            "cpu": "CPU",
            "dtc": "DTC",
            "greenville": "BFS Greenville",
        }.get(kind)
        if mapped:
            return mapped
        if " - " in stage:
            return stage.split(" - ", 1)[0].strip() or stage
        return stage

    def sheet_title(delivery_list: dict, mode: str = "") -> str:
        """Purpose: Run the sheet title workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        date_text = print_display_date(delivery_list.get("deliveryDate"))
        stage_name = stage_print_name(delivery_list)
        if mode == "remake":
            return f"{stage_name} Remake Sheet for {date_text}"
        if mode == "rush":
            return f"{stage_name} Rush Sheet for {date_text}"
        if updated_only or delivery_list.get("sheetKind") == "updated":
            return f"{stage_name} Updated Delivery List for {date_text}"
        return f"{stage_name} Delivery List for {date_text}"

    def sheet_badge(delivery_list: dict, mode: str = "") -> str:
        """Purpose: Run the sheet badge workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        if mode == "remake":
            return "REMAKE"
        if mode == "rush":
            return "RUSH"
        if updated_only or delivery_list.get("sheetKind") == "updated":
            return "UPDATED"
        return ""

    def sheet_subtitle(delivery_list: dict, mode: str = "") -> str:
        """Purpose: Run the sheet subtitle workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        if mode == "rush":
            priority_date = str(delivery_list.get("deliveryDate") or "")
            original_date = str(delivery_list.get("originalDeliveryDate") or "")
            details = []
            if original_date and original_date != priority_date:
                details.append(f"Original delivery-list date: {print_display_date(original_date)}")
            stage_kind = str(delivery_list.get("stageKind") or delivery_list.get("sheetKind") or "").lower()
            if stage_kind == "indian-trail" and delivery_list.get("priorityDirectToTruck"):
                handling = "Handling: Send straight to installer truck / skip bay"
            elif stage_kind == "indian-trail":
                handling = "Handling: Receive into the indicated priority Rush bay"
            else:
                handling = "Handling: Expedite through this stage"
            details.append(handling)
            return " | ".join(details)
        mirror_count = int(delivery_list.get("excludedMirrorCount") or 0)
        if mirror_count:
            return f"Regular mirror rows excluded: {mirror_count}"
        return ""

    for delivery_list in package.get("lists", []):
        remakes = delivery_list.get("remakes", [])
        rushes = delivery_list.get("rushes", [])
        normal_items = delivery_list.get("normalItems")
        if normal_items is None:
            normal_items = [item for item in delivery_list.get("items", []) if item not in remakes and item not in rushes]
        sheet_kind = esc(str(delivery_list.get("stageKind") or "regular"))
        updated_class = "updated" if updated_only or delivery_list.get("sheetKind") == "updated" else ""
        if normal_items and not special_only:
            title = sheet_title(delivery_list)
            badge = sheet_badge(delivery_list)
            # Print one physical copy by default. The browser print dialog should also stay at Copies = 1.
            # If the shop later wants duplicate physical copies again, add a second render_sheet call here.
            sections.append(render_sheet(title, sheet_subtitle(delivery_list), normal_items, f"regular {sheet_kind} {updated_class}", badge, printed_at))
        if rushes and not remake_only:
            sections.append(
                render_sheet(
                    sheet_title(delivery_list, "rush"),
                    sheet_subtitle(delivery_list, "rush"),
                    rushes,
                    "rush",
                    sheet_badge(delivery_list, "rush"),
                    printed_at,
                )
            )
        if remakes and not rush_only:
            title = sheet_title(delivery_list, "remake")
            # Remake sheets also print one physical copy by default.
            sections.append(render_sheet(title, "", remakes, "remake", sheet_badge(delivery_list, "remake"), printed_at))
    base_sections = list(sections)
    if copies > 1 and base_sections:
        sections = [section for _copy_number in range(copies) for section in base_sections]
    body = "".join(sections) or '<section class="sheet"><h1>No printable rows found</h1></section>'
    page_size = "letter landscape" if orientation == "landscape" else "letter portrait"
    sheet_width = "min(1460px, calc(100% - 32px))" if orientation == "landscape" else "min(1120px, calc(100% - 32px))"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Delivery List Print Package</title>
  <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
  <style>
    body {{ margin: 0; color: #07122f; font-family: "Segoe UI", Arial, sans-serif; background: #f6f8fb; }}
    .sheet {{ width: {sheet_width}; margin: 16px auto; padding: 18px 20px 14px; background: #fff; border: 1px solid #444; border-radius: 0; break-inside: avoid; page-break-inside: avoid; }}
    .sheet-header {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; border-bottom: 3px solid #072a63; padding-bottom: 10px; margin-bottom: 10px; }}
    .sheet-header-compact {{ align-items: center; padding-bottom: 8px; margin-bottom: 9px; border-bottom-width: 2px; }}
    h1 {{ margin: 4px 0 0; color: #041a3d; font-size: 26px; line-height: 1.12; text-transform: uppercase; }}
    h2 {{ margin: 3px 0 0; color: #041a3d; font-size: 18px; line-height: 1.15; text-transform: uppercase; }}
    p {{ margin: 3px 0 0; font-weight: 750; color: #41506c; }}
    .printed-at {{ color: #263550; font-size: 12px; font-weight: 850; }}
    .sheet-page-top {{ color: #526078; font-size: 12px; font-weight: 900; text-align: right; margin-bottom: 5px; }}
    .sheet-badge {{ display: inline-flex; min-height: 24px; align-items: center; border: 1px solid #072a63; border-radius: 999px; background: #eaf2ff; color: #041a3d; padding: 0 11px; font-size: 11px; font-weight: 900; letter-spacing: .08em; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12.25px; line-height: 1.22; }}
    .delivery-print-table {{ table-layout: fixed; }}
    .delivery-print-table .job-col {{ width: 26%; }}
    .delivery-print-table .order-col {{ width: 9%; }}
    .delivery-print-table .item-col {{ width: 8%; }}
    .delivery-print-table .qty-col {{ width: 5%; }}
    .delivery-print-table .dimensions-col {{ width: 17%; }}
    .delivery-print-table .customer-col {{ width: 24%; }}
    .delivery-print-table .route-col {{ width: 6%; }}
    .delivery-print-table .check-col {{ width: 5%; }}
    th, td {{ border: 1px solid #d9e1ee; padding: 6px 7px; text-align: left; vertical-align: top; }}
    .print-nowrap,
    .print-truncate {{ white-space: nowrap; }}
    .print-truncate {{ overflow: hidden; text-overflow: ellipsis; }}
    th {{ background: #f1f1f1; color: #041a3d; font-size: 11.5px; }}
    tr, td, th {{ break-inside: avoid; page-break-inside: avoid; }}
    .glass-group td {{ background: #e9e9e9; font-size: 12px; font-weight: 900; text-transform: uppercase; padding-top: 6px; padding-bottom: 6px; }}
    .check-cell {{ width: 30px; text-align: center; font-size: 16px; }}
    .copy-box {{ border: 1px solid #333; padding: 8px 10px; font-size: 16px; font-weight: 850; white-space: nowrap; display: flex; align-items: center; gap: 16px; }}
    .copy-box .write-line {{ display: inline-block; height: 1em; border-bottom: 1px solid #333; vertical-align: -2px; }}
    .copy-box .checked-line {{ width: 82px; }}
    .copy-box .date-line {{ width: 112px; }}
    .notes {{ margin-top: 10px; min-height: 72px; border: 1px solid #333; display: grid; grid-template-columns: auto 1fr; gap: 8px; padding: 9px; font-size: 14px; }}
    .updated .sheet-badge {{ border-color: #135cff; background: #eaf2ff; color: #072a63; }}
    .indian-trail .sheet-header {{ border-bottom-color: #2fa84f; }}
    .cpu .sheet-header {{ border-bottom-color: #8a63d2; }}
    .dtc .sheet-header {{ border-bottom-color: #d9468f; }}
    .rush {{ border: 4px double #000; }}
    .rush .sheet-header {{ border-bottom: 6px double #000; }}
    .rush h1::before, .rush h1::after {{ content: " !!! "; }}
    .remake {{ border: 3px dashed #000; }}
    .remake .sheet-badge {{ border-color: #c92f42; background: #fff0f1; color: #9f1f31; }}
    .remake .sheet-header {{ border-bottom: 3px dashed #000; }}
    @page {{ size: {page_size}; margin: 0.25in; }}
    @media print {{
      body {{ background: #fff; }}
      .sheet {{
        width: auto;
        margin: 0;
        padding: 0.04in 0.06in 0.03in;
        border: 0;
        border-radius: 0;
        page-break-after: always;
        break-after: page;
      }}
      /* Keep notes directly under the table. Using flex + margin-top:auto caused
         large gaps and, in Edge/Chrome print preview, an extra mostly blank page. */
      .sheet .notes {{ margin-top: 10px; }}
      .sheet:last-child {{ page-break-after: auto; break-after: auto; }}
    }}
  </style>
</head>
<body>
  {body}
  {print_lifecycle_script(250)}
</body>
</html>"""


def summarize_print_package(package: dict, requested_stage_count: int = 0) -> dict:
    """Build the live Print / Export preview from the exact package output.

    The preview deliberately consumes ``STORE.get_print_package`` instead of
    reimplementing its filters in JavaScript. This keeps the displayed piece
    count aligned with the rows that the print and XLSX endpoints will emit.
    """
    lists = list(package.get("lists") or [])
    glass_totals: dict[str, int] = {}
    customer_totals: dict[str, int] = {}
    order_totals: dict[str, int] = {}
    unique_customers: set[str] = set()
    unique_orders: set[str] = set()
    unique_glass_types: set[str] = set()
    stage_breakdown: list[dict] = []
    preview_rows: list[dict] = []
    total_pieces = 0
    total_rows = 0
    normal_pieces = 0
    remake_pieces = 0
    rush_pieces = 0

    def piece_qty(item: dict) -> int:
        try:
            return max(int(item.get("qty") or 0), 0)
        except (TypeError, ValueError):
            return 0

    def item_glass_type(item: dict) -> str:
        raw = item.get("glassType") or item.get("product") or item.get("job") or item.get("suggestedBay") or "Other Glass"
        return canonical_clear_glass_label(raw) or "Other Glass"

    for delivery_list in lists:
        items = list(delivery_list.get("items") or [])
        normal_items = list(delivery_list.get("normalItems") or [])
        remake_items = list(delivery_list.get("remakes") or [])
        rush_items = list(delivery_list.get("rushes") or [])
        stage_pieces = sum(piece_qty(item) for item in items)
        stage_rows = len(items)
        total_pieces += stage_pieces
        total_rows += stage_rows
        normal_pieces += sum(piece_qty(item) for item in normal_items)
        remake_pieces += sum(piece_qty(item) for item in remake_items)
        rush_pieces += sum(piece_qty(item) for item in rush_items)

        stage_customers: set[str] = set()
        stage_orders: set[str] = set()
        stage_glass: set[str] = set()
        for item in items:
            qty = piece_qty(item)
            glass_type = item_glass_type(item)
            customer = str(item.get("customer") or "Unassigned customer").strip() or "Unassigned customer"
            order = str(item.get("order") or "").strip()
            item_no = str(item.get("item") or "").strip()
            scanned = max(int(item.get("scanned") or 0), 0)
            if qty > 0 and scanned >= qty:
                status_key, status_label = "complete", "Complete"
            elif scanned > 0:
                status_key, status_label = "partial", "Partial"
            else:
                status_key, status_label = "not-scanned", "Not Scanned"

            attention: list[dict[str, str]] = []
            signal = f"{item.get('processState', '')} {item.get('queueState', '')}"
            if re.search(r"\b(?:remake|rm)\b", signal, flags=re.IGNORECASE):
                attention.append({"key": "remake", "label": "Remakes"})
            if re.search(r"\b(?:rush|sdi)\b", signal, flags=re.IGNORECASE):
                attention.append({"key": "rush", "label": "Rushes"})
            if int(item.get("internalRejectCount") or 0) > 0:
                attention.append({"key": "reject", "label": "Internal Rejects"})
            if re.search(r"\b(?:update|updated|new|change|changed|added|add)\b", signal, flags=re.IGNORECASE):
                attention.append({"key": "updated", "label": "New/Updated"})
            if str(item.get("errorType") or "").strip() or str(item.get("errorReason") or "").strip():
                attention.append({"key": "error", "label": "Errors"})

            preview_rows.append(
                {
                    "listId": delivery_list.get("id", ""),
                    "stage": delivery_list.get("stage") or delivery_list.get("label") or "Delivery List",
                    "scanner": delivery_list.get("scanner") or "",
                    "deliveryDate": delivery_list.get("deliveryDate") or "",
                    "order": order,
                    "item": item_no,
                    "job": str(item.get("job") or item.get("product") or ""),
                    "customer": customer,
                    "pieces": qty,
                    "glassType": glass_type,
                    "dimensions": str(item.get("dimensions") or ""),
                    "statusKey": status_key,
                    "statusLabel": status_label,
                    "attention": attention,
                    "route": public_route_label(item.get("route")) or "Indian Trail",
                }
            )

            unique_glass_types.add(glass_type)
            stage_glass.add(glass_type)
            glass_totals[glass_type] = glass_totals.get(glass_type, 0) + qty

            unique_customers.add(customer)
            stage_customers.add(customer)
            customer_totals[customer] = customer_totals.get(customer, 0) + qty

            if order:
                unique_orders.add(order)
                stage_orders.add(order)
                order_totals[order] = order_totals.get(order, 0) + qty

        stage_breakdown.append(
            {
                "listId": delivery_list.get("id", ""),
                "stage": delivery_list.get("stage") or delivery_list.get("label") or "Delivery List",
                "scanner": delivery_list.get("scanner") or "",
                "deliveryDate": delivery_list.get("deliveryDate") or "",
                "pieceCount": stage_pieces,
                "rowCount": stage_rows,
                "normalPieces": sum(piece_qty(item) for item in normal_items),
                "remakePieces": sum(piece_qty(item) for item in remake_items),
                "rushPieces": sum(piece_qty(item) for item in rush_items),
                "customerCount": len(stage_customers),
                "orderCount": len(stage_orders),
                "glassTypeCount": len(stage_glass),
            }
        )

    def sorted_breakdown(values: dict[str, int]) -> list[dict]:
        return [
            {"label": label, "pieceCount": qty}
            for label, qty in sorted(values.items(), key=lambda entry: (-entry[1], entry[0].lower()))
        ]

    preview_rows.sort(
        key=lambda row: (
            str(row.get("deliveryDate") or ""),
            str(row.get("stage") or ""),
            str(row.get("glassType") or ""),
            int(row.get("order") or 0) if str(row.get("order") or "").isdigit() else 0,
            int(row.get("item") or 0) if str(row.get("item") or "").isdigit() else 0,
        )
    )
    preview_page_size = 18

    return {
        "ok": True,
        "generatedAt": package.get("generatedAt"),
        "requestedStageCount": max(int(requested_stage_count or 0), 0),
        "matchedStageCount": len(lists),
        "totalPieces": total_pieces,
        "rowCount": total_rows,
        "normalPieces": normal_pieces,
        "remakePieces": remake_pieces,
        "rushPieces": rush_pieces,
        "customerCount": len(unique_customers),
        "orderCount": len(unique_orders),
        "glassTypeCount": len(unique_glass_types),
        "noResults": total_rows == 0 or total_pieces == 0,
        "previewPageSize": preview_page_size,
        "pageCount": max((len(preview_rows) + preview_page_size - 1) // preview_page_size, 1),
        "previewRows": preview_rows,
        "stageBreakdown": stage_breakdown,
        "glassTypeBreakdown": sorted_breakdown(glass_totals),
        "customerBreakdown": sorted_breakdown(customer_totals),
        "orderBreakdown": sorted_breakdown(order_totals),
        "filters": package.get("filters") or {},
    }


class Handler(SimpleHTTPRequestHandler):
    _compressed_asset_cache: dict[tuple[str, int, int], bytes] = {}
    _compressed_asset_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        """Purpose: Initialize a handler instance and its required state.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        """Purpose: Run the end headers workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        request_path = urlparse(self.path).path
        if request_path.startswith(("/static/", "/assets/", "/sounds/")):
            # Asset URLs carry a release cache key in index.html. Retaining them
            # avoids re-downloading several megabytes on every page visit while
            # the next release still invalidates the browser cache immediately.
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        """Serve versioned text assets compressed, then reuse the process cache."""
        request_path = urlparse(self.path).path
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "").lower()
        compressible_asset = (
            request_path.startswith(("/static/", "/assets/"))
            and Path(request_path).suffix.lower() in {".css", ".js", ".json", ".svg"}
        )
        if self.command in {"GET", "HEAD"} and accepts_gzip and compressible_asset:
            source = Path(self.translate_path(request_path))
            if source.is_file():
                stat = source.stat()
                cache_key = (str(source), stat.st_mtime_ns, stat.st_size)
                with self._compressed_asset_lock:
                    body = self._compressed_asset_cache.get(cache_key)
                    if body is None:
                        body = gzip.compress(source.read_bytes(), compresslevel=6, mtime=0)
                        stale_keys = [key for key in self._compressed_asset_cache if key[0] == str(source)]
                        for stale_key in stale_keys:
                            self._compressed_asset_cache.pop(stale_key, None)
                        self._compressed_asset_cache[cache_key] = body
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", self.guess_type(str(source)))
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Vary", "Accept-Encoding")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
                self.end_headers()
                return io.BytesIO(body)
        return super().send_head()

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Purpose: Send JSON for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        use_gzip = len(body) >= 1024 and "gzip" in self.headers.get("Accept-Encoding", "").lower()
        if use_gzip:
            body = gzip.compress(body, compresslevel=4, mtime=0)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, markup: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Purpose: Send HTML for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        body = markup.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        """Purpose: Read JSON for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def session_token(self) -> str:
        """Purpose: Run the session token workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie(cookie_header)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel else ""

    def current_user(self) -> dict | None:
        """Purpose: Run the current user workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return STORE.get_user_by_session(self.session_token())

    def require_permission(self, permission: str) -> dict | None:
        """Purpose: Run the require permission workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        requested = canonical_permission_name(permission)
        granted = {canonical_permission_name(value) for value in user.get("permissions", [])}
        if requested not in granted:
            self.send_json({"error": "Permission denied", "permission": requested}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def require_any_permission(self, *permissions: str) -> dict | None:
        """Purpose: Run the require any permission workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        granted = {canonical_permission_name(value) for value in user.get("permissions", [])}
        requested = [canonical_permission_name(permission) for permission in permissions]
        if not any(permission in granted for permission in requested):
            self.send_json({"error": "Permission denied", "permissions": requested}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def require_all_permissions(self, *permissions: str) -> dict | None:
        """Require every named permission for an operation that crosses security domains.

        v0.340 uses this for new-user creation because that workflow creates a
        profile *and* assigns its initial role/station. Keeping the check here
        prevents a profile-management role from silently becoming an access-
        assignment role through a combined endpoint.
        """
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        granted = {canonical_permission_name(value) for value in user.get("permissions", [])}
        requested = [canonical_permission_name(permission) for permission in permissions]
        missing = [permission for permission in requested if permission not in granted]
        if missing:
            self.send_json({"error": "Permission denied", "permissions": requested, "missingPermissions": missing}, HTTPStatus.FORBIDDEN)
            return None
        return user


    def require_admin_role(self) -> dict | None:
        """Require the built-in Admin role for destructive reject management."""
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        roles = {str(role).strip().lower() for role in (user.get("roles") or [])}
        if "admin" not in roles:
            self.send_json({"error": "Admin role required", "role": "Admin"}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def user_can_preview_delivery_update(self, user: dict, list_id: str) -> bool:
        """Allow privileged Admin review across every delivery-list stage.

        Delivery List Management is an administrative reconciliation workspace.
        Admins, supervisors, and users explicitly granted the complete update-review
        permission set must be able to inspect changes for Airport, Indian Trail,
        Greenville, CPU, and DTC even when their ordinary scanner stage assignment
        is narrower. Other users continue to respect their assigned stage access.
        """
        roles = {str(role).strip().lower() for role in (user.get("roles") or [])}
        if roles.intersection({"admin", "supervisor"}):
            return True

        granted = {
            canonical_permission_name(str(permission))
            for permission in (user.get("permissions") or [])
        }
        administrative_review_permissions = {
            canonical_permission_name("view_admin"),
            canonical_permission_name("edit_delivery_list_items"),
            canonical_permission_name("preview_delivery_updates"),
        }
        if administrative_review_permissions.issubset(granted):
            return True

        return STORE.user_can_access_list(user, list_id)

    def require_confirmation_text(self, data: dict, required_text: str) -> bool:
        """Purpose: Run the require confirmation text workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        typed = str(data.get("confirmText") or "").strip()
        if typed == required_text:
            return True
        self.send_json(
            {"error": f"Type {required_text} to confirm this action."},
            HTTPStatus.BAD_REQUEST,
        )
        return False

    def require_rack_recovery_power(self) -> dict | None:
        """Allow only Admin/Supervisor-level users to manually recover rack locations."""
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        roles = set(user.get("roles") or [])
        permissions = set(user.get("permissions") or [])
        if "manage_racks" not in permissions and not roles.intersection({"Admin", "Supervisor"}):
            self.send_json({"error": "Permission denied", "permission": "rack_recovery"}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def set_session_cookie(self, token: str, expires_at: str) -> None:
        """Purpose: Update session cookie for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        secure = "; Secure" if CONFIG.production else ""
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200{secure}",
        )

    def clear_session_cookie(self) -> None:
        """Purpose: Remove session cookie for the delivery-list scanner workflow.

        Effects: This function reads or updates shared application state.
        Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
        """
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )

    def do_GET(self) -> None:
        """Purpose: Handle get for the delivery-list scanner workflow.

        Effects: This function writes an HTTP response.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self.send_json(STORE.health())
            return

        if parsed.path == "/api/presentation-profile":
            # v0.355 presentation metadata is intentionally non-sensitive so the
            # sign-in screen and shell can use the configured organization name
            # before a user session exists. Workflow identifiers are never exposed
            # or changed through this endpoint.
            self.send_json(STORE.get_presentation_context())
            return

        if parsed.path == "/api/session":
            user = self.current_user()
            self.send_json({"authenticated": bool(user), "user": user})
            return

        if parsed.path == "/api/notifications/pending":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            self.send_json({"notifications": STORE.get_pending_notifications(user["username"])})
            return
        if parsed.path == "/api/notifications/history":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            limit = parse_qs(parsed.query).get("limit", ["50"])[0]
            self.send_json({"notifications": STORE.get_notification_history(user["username"], int(limit or 50))})
            return
        if parsed.path == "/api/delivery-list-updates":
            user = self.require_permission("view_delivery_lists")
            if not user:
                return
            list_id = str(parse_qs(parsed.query).get("listId", [""])[0] or "").strip()
            if not list_id:
                self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                return
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            self.send_json(STORE.get_user_line_update_summary(user["username"], list_id))
            return
        # DLS_V135_OPERATIONS_ROUTES: per-user line flags, rejects, and packing history.
        if parsed.path == "/api/operations/line-flags":
            user = self.require_permission("view_delivery_lists")
            if not user:
                return
            list_id = str(parse_qs(parsed.query).get("listId", [""])[0] or "").strip()
            if not list_id:
                self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                return
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            self.send_json(OPERATIONS.line_flags(list_id, user["username"]))
            return

        if parsed.path == "/api/rejects":
            if not self.require_any_permission("view_rejects", "log_rejects", "manage_reject_settings", "manage_reject_records"):
                return
            params = parse_qs(parsed.query)
            self.send_json(
                OPERATIONS.list_rejects(
                    date_from=params.get("dateFrom", [""])[0],
                    date_to=params.get("dateTo", [""])[0],
                    query=params.get("q", [""])[0],
                    limit=int(params.get("limit", ["500"])[0] or 500),
                )
            )
            return

        if parsed.path == "/api/rejects/catalog":
            if not self.require_any_permission("view_rejects", "log_rejects", "manage_reject_settings", "manage_reject_records"):
                return
            self.send_json(OPERATIONS.reject_catalog())
            return

        if parsed.path == "/api/rejects/matches":
            if not self.require_any_permission("view_rejects", "log_rejects", "manage_reject_settings", "manage_reject_records"):
                return
            params = parse_qs(parsed.query)
            self.send_json(
                enrich_reject_match_details(
                    OPERATIONS.reject_matches(
                        params.get("order", [""])[0],
                        params.get("item", [""])[0],
                    )
                )
            )
            return

        packing_history_print_match = re.match(r"^/api/racks/packing-history/(\d+)/print$", parsed.path)
        if packing_history_print_match:
            if not self.require_any_permission("view_racks", "print_export"):
                return
            self.send_html(OPERATIONS.packing_history_print_html(int(packing_history_print_match.group(1))))
            return

        if parsed.path == "/api/racks/packing-history":
            if not self.require_any_permission("view_racks", "print_export"):
                return
            limit = int(parse_qs(parsed.query).get("limit", ["250"])[0] or 250)
            self.send_json(OPERATIONS.packing_history(limit))
            return

        if parsed.path == "/api/admin/delivery-automation":
            user = self.require_any_permission("manage_automation", "import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_dashboard())
            return

        if parsed.path == "/api/admin/delivery-automation/recent-imports":
            user = self.require_any_permission("manage_automation", "import_delivery_lists")
            if not user:
                return
            params = parse_qs(parsed.query)
            self.send_json(
                DELIVERY_AUTOMATION.get_import_history(
                    page=int(params.get("page", ["1"])[0] or 1),
                    page_size=int(params.get("pageSize", params.get("limit", ["20"]))[0] or 20),
                    query=params.get("q", [""])[0],
                    classification=params.get("classification", [""])[0],
                    date_from=params.get("dateFrom", [""])[0],
                    date_to=params.get("dateTo", [""])[0],
                    page_mode=params.get("pageMode", ["rows"])[0],
                )
            )
            return
        if parsed.path == "/api/admin/delivery-automation/latest-import":
            user = self.require_any_permission("manage_automation", "import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_latest_import_result())
            return

        if parsed.path == "/api/admin/delivery-list-catalog":
            user = self.require_any_permission(
                "edit_delivery_list_items",
                "create_delivery_list_orders",
                "delete_delivery_list_items",
                "delete_delivery_lists",
                "reset_delivery_lists",
            )
            if not user:
                return
            params = parse_qs(parsed.query)
            try:
                page = max(int(params.get("page", ["1"])[0] or 1), 1)
            except (TypeError, ValueError):
                page = 1
            self.send_json(
                STORE.get_admin_delivery_list_catalog(
                    page=page,
                    query=params.get("q", [""])[0],
                    user=user,
                )
            )
            return

        if parsed.path == "/api/delivery-lists":
            user = self.require_permission("view_delivery_lists")
            if not user:
                return
            self.send_json({"lists": STORE.get_delivery_lists(user)})
            return

        if parsed.path == "/api/stations":
            if not self.require_permission("use_assigned_stations"):
                return
            self.send_json({"stations": STORE.get_stations()})
            return

        if parsed.path == "/api/exceptions":
            if not self.require_permission("manage_scan_exceptions"):
                return
            filters = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.send_json({"exceptions": STORE.get_exceptions(filters)})
            return

        if parsed.path == "/api/admin/summary":
            if not self.require_any_permission(*ADMIN_DASHBOARD_PERMISSIONS):
                return
            summary = dict(STORE.admin_summary() or {})
            latest_import = DELIVERY_AUTOMATION.get_latest_import_result()
            latest_results = list(latest_import.get("latestImportResults") or [])
            summary["recentImports"] = latest_results
            summary["latestImportResults"] = latest_results
            summary["lastCheckedAt"] = str(latest_import.get("lastCheckedAt") or "")
            summary["lastImportCheckedAt"] = str(latest_import.get("lastCheckedAt") or "")
            summary["latestImportRun"] = dict(latest_import.get("latestRun") or {})
            self.send_json(summary)
            return

        if parsed.path == "/api/admin/superseded-order-reviews/summary":
            user = self.require_any_permission("view_admin", "review_superseded_orders")
            if not user:
                return
            self.send_json(STORE.superseded_order_review_summary())
            return

        if parsed.path == "/api/admin/superseded-order-reviews":
            user = self.require_any_permission("view_admin", "review_superseded_orders")
            if not user:
                return
            params = parse_qs(parsed.query)
            self.send_json(
                STORE.list_superseded_order_reviews(
                    status=params.get("status", [""])[0],
                    include_inactive=params.get("includeInactive", ["0"])[0] in {"1", "true", "yes"},
                )
            )
            return

        if parsed.path == "/api/admin/users":
            if not self.require_any_permission("manage_users", "manage_user_access", "manage_user_assignments"):
                return
            self.send_json({"users": STORE.list_users()})
            return

        if parsed.path == "/api/admin/customer-route-rules":
            if not self.require_permission("manage_route_rules"):
                return
            self.send_json({"rules": STORE.get_customer_route_rules()})
            return

        email_manifest_match = re.match(r"^/api/admin/customer-emails/(\d+)/manifest-pdf$", parsed.path)
        if email_manifest_match:
            if not self.require_permission("manage_customer_emails"):
                return
            html_body = render_customer_email_manifest_pdf_page(STORE.get_email_outbox_item(int(email_manifest_match.group(1))))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_body.encode("utf-8"))
            return

        if parsed.path == "/api/admin/customer-emails":
            if not self.require_permission("manage_customer_emails"):
                return
            self.send_json(STORE.get_customer_email_settings())
            return

        if parsed.path == "/api/admin/bay-scanner-rules":
            if not self.require_permission("manage_bay_scanner_rules"):
                return
            self.send_json(STORE.get_bay_scan_settings())
            return

        if parsed.path == "/api/admin/cross-date-scan-settings":
            if not self.require_permission("manage_cross_date_scanning"):
                return
            self.send_json(STORE.get_cross_date_scan_settings())
            return

        if parsed.path == "/api/admin/bay-auto-assigner":
            if not self.require_permission("manage_bay_auto_assigner"):
                return
            self.send_json(STORE.get_bay_auto_assign_settings())
            return

        if parsed.path == "/api/glass-type-colors":
            # v0.379: Glass colors are presentation metadata, not an admin-only secret.
            # Every authenticated operator needs the same Lookup Manager palette so
            # Scan, Bay Map, racks, rejects, and other workflows stay visually consistent.
            if not self.current_user():
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            lookups = STORE.get_manual_edit_lookups() or {}
            # v0.452: color consumers need aliases in the same lightweight payload.
            # This removes the startup race where Scan could paint a combined source
            # name before the separate presentation-profile request loaded aliases.
            self.send_json({
                "glassColors": lookups.get("glassColors", []),
                "glassAliases": lookups.get("glassAliases", []),
            })
            return

        if parsed.path == "/api/admin/manual-edit-lookups":
            if not self.require_any_permission("manage_lookup_values", "edit_delivery_list_items", "create_delivery_list_orders"):
                return
            self.send_json(STORE.get_manual_edit_lookups())
            return

        if parsed.path == "/api/admin/permissions":
            if not self.require_permission("manage_roles"):
                return
            self.send_json({"permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/roles":
            if not self.require_any_permission("manage_roles", "manage_user_assignments", "manage_users"):
                return
            self.send_json({"roles": STORE.list_roles(), "permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/delivery-list-update-preview":
            user = self.require_any_permission("preview_delivery_updates", "edit_delivery_list_items", "preview_delivery_imports")
            if not user:
                return
            list_id = str(parse_qs(parsed.query).get("listId", [""])[0] or "").strip()
            if not list_id:
                self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                return
            if not self.user_can_preview_delivery_update(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            try:
                self.send_json(STORE.get_delivery_list_update_preview(list_id))
            except (KeyError, ValueError) as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                traceback.print_exc()
                self.send_json(
                    {"error": f"Unable to load the delivery-list update preview: {exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if parsed.path == "/api/admin/line-items/search":
            if not self.require_any_permission("edit_delivery_list_items", "delete_delivery_list_items", "create_delivery_list_orders"):
                return
            query_values = parse_qs(parsed.query)
            query = query_values.get("q", [""])[0]
            list_id = query_values.get("listId", [""])[0]
            limit = int(query_values.get("limit", ["20"])[0] or 20)
            offset = int(query_values.get("offset", ["0"])[0] or 0)
            filters = {
                "progress": query_values.get("progress", ["all"])[0],
                "route": query_values.get("route", ["all"])[0],
                "location": query_values.get("location", ["all"])[0],
                "attention": [value for raw in query_values.get("attention", []) for value in str(raw).split(",") if value],
                "glassTypes": [str(value).strip() for value in query_values.get("glassType", []) if str(value).strip()],
                # v0.468: Whole Delivery List editing uses the same maintained
                # search endpoint, scoped to one delivery date and de-duplicated
                # by physical line identity in the store.
                "wholeList": query_values.get("wholeList", ["0"])[0] in {"1", "true", "yes"},
                "deliveryDate": str(query_values.get("deliveryDate", [""])[0] or "").strip(),
            }
            self.send_json(STORE.admin_search_line_items(query, list_id, limit, offset, filters))
            return

        if parsed.path == "/api/admin/action-history":
            query_values = parse_qs(parsed.query)
            context = str(query_values.get("context", [""])[0] or "").strip()
            context_permissions = ACTION_HISTORY_CONTEXT_PERMISSIONS.get(context, ("view_admin",))
            user = self.require_any_permission(*context_permissions)
            if not user:
                return
            rack_code = query_values.get("rackCode", [""])[0]
            rack_codes = [
                value
                for raw in query_values.get("rackCodes", [])
                for value in str(raw).split(",")
                if str(value).strip()
            ]
            page = int(query_values.get("page", ["1"])[0] or 1)
            page_size = int(query_values.get("pageSize", ["50"])[0] or 50)
            self.send_json(
                STORE.list_gui_action_history_page(
                    context=context,
                    page=page,
                    page_size=page_size,
                    rack_code=rack_code,
                    query=query_values.get("query", [""])[0],
                    user=query_values.get("user", [""])[0],
                    action=query_values.get("action", [""])[0],
                    date_from=query_values.get("dateFrom", [""])[0],
                    date_to=query_values.get("dateTo", [""])[0],
                    rack_codes=rack_codes if "rackCodes" in query_values else None,
                )
            )
            return

        if parsed.path == "/api/admin/sessions":
            if not self.require_permission("view_sessions"):
                return
            self.send_json({"sessions": STORE.list_active_sessions()})
            return

        if parsed.path == "/api/admin/audit":
            if not self.require_permission("view_admin"):
                return
            limit = parse_qs(parsed.query).get("limit", ["100"])[0]
            self.send_json({"events": STORE.list_audit_events(int(limit or 100))})
            return

        if parsed.path == "/api/search":
            user = self.require_permission("global_search")
            if not user:
                return
            query = parse_qs(parsed.query).get("q", [""])[0]
            self.send_json({"results": STORE.global_search(query, user)})
            return

        if parsed.path == "/api/reports/summary":
            if not self.require_permission("view_reports"):
                return
            filters = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.send_json(STORE.reports_summary(filters))
            return

        if parsed.path == "/api/indian-trail/summary":
            if not self.require_permission("view_indian_trail"):
                return
            delivery_date = parse_qs(parsed.query).get("deliveryDate", [""])[0]
            self.send_json(STORE.indian_trail_summary(delivery_date))
            return

        if parsed.path == "/api/indian-trail/in-transit":
            if not self.require_permission("view_indian_trail"):
                return
            delivery_date = parse_qs(parsed.query).get("deliveryDate", [""])[0]
            self.send_json(STORE.indian_trail_in_transit(delivery_date))
            return

        if parsed.path == "/api/indian-trail/bays":
            if not self.require_permission("view_bays"):
                return
            self.send_json({"bays": STORE.get_bays()})
            return

        if parsed.path == "/api/indian-trail/bay-job-details":
            if not self.require_permission("view_bays"):
                return
            bay_code = parse_qs(parsed.query).get("bayCode", [""])[0]
            self.send_json(STORE.get_bay_job_details(bay_code))
            return

        if parsed.path == "/api/indian-trail/sdi-workspace":
            if not self.require_permission("view_bays"):
                return
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            bay_code = params.get("bayCode", [""])[0]
            self.send_json(STORE.get_sdi_workspace(query, bay_code))
            return

        if parsed.path == "/api/indian-trail/priority-work-lookup":
            if not self.require_permission("manage_rush_work"):
                return
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            priority_type = params.get("priorityType", ["Rush"])[0]
            self.send_json(STORE.priority_work_lookup(query, priority_type))
            return

        if parsed.path == "/api/indian-trail/layout":
            if not self.require_permission("view_bays"):
                return
            self.send_json(STORE.get_bay_layout())
            return

        if parsed.path == "/api/indian-trail/events":
            if not self.require_permission("view_bays"):
                return
            params = parse_qs(parsed.query)

            def bounded_positive_int(name: str, default: int, maximum: int) -> int:
                try:
                    value = int(params.get(name, [str(default)])[0] or default)
                except (TypeError, ValueError):
                    value = default
                return max(1, min(value, maximum))

            page = bounded_positive_int("page", 1, 100000)
            requested_size = params.get("pageSize", params.get("limit", ["20"]))[0]
            try:
                page_size = max(1, min(int(requested_size or 20), 25))
            except (TypeError, ValueError):
                page_size = 20
            self.send_json(STORE.get_bay_events_page(page, page_size))
            return

        if parsed.path == "/api/indian-trail/stale-bays":
            user = self.require_permission("view_bays")
            if not user:
                return
            params = parse_qs(parsed.query)
            include_snoozed = params.get("includeSnoozed", ["0"])[0] in {"1", "true", "yes"}
            claim_alert = params.get("claimAlert", ["0"])[0] in {"1", "true", "yes"}
            orders = STORE.get_stale_bay_orders(include_snoozed=include_snoozed)
            unique_orders = {
                (str(order.get("deliveryDate") or ""), str(order.get("order") or order.get("assignmentId") or ""))
                for order in orders
            }
            alert = (
                STORE.claim_stale_bay_alert(user.get("username", "user"), len(unique_orders), 6)
                if claim_alert and not include_snoozed
                else {"shouldNotify": False, "orderCount": len(unique_orders), "intervalHours": 6}
            )
            self.send_json({"orders": orders, "alert": alert})
            return

        if parsed.path == "/api/indian-trail/stale-bays/print":
            if not self.require_permission("view_bays"):
                return
            params = parse_qs(parsed.query)
            rows = filter_stale_bay_report_rows(
                STORE.get_stale_bay_orders(include_snoozed=True),
                params,
            )
            body = render_stale_bay_report(rows).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/racks":
            if not self.require_permission("view_racks"):
                return
            self.send_json(STORE.get_racks())
            return

        if parsed.path == "/api/racks/packing-list":
            user = self.require_permission("view_racks")
            if not user:
                return
            params = parse_qs(parsed.query)
            rack_code = params.get("rackCode", [""])[0]
            delivery_date = params.get("deliveryDate", [""])[0]
            body = render_rack_packing_list(STORE.rack_packing_list(rack_code, delivery_date)).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/delivery-lists/"):
            user = self.require_permission("view_delivery_lists")
            if not user:
                return
            list_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                self.send_json(STORE.get_delivery_list(list_id, user=user))
            except PermissionError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
            except KeyError:
                self.send_json({"error": "Delivery list not found"}, HTTPStatus.NOT_FOUND)
            return

        if parsed.path == "/api/export.csv":
            user = self.require_permission("print_export")
            if not user:
                return
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            body = STORE.export_csv(list_id).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/export.xlsx":
            user = self.require_permission("print_export")
            if not user:
                return
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            body = STORE.export_xlsx(list_id)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.xlsx")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/print/package-preview":
            user = self.require_permission("print_export")
            if not user:
                return
            params = parse_qs(parsed.query)
            raw_ids = params.get("listId", [])
            list_ids = []
            for value in raw_ids:
                list_ids.extend(part for part in value.split(",") if part)
            unique_list_ids = list(dict.fromkeys(list_ids))
            package = STORE.get_print_package(
                unique_list_ids,
                user=user,
                filters={key: values[0] for key, values in params.items()},
            )
            self.send_json(summarize_print_package(package, requested_stage_count=len(unique_list_ids)))
            return

        if parsed.path == "/api/export/package.xlsx":
            user = self.require_permission("print_export")
            if not user:
                return
            params = parse_qs(parsed.query)
            token = params.get("token", [""])[0]
            session = read_print_package_session(token, user) if token else None
            if token and not session:
                self.send_json({"error": "This print/export selection has expired. Reopen Print / Export and try again."}, HTTPStatus.GONE)
                return
            if session:
                list_ids = session["listIds"]
                filters = session["filters"]
            else:
                raw_ids = params.get("listId", [])
                list_ids = []
                for value in raw_ids:
                    list_ids.extend(part for part in value.split(",") if part)
                filters = {key: values[0] for key, values in params.items()}
            body = STORE.export_package_xlsx(list_ids, user=user, filters=filters)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.xlsx")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/export/package.csv":
            user = self.require_permission("print_export")
            if not user:
                return
            params = parse_qs(parsed.query)
            token = params.get("token", [""])[0]
            session = read_print_package_session(token, user) if token else None
            if token and not session:
                self.send_json({"error": "This print/export selection has expired. Reopen Print / Export and try again."}, HTTPStatus.GONE)
                return
            if session:
                list_ids = session["listIds"]
                filters = session["filters"]
            else:
                raw_ids = params.get("listId", [])
                list_ids = []
                for value in raw_ids:
                    list_ids.extend(part for part in value.split(",") if part)
                filters = {key: values[0] for key, values in params.items()}
            body = STORE.export_package_csv(list_ids, user=user, filters=filters).encode("utf-8-sig")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/print/package":
            user = self.require_permission("print_export")
            if not user:
                return
            params = parse_qs(parsed.query)
            token = params.get("token", [""])[0]
            session = read_print_package_session(token, user) if token else None
            if token and not session:
                self.send_html("<h1>This print selection has expired.</h1><p>Close this window and run Print / Export again.</p>", HTTPStatus.GONE)
                return
            if session:
                list_ids = session["listIds"]
                filters = session["filters"]
            else:
                raw_ids = params.get("listId", [])
                list_ids = []
                for value in raw_ids:
                    list_ids.extend(part for part in value.split(",") if part)
                filters = {key: values[0] for key, values in params.items()}
            package = STORE.get_print_package(list_ids, user=user, filters=filters)
            self.send_html(render_print_package(package))
            return

        super().do_GET()

    def do_POST(self) -> None:
        """Purpose: Handle post for the delivery-list scanner workflow.

        Effects: This function writes an HTTP response.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        parsed = urlparse(self.path)
        try:
            data = self.read_json()

            if parsed.path == "/api/print/package-preview":
                user = self.require_permission("print_export")
                if not user:
                    return
                list_ids, filters, _copies, _orientation = normalize_print_package_request(data)
                package = STORE.get_print_package(list_ids, user=user, filters=filters)
                self.send_json(summarize_print_package(package, requested_stage_count=len(list_ids)))
                return

            if parsed.path == "/api/print/package-session":
                user = self.require_permission("print_export")
                if not user:
                    return
                list_ids, filters, copies, orientation = normalize_print_package_request(data)
                package = STORE.get_print_package(list_ids, user=user, filters=filters)
                preview = summarize_print_package(package, requested_stage_count=len(list_ids))
                if preview.get("noResults"):
                    self.send_json(
                        {"error": "The selected filters produced no printable rows.", "preview": preview},
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                    )
                    return
                token = create_print_package_session(user, list_ids, filters)
                self.send_json({"ok": True, "token": token, "copies": copies, "orientation": orientation, "preview": preview})
                return

            if parsed.path == "/api/login":
                try:
                    payload = STORE.authenticate_user(str(data.get("username") or ""), str(data.get("password") or ""))
                except PermissionError as exc:
                    self.send_json({"error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                    return
                body = json.dumps({"authenticated": True, "user": payload["user"]}, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.set_session_cookie(payload["token"], payload["expiresAt"])
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/password-reset/request":
                self.send_json(STORE.request_password_reset(str(data.get("identity") or data.get("username") or data.get("email") or "")))
                return

            if parsed.path == "/api/password-reset/confirm":
                self.send_json(
                    STORE.confirm_password_reset(
                        str(data.get("identity") or data.get("username") or data.get("email") or ""),
                        str(data.get("resetCode") or data.get("code") or ""),
                        str(data.get("newPassword") or data.get("password") or ""),
                    )
                )
                return

            if parsed.path == "/api/logout":
                STORE.delete_session(self.session_token())
                body = json.dumps({"ok": True}, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.clear_session_cookie()
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/notifications/acknowledge":
                user = self.current_user()
                if not user:
                    self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_json(
                    STORE.acknowledge_notification(
                        int(data.get("notificationId") or 0),
                        user["username"],
                    )
                )
                return
            if parsed.path == "/api/notifications/read-all":
                user = self.current_user()
                if not user:
                    self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_json(STORE.mark_all_notifications_read(user["username"]))
                return
            if parsed.path == "/api/delivery-list-updates/acknowledge":
                user = self.require_permission("view_delivery_lists")
                if not user:
                    return
                list_id = str(data.get("listId") or "").strip()
                if not list_id:
                    self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                    return
                if not STORE.user_can_access_list(user, list_id):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                notice_ids = data.get("noticeIds") if isinstance(data.get("noticeIds"), list) else None
                self.send_json(STORE.acknowledge_user_line_updates(user["username"], list_id, notice_ids))
                return

            # DLS_V135_OPERATIONS_POST_ROUTES
            if parsed.path == "/api/operations/line-flags/acknowledge":
                user = self.require_permission("view_delivery_lists")
                if not user:
                    return
                list_id = str(data.get("listId") or "").strip()
                if not list_id:
                    self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                    return
                if not STORE.user_can_access_list(user, list_id):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                notice_ids = data.get("noticeIds") if isinstance(data.get("noticeIds"), list) else []
                self.send_json(OPERATIONS.acknowledge_line_updates(list_id, notice_ids, user["username"]))
                return

            if parsed.path == "/api/rejects":
                user = self.require_permission("log_rejects")
                if not user:
                    return
                self.send_json(OPERATIONS.create_reject(data, user["username"]))
                return

            if parsed.path == "/api/rejects/update":
                user = self.require_permission("manage_reject_records")
                if not user:
                    return
                self.send_json(OPERATIONS.update_reject(data, user["username"]))
                return

            if parsed.path == "/api/rejects/delete":
                user = self.require_permission("manage_reject_records")
                if not user:
                    return
                self.send_json(OPERATIONS.delete_reject(data, user["username"]))
                return

            if parsed.path == "/api/rejects/catalog":
                user = self.require_permission("manage_reject_settings")
                if not user:
                    return
                self.send_json(
                    OPERATIONS.upsert_reject_catalog(
                        str(data.get("kind") or ""),
                        str(data.get("label") or ""),
                        user["username"],
                    )
                )
                return

            if parsed.path == "/api/rejects/catalog/update":
                user = self.require_permission("manage_reject_settings")
                if not user:
                    return
                self.send_json(
                    OPERATIONS.update_reject_catalog(
                        str(data.get("kind") or ""),
                        int(data.get("id") or 0),
                        str(data.get("label") or ""),
                        user["username"],
                    )
                )
                return

            if parsed.path == "/api/rejects/catalog/remove":
                user = self.require_permission("manage_reject_settings")
                if not user:
                    return
                self.send_json(
                    OPERATIONS.remove_reject_catalog(
                        str(data.get("kind") or ""),
                        int(data.get("id") or 0),
                        user["username"],
                    )
                )
                return

            if parsed.path == "/api/admin/superseded-order-reviews/decision":
                user = self.require_permission("review_superseded_orders")
                if not user:
                    return
                self.send_json(
                    STORE.decide_superseded_order_review(
                        int(data.get("reviewId") or data.get("id") or 0),
                        str(data.get("action") or ""),
                        user["username"],
                        str(data.get("reason") or ""),
                        str(data.get("removeOrderNumber") or ""),
                    )
                )
                return

            if parsed.path == "/api/admin/manual-order":
                user = self.require_permission("create_delivery_list_orders")
                if not user:
                    return
                self.send_json(OPERATIONS.create_manual_order(data, user["username"]))
                return

            if parsed.path == "/api/racks/packing-history":
                user = self.require_any_permission("view_racks", "print_export")
                if not user:
                    return
                self.send_json(OPERATIONS.record_packing_print(data, user["username"]))
                return

            if parsed.path == "/api/scans":
                user = self.require_permission("scan_delivery_lists")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                data["user"] = user["username"]
                data["_userContext"] = user
                self.send_json(STORE.record_scan(data))
                return

            if parsed.path == "/api/reset":
                user = self.require_permission("reset_delivery_lists")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                if not self.require_confirmation_text(data, "RESET"):
                    return
                self.send_json(
                    STORE.reset_stage(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/undo":
                user = self.require_permission("correct_scans")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.undo_last_scan(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/redo":
                user = self.require_permission("correct_scans")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.redo_last_undo(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/stations":
                if not self.require_permission("manage_stations"):
                    return
                self.send_json(STORE.add_station(str(data.get("name") or "")))
                return

            if parsed.path == "/api/stations/remove":
                if not self.require_permission("manage_stations"):
                    return
                self.send_json(STORE.remove_station(str(data.get("name") or "")))
                return

            if parsed.path == "/api/stations/rename":
                if not self.require_permission("manage_stations"):
                    return
                self.send_json(STORE.rename_station(str(data.get("oldName") or ""), str(data.get("newName") or "")))
                return

            if parsed.path == "/api/import":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                data["user"] = user["username"]
                self.send_json(STORE.import_delivery_list(data))
                return

            if parsed.path == "/api/import/folder":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                data["user"] = user["username"]
                self.send_json(STORE.import_delivery_folder(data))
                return
            if parsed.path == "/api/admin/delivery-automation/run":
                user = self.require_any_permission("manage_automation", "import_delivery_lists")
                if not user:
                    return
                self.send_json(
                    DELIVERY_AUTOMATION.start_run(data, user["username"]),
                    HTTPStatus.ACCEPTED,
                )
                return

            if parsed.path == "/api/admin/delivery-automation/config":
                user = self.require_any_permission("manage_automation", "import_delivery_lists")
                if not user:
                    return
                self.send_json(DELIVERY_AUTOMATION.save_settings(data, user["username"]))
                return

            if parsed.path == "/api/admin/delivery-automation/schedule/install":
                if not self.require_any_permission("manage_automation", "import_delivery_lists"):
                    return
                self.send_json(DELIVERY_AUTOMATION.install_schedule())
                return

            if parsed.path == "/api/admin/delivery-automation/schedule/remove":
                if not self.require_any_permission("manage_automation", "import_delivery_lists"):
                    return
                self.send_json(DELIVERY_AUTOMATION.remove_schedule())
                return

            if parsed.path == "/api/import/preview":
                if not self.require_permission("preview_delivery_imports"):
                    return
                self.send_json(STORE.preview_import(data.get("payload") or data))
                return

            if parsed.path == "/api/exceptions/resolve":
                user = self.require_permission("manage_scan_exceptions")
                if not user:
                    return
                self.send_json(STORE.resolve_exception(data, user["username"]))
                return

            if parsed.path == "/api/admin/users":
                user = self.require_all_permissions("manage_users", "manage_user_assignments")
                if not user:
                    return
                self.send_json({"user": STORE.create_user(data, created_by=user["username"])})
                return

            if parsed.path == "/api/admin/users/deactivate":
                user = self.require_permission("manage_user_access")
                if not user:
                    return
                self.send_json(STORE.deactivate_user(str(data.get("username") or ""), deactivated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/reactivate":
                user = self.require_permission("manage_user_access")
                if not user:
                    return
                self.send_json(STORE.reactivate_user(str(data.get("username") or ""), activated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/delete":
                user = self.require_permission("manage_users")
                if not user:
                    return
                self.send_json(STORE.delete_user(str(data.get("username") or ""), deleted_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/password":
                user = self.require_permission("manage_user_access")
                if not user:
                    return
                self.send_json(STORE.update_user_password(str(data.get("username") or ""), str(data.get("password") or ""), updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/roles":
                user = self.require_permission("manage_user_assignments")
                if not user:
                    return
                self.send_json(
                    STORE.update_user_roles(
                        str(data.get("username") or ""),
                        data.get("roles") or [],
                        station=data.get("station"),
                        email=data.get("email"),
                        display_name=data.get("displayName"),
                        updated_by=user["username"],
                    )
                )
                return

            if parsed.path == "/api/admin/roles":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(STORE.create_role(data, created_by=user["username"]), HTTPStatus.CREATED)
                return

            if parsed.path == "/api/admin/roles/permissions":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(STORE.update_role_permissions(str(data.get("role") or ""), data.get("permissions") or [], updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/line-item":
                user = self.require_permission("edit_delivery_list_items")
                if not user:
                    return
                self.send_json(STORE.update_line_item(data, user["username"]))
                return

            if parsed.path == "/api/admin/line-item/delete":
                user = self.require_permission("delete_delivery_list_items")
                if not user:
                    return
                self.send_json(STORE.delete_line_item(str(data.get("lineItemId") or ""), user["username"]))
                return

            if parsed.path == "/api/admin/customer-route-rules":
                user = self.require_permission("manage_route_rules")
                if not user:
                    return
                self.send_json(STORE.add_customer_route_rule(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-route-rules/remove":
                user = self.require_permission("manage_route_rules")
                if not user:
                    return
                self.send_json(STORE.remove_customer_route_rule(int(data.get("ruleId") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails":
                user = self.require_permission("manage_customer_emails")
                if not user:
                    return
                self.send_json(STORE.upsert_customer_email_contact(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/remove":
                user = self.require_permission("manage_customer_emails")
                if not user:
                    return
                self.send_json(STORE.remove_customer_email_contact(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/draft/delete":
                user = self.require_permission("manage_customer_emails")
                if not user:
                    return
                self.send_json(STORE.delete_customer_email_draft(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/test":
                user = self.require_permission("manage_customer_emails")
                if not user:
                    return
                self.send_json(STORE.queue_customer_email_test(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/cc":
                user = self.require_permission("manage_customer_emails")
                if not user:
                    return
                self.send_json(STORE.upsert_customer_email_cc(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/cc/remove":
                user = self.require_permission("manage_customer_emails")
                if not user:
                    return
                self.send_json(STORE.remove_customer_email_cc(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/bay-scanner-rules/settings":
                user = self.require_permission("manage_bay_scanner_rules")
                if not user:
                    return
                self.send_json(STORE.update_bay_scan_settings(data, user["username"]))
                return

            if parsed.path == "/api/admin/cross-date-scan-settings":
                user = self.require_permission("manage_cross_date_scanning")
                if not user:
                    return
                self.send_json(STORE.update_cross_date_scan_settings(data, user["username"]))
                return

            if parsed.path == "/api/admin/bay-scanner-rules/manual":
                user = self.require_permission("manage_bay_scanner_rules")
                if not user:
                    return
                self.send_json(STORE.upsert_bay_manual_input_rule(data, user["username"]))
                return

            if parsed.path == "/api/admin/bay-scanner-rules/manual/remove":
                user = self.require_permission("manage_bay_scanner_rules")
                if not user:
                    return
                self.send_json(STORE.remove_bay_manual_input_rule(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/bay-scanner-rules/barcode":
                user = self.require_permission("manage_bay_scanner_rules")
                if not user:
                    return
                self.send_json(STORE.upsert_bay_scan_barcode_rule(data, user["username"]))
                return

            if parsed.path == "/api/admin/bay-scanner-rules/barcode/remove":
                user = self.require_permission("manage_bay_scanner_rules")
                if not user:
                    return
                self.send_json(STORE.remove_bay_scan_barcode_rule(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/bay-auto-assigner":
                user = self.require_permission("manage_bay_auto_assigner")
                if not user:
                    return
                self.send_json(STORE.update_bay_auto_assign_settings(data, user["username"]))
                return

            if parsed.path == "/api/admin/presentation-profile":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(STORE.update_presentation_profile(data, user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups/glass-profile":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(STORE.upsert_glass_profile(data, user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups/glass-profile/combine":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(STORE.combine_glass_profiles(data, user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups/glass-profile/uncombine":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(STORE.uncombine_glass_profiles(data, user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups/glass-profile/remove":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(STORE.remove_glass_profile(str(data.get("value") or ""), user["username"], data.get("values")))
                return

            if parsed.path == "/api/admin/manual-edit-lookups":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(STORE.add_manual_edit_lookup(data, user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups/remove":
                user = self.require_permission("manage_lookup_values")
                if not user:
                    return
                self.send_json(
                    STORE.remove_manual_edit_lookup(
                        str(data.get("type") or ""),
                        str(data.get("value") or ""),
                        user["username"],
                    )
                )
                return

            if parsed.path == "/api/admin/delete-list":
                user = self.require_permission("delete_delivery_lists")
                if not user:
                    return
                if not self.require_confirmation_text(data, "DELETE"):
                    return
                self.send_json(STORE.delete_delivery_list(str(data.get("listId") or ""), user["username"]))
                return

            if parsed.path == "/api/admin/delete-date":
                user = self.require_permission("delete_delivery_lists")
                if not user:
                    return
                if not self.require_confirmation_text(data, "DELETE"):
                    return
                self.send_json(STORE.delete_delivery_date(str(data.get("deliveryDate") or ""), user["username"]))
                return

            if parsed.path == "/api/indian-trail/receive":
                user = self.require_permission("receive_indian_trail")
                if not user:
                    return
                if data.get("listId") and not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                data["user"] = user["username"]
                data["_userContext"] = user
                self.send_json(STORE.receive_indian_trail_scan(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/manual-assign":
                user = self.require_permission("assign_bay_items")
                if not user:
                    return
                self.send_json(STORE.manual_assign_bay_item(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/assign":
                user = self.require_permission("assign_bay_items")
                if not user:
                    return
                self.send_json(STORE.assign_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/move":
                user = self.require_any_permission("move_bay_items", "receive_indian_trail")
                if not user:
                    return
                self.send_json(STORE.move_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear":
                user = self.require_permission("clear_bay_items")
                if not user:
                    return
                self.send_json(STORE.clear_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear-assignment":
                user = self.require_any_permission("clear_bay_items", "receive_indian_trail")
                if not user:
                    return
                self.send_json(STORE.clear_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/restore-assignment":
                user = self.require_any_permission("clear_bay_items", "receive_indian_trail")
                if not user:
                    return
                self.send_json(STORE.restore_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-status":
                user = self.require_permission("clear_bay_items")
                if not user:
                    return
                self.send_json(STORE.set_bay_status(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/scan-out":
                user = self.require_any_permission("clear_bay_items", "receive_indian_trail")
                if not user:
                    return
                self.send_json(STORE.scan_out_bay_item(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/layout":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                if data.get("setGroupPosition"):
                    self.send_json(STORE.set_bay_group_position(data, user["username"]))
                elif data.get("moveGroup"):
                    self.send_json(STORE.move_bay_group(data, user["username"]))
                else:
                    self.send_json(STORE.update_bay_layout(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bays/add":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                self.send_json(STORE.create_bays(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bays/delete":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                self.send_json(STORE.delete_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bays/delete-group":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                self.send_json(STORE.delete_bay_group(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/priority-work":
                user = self.require_permission("manage_rush_work")
                if not user:
                    return
                self.send_json(STORE.submit_priority_work(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/priority-intake":
                user = self.require_permission("manage_rush_work")
                if not user:
                    return
                if str(data.get("requestId") or "").strip():
                    self.send_json(STORE.update_priority_intake_request(data, user["username"]))
                else:
                    self.send_json(STORE.create_priority_intake_request(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/priority-intake/cancel":
                user = self.require_permission("manage_rush_work")
                if not user:
                    return
                self.send_json(STORE.cancel_priority_intake_request(str(data.get("requestId") or ""), user["username"]))
                return

            if parsed.path == "/api/indian-trail/mark-sdi":
                user = self.require_permission("manage_rush_work")
                if not user:
                    return
                self.send_json(STORE.mark_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/remove-sdi":
                user = self.require_permission("manage_rush_work")
                if not user:
                    return
                self.send_json(STORE.remove_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-check":
                user = self.require_permission("run_bay_checks")
                if not user:
                    return
                self.send_json(STORE.bay_check(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/stale-bays/snooze":
                user = self.require_permission("view_bays")
                if not user:
                    return
                self.send_json(STORE.snooze_stale_bay_orders(data, user["username"]))
                return

            if parsed.path == "/api/racks/scan":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(STORE.scan_item_to_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/complete":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                self.send_json(STORE.complete_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/uncomplete":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                self.send_json(STORE.uncomplete_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/return":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                self.send_json(STORE.return_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/on-way":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                self.send_json(STORE.mark_rack_on_way(data, user["username"]))
                return

            if parsed.path == "/api/racks/not-on-way":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                if not self.require_confirmation_text(data, "NOT ON THE WAY"):
                    return
                self.send_json(STORE.not_on_way_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/assign-line-item":
                user = self.require_rack_recovery_power()
                if not user:
                    return
                self.send_json(STORE.assign_line_item_to_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/move-item":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.move_rack_item(data, user["username"]))
                return

            if parsed.path == "/api/racks/move-contents":
                user = self.require_any_permission("transfer_rack_contents", "manage_racks")
                if not user:
                    return
                self.send_json(STORE.move_rack_contents(data, user["username"]))
                return

            if parsed.path == "/api/racks/clear-item":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.clear_rack_item(data, user["username"]))
                return

            if parsed.path == "/api/racks/clear":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.clear_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.update_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/create-set":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.create_rack_set(data, user["username"]))
                return

            if parsed.path == "/api/racks/delete":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.delete_rack(data, user["username"]))
                return

            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def daily_import_loop() -> None:
    """Run the Temp Delivery Lists import once per day at 5 PM Eastern.

    This is intentionally local-server based. If the server is not running at
    5 PM Eastern, the next run happens the next time the server is running at
    the scheduled time.
    """
    if os.environ.get("DLS_DAILY_IMPORT_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        return
    try:
        eastern_tz = ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        eastern_tz = None
        print("Timezone database unavailable; daily import will use the Windows local timezone.")

    def scheduled_now() -> datetime:
        return datetime.now(eastern_tz) if eastern_tz is not None else datetime.now().astimezone()

    while True:
        now = scheduled_now()
        next_run = now.replace(hour=17, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        time.sleep(max((next_run - now).total_seconds(), 1))
        try:
            date_from = (scheduled_now().date() - timedelta(days=7)).isoformat()
            result = STORE.import_delivery_folder({"user": "daily-auto-import", "dateFrom": date_from, "dateTo": ""})
            print(f"Daily 5 PM ET delivery-list import complete: {result.get('scannedFiles', 0)} files checked")
        except Exception as exc:
            print(f"Daily 5 PM ET delivery-list import failed: {exc}")


def start_daily_import_scheduler() -> None:
    """Purpose: Run the start daily import scheduler workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    thread = threading.Thread(target=daily_import_loop, name="daily-delivery-list-import", daemon=True)
    thread.start()


def write_startup_failure_log(exc: BaseException) -> Path:
    """Persist startup failures so the Windows launcher can show a useful diagnosis.

    Effects: Creates or appends ``logs/startup-error.log`` beside the application.
    Flow: Records the timestamp, Python/runtime details, configured database path,
    and the complete traceback without modifying the SQLite database.
    """
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "startup-error.log"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    details = [
        "=" * 80,
        f"Startup failure: {timestamp}",
        f"Python: {sys.version}",
        f"Executable: {sys.executable}",
        f"Application root: {ROOT}",
        f"Database type: {CONFIG.database_type}",
        f"Database path: {CONFIG.database_path}",
        "",
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip(),
        "",
    ]
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(details))
    return log_path


def main() -> int:
    """Start the database, scheduler, and HTTP server in a diagnosable order.

    Effects: Initializes the configured store, starts the optional daily import
    scheduler, binds the local HTTP port, and serves the browser application.
    Flow: Emits flushed startup milestones so launchers can distinguish database
    initialization from port-binding failures.
    """
    print("Initializing Delivery List Scanner database...", flush=True)
    STORE.initialize()
    print("Database initialization complete.", flush=True)
    start_daily_import_scheduler()
    print(f"Binding web server to {CONFIG.host}:{CONFIG.port}...", flush=True)
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), Handler)
    health = STORE.health()
    print(f"Delivery List Scanner running at http://{CONFIG.host}:{CONFIG.port}/", flush=True)
    print(f"Database type: {health.get('mode', CONFIG.database_type)}", flush=True)
    print(f"Database: {health.get('database', CONFIG.database_path)}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Delivery List Scanner stopped.", flush=True)
        raise SystemExit(0)
    except Exception as exc:
        log_path = write_startup_failure_log(exc)
        print(f"Delivery List Scanner failed to start: {exc}", file=sys.stderr, flush=True)
        print(f"Startup details were written to: {log_path}", file=sys.stderr, flush=True)
        raise
