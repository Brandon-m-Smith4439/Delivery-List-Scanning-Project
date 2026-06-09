#!/usr/bin/env python
"""Exercise the VBA tolerant barcode-recovery rules against an XLSM workbook.

This intentionally reads workbook XML directly so it does not depend on Excel,
openpyxl styles, or macro permissions.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {
    "r": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass(frozen=True)
class DeliveryLine:
    order: int
    item: int


def col_number(cell_ref: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_ref).group(1)
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch) - 64
    return value


def read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for si in root.findall("m:si", MAIN_NS):
        strings.append("".join(t.text or "" for t in si.findall(".//m:t", MAIN_NS)))
    return strings


def workbook_sheet_paths(workbook: zipfile.ZipFile) -> dict[str, str]:
    wb_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rel_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root}

    paths: dict[str, str] = {}
    for sheet in wb_root.find("m:sheets", MAIN_NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = rels[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        paths[name] = target
    return paths


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.find("m:v", MAIN_NS)
    if value is None:
        return ""

    raw = value.text or ""
    if cell.attrib.get("t") == "s":
        return shared_strings[int(raw)]
    return raw


def worksheet_rows(
    workbook: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]
) -> list[tuple[int, dict[int, str]]]:
    root = ET.fromstring(workbook.read(sheet_path))
    rows: list[tuple[int, dict[int, str]]] = []
    for row in root.findall(".//m:sheetData/m:row", MAIN_NS):
        row_num = int(row.attrib["r"])
        values: dict[int, str] = {}
        for cell in row.findall("m:c", MAIN_NS):
            value = cell_value(cell, shared_strings)
            if value != "":
                values[col_number(cell.attrib["r"])] = value
        rows.append((row_num, values))
    return rows


def load_delivery_lines(path: Path, sheet_name: str) -> list[DeliveryLine]:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = read_shared_strings(workbook)
        sheet_paths = workbook_sheet_paths(workbook)
        if sheet_name not in sheet_paths:
            raise SystemExit(f"Sheet not found: {sheet_name}")
        rows = worksheet_rows(workbook, sheet_paths[sheet_name], shared_strings)

    header_row = None
    order_col = None
    item_col = None
    for row_num, values in rows[:250]:
        for col, value in values.items():
            if col > 14:
                continue
            normalized = value.strip().lower()
            if normalized == "order nr.":
                header_row = row_num
                order_col = col
            elif normalized == "item nr." and header_row == row_num:
                item_col = col
        if order_col and item_col:
            break

    if not header_row or not order_col or not item_col:
        raise SystemExit("Could not find Order Nr. and Item Nr. headers.")

    lines: list[DeliveryLine] = []
    for row_num, values in rows:
        if row_num <= header_row:
            continue
        order = int(float(values.get(order_col, "0") or 0))
        item = int(float(values.get(item_col, "0") or 0))
        if order > 0 and item > 0:
            lines.append(DeliveryLine(order, item))
    return lines


def clean_barcode(value: str) -> str:
    trimmed = value.replace("*", "").replace("\r", "").replace("\n", "").strip()
    return "".join(ch for ch in trimmed if ch.isalnum()).upper()


def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def canonical(order: int, item: int) -> str:
    return f"T200{order:06d}{item:03d}000"


def has_order_item(lines: list[DeliveryLine], order: int, item: int) -> bool:
    return any(line.order == order and line.item == item for line in lines)


def find_unique_order_by_suffix_item(
    lines: list[DeliveryLine], suffix: str, item: int
) -> int | None:
    found: list[int] = []
    for line in lines:
        if line.item == item and f"{line.order:06d}".endswith(suffix):
            if line.order not in found:
                found.append(line.order)
    return found[0] if len(found) == 1 else None


def recover_scan(raw_scan: str, lines: list[DeliveryLine]) -> tuple[bool, str, str]:
    clean_text = clean_barcode(raw_scan)
    if len(clean_text) == 16 and re.fullmatch(r"T200\d{12}", clean_text):
        order = int(clean_text[4:10])
        item = int(clean_text[10:13])
        return order > 0 and item > 0, clean_text, "exact canonical format"

    numbers = digits_only(clean_text)

    for start in range(0, len(numbers) - 11):
        window = numbers[start : start + 12]
        order = int(window[:6])
        item = int(window[6:9])
        if order > 0 and item > 0 and has_order_item(lines, order, item):
            return True, canonical(order, item), "recovered exact order/item digits"

    for start in range(0, len(numbers) - 8):
        window = numbers[start : start + 9]
        suffix = window[:3]
        item = int(window[3:6])
        order = find_unique_order_by_suffix_item(lines, suffix, item)
        if item > 0 and order:
            return True, canonical(order, item), "recovered unique suffix/item match"

    return False, "", "no unique delivery-list match"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workbook",
        default="Multi User Scanner Queue Testing (version 3).xlsm",
        help="Workbook path to test.",
    )
    parser.add_argument("--sheet", default="Delivery List")
    args = parser.parse_args()

    workbook_path = Path(args.workbook).resolve()
    lines = load_delivery_lines(workbook_path, args.sheet)
    if not lines:
        raise SystemExit("No delivery-list lines found.")

    first = lines[0]
    suffix = f"{first.order:06d}"[-3:]
    examples = [
        ("Good canonical", canonical(first.order, first.item), lines),
        ("Damaged prefix", f"TDEX{first.order:06d}{first.item:03d}000", lines),
        ("Bad label with order suffix", f"TDEXRTY{suffix}{first.item:03d}000", lines),
        ("Unknown order", f"TDEX999999{first.item:03d}000", lines),
        ("Old sample not on Version 3 list", "TDEX234481001000", lines),
        (
            "Ambiguous suffix conflict",
            f"TDEXRTY{suffix}{first.item:03d}000",
            [*lines, DeliveryLine(first.order + 100000, first.item)],
        ),
    ]

    print(f"Workbook: {workbook_path.name}")
    print(f"Sheet: {args.sheet}")
    print(f"Delivery lines read: {len(lines)}")
    print(f"Primary test line: order {first.order}, item {first.item:03d}")
    print()

    failures = 0
    expected = {
        "Good canonical": True,
        "Damaged prefix": True,
        "Bad label with order suffix": True,
        "Unknown order": False,
        "Old sample not on Version 3 list": False,
        "Ambiguous suffix conflict": False,
    }

    for name, scan, data in examples:
        ok, recovered, reason = recover_scan(scan, data)
        passed = ok == expected[name]
        failures += 0 if passed else 1
        status = "PASS" if passed else "FAIL"
        result = recovered if ok else "rejected"
        print(f"{status} | {name}: {scan} -> {result} ({reason})")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
