#!/usr/bin/env python3
"""Install the v147 Bay Scanner containment refinement over a v146 scanner project.

The patch is browser-only. It removes unnecessary header copy, keeps Route Pulse
fully contained, hides Destination Control while Remove is selected, and moves only
the scanner panel higher when sticky. The Bay Map action buttons remain non-sticky.
API routes, database code, permissions, scan rules, and event handlers are preserved.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

RELEASE = 147
CACHE_KEY_NEW = "20260728-v147"
CACHE_KEYS_OLD = ("20260728-v146", "20260728-v145", "20260727-v144", "20260727-v143")
MARKER = "bay-scanner-panel-v147"

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

Current maintained release: **v147**. SQLite remains the active/default backend.

v147 tightens the Bay Map scanner after floor review. The blue header now contains only the Bay Scanner title, live state, and a fully contained Route Pulse. Remove mode hides Destination Control, legacy route connector graphics are suppressed, and only the scanner panel sticks near the top after the Bay Map action buttons scroll away.

## Install v147 over v146

1. Close the Delivery List Scanner server.
2. Extract `Delivery_List_Scanner_v147_Bay_Scanner_Containment_Refinement_Changed_Files.zip` into the current v146 project folder and replace the included files.
3. Run `Apply-v147-BayScannerContainmentRefinement.bat` once.
4. Restart the scanner normally.
5. Hard-refresh the browser once with `Ctrl+F5` so the `20260728-v147` cache keys take effect.

No database migration or backend patch is required. Keep the existing v142 role-management and v135 operations patches already installed.

## v147 highlights

- Removed `Indian Trail receiving`, the header workflow sentence, and the visible Current Mode card.
- Kept the Bay Scanner title and Route Pulse inside one continuous blue header.
- Recolored Route Pulse metrics with restrained dark-blue surfaces instead of bright white controls.
- Removed the inherited dotted connector and arrow that crossed the Route Pulse section.
- Added strict paint and width containment so Route Pulse remains inside the rounded panel.
- Hid Destination Control whenever Remove is selected and restored it immediately for Add mode.
- Moved only the sticky scanner panel to an 8-pixel top offset; Bay Map action buttons remain non-sticky.
- Preserved barcode scanning, Undo/Redo, Manual Scan, All Scans, recent history, location correction, permissions, API calls, and scan behavior.
- No PNG previews were generated or packaged.

"""

CHANGELOG_ENTRY = """## v147 - Bay Scanner Route and Sticky Refinement

### Bay Map scanner

- Removed the redundant receiving eyebrow, workflow sentence, and visible Current Mode summary from the blue header.
- Kept the Bay Scanner title, live scan status, and Route Pulse in one continuous header surface.
- Replaced bright Route Pulse surfaces with contained dark-blue metric cards.
- Suppressed the legacy dotted transit connector, arrow, and inherited white transit pill styling.
- Added paint containment to prevent Route Pulse elements from drawing outside the panel.
- Hid Destination Control in Remove mode while preserving it for Add mode.
- Changed only the scanner slot to `position: sticky` with an 8-pixel top offset; the Bay Map action toolbar remains in normal flow.
- Advanced browser cache keys to v147.

### Safety and validation

- No API route, database schema, permission, scan rule, or backend workflow was changed.
- Added v147 release checks for removed header copy, hidden mode summary, route pseudo-element suppression, dark route surfaces, mode-controlled Destination Control, sticky ownership, unique IDs, cache markers, and CSS integrity.

"""

TEST_REPORT_ENTRY = """## v147 Bay Scanner route and sticky verification

- Verified the removed header copy and visible Current Mode card are absent from the rendered scanner.
- Verified Route Pulse is nested inside the blue header, uses dark contained surfaces, and suppresses legacy connector pseudo-elements.
- Verified Destination Control is hidden by Remove mode and shown by Add mode.
- Verified the scanner slot alone is sticky at 8 pixels while the Bay Map action toolbar remains static.
- Verified required Bay Scanner IDs remain unique and no database/backend files are changed.

"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def replace_scanner(index_text: str, fragment: str) -> str:
    start_markers = (
        '            <div class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v147">',
        '            <div class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v146">',
        '            <div class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v145">',
        '            <div class="bay-scanner-sticky-slot bay-scanner-sticky-slot-v144">',
        '            <div class="bay-scanner-sticky-slot">',
    )
    starts = [index_text.find(marker) for marker in start_markers]
    starts = [position for position in starts if position >= 0]
    if not starts:
        raise RuntimeError("Could not locate the Bay Scanner sticky slot in index.html")

    start = min(starts)
    end_marker = '          <section class="bay-detail-panel bay-detail-panel-v2">'
    end = index_text.find(end_marker, start)
    if end < 0:
        raise RuntimeError("Could not locate the Bay Map detail-panel anchor after the scanner")

    return index_text[:start] + fragment.rstrip() + "\n\n" + index_text[end:]


def patch_action_toolbar(index_text: str) -> str:
    pattern = re.compile(
        r'class="bay-action-buttons\s+bay-action-buttons-v2(?:\s+bay-action-buttons-v\d+)?"\s+id="bayActionButtons"'
    )
    replacement = 'class="bay-action-buttons bay-action-buttons-v2 bay-action-buttons-v147" id="bayActionButtons"'
    updated, count = pattern.subn(replacement, index_text, count=1)
    if count != 1:
        raise RuntimeError("Could not locate the Bay Map action-button toolbar")
    return updated


def patch_stylesheet_link(index_text: str) -> str:
    existing_pattern = re.compile(r'<link rel="stylesheet" href="bay-scanner-v\d+\.css\?v=[^"]+">')
    if existing_pattern.search(index_text):
        return existing_pattern.sub(
            f'<link rel="stylesheet" href="bay-scanner-v147.css?v={CACHE_KEY_NEW}">',
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
    addition = line + f'\n{indent}<link rel="stylesheet" href="bay-scanner-v147.css?v={CACHE_KEY_NEW}">'
    return index_text[: match.start()] + addition + index_text[match.end() :]


def patch_index(index_text: str, fragment: str) -> str:
    updated = patch_stylesheet_link(index_text)
    updated = patch_action_toolbar(updated)
    updated = replace_scanner(updated, fragment)
    for old_key in CACHE_KEYS_OLD:
        updated = updated.replace(old_key, CACHE_KEY_NEW)
    return updated


def patch_app(app_text: str) -> str:
    updated = app_text
    for sentence in REMOVED_TARGET_COPY:
        updated = updated.replace(f'"{sentence}"', '""')
        updated = updated.replace(f"'{sentence}'", "''")
    return updated


def patch_readme(readme: str) -> str:
    markers = ("## v146 highlights", "## v145 highlights", "## v144 highlights", "## v143 highlights")
    marker_index = -1
    for marker in markers:
        marker_index = readme.find(marker)
        if marker_index >= 0:
            break
    if marker_index < 0:
        raise RuntimeError("README.md does not contain the expected previous-release highlights anchor")

    updated = README_PREFIX + readme[marker_index:]
    doc_line = "- v147 Bay Scanner route and sticky refinement: `docs/V147_BAY_SCANNER_CONTAINMENT_AND_STICKY_REFINEMENT.md`"
    if doc_line not in updated:
        docs_anchor = "- Ongoing version history: `README_CHANGELOG.md`"
        if docs_anchor not in updated:
            raise RuntimeError("README.md project documentation list was not found")
        updated = updated.replace(docs_anchor, docs_anchor + "\n" + doc_line, 1)
    return updated


def patch_changelog(changelog: str) -> str:
    if changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement"):
        return changelog
    return CHANGELOG_ENTRY + changelog.lstrip()


def patch_test_report(report: str) -> str:
    if "## v147 Bay Scanner route and sticky verification" in report:
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
        updated = re.sub(
            r'assert\s+(["\'])2026072[78]-v\d+\1\s+in\s+',
            'assert "20260728-v147" in ',
            updated,
        )
        updated = re.sub(
            r'assert\s+([A-Za-z_][A-Za-z0-9_]*)\.count\((["\'])2026072[78]-v\d+\2\)',
            r'assert \1.count("20260728-v147")',
            updated,
        )
        updated = re.sub(
            r'assert\s+(["\'])Current maintained release: \*\*v\d+\*\*\1\s+in\s+',
            'assert "Current maintained release: **v147**" in ',
            updated,
        )
        updated = re.sub(
            r'assert\s+changelog\.startswith\((["\'])## v\d+ -[^"\']*\1\)',
            'assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")',
            updated,
        )

        # v145 and v146 owned the same Bay Scanner surface now superseded by v147.
        # Keep their useful historical assertions active by retargeting only their
        # current-owner class/file references; historical release-note paths remain unchanged.
        if test_path.name == "test_v145_release.py":
            updated = updated.replace("v145", "v147").replace("v146", "v147")
            updated = updated.replace("top: 68px !important", "top: 8px !important")
            updated = updated.replace("top: 60px !important", "top: 8px !important")
            updated = updated.replace(
                'assert changelog.startswith("## v147 - Bay Scanner Layout Correction")',
                'assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")',
            )
        elif test_path.name == "test_v146_release.py":
            updated = updated.replace("v146", "v147")
            updated = updated.replace(
                'assert changelog.startswith("## v147 - Bay Scanner Workflow Refinement")',
                'assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")',
            )

        if updated != original:
            updates[test_path] = updated
    return updates


def validate_index(index_text: str) -> None:
    if MARKER not in index_text:
        raise RuntimeError("The v147 Bay Scanner ownership marker is missing")
    if f'bay-scanner-v147.css?v={CACHE_KEY_NEW}' not in index_text:
        raise RuntimeError("The v147 Bay Scanner stylesheet is not linked")
    if re.search(r'bay-scanner-v(?:144|145|146)\.css', index_text):
        raise RuntimeError("A previous Bay Scanner stylesheet link remains in index.html")
    if "bay-action-buttons-v147" not in index_text:
        raise RuntimeError("The v147 Bay Map action-toolbar owner is missing")
    if any(old_key in index_text for old_key in CACHE_KEYS_OLD):
        raise RuntimeError("A previous browser cache key remains in index.html")

    ids = re.findall(r'\bid="([^"]+)"', index_text)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise RuntimeError("Duplicate HTML IDs after patch: " + ", ".join(duplicates[:12]))

    missing = sorted(value for value in REQUIRED_IDS if ids.count(value) != 1)
    if missing:
        raise RuntimeError("Required Bay Scanner IDs are missing or duplicated: " + ", ".join(missing))

    panel_start = index_text.find('class="scanner-panel bay-scanner-panel bay-scanner-panel-v147"')
    panel_end = index_text.find('<section class="bay-detail-panel', panel_start)
    panel_text = index_text[panel_start:panel_end]
    header_start = panel_text.find('<header class="bay-scanner-header-v147">')
    route_start = panel_text.find('<section class="bay-route-pulse-v147"')
    form_start = panel_text.find('id="bayScanOutForm"')
    header_close = panel_text.find('</header>\n\n                <form', header_start)
    if min(panel_start, panel_end, header_start, route_start, form_start, header_close) < 0:
        raise RuntimeError("Could not verify the v147 Bay Scanner header and form structure")
    if not (header_start < route_start < header_close < form_start):
        raise RuntimeError("Route Pulse must be nested inside the combined blue header")

    scan_surface_start = panel_text.find('class="bay-command-scan-input-v147"')
    scan_surface_end = panel_text.find('</span>\n                      </div>', scan_surface_start)
    scan_surface = panel_text[scan_surface_start:scan_surface_end]
    if 'id="bayUndoBtn"' not in scan_surface or 'id="bayRedoBtn"' not in scan_surface:
        raise RuntimeError("Undo and Redo must be inside the barcode scan surface")

    if "Submit Scan" in panel_text or "bay-scan-submit-v147" in panel_text:
        raise RuntimeError("The redundant barcode Submit Scan control remains")
    if '<small id="bayScannerTargetState"></small>' not in panel_text:
        raise RuntimeError("The Remove-mode target guidance must be empty in static markup")
    if "Finds the piece's current bay" not in panel_text:
        raise RuntimeError("The corrected Remove-mode copy is missing")
    if any(sentence in panel_text for sentence in REMOVED_TARGET_COPY):
        raise RuntimeError("Removed target guidance remains in the Bay Scanner markup")
    for removed_copy in (
        "Indian Trail receiving",
        "Choose the action, confirm the bay, and scan the piece.",
        "Current mode",
    ):
        if removed_copy in panel_text:
            raise RuntimeError(f"Removed header copy remains visible: {removed_copy}")
    if 'class="bay-scanner-mode-summary-v147" hidden' not in panel_text:
        raise RuntimeError("The compatibility mode summary must remain hidden")
    if 'class="bay-command-target-v147"' not in panel_text:
        raise RuntimeError("Destination Control must remain available for Add mode")
    if 'maxlength="3"' not in panel_text or 'pattern="[0-9]{1,3}"' not in panel_text:
        raise RuntimeError("Manual Item must be limited to three numeric characters")
    if "bay-manual-disclosure" in panel_text:
        raise RuntimeError("The old collapsible Manual Entry workflow remains")


def validate_app(app_text: str) -> None:
    remaining = [sentence for sentence in REMOVED_TARGET_COPY if sentence in app_text]
    if remaining:
        raise RuntimeError("Removed target guidance remains in app.js: " + ", ".join(remaining))


def validate_css(css_text: str) -> None:
    if css_text.count("{") != css_text.count("}"):
        raise RuntimeError("bay-scanner-v147.css has unbalanced braces")
    required = (
        ".bay-action-buttons-v147",
        "position: static !important",
        "top: auto !important",
        ".bay-scanner-sticky-slot-v147",
        "top: 8px !important",
        ".bay-scanner-panel-v147",
        ".bay-scanner-heading-line-v147",
        ".bay-route-pulse-v147",
        "contain: layout paint",
        ".bay-route-metrics-v147 .bay-panel-route-lane::before",
        "content: none !important",
        "background: rgba(3, 23, 55, 0.38) !important",
        ".bay-scanner-panel-v147:has(#bayScanRemoveMode:checked) .bay-command-target-v147",
        ".bay-scanner-panel-v147:has(#bayScanModeToggle:checked) .bay-command-target-v147",
        ".bay-command-history-overlay-v147",
        "top: -15px !important",
        ".bay-manual-inline-v147",
        "grid-template-columns: minmax(150px, 1fr) 78px 92px !important",
        "prefers-reduced-motion: reduce",
    )
    missing = [value for value in required if value not in css_text]
    if missing:
        raise RuntimeError("The v147 stylesheet is missing: " + ", ".join(missing))
    if "top: 68px !important" in css_text or "top: 60px !important" in css_text:
        raise RuntimeError("An older low sticky position remains in the v147 stylesheet")
    if ".bay-scan-submit-v147" in css_text:
        raise RuntimeError("The v147 stylesheet still owns a removed barcode submit button")


def validate_release(project_root: Path) -> None:
    index_text = read_text(project_root / "index.html")
    app_text = read_text(project_root / "app.js")
    readme = read_text(project_root / "README.md")
    changelog = read_text(project_root / "README_CHANGELOG.md")
    css = read_text(project_root / "bay-scanner-v147.css")

    validate_index(index_text)
    validate_app(app_text)
    validate_css(css)
    if "Current maintained release: **v147**" not in readme:
        raise RuntimeError("README.md release marker is not v147")
    if not changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement"):
        raise RuntimeError("README_CHANGELOG.md does not start with the v147 route/sticky entry")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parent),
        help="Current Delivery List Scanner project folder (defaults to this script's folder)",
    )
    args = parser.parse_args()

    package_root = Path(__file__).resolve().parent
    payload_root = package_root / "v147_payload"
    project_root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()

    index_path = project_root / "index.html"
    app_path = project_root / "app.js"
    readme_path = project_root / "README.md"
    changelog_path = project_root / "README_CHANGELOG.md"
    css_path = project_root / "bay-scanner-v147.css"
    old_css_paths = (
        project_root / "bay-scanner-v146.css",
        project_root / "bay-scanner-v145.css",
        project_root / "bay-scanner-v144.css",
    )
    fragment_path = payload_root / "bay-scanner-v147-fragment.html"
    source_css_path = payload_root / "bay-scanner-v147.css"
    final_doc_path = project_root / "docs" / "V147_BAY_SCANNER_CONTAINMENT_AND_STICKY_REFINEMENT.md"
    source_doc_path = payload_root / "docs" / "V147_BAY_SCANNER_CONTAINMENT_AND_STICKY_REFINEMENT.md"
    source_test_path = payload_root / "tests" / "test_v147_release.py"
    target_test_path = project_root / "tests" / "test_v147_release.py"
    test_report_path = project_root / "docs" / "TEST_REPORT.md"

    required = (
        index_path,
        app_path,
        readme_path,
        changelog_path,
        fragment_path,
        source_css_path,
        source_doc_path,
        source_test_path,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Required v147 patch file was not found: " + ", ".join(missing))

    original_index = read_text(index_path)
    original_app = read_text(app_path)
    original_readme = read_text(readme_path)
    original_changelog = read_text(changelog_path)
    fragment = read_text(fragment_path)
    css_text = read_text(source_css_path)

    updated_index = patch_index(original_index, fragment)
    updated_app = patch_app(original_app)
    updated_readme = patch_readme(original_readme)
    updated_changelog = patch_changelog(original_changelog)
    historical_test_updates = update_historical_release_tests(project_root)
    updated_test_report = patch_test_report(read_text(test_report_path)) if test_report_path.is_file() else ""

    validate_index(updated_index)
    validate_app(updated_app)
    validate_css(css_text)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = project_root / "backups" / "v147-bay-scanner" / timestamp
    backup_root.mkdir(parents=True, exist_ok=False)

    tracked_targets = [
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
        tracked_targets.append(test_report_path)
    tracked_targets = list(dict.fromkeys(tracked_targets))

    existed: dict[Path, bool] = {}
    for path in tracked_targets:
        existed[path] = path.exists()
        if path.is_file():
            relative = path.relative_to(project_root)
            backup_path = backup_root / relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_path)

    try:
        write_text(index_path, updated_index)
        write_text(app_path, updated_app)
        write_text(readme_path, updated_readme)
        write_text(changelog_path, updated_changelog)
        for test_path, updated_test in historical_test_updates.items():
            write_text(test_path, updated_test)
        if test_report_path.is_file():
            write_text(test_report_path, updated_test_report)

        shutil.copy2(source_css_path, css_path)
        final_doc_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_doc_path, final_doc_path)
        target_test_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_test_path, target_test_path)

        for old_css_path in old_css_paths:
            if old_css_path.is_file() and old_css_path.resolve() != css_path.resolve():
                old_css_path.unlink()

        validate_release(project_root)
    except Exception:
        for path in tracked_targets:
            relative = path.relative_to(project_root)
            backup_path = backup_root / relative
            if backup_path.is_file():
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, path)
            elif not existed[path] and path.exists() and path.is_file():
                path.unlink()
        raise

    print("Delivery List Scanner v147 Bay Scanner containment refinement installed successfully.")
    print(f"Project: {project_root}")
    print(f"Backups: {backup_root}")
    print("No database migration or backend patch was applied.")
    print("Restart the scanner, then hard-refresh the browser with Ctrl+F5.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PATCH FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
