from __future__ import annotations

from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
import tinycss2

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_v136_cache_markers_and_release_docs():
    html = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert html.count("20260724-v136") >= 3
    assert "Current maintained release: **v136**" in readme
    assert changelog.startswith("## v136 - Interface Stability")
    assert (ROOT / "docs" / "V136_INTERFACE_STABILITY.md").is_file()


def test_rack_modal_uses_global_status_helpers_and_no_duplicate_local_wrappers():
    app = read("app.js")
    assert 'rack-details-modal-shell ${escapeHtml(rackStatusClassName(rack))}' in app
    assert '${escapeHtml(rackStatusLabel(rack))}' in app
    assert "const rackStatusText" not in app
    assert "const rackStatusClass" not in app


def test_reject_page_has_resilient_loading_and_retry_states():
    app = read("app.js")
    html = read("index.html")
    assert 'id="rejectPageStatus"' in html
    assert "Promise.allSettled" in app
    assert "data-reject-retry" in app
    assert "Verify a matching active order and item" in app
    assert "Recording Reject..." in app


def test_import_tabs_are_accessible_stable_and_readable():
    app = read("app.js")
    css = read("styles.css")
    assert 'role="tab"' in app
    assert 'aria-selected="${group.key === selected.key ? "true" : "false"}"' in app
    assert 'role="tabpanel"' in app
    assert 'id="adminImportRunPanel"' not in app
    assert "scrollPositions" in app
    assert '.admin-import-run-tab[aria-selected="true"]' in css
    assert "renderAdminDeliveryLists();\n  if (els.importHistory)" not in app


def test_button_system_is_scoped_and_flat():
    css = read("styles.css")
    assert ".app :where(button:not(.sidebar-scrim):not(.modal-backdrop))" not in css
    assert "--control-surface: #f8fafc" in css
    assert "text-shadow" not in css[css.index("/* 13. v136"):css.index("/* Scan table operational markers */")]
    for selector in ("#headerGlobalSearchBtn", "#globalPrintExportBtn", "#adminPage .link-button"):
        assert selector in css


def test_reject_icon_and_bay_scanner_width_ownership_exist():
    css = read("styles.css")
    assert ".top-nav-icon.rejects {" in css
    assert ".top-nav-icon.rejects::before" not in css
    assert "Bay Scanner owns the width of the right rail" in css
    assert ".bay-scanner-panel-v105 .recent-table-wrap" in css
    assert "overflow-x: auto !important" in css


def test_html_ids_unique_and_css_has_no_exact_duplicate_rules():
    soup = BeautifulSoup(read("index.html"), "html.parser")
    ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
    assert [value for value, count in Counter(ids).items() if count > 1] == []

    css = read("styles.css")
    assert css.count("{") == css.count("}")
    rules = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    seen: set[tuple[str, str, str]] = set()
    duplicates: list[tuple[str, str, str]] = []

    def walk(items, context=""):
        for rule in items:
            if rule.type == "qualified-rule":
                key = (context, tinycss2.serialize(rule.prelude).strip(), tinycss2.serialize(rule.content).strip())
                if key in seen:
                    duplicates.append(key)
                seen.add(key)
            elif rule.type == "at-rule" and rule.content is not None:
                nested = tinycss2.parse_rule_list(rule.content, skip_whitespace=True, skip_comments=True)
                walk(nested, f"{context}|@{rule.at_keyword} {tinycss2.serialize(rule.prelude).strip()}")

    walk(rules)
    assert duplicates == []
