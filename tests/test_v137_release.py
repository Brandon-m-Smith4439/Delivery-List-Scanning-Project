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


def test_v137_release_markers_and_documentation():
    html = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert html.count("20260728-v147") >= 6
    assert "Current maintained release: **v147**" in readme
    assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")
    assert (ROOT / "docs" / "V137_INTERFACE_AND_WORKFLOW_VERIFICATION.md").is_file()
    assert "notification-center-v137.css" not in html


def test_truck_and_rack_modal_prints_do_not_inherit_active_scan_date():
    app = read("app.js")
    block = function_block(app, "printSelectedRackPackingSlip", "saveRackDefinition")
    assert 'const dateParam = String(deliveryDateOverride || "").trim();' in block
    assert "activeList" not in block
    assert "isTruckRack" not in block
    assert "rackPackingListUrl(selectedCode, dateParam)" in block
    assert 'body: JSON.stringify({ rackCode: selectedCode, deliveryDate: dateParam })' in block


def test_reject_log_trigger_is_repeatable_and_guarded():
    app = read("app.js")
    html = read("index.html")
    assert 'id="rejectLogOpenBtn"' in html
    assert "rejectLogOpening: false" in app
    assert 'els.rejectLogOpenBtn?.addEventListener("click"' in app
    assert 'event.target.closest("[data-reject-log-open], #rejectLogOpenBtn")' not in app
    block = app[app.index("async function openRejectLogModal"):app.index("async function previewRejectMatch")]
    assert "if (state.rejectLogOpening) return;" in block
    assert "finally" in block
    assert "state.rejectLogOpening = false;" in block
    assert 'trigger?.removeAttribute("aria-busy")' in block
    assert "Find the affected piece" in app
    assert "Describe what happened" in app


def test_only_bottom_right_personal_update_prompt_remains():
    notification = read("notification-center-v135.js")
    css = read("styles.css")
    html = read("index.html")
    assert "ensureUpdateBanner" not in notification
    assert "renderUpdateBanner" not in notification
    assert 'document.getElementById("userLineUpdateBannerV135")?.remove();' in notification
    assert ".user-line-update-banner.v135" in css
    assert "display: none !important" in css[css.index(".user-line-update-banner.v135"):css.index("/* Shared operations modal")]
    assert ".line-update-review-prompt-shell" in css
    prompt_css = css[css.index(".line-update-review-prompt-shell"):css.index("/* Shared operations modal")]
    assert "right: 22px" in prompt_css
    assert "bottom: 22px" in prompt_css
    assert ".line-update-review-primary" in prompt_css
    for element_id in (
        "scanUpdateReviewControl",
        "scanUpdateReviewBtn",
        "scanUpdateMarkReviewedBtn",
    ):
        assert f'id="{element_id}"' in html
        assert element_id in notification


def test_filter_glance_counts_review_actions_and_glass_grid():
    html = read("index.html")
    app = read("app.js")
    css = read("styles.css")
    for element_id in ("scanFilterRemakeBadge", "scanFilterRushBadge", "scanFilterUpdatedBadge"):
        assert f'id="{element_id}"' in html
        assert element_id in app
    assert "updateScanFilterGlanceBadge" in app
    assert 'document.dispatchEvent(new CustomEvent("dls:scan-filters-changed"' in app
    assert "grid-template-columns: repeat(auto-fit, minmax(165px, 1fr))" in css
    assert ".scan-filter-glass-section .glass-filter-tabs" in css
    assert "max-height: 238px" in css
    assert "overflow-y: auto" in css


def test_bay_scanner_has_readable_contained_final_owner():
    html = read("index.html")
    css = read("styles.css")
    soup = BeautifulSoup(html, "html.parser")
    panel = soup.select_one(".bay-scanner-panel-v137")
    assert panel is not None
    required_ids = {
        "bayScanOutForm",
        "bayScanModeToggle",
        "bayScanRemoveMode",
        "bayScanBayInput",
        "bayTargetClearBtn",
        "bayScanOutInput",
        "bayUndoBtn",
        "bayRedoBtn",
        "bayManualOrderInput",
        "bayManualItemInput",
        "bayManualSubmitBtn",
        "bayLastCard",
        "bayScanOutRecent",
    }
    assert required_ids.issubset({node.get("id") for node in panel.find_all(attrs={"id": True})})
    assert "Add or remove glass in three clear steps." in panel.get_text(" ", strip=True)
    assert ".bay-scanner-panel-v137 .bay-scan-step-card-v137" in css
    assert "grid-template-columns: minmax(0, 1fr) !important" in css
    assert "grid-template-columns: minmax(90px, 1fr) minmax(135px, 1.25fr) minmax(90px, 1fr)" in css
    assert ".bay-scanner-panel-v137 .bay-barcode-step-v105 .bay-scan-input-row-v137" in css
    assert ".bay-scanner-panel-v137 :where(input, select)" in css


def test_trash_icon_has_visible_rest_and_reverse_hover_states():
    css = read("styles.css")
    rest = re.search(r"\.app button\.icon-trash\s*\{([^}]*)\}", css)
    hover = re.search(r"\.app button\.icon-trash:hover[^\{]*,\s*\.app button\.icon-trash:focus-visible\s*\{([^}]*)\}", css)
    assert rest and hover
    assert "background: #fff" in rest.group(1)
    assert "color: #a92434" in rest.group(1)
    assert "background: #a92434" in hover.group(1)
    assert "color: #fff" in hover.group(1)


def test_javascript_syntax_html_ids_and_css_integrity():
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
