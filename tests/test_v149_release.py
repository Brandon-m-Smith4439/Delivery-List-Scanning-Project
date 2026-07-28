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
    panel = soup.select_one(".bay-scanner-panel-v149")
    assert panel is not None
    return soup, panel


def test_release_markers_are_v149() -> None:
    index = read("index.html")
    assert "20260728-v149" in index
    assert "bay-scanner-v149.css" in index
    assert not re.search(r"bay-scanner-v(?:144|145|146|147|148)\.css", index)
    assert "Current maintained release: **v149**" in read("README.md")
    assert read("README_CHANGELOG.md").startswith("## v149 - Bay Scanner Sticky Fit and Input Refinement")


def test_toolbar_stays_outside_sticky_panel_and_gap_is_closed() -> None:
    soup, panel = scanner_panel()
    toolbar = soup.select_one("#bayActionButtons")
    sticky = panel.find_parent(class_="bay-scanner-sticky-slot-v149")
    assert toolbar is not None and sticky is not None
    assert toolbar not in sticky.descendants
    assert toolbar.find_next_sibling() == sticky
    css = read("bay-scanner-v149.css")
    assert re.search(
        r"\.bay-right-rail:has\(\.bay-scanner-sticky-slot-v149\)\s*\{[^}]*justify-content:\s*flex-start\s*!important[^}]*gap:\s*4px\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(r"\.bay-action-buttons-v149\s*\{[^}]*position:\s*static\s*!important", css, flags=re.S)


def test_sticky_panel_has_five_pixel_viewport_margins_in_fullscreen_too() -> None:
    css = read("bay-scanner-v149.css")
    assert re.search(
        r"\.bay-scanner-sticky-slot-v149\s*\{[^}]*position:\s*sticky\s*!important[^}]*top:\s*5px\s*!important[^}]*height:\s*calc\(100dvh - 10px\)\s*!important[^}]*max-height:\s*calc\(100dvh - 10px\)\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"body:has\(:fullscreen\) \.bay-scanner-sticky-slot-v149\s*\{[^}]*top:\s*5px\s*!important[^}]*height:\s*calc\(100dvh - 10px\)\s*!important",
        css,
        flags=re.S,
    )


def test_destination_and_manual_controls_are_condensed() -> None:
    _, panel = scanner_panel()
    target = panel.select_one(".bay-command-target-v149")
    assert target is not None
    assert target.select_one(".bay-command-target-copy-v149") is None
    assert target.select_one(".bay-command-target-controls-v149") is None
    assert target.select_one("#bayScanBayInput") is not None
    clear = target.select_one("#bayTargetClearBtn.tool-button")
    assert clear is not None

    manual = panel.select_one(".bay-manual-inline-v149")
    assert manual is not None
    assert manual.select_one("#bayManualOrderInput") is not None
    item = manual.select_one("#bayManualItemInput")
    assert item is not None and item.get("maxlength") == "3"
    submit = manual.select_one("#bayManualSubmitBtn.tool-button.primary-tool")
    assert submit is not None


def test_undo_and_redo_are_icon_only_accessible_buttons() -> None:
    _, panel = scanner_panel()
    undo = panel.select_one("#bayUndoBtn")
    redo = panel.select_one("#bayRedoBtn")
    assert undo is not None and redo is not None
    assert undo.get("aria-label") == "Undo last bay action"
    assert redo.get("aria-label") == "Redo last bay action"
    assert undo.select_one(".undo-icon") is not None
    assert redo.select_one(".redo-icon") is not None
    assert undo.select_one("small") is None
    assert redo.select_one("small") is None
    assert undo.select_one(".sr-only").get_text(strip=True) == "Undo"
    assert redo.select_one(".sr-only").get_text(strip=True) == "Redo"


def test_last_and_recent_scan_restore_check_feedback() -> None:
    _, panel = scanner_panel()
    assert panel.select_one("#bayLastCheck.bay-scan-check-v149") is not None
    headers = [cell.get_text(" ", strip=True) for cell in panel.select(".bay-recent-panel-v149 thead th")]
    assert headers == ["Order Nr.", "Job Nr.", "Action", "Current Bay", "Check"]
    app = read("app.js")
    assert "DLS_V149_LAST_BAY_CHECK_FEEDBACK" in app
    assert "function bayScanCheckFeedbackV149(event)" in app
    assert 'data-label="Check"' in app
    assert "is-${check.key}" in app


def test_recent_scans_are_limited_to_one_non_scrollable_row() -> None:
    _, panel = scanner_panel()
    recent = panel.select_one(".bay-recent-panel-v149")
    assert recent is not None and recent.name == "section"
    assert panel.select_one("details.bay-recent-disclosure-v149") is None
    assert panel.select_one("#bayRecentScanCountLabel").get_text(strip=True) == "Latest 1"
    app = read("app.js")
    assert "DLS_V149_SINGLE_BAY_RECENT_HISTORY" in app
    assert "events.slice(0, 1)" in app
    assert "events.slice(0, 2)" not in app
    assert 'colspan="5"' in app
    css = read("bay-scanner-v149.css")
    assert re.search(
        r"\.bay-recent-table-wrap-v149\s*\{[^}]*max-height:\s*none\s*!important[^}]*overflow:\s*visible\s*!important",
        css,
        flags=re.S,
    )
    assert "table-layout: fixed !important" in css


def test_required_ids_are_unique_and_release_is_code_only() -> None:
    soup, _ = scanner_panel()
    required = {
        "bayScanOutForm", "bayScanRemoveMode", "bayScanModeToggle", "bayScannerModeSummary",
        "bayScannerTargetState", "bayScanBayInput", "bayTargetClearBtn", "bayScanOutInput",
        "bayUndoBtn", "bayRedoBtn", "bayManualOrderInput", "bayManualItemInput",
        "bayManualQtyInput", "bayManualSubmitBtn", "bayPanelRouteMini", "bayScanOutStatus",
        "bayAllScansBtn", "bayLastCard", "bayLastBay", "bayLastTitle", "bayLastAction",
        "bayLastOrder", "bayLastTime", "bayLastCheck", "bayLastMoveSelect",
        "bayRecentScanCountLabel", "bayScanOutRecent",
    }
    ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
    counts = Counter(ids)
    for element_id in required:
        assert counts[element_id] == 1, element_id
    assert not [value for value, count in counts.items() if count > 1]
    css = read("bay-scanner-v149.css")
    assert css.count("{") == css.count("}")
    assert "prefers-reduced-motion: reduce" in css
    assert not list((ROOT / "v149_payload").rglob("*.png"))
