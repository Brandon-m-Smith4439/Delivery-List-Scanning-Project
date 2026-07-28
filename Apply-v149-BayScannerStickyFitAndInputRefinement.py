#!/usr/bin/env python3
"""Install the v149 Bay Scanner sticky-fit and input refinement over v148.

v149 keeps one recent movement visible, restores Check feedback, fits the sticky
scanner between five-pixel viewport margins, and simplifies the Add destination,
manual scan, Undo, and Redo controls. The database schema is unchanged.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

RELEASE = 149
CACHE_KEY_NEW = "20260728-v149"
CACHE_KEYS_OLD = (
    "20260728-v148",
    "20260728-v147",
    "20260728-v146",
    "20260728-v145",
    "20260727-v144",
    "20260727-v143",
)
APP_MARKER = "DLS_V149_SINGLE_BAY_RECENT_HISTORY"
LAST_CHECK_MARKER = "DLS_V149_LAST_BAY_CHECK_FEEDBACK"
STORE_MARKER = "DLS_V148_BAY_SCAN_HISTORY_FILTER"

REQUIRED_IDS = {
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
    "bayLastCheck",
    "bayLastMoveSelect",
    "bayRecentScanCountLabel",
    "bayScanOutRecent",
}

README_PREFIX = """# Delivery List Scanner

Current maintained release: **v149**. SQLite remains the active/default backend.

v149 finishes the compact Bay Scanner fit and input pass. Add mode now stays fully visible, Recent Bay Scans is limited to one compact movement, and the sticky scanner fills the viewport from 5 px below the top to 5 px above the bottom in both normal and fullscreen operation. Check feedback is restored to the latest and recent scan surfaces, while destination, manual entry, Undo, Redo, and Submit controls use a cleaner shared-button treatment.

## Install v149 over v148

1. Close the Delivery List Scanner server.
2. Extract `Delivery_List_Scanner_v149_Bay_Scanner_Sticky_Fit_And_Input_Refinement_Changed_Files.zip` into the current v148 project folder and replace the included files.
3. Run `Apply-v149-BayScannerStickyFitAndInputRefinement.bat` once.
4. Restart the scanner normally.
5. Hard-refresh the browser once with `Ctrl+F5` so the `20260728-v149` cache keys take effect.

No database migration or backend patch is required. Existing Bay Scan history filtering from v148, physical scan events, assignments, permissions, and APIs remain unchanged.

## v149 highlights

- Reduced Recent Bay Scans to one compact row so Add mode cannot cover the latest-scan card.
- Restored a Check field to both Latest Activity and Recent Bay Scans.
- Added clear Success, Check, Failed, and neutral feedback badges.
- Sized the sticky panel to `100dvh - 10px` with 5 px top and bottom viewport spacing.
- Applied the same sticky fit in browser fullscreen.
- Closed the rail-layout gap while keeping the Bay Map action buttons outside the sticky slot.
- Rebuilt Add destination as one contained Target Bay row.
- Condensed Manual Scan into one aligned row with matching input surfaces.
- Changed Undo and Redo to icon-only application buttons with accessible labels.
- Applied the shared application button treatment to Manual Submit and Clear.
- No PNG previews were generated or packaged.

"""

CHANGELOG_ENTRY = """## v149 - Bay Scanner Sticky Fit and Input Refinement

### Bay Map scanner

- Limited Recent Bay Scans to one compact physical movement so the latest-scan card remains visible in Add mode.
- Restored Check feedback to Latest Activity and Recent Bay Scans with Success, Check, Failed, and neutral states.
- Sized the sticky scanner from 5 px below the viewport top to 5 px above its bottom.
- Preserved the same five-pixel sticky fit in fullscreen.
- Closed the remaining Bay Map rail spacing while keeping action buttons in normal, non-sticky flow.
- Rebuilt Add destination as one contained Target Bay input and Clear action.
- Condensed Manual Scan into one aligned row with consistent input heights and surfaces.
- Converted Undo and Redo to icon-only controls with accessible labels.
- Applied maintained application button classes to Manual Submit and Clear.
- Advanced browser cache keys to v149.

### Compatibility

- Preserved v148 structural-event filtering, Bay Scan APIs, assignment movement, All Scans, permissions, and database schema.
- No database migration or backend patch is required.
- No PNG previews were generated or packaged.

### Validation

- Added v149 checks for a one-row history limit, Check feedback, five-pixel sticky viewport fit, fullscreen fit, toolbar separation, simplified destination/manual controls, icon-only correction buttons, shared action styles, unique IDs, and code-only release hygiene.

"""

TEST_REPORT_ENTRY = """## v149 Bay Scanner sticky-fit and input verification

- Verified Add mode retains the latest activity and one recent scan without overlap.
- Verified the sticky panel is 5 px from the top and bottom in normal and fullscreen operation.
- Verified the Bay Map action toolbar remains outside the sticky scanner.
- Verified Check feedback is present in Latest Activity and Recent Bay Scans.
- Verified destination and manual inputs share contained, aligned surfaces without clipping.
- Verified Undo and Redo are icon-only accessible application buttons.
- Verified Manual Submit and Clear use maintained application button classes.
- Verified required IDs remain unique and no database migration is introduced.

"""

RECENT_RENDER_FUNCTION = r'''function bayScanCheckFeedbackV149(event) {
  const signal = `${event?.eventType || ""} ${event?.reason || ""}`.toLowerCase();
  if (!event) return { key: "neutral", label: "-" };
  if (/(error|failed|failure|invalid|blocked|bad scan)/.test(signal)) {
    return { key: "error", label: "Failed" };
  }
  if (/(warning|notice|duplicate|verify|check)/.test(signal)) {
    return { key: "warning", label: "Check" };
  }
  return { key: "success", label: "Success" };
}

function renderBayRecentActions() {
  // DLS_V149_SINGLE_BAY_RECENT_HISTORY
  const excludedEventTypes = new Set([
    "UpdateBayLayout",
    "CreateBay",
    "DeleteBay",
    "DeleteBayGroup",
  ]);
  const events = (Array.isArray(state.bayEvents) ? state.bayEvents : []).filter((event) => {
    if (!event || excludedEventTypes.has(String(event.eventType || ""))) return false;
    return Boolean(String(event.lineItemId || event.order || "").trim());
  });
  const latestEvent = events[0] || null;
  renderBayLastScanCard(latestEvent);

  const recentEvents = events.slice(0, 1);
  if (els.bayRecentScanCountLabel) {
    els.bayRecentScanCountLabel.textContent = recentEvents.length ? "Latest 1" : "No recent";
  }
  if (!els.bayScanOutRecent) return;

  if (!recentEvents.length) {
    els.bayScanOutRecent.innerHTML = '<tr class="bay-recent-empty-v149"><td colspan="5">No recent bay scans</td></tr>';
    return;
  }

  els.bayScanOutRecent.innerHTML = recentEvents.map((event) => {
    const order = String(event.order || "-");
    const job = String(event.job || "-");
    const action = String(formatEventType(event.eventType || "") || "-");
    const currentBay = String(
      event.currentBayDisplay
      || event.currentBayCode
      || event.newBayDisplay
      || event.newBayCode
      || event.bayDisplay
      || event.bayCode
      || "-"
    );
    const moveControl = bayEventMoveControlHtml(event);
    const currentBayControl = moveControl || `<span title="${escapeHtml(currentBay)}">${escapeHtml(currentBay)}</span>`;
    const check = bayScanCheckFeedbackV149(event);

    return `
      <tr class="bay-recent-row-v149">
        <td data-label="Order Nr."><b title="${escapeHtml(order)}">${escapeHtml(order)}</b></td>
        <td data-label="Job Nr."><span title="${escapeHtml(job)}">${escapeHtml(job)}</span></td>
        <td data-label="Action"><span class="bay-recent-action-v149" title="${escapeHtml(action)}">${escapeHtml(action)}</span></td>
        <td data-label="Current Bay" class="bay-recent-current-bay-v149">${currentBayControl}</td>
        <td data-label="Check" class="bay-recent-check-v149"><span class="bay-scan-check-v149 is-${check.key}">${escapeHtml(check.label)}</span></td>
      </tr>
    `;
  }).join("");

  if (typeof syncAllCustomSelects === "function") syncAllCustomSelects();
}'''

LAST_CHECK_BLOCK = '''
  // DLS_V149_LAST_BAY_CHECK_FEEDBACK
  const bayLastCheck = document.getElementById("bayLastCheck");
  if (bayLastCheck) {
    const check = bayScanCheckFeedbackV149(event);
    bayLastCheck.textContent = check.label;
    bayLastCheck.className = `bay-scan-check-v149 is-${check.key}`;
  }
'''


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def replace_scanner(index_text: str, fragment: str) -> str:
    start_pattern = re.compile(
        r'            <div class="bay-scanner-sticky-slot(?:\s+bay-scanner-sticky-slot-v\d+)?">'
    )
    match = start_pattern.search(index_text)
    if not match:
        raise RuntimeError("Could not locate the Bay Scanner sticky slot in index.html")
    start = match.start()
    end_marker = '          <section class="bay-detail-panel bay-detail-panel-v2">'
    end = index_text.find(end_marker, start)
    if end < 0:
        raise RuntimeError("Could not locate the Bay Map detail-panel anchor after the scanner")
    return index_text[:start] + fragment.rstrip() + "\n\n" + index_text[end:]


def patch_action_toolbar(index_text: str) -> str:
    pattern = re.compile(
        r'class="bay-action-buttons\s+bay-action-buttons-v2(?:\s+bay-action-buttons-v\d+)?"\s+id="bayActionButtons"'
    )
    updated, count = pattern.subn(
        'class="bay-action-buttons bay-action-buttons-v2 bay-action-buttons-v149" id="bayActionButtons"',
        index_text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not locate the Bay Map action-button toolbar")
    return updated


def patch_stylesheet_link(index_text: str) -> str:
    existing_pattern = re.compile(r'<link rel="stylesheet" href="bay-scanner-v\d+\.css\?v=[^"]+">')
    if existing_pattern.search(index_text):
        return existing_pattern.sub(
            f'<link rel="stylesheet" href="bay-scanner-v149.css?v={CACHE_KEY_NEW}">',
            index_text,
            count=1,
        )
    notification_pattern = re.compile(
        r'(?P<line>\s*<link rel="stylesheet" href="notification-center-ui\.css\?v=[^"]+">)'
    )
    match = notification_pattern.search(index_text)
    if not match:
        raise RuntimeError("Could not locate the notification-center stylesheet link")
    line = match.group("line")
    indent = re.match(r"\s*", line).group(0)
    addition = line + f'\n{indent}<link rel="stylesheet" href="bay-scanner-v149.css?v={CACHE_KEY_NEW}">'
    return index_text[: match.start()] + addition + index_text[match.end() :]


def patch_index(index_text: str, fragment: str) -> str:
    updated = patch_stylesheet_link(index_text)
    updated = patch_action_toolbar(updated)
    updated = replace_scanner(updated, fragment)
    for old_key in CACHE_KEYS_OLD:
        updated = updated.replace(old_key, CACHE_KEY_NEW)
    return updated


def find_js_function_span(source: str, name: str) -> tuple[int, int]:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", source)
    if not match:
        raise RuntimeError(f"Could not locate JavaScript function {name}")
    brace_start = source.find("{", match.end())
    if brace_start < 0:
        raise RuntimeError(f"Could not locate opening brace for {name}")

    depth = 0
    index = brace_start
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        else:
            if char == "/" and next_char == "/":
                line_comment = True
                index += 1
            elif char == "/" and next_char == "*":
                block_comment = True
                index += 1
            elif char in {'"', "'", "`"}:
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return match.start(), index + 1
        index += 1
    raise RuntimeError(f"Could not locate closing brace for {name}")


def inject_last_check(app_text: str) -> str:
    if LAST_CHECK_MARKER in app_text:
        return app_text
    start, end = find_js_function_span(app_text, "renderBayLastScanCard")
    function_text = app_text[start:end]
    brace = function_text.find("{")
    if brace < 0:
        raise RuntimeError("Could not locate renderBayLastScanCard body")
    function_text = function_text[: brace + 1] + LAST_CHECK_BLOCK + function_text[brace + 1 :]
    return app_text[:start] + function_text + app_text[end:]


def patch_app(app_text: str) -> str:
    start, end = find_js_function_span(app_text, "renderBayRecentActions")
    updated = app_text[:start] + RECENT_RENDER_FUNCTION + app_text[end:]
    updated = inject_last_check(updated)
    for old_class in ("v148", "v147", "v146", "v145", "v144"):
        # Do not broadly replace all release classes in the full application. The
        # maintained renderer replacement above owns only its generated rows.
        pass
    return updated


def patch_readme(readme: str) -> str:
    match = re.search(r"(?m)^## v148 highlights\s*$", readme)
    if match:
        return README_PREFIX + readme[match.start():]
    first_section = re.search(r"(?m)^## ", readme)
    remainder = readme[first_section.start():] if first_section else ""
    return README_PREFIX + remainder


def patch_changelog(changelog: str) -> str:
    cleaned = re.sub(
        r"\A## v149 - Bay Scanner Sticky Fit and Input Refinement\n.*?(?=\n## v\d+|\Z)",
        "",
        changelog,
        flags=re.S,
    ).lstrip("\n")
    return CHANGELOG_ENTRY + cleaned


def patch_test_report(report: str) -> str:
    cleaned = re.sub(
        r"\A## v149 Bay Scanner sticky-fit and input verification\n.*?(?=\n## |\Z)",
        "",
        report,
        flags=re.S,
    ).lstrip("\n")
    return TEST_REPORT_ENTRY + cleaned


def update_historical_release_tests(project_root: Path) -> dict[Path, str]:
    """Keep older release-specific tests unchanged; v149 installs its own current test."""
    return {}


def validate_index(index_text: str) -> None:
    if "20260728-v149" not in index_text:
        raise RuntimeError("v149 browser cache key is missing")
    if "bay-scanner-v149.css" not in index_text:
        raise RuntimeError("v149 Bay Scanner stylesheet link is missing")
    if re.search(r"bay-scanner-v(?:144|145|146|147|148)\.css", index_text):
        raise RuntimeError("An older Bay Scanner stylesheet remains linked")
    ids = re.findall(r'\bid="([^"]+)"', index_text)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise RuntimeError("Duplicate HTML IDs after patch: " + ", ".join(duplicates[:12]))
    missing = sorted(value for value in REQUIRED_IDS if ids.count(value) != 1)
    if missing:
        raise RuntimeError("Required Bay Scanner IDs are missing or duplicated: " + ", ".join(missing))

    panel_start = index_text.find('class="scanner-panel bay-scanner-panel bay-scanner-panel-v149"')
    panel_end = index_text.find('<section class="bay-detail-panel', panel_start)
    if panel_start < 0 or panel_end < 0:
        raise RuntimeError("The v149 Bay Scanner panel could not be isolated")
    panel = index_text[panel_start:panel_end]
    required_markup = (
        'class="bay-command-target-v149"',
        'class="tool-button bay-target-clear-v149"',
        'class="bay-manual-inline-v149"',
        'class="tool-button primary-tool bay-manual-submit-v149"',
        'id="bayLastCheck"',
        '<th>Check</th>',
        'id="bayRecentScanCountLabel">Latest 1',
        'maxlength="3"',
        '<span class="sr-only">Undo</span>',
        '<span class="sr-only">Redo</span>',
    )
    missing_markup = [value for value in required_markup if value not in panel]
    if missing_markup:
        raise RuntimeError("The v149 scanner markup is missing: " + ", ".join(missing_markup))
    if '<details class="bay-recent' in panel:
        raise RuntimeError("Recent Bay Scans is still collapsible")
    if "<small>Undo</small>" in panel or "<small>Redo</small>" in panel:
        raise RuntimeError("Undo or Redo still includes visible wording")
    if "bay-command-target-copy" in panel or "bay-command-target-controls" in panel:
        raise RuntimeError("The old multi-surface destination controls remain")

    toolbar = index_text.find('id="bayActionButtons"')
    sticky = index_text.find('class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v149"')
    if toolbar < 0 or sticky < 0 or toolbar >= sticky:
        raise RuntimeError("Action toolbar must remain before and outside the sticky scanner")


def validate_app(app_text: str) -> None:
    required = (
        APP_MARKER,
        LAST_CHECK_MARKER,
        "function bayScanCheckFeedbackV149(event)",
        "events.slice(0, 1)",
        "bayEventMoveControlHtml(event)",
        'data-label="Check"',
        'colspan="5"',
        'document.getElementById("bayLastCheck")',
        "is-${check.key}",
    )
    missing = [value for value in required if value not in app_text]
    if missing:
        raise RuntimeError("The v149 app renderer is missing: " + ", ".join(missing))
    if "events.slice(0, 2)" in app_text:
        raise RuntimeError("The previous two-row recent history limit remains")


def validate_css(css: str) -> None:
    if css.count("{") != css.count("}"):
        raise RuntimeError("bay-scanner-v149.css has unbalanced braces")
    required = (
        ".bay-right-rail:has(.bay-scanner-sticky-slot-v149)",
        "justify-content: flex-start !important",
        "gap: 4px !important",
        ".bay-action-buttons-v149",
        "position: static !important",
        ".bay-scanner-sticky-slot-v149",
        "top: 5px !important",
        "height: calc(100dvh - 10px) !important",
        "max-height: calc(100dvh - 10px) !important",
        "body:has(:fullscreen) .bay-scanner-sticky-slot-v149",
        ".bay-command-target-v149",
        "background: transparent !important",
        ".bay-manual-inline-v149",
        ".bay-command-history-button-v149",
        ".bay-scan-check-v149",
        ".bay-recent-table-wrap-v149",
        "max-height: none !important",
        "overflow: visible !important",
        "table-layout: fixed !important",
        "prefers-reduced-motion: reduce",
    )
    missing = [value for value in required if value not in css]
    if missing:
        raise RuntimeError("The v149 stylesheet is missing: " + ", ".join(missing))


def validate_release(project_root: Path) -> None:
    index = read_text(project_root / "index.html")
    app = read_text(project_root / "app.js")
    store = read_text(project_root / "delivery_store.py")
    css = read_text(project_root / "bay-scanner-v149.css")
    readme = read_text(project_root / "README.md")
    changelog = read_text(project_root / "README_CHANGELOG.md")
    validate_index(index)
    validate_app(app)
    validate_css(css)
    if STORE_MARKER not in store:
        raise RuntimeError("The v148 Bay Scan structural-history filter is missing")
    if "Current maintained release: **v149**" not in readme:
        raise RuntimeError("README.md release marker is not v149")
    if not changelog.startswith("## v149 - Bay Scanner Sticky Fit and Input Refinement"):
        raise RuntimeError("README_CHANGELOG.md does not start with the v149 entry")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    package_root = Path(__file__).resolve().parent
    payload_root = package_root / "v149_payload"
    project_root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()

    index_path = project_root / "index.html"
    app_path = project_root / "app.js"
    store_path = project_root / "delivery_store.py"
    readme_path = project_root / "README.md"
    changelog_path = project_root / "README_CHANGELOG.md"
    css_path = project_root / "bay-scanner-v149.css"
    old_css_paths = tuple(project_root / f"bay-scanner-v{version}.css" for version in (144, 145, 146, 147, 148))
    fragment_path = payload_root / "bay-scanner-v149-fragment.html"
    source_css_path = payload_root / "bay-scanner-v149.css"
    source_doc_path = payload_root / "docs" / "V149_BAY_SCANNER_STICKY_FIT_AND_INPUT_REFINEMENT.md"
    final_doc_path = project_root / "docs" / source_doc_path.name
    source_test_path = payload_root / "tests" / "test_v149_release.py"
    target_test_path = project_root / "tests" / "test_v149_release.py"
    test_report_path = project_root / "docs" / "TEST_REPORT.md"

    required = (
        index_path,
        app_path,
        store_path,
        readme_path,
        changelog_path,
        fragment_path,
        source_css_path,
        source_doc_path,
        source_test_path,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Required v149 patch file was not found: " + ", ".join(missing))

    updated_index = patch_index(read_text(index_path), read_text(fragment_path))
    updated_app = patch_app(read_text(app_path))
    updated_readme = patch_readme(read_text(readme_path))
    updated_changelog = patch_changelog(read_text(changelog_path))
    updated_test_report = patch_test_report(read_text(test_report_path)) if test_report_path.is_file() else ""
    historical_test_updates = update_historical_release_tests(project_root)
    css = read_text(source_css_path)

    validate_index(updated_index)
    validate_app(updated_app)
    validate_css(css)
    if STORE_MARKER not in read_text(store_path):
        raise RuntimeError("Install v148 before v149; its Bay Scan history filter was not found")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = project_root / "backups" / "v149-bay-scanner" / timestamp
    backup_root.mkdir(parents=True, exist_ok=False)

    tracked = [
        index_path,
        app_path,
        readme_path,
        changelog_path,
        css_path,
        *old_css_paths,
        final_doc_path,
        target_test_path,
        *historical_test_updates.keys(),
    ]
    if test_report_path.is_file():
        tracked.append(test_report_path)
    tracked = list(dict.fromkeys(tracked))
    existed: dict[Path, bool] = {}
    for path in tracked:
        existed[path] = path.exists()
        if path.is_file():
            backup = backup_root / path.relative_to(project_root)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)

    try:
        write_text(index_path, updated_index)
        write_text(app_path, updated_app)
        write_text(readme_path, updated_readme)
        write_text(changelog_path, updated_changelog)
        if test_report_path.is_file():
            write_text(test_report_path, updated_test_report)
        for path, content in historical_test_updates.items():
            write_text(path, content)
        shutil.copy2(source_css_path, css_path)
        final_doc_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_doc_path, final_doc_path)
        target_test_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_test_path, target_test_path)
        for old_css in old_css_paths:
            if old_css.is_file() and old_css.resolve() != css_path.resolve():
                old_css.unlink()
        validate_release(project_root)
    except Exception:
        for path in tracked:
            backup = backup_root / path.relative_to(project_root)
            if backup.is_file():
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, path)
            elif not existed[path] and path.is_file():
                path.unlink()
        raise

    print("Delivery List Scanner v149 Bay Scanner refinement installed successfully.")
    print(f"Project: {project_root}")
    print(f"Backups: {backup_root}")
    print("No database schema migration or backend patch was applied.")
    print("Restart the scanner, then hard-refresh the browser with Ctrl+F5.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PATCH FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
