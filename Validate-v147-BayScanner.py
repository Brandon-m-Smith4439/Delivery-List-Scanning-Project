#!/usr/bin/env python3
"""Validate an installed Delivery List Scanner v147 Bay Scanner release."""

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
    "Indian Trail receiving",
    "Choose the action, confirm the bay, and scan the piece.",
    "Current mode",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    paths = {
        "index": root / "index.html",
        "app": root / "app.js",
        "css": root / "bay-scanner-v147.css",
        "readme": root / "README.md",
        "changelog": root / "README_CHANGELOG.md",
        "doc": root / "docs" / "V147_BAY_SCANNER_CONTAINMENT_AND_STICKY_REFINEMENT.md",
        "test": root / "tests" / "test_v147_release.py",
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
        "v147 cache key": "20260728-v147" in index,
        "v147 stylesheet link": "bay-scanner-v147.css" in index,
        "old scanner stylesheet removed": not re.search(r"bay-scanner-v(?:144|145|146)\.css", index),
        "v147 scanner marker": "bay-scanner-panel-v147" in index,
        "v147 action toolbar": "bay-action-buttons-v147" in index,
        "combined route header": 'class="bay-route-pulse-v147"' in index,
        "hidden mode compatibility node": 'class="bay-scanner-mode-summary-v147" hidden' in index,
        "correct Remove copy": "Finds the piece's current bay" in index,
        "empty target-state markup": '<small id="bayScannerTargetState"></small>' in index,
        "no barcode submit label": "Submit Scan" not in index,
        "manual three-digit limit": 'maxlength="3"' in index and 'pattern="[0-9]{1,3}"' in index,
        "v147 README marker": "Current maintained release: **v147**" in readme,
        "v147 changelog marker": changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement"),
        "balanced CSS": css.count("{") == css.count("}"),
        "route paint containment": "contain: layout paint" in css,
        "legacy route connector reset": ".bay-route-metrics-v147 .bay-panel-route-lane::before" in css and "content: none !important" in css,
        "dark route surfaces": "background: rgba(3, 23, 55, 0.38) !important" in css,
        "remove hides target": ":has(#bayScanRemoveMode:checked) .bay-command-target-v147" in css,
        "add shows target": ":has(#bayScanModeToggle:checked) .bay-command-target-v147" in css,
        "scanner sticky at top": ".bay-scanner-sticky-slot-v147" in css and "top: 8px !important" in css,
        "action toolbar non-sticky": ".bay-action-buttons-v147" in css and "position: static !important" in css and "top: auto !important" in css,
        "overlay correction controls": ".bay-command-history-overlay-v147" in css and "top: -15px !important" in css,
        "one-row manual layout": "grid-template-columns: minmax(150px, 1fr) 78px 92px !important" in css,
        "reduced motion": "prefers-reduced-motion: reduce" in css,
        "no removed submit style": ".bay-scan-submit-v147" not in css,
        "old sticky offsets removed": "top: 68px !important" not in css and "top: 60px !important" not in css,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(name)

    panel_start = index.find('class="scanner-panel bay-scanner-panel bay-scanner-panel-v147"')
    panel_end = index.find('<section class="bay-detail-panel', panel_start)
    panel = index[panel_start:panel_end]

    for sentence in REMOVED_COPY[:3]:
        if sentence in index or sentence in app:
            failures.append(f"Removed guidance remains: {sentence}")
    for sentence in REMOVED_COPY[3:]:
        if sentence in panel:
            failures.append(f"Removed visible header copy remains: {sentence}")

    ids = re.findall(r'\bid="([^"]+)"', index)
    counts = Counter(ids)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    if duplicates:
        failures.append("Duplicate IDs: " + ", ".join(duplicates[:12]))
    missing_ids = sorted(value for value in REQUIRED_IDS if counts[value] != 1)
    if missing_ids:
        failures.append("Missing/duplicate Bay Scanner IDs: " + ", ".join(missing_ids))

    header_start = panel.find('<header class="bay-scanner-header-v147">')
    route_start = panel.find('<section class="bay-route-pulse-v147"')
    header_close = panel.find('</header>\n\n                <form', header_start)
    form_start = panel.find('id="bayScanOutForm"')
    if min(panel_start, panel_end, header_start, route_start, header_close, form_start) < 0 or not (
        header_start < route_start < header_close < form_start
    ):
        failures.append("Route Pulse is not nested inside the combined header")

    scan_start = panel.find('class="bay-command-scan-input-v147"')
    scan_end = panel.find('</span>\n                      </div>', scan_start)
    scan_surface = panel[scan_start:scan_end]
    if 'id="bayUndoBtn"' not in scan_surface or 'id="bayRedoBtn"' not in scan_surface:
        failures.append("Undo/Redo are not inside the scan input surface")

    action_pos = index.find('id="bayActionButtons"')
    sticky_pos = index.find('class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v147"')
    if action_pos < 0 or sticky_pos < 0 or action_pos >= sticky_pos:
        failures.append("Bay Map action buttons must remain before and outside the sticky scanner slot")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()
    failures = validate(root)
    if failures:
        print("v147 validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("v147 Bay Scanner validation passed.")
    print(f"Project: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
