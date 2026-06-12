#!/usr/bin/env python
"""Repeatable workflow validation for the delivery-list scanner pilot."""

from __future__ import annotations

import json
import gc
import os
import sqlite3
import sys
import time
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from delivery_store import create_store, is_cpu_item  # noqa: E402
from scanner_config import load_config  # noqa: E402


def assert_true(name: str, condition: bool, details: dict | None = None) -> dict:
    if not condition:
        raise AssertionError(f"{name} failed: {details or {}}")
    return {"test": name, "ok": True, **(details or {})}


def main() -> int:
    validation_db = ROOT / "_verification" / f"validation-workflows-{os.getpid()}.db"
    validation_db.parent.mkdir(exist_ok=True)
    cleanup_db(validation_db)

    config = replace(load_config(ROOT), database_path=validation_db)
    store = create_store(config)
    store.initialize()

    results = []
    lists = store.get_delivery_lists()
    results.append(assert_true("delivery_list_count", len(lists) == 4, {"count": len(lists)}))

    customer = store.get_delivery_list("2026-04-01-customer-pickup")
    customer_items = customer["items"]
    customer_qty = sum(int(item["qty"]) for item in customer_items)
    results.append(
        assert_true(
            "customer_pickup_cpu_filter",
            len(customer_items) == 7 and customer_qty == 9 and all(is_cpu_item(item) for item in customer_items),
            {"items": len(customer_items), "qty": customer_qty},
        )
    )

    list_id = "2026-04-01-staging-airport"
    store.reset_stage(list_id, "Validator", "Test Bench")

    exact = store.record_scan({"listId": list_id, "barcode": "T200231887001000", "user": "Validator", "station": "Test Bench"})
    results.append(assert_true("good_exact_scan", exact["lastScan"]["ok"], {"order": exact["lastScan"]["item"]["order"]}))

    damaged = store.record_scan({"listId": list_id, "barcode": "TDEXRTY887001000", "user": "Validator", "station": "Test Bench"})
    results.append(assert_true("damaged_scan_recovery", damaged["lastScan"]["ok"], {"message": damaged["lastScan"]["message"]}))

    duplicate = store.record_scan({"listId": list_id, "barcode": "T200231887001000", "user": "Validator", "station": "Test Bench"})
    results.append(
        assert_true(
            "duplicate_after_complete_rejects",
            duplicate["lastScan"]["eventType"] == "duplicate" and not duplicate["lastScan"]["ok"],
            {"message": duplicate["lastScan"]["message"]},
        )
    )

    unknown = store.record_scan({"listId": list_id, "barcode": "BADSCAN-DOES-NOT-MATCH", "user": "Validator", "station": "Test Bench"})
    results.append(
        assert_true(
            "bad_scan_rejects",
            unknown["lastScan"]["eventType"] == "error" and unknown["lastScan"]["reason"] == "No unique delivery-list match",
            {"reason": unknown["lastScan"]["reason"]},
        )
    )

    ambiguous = store.record_scan({"listId": list_id, "barcode": "T200231704001000", "user": "Validator", "station": "Test Bench"})
    results.append(
        assert_true(
            "ambiguous_scan_rejects",
            ambiguous["lastScan"]["eventType"] == "error" and ambiguous["lastScan"]["reason"] == "Ambiguous delivery-list match",
            {"reason": ambiguous["lastScan"]["reason"]},
        )
    )

    undone = store.undo_last_scan(list_id, "Validator", "Test Bench")
    scanned_qty = sum(int(item["scanned"]) for item in undone["items"])
    results.append(assert_true("undo_last_scan", undone["lastScan"]["eventType"] == "undo" and scanned_qty == 1, {"scannedQty": scanned_qty}))

    station_result = store.add_station("Validation Bench")
    results.append(assert_true("station_add", "Validation Bench" in station_result["stations"], {"stations": station_result["stations"]}))

    outbound_id = "2026-04-01-outbound-airport"
    store.reset_stage(list_id, "Validator", "Test Bench")
    store.reset_stage(outbound_id, "Validator", "Test Bench")
    outbound_scan = store.record_scan({"listId": outbound_id, "barcode": "T200231887001000", "user": "Validator", "station": "Outbound Bench"})
    staging_after = store.get_delivery_list(list_id)
    staged_item = next(item for item in staging_after["items"] if item["order"] == "231887" and item["item"] == "001")
    outbound_notices = [entry for entry in outbound_scan["recent"] if entry["eventType"] == "notice"]
    results.append(
        assert_true(
            "outbound_auto_stages_missing_staging_scan",
            outbound_scan["lastScan"]["ok"] and int(staged_item["scanned"]) == 1 and outbound_notices,
            {"stagedScanned": staged_item["scanned"], "notice": outbound_notices[0]["message"] if outbound_notices else ""},
        )
    )

    exceptions = store.get_exceptions({"listId": list_id})
    results.append(assert_true("exceptions_logged", len(exceptions) >= 2, {"count": len(exceptions)}))

    csv_text = store.export_csv(list_id)
    results.append(assert_true("csv_export", len(csv_text.splitlines()) == 106, {"lineCount": len(csv_text.splitlines())}))

    sample = json.loads((ROOT / "data" / "sample-delivery-list.json").read_text(encoding="utf-8"))
    sample["deliveryDate"] = "2026-04-02"
    imported = store.import_delivery_list({"payload": sample, "user": "Validator", "fileName": "sample-delivery-list.json"})
    results.append(assert_true("import_update", imported["importedCount"] == 4, {"importedCount": imported["importedCount"]}))

    print(json.dumps({"ok": True, "results": results}, indent=2))

    with sqlite3.connect(validation_db) as con:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    del store
    gc.collect()
    time.sleep(0.5)
    cleanup_db(validation_db)
    return 0


def cleanup_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(path) + suffix)
        if not target.exists():
            continue
        try:
            target.unlink()
        except PermissionError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
