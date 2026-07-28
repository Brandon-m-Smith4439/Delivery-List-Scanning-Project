from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import re
import sys

from bs4 import BeautifulSoup
import tinycss2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database_migrations import MIGRATIONS


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_release_cache_markers_and_new_pages_are_wired():
    html = read("index.html")
    assert "20260728-v147" in html
    assert "notification-center-v135.js" in html
    assert "notification-center-ui.js" not in html
    assert 'data-page-target="rejects"' in html
    assert 'id="rejectsPage"' in html
    assert 'id="rackPackingHistoryBtn"' in html
    assert 'id="operationsModal"' in html
    assert "Delivery Automation Control Center" in html
    assert 'id="rejectLogOpenBtn"' in html and 'data-permission-any="scan,manual_adjust,resolve_exceptions"' in html


def test_html_ids_are_unique():
    soup = BeautifulSoup(read("index.html"), "html.parser")
    ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
    duplicates = [value for value, count in Counter(ids).items() if count > 1]
    assert duplicates == []


def test_frontend_contains_requested_workflow_owners():
    app = read("app.js")
    notification = read("notification-center-v135.js")
    required_app_markers = (
        "function openRackDetailsModal",
        "function openPackingHistoryModal",
        "function refreshRejectPage",
        "function submitManualOrderForm",
        "function renderAdminImportRunBrowser",
        "function openImportNotificationRun",
        "function applyOperationalLineFlags",
        "todayStaging",
        "internal-reject-ribbon",
        "manualOnly",
        'title="${escapeHtml(item.scanned)} scanned of ${escapeHtml(item.qty)}"',
    )
    for marker in required_app_markers:
        assert marker in app
    assert "event.stopImmediatePropagation();" in app
    assert "Review Updates" in notification
    assert "Mark Reviewed" in notification
    assert "noticeIds: flags.noticeIds" in notification
    assert "flagsByList.clear();" in notification
    assert "options.render !== false" in notification


def test_css_has_clean_owner_note_balanced_braces_and_no_exact_duplicate_rules():
    css = read("styles.css")
    assert "v136 CSS ownership rules" in css
    assert css.count("{") == css.count("}")
    parsed = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
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
                header = f"@{rule.at_keyword} {tinycss2.serialize(rule.prelude).strip()}"
                walk(nested, f"{context}|{header}")

    walk(parsed)
    assert duplicates == []


def test_v135_schema_contract_and_existing_migration_checksums_are_stable():
    assert [migration.version for migration in MIGRATIONS] == [1, 2, 3, 4]
    expected = {
        1: "9892a24ebc2fce637a087c4927010f660d11510cb5e4bd20330c4b3df21f08dd",
        2: "b2933ab902109c77979b0021e8d469e22d9e9e33796e9ae7a7d146626b86238e",
        3: "50cb440854d3b0d9167297691aa28838a6480d25c8823f52f99ca1a700c75935",
    }
    assert {migration.version: migration.checksum for migration in MIGRATIONS[:3]} == expected
    contract = read("database_contract.py")
    assert 'APPLICATION_VERSION = "135"' in contract
    assert "CURRENT_SCHEMA_VERSION = 4" in contract
    for table in ("reject_events", "packing_list_prints", "manual_delivery_entries"):
        assert f'"{table}"' in contract
    migrations_text = read("database_migrations.py")
    manual_column_call = '_ensure_column(connection, "line_items", "manual_only"'
    assert migrations_text.count(manual_column_call) == 1
    assert 'before-v{APPLICATION_VERSION}' in migrations_text
    migrations_text = read("database_migrations.py")
    manual_column_call = '_ensure_column(connection, "line_items", "manual_only"'
    assert migrations_text.count(manual_column_call) == 1
    assert 'before-v{APPLICATION_VERSION}' in migrations_text


def test_patch_inserts_server_routes_once_and_compiles():
    patch_path = ROOT / "Apply-v135-OperationsPatch.py"
    spec = importlib.util.spec_from_file_location("v135_patch_release", patch_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    source = '''from delivery_import_safety import install_safe_delivery_import\n\nROOT = object()\nCONFIG = object()\nSTORE = object()\nDELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG, STORE)\n\nclass Handler:\n    def do_GET(self):\n        parsed = object()\n        if parsed.path == "/api/admin/delivery-automation":\n            return\n\n    def do_POST(self):\n        parsed = object()\n        data = {}\n        try:\n            if parsed.path == "/api/scans":\n                return\n        except Exception:\n            return\n'''
    updated = source
    updated = module.replace_once(updated, module.IMPORT_ANCHOR, module.IMPORT_BLOCK, "import")
    updated = module.replace_once(updated, module.GLOBAL_ANCHOR, module.GLOBAL_BLOCK, "service")
    updated = module.replace_once(updated, module.GET_ANCHOR, module.GET_BLOCK, "get")
    updated = module.replace_once(updated, module.POST_ANCHOR, module.POST_BLOCK, "post")
    compile(updated, "server.py", "exec")
    assert updated.count(module.MARKER) == 1
    assert updated.count("/api/rejects") >= 2
    assert updated.count("/api/operations/line-flags") >= 2


def test_changed_files_do_not_include_live_data_or_secrets():
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".env", ".log"}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] in {"__pycache__", ".pytest_cache"}:
            continue
        assert path.suffix.lower() not in forbidden_suffixes, str(relative)
