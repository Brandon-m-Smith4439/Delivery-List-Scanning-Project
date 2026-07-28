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
    panel = soup.select_one(".bay-scanner-panel-v148")
    assert panel is not None
    return soup, panel


def test_release_markers_are_v148() -> None:
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert "20260728-v148" in index
    assert "bay-scanner-v148.css" in index
    assert not re.search(r"bay-scanner-v(?:144|145|146)\.css", index)
    assert "Current maintained release: **v148**" in readme
    assert changelog.startswith("## v148 - Bay Scanner History and Flow Refinement")


def test_header_contains_only_title_status_and_route_pulse() -> None:
    _, panel = scanner_panel()
    header = panel.select_one(":scope > .bay-scanner-header-v148")
    route = panel.select_one(".bay-route-pulse-v148")
    form = panel.select_one("#bayScanOutForm")
    assert header is not None and route is not None and form is not None
    assert route in header.descendants
    assert route not in form.descendants
    visible_text = header.get_text(" ", strip=True)
    assert "Indian Trail receiving" not in visible_text
    assert "Choose the action, confirm the bay, and scan the piece." not in visible_text
    assert "Current mode" not in visible_text
    mode_summary = panel.select_one(".bay-scanner-mode-summary-v148")
    assert mode_summary is not None and mode_summary.has_attr("hidden")


def test_route_pulse_removes_legacy_connector_and_white_pill() -> None:
    css = read("bay-scanner-v148.css")
    assert "contain: layout paint" in css
    assert ".bay-route-metrics-v148 .bay-panel-route-lane::before" in css
    assert ".bay-route-metrics-v148 .bay-panel-route-lane::after" in css
    assert ".bay-route-metrics-v148 .bay-panel-route-lane > span::before" in css
    assert "content: none !important" in css
    assert "background: rgba(3, 23, 55, 0.38) !important" in css
    assert re.search(
        r"\.bay-panel-route-lane > span\s*\{[^}]*background:\s*transparent\s*!important[^}]*box-shadow:\s*none\s*!important",
        css,
        flags=re.S,
    )


def test_destination_control_is_mode_specific() -> None:
    _, panel = scanner_panel()
    target = panel.select_one(".bay-command-target-v148")
    assert target is not None
    assert target.select_one("#bayScanBayInput") is not None
    css = read("bay-scanner-v148.css")
    assert ".bay-scanner-panel-v148:has(#bayScanRemoveMode:checked) .bay-command-target-v148" in css
    assert ".bay-scanner-panel-v148:has(#bayScanModeToggle:checked) .bay-command-target-v148" in css
    assert re.search(
        r":has\(#bayScanRemoveMode:checked\) \.bay-command-target-v148\s*\{[^}]*display:\s*none\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r":has\(#bayScanModeToggle:checked\) \.bay-command-target-v148\s*\{[^}]*display:\s*grid\s*!important",
        css,
        flags=re.S,
    )


def test_only_scanner_slot_is_sticky_and_moves_to_top() -> None:
    soup, panel = scanner_panel()
    action_toolbar = soup.select_one("#bayActionButtons")
    sticky_slot = panel.find_parent(class_="bay-scanner-sticky-slot-v148")
    assert action_toolbar is not None and sticky_slot is not None
    assert action_toolbar not in sticky_slot.descendants
    css = read("bay-scanner-v148.css")
    assert re.search(
        r"\.bay-scanner-sticky-slot-v148\s*\{[^}]*position:\s*sticky\s*!important[^}]*top:\s*8px\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.bay-action-buttons-v148\s*\{[^}]*position:\s*static\s*!important[^}]*top:\s*auto\s*!important",
        css,
        flags=re.S,
    )
    assert "top: 68px !important" not in css
    assert "top: 60px !important" not in css


def test_barcode_and_manual_workflows_remain_intact() -> None:
    _, panel = scanner_panel()
    scan_surface = panel.select_one(".bay-command-scan-input-v148")
    assert scan_surface is not None
    assert scan_surface.select_one("#bayScanOutInput") is not None
    assert scan_surface.select_one("#bayUndoBtn") is not None
    assert scan_surface.select_one("#bayRedoBtn") is not None
    assert panel.find(string=lambda value: value and "Submit Scan" in value) is None
    manual = panel.select_one(".bay-manual-inline-v148")
    assert manual is not None
    assert manual.select_one("#bayManualOrderInput") is not None
    item_input = manual.select_one("#bayManualItemInput")
    assert item_input is not None
    assert item_input.get("maxlength") == "3"
    assert item_input.get("pattern") == "[0-9]{1,3}"
    assert manual.select_one("#bayManualSubmitBtn") is not None


def test_existing_bay_scanner_controls_are_preserved_once() -> None:
    soup, _ = scanner_panel()
    required_ids = {
        "bayScanOutForm", "bayScanRemoveMode", "bayScanModeToggle", "bayScannerModeSummary",
        "bayScannerTargetState", "bayScanBayInput", "bayTargetClearBtn", "bayScanOutInput",
        "bayUndoBtn", "bayRedoBtn", "bayManualOrderInput", "bayManualItemInput",
        "bayManualQtyInput", "bayManualSubmitBtn", "bayPanelRouteMini", "bayScanOutStatus",
        "bayAllScansBtn", "bayLastCard", "bayLastBay", "bayLastTitle", "bayLastAction",
        "bayLastOrder", "bayLastTime", "bayLastMoveSelect", "bayRecentScanCountLabel",
        "bayScanOutRecent",
    }
    ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
    counts = Counter(ids)
    for element_id in required_ids:
        assert counts[element_id] == 1, element_id
    assert not [value for value, count in counts.items() if count > 1]


def test_css_is_balanced_scoped_and_reduced_motion_safe() -> None:
    css = read("bay-scanner-v148.css")
    assert css.count("{") == css.count("}")
    assert ".bay-scanner-panel-v148" in css
    assert ".bay-action-buttons-v148" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".bay-scan-submit-v148" not in css
