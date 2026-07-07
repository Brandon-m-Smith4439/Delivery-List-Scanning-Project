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

from delivery_store import create_store, is_cpu_item, load_delivery_source_payload, route_category  # noqa: E402
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
    results.append(assert_true("delivery_list_count", len(lists) == 6, {"count": len(lists)}))

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
    indian_trail = store.get_delivery_list("2026-04-01-inbound-indian-trail")
    greenville = store.get_delivery_list("2026-04-01-bfs-greenville")
    dtc = store.get_delivery_list("2026-04-01-dtc")
    results.append(
        assert_true(
            "route_stage_filters",
            indian_trail["items"]
            and greenville["items"]
            and dtc["items"]
            and all(route_category(item) == "indian_trail" for item in indian_trail["items"])
            and all(route_category(item) == "greenville" for item in greenville["items"])
            and all(route_category(item) == "dtc" for item in dtc["items"]),
            {"indianTrail": len(indian_trail["items"]), "greenville": len(greenville["items"]), "dtc": len(dtc["items"])},
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

    store.reset_stage(list_id, "Validator", "Test Bench")
    store.reset_stage(outbound_id, "Validator", "Test Bench")
    rack_barcode_item = "T200231715002000"
    store.clear_rack({"rackCode": "R1S"}, "Validator")
    store.record_scan({"listId": list_id, "barcode": rack_barcode_item, "rackCode": "R1S", "user": "Validator", "station": "Staging Bench"})
    store.record_scan({"listId": list_id, "barcode": rack_barcode_item, "rackCode": "R1S", "user": "Validator", "station": "Staging Bench"})
    store.complete_rack({"rackCode": "R1S"}, "Validator")
    rack_packing = store.rack_packing_list("R1S", "2026-04-01")
    rack_barcode = rack_packing["rack"]["barcode"]
    first_rack_scan = store.record_scan({"listId": outbound_id, "barcode": rack_barcode, "user": "Validator", "station": "Outbound Bench"})
    outbound_after_first = store.get_delivery_list(outbound_id)
    outbound_rack_item = next(item for item in outbound_after_first["items"] if item["order"] == "231715" and item["item"] == "002")
    with sqlite3.connect(validation_db) as con:
        first_delta = con.execute(
            """
            SELECT qty_delta
            FROM scan_events
            WHERE list_id = ? AND line_item_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (outbound_id, outbound_rack_item["id"]),
        ).fetchone()[0]
    results.append(
        assert_true(
            "rack_packing_barcode_uses_rack_qty",
            first_rack_scan["lastScan"]["ok"] and int(outbound_rack_item["scanned"]) == 2 and int(first_delta) == 2,
            {"scanned": outbound_rack_item["scanned"], "eventQtyDelta": first_delta, "message": first_rack_scan["message"]},
        )
    )

    second_rack_scan = store.record_scan({"listId": outbound_id, "barcode": rack_barcode, "user": "Validator", "station": "Outbound Bench"})
    outbound_after_second = store.get_delivery_list(outbound_id)
    capped_item = next(item for item in outbound_after_second["items"] if item["order"] == "231715" and item["item"] == "002")
    with sqlite3.connect(validation_db) as con:
        second_delta = con.execute(
            """
            SELECT qty_delta
            FROM scan_events
            WHERE list_id = ? AND line_item_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (outbound_id, capped_item["id"]),
        ).fetchone()[0]
    results.append(
        assert_true(
            "rack_packing_barcode_caps_at_remaining_qty",
            second_rack_scan["lastScan"]["ok"]
            and int(capped_item["scanned"]) == int(capped_item["qty"]) == 3
            and int(second_delta) == 1
            and "capped" in second_rack_scan["message"].lower(),
            {"scanned": capped_item["scanned"], "qty": capped_item["qty"], "eventQtyDelta": second_delta, "message": second_rack_scan["message"]},
        )
    )

    third_rack_scan = store.record_scan({"listId": outbound_id, "barcode": rack_barcode, "user": "Validator", "station": "Outbound Bench"})
    over_scan_check = store.get_delivery_list(outbound_id)
    complete_item = next(item for item in over_scan_check["items"] if item["order"] == "231715" and item["item"] == "002")
    results.append(
        assert_true(
            "rack_packing_barcode_rejects_over_scan",
            third_rack_scan["lastScan"]["eventType"] == "duplicate" and int(complete_item["scanned"]) == int(complete_item["qty"]) == 3,
            {"eventType": third_rack_scan["lastScan"]["eventType"], "scanned": complete_item["scanned"], "qty": complete_item["qty"]},
        )
    )

    exceptions = store.get_exceptions({"listId": list_id})
    results.append(assert_true("exceptions_logged", len(exceptions) >= 2, {"count": len(exceptions)}))

    csv_text = store.export_csv(list_id)
    results.append(assert_true("csv_export", len(csv_text.splitlines()) == 106, {"lineCount": len(csv_text.splitlines())}))

    sample = json.loads((ROOT / "data" / "sample-delivery-list.json").read_text(encoding="utf-8"))
    sample["deliveryDate"] = "2026-04-02"
    imported = store.import_delivery_list({"payload": sample, "user": "Validator", "fileName": "sample-delivery-list.json"})
    results.append(
        assert_true(
            "new_import_not_marked_updated",
            imported["importedCount"] == 6 and imported["updatedCount"] == 0,
            {"importedCount": imported["importedCount"], "updatedCount": imported["updatedCount"]},
        )
    )
    unchanged_reimport = store.import_delivery_list({"payload": sample, "user": "Validator", "fileName": "sample-delivery-list.json"})
    results.append(
        assert_true(
            "unchanged_reimport_not_marked_updated",
            unchanged_reimport["updatedCount"] == 0 and not unchanged_reimport["changedListIds"],
            {"updatedCount": unchanged_reimport["updatedCount"], "changedListIds": unchanged_reimport["changedListIds"]},
        )
    )
    shifted_sample = json.loads(json.dumps(sample))
    shifted_sample["deliveryDate"] = "2026-04-03"
    first_shift_import = store.import_delivery_list({"payload": shifted_sample, "user": "Validator", "fileName": "sample-delivery-list.json"})
    shifted_sample["items"].insert(
        0,
        {
            "id": "validation-new-row-001",
            "barcode": "T200999991001000",
            "order": "999991",
            "item": "001",
            "qty": 2,
            "scanned": 0,
            "dimensions": '40" x 40"',
            "customer": "VALIDATION CUSTOMER",
            "route": "",
            "job": "99999999 VALIDATION",
            "product": '3/8" Clear Tempered',
            "processState": "",
            "queueState": "",
        },
    )
    shifted_reimport = store.import_delivery_list({"payload": shifted_sample, "user": "Validator", "fileName": "sample-delivery-list.json"})
    shifted_staging = next(row for row in shifted_reimport["stageSummaries"] if row["listId"] == "2026-04-03-staging-airport")
    results.append(
        assert_true(
            "row_position_shift_only_marks_inserted_lines_new",
            first_shift_import["createdCount"] == 6
            and shifted_reimport["updatedCount"] >= 1
            and shifted_staging["newPieceQty"] == 2
            and shifted_staging["changedLineCount"] == 1,
            {
                "createdCount": first_shift_import["createdCount"],
                "updatedCount": shifted_reimport["updatedCount"],
                "stagingNewPieceQty": shifted_staging["newPieceQty"],
                "stagingChangedLineCount": shifted_staging["changedLineCount"],
            },
        )
    )
    initial_lookups = store.get_manual_edit_lookups()
    results.append(
        assert_true(
            "manual_edit_lookups_include_discovered_products",
            any(item["value"] for item in initial_lookups["products"]) and any("Mirror" in item["value"] for item in initial_lookups["products"]),
            {"products": len(initial_lookups["products"])},
        )
    )
    store.add_manual_edit_lookup({"type": "product", "value": "Validation Glass", "label": "Validation Glass"}, "Validator")
    store.add_manual_edit_lookup({"type": "route", "value": "VAL", "label": "Validation Route", "category": "Test", "matchTerms": "validation route"}, "Validator")
    lookups = store.add_manual_edit_lookup({"type": "process", "value": "Validation Process", "label": "Validation Process"}, "Validator")
    results.append(
        assert_true(
            "manual_edit_lookups_include_admin_added_values",
            any(item["value"] == "Validation Glass" for item in lookups["products"])
            and any(item["value"] == "VAL" for item in lookups["routes"])
            and any(item["value"] == "Validation Process" for item in lookups["processes"]),
            {"products": len(lookups["products"]), "routes": len(lookups["routes"]), "processes": len(lookups["processes"])},
        )
    )

    temp_source = ROOT.parent / "Temp Delivery Lists" / "6.9.26.xlsx"
    if temp_source.exists():
        parsed_payload = load_delivery_source_payload(temp_source)
        parsed_preview = store.preview_import(parsed_payload)
        results.append(
            assert_true(
                "temp_delivery_xlsx_parser",
                parsed_payload["deliveryDate"] == "2026-06-09" and parsed_preview["valid"] and parsed_preview["rowCount"] >= 50,
                {"deliveryDate": parsed_payload["deliveryDate"], "rows": parsed_preview["rowCount"]},
            )
        )

    folder_result = store.import_delivery_folder({"user": "Validator"})
    changed_files = len(folder_result["importedFiles"]) + len(folder_result["updatedFiles"])
    results.append(
        assert_true(
            "temp_folder_import_update",
            not folder_result["failedFiles"] and (changed_files >= 1 or folder_result["skippedFiles"]),
            {"changed": changed_files, "printCandidates": len(folder_result["printCandidates"])},
        )
    )
    if folder_result["printCandidates"]:
        print_package = store.get_print_package(folder_result["printCandidates"][0]["listIds"])
        results.append(
            assert_true(
                "print_package_excludes_regular_mirrors",
                bool(print_package["lists"]) and all(item for delivery_list in print_package["lists"] for item in delivery_list["items"]),
                {"lists": len(print_package["lists"])},
            )
        )
    second_folder_result = store.import_delivery_folder({"user": "Validator"})
    results.append(
        assert_true(
            "temp_folder_second_run_skips_unchanged",
            len(second_folder_result["skippedFiles"]) >= len(folder_result["importedFiles"]) + len(folder_result["updatedFiles"]),
            {"skipped": len(second_folder_result["skippedFiles"])},
        )
    )

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
