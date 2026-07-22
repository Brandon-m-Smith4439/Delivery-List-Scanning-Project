from dataclasses import replace
from pathlib import Path
import unittest
import uuid

from delivery_store import SQLiteDeliveryStore
from scanner_config import load_config


ROOT = Path(__file__).resolve().parents[1]


class ManualEditPaginationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = ROOT / "_verification" / "unit-tests" / f"manual-edit-{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        base = load_config(ROOT)
        config = replace(
            base,
            database_path=self.tmp_path / "scanner.db",
            environment="production",
            sample_path=self.tmp_path / "no-sample.json",
        )
        self.store = SQLiteDeliveryStore(config)
        self.store.initialize()
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO delivery_lists (id,label,delivery_date,stage,scanner,status,revision,created_at) "
                "VALUES ('list-1','Pagination Test','2026-07-22','Staging - Airport Rd','Airport Rd','active',1,'2026-07-22T12:00:00+00:00')"
            )
            for index in range(45):
                connection.execute(
                    """
                    INSERT INTO line_items (
                        id,list_id,source_id,barcode,order_no,item_no,qty,scanned_qty,customer,job,product
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        f"item-{index:03d}",
                        "list-1",
                        f"source-{index:03d}",
                        f"T200235{index:03d}001000",
                        f"235{index:03d}",
                        "001",
                        1,
                        0,
                        f"Customer {index:03d}",
                        f"JOB-{index:04d}",
                        "3/8 Clear Tempered",
                    ),
                )
            connection.commit()

    def test_twenty_row_pages_reach_every_item_without_duplicates(self) -> None:
        first = self.store.admin_search_line_items("", "list-1", 20, 0)
        second = self.store.admin_search_line_items("", "list-1", 20, 20)
        third = self.store.admin_search_line_items("", "list-1", 20, 40)

        self.assertEqual(first["total"], 45)
        self.assertEqual([len(first["results"]), len(second["results"]), len(third["results"])], [20, 20, 5])
        ids = [row["lineItemId"] for page in (first, second, third) for row in page["results"]]
        self.assertEqual(len(ids), 45)
        self.assertEqual(len(set(ids)), 45)

    def test_job_and_partial_order_queries_filter_predictively(self) -> None:
        job_match = self.store.admin_search_line_items("JOB-0044", "list-1", 20, 0)
        order_matches = self.store.admin_search_line_items("23500", "list-1", 20, 0)

        self.assertEqual(job_match["total"], 1)
        self.assertEqual(job_match["results"][0]["job"], "JOB-0044")
        self.assertGreater(order_matches["total"], 1)
        self.assertTrue(all("23500" in row["order"] for row in order_matches["results"]))


if __name__ == "__main__":
    unittest.main()
