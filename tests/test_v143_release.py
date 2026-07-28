from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_v143_version_markers_and_docs():
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert "20260728-v147" in index
    assert "20260727-v142" not in index
    assert "Current maintained release: **v147**" in readme
    assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")
    assert (ROOT / "docs/V143_INTERNAL_REJECT_TIMELINE.md").is_file()


def test_reject_page_matches_timeline_workspace_contract():
    index = read("index.html")
    app = read("app.js")
    css = read("styles.css")
    reject_section = index.split('id="rejectsPage"', 1)[1].split("<!-- SECTION: Indian Trail", 1)[0]
    assert "reject-header-actions-v143" in reject_section
    assert 'id="rejectSummaryBar"' in reject_section
    assert 'id="rejectLocationFilter"' in reject_section
    assert "reject-timeline-group-v143" in app
    assert "reject-timeline-event-v143" in app
    assert "rejectTimelineDetailHtml" in app
    assert ".reject-timeline-card-v143" in css
    assert ".reject-summary-bar-v143" in css


def test_reject_summary_and_location_filter_are_live():
    app = read("app.js")
    assert "function updateRejectLocationOptions" in app
    assert "function rejectRowsForView" in app
    assert "function renderRejectSummary" in app
    assert 'els.rejectLocationFilter?.addEventListener("change", renderRejectPage)' in app
    assert "Total rejected quantity" in app
    assert "Machines / locations" in app


def test_reject_timeline_contains_required_operational_fields():
    app = read("app.js")
    for label in ("Order / Item", "Delivery date", "Reason", "Machine / location", "Rejected by", "Investigation notes"):
        assert label in app
    assert "formatRejectTime" in app
    assert "rejected_at" in app


def test_static_html_ids_are_unique():
    ids = re.findall(r'\bid="([^"]+)"', read("index.html"))
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    assert not duplicates


def test_javascript_and_css_are_balanced():
    app = read("app.js")
    css = read("styles.css")
    assert app.count("{") == app.count("}")
    assert app.count("(") == app.count(")")
    assert css.count("{") == css.count("}")
