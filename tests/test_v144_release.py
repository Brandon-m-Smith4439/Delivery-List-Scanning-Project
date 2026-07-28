"""Release-contract tests for the v144 Bay Scanner operations console."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
CSS = ROOT / "bay-scanner-v144.css"
README = ROOT / "README.md"
CHANGELOG = ROOT / "README_CHANGELOG.md"
DOC = ROOT / "docs" / "V144_BAY_SCANNER_CONSOLE_REDESIGN.md"
OBSOLETE_DOC = ROOT / "docs" / "V144_BOTTOM_DOCKED_BAY_SCANNER.md"

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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_release_markers_and_cache_keys_are_v144() -> None:
    index = read(INDEX)
    readme = read(README)
    changelog = read(CHANGELOG)

    assert "Current maintained release: **v147**" in readme
    assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")
    assert "20260727-v143" not in index
    markers = re.findall(r"2026\d{4}-v(\d+)", index)
    assert markers
    assert set(markers) == {"144"}
    assert 'href="bay-scanner-v144.css?v=20260727-v144"' in index


def test_scanner_markup_is_compact_and_preserves_every_control_id_once() -> None:
    index = read(INDEX)
    ids = re.findall(r'\bid="([^"]+)"', index)

    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    assert duplicates == []
    assert all(ids.count(value) == 1 for value in REQUIRED_IDS)

    required_classes = (
        "bay-scanner-panel-v144",
        "bay-scanner-command-v144",
        "bay-mode-segment-v144",
        "bay-target-command-v144",
        "bay-scan-core-v144",
        "bay-route-status-v144",
        "bay-scan-history-v144",
    )
    assert all(value in index for value in required_classes)


def test_scan_command_keeps_primary_controls_together() -> None:
    index = read(INDEX)
    command_start = index.index('<section class="bay-scanner-command-v144"')
    command_end = index.index('<details class="bay-manual-disclosure', command_start)
    command = index[command_start:command_end]

    assert command.index('id="bayScanRemoveMode"') < command.index('id="bayScanBayInput"')
    assert command.index('id="bayScanBayInput"') < command.index('id="bayScanOutInput"')
    assert command.index('id="bayScanOutInput"') < command.index('id="bayUndoBtn"')
    assert command.index('id="bayUndoBtn"') < command.index('id="bayRedoBtn"')


def test_stylesheet_is_scoped_balanced_and_motion_accessible() -> None:
    css = read(CSS)

    assert css.count("{") == css.count("}")
    assert ".bay-scanner-panel-v144" in css
    assert "bayScannerEnterV144" in css
    assert "bayScannerReadyPulseV144" in css
    assert "bayScannerProgressSheenV144" in css
    assert "@media (min-width: 941px) and (max-height: 900px)" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr)) !important" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert re.search(r"(?m)^\s*button\s*\{", css) is None
    assert re.search(r"(?m)^\s*body\s*\{", css) is None
    assert ".app button" not in css


def test_release_notes_preserve_backend_and_remove_the_abandoned_draft() -> None:
    notes = read(DOC)

    assert "No API routes, database schema, scan logic, permissions, event handlers" in notes
    assert "prefers-reduced-motion" in notes
    assert "v144 classes" in notes
    assert not OBSOLETE_DOC.exists()
