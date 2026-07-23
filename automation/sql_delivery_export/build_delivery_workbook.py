#!/usr/bin/env python3
"""Build an A+W-style Delivery List workbook using only Python's standard library.

The workbook intentionally places the scanner import fields in the same columns
used by the existing A+W Crystal export:

A  Job Nr.
F  Order Nr.
G  Item Nr.
J  Qty.
L  Dimensions
N  Customer
V  Remake
X  Route

This keeps the generated XLSX compatible with the Delivery List Scanner's
existing parse_aw_delivery_workbook() function without adding a second parser.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WORKBOOK_FORMAT_VERSION = "v115-ooxml-1"


def parse_args() -> argparse.Namespace:
    """Parse workbook creation, validation, and self-test arguments."""
    parser = argparse.ArgumentParser(description="Build a Delivery List Scanner-compatible XLSX workbook.")
    parser.add_argument("--input", help="JSON payload created by the SQL exporter.")
    parser.add_argument("--output", help="XLSX file to create.")
    parser.add_argument("--delivery-date", help="Delivery date in YYYY-MM-DD format.")
    parser.add_argument("--validate", help="Validate an existing XLSX workbook.")
    parser.add_argument("--self-test", action="store_true", help="Run an isolated workbook build/validation test.")
    return parser.parse_args()


def as_decimal(value: object) -> Decimal:
    """Return a stable Decimal for a SQL numeric value."""
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def as_int(value: object) -> int:
    """Convert SQL numeric text to the nearest whole integer."""
    return int(as_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_dimension_units(value: object, units_per_inch: int = 32) -> str:
    """Format a source dimension stored in configurable whole units per inch."""
    units = max(int(units_per_inch or 32), 1)
    total_units = as_int(value)
    whole, remainder = divmod(total_units, units)
    if remainder == 0:
        return f'{whole}"'
    divisor = math.gcd(remainder, units)
    numerator = remainder // divisor
    denominator = units // divisor
    if whole:
        return f'{whole} {numerator}/{denominator}"'
    return f'{numerator}/{denominator}"'


def format_dimensions(width_units: object, height_units: object, units_per_inch: int = 32) -> str:
    """Return the Crystal-style width x height display text."""
    return f"{format_dimension_units(width_units, units_per_inch)} x {format_dimension_units(height_units, units_per_inch)}"


def display_date(value: str) -> str:
    """Convert YYYY-MM-DD to M/D/YYYY for the report title."""
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return f"{parsed.month}/{parsed.day}/{parsed.year}"


def safe_text(value: object) -> str:
    """Normalize nullable SQL strings without changing visible content."""
    return str(value or "").strip()


def xml_text(value: object) -> str:
    """Escape text for an inline-string spreadsheet cell."""
    return escape(str(value or ""), {'"': "&quot;"})


def inline_cell(reference: str, value: object, style: int = 0) -> str:
    """Create one inline-string cell so no shared-string dependency is required."""
    return (
        f'<c r="{reference}" s="{style}" t="inlineStr">'
        f'<is><t xml:space="preserve">{xml_text(value)}</t></is>'
        f"</c>"
    )


def numeric_cell(reference: str, value: object, style: int = 0) -> str:
    """Create one numeric cell using a normal OOXML value node."""
    return f'<c r="{reference}" s="{style}" t="n"><v>{as_int(value)}</v></c>'


def row_xml(row_number: int, cells: list[str], height: float | None = None) -> str:
    """Create one worksheet row."""
    attrs = [f'r="{row_number}"']
    if height is not None:
        attrs.extend([f'ht="{height}"', 'customHeight="1"'])
    return f"<row {' '.join(attrs)}>{''.join(cells)}</row>"


def normalize_rows(payload: dict) -> list[dict[str, object]]:
    """Normalize and sort database rows into deterministic report order."""
    normalized: list[dict[str, object]] = []
    units_per_inch = max(as_int(payload.get("dimensionUnitsPerInch") or 32), 1)
    for source in payload.get("rows") or []:
        quantity = max(as_int(source.get("quantity")), 0)
        normalized.append(
            {
                "product": safe_text(source.get("product")) or "Uncategorized",
                "job": safe_text(source.get("job")),
                "order": as_int(source.get("order")),
                "item": as_int(source.get("item")),
                "quantity": quantity,
                "dimensions": format_dimensions(source.get("widthUnits"), source.get("heightUnits"), units_per_inch),
                "customer": safe_text(source.get("customer")),
                "remake": safe_text(source.get("remake")),
                "route": safe_text(source.get("route")),
            }
        )
    normalized.sort(
        key=lambda row: (
            str(row["product"]).casefold(),
            str(row["job"]).casefold(),
            int(row["order"]),
            int(row["item"]),
        )
    )
    return normalized


def worksheet_xml(payload: dict, delivery_date: str) -> str:
    """Build the first worksheet with the legacy scanner-compatible column layout."""
    rows = normalize_rows(payload)
    report_rows: list[str] = []
    merges = ["D3:J3", "L3:N3"]

    report_rows.append(row_xml(1, []))
    report_rows.append(row_xml(2, []))
    report_rows.append(
        row_xml(
            3,
            [
                inline_cell("D3", "DELIVERY LIST FOR", 1),
                inline_cell("L3", display_date(delivery_date), 1),
            ],
            22,
        )
    )
    report_rows.append(row_xml(4, []))
    report_rows.append(row_xml(5, []))
    report_rows.append(
        row_xml(
            6,
            [
                inline_cell("A6", "Job Nr.", 2),
                inline_cell("F6", "Order Nr.", 2),
                inline_cell("G6", "Item Nr.", 2),
                inline_cell("J6", "Qty.", 2),
                inline_cell("L6", "Dimensions", 2),
                inline_cell("N6", "Customer", 2),
                inline_cell("V6", "Remake", 2),
                inline_cell("X6", "Route", 2),
            ],
            20,
        )
    )

    current_row = 7
    grouped: "OrderedDict[str, list[dict[str, object]]]" = OrderedDict()
    for item in rows:
        grouped.setdefault(str(item["product"]), []).append(item)

    for product, items in grouped.items():
        report_rows.append(row_xml(current_row, [inline_cell(f"A{current_row}", product, 3)], 18))
        merges.append(f"A{current_row}:X{current_row}")
        current_row += 1
        report_rows.append(row_xml(current_row, []))
        current_row += 1

        for item in items:
            report_rows.append(
                row_xml(
                    current_row,
                    [
                        inline_cell(f"A{current_row}", item["job"], 4),
                        numeric_cell(f"F{current_row}", item["order"], 4),
                        numeric_cell(f"G{current_row}", item["item"], 4),
                        numeric_cell(f"J{current_row}", item["quantity"], 4),
                        inline_cell(f"L{current_row}", item["dimensions"], 4),
                        inline_cell(f"N{current_row}", item["customer"], 4),
                        inline_cell(f"V{current_row}", item["remake"], 4),
                        inline_cell(f"X{current_row}", item["route"], 4),
                    ],
                    18,
                )
            )
            current_row += 1
            report_rows.append(row_xml(current_row, []))
            current_row += 1

    current_row += 1
    generated = datetime.now().astimezone()
    report_rows.append(
        row_xml(
            current_row,
            [
                inline_cell(f"N{current_row}", f"Generated {generated.month}/{generated.day}/{generated.year}", 5),
                inline_cell(f"P{current_row}", generated.strftime("%H:%M"), 5),
            ],
        )
    )

    merge_xml = "".join(f'<mergeCell ref="{reference}"/>' for reference in merges)
    dimension_end = max(current_row, 6)

    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">
  <sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>
  <dimension ref="A1:X{dimension_end}"/>
  <sheetViews>
    <sheetView workbookViewId="0">
      <pane ySplit="6" topLeftCell="A7" activePane="bottomLeft" state="frozen"/>
      <selection pane="bottomLeft" activeCell="A7" sqref="A7"/>
    </sheetView>
  </sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>
    <col min="1" max="1" width="40" customWidth="1"/>
    <col min="2" max="5" width="3" customWidth="1"/>
    <col min="6" max="6" width="12" customWidth="1"/>
    <col min="7" max="7" width="10" customWidth="1"/>
    <col min="8" max="9" width="3" customWidth="1"/>
    <col min="10" max="10" width="8" customWidth="1"/>
    <col min="11" max="11" width="3" customWidth="1"/>
    <col min="12" max="12" width="22" customWidth="1"/>
    <col min="13" max="13" width="3" customWidth="1"/>
    <col min="14" max="14" width="31" customWidth="1"/>
    <col min="15" max="21" width="3" customWidth="1"/>
    <col min="22" max="22" width="10" customWidth="1"/>
    <col min="23" max="23" width="3" customWidth="1"/>
    <col min="24" max="24" width="12" customWidth="1"/>
  </cols>
  <sheetData>{''.join(report_rows)}</sheetData>
  <mergeCells count="{len(merges)}">{merge_xml}</mergeCells>
  <pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0" paperSize="9"/>
</worksheet>'''


def content_types_xml() -> str:
    """Return required OOXML content type declarations."""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''


def root_relationships_xml() -> str:
    """Return package-level relationships."""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def workbook_xml() -> str:
    """Return a one-sheet workbook definition."""
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">
  <bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="12000"/></bookViews>
  <sheets><sheet name="Delivery List" sheetId="1" r:id="rId1"/></sheets>
  <calcPr calcId="191029"/>
</workbook>'''


def workbook_relationships_xml() -> str:
    """Return worksheet and style relationships."""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def styles_xml() -> str:
    """Return compact styles for title, headers, groups, data, and footer."""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="5">
    <font><sz val="11"/><name val="Calibri"/><family val="2"/><scheme val="minor"/></font>
    <font><b/><sz val="14"/><name val="Calibri"/><family val="2"/><scheme val="minor"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/><scheme val="minor"/></font>
    <font><b/><sz val="11"/><color rgb="FF072B54"/><name val="Calibri"/><family val="2"/><scheme val="minor"/></font>
    <font><i/><sz val="9"/><color rgb="FF666666"/><name val="Calibri"/><family val="2"/><scheme val="minor"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF072B54"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE8F0F8"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="3">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left/><right/><top/><bottom style="thin"><color rgb="FF7A8DA6"/></bottom><diagonal/></border>
    <border><left style="thin"><color rgb="FFD4DCE7"/></left><right style="thin"><color rgb="FFD4DCE7"/></right><top style="thin"><color rgb="FFD4DCE7"/></top><bottom style="thin"><color rgb="FFD4DCE7"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="6">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="2" borderId="2" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0"><alignment horizontal="right"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>'''


def app_properties_xml() -> str:
    """Return basic application properties."""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Delivery List SQL Exporter</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>
  <TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Delivery List</vt:lpstr></vt:vector></TitlesOfParts>
  <Company>Barefoot and Company</Company>
  <AppVersion>1.0</AppVersion>
</Properties>'''


def core_properties_xml() -> str:
    """Return document metadata with the current UTC timestamp."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Delivery List</dc:title>
  <dc:creator>Delivery List SQL Exporter</dc:creator>
  <cp:lastModifiedBy>Delivery List SQL Exporter</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>'''


def write_workbook(payload: dict, output_path: Path, delivery_date: str) -> None:
    """Write a complete XLSX package atomically."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".building")
    if temporary_path.exists():
        temporary_path.unlink()

    with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml())
        archive.writestr("_rels/.rels", root_relationships_xml())
        archive.writestr("docProps/app.xml", app_properties_xml())
        archive.writestr("docProps/core.xml", core_properties_xml())
        archive.writestr("xl/workbook.xml", workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_relationships_xml())
        archive.writestr("xl/styles.xml", styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml(payload, delivery_date))

    validate_workbook(temporary_path)
    temporary_path.replace(output_path)


def workbook_cells(path: Path) -> dict[str, str]:
    """Read non-empty inline-string and numeric cells from the first worksheet."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    namespace = {"x": MAIN_NS}
    values: dict[str, str] = {}
    for cell in root.findall(".//x:c", namespace):
        reference = cell.attrib.get("r", "")
        text = "".join(node.text or "" for node in cell.findall(".//x:t", namespace))
        if not text:
            value_node = cell.find("x:v", namespace)
            text = value_node.text if value_node is not None and value_node.text is not None else ""
        if reference and text:
            values[reference] = text
    return values


def validate_worksheet_order(root: ET.Element) -> None:
    """Enforce the child order required by Excel's worksheet schema.

    XML parsers accept elements in any order, but Microsoft Excel validates the
    SpreadsheetML sequence strictly. A misplaced ``sheetPr`` can cause Excel to
    repair the file and discard the worksheet contents even though the ZIP and
    XML are otherwise readable.
    """
    allowed_order = {
        "sheetPr": 10,
        "dimension": 20,
        "sheetViews": 30,
        "sheetFormatPr": 40,
        "cols": 50,
        "sheetData": 60,
        "sheetCalcPr": 70,
        "sheetProtection": 80,
        "protectedRanges": 90,
        "scenarios": 100,
        "autoFilter": 110,
        "sortState": 120,
        "dataConsolidate": 130,
        "customSheetViews": 140,
        "mergeCells": 150,
        "phoneticPr": 160,
        "conditionalFormatting": 170,
        "dataValidations": 180,
        "hyperlinks": 190,
        "printOptions": 200,
        "pageMargins": 210,
        "pageSetup": 220,
        "headerFooter": 230,
        "rowBreaks": 240,
        "colBreaks": 250,
        "customProperties": 260,
        "cellWatches": 270,
        "ignoredErrors": 280,
        "smartTags": 290,
        "drawing": 300,
        "legacyDrawing": 310,
        "legacyDrawingHF": 320,
        "picture": 330,
        "oleObjects": 340,
        "controls": 350,
        "webPublishItems": 360,
        "tableParts": 370,
        "extLst": 380,
    }
    previous = -1
    for child in list(root):
        local_name = child.tag.rsplit("}", 1)[-1]
        position = allowed_order.get(local_name)
        if position is None:
            continue
        if position < previous:
            raise ValueError(
                f"Worksheet element {local_name!r} is out of SpreadsheetML order."
            )
        previous = position


def validate_style_counts(root: ET.Element) -> None:
    """Confirm declared style collection counts match their actual children."""
    namespace = {"x": MAIN_NS}
    for name, child_name in (
        ("fonts", "font"),
        ("fills", "fill"),
        ("borders", "border"),
        ("cellStyleXfs", "xf"),
        ("cellXfs", "xf"),
        ("cellStyles", "cellStyle"),
    ):
        collection = root.find(f"x:{name}", namespace)
        if collection is None:
            raise ValueError(f"Workbook styles are missing {name}.")
        declared = int(collection.attrib.get("count", "0"))
        actual = len(collection.findall(f"x:{child_name}", namespace))
        if declared != actual:
            raise ValueError(
                f"Workbook styles declare {declared} {name} entries but contain {actual}."
            )


def validate_workbook(path: Path) -> dict[str, int | str]:
    """Validate the OOXML package and scanner-compatible data columns."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with zipfile.ZipFile(path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member:
            raise ValueError(f"Workbook ZIP member is corrupt: {corrupt_member}")
        required = {
            "[Content_Types].xml",
            "_rels/.rels",
            "docProps/app.xml",
            "docProps/core.xml",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
            "xl/styles.xml",
        }
        missing = required.difference(archive.namelist())
        if missing:
            raise ValueError(f"Workbook is missing required parts: {sorted(missing)}")
        for member in sorted(required):
            ET.fromstring(archive.read(member))
        worksheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        styles_root = ET.fromstring(archive.read("xl/styles.xml"))
        validate_worksheet_order(worksheet_root)
        validate_style_counts(styles_root)

        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = set()
        for relationship in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship"):
            target = str(relationship.attrib.get("Target", "")).replace("\\", "/").lstrip("/")
            if target.startswith("xl/"):
                target = target[3:]
            relationship_targets.add(target)
        if "worksheets/sheet1.xml" not in relationship_targets:
            raise ValueError("Workbook relationship to the delivery-list worksheet is missing.")
        if "styles.xml" not in relationship_targets:
            raise ValueError("Workbook relationship to styles.xml is missing.")

    cells = workbook_cells(path)
    data_rows = 0
    row_numbers = sorted({int("".join(ch for ch in ref if ch.isdigit())) for ref in cells if any(ch.isdigit() for ch in ref)})
    for row_number in row_numbers:
        numeric_values = [cells.get(f"{column}{row_number}", "").strip() for column in ("F", "G", "J")]
        try:
            [int(Decimal(value)) for value in numeric_values]
        except (InvalidOperation, ValueError):
            continue
        data_rows += 1
    if data_rows == 0:
        raise ValueError("Workbook contains no scanner-compatible delivery rows.")
    return {
        "dataRows": data_rows,
        "cellCount": len(cells),
        "formatVersion": WORKBOOK_FORMAT_VERSION,
    }


def self_test() -> None:
    """Build a known workbook and verify dimensions, columns, route, and remake markers."""
    sample = {
        "dimensionUnitsPerInch": 32,
        "rows": [
            {
                "product": '3/8" Clear Tempered',
                "job": "88915190. Add It. Duke 7726",
                "order": 235897,
                "item": 1,
                "quantity": 1,
                "widthUnits": 960,
                "heightUnits": 2368,
                "customer": "ADD IT HOME SERVICES",
                "remake": "",
                "route": "DTC",
            },
            {
                "product": '1/4" Mirror',
                "job": "87697297M.2 REDHAWK WALK 176",
                "order": 236067,
                "item": 1,
                "quantity": 1,
                "widthUnits": 1856,
                "heightUnits": 1344,
                "customer": "LENNAR HOMES",
                "remake": "RM",
                "route": "",
            },
        ]
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "self-test.xlsx"
        write_workbook(sample, output, "2026-07-15")
        result = validate_workbook(output)
        cells = workbook_cells(output)
        if result["dataRows"] != 2:
            raise AssertionError(result)
        if "30\" x 74\"" not in cells.values():
            raise AssertionError("Dimension conversion failed.")
        if "RM" not in cells.values() or "DTC" not in cells.values():
            raise AssertionError("Route/remake layout failed.")
    print("Workbook builder self-test passed.")


def main() -> int:
    """Execute the requested builder action."""
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.validate:
        result = validate_workbook(Path(args.validate))
        print(json.dumps(result, sort_keys=True))
        return 0
    if not args.input or not args.output or not args.delivery_date:
        raise ValueError("--input, --output, and --delivery-date are required when building a workbook.")
    with Path(args.input).open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    rows = payload.get("rows") or []
    if not rows:
        raise ValueError("The SQL payload contains no delivery-list rows.")
    output_path = Path(args.output)
    write_workbook(payload, output_path, args.delivery_date)
    result = validate_workbook(output_path)
    print(json.dumps({"path": str(output_path), **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Delivery workbook build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
