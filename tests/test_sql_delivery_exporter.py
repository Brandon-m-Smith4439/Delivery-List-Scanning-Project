"""Regression tests for the v115 SQL delivery-list workbook builder."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "automation" / "sql_delivery_export" / "build_delivery_workbook.py"
SPEC = importlib.util.spec_from_file_location("build_delivery_workbook", BUILDER_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class DeliveryListSqlExporterTests(unittest.TestCase):
    """Protect dimension conversion and the scanner's legacy workbook columns."""

    def test_dimension_conversion_uses_configurable_reduced_fractions(self) -> None:
        self.assertEqual(builder.format_dimension_units(960, 32), '30"')
        self.assertEqual(builder.format_dimension_units(1156, 32), '36 1/8"')
        self.assertEqual(builder.format_dimension_units(2042, 32), '63 13/16"')
        self.assertEqual(builder.format_dimension_units(892, 32), '27 7/8"')
        self.assertEqual(builder.format_dimensions(960, 2368, 32), '30" x 74"')
        self.assertEqual(builder.format_dimension_units(20, 16), '1 1/4"')

    def test_generated_workbook_uses_existing_scanner_columns(self) -> None:
        payload = {
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
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Delivery List 07-15-2026.xlsx"
            builder.write_workbook(payload, path, "2026-07-15")
            result = builder.validate_workbook(path)
            self.assertEqual(result["dataRows"], 2)
            self.assertEqual(result["formatVersion"], "v115-ooxml-1")
            cells = builder.workbook_cells(path)

            data_rows = []
            row_numbers = sorted(
                {
                    int("".join(character for character in reference if character.isdigit()))
                    for reference in cells
                    if any(character.isdigit() for character in reference)
                }
            )
            for row_number in row_numbers:
                values = [cells.get(f"{column}{row_number}", "") for column in ("F", "G", "J")]
                if all(value.isdigit() for value in values):
                    data_rows.append(row_number)
            self.assertEqual(len(data_rows), 2)

            first = data_rows[0]
            self.assertEqual(cells[f"A{first}"], "87697297M.2 REDHAWK WALK 176")
            self.assertEqual(cells[f"F{first}"], "236067")
            self.assertEqual(cells[f"G{first}"], "1")
            self.assertEqual(cells[f"J{first}"], "1")
            self.assertEqual(cells[f"L{first}"], '58" x 42"')
            self.assertEqual(cells[f"N{first}"], "LENNAR HOMES")
            self.assertEqual(cells[f"V{first}"], "RM")

            second = data_rows[1]
            self.assertEqual(cells[f"A{second}"], "88915190. Add It. Duke 7726")
            self.assertEqual(cells[f"X{second}"], "DTC")
            self.assertEqual(cells[f"L{second}"], '30" x 74"')

            with zipfile.ZipFile(path) as archive:
                worksheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                self.assertTrue(worksheet.tag.endswith("worksheet"))
                child_names = [child.tag.rsplit("}", 1)[-1] for child in list(worksheet)]
                self.assertLess(child_names.index("sheetPr"), child_names.index("dimension"))
                self.assertLess(child_names.index("sheetData"), child_names.index("pageMargins"))

    def test_validator_rejects_excel_incompatible_worksheet_order(self) -> None:
        payload = {
            "dimensionUnitsPerInch": 32,
            "rows": [
                {
                    "product": '3/8" Clear Tempered',
                    "job": "JOB",
                    "order": 1,
                    "item": 1,
                    "quantity": 1,
                    "widthUnits": 960,
                    "heightUnits": 2368,
                    "customer": "Customer",
                    "remake": "",
                    "route": "DTC",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_path = Path(temp_dir) / "valid.xlsx"
            invalid_path = Path(temp_dir) / "invalid.xlsx"
            builder.write_workbook(payload, valid_path, "2026-07-28")
            with zipfile.ZipFile(valid_path) as source, zipfile.ZipFile(invalid_path, "w", zipfile.ZIP_DEFLATED) as target:
                for name in source.namelist():
                    content = source.read(name)
                    if name == "xl/worksheets/sheet1.xml":
                        text = content.decode("utf-8")
                        sheet_pr = '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>'
                        text = text.replace(f"  {sheet_pr}\n", "")
                        text = text.replace("</worksheet>", f"  {sheet_pr}\n</worksheet>")
                        content = text.encode("utf-8")
                    target.writestr(name, content)
            with self.assertRaisesRegex(ValueError, "out of SpreadsheetML order"):
                builder.validate_workbook(invalid_path)

    def test_command_line_build_and_validate(self) -> None:
        payload = {
            "dimensionUnitsPerInch": 32,
            "rows": [
                {
                    "product": '1/8" Clear Annealed',
                    "job": "88624098M.2 STEPHENS FARM 12",
                    "order": 236069,
                    "item": 1,
                    "quantity": 1,
                    "widthUnits": 262,
                    "heightUnits": 1220,
                    "customer": "CLASSICA HOMES",
                    "remake": "RM",
                    "route": "",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "payload.json"
            output_path = Path(temp_dir) / "output.xlsx"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            build = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER_PATH),
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--delivery-date",
                    "2026-07-15",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            validate = subprocess.run(
                [sys.executable, str(BUILDER_PATH), "--validate", str(output_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validate.returncode, 0, validate.stderr)
            self.assertEqual(json.loads(validate.stdout)["dataRows"], 1)

    def test_builder_self_test(self) -> None:
        result = subprocess.run(
            [sys.executable, str(BUILDER_PATH), "--self-test"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("self-test passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
