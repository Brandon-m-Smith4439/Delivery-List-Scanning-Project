#!/usr/bin/env python3
"""Validate an installed Delivery List Scanner v148 Bay Scanner release."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from pathlib import Path

REQUIRED_IDS = {
    "bayScanOutForm", "bayScanRemoveMode", "bayScanModeToggle", "bayScannerModeSummary",
    "bayScannerTargetState", "bayScanBayInput", "bayTargetClearBtn", "bayScanOutInput",
    "bayUndoBtn", "bayRedoBtn", "bayManualOrderInput", "bayManualItemInput",
    "bayManualQtyInput", "bayManualSubmitBtn", "bayPanelRouteMini", "bayScanOutStatus",
    "bayAllScansBtn", "bayLastCard", "bayLastBay", "bayLastTitle", "bayLastAction",
    "bayLastOrder", "bayLastTime", "bayLastMoveSelect", "bayRecentScanCountLabel",
    "bayScanOutRecent",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    paths = {
        "index": root / "index.html",
        "app": root / "app.js",
        "store": root / "delivery_store.py",
        "css": root / "bay-scanner-v148.css",
        "readme": root / "README.md",
        "changelog": root / "README_CHANGELOG.md",
        "doc": root / "docs" / "V148_BAY_SCANNER_HISTORY_AND_FLOW_REFINEMENT.md",
        "test": root / "tests" / "test_v148_release.py",
    }
    for label, path in paths.items():
        if not path.is_file():
            failures.append(f"Missing {label}: {path}")
    if failures:
        return failures

    index = read(paths["index"])
    app = read(paths["app"])
    store = read(paths["store"])
    css = read(paths["css"])
    readme = read(paths["readme"])
    changelog = read(paths["changelog"])

    checks = {
        "v148 cache key": "20260728-v148" in index,
        "v148 stylesheet": "bay-scanner-v148.css" in index,
        "old scanner stylesheet removed": not re.search(r"bay-scanner-v(?:144|145|146|147)\.css", index),
        "v148 scanner owner": "bay-scanner-panel-v148" in index,
        "v148 action owner": "bay-action-buttons-v148" in index,
        "hidden title status": 'id="bayScanOutStatus" hidden' in index and "Just now" not in index,
        "permanently open recent history": 'class="bay-recent-panel-v148"' in index and '<details class="bay-recent' not in index,
        "four recent columns": all(f"<th>{label}</th>" in index for label in ("Order Nr.", "Job Nr.", "Action", "Current Bay")),
        "compact renderer": "DLS_V148_COMPACT_BAY_RECENT_HISTORY" in app,
        "renderer job": "event.job" in app,
        "renderer move selector": "bayEventMoveControlHtml(event)" in app,
        "history store filter": "DLS_V148_BAY_SCAN_HISTORY_FILTER" in store,
        "item-linked events only": "WHERE COALESCE(be.line_item_id, '') <> ''" in store,
        "store job field": "li.product, li.job" in store and '"job": row["job"] or ""' in store,
        "README marker": "Current maintained release: **v148**" in readme,
        "changelog marker": changelog.startswith("## v148 - Bay Scanner History and Flow Refinement"),
        "CSS balanced": css.count("{") == css.count("}"),
        "right rail top aligned": ".bay-right-rail:has(.bay-scanner-sticky-slot-v148)" in css and "justify-content: flex-start !important" in css,
        "toolbar static": ".bay-action-buttons-v148" in css and "position: static !important" in css,
        "scanner sticky": ".bay-scanner-sticky-slot-v148" in css and "top: 8px !important" in css,
        "remove percentages hidden": ":has(#bayScanRemoveMode:checked) .bay-route-metrics-v148 .bay-dual-progress-label" in css,
        "recent no scroll": ".bay-recent-table-wrap-v148" in css and "max-height: none !important" in css and "overflow: visible !important" in css,
        "fixed recent table": "table-layout: fixed !important" in css,
        "no old recent disclosure CSS": ".bay-recent-disclosure-v148" not in css,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(name)

    try:
        ast.parse(store)
    except SyntaxError as exc:
        failures.append(f"delivery_store.py syntax: {exc}")

    ids = re.findall(r'\bid="([^"]+)"', index)
    counts = Counter(ids)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    if duplicates:
        failures.append("Duplicate IDs: " + ", ".join(duplicates[:12]))
    missing = sorted(value for value in REQUIRED_IDS if counts[value] != 1)
    if missing:
        failures.append("Missing/duplicate Bay Scanner IDs: " + ", ".join(missing))

    toolbar = index.find('id="bayActionButtons"')
    sticky = index.find('class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v148"')
    if toolbar < 0 or sticky < 0 or toolbar >= sticky:
        failures.append("Action toolbar must remain before and outside the sticky scanner")

    structural = ("UpdateBayLayout", "CreateBay", "DeleteBay", "DeleteBayGroup")
    if not all(event_type in store for event_type in structural):
        failures.append("Structural event exclusion list is incomplete")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()
    failures = validate(root)
    if failures:
        print("v148 validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("v148 Bay Scanner validation passed.")
    print(f"Project: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
