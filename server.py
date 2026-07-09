#!/usr/bin/env python
"""Local pilot server for the delivery-list scanner web app."""

from __future__ import annotations

import json
import html
import os
import re
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from delivery_store import SESSION_COOKIE_NAME, create_store, request_station, request_user_name
from scanner_config import load_config


ROOT = Path(__file__).resolve().parent
CONFIG = load_config(ROOT)
STORE = create_store(CONFIG)


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


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
              <td class="print-nowrap route-cell">{esc(item.get("route"))}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """


def paginate_item_rows(items: list[dict], rows_per_page: int = 23) -> list[str]:
    """Build explicit one-paper-page chunks for printed delivery lists.

    Important for future edits: the browser print preview only understands the
    sections we give it. If this number is too high, Chrome/Edge may split one
    logical list page across two physical pieces of paper, which makes the page
    label wrong. Keep this conservative so every rendered <section class="sheet">
    fits on one printed page. The current print CSS uses larger rows/fonts, so
    rows_per_page is set to 23 to use more of the sheet without forcing the
    browser to create unexpected extra pages. The default print output is one physical
    copy, so the labels stay as the actual list page count: 1 of 3, 2 of 3,
    3 of 3.
    """
    if not items:
        return ['<tr><td colspan="8">No printable rows.</td></tr>']

    pages: list[str] = []
    current_rows: list[str] = []
    current_count = 0
    current_product = object()

    def flush_page() -> None:
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
        if current_rows and current_count + needed_rows > rows_per_page:
            flush_page()
            needs_group_row = True

        if needs_group_row:
            current_product = product
            current_rows.append(f'<tr class="glass-group"><td colspan="8">{esc(product)}</td></tr>')
            current_count += 1

        if current_count >= rows_per_page and current_rows:
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
    rack = payload.get("rack") or {}
    barcode = rack.get("barcode") or f"RACK-{rack.get('code', '')}"
    delivery_label = rack.get("deliveryLabel") or ""
    delivery_suffix = f" - {esc(delivery_label)}" if delivery_label else ""
    destination = rack.get("destination") or "Indian Trail"
    rows = []
    for item in rack.get("items") or []:
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
              <td>{esc(item.get("route"))}</td>
              <td class="flag-cell">{'RM' if printed_item_is_remake(item) else ''}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """
        )
    if not rows:
        rows.append('<tr><td colspan="10">No pieces are currently assigned to this rack.</td></tr>')
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{esc(rack.get("name") or rack.get("code"))} Packing List</title>
      <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
      <style>
        body {{ font-family: Arial, sans-serif; color: #071633; margin: 24px; }}
        header {{ display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; border-bottom: 3px solid #071633; padding-bottom: 14px; }}
        h1 {{ margin: 0; font-size: 28px; }}
        p {{ margin: 4px 0; }}
        .barcode-box {{ width: 320px; text-align: center; }}
        .rack-barcode {{ width: 100%; height: 72px; display: block; }}
        .barcode-text {{ font-size: 18px; font-weight: 900; letter-spacing: 1px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 12px; }}
        th, td {{ border: 1px solid #222; padding: 6px; text-align: left; }}
        th {{ background: #efefef; }}
        .check-cell {{ width: 44px; text-align: center; font-size: 20px; }}
        .notes {{ margin-top: 24px; border: 1px solid #222; min-height: 80px; padding: 8px; }}
        @media print {{ body {{ margin: 0.3in; }} button {{ display: none; }} }}
      </style>
    </head>
    <body onload="setTimeout(function(){{ window.print(); }}, 350)">
      <button onclick="window.print()">Print</button>
      <header>
        <div>
          <h1>{esc(rack.get("name") or rack.get("code"))} Packing List{delivery_suffix}</h1>
          <p>Rack Type: {esc(rack.get("type"))} | Destination: {esc(destination)} | Status: {esc(rack.get("status"))} | Qty: {esc(rack.get("qty"))}</p>
          <p>Scan this rack barcode on the outbound stage to mark the rack on the way.</p>
        </div>
        <div class="barcode-box">
          {code39_svg(str(barcode))}
          <div class="barcode-text">*{esc(barcode)}*</div>
        </div>
      </header>
      <table>
        <thead><tr><th>Delivery Date</th><th>Job Nr.</th><th>Order Nr.</th><th>Item Nr.</th><th>Qty</th><th>Dimensions</th><th>Customer</th><th>Route</th><th>Flags</th><th>Check</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      <div class="notes"><strong>Notes:</strong></div>
    </body>
    </html>
    """


def render_stale_bay_report(rows: list[dict]) -> str:
    body_rows = []
    for row in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{esc(row.get("daysOld"))} days</td>
              <td>{esc(row.get("bayDisplay") or row.get("bayCode"))}</td>
              <td>{esc(row.get("order"))}</td>
              <td>{esc(row.get("item"))}</td>
              <td>{esc(row.get("job") or row.get("product"))}</td>
              <td>{esc(row.get("dimensions"))}</td>
              <td>{esc(row.get("customer"))}</td>
              <td>{esc(row.get("deliveryDate"))}</td>
              <td>{esc(row.get("lastScannedAt"))}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """
        )
    if not body_rows:
        body_rows.append('<tr><td colspan="10">No bay orders are older than 10 days.</td></tr>')
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Old Bay Orders</title>
      <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
      <style>
        body {{ font-family: Arial, sans-serif; color: #071633; margin: 24px; }}
        header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #071633; padding-bottom: 12px; }}
        .copy-box {{ border: 1px solid #222; padding: 7px 10px; font-weight: 800; display: flex; gap: 14px; align-items: center; white-space: nowrap; }}
        .write-line {{ display: inline-block; height: 1em; border-bottom: 1px solid #222; vertical-align: -2px; }}
        .checked-line {{ width: 82px; }}
        .date-line {{ width: 112px; }}
        h1 {{ margin: 0; font-size: 26px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }}
        th, td {{ border: 1px solid #222; padding: 6px; text-align: left; vertical-align: top; }}
        th {{ background: #efefef; }}
        .check-cell {{ width: 44px; text-align: center; font-size: 20px; }}
        @media print {{ body {{ margin: 0.3in; }} button {{ display: none; }} }}
      </style>
    </head>
    <body>
      <button onclick="window.print()">Print</button>
      <header>
        <div>
          <h1>Old Bay Orders</h1>
          <p>Orders in Indian Trail bays more than 10 days.</p>
        </div>
        <div class="copy-box"><span>Checked By: <i class="write-line checked-line"></i></span><span>Date: <i class="write-line date-line"></i></span></div>
      </header>
      <table>
        <thead>
          <tr><th>Age</th><th>Bay</th><th>Order</th><th>Item</th><th>Job Nr.</th><th>Dimensions</th><th>Customer</th><th>Delivery</th><th>Last Scanned</th><th>Check</th></tr>
        </thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </body>
    </html>
    """


def render_print_package(package: dict) -> str:
    sections = []
    printed_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    filters = package.get("filters", {}) or {}
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
        if mode == "remake":
            return "REMAKE"
        if mode == "rush":
            return "RUSH"
        if updated_only or delivery_list.get("sheetKind") == "updated":
            return "UPDATED"
        return ""

    def sheet_subtitle(delivery_list: dict) -> str:
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
            sections.append(render_sheet(sheet_title(delivery_list, "rush"), "", rushes, "rush", sheet_badge(delivery_list, "rush"), printed_at))
        if remakes and not rush_only:
            title = sheet_title(delivery_list, "remake")
            # Remake sheets also print one physical copy by default.
            sections.append(render_sheet(title, "", remakes, "remake", sheet_badge(delivery_list, "remake"), printed_at))
    body = "".join(sections) or '<section class="sheet"><h1>No printable rows found</h1></section>'
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Delivery List Print Package</title>
  <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
  <style>
    body {{ margin: 0; color: #07122f; font-family: "Segoe UI", Arial, sans-serif; background: #f6f8fb; }}
    .sheet {{ width: min(1120px, calc(100% - 32px)); margin: 16px auto; padding: 18px 20px 14px; background: #fff; border: 1px solid #444; border-radius: 0; break-inside: avoid; page-break-inside: avoid; }}
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
    @page {{ size: letter portrait; margin: 0.25in; }}
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
  <script>window.addEventListener("load", () => setTimeout(() => window.print(), 250));</script>
</body>
</html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, markup: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = markup.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def session_token(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie(cookie_header)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel else ""

    def current_user(self) -> dict | None:
        return STORE.get_user_by_session(self.session_token())

    def require_permission(self, permission: str) -> dict | None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        if permission not in user.get("permissions", []):
            self.send_json({"error": "Permission denied", "permission": permission}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def set_session_cookie(self, token: str, expires_at: str) -> None:
        secure = "; Secure" if CONFIG.production else ""
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200{secure}",
        )

    def clear_session_cookie(self) -> None:
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self.send_json(STORE.health())
            return

        if parsed.path == "/api/session":
            user = self.current_user()
            self.send_json({"authenticated": bool(user), "user": user})
            return

        if parsed.path == "/api/delivery-lists":
            user = self.require_permission("view_lists")
            if not user:
                return
            self.send_json({"lists": STORE.get_delivery_lists(user)})
            return

        if parsed.path == "/api/stations":
            if not self.require_permission("view_stations"):
                return
            self.send_json({"stations": STORE.get_stations()})
            return

        if parsed.path == "/api/exceptions":
            if not self.require_permission("view_exceptions"):
                return
            filters = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.send_json({"exceptions": STORE.get_exceptions(filters)})
            return

        if parsed.path == "/api/admin/summary":
            if not self.require_permission("view_admin"):
                return
            self.send_json(STORE.admin_summary())
            return

        if parsed.path == "/api/admin/users":
            if not self.require_permission("manage_users"):
                return
            self.send_json({"users": STORE.list_users()})
            return

        if parsed.path == "/api/admin/customer-route-rules":
            if not self.require_permission("manage_customer_route_rules"):
                return
            self.send_json({"rules": STORE.get_customer_route_rules()})
            return

        if parsed.path == "/api/admin/customer-emails":
            if not self.require_permission("manage_customer_route_rules"):
                return
            self.send_json(STORE.get_customer_email_settings())
            return

        if parsed.path == "/api/admin/manual-edit-lookups":
            if not self.require_permission("edit_delivery_lists"):
                return
            self.send_json(STORE.get_manual_edit_lookups())
            return

        if parsed.path == "/api/admin/permissions":
            if not self.require_permission("manage_roles"):
                return
            self.send_json({"permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/roles":
            if not self.require_permission("manage_roles"):
                return
            self.send_json({"roles": STORE.list_roles(), "permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/line-items/search":
            if not self.require_permission("edit_delivery_lists"):
                return
            query = parse_qs(parsed.query).get("q", [""])[0]
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            self.send_json({"results": STORE.admin_search_line_items(query, list_id)})
            return

        if parsed.path == "/api/admin/sessions":
            if not self.require_permission("view_active_sessions"):
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
            self.send_json(STORE.indian_trail_summary())
            return

        if parsed.path == "/api/indian-trail/in-transit":
            if not self.require_permission("view_indian_trail"):
                return
            self.send_json(STORE.indian_trail_in_transit())
            return

        if parsed.path == "/api/indian-trail/bays":
            if not self.require_permission("view_bays"):
                return
            self.send_json({"bays": STORE.get_bays()})
            return

        if parsed.path == "/api/indian-trail/layout":
            if not self.require_permission("view_bays"):
                return
            self.send_json(STORE.get_bay_layout())
            return

        if parsed.path == "/api/indian-trail/events":
            if not self.require_permission("view_bays"):
                return
            limit = parse_qs(parsed.query).get("limit", ["20"])[0]
            self.send_json({"events": STORE.get_bay_events(int(limit or 20))})
            return

        if parsed.path == "/api/indian-trail/stale-bays":
            if not self.require_permission("view_bays"):
                return
            include_snoozed = parse_qs(parsed.query).get("includeSnoozed", ["0"])[0] in {"1", "true", "yes"}
            self.send_json({"orders": STORE.get_stale_bay_orders(include_snoozed=include_snoozed)})
            return

        if parsed.path == "/api/indian-trail/stale-bays/print":
            if not self.require_permission("view_bays"):
                return
            body = render_stale_bay_report(STORE.get_stale_bay_orders(include_snoozed=True)).encode("utf-8")
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
            user = self.require_permission("view_lists")
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
            user = self.require_permission("export_reports")
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
            user = self.require_permission("export_reports")
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

        if parsed.path == "/api/export/package.xlsx":
            user = self.require_permission("export_reports")
            if not user:
                return
            params = parse_qs(parsed.query)
            raw_ids = params.get("listId", [])
            list_ids = []
            for value in raw_ids:
                list_ids.extend(part for part in value.split(",") if part)
            body = STORE.export_package_xlsx(list_ids, user=user, filters={key: values[0] for key, values in params.items()})
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.xlsx")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/print/package":
            user = self.require_permission("export_reports")
            if not user:
                return
            params = parse_qs(parsed.query)
            raw_ids = params.get("listId", [])
            list_ids = []
            for value in raw_ids:
                list_ids.extend(part for part in value.split(",") if part)
            package = STORE.get_print_package(list_ids, user=user, filters={key: values[0] for key, values in params.items()})
            self.send_html(render_print_package(package))
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            data = self.read_json()

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

            if parsed.path == "/api/scans":
                user = self.require_permission("scan")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                data["user"] = user["username"]
                self.send_json(STORE.record_scan(data))
                return

            if parsed.path == "/api/reset":
                user = self.require_permission("reset_lists")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
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
                user = self.require_permission("undo_scan")
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
                user = self.require_permission("undo_scan")
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
                if not self.require_permission("remove_stations"):
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

            if parsed.path == "/api/import/preview":
                if not self.require_permission("preview_import"):
                    return
                self.send_json(STORE.preview_import(data.get("payload") or data))
                return

            if parsed.path == "/api/exceptions/resolve":
                user = self.require_permission("resolve_exceptions")
                if not user:
                    return
                self.send_json(STORE.resolve_exception(data, user["username"]))
                return

            if parsed.path == "/api/admin/users":
                user = self.require_permission("manage_users")
                if not user:
                    return
                self.send_json({"user": STORE.create_user(data, created_by=user["username"])})
                return

            if parsed.path == "/api/admin/users/deactivate":
                user = self.require_permission("deactivate_users")
                if not user:
                    return
                self.send_json(STORE.deactivate_user(str(data.get("username") or ""), deactivated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/reactivate":
                user = self.require_permission("reactivate_users")
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
                user = self.require_permission("update_user_passwords")
                if not user:
                    return
                self.send_json(STORE.update_user_password(str(data.get("username") or ""), str(data.get("password") or ""), updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/roles":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(
                    STORE.update_user_roles(
                        str(data.get("username") or ""),
                        data.get("roles") or [],
                        station=data.get("station"),
                        updated_by=user["username"],
                    )
                )
                return

            if parsed.path == "/api/admin/roles/permissions":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(STORE.update_role_permissions(str(data.get("role") or ""), data.get("permissions") or [], updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/line-item":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.update_line_item(data, user["username"]))
                return

            if parsed.path == "/api/admin/line-item/delete":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.delete_line_item(str(data.get("lineItemId") or ""), user["username"]))
                return

            if parsed.path == "/api/admin/customer-route-rules":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.add_customer_route_rule(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-route-rules/remove":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.remove_customer_route_rule(int(data.get("ruleId") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.upsert_customer_email_contact(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/remove":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.remove_customer_email_contact(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/test":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.queue_customer_email_test(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/cc":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.upsert_customer_email_cc(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-emails/cc/remove":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.remove_customer_email_cc(int(data.get("id") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.add_manual_edit_lookup(data, user["username"]))
                return

            if parsed.path == "/api/admin/delete-list":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.delete_delivery_list(str(data.get("listId") or ""), user["username"]))
                return

            if parsed.path == "/api/admin/delete-date":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.delete_delivery_date(str(data.get("deliveryDate") or ""), user["username"]))
                return

            if parsed.path == "/api/indian-trail/receive":
                user = self.require_permission("indian_trail_receive")
                if not user:
                    return
                if data.get("listId") and not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(STORE.receive_indian_trail_scan(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/assign":
                user = self.require_permission("assign_bay")
                if not user:
                    return
                self.send_json(STORE.assign_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/move":
                user = self.require_permission("move_bay")
                if not user:
                    return
                self.send_json(STORE.move_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.clear_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear-assignment":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.clear_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/restore-assignment":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.restore_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-status":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.set_bay_status(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/scan-out":
                user = self.require_permission("clear_bay")
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

            if parsed.path == "/api/indian-trail/mark-sdi":
                user = self.require_permission("mark_sdi")
                if not user:
                    return
                self.send_json(STORE.mark_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/remove-sdi":
                user = self.require_permission("remove_sdi")
                if not user:
                    return
                self.send_json(STORE.remove_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-check":
                user = self.require_permission("bay_check")
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

            if parsed.path == "/api/racks/move-item":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.move_rack_item(data, user["username"]))
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
    tz = ZoneInfo("America/New_York")
    while True:
        now = datetime.now(tz)
        next_run = now.replace(hour=17, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        time.sleep(max((next_run - now).total_seconds(), 1))
        try:
            date_from = (datetime.now(tz).date() - timedelta(days=7)).isoformat()
            result = STORE.import_delivery_folder({"user": "daily-auto-import", "dateFrom": date_from, "dateTo": ""})
            print(f"Daily 5 PM ET delivery-list import complete: {result.get('scannedFiles', 0)} files checked")
        except Exception as exc:
            print(f"Daily 5 PM ET delivery-list import failed: {exc}")


def start_daily_import_scheduler() -> None:
    thread = threading.Thread(target=daily_import_loop, name="daily-delivery-list-import", daemon=True)
    thread.start()


def main() -> int:
    STORE.initialize()
    start_daily_import_scheduler()
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), Handler)
    print(f"Delivery List Scanner running at http://{CONFIG.host}:{CONFIG.port}/")
    print(f"Database type: {CONFIG.database_type}")
    print(f"Database: {CONFIG.database_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
