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


def test_v139_release_markers_and_documentation():
    html = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert html.count("20260728-v147") >= 6
    assert "Current maintained release: **v147**" in readme
    assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")
    assert (ROOT / "docs" / "V139_DROPDOWN_REJECT_AND_IMPORT_HISTORY.md").is_file()


def test_all_single_value_dropdowns_share_swoosh_and_date_indicator_support():
    app = read("app.js")
    assert 'void playAppSound("collapse_open")' in app
    assert app.count('void playAppSound("collapse_close")') >= 2
    assert "custom-select-value-indicator" in app
    assert "custom-select-option-indicator" in app
    assert 'data-custom-indicator="${pendingCount ? "new" : ""}"' in app
    assert "refreshPendingUpdateDates" in app
    assert "window.DLSLineUpdates?.loadAndApply" in app


def test_internal_reject_filter_counter_and_flags_are_explicit():
    html = read("index.html")
    app = read("app.js")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one('#scanFilterRejectBadge i').get_text(strip=True) == "IR"
    assert soup.select_one('[data-filter="internal-rejects"]') is not None
    assert soup.select_one('#countInternalRejects') is not None
    assert soup.select_one('#scanActiveFilterCount') is None
    assert 'filter === "internal-rejects"' in app
    assert 'internal-reject-marker">IR<' in app


def test_reject_history_uses_logged_date_and_preserves_delivery_date():
    app = read("app.js")
    operations = read("operations_features.py")
    assert 'String(row.rejected_at || "").slice(0, 10)' in app
    assert "Rejected / entered" in app
    assert "Delivery date" in app
    assert "formatDisplayDate(row.delivery_date)" in app
    assert 'substr(rejected_at, 1, 10) >= ?' in operations
    assert 'substr(rejected_at, 1, 10) <= ?' in operations


def test_internal_reject_creates_persistent_notification_and_30_second_alert():
    operations = read("operations_features.py")
    notification = read("notification-center-v135.js")
    assert '"source": "internal-reject"' in operations
    assert 'getattr(self.store, "create_app_notification", None)' in operations
    assert "acknowledge_creator=False" in operations
    assert "isInternalRejectNotification" in notification
    assert "internal-reject-notification-toast" in notification
    assert "internal-reject-toast-ack" in notification
    assert "window.setTimeout(dismissRejectToast, 30000)" in notification
    assert 'dls:open-internal-reject-notification' in notification


def test_current_day_import_runs_use_five_per_page_and_reset_by_local_date():
    app = read("app.js")
    assert "adminImportRunsPerPage: 5" in app
    assert 'fetchJson("/api/notifications/history?limit=100")' in app
    assert "importRunLocalDate(entry) === today" in app
    assert "adminTodayImportDate !== today" in app
    assert "data-admin-import-page" in app
    assert "Showing up to five runs per page" in app


def test_automation_history_is_nested_day_run_and_delivery_result():
    app = read("app.js")
    css = read("styles.css")
    assert "function enhanceAutomationImportHistoryResults" in app
    assert "automation-history-day" in app
    assert "automation-history-run" in app
    assert 'details.import-history-entry' in app
    assert "automation-history-day-body" in css
    assert "automation-history-run-body" in css
    assert "delete results.dataset.v139Grouped" in app


def test_javascript_python_html_and_css_integrity():
    for script in ("app.js", "notification-center-v135.js"):
        subprocess.run(["node", "--check", str(ROOT / script)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["python", "-m", "py_compile", str(ROOT / "operations_features.py")],
        check=True,
        capture_output=True,
        text=True,
    )

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
