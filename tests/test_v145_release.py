from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_release_markers_are_v147() -> None:
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert "20260728-v147" in index
    assert "bay-scanner-v147.css" in index
    assert "bay-scanner-v144.css" not in index
    assert "Current maintained release: **v147**" in readme
    assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")


def test_route_pulse_precedes_scan_command() -> None:
    soup = BeautifulSoup(read("index.html"), "html.parser")
    panel = soup.select_one(".bay-scanner-panel-v147")
    assert panel is not None
    route = panel.select_one(".bay-route-pulse-v147")
    form = panel.select_one("#bayScanOutForm")
    assert route is not None and form is not None
    descendants = list(panel.descendants)
    assert descendants.index(route) < descendants.index(form)


def test_existing_bay_scanner_controls_are_preserved_once() -> None:
    soup = BeautifulSoup(read("index.html"), "html.parser")
    required_ids = {
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
    ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
    counts = Counter(ids)
    for element_id in required_ids:
        assert counts[element_id] == 1, element_id
    assert not [value for value, count in counts.items() if count > 1]


def test_v147_markup_drops_old_layout_owners() -> None:
    index = read("index.html")
    section = index.split('class="bay-scanner-sticky-slot', 1)[1].split(
        '<section class="bay-detail-panel', 1
    )[0]
    for old_class in (
        "bay-scanner-panel-v144",
        "bay-scanner-panel-v137",
        "bay-scan-command-form-v137",
        "bay-scan-mode-card-v137",
        "bay-target-row-v137",
        "bay-scan-input-row-v137",
    ):
        assert old_class not in section
    assert "bay-scanner-panel-v147" in section
    assert "bay-action-buttons-v147" in index


def test_css_owns_flush_header_stable_command_and_sticky_offset() -> None:
    css = read("bay-scanner-v147.css")
    assert re.search(
        r"\.bay-scanner-panel-v147\s*\{[^}]*padding:\s*0\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.bay-scanner-header-v147\s*\{[^}]*border-radius:\s*17px 17px 0 0\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.bay-scan-command-v147\s*\{[^}]*display:\s*flex\s*!important[^}]*flex-direction:\s*column\s*!important",
        css,
        flags=re.S,
    )
    assert "top: 8px !important" in css
    assert "top: 8px !important" in css
    assert ".bay-action-buttons-v147" in css
    assert "prefers-reduced-motion: reduce" in css
    assert css.count("{") == css.count("}")


def test_release_notes_document_feedback_corrections() -> None:
    notes = read("docs/V145_BAY_SCANNER_LAYOUT_CORRECTION.md")
    for phrase in (
        "Route Pulse",
        "rounded top corners",
        "narrow implicit columns",
        "sticks at 60 pixels",
        "five-button toolbar",
        "No API routes",
    ):
        assert phrase in notes
