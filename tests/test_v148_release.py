from __future__ import annotations

from collections import Counter
from pathlib import Path
import ast
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
    assert not re.search(r"bay-scanner-v(?:144|145|146|147)\.css", index)
    assert "Current maintained release: **v148**" in readme
    assert changelog.startswith("## v148 - Bay Scanner History and Flow Refinement")


def test_action_toolbar_is_adjacent_but_not_sticky() -> None:
    soup, panel = scanner_panel()
    toolbar = soup.select_one("#bayActionButtons")
    sticky = panel.find_parent(class_="bay-scanner-sticky-slot-v148")
    assert toolbar is not None and sticky is not None
    assert toolbar not in sticky.descendants
    css = read("bay-scanner-v148.css")
    assert re.search(
        r"\.bay-right-rail:has\(\.bay-scanner-sticky-slot-v148\)\s*\{[^}]*display:\s*flex\s*!important[^}]*justify-content:\s*flex-start\s*!important[^}]*gap:\s*0\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.bay-action-buttons-v148\s*\{[^}]*position:\s*static\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.bay-scanner-sticky-slot-v148\s*\{[^}]*position:\s*sticky\s*!important[^}]*top:\s*8px\s*!important[^}]*margin:\s*0\s*!important",
        css,
        flags=re.S,
    )


def test_title_status_is_hidden_and_remove_hides_percentages() -> None:
    _, panel = scanner_panel()
    status = panel.select_one("#bayScanOutStatus")
    assert status is not None and status.has_attr("hidden")
    assert "Just now" not in panel.get_text(" ", strip=True)
    css = read("bay-scanner-v148.css")
    assert re.search(
        r"\.bay-scanner-live-status-v148\s*\{[^}]*display:\s*none\s*!important",
        css,
        flags=re.S,
    )
    assert re.search(
        r":has\(#bayScanRemoveMode:checked\) \.bay-route-metrics-v148 \.bay-dual-progress-label\s*\{[^}]*display:\s*none\s*!important",
        css,
        flags=re.S,
    )


def test_recent_scans_are_permanently_open_and_compact() -> None:
    _, panel = scanner_panel()
    recent = panel.select_one(".bay-recent-panel-v148")
    assert recent is not None and recent.name == "section"
    assert panel.select_one("details.bay-recent-disclosure-v148") is None
    headers = [cell.get_text(" ", strip=True) for cell in recent.select("thead th")]
    assert headers == ["Order Nr.", "Job Nr.", "Action", "Current Bay"]
    css = read("bay-scanner-v148.css")
    assert re.search(
        r"\.bay-recent-table-wrap-v148\s*\{[^}]*max-height:\s*none\s*!important[^}]*overflow:\s*visible\s*!important",
        css,
        flags=re.S,
    )
    assert "table-layout: fixed !important" in css
    assert ".bay-recent-disclosure-v148" not in css


def test_recent_renderer_uses_job_and_existing_move_dropdown() -> None:
    app = read("app.js")
    assert "DLS_V148_COMPACT_BAY_RECENT_HISTORY" in app
    assert "events.slice(0, 2)" in app
    assert "event.job" in app
    assert "bayEventMoveControlHtml(event)" in app
    assert 'data-label="Current Bay"' in app
    assert 'colspan="4"' in app
    assert "Time</th>" not in read("index.html").split('class="bay-recent-panel-v148"', 1)[1].split("</section>", 1)[0]


def test_bay_history_filters_layout_edits_and_includes_job() -> None:
    store = read("delivery_store.py")
    ast.parse(store)
    assert "DLS_V148_BAY_SCAN_HISTORY_FILTER" in store
    assert "WHERE COALESCE(be.line_item_id, '') <> ''" in store
    assert "li.product, li.job" in store
    assert '"job": row["job"] or ""' in store
    for event_type in ("UpdateBayLayout", "CreateBay", "DeleteBay", "DeleteBayGroup"):
        assert event_type in store
    assert re.search(
        r"def insert_bay_event\([\s\S]*?if not str\(line_item_id or \"\"\)\.strip\(\) or clean_event_type in \{[\s\S]*?return[\s\S]*?INSERT INTO bay_events",
        store,
    )


def test_required_bay_scanner_ids_remain_unique() -> None:
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


def test_css_is_balanced_and_release_is_code_only() -> None:
    css = read("bay-scanner-v148.css")
    assert css.count("{") == css.count("}")
    assert "prefers-reduced-motion: reduce" in css
    assert not list(ROOT.rglob("*.png"))
