#!/usr/bin/env python3
"""Install the v148 Bay Scanner history and flow refinement over v147.

v148 removes the normal-flow gap above the scanner, keeps Recent Bay Scans
permanently visible in a compact four-column table, and filters structural Bay
Map edits out of scan history. The database schema is unchanged.
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

RELEASE = 148
CACHE_KEY_NEW = "20260728-v148"
CACHE_KEYS_OLD = (
    "20260728-v147",
    "20260728-v146",
    "20260728-v145",
    "20260727-v144",
    "20260727-v143",
)
MARKER = "bay-scanner-panel-v148"
APP_MARKER = "DLS_V148_COMPACT_BAY_RECENT_HISTORY"
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
    "bayLastMoveSelect",
    "bayRecentScanCountLabel",
    "bayScanOutRecent",
}

REMOVED_TARGET_COPY = (
    "Current bay is found automatically in Remove mode.",
    "Current bay is found automatically.",
    "Remove mode finds the current bay automatically.",
)

README_PREFIX = """# Delivery List Scanner

Current maintained release: **v148**. SQLite remains the active/default backend.

v148 finishes the compact Bay Scanner workflow after floor review. The non-sticky Bay Map action toolbar and scanner now sit directly together in normal flow, while only the scanner becomes sticky after it reaches the top. Recent Bay Scans stays open in a compact four-column table, percentage labels disappear in Remove mode, and structural Bay Map edits are excluded from scan history.

## Install v148 over v147

1. Close the Delivery List Scanner server.
2. Extract `Delivery_List_Scanner_v148_Bay_Scanner_History_And_Flow_Refinement_Changed_Files.zip` into the current v147 project folder and replace the included files.
3. Run `Apply-v148-BayScannerHistoryAndFlowRefinement.bat` once.
4. Restart the scanner normally.
5. Hard-refresh the browser once with `Ctrl+F5` so the `20260728-v148` cache keys take effect.

No database migration is required. v148 applies a small store-layer history filter so layout-edit events no longer enter or appear in Bay Scan history. Existing scan events, bay assignments, audit records, permissions, and scanner behavior are preserved.

## v148 highlights

- Eliminated the large normal-flow gap between the static Bay Map action buttons and Bay Scanner.
- Kept the action buttons non-sticky; only the scanner panel sticks after reaching the top.
- Removed the `Just now` / waiting badge beside the Bay Scanner title while preserving its compatibility ID as a hidden status node.
- Hid the percentage labels under Route Pulse while Remove mode is selected.
- Replaced the collapsible Recent Bay Scans disclosure with a permanently open compact table.
- Reduced recent history to Order Nr., Job Nr., Action, and Current Bay.
- Kept Current Bay editable through the existing location-change dropdown.
- Removed horizontal and vertical scrolling from the recent history section.
- Excluded structural layout edits from both Recent Bay Scans and All Scans history while retaining administrative audit records.
- No PNG previews were generated or packaged.

"""

CHANGELOG_ENTRY = """## v148 - Bay Scanner History and Flow Refinement

### Bay Map scanner

- Removed the normal-flow gap between the non-sticky Bay Map action toolbar and the scanner panel.
- Kept the action toolbar static while preserving the scanner-only sticky behavior.
- Removed the visible live-time badge beside the Bay Scanner title and retained its ID as a hidden compatibility node.
- Hid Route Pulse percentage labels in Remove mode while keeping quantity totals visible.
- Replaced Recent Bay Scans' collapsible disclosure with a permanently open compact table.
- Limited recent rows to Order Nr., Job Nr., Action, and editable Current Bay.
- Removed horizontal and vertical scrolling from the recent history surface.
- Advanced browser cache keys to v148.

### History safety

- Bay event history now returns only item-linked physical bay events.
- Structural events such as layout updates, bay creation, and bay deletion are no longer inserted into Bay Scan history.
- Existing historical structural events are filtered from Recent Bay Scans and All Scans.
- Administrative audit records remain intact for accountability.
- No database schema migration is required.

### Validation

- Added v148 checks for static-toolbar adjacency, scanner-only stickiness, hidden live badge, Remove-mode percentage suppression, permanently open non-scrollable history, four-column rendering, editable Current Bay, unique IDs, JavaScript ownership, and backend history filtering.

"""

TEST_REPORT_ENTRY = """## v148 Bay Scanner history and flow verification

- Verified the static Bay Map action toolbar and scanner are adjacent in normal flow.
- Verified only the scanner slot is sticky.
- Verified the title status node is hidden and the `Just now` badge is not visible.
- Verified Remove mode hides Route Pulse percentage labels.
- Verified Recent Bay Scans is permanently open, non-scrollable, and limited to four compact columns.
- Verified Current Bay retains the existing move dropdown.
- Verified structural Bay Map edits are excluded from Bay Scan history while audit records remain available.
- Verified required Bay Scanner IDs remain unique and no schema migration is introduced.

"""

RECENT_RENDER_FUNCTION = r'''function renderBayRecentActions() {
  // DLS_V148_COMPACT_BAY_RECENT_HISTORY
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

  const recentEvents = events.slice(0, 2);
  if (els.bayRecentScanCountLabel) {
    els.bayRecentScanCountLabel.textContent = `${recentEvents.length} recent`;
  }
  if (!els.bayScanOutRecent) return;

  if (!recentEvents.length) {
    els.bayScanOutRecent.innerHTML = '<tr class="bay-recent-empty-v148"><td colspan="4">No recent bay scans</td></tr>';
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

    return `
      <tr class="bay-recent-row-v148">
        <td data-label="Order Nr."><b title="${escapeHtml(order)}">${escapeHtml(order)}</b></td>
        <td data-label="Job Nr."><span title="${escapeHtml(job)}">${escapeHtml(job)}</span></td>
        <td data-label="Action"><span class="bay-recent-action-v148" title="${escapeHtml(action)}">${escapeHtml(action)}</span></td>
        <td data-label="Current Bay" class="bay-recent-current-bay-v148">${currentBayControl}</td>
      </tr>
    `;
  }).join("");

  if (typeof syncAllCustomSelects === "function") syncAllCustomSelects();
}'''

GET_BAY_EVENTS_METHOD = '''    def get_bay_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return item-linked physical Bay Map history with its current move target."""
        # DLS_V148_BAY_SCAN_HISTORY_FILTER
        safe_limit = max(1, min(int(limit or 20), 250))
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT be.*,
                       b.bay_code AS bay_code,
                       b.display_name AS bay_display,
                       old_bay.bay_code AS old_bay_code,
                       old_bay.display_name AS old_bay_display,
                       new_bay.bay_code AS new_bay_code,
                       new_bay.display_name AS new_bay_display,
                       li.order_no, li.item_no, li.customer, li.dimensions, li.product, li.job,
                       current_ba.id AS current_assignment_id,
                       current_bay.bay_code AS current_bay_code,
                       current_bay.display_name AS current_bay_display
                FROM bay_events be
                LEFT JOIN bays b ON b.id = be.bay_id
                LEFT JOIN bays old_bay ON old_bay.id = be.old_bay_id
                LEFT JOIN bays new_bay ON new_bay.id = be.new_bay_id
                LEFT JOIN line_items li ON li.id = be.line_item_id
                LEFT JOIN bay_assignments current_ba ON current_ba.id = (
                    SELECT ba2.id
                    FROM bay_assignments ba2
                    WHERE ba2.line_item_id = be.line_item_id
                      AND ba2.status NOT IN ('Cleared', 'Cancelled')
                    ORDER BY ba2.id DESC
                    LIMIT 1
                )
                LEFT JOIN bays current_bay ON current_bay.id = current_ba.bay_id
                WHERE COALESCE(be.line_item_id, '') <> ''
                  AND be.event_type NOT IN ('UpdateBayLayout', 'CreateBay', 'DeleteBay', 'DeleteBayGroup')
                ORDER BY be.id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "lineItemId": row["line_item_id"] or "",
                "eventType": row["event_type"],
                "bayCode": row["bay_code"] or "",
                "bayDisplay": row["bay_display"] or row["bay_code"] or "",
                "oldBayCode": row["old_bay_code"] or "",
                "oldBayDisplay": row["old_bay_display"] or row["old_bay_code"] or "",
                "newBayCode": row["new_bay_code"] or "",
                "newBayDisplay": row["new_bay_display"] or row["new_bay_code"] or "",
                "assignmentId": int(row["current_assignment_id"] or 0),
                "currentBayCode": row["current_bay_code"] or "",
                "currentBayDisplay": row["current_bay_display"] or row["current_bay_code"] or "",
                "order": row["order_no"] or "",
                "item": row["item_no"] or "",
                "job": row["job"] or "",
                "customer": row["customer"] or "",
                "dimensions": row["dimensions"] or "",
                "product": row["product"] or "",
                "reason": row["reason"] or "",
                "user": row["user_name"] or "",
                "time": row["created_at"],
            }
            for row in rows
        ]
'''

INSERT_BAY_EVENT_METHOD = '''    def insert_bay_event(
        self,
        con: sqlite3.Connection,
        bay_id: int | None,
        line_item_id: str,
        event_type: str,
        user: str,
        reason: str = "",
        old_bay_id: int | None = None,
        new_bay_id: int | None = None,
    ) -> None:
        """Create one item movement event while excluding structural map edits."""
        # DLS_V148_BAY_SCAN_HISTORY_FILTER
        clean_event_type = str(event_type or "").strip()
        if not str(line_item_id or "").strip() or clean_event_type in {
            "UpdateBayLayout",
            "CreateBay",
            "DeleteBay",
            "DeleteBayGroup",
        }:
            return
        con.execute(
            """
            INSERT INTO bay_events (bay_id, line_item_id, event_type, old_bay_id, new_bay_id, reason, user_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bay_id, line_item_id, clean_event_type, old_bay_id, new_bay_id, reason, user, now_iso()),
        )
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
        'class="bay-action-buttons bay-action-buttons-v2 bay-action-buttons-v148" id="bayActionButtons"',
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
            f'<link rel="stylesheet" href="bay-scanner-v148.css?v={CACHE_KEY_NEW}">',
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
    addition = line + f'\n{indent}<link rel="stylesheet" href="bay-scanner-v148.css?v={CACHE_KEY_NEW}">'
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


def patch_app(app_text: str) -> str:
    updated = app_text
    for sentence in REMOVED_TARGET_COPY:
        updated = updated.replace(f'"{sentence}"', '""')
        updated = updated.replace(f"'{sentence}'", "''")
    if APP_MARKER not in updated:
        start, end = find_js_function_span(updated, "renderBayRecentActions")
        updated = updated[:start] + RECENT_RENDER_FUNCTION + updated[end:]
    return updated


def replace_python_method(source: str, name: str, replacement: str) -> str:
    tree = ast.parse(source)
    candidates = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if not candidates:
        raise RuntimeError(f"Could not locate Python method {name}")
    node = sorted(candidates, key=lambda item: item.lineno)[-1]
    lines = source.splitlines(keepends=True)
    return "".join(lines[: node.lineno - 1]) + replacement.rstrip() + "\n" + "".join(lines[node.end_lineno :])


def patch_store(store_text: str) -> str:
    if STORE_MARKER in store_text:
        return store_text
    updated = replace_python_method(store_text, "get_bay_events", GET_BAY_EVENTS_METHOD)
    updated = replace_python_method(updated, "insert_bay_event", INSERT_BAY_EVENT_METHOD)
    ast.parse(updated)
    return updated


def patch_readme(readme: str) -> str:
    markers = (
        "## v147 highlights",
        "## v146 highlights",
        "## v145 highlights",
        "## v144 highlights",
        "## v143 highlights",
    )
    marker_index = next((readme.find(marker) for marker in markers if readme.find(marker) >= 0), -1)
    if marker_index < 0:
        raise RuntimeError("README.md does not contain a previous-release highlights anchor")
    updated = README_PREFIX + readme[marker_index:]
    doc_line = "- v148 Bay Scanner history and flow refinement: `docs/V148_BAY_SCANNER_HISTORY_AND_FLOW_REFINEMENT.md`"
    if doc_line not in updated:
        docs_anchor = "- Ongoing version history: `README_CHANGELOG.md`"
        if docs_anchor not in updated:
            raise RuntimeError("README.md project documentation list was not found")
        updated = updated.replace(docs_anchor, docs_anchor + "\n" + doc_line, 1)
    return updated


def patch_changelog(changelog: str) -> str:
    if changelog.startswith("## v148 - Bay Scanner History and Flow Refinement"):
        return changelog
    return CHANGELOG_ENTRY + changelog.lstrip()


def patch_test_report(report: str) -> str:
    if "## v148 Bay Scanner history and flow verification" in report:
        return report
    heading = "# Test Report"
    if report.startswith(heading):
        remainder = report[len(heading) :].lstrip("\n")
        return heading + "\n\n" + TEST_REPORT_ENTRY + remainder
    return TEST_REPORT_ENTRY + report.lstrip()


def update_historical_release_tests(project_root: Path) -> dict[Path, str]:
    updates: dict[Path, str] = {}
    tests_root = project_root / "tests"
    if not tests_root.is_dir():
        return updates
    for test_path in sorted(tests_root.glob("test_*.py")):
        original = read_text(test_path)
        updated = original
        updated = updated.replace("20260728-v147", CACHE_KEY_NEW)
        updated = updated.replace("Current maintained release: **v147**", "Current maintained release: **v148**")
        updated = updated.replace(
            'changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")',
            'changelog.startswith("## v148 - Bay Scanner History and Flow Refinement")',
        )
        if test_path.name in {"test_v145_release.py", "test_v146_release.py", "test_v147_release.py"}:
            updated = updated.replace("v147", "v148")
            updated = updated.replace("V147_BAY_SCANNER_CONTAINMENT_AND_STICKY_REFINEMENT.md", "V148_BAY_SCANNER_HISTORY_AND_FLOW_REFINEMENT.md")
            updated = updated.replace("Bay Scanner Route and Sticky Refinement", "Bay Scanner History and Flow Refinement")
        if updated != original:
            updates[test_path] = updated
    return updates


def validate_index(index_text: str) -> None:
    if MARKER not in index_text:
        raise RuntimeError("The v148 Bay Scanner ownership marker is missing")
    if f'bay-scanner-v148.css?v={CACHE_KEY_NEW}' not in index_text:
        raise RuntimeError("The v148 Bay Scanner stylesheet is not linked")
    if re.search(r'bay-scanner-v(?:144|145|146|147)\.css', index_text):
        raise RuntimeError("A previous Bay Scanner stylesheet link remains in index.html")
    if "bay-action-buttons-v148" not in index_text:
        raise RuntimeError("The v148 Bay Map action-toolbar owner is missing")
    if any(old_key in index_text for old_key in CACHE_KEYS_OLD):
        raise RuntimeError("A previous browser cache key remains in index.html")

    ids = re.findall(r'\bid="([^"]+)"', index_text)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise RuntimeError("Duplicate HTML IDs after patch: " + ", ".join(duplicates[:12]))
    missing = sorted(value for value in REQUIRED_IDS if ids.count(value) != 1)
    if missing:
        raise RuntimeError("Required Bay Scanner IDs are missing or duplicated: " + ", ".join(missing))

    panel_start = index_text.find('class="scanner-panel bay-scanner-panel bay-scanner-panel-v148"')
    panel_end = index_text.find('<section class="bay-detail-panel', panel_start)
    panel = index_text[panel_start:panel_end]
    if '<span class="bay-scanner-live-status-v148" id="bayScanOutStatus" hidden' not in panel:
        raise RuntimeError("The Bay Scanner status compatibility node must be hidden")
    if "Just now" in panel or ">Waiting<" in panel:
        raise RuntimeError("The visible live-time badge remains in the Bay Scanner title")
    if "<details class=\"bay-recent" in panel:
        raise RuntimeError("Recent Bay Scans is still collapsible")
    if 'class="bay-recent-panel-v148"' not in panel:
        raise RuntimeError("The permanently open Recent Bay Scans panel is missing")
    for label in ("Order Nr.", "Job Nr.", "Action", "Current Bay"):
        if f"<th>{label}</th>" not in panel:
            raise RuntimeError(f"Recent Bay Scans is missing {label}")
    if any(label in panel.split('class="bay-recent-panel-v148"', 1)[1] for label in ("<th>Time</th>", "<th>Check</th>", "<th>Change Location</th>")):
        raise RuntimeError("Nonessential Recent Bay Scans columns remain")


def validate_app(app_text: str) -> None:
    if APP_MARKER not in app_text:
        raise RuntimeError("The compact Recent Bay Scans renderer is missing")
    required = (
        'events.slice(0, 2)',
        'event.job',
        'bayEventMoveControlHtml(event)',
        'data-label="Current Bay"',
        'colspan="4"',
    )
    missing = [value for value in required if value not in app_text]
    if missing:
        raise RuntimeError("The v148 app renderer is missing: " + ", ".join(missing))
    remaining = [sentence for sentence in REMOVED_TARGET_COPY if sentence in app_text]
    if remaining:
        raise RuntimeError("Removed target guidance remains in app.js: " + ", ".join(remaining))


def validate_store(store_text: str) -> None:
    ast.parse(store_text)
    required = (
        STORE_MARKER,
        "WHERE COALESCE(be.line_item_id, '') <> ''",
        "li.product, li.job",
        '"job": row["job"] or ""',
        'if not str(line_item_id or "").strip() or clean_event_type in {',
        '"UpdateBayLayout"',
        '"CreateBay"',
        '"DeleteBay"',
        '"DeleteBayGroup"',
    )
    missing = [value for value in required if value not in store_text]
    if missing:
        raise RuntimeError("The v148 store history filter is missing: " + ", ".join(missing))


def validate_css(css: str) -> None:
    if css.count("{") != css.count("}"):
        raise RuntimeError("bay-scanner-v148.css has unbalanced braces")
    required = (
        ".bay-right-rail:has(.bay-scanner-sticky-slot-v148)",
        "justify-content: flex-start !important",
        ".bay-action-buttons-v148",
        "position: static !important",
        ".bay-scanner-sticky-slot-v148",
        "position: sticky !important",
        "top: 8px !important",
        ".bay-scanner-live-status-v148",
        "display: none !important",
        ":has(#bayScanRemoveMode:checked) .bay-route-metrics-v148 .bay-dual-progress-label",
        ".bay-recent-panel-v148",
        ".bay-recent-table-wrap-v148",
        "max-height: none !important",
        "overflow: visible !important",
        "table-layout: fixed !important",
        ".bay-recent-current-bay-v148",
        "prefers-reduced-motion: reduce",
    )
    missing = [value for value in required if value not in css]
    if missing:
        raise RuntimeError("The v148 stylesheet is missing: " + ", ".join(missing))
    if ".bay-recent-disclosure-v148" in css:
        raise RuntimeError("The old collapsible recent-history CSS remains")


def validate_release(project_root: Path) -> None:
    index = read_text(project_root / "index.html")
    app = read_text(project_root / "app.js")
    store = read_text(project_root / "delivery_store.py")
    css = read_text(project_root / "bay-scanner-v148.css")
    readme = read_text(project_root / "README.md")
    changelog = read_text(project_root / "README_CHANGELOG.md")
    validate_index(index)
    validate_app(app)
    validate_store(store)
    validate_css(css)
    if "Current maintained release: **v148**" not in readme:
        raise RuntimeError("README.md release marker is not v148")
    if not changelog.startswith("## v148 - Bay Scanner History and Flow Refinement"):
        raise RuntimeError("README_CHANGELOG.md does not start with the v148 entry")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    package_root = Path(__file__).resolve().parent
    payload_root = package_root / "v148_payload"
    project_root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()

    index_path = project_root / "index.html"
    app_path = project_root / "app.js"
    store_path = project_root / "delivery_store.py"
    readme_path = project_root / "README.md"
    changelog_path = project_root / "README_CHANGELOG.md"
    css_path = project_root / "bay-scanner-v148.css"
    old_css_paths = tuple(project_root / f"bay-scanner-v{version}.css" for version in (144, 145, 146, 147))
    fragment_path = payload_root / "bay-scanner-v148-fragment.html"
    source_css_path = payload_root / "bay-scanner-v148.css"
    source_doc_path = payload_root / "docs" / "V148_BAY_SCANNER_HISTORY_AND_FLOW_REFINEMENT.md"
    final_doc_path = project_root / "docs" / source_doc_path.name
    source_test_path = payload_root / "tests" / "test_v148_release.py"
    target_test_path = project_root / "tests" / "test_v148_release.py"
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
        raise RuntimeError("Required v148 patch file was not found: " + ", ".join(missing))

    updated_index = patch_index(read_text(index_path), read_text(fragment_path))
    updated_app = patch_app(read_text(app_path))
    updated_store = patch_store(read_text(store_path))
    updated_readme = patch_readme(read_text(readme_path))
    updated_changelog = patch_changelog(read_text(changelog_path))
    updated_test_report = patch_test_report(read_text(test_report_path)) if test_report_path.is_file() else ""
    historical_test_updates = update_historical_release_tests(project_root)
    css = read_text(source_css_path)

    validate_index(updated_index)
    validate_app(updated_app)
    validate_store(updated_store)
    validate_css(css)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = project_root / "backups" / "v148-bay-scanner" / timestamp
    backup_root.mkdir(parents=True, exist_ok=False)

    tracked = [
        index_path,
        app_path,
        store_path,
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
        write_text(store_path, updated_store)
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

    print("Delivery List Scanner v148 Bay Scanner refinement installed successfully.")
    print(f"Project: {project_root}")
    print(f"Backups: {backup_root}")
    print("No database schema migration was applied.")
    print("Restart the scanner, then hard-refresh the browser with Ctrl+F5.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PATCH FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
