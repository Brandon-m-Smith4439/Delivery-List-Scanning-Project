#!/usr/bin/env python3
"""Validate an installed Delivery List Scanner v146 Bay Scanner release."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REQUIRED_IDS = {
    "bayScanOutForm",
    "bayScanRemoveMode",
    "bayScanModeToggle",
    "bayScannerModeSummary",
    "bayScannerTargetState",
    "bayScanBayInput",
    "bayTargetClearBtn",
    "bayScanOutInput",
    "bayUndoBtn",
    "bayRedoBtn",
    "bayManualOrderInput",
    "bayManualItemInput",
    "bayManualQtyInput",
    "bayManualSubmitBtn",
    "bayPanelRouteMini",
    "bayScanOutStatus",
    "bayAllScansBtn",
    "bayLastCard",
    "bayLastBay",
    "bayLastTitle",
    "bayLastAction",
    "bayLastOrder",
    "bayLastTime",
    "bayLastMoveSelect",
    "bayRecentScanCountLabel",
    "bayScanOutRecent",
}

REMOVED_COPY = (
    "Current bay is found automatically in Remove mode.",
    "Current bay is found automatically.",
    "Remove mode finds the current bay automatically.",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    paths = {
        "index": root / "index.html",
        "app": root / "app.js",
        "css": root / "bay-scanner-v146.css",
        "readme": root / "README.md",
        "changelog": root / "README_CHANGELOG.md",
        "doc": root / "docs" / "V146_BAY_SCANNER_WORKFLOW_REFINEMENT.md",
        "test": root / "tests" / "test_v146_release.py",
    }
    for label, path in paths.items():
        if not path.is_file():
            failures.append(f"Missing {label}: {path}")
    if failures:
        return failures

    index = read(paths["index"])
    app = read(paths["app"])
    css = read(paths["css"])
    readme = read(paths["readme"])
    changelog = read(paths["changelog"])

    checks = {
        "v146 cache key": "20260728-v146" in index,
        "v146 stylesheet link": "bay-scanner-v146.css" in index,
        "old scanner stylesheet removed": not re.search(r"bay-scanner-v(?:144|145)\.css", index),
        "v146 scanner marker": "bay-scanner-panel-v146" in index,
        "v146 action toolbar": "bay-action-buttons-v146" in index,
        "combined route header": 'class="bay-route-pulse-v146"' in index,
        "correct Remove copy": "Finds the piece's current bay" in index,
        "empty target-state markup": '<small id="bayScannerTargetState"></small>' in index,
        "no barcode submit label": "Submit Scan" not in index,
        "manual three-digit limit": 'maxlength="3"' in index and 'pattern="[0-9]{1,3}"' in index,
        "v146 README marker": "Current maintained release: **v146**" in readme,
        "v146 changelog marker": changelog.startswith("## v146 - Bay Scanner Workflow Refinement"),
        "balanced CSS": css.count("{") == css.count("}"),
        "route width containment": ".bay-route-metrics-v146" in css and "max-width: 100% !important" in css,
        "overlay correction controls": ".bay-command-history-overlay-v146" in css and "top: -15px !important" in css,
        "one-row manual layout": "grid-template-columns: minmax(150px, 1fr) 78px 92px !important" in css,
        "reduced motion": "prefers-reduced-motion: reduce" in css,
        "no removed submit style": ".bay-scan-submit-v146" not in css,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(name)

    for sentence in REMOVED_COPY:
        if sentence in index or sentence in app:
            failures.append(f"Removed copy remains: {sentence}")

    ids = re.findall(r'\bid="([^"]+)"', index)
    counts = Counter(ids)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    if duplicates:
        failures.append("Duplicate IDs: " + ", ".join(duplicates[:12]))
    missing_ids = sorted(value for value in REQUIRED_IDS if counts[value] != 1)
    if missing_ids:
        failures.append("Missing/duplicate Bay Scanner IDs: " + ", ".join(missing_ids))

    panel_start = index.find('class="scanner-panel bay-scanner-panel bay-scanner-panel-v146"')
    panel_end = index.find('<section class="bay-detail-panel', panel_start)
    panel = index[panel_start:panel_end]
    header_start = panel.find('<header class="bay-scanner-header-v146">')
    route_start = panel.find('<section class="bay-route-pulse-v146"')
    header_close = panel.find('</header>\n\n                <form', header_start)
    form_start = panel.find('id="bayScanOutForm"')
    if min(panel_start, panel_end, header_start, route_start, header_close, form_start) < 0 or not (
        header_start < route_start < header_close < form_start
    ):
        failures.append("Route Pulse is not nested inside the combined header")

    scan_start = panel.find('class="bay-command-scan-input-v146"')
    scan_end = panel.find('</span>\n                      </div>', scan_start)
    scan_surface = panel[scan_start:scan_end]
    if 'id="bayUndoBtn"' not in scan_surface or 'id="bayRedoBtn"' not in scan_surface:
        failures.append("Undo/Redo are not inside the scan input surface")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()
    failures = validate(root)
    if failures:
        print("v146 validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("v146 Bay Scanner validation passed.")
    print(f"Project: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
