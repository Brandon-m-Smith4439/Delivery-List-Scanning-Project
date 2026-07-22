from __future__ import annotations

from pathlib import Path
import unittest

from database_contract import INDEX_DESCRIPTIONS, TABLE_DESCRIPTIONS, TEXT_BUSINESS_IDENTIFIERS
from migrate_sqlite_to_azure_sql import APPEND_ONLY_TRIGGERS, normalized_value, rows_checksum


ROOT = Path(__file__).resolve().parents[1]


class DatabaseIntegrityAndAzureTests(unittest.TestCase):
    def test_checksum_is_deterministic_and_order_independent(self) -> None:
        columns = ["id", "order_no", "item_no"]
        first = [(1, "235000", "001"), (2, "235000", "002")]
        second = list(reversed(first))
        self.assertEqual(rows_checksum(columns, first), rows_checksum(columns, second))
        self.assertNotEqual(rows_checksum(columns, first), rows_checksum(columns, [(1, "235000", "001")]))

    def test_azure_checksum_normalizes_timestamps_and_numeric_values(self) -> None:
        self.assertEqual(normalized_value("2026-07-21T12:00:00+00:00"), "2026-07-21T12:00:00")
        self.assertEqual(normalized_value(1.0), "1")
        self.assertEqual(set(APPEND_ONLY_TRIGGERS), {"scan_events", "audit_events", "machine_events"})

    def test_azure_schema_contains_v097_contract_and_sql_server_types(self) -> None:
        schema = (ROOT / "azure_sql_schema.sql").read_text(encoding="utf-8").lower()
        for table in ("schema_migrations", "machines", "scanners", "machine_events"):
            self.assertIn(f"dbo.{table}", schema)
        self.assertIn("datetime2(0)", schema)
        self.assertIn("isjson(metadata_json)", schema)
        self.assertIn("ck_line_items_qty", schema)
        self.assertIn("idx_machine_events_order_item", schema)
        self.assertIn("trg_scan_events_append_only", schema)
        self.assertIn("trg_audit_events_append_only", schema)
        self.assertIn("trg_machine_events_append_only", schema)

    def test_business_identifiers_remain_text_in_both_schemas(self) -> None:
        sqlite_source = (ROOT / "delivery_store.py").read_text(encoding="utf-8")
        azure_source = (ROOT / "azure_sql_schema.sql").read_text(encoding="utf-8").lower()
        self.assertIn("order_no TEXT NOT NULL", sqlite_source)
        self.assertIn("item_no TEXT NOT NULL", sqlite_source)
        self.assertIn("barcode TEXT NOT NULL", sqlite_source)
        self.assertIn("order_no nvarchar", azure_source)
        self.assertIn("item_no nvarchar", azure_source)
        self.assertIn("barcode nvarchar", azure_source)
        self.assertGreaterEqual(TEXT_BUSINESS_IDENTIFIERS["line_items"], {"order_no", "item_no", "barcode"})

    def test_every_documented_index_and_table_has_a_contract_entry(self) -> None:
        self.assertGreaterEqual(len(TABLE_DESCRIPTIONS), 35)
        self.assertGreaterEqual(len(INDEX_DESCRIPTIONS), 17)
        schema_doc = (ROOT / "docs" / "DATABASE_SCHEMA.md").read_text(encoding="utf-8").lower()
        sqlite_source = (ROOT / "delivery_store.py").read_text(encoding="utf-8").lower()
        azure_source = (ROOT / "azure_sql_schema.sql").read_text(encoding="utf-8").lower()
        for table in TABLE_DESCRIPTIONS:
            self.assertIn(f"`{table}`", schema_doc)
            self.assertIn(f"dbo.{table}", azure_source)
        for index in INDEX_DESCRIPTIONS:
            self.assertIn(index.lower(), sqlite_source)
            self.assertIn(index.lower(), azure_source)


if __name__ == "__main__":
    unittest.main()
