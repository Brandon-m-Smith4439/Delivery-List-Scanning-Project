from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import subprocess

from bs4 import BeautifulSoup
import tinycss2

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def function_block(source: str, name: str, next_name: str) -> str:
    start = source.index(f"function {name}")
    end = source.index(f"function {next_name}", start)
    return source[start:end]


def test_v138_release_markers_and_documentation():
    html = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    notification = read("notification-center-v135.js")
    assert html.count("20260728-v148") >= 6
    assert "Current maintained release: **v148**" in readme
    assert changelog.startswith("## v148 - Bay Scanner History and Flow Refinement")
    assert (ROOT / "docs" / "V138_REJECT_TRACKING_REDESIGN.md").is_file()
    assert "last-seen.v138" in notification


def test_reject_page_has_professional_date_filter_and_clear_workflow():
    html = read("index.html")
    app = read("app.js")
    soup = BeautifulSoup(html, "html.parser")
    page = soup.select_one("#rejectsPage")
    assert page is not None
    for element_id in (
        "rejectLogOpenBtn",
        "rejectDatePreset",
        "rejectDateFrom",
        "rejectDateTo",
        "rejectClearFiltersBtn",
        "rejectRefreshBtn",
        "rejectPageStatus",
        "rejectHistory",
    ):
        assert page.select_one(f"#{element_id}") is not None
    preset_values = [option.get("value") for option in page.select("#rejectDatePreset option")]
    assert preset_values == ["all", "today", "7-days", "30-days", "custom"]
    assert "function setRejectDatePreset" in app
    assert "function clearRejectFilters" in app
    assert "The From date cannot be later than the Through date." in app
    assert "syncRejectDateLimits" in app


def test_reject_open_button_uses_direct_owner_and_modal_opens_before_catalog_fetch():
    html = read("index.html")
    app = read("app.js")
    soup = BeautifulSoup(html, "html.parser")
    button = soup.select_one("#rejectLogOpenBtn")
    assert button is not None
    assert "primary" in button.get("class", [])
    assert button.get("type") == "button"
    assert 'els.rejectLogOpenBtn?.addEventListener("click"' in app
    assert 'event.target.closest("[data-reject-log-open], #rejectLogOpenBtn")' not in app
    block = function_block(app, "openRejectLogModal", "previewRejectMatch")
    assert block.index("openOperationsModal({") < block.index('fetchJson("/api/rejects/catalog")')
    assert 'body: rejectLogModalHtml({ catalogLoading:' in block
    assert 'kind: "reject-log"' in block
    assert 'trigger?.removeAttribute("aria-busy")' in block


def test_reject_entry_requires_explicit_fresh_verification():
    app = read("app.js")
    modal = function_block(app, "rejectLogModalHtml", "rejectHistoryHtml")
    assert 'id="rejectVerifyBtn"' in modal
    assert "Verify Item" in modal
    assert "What happens after submission" in modal
    assert 'data-operations-close' in modal
    assert 'id="rejectReasonSelect"' in modal
    assert 'id="rejectLocationSelect"' in modal
    assert 'state.rejectMatches = [];' in app
    assert 'event.target.matches("#rejectOrderInput, #rejectItemInput")' in app
    assert 'event.key !== "Enter"' in app
    verify = function_block(app, "previewRejectMatch", "submitRejectLog")
    assert "rejectMatchRequestId" in verify
    assert "reject-match-stage-list" in verify
    assert "Verification failed" in verify


def test_reject_css_is_owned_by_v138_without_superseded_v137_modal_rules():
    css = read("styles.css")
    required = (
        ".rejects-command-header",
        ".reject-filter-panel",
        ".reject-date-range",
        ".reject-summary-card",
        ".reject-event-card",
        '.operations-modal-panel[data-kind="reject-log"]',
        ".reject-log-form-v138",
        ".reject-log-identify-grid-v138",
        ".reject-match-preview.is-valid",
        ".reject-log-actions-v138",
    )
    for selector in required:
        assert selector in css
    assert "reject-log-form-v137" not in css
    assert "reject-log-actions-v137" not in css
    assert "reject-history-toolbar" not in css
    assert "@media (max-width: 720px)" in css
    assert ".reject-log-action-buttons" in css


def test_javascript_html_and_css_integrity():
    for script in ("app.js", "notification-center-v135.js"):
        subprocess.run(["node", "--check", str(ROOT / script)], check=True, capture_output=True, text=True)

    soup = BeautifulSoup(read("index.html"), "html.parser")
    ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
    assert [value for value, count in Counter(ids).items() if count > 1] == []

    css = read("styles.css")
    assert css.count("{") == css.count("}")
    parsed = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    assert [rule for rule in parsed if rule.type == "error"] == []

    seen: set[tuple[str, str, str]] = set()
    duplicates: list[tuple[str, str, str]] = []

    def walk(rules, context=""):
        for rule in rules:
            if rule.type == "qualified-rule":
                key = (
                    context,
                    tinycss2.serialize(rule.prelude).strip(),
                    tinycss2.serialize(rule.content).strip(),
                )
                if key in seen:
                    duplicates.append(key)
                seen.add(key)
            elif rule.type == "at-rule" and rule.content is not None:
                nested = tinycss2.parse_rule_list(rule.content, skip_whitespace=True, skip_comments=True)
                walk(nested, f"{context}|@{rule.at_keyword} {tinycss2.serialize(rule.prelude).strip()}")

    walk(parsed)
    assert duplicates == []
