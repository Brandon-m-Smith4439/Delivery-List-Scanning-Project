from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def scanner_panel():
    soup = BeautifulSoup(read("index.html"), "html.parser")
    panel = soup.select_one(".bay-scanner-panel-v146")
    assert panel is not None
    return soup, panel


def test_release_markers_are_v146() -> None:
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert "20260728-v146" in index
    assert "bay-scanner-v146.css" in index
    assert "bay-scanner-v145.css" not in index
    assert "Current maintained release: **v146**" in readme
    assert changelog.startswith("## v146 - Bay Scanner Workflow Refinement")


def test_title_and_route_are_one_header() -> None:
    _, panel = scanner_panel()
    header = panel.select_one(":scope > .bay-scanner-header-v146")
    route = panel.select_one(".bay-route-pulse-v146")
    form = panel.select_one("#bayScanOutForm")
    assert header is not None and route is not None and form is not None
    assert route in header.descendants
    assert route not in form.descendants


def test_route_pulse_is_contained_by_css() -> None:
    css = read("bay-scanner-v146.css")
    assert re.search(
        r"\.bay-route-pulse-v146\s*\{[^}]*width:\s*100%\s*!important[^}]*max-width:\s*100%\s*!important[^}]*overflow:\s*hidden\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.bay-route-metrics-v146\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*0\.82fr\)\s+minmax\(0,\s*1\.3fr\)\s+minmax\(0,\s*0\.82fr\)",
        css,
        flags=re.S,
    )


def test_barcode_scan_uses_enter_and_overlay_corrections() -> None:
    _, panel = scanner_panel()
    scan_surface = panel.select_one(".bay-command-scan-input-v146")
    assert scan_surface is not None
    assert scan_surface.select_one("#bayScanOutInput") is not None
    assert scan_surface.select_one("#bayUndoBtn") is not None
    assert scan_surface.select_one("#bayRedoBtn") is not None
    assert panel.find(string=lambda value: value and "Submit Scan" in value) is None
    assert panel.select_one(".bay-scan-submit-v146") is None


def test_manual_scan_is_one_row_with_compact_item() -> None:
    _, panel = scanner_panel()
    manual = panel.select_one(".bay-manual-inline-v146")
    assert manual is not None
    assert manual.name == "section"
    assert panel.select_one(".bay-manual-disclosure-v145") is None
    order_input = manual.select_one("#bayManualOrderInput")
    item_input = manual.select_one("#bayManualItemInput")
    submit = manual.select_one("#bayManualSubmitBtn")
    assert order_input is not None and item_input is not None and submit is not None
    assert item_input.get("maxlength") == "3"
    assert item_input.get("pattern") == "[0-9]{1,3}"
    css = read("bay-scanner-v146.css")
    assert "grid-template-columns: minmax(150px, 1fr) 78px 92px !important" in css


def test_requested_copy_is_exact_and_removed_copy_is_absent() -> None:
    index = read("index.html")
    app = read("app.js")
    assert "Finds the piece's current bay" in index
    for sentence in (
        "Current bay is found automatically in Remove mode.",
        "Current bay is found automatically.",
        "Remove mode finds the current bay automatically.",
    ):
        assert sentence not in index
        assert sentence not in app
    assert '<small id="bayScannerTargetState"></small>' in index


def test_existing_bay_scanner_controls_are_preserved_once() -> None:
    soup, _ = scanner_panel()
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


def test_css_is_balanced_scoped_and_reduced_motion_safe() -> None:
    css = read("bay-scanner-v146.css")
    assert css.count("{") == css.count("}")
    assert ".bay-scanner-panel-v146" in css
    assert ".bay-action-buttons-v146" in css
    assert ".bay-command-history-overlay-v146" in css
    assert "top: -15px !important" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".bay-scan-submit-v146" not in css
