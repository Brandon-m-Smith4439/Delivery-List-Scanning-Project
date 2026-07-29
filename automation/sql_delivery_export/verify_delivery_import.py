#!/usr/bin/env python3
# File: automation/sql_delivery_export/verify_delivery_import.py
"""Verify that one generated workbook has all expected scanner stage lists.

This helper is read-only with respect to delivery-list data. It loads the same
workbook parser and stage builder used by the maintained importer, then confirms
that every expected list id exists in the configured scanner store.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify one SQL-generated delivery-list import.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--delivery-date", required=True)
    return parser.parse_args()


def row_value(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    try:
        return row[name]
    except (KeyError, TypeError, IndexError):
        return None


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    workbook = Path(args.workbook).expanduser().resolve()
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project root not found: {project_root}")
    if not workbook.is_file():
        raise FileNotFoundError(f"Generated workbook not found: {workbook}")

    sys.path.insert(0, str(project_root))
    from backend.config import load_config
    from backend.store import build_delivery_lists, create_store, load_delivery_source_payload

    payload = load_delivery_source_payload(workbook)
    config = load_config(project_root)
    store = create_store(config)
    store.initialize()
    routed_payload = store.apply_customer_route_rules_to_payload(payload)
    definitions = build_delivery_lists(routed_payload)
    expected_ids = sorted({str(row[0]).strip() for row in definitions if row and str(row[0]).strip()})
    if not expected_ids:
        raise RuntimeError("The workbook produced no expected scanner stage lists.")

    current_rows = store.get_delivery_lists() or []
    current_ids = {
        str(row_value(row, "id") or "").strip()
        for row in current_rows
        if str(row_value(row, "id") or "").strip()
    }
    missing_ids = sorted(set(expected_ids).difference(current_ids))

    result = {
        "ok": not missing_ids,
        "deliveryDate": args.delivery_date,
        "workbook": str(workbook),
        "expectedListCount": len(expected_ids),
        "existingExpectedListCount": len(expected_ids) - len(missing_ids),
        "expectedListIds": expected_ids,
        "missingListIds": missing_ids,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if missing_ids:
        raise RuntimeError(
            "The scanner import is incomplete. Missing expected stage list ids: "
            + ", ".join(missing_ids)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
