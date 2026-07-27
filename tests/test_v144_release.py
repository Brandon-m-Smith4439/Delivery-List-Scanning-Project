from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_release_markers_are_v144() -> None:
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert "20260727-v144" in index
    assert "Current maintained release: **v144**" in readme
    assert changelog.startswith("## v144 - Bottom-Docked Indian Trail Bay Scanner")


def test_bay_scanner_is_outside_the_former_right_rail() -> None:
    soup = BeautifulSoup(read("index.html"), "html.parser")
    shell = soup.select_one(".bay-map-shell-v144")
    right_rail = soup.select_one(".bay-right-rail-v144")
    dock = soup.select_one(".bay-scanner-dock-slot-v144")
    scanner = soup.select_one(".bay-scanner-dock-v144")
    assert shell is not None
    assert right_rail is not None
    assert dock is not None
    assert scanner is not None
    assert scanner in dock.descendants
    assert scanner not in right_rail.descendants
    assert right_rail.select_one("#bayActionButtons") is not None
    assert not right_rail.select(".bay-scanner-panel")
    assert not soup.select(".bay-scanner-sticky-slot")


def test_existing_bay_scanner_controls_are_preserved_once() -> None:
    soup = BeautifulSoup(read("index.html"), "html.parser")
    required_ids = {
        "bayScanOutForm",
        "bayScanRemoveMode",
        "bayScanModeToggle",
        "bayScanBayInput",
        "bayTargetClearBtn",
        "bayScanOutInput",
        "bayUndoBtn",
        "bayRedoBtn",
        "bayManualOrderInput",
        "bayManualItemInput",
        "bayManualSubmitBtn",
        "bayAllScansBtn",
        "bayLastMoveSelect",
        "bayScanOutRecent",
    }
    for element_id in required_ids:
        assert len(soup.select(f"#{element_id}")) == 1, element_id


def test_saved_floor_layout_remains_seven_columns() -> None:
    css = read("styles.css")
    assert re.search(
        r"\.bay-map-page-v144\s+\.bay-floor-grid-v19\s*\{[^}]*grid-template-columns:\s*repeat\(7,\s*minmax\(0,\s*1fr\)\)\s*!important",
        css,
        flags=re.S,
    )
    assert "The seven saved physical columns remain unchanged" in css


def test_v144_layout_owns_full_width_map_and_bottom_dock() -> None:
    css = read("styles.css")
    assert 'grid-template-areas:\n    "actions"\n    "map"\n    "scanner"\n    "details"' in css
    assert ".bay-scanner-dock-slot-v144" in css
    assert "position: fixed;" in css
    assert "bottom: 10px;" in css
    assert "padding-bottom: 286px;" in css
    assert ".bay-scanner-dock-v144" in css
    assert 'grid-template-areas: "dock-title dock-route dock-workflow dock-history";' in css



def test_compact_mode_updates_preserve_the_mode_summary_structure() -> None:
    app = read("app.js")
    assert 'const modeValue = els.bayScannerModeSummary.querySelector("b")' in app
    assert 'modeValue.textContent = adding ? "Add to bay" : "Remove from bay"' in app
    assert '"Choose a bay for Add mode."' in app
    assert '"Current bay is found automatically."' in app
    assert '"Scan piece to add..."' in app

def test_html_ids_are_unique() -> None:
    soup = BeautifulSoup(read("index.html"), "html.parser")
    ids = [tag["id"] for tag in soup.find_all(id=True)]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    assert not duplicates


def test_css_braces_are_balanced() -> None:
    css = read("styles.css")
    assert css.count("{") == css.count("}")


def test_release_notes_document_no_backend_change() -> None:
    notes = read("docs/V144_BOTTOM_DOCKED_BAY_SCANNER.md")
    assert "No API, database, scan logic, permissions, or event handlers were changed." in notes
    assert "seven saved physical columns" in notes
