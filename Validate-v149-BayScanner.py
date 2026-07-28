#!/usr/bin/env python3
"""Validate the installed v149 Bay Scanner release."""

from __future__ import annotations

import argparse
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
    "bayLastOrder", "bayLastTime", "bayLastCheck", "bayLastMoveSelect",
    "bayRecentScanCountLabel", "bayScanOutRecent",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    paths = {
        "index": root / "index.html",
        "app": root / "app.js",
        "store": root / "delivery_store.py",
        "css": root / "bay-scanner-v149.css",
        "readme": root / "README.md",
        "changelog": root / "README_CHANGELOG.md",
        "doc": root / "docs" / "V149_BAY_SCANNER_STICKY_FIT_AND_INPUT_REFINEMENT.md",
        "test": root / "tests" / "test_v149_release.py",
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
        "v149 cache key": "20260728-v149" in index,
        "v149 stylesheet": "bay-scanner-v149.css" in index,
        "old scanner stylesheet removed": not re.search(r"bay-scanner-v(?:144|145|146|147|148)\.css", index),
        "v149 scanner owner": "bay-scanner-panel-v149" in index,
        "v149 action owner": "bay-action-buttons-v149" in index,
        "single recent label": 'id="bayRecentScanCountLabel">Latest 1' in index,
        "latest Check": 'id="bayLastCheck"' in index,
        "recent Check": "<th>Check</th>" in index,
        "condensed target": 'class="bay-command-target-v149"' in index and "bay-command-target-copy-v149" not in index,
        "condensed manual": 'class="bay-manual-inline-v149"' in index and 'maxlength="3"' in index,
        "shared submit": 'class="tool-button primary-tool bay-manual-submit-v149"' in index,
        "icon-only corrections": "<small>Undo</small>" not in index and "<small>Redo</small>" not in index,
        "single-row renderer": "DLS_V149_SINGLE_BAY_RECENT_HISTORY" in app and "events.slice(0, 1)" in app,
        "last Check renderer": "DLS_V149_LAST_BAY_CHECK_FEEDBACK" in app,
        "Check feedback helper": "function bayScanCheckFeedbackV149(event)" in app,
        "history filter retained": "DLS_V148_BAY_SCAN_HISTORY_FILTER" in store,
        "README marker": "Current maintained release: **v149**" in readme,
        "changelog marker": changelog.startswith("## v149 - Bay Scanner Sticky Fit and Input Refinement"),
        "CSS balanced": css.count("{") == css.count("}"),
        "toolbar static": ".bay-action-buttons-v149" in css and "position: static !important" in css,
        "five-pixel sticky": ".bay-scanner-sticky-slot-v149" in css and "top: 5px !important" in css,
        "viewport fit": "height: calc(100dvh - 10px) !important" in css and "max-height: calc(100dvh - 10px) !important" in css,
        "fullscreen fit": "body:has(:fullscreen) .bay-scanner-sticky-slot-v149" in css,
        "recent no scroll": ".bay-recent-table-wrap-v149" in css and "max-height: none !important" in css and "overflow: visible !important" in css,
        "Check styles": ".bay-scan-check-v149.is-success" in css and ".bay-scan-check-v149.is-error" in css,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(name)

    ids = re.findall(r'\bid="([^"]+)"', index)
    counts = Counter(ids)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    if duplicates:
        failures.append("Duplicate IDs: " + ", ".join(duplicates[:12]))
    missing = sorted(value for value in REQUIRED_IDS if counts[value] != 1)
    if missing:
        failures.append("Missing/duplicate Bay Scanner IDs: " + ", ".join(missing))

    toolbar = index.find('id="bayActionButtons"')
    sticky = index.find('class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v149"')
    if toolbar < 0 or sticky < 0 or toolbar >= sticky:
        failures.append("Action toolbar must remain before and outside the sticky scanner")

    if "events.slice(0, 2)" in app:
        failures.append("Old two-row recent history limit remains")
    if (root / "v149_payload").is_dir() and list((root / "v149_payload").rglob("*.png")):
        failures.append("PNG files were found in the v149 payload")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()
    failures = validate(root)
    if failures:
        print("v149 validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("v149 Bay Scanner validation passed.")
    print(f"Project: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
