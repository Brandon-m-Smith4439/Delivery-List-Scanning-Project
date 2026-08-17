# File: tests/test_static_structure.py

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_index_local_assets_exist() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    references = re.findall(r'(?:href|src)="([^"]+)"', index)
    missing = []
    for reference in references:
        path_text = reference.split("?", 1)[0]
        if (
            not path_text
            or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path_text)
            or path_text.startswith("#")
        ):
            continue
        if not (ROOT / path_text).is_file():
            missing.append(path_text)
    assert not missing, f"Missing local assets: {missing}"


def test_page_stylesheets_are_present_and_balanced() -> None:
    css_dir = ROOT / "static" / "css"
    expected = {
        "styles.css",
        "shared-ui.css",
        "statistics.css",
        "rejects.css",
        "home.css",
        "scan.css",
        "racks.css",
        "bays.css",
        "admin.css",
        "print.css",
        "shell.css",
        "mobile.css",
    }
    assert {path.name for path in css_dir.glob("*.css")} == expected
    for path in css_dir.glob("*.css"):
        content = path.read_text(encoding="utf-8")
        assert content.count("{") == content.count("}"), path


def test_version_numbers_are_not_embedded_in_asset_filenames() -> None:
    versioned = []
    for folder in (ROOT / "static" / "css", ROOT / "static" / "js"):
        versioned.extend(path.name for path in folder.iterdir() if re.search(r"-v\d+", path.name))
    assert not versioned


def test_single_javascript_bundle_is_loaded() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script\s+src="([^"]+)"', index)
    assert scripts == ["static/js/app.js?v=20260817-v0.324"]
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "DELIVERY AUTOMATION CONTROL CENTER" in app
    assert "NOTIFICATION CENTER AND LINE UPDATE REVIEW" in app


def test_python_packages_are_organized() -> None:
    expected_backend = {
        "__init__.py",
        "automation_control.py",
        "config.py",
        "import_safety.py",
        "operations.py",
        "store.py",
    }
    expected_database = {
        "__init__.py",
        "azure_compat.py",
        "azure_schema.sql",
        "contract.py",
        "integrity.py",
        "migrations.py",
        "migrate_sqlite_to_azure_sql.py",
    }
    assert {path.name for path in (ROOT / "backend").iterdir() if path.is_file()} == expected_backend
    assert {path.name for path in (ROOT / "database").iterdir() if path.is_file()} == expected_database
    root_python_files = {path.name for path in ROOT.glob("*.py")}
    assert root_python_files == {"server.py", "scanner_config.py", "delivery_store.py"}
    assert "from backend.config import AppConfig, load_config" in (ROOT / "scanner_config.py").read_text(encoding="utf-8")
    assert "from backend.store import *" in (ROOT / "delivery_store.py").read_text(encoding="utf-8")


def test_deployment_files_are_organized() -> None:
    assert not (ROOT / "Dockerfile").exists()
    assert not (ROOT / ".env.azure.example").exists()
    assert (ROOT / ".dockerignore").is_file()
    assert (ROOT / "pytest.ini").is_file()
    assert (ROOT / "Start-DeliveryScannerWebApp.bat").is_file()
    assert (ROOT / "Start-DeliveryScannerWebApp.ps1").is_file()
    dockerfile = ROOT / "deployment" / "docker" / "Dockerfile"
    requirements = ROOT / "deployment" / "docker" / "requirements.txt"
    azure_example = ROOT / "deployment" / "azure" / "app-service.env.example"
    assert dockerfile.is_file()
    assert requirements.is_file()
    assert azure_example.is_file()
    assert "deployment/docker/requirements.txt" in dockerfile.read_text(encoding="utf-8")


def test_v154_admin_reject_management_and_scan_ribbon() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    rejects_css = (ROOT / "static" / "css" / "rejects.css").read_text(encoding="utf-8")

    assert "def require_admin_role" in server
    assert 'parsed.path == "/api/rejects/update"' in server
    assert 'parsed.path == "/api/rejects/delete"' in server
    assert "def update_reject" in operations
    assert "def delete_reject" in operations
    assert 'data-reject-edit=' in app
    assert 'data-reject-delete=' in app
    assert 'class="internal-reject-detail-row-v154"' in app
    assert '<td colspan="6">' in app
    assert 'class="internal-reject-detail-tail-v154" colspan="4"' in app
    assert ".internal-reject-incident-strip-v154" in scan_css
    assert ".reject-edit-form-v154" in rejects_css


def test_scan_time_pill_qty_headers_and_table_are_width_safe() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    ribbon_start = app.index('internal-reject-incident-strip-v154')
    ribbon_end = app.index("</div>", ribbon_start)
    ribbon_markup = app[ribbon_start:ribbon_end]
    assert "Delivery</small>" not in ribbon_markup
    assert "internal-reject-incident-count-v154" not in ribbon_markup
    assert "internal-reject-incident-notes-v154" not in ribbon_markup
    assert 'colspan="6"' in app
    assert 'colspan="4"' in app

    assert "table-layout: fixed" in scan_css
    assert "width: 100%" in scan_css
    assert ".scan-page .delivery-table td.location-cell {\n  width: 8%" in scan_css
    assert ".scan-page .delivery-table td:nth-child(10) {\n  width: 11%" in scan_css
    assert "overflow-wrap: anywhere" in scan_css

    render_start = app.index("function renderItemRow(item)")
    render_end = app.index("function renderTable()", render_start)
    render_markup = app[render_start:render_end]
    assert 'class="last-scan-pill-v157"' in render_markup
    assert 'has-scan-time-pill-v157' in render_markup
    assert 'class="scan-time-detail-row-v156"' not in render_markup
    assert 'data-line-detail-ribbon="scan"' not in render_markup
    assert 'class="qty-value-v156"' in render_markup
    assert 'class="qty-pill ${status}"' not in render_markup
    assert ".last-scan-pill-v157" in scan_css
    assert "width: calc(177.7778% - 22px)" in scan_css
    assert "<th>Item</th>" in index
    assert "<th>Progress</th>" in index
    assert "<th>Item Nr.</th>" not in index[index.index('<table class="delivery-table">'):index.index('</table>', index.index('<table class="delivery-table">'))]
    assert "<th>Process State</th>" not in index[index.index('<table class="delivery-table">'):index.index('</table>', index.index('<table class="delivery-table">'))]
    assert "static/css/scan.css?v=20260817-v0.324" in index
    assert "static/js/app.js?v=20260817-v0.324" in index


def test_v158_core_page_polish_and_scan_geometry() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    styles = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    home = (ROOT / "static" / "css" / "home.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    assert "13. v158 shared workspace visual system" in styles
    assert "v158 Home dashboard visual polish" in home
    assert "18. v158 Scan workspace visual polish" in scan
    assert "v158 Rack workspace visual polish" in racks
    assert "v158 Administration workspace visual polish" in admin
    assert "width: calc(177.7778% - 22px)" in scan
    assert "tr.has-scan-time-pill-v157 > td.job-cell-v157" in scan
    assert ".delivery-table td:nth-child(7) {\n  width: 7%" in scan
    assert ".delivery-table td:nth-child(8) {\n  width: 6%" in scan
    assert ".delivery-table td.location-cell {\n  width: 8%" in scan
    assert "width: calc(100% - 2px)" not in scan
    assert "padding-right: 2px" not in scan
    expected_asset_keys = {
        "styles": "20260817-v0.324",
        "home": "20260817-v0.324",
        "scan": "20260817-v0.324",
        "racks": "20260817-v0.324",
        "admin": "20260817-v0.324",
    }
    for name, cache_key in expected_asset_keys.items():
        assert f"static/css/{name}.css?v={cache_key}" in index
    assert "static/js/app.js?v=20260817-v0.324" in index


def test_admin_control_center_modal_structure() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'static/css/admin.css?v=20260817-v0.324' in index
    for element_id in (
        "adminModalEyebrow",
        "adminModalDescription",
        "adminModalStatusText",
    ):
        assert f'id="{element_id}"' in index
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "ADMIN_MODAL_PROFILES" in app
    assert "applyAdminModalProfile(kind, options)" in app
    for kind in (
        "deliveryLists", "deliveryActions", "manualEdit", "users", "roles",
        "sessions", "stations", "customerRoutes", "customerEmails", "lookups",
        "rejectSettings", "bayScannerRules", "bayAutoAssigner", "crossDateScanning", "racks",
        "rackForm", "rackSetForm", "recentScans",
    ):
        assert f"{kind}: {{" in app
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    assert "v160 Administration Control Center modal system" in css
    assert ".admin-modal-context-strip" not in css


def test_v161_scan_timestamp_rack_status_and_rack_control_centers() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")

    assert "static/css/scan.css?v=20260817-v0.324" in index
    assert "static/css/racks.css?v=20260817-v0.324" in index
    assert "static/js/app.js?v=20260817-v0.324" in index
    for element_id in (
        "operationsModalDescription",
        "operationsModalStatusText",
    ):
        assert f'id="{element_id}"' in index

    assert "date: `${parsed.getMonth() + 1}/${parsed.getDate()}`" in app
    assert '.replace(/\\s+/g, "")' in app
    assert '.toLowerCase()' in app
    assert '`${state.meta.stage} • ${dateText}`' in app
    assert 'class="rack-board-card ${rackVisualClass(rack)}"' in app
    assert 'aria-current="${selected ? "true" : "false"}"' in app
    assert 'class="rack-board-card ${rackVisualClass(rack)} ${selected ? "is-selected" : ""}"' not in app
    assert '"rack-details": {' in app
    assert '"packing-history": {' in app
    assert 'classList.toggle("is-control-center", controlCenter)' in app

    assert "tr.has-scan-time-pill-v157 > td:nth-child(-n + 3)" not in scan
    assert "tr.has-scan-time-pill-v157 > td.job-cell-v157" in scan
    assert "v161 Rack Control Center dialogs and status-safe selection" in racks
    assert '#operationsModal.is-control-center' in racks
    assert '#operationsModal[data-kind="rack-details"]' in racks
    assert '#operationsModal[data-kind="packing-history"]' in racks
    assert '#adminModal[data-kind="racks"]' in racks


def test_v162_scan_typography_and_control_center_layering_repair() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    assert "static/css/scan.css?v=20260817-v0.324" in index
    assert "static/css/racks.css?v=20260817-v0.324" in index
    assert "static/css/admin.css?v=20260817-v0.324" in index
    assert "static/js/app.js?v=20260817-v0.324" in index

    assert ".last-scan-pill-v157 > :is(span, b, em)" in scan
    assert "font-size: 11.5px" in scan
    assert "width: 8%;\n  min-width: 0;" in scan
    assert "grid-template-rows: minmax(118px, auto) minmax(0, 1fr) !important" in admin
    assert "#adminModal > .admin-control-center-header" in admin
    assert "grid-row: 2" in admin
    assert "width: 42px !important" in admin
    assert "grid-template-rows: minmax(126px, auto) minmax(0, 1fr) !important" in racks
    assert "#operationsModal.is-control-center > .operations-modal-heading" in racks
    assert "#operationsModal.is-control-center #operationsModalBody" in racks
    assert "color: #fff !important" in racks


def test_v163_modal_hidden_state_and_close_repair() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    assert "static/css/racks.css?v=20260817-v0.324" in index
    assert "static/css/admin.css?v=20260817-v0.324" in index
    assert "static/js/app.js?v=20260817-v0.324" in index
    assert 'id="adminModal" aria-hidden="true" hidden' in index
    assert 'id="operationsModal" aria-hidden="true" hidden' in index

    assert "#adminModal[hidden]" in admin
    assert "#adminModalBackdrop[hidden]" in admin
    assert "#operationsModal[hidden]" in racks
    assert "#operationsModalBackdrop[hidden]" in racks
    assert 'els.adminModal.setAttribute("aria-hidden", "true")' in app
    assert 'els.operationsModal.classList.remove("is-control-center")' in app
    assert "els.adminModalBody.replaceChildren()" in app
    assert "els.operationsModalBody.replaceChildren()" in app


def test_v164_simplified_gui_headers_and_automation_action() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")

    assert "static/css/admin.css?v=20260817-v0.324" in index
    assert "static/css/racks.css?v=20260817-v0.324" in index
    assert "static/js/app.js?v=20260817-v0.324" in index
    assert 'id="folderImportBtn" class="link-button admin-automation-link"' in index
    assert "Edit automated DL import" in index
    assert index.index("Edit automated DL import") < index.index("Edit delivery lists")
    assert "Live scanner data" not in index
    assert "Changes are audited" not in index
    assert "adminModalContextLabel" not in index
    assert "operationsModalContextLabel" not in index
    assert ".admin-modal-context-strip" not in admin
    assert ".operations-modal-context-strip" not in racks
    assert "grid-template-rows: minmax(118px, auto) minmax(0, 1fr) !important" in admin
    assert "grid-template-rows: minmax(126px, auto) minmax(0, 1fr) !important" in racks
    assert "Edit automated DL import" in app
    assert "delivery-automation-tabs" in app


def test_v165_manual_edit_history_and_rack_override() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")

    assert "manualEditFilterDrawerHtml" in app
    assert "data-manual-order-toggle" in app
    assert "/api/admin/action-history" in app
    assert "destinationOverrideMinutes" in app
    assert "logicalUpdatedCount" in store
    assert "stageRecordCount" in store
    assert "affectedListIds" in store
    assert "start_rack_destination_override_window" in store
    assert "apply_rack_destination_override_window" in store
    assert "destination_override_until" in store
    assert "ensure_rack_destination_override_columns" in store
    assert "update_bay_scan_settings" in store
    assert 'parsed.path == "/api/admin/action-history"' in server
    assert 'parsed.path == "/api/admin/bay-scanner-rules/settings"' in server
    assert 'id="adminModalHistory"' in html
    assert 'id="operationsModalHistory"' in html
    assert "manual-edit-modal-tools" in admin_css
    assert "modal-action-history" in admin_css
    assert "operations-action-history" in racks_css
    assert "20260803-v0.196" in html


def test_v166_manual_route_and_admin_gui_refinement() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'value = canonical or "INDIAN TRAIL"' in store
    assert 'payload["updatedItem"] = updated_item or {}' in store
    assert 'route_aliases = {' in store
    assert '_manualEditFilterMismatch: true' in app
    assert 'manualEditRouteSelectionValue' in app
    assert 'setAdminModalSection' in app
    assert 'data-admin-modal-section="workspace"' in html
    assert 'data-admin-modal-section="history"' in html
    assert '.manual-edit-card.is-scanned' in admin_css
    assert 'position: fixed !important;' in admin_css
    assert '.admin-modal-section-tabs' in admin_css
    assert '#7d58bd' not in admin_css[admin_css.find('v158 Administration workspace visual polish'):admin_css.find('v160 Administration Control Center modal system')]
    assert '20260803-v0.196' in html



def test_v167_manual_route_and_new_order_workspace() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'return designation.route || "INDIAN TRAIL"' in app
    assert 'data.routeOverride = data.route' in app
    assert 'manualEditVisibleChoiceValue' in app
    assert 'data["route"] = data.get("routeOverride")' in store
    assert 'payload["routeApplied"]' in store
    assert 'grid-template-rows: auto auto auto minmax(0, 1fr)' in css
    assert '#adminModal[data-kind="manualEdit"] .manual-order-create-panel[open]' in css
    assert '20260803-v0.196' in html


def test_v168_manual_edit_exact_row_capture_repair() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "manualEditCollectRowData" in app
    assert "manualEditOriginalRowData" in app
    assert "manualEditChangedFields" in app
    assert "data-manual-edit-original" in app
    assert 'sourceButton?.closest("[data-edit-row]")' in app
    assert "data.clientChangedFields = clientChangedFields" in app
    assert "The row has been left open so the entered values are not lost." in app
    assert "saveManualLineItem(saveLineItemButton.dataset.saveLineItem, saveLineItemButton)" in app
    assert "static/js/app.js?v=20260817-v0.324" in html


def test_v169_manual_edit_glass_type_filters() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'manualEditGlassTypes: []' in app
    assert 'glassTypes: []' in app
    assert 'manualEditFilterButton("glassType"' in app
    assert 'Only glass types present in the selected delivery-list stage are shown.' in app
    assert 'params.append("glassType"' in app
    assert 'filterOptions: payload.filterOptions' in app
    assert '"glassTypes": [str(value).strip()' in server
    assert 'glass_type_expression' in store
    assert '"filterOptions": {' in store
    assert '"pieceQty": int(row["piece_qty"] or 0)' in store
    assert '.manual-edit-glass-filter-options' in css
    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html


def test_v193_guarded_cross_delivery_date_scanning() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    admin_css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '"v192_action_history_archive"' in migrations
    assert 'v193_' not in migrations

    assert 'parsed.path == "/api/admin/cross-date-scan-settings"' in server
    assert 'STORE.get_cross_date_scan_settings()' in server
    assert 'STORE.update_cross_date_scan_settings(data, user["username"])' in server
    assert 'data["_userContext"] = user' in server

    assert 'DEFAULT_CROSS_DATE_SCAN_MODE = "auto_unique"' in store
    assert 'DEFAULT_CROSS_DATE_SCAN_PAST_DAYS = 7' in store
    assert 'DEFAULT_CROSS_DATE_SCAN_FUTURE_DAYS = 30' in store
    assert 'def resolve_cross_date_scan' in store
    assert 'def cross_date_candidate_safety' in store
    assert 'def cross_date_scan_candidates' in store
    assert 'def _record_scan_for_list' in store
    assert 'def _receive_indian_trail_scan_for_list' in store
    assert 'cross_date_scan_match_found' in store
    assert 'cross_date_scan_switch' in store
    assert 'if resolved["candidate"].get("clearRack")' in store

    assert 'delivery_date_changed: "sounds/scan_success.wav"' in app
    assert 'function showCrossDateScanSelection' in app
    assert 'function applyCrossDateSwitchUi' in app
    assert 'function crossDateScanSettingsModalHtml' in app
    assert 'crossDateListId: options.crossDateListId || ""' in app
    assert 'crossDateConfirmed: Boolean(options.crossDateConfirmed)' in app
    assert 'crossDateScanning: {' in app
    assert '["Cross-Date Scanning", "Escaneo entre fechas"]' in app

    assert 'id="crossDateScanOverview"' in index
    assert 'data-admin-modal="crossDateScanning"' in index
    assert 'static/css/scan.css?v=20260817-v0.324' in index
    assert 'static/css/admin.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert '<strong>0.324</strong>' in index

    assert 'v0.193 guarded cross-delivery-date scanning' in scan_css
    assert '.cross-date-scan-dialog' in scan_css
    assert '.cross-date-switch-notice' in scan_css
    assert 'v0.193 cross-delivery-date scan settings' in admin_css
    assert '.cross-date-settings-shell' in admin_css

    assert 'Current maintained release: **v0.324**' in readme
    assert 'No database migration or separate setup script is required' in readme
    assert '## v0.193 - Guarded Cross-Delivery-Date Scanning' in changelog


def test_v194_exact_manual_scans_result_colors_sound_and_all_scans_history() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'strict_order_item: bool = False' in store
    assert 'strict_order_item=is_manual' in store
    assert 'No exact order/item match' in store
    assert 'and not is_manual' in store

    assert 'Manual scan order numbers must contain exactly six digits.' in app
    assert 'Manual scan item numbers must contain one to three digits.' in app
    assert 'recoverScan(scanText, { strictOrderItem: Boolean(options.isManual) })' in app
    assert 'function recoverScan(rawScan, { strictOrderItem = false } = {})' in app
    assert 'delivery_date_changed: "sounds/scan_success.wav"' in app
    assert 'scanFlash("notice", "scan_warning")' in app
    assert 'const actionHistoryEnabled = !["deliveryUpdatePreview", "recentScans"].includes(kind);' in app

    assert 'v0.194 exact manual scans and last-result status ownership' in scan_css
    assert '.scan-page .scanner-panel .last-card.ok' in scan_css
    assert '.scan-page .scanner-panel .last-card.error' in scan_css

    assert 'static/css/scan.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.194 - Exact Manual Scans and Result Feedback Repair' in changelog


def test_v195_print_export_filter_workspace_and_exact_preview() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'def summarize_print_package' in server
    assert 'parsed.path == "/api/print/package-preview"' in server
    assert 'STORE.get_print_package(' in server
    assert 'exact_filter_values("glassTypesExact")' in store
    assert 'glass_value in exact_glass_types' in store
    assert "function printSelectionFilters(" in app
    assert 'function buildFormattedPrintWorkbookBytes(' in app
    assert "JSON.stringify(printBackendSelectionPayload())" in app
    assert "state.printPreviewResult?.noResults" in app
    assert 'Selected filters yield 0 results. Adjust the Print / Export filters before continuing.' in app
    assert "## v0.195 - Print / Export Filter Workspace and Exact Preview" in changelog

def test_v196_scanner_panel_context_selectors() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    scan_heading = index[index.index('<div class="scan-heading">'):index.index('<main class="workspace">')]
    assert 'deliveryDateSelect' not in scan_heading
    assert 'deliveryStageSelect' not in scan_heading
    assert 'scan-heading-selectors-v195' not in scan_heading

    panel_start = index.index('<section class="progress-band scanner-summary-header"')
    panel_end = index.index('<section class="scan-rack-panel"', panel_start)
    panel = index[panel_start:panel_end]
    assert 'class="scanner-panel-context-row-v196"' in panel
    assert panel.index('id="deliveryDateSelect"') < panel.index('id="stationProfileDisplay"')
    assert panel.index('id="stationProfileDisplay"') < panel.index('id="deliveryStageSelect"')
    assert 'id="stageHeading"' not in panel
    assert '<span>Assigned station</span>' not in panel
    assert 'id="stationSelect" hidden' in panel

    assert 'stageHeading: document.getElementById("stageHeading")' not in app
    assert '`${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}`' not in app
    assert '${escapeHtml(scanStageLabel(list))}</option>`' in app
    assert 'return scanStageLabel(item);' in app

    assert 'v0.196 scanner-panel context selectors' in scan
    assert '.scanner-panel-context-row-v196' in scan
    assert '.scanner-panel-station-v196' in scan
    assert 'background: rgba(255, 255, 255, 0.07) !important' in scan

    assert 'static/css/scan.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert '<strong>0.324</strong>' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.196 - Scanner Panel Date, Station, and Stage Header' in changelog


def test_v197_print_export_document_preview_control_center() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    for element_id in (
        "printSearchInput", "printDateFrom", "printDateTo",
        "printStatusOptions", "printAttentionOptions", "printRouteOptions",
        "printOptionsGlassType", "printPreviewPageCount", "printCopies", "printOrientation",
        "printPreviewZoomOut", "printPreviewZoomIn", "printPreviewFullscreen",
        "printDocumentViewport", "printDocumentPaper",
        "printSavePresetBtn", "printPresetSelect", "printExportType", "printOptionsSubmit",
    ):
        assert f'id="{element_id}"' in index

    assert 'class="print-options-panel print-options-panel-v197"' in index
    assert 'Delivery List Preview' in index
    assert 'File Type' in index
    assert '<option value="xlsx">Excel Workbook (.xlsx)</option>' in index
    assert 'Print List' in index
    assert 'v0.197 Print / Export document-preview control center' in styles
    assert '.print-filter-pane-v197' in styles
    assert '.print-document-paper-v197' in styles
    assert '.print-paper-table-v197' in styles
    assert '.print-options-footer-v197' in styles
    assert '.print-export-control-v197' in styles
    assert 'grid-row: 4' in styles

    assert 'const PRINT_PREVIEW_PAGE_SIZE = 18;' in app
    assert 'const PRINT_PRESET_STORAGE_KEY = "deliveryScannerPrintPresetsV205";' in app
    assert 'function renderPrintDocumentPreview(preview = {})' in app
    assert 'async function savePrintPreset()' in app
    assert 'statusesExact: statuses.length ? JSON.stringify(statuses) : ""' in app
    assert 'attentionExact: attention.length ? JSON.stringify(attention) : ""' in app
    assert 'submitPrintOptions(els.printExportType?.value || "pdf")' in app
    assert 'function updatePrintOutputAction()' in app

    assert 'exact_filter_values("statusesExact")' in store
    assert 'exact_filter_values("attentionExact")' in store
    assert 'search_query = str(filters.get("searchQuery")' in store
    assert 'item_status_key(item) not in exact_statuses' in store
    assert 'item_attention_keys(item) & exact_attention' in store
    assert 'item.get("route") or "Unassigned"' in store
    assert '"previewRows": preview_rows' in server
    assert '"pageCount": max((len(preview_rows)' in server

    assert 'static/css/print.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert '<strong>0.324</strong>' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.197 - Print / Export Document Preview Control Center' in changelog


def test_v198_route_first_print_filters_quick_date_and_smart_search() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'id="printOptionsStages"' not in index
    assert 'id="printQuickDate"' not in index
    assert 'id="printDateQuickSelect"' in index
    assert 'id="printSearchSuggestions"' in index
    assert 'Search customer, order, item, or Job Nr.' in index
    assert 'Airport includes every outbound item.' in index
    assert 'Select exact stages' not in index

    assert 'const PRINT_ROUTE_GROUPS = [' in app
    for value, label in (
        ('airport', 'Airport'),
        ('indian_trail', 'Indian Trail'),
        ('greenville', 'Greenville'),
        ('cpu', 'CPU'),
        ('dtc', 'DTC'),
    ):
        assert f'value: "{value}", label: "{label}"' in app
    assert 'stageCategory(list) === "outbound"' in app
    assert 'function printRowsForSelectedRoutes' in app
    assert 'routeGroupsExact: JSON.stringify(selectedPrintRouteGroups())' in app
    assert 'function renderPrintQuickDateOptions' in app
    assert 'function renderPrintSearchSuggestions' in app
    assert 'printItemsForCountList' not in app
    assert 'for (const item of Array.isArray(list.items) ? list.items : [])' in app
    assert 'openPrintOptions({ date, listIds, updatedOnly, fixedListIds: true });' in app

    assert 'exact_filter_values("routeGroupsExact")' in store
    assert '"airport" not in exact_route_groups' in store
    assert 'search_matches_job = search_query in job_value' in store
    assert 'public_route_label(item.get("route")) or "Indian Trail"' in server

    assert 'v0.198 Route-first Print / Export filters and smart search' in styles
    assert '.print-search-suggestions-v198' in styles
    assert '.print-date-selector-section-v201' in styles
    assert '.print-route-options-v197' in styles
    assert 'radial-gradient(circle at 94% 40%' in styles
    hero_start = styles.index('.print-options-hero-v197 {')
    hero_end = styles.index('}', hero_start)
    assert 'radial-gradient(circle at 96%' not in styles[hero_start:hero_end]

    assert 'static/css/print.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert '<strong>0.324</strong>' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.198 - Route-First Print Filters, Quick Date, and Smart Search' in changelog



def test_v199_multi_order_preset_gui_and_live_preview() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    for element_id in (
        "printSelectedOrdersList",
        "printSelectedOrdersCount",
        "printSelectedOrdersClear",
        "printPresetModal",
        "printPresetNameInput",
        "printPresetConfirmBtn",
    ):
        assert f'id="{element_id}"' in html
    assert "print-filter-matrix-v203" in html
    assert "print-route-section-v203" in html
    assert "data-print-add-order" in app
    assert "selectedPrintOrderValues" in app
    assert 'ordersExact: orders.length ? JSON.stringify(orders) : ""' in app
    assert "buildLocalPrintSelectionPreview" in app
    assert "confirmPrintPresetSave" in app
    assert "window.prompt(\"Preset name\")" not in app
    assert "class=\"glass-group\"" in app
    assert '"job": str(item.get("job") or item.get("product") or "")' in server
    assert "preview_page_size = 18" in server
    assert ".print-filter-chip-v197:has(input:checked) span" in css
    assert ".print-selected-orders-list-v199" in css
    assert ".print-preset-modal-v199" in css
    assert "APPLICATION_VERSION = \"322\"" in contract
    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html


def test_v200_live_preview_all_filters_preset_builder_and_output_selector() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'id="printResetFiltersBtn"' not in html
    assert 'id="printExportBtn"' not in html
    assert '> Create Preset</button>' in html
    assert 'id="printExportType"' in html
    assert '<option value="pdf">PDF</option>' in html
    assert '<option value="xlsx">Excel Workbook (.xlsx)</option>' in html
    assert '<option value="csv">Comma-Separated Values (.csv)</option>' in html
    assert 'id="printOutputActionLabel">Print List</span>' in html
    assert 'Create Print Preset' in html

    assert 'function selectedPrintStatusValues()' in app
    assert 'function selectedPrintAttentionValues()' in app
    assert 'data-print-status-all' in app
    assert 'data-print-attention-all' in app
    assert 'allPrintGlassTypesSelected() ? ""' in app
    assert 'function printPresetFromBuilder()' in app
    assert 'function handlePrintPresetBuilderChange(event)' in app
    assert 'function updatePrintOutputAction()' in app
    assert 'function exportRawPrintCsv(' in app

    assert 'parsed.path == "/api/export/package.csv"' in server
    assert 'def export_package_csv(' in store
    assert '.print-clear-filters-v200' in css
    assert '.print-output-format-v200 .custom-select-trigger' in css
    assert '.print-preset-builder-v200' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme


def test_v201_print_calendar_all_glass_and_preview_stability() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for element_id in (
        "printDateQuickSelect", "printDateCalendar",
        "printCalendarLeftGrid", "printCalendarRightGrid",
        "printCalendarApply", "printDateFrom", "printDateTo",
    ):
        assert f'id="{element_id}"' in html
    assert 'printCalendarSingleMode' not in html
    assert 'printCalendarRangeMode' not in html
    assert '<option value="__custom__">Custom Range…</option>' in html
    assert 'id="printQuickDate"' not in html
    assert 'type="hidden"' in html[html.index('id="printDateFrom"') - 40:html.index('id="printDateFrom"') + 80]
    assert "function syncPrintAllGlassChoice(changed)" in app
    assert "if (allInput.checked) detailInputs.forEach((input) => { input.checked = false; });" in app
    assert 'function printGlassCategoryMarkup(glassEntries, selectedKeys, selectAllCurrent)' in app
    assert 'if (!allGlass && !selectedGlass.size) return false;' in app
    assert 'function renderPrintDateCalendar()' in app
    assert 'is-today' in app
    assert 'function applyPrintCalendarSelection()' in app
    assert '.print-date-calendar-v201' in css
    assert '.print-header-date-control-v203' in css
    assert '.print-calendar-day-v201.is-today' in css
    assert 'grid-column: auto;' in css[css.index('.print-filter-chip-v197.is-status-all'):css.index('.print-options-footer-v200')]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme


def test_v202_exact_print_sessions_item_selection_output_presets_and_scroll_preview() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    header_start = html.index('class="print-pane-heading-v197 print-pane-heading-v203')
    header_end = html.index('<div class="print-filter-scroll-v197">', header_start)
    filter_header = html[header_start:header_end]
    assert filter_header.index('id="printSavePresetBtn"') < filter_header.index('id="printClearAllBtn"')
    assert 'id="printPresetSelect"' in filter_header
    assert 'id="printPreviewPageInput"' not in html
    assert 'id="printPreviewPageTotal"' not in html
    assert 'id="printPreviewPageCount"' in html
    assert 'id="printCopies"' in html
    assert 'id="printOrientation"' in html

    preset_start = app.index('function renderPrintPresetSaveSummary(')
    preset_end = app.index('function printPresetFromBuilder()', preset_start)
    preset_code = app[preset_start:preset_end]
    assert 'Date Range' not in preset_code
    assert 'Specific Orders' not in preset_code
    assert 'data-preset-output-type' in preset_code
    assert 'data-preset-copies' in preset_code
    assert 'data-preset-orientation' in preset_code

    assert 'data-print-add-item' in app
    assert 'data-print-remove-item' in app
    assert 'state.printSelectedItems = []' in app
    assert 'delivery-print-sheet-v203' in app
    assert 'launchLocalPrintPackage' in app
    assert 'function buildFormattedPrintWorkbookBytes(' in app
    assert 'function exportFormattedPrintXlsx(' in app
    assert 'function exportRawPrintCsv(' in app

    assert 'PRINT_PACKAGE_SESSION_TTL_SECONDS' in server
    assert 'def normalize_print_package_request' in server
    assert 'parsed.path == "/api/print/package-session"' in server
    assert 'filters["lineItemIdsExact"]' in server
    assert 'filters["rowKeysExact"]' in server
    assert 'page_size = "letter landscape"' in server
    assert 'base_sections = list(sections)' in server

    assert 'exact_filter_values("orderItemsExact")' in store
    assert 'exact_filter_values("lineItemIdsExact")' in store
    assert 'exact_filter_values("rowKeysExact")' in store
    assert "row_key = f\"{str(list_id or '').strip()}|{order_value}|{item_value}\"" in store

    assert 'v0.202 exact print sessions, item selection, presets, and scroll preview' in css
    assert 'v0.203 Print filter matrix, header date selector, and exact print preview' in css
    assert '.print-document-page-v202.is-portrait' in css
    assert '.print-document-page-v202.is-landscape' in css
    assert '.print-search-result-actions-v202' in css
    assert '.print-preset-output-grid-v202' in css

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog


def test_v203_print_header_date_layout_direct_print_and_exact_preview() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    header_start = html.index('class="print-pane-heading-v197 print-pane-heading-v203')
    header_end = html.index('<div class="print-filter-scroll-v197">', header_start)
    header = html[header_start:header_end]
    assert 'id="printDateQuickSelect"' in header
    assert '<option value="__custom__">Custom Range…</option>' in header
    assert header.index('id="printDateQuickSelect"') < header.index('id="printSavePresetBtn"') < header.index('id="printClearAllBtn"')
    assert 'class="print-filter-matrix-v203"' in html
    assert html.index('print-route-section-v203') < html.index('print-glass-section-v203') < html.index('print-status-section-v203') < html.index('print-attention-section-v203')
    assert html.index('print-attention-section-v203') < html.index('print-filter-search-section-v203') < html.index('print-selected-orders-section-v203')
    assert 'id="printCopies" type="number"' in html
    assert 'id="printCopiesDecrease"' in html
    assert 'id="printCopiesIncrease"' in html
    assert 'data-print-orientation="portrait"' in html
    assert 'data-print-orientation="landscape"' in html

    assert 'function launchLocalPrintPackage(preview)' in app
    assert 'window.open("", "deliveryListPdfExportWindow"' in app
    assert '@page{size:${pageSize}' in app
    assert 'function paginatePrintSheetRows(rows, orientation = "portrait")' in app
    assert 'function printSheetPageMarkup(' in app
    assert 'renderPrintSelectionPreview(buildLocalPrintSelectionPreview())' in app
    assert 'The exact server preview could not be refreshed' not in app
    assert 'data-print-add-item' in app
    assert 'refreshPrintSearchSuggestions' in app
    assert 'data-preset-orientation-choice="portrait"' in app

    assert 'v0.203 Print filter matrix, header date selector, and exact print preview' in css
    assert '.print-filter-matrix-v203' in css
    assert '.print-copy-stepper-v203' in css
    assert '.print-orientation-toggle-v203' in css
    assert '.delivery-print-sheet-v203' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog



def test_v204_print_preview_geometry_and_visual_polish() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.204 - Print / Export Visual Polish and Preview Geometry Repair' in changelog
    assert 'v0.204 Print / Export visual polish and preview geometry repair' in css

    # The prior max-content/percentage-width cycle created a million-pixel page
    # stack and placed the actual sheet far outside the visible viewport.
    assert 'width: 100% !important;' in css[css.index('v0.204 Print / Export visual polish'): ]
    assert 'zoom: var(--print-preview-zoom);' in css
    assert 'transform: none !important;' in css
    assert 'width: min(720px, calc(100% - 28px)) !important;' in css
    assert 'width: min(960px, calc(100% - 28px)) !important;' in css
    assert 'white-space: normal;' in css[css.index('v0.204 Print / Export visual polish'): ]



def test_v205_range_calendar_known_glass_and_user_preset_persistence() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'print-filter-header-actions-v205' in html
    assert 'id="printCalendarLeftGrid"' in html
    assert 'id="printCalendarRightGrid"' in html
    assert 'id="printCalendarFromValue"' in html
    assert 'id="printCalendarToValue"' in html
    assert 'id="printCalendarReset"' in html
    assert 'printCalendarSingleMode' not in html
    assert 'printCalendarRangeMode' not in html
    assert 'Custom Range…' in html
    assert 'printCalendarMonthButtons' in app
    assert 'resetPrintCalendarRange' in app
    assert 'if (els.printCalendarApply) els.printCalendarApply.disabled = !(start && end)' in app
    assert 'collectKnownPrintGlassTypes' in app
    assert 'deliveryScannerActivePrintPresetV205' in app
    assert 'printPresetUserToken' in app
    assert 'resetPrintFilters({ clearActivePreset: false })' in app
    assert 'const initialization = resetPrintFilters({ clearActivePreset: false })' in app
    assert 'v0.205 consistent print controls, range calendar, and user preset state' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.205 - Consistent Header Controls, Range Calendar, and User Presets' in changelog


def test_v206_compact_print_controls_instant_preset_builder_and_calendar_repair() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'print-preset-modal-v206' in html
    assert 'print-preset-name-card-v206' in html
    assert 'print-preset-builder-heading-v206' in html
    assert 'collectKnownPrintGlassTypes' in app
    assert 'loadKnownPrintGlassTypes' not in app
    assert 'ensurePrintListDetails(listIds)' not in app[app.index('function collectKnownPrintGlassTypes'):app.index('/** Build an editable preset', app.index('function collectKnownPrintGlassTypes'))]
    assert 'data-preset-glass-search' in app
    assert 'count !== ""' not in app[app.index('function printPresetBuilderGroup'):app.index('/** Collect every known product value', app.index('function printPresetBuilderGroup'))]
    assert '.custom-select-menu[data-select-id="printDateQuickSelect"]' in app
    assert 'v0.206 compact print header, instant preset builder, and calendar repair' in css
    assert 'min-height: 34px !important;' in css[css.index('v0.205 consistent print controls'):]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.206 - Compact Print Controls, Instant Preset Builder, and Calendar Repair' in changelog


def test_v207_custom_range_stable_initial_filters_and_lookup_glass_library() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert '<option value="__custom__">Custom Range…</option>' in html
    assert '>Apply Dates</button>' in html
    assert 'editingExistingRange' in app
    assert 'event.composedPath' in app
    assert 'eventPath.includes(els.printDateCalendar)' in app
    assert 'setPrintRouteGroups(["airport"], { syncControls: false });' in app
    assert 'state.printAllGlass = true' in app
    assert 'activePrintPreset()?.glassTypes' not in app[app.index('function allPrintGlassTypesSelected'):app.index('/** Keep All Glass mutually exclusive')]
    assert 'ensurePrintProductLookupLibrary' in app
    assert 'adoptManualEditLookups' in app
    assert 'product?.label || product?.value' in app
    assert 'data-preset-search' in app
    assert 'grid-template-areas:' in css[css.index('v0.207 fills every desktop grid cell'):]
    assert 'font-size: 10.5px !important;' in css[css.index('v0.205 consistent print controls'):]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.207 - Custom Range Completion, Stable Initial Filters, and Lookup Glass Library' in changelog


def test_v208_exact_glass_preview_state_and_centered_header_controls() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'function printGlassTypeMatchKey(value)' in app
    assert '.normalize("NFKC")' in app
    assert '[“”″]' in app
    assert 'function commitPrintGlassSelectionFromControls()' in app
    assert 'function commitPrintRouteSelectionFromControls()' in app
    assert 'Preview filtering must never depend on detached DOM.' in app
    assert 'selectedPrintGlassTypeValues().map(printGlassTypeMatchKey)' in app
    assert 'selectedGlass.has(printGlassTypeMatchKey(glassTypeLabel(item)))' in app
    assert 'data-print-glass-value=' in app
    assert 'commitPrintRouteSelectionFromControls();' in app
    assert 'const selectedGlass = selectedPrintGlassTypeValues();' in app
    assert 'grid-template-columns: 18px minmax(0, 1fr) 18px;' in css
    assert '.print-header-control-v205 .custom-select-value {' in css
    assert 'text-align: center !important;' in css[css.index('v0.205 consistent print controls'):]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.208 - Exact Glass Preview State and Centered Header Controls' in changelog


def test_v209_system_default_landscape_totals_and_preset_redesign() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'print-filter-heading-cluster-v209' in html
    assert 'print-preset-modal-v209' in html
    assert 'print-preset-sidebar-v209' in html
    assert 'PRINT_SYSTEM_DEFAULT_PRESET_NAME = "System Default"' in app
    assert 'System Default · All Items' in app
    assert 'routeGroups: Object.freeze(["airport"])' in app
    assert 'outputType: "pdf"' in app
    assert 'orientation: "portrait"' in app
    assert 'function localPrintPackageStyles(orientation)' in app
    assert 'paginatePrintSheetRows(sheet.rows || [], orientation)' in app
    assert 'class="sheet-totals"' in app
    assert 'Rows: ${printableRows}' in app
    assert 'Orders: ${totalOrders}' in app
    assert 'QTY: ${totalQty}' in app
    assert '.delivery-print-sheet-v203.remake::after' in css
    assert 'inset: 10px;' in css
    assert '.delivery-print-sheet-v203.is-landscape .customer-col { width: 24%; }' in css
    assert 'font-size: 12.5px !important;' in css[css.index('v0.212 print header'):]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.209 - System Default Preset, Landscape Sheets, and Print Totals' in changelog


def test_v210_deterministic_initial_airport_route() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'function normalizePrintRouteGroups(values = state.printRouteGroups)' in app
    assert 'if (!selected.length || selected.includes("airport")) return ["airport"];' in app
    assert 'function setPrintRouteGroups(values, { syncControls = true } = {})' in app
    assert 'captureControlSelections = preserveSelections' in app
    assert 'if (captureControlSelections) {' in app
    assert 'setPrintRouteGroups(["airport"], { syncControls: false });' in app
    assert 'const openId = ++state.printWorkspaceOpenId;' in app
    assert 'const initialization = resetPrintFilters({ clearActivePreset: false })' in app
    assert '.then(() => applyPrintPreset(initialPreset' not in app
    assert 'if (state.printWorkspacePromise) await state.printWorkspacePromise;' in app
    assert 'state.printWorkspaceReady = true;' in app
    assert 'if (!state.printWorkspaceReady) {' in app
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.210 - Deterministic Initial Airport Route' in changelog


def test_v211_letter_preview_parity_and_filter_summary() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'function printCurrentFilterSummary()' in app
    assert 'class="sheet-filter-summary"' in app
    assert 'filterSummary,' in app
    assert 'function localPrintPackageStylesheetUrls()' in app
    assert 'static/css/styles.css?v=20260817-v0.324' in app
    assert '@page{size:${pageSize};margin:.4in}' in app
    assert 'width: 8.5in !important;' in css
    assert 'height: 11in;' in css
    assert 'width: 11in !important;' in css
    assert 'height: 8.5in;' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary' in css
    assert 'inset: .49in;' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.211 - Letter Preview Parity and Printed Filter Summary' in changelog


def test_v212_adaptive_filters_columns_and_route_state() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'return `Filters: ${uniqueParts.length ? uniqueParts.join(" | ") : "All items"}`;' in app
    assert 'Route:' not in app[app.index('function printCurrentFilterSummary()'):app.index('/** Paginate rows', app.index('function printCurrentFilterSummary()'))]
    assert 'Rows: ${printableRows} | Orders: ${totalOrders} | QTY: ${totalQty}' in app
    assert '<th>Order</th><th>Item</th><th>QTY</th>' in app
    assert 'function printPreviewFitZoom(' in app
    assert 'state.printPreviewZoom = printPreviewFitZoom("landscape")' in app
    assert 'setPrintRouteGroups(selectedPrintRouteGroups());' in app
    assert app.count('commitPrintRouteSelectionFromControls();') == 1
    assert 'setPrintRouteGroups(preset.routeGroups?.length ? preset.routeGroups : ["airport"], { syncControls: false });' in app
    assert '--print-date-control-width' in css
    assert '.delivery-print-sheet-v203 .dimensions-col { width: 21%; }' in css
    assert '.delivery-print-sheet-v203 .customer-col { width: 20%; }' in css
    assert '.delivery-print-sheet-v203.is-landscape .dimensions-col { width: 23%; }' in css
    assert '.delivery-print-sheet-v203.is-landscape .customer-col { width: 24%; }' in css
    assert 'inset: .42in;' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.212 - Adaptive Print Metadata, Stable Route State, and Table Fit' in changelog


def test_v213_dense_rows_route_check_and_remake_frame() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    sheet_markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    pagination = app[app.index('function paginatePrintSheetRows('):app.index('function printSheetBodyMarkup', app.index('function paginatePrintSheetRows('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert '<div class="notes">' not in sheet_markup
    assert '? (pages.length ? 28 : 27)' in pagination
    assert ': (pages.length ? 28 : 26)' in pagination
    assert 'function localPrintPackageStylesheetUrls()' in app
    assert 'static/css/styles.css?v=20260817-v0.324' in app
    assert '.delivery-print-sheet-v203 .check-cell {' in css
    assert '.delivery-print-sheet-v203 th:nth-child(7) {' in css
    assert '.delivery-print-sheet-v203 td:nth-child(7) {' in css
    assert '.delivery-print-sheet-v203.remake,' in css
    assert '.delivery-print-sheet-v203.remake::after {' in css
    assert 'overflow:hidden!important' in print_styles
    assert '.delivery-print-sheet-v203.remake{padding:.1in!important}' in print_styles
    assert '.delivery-print-sheet-v203.remake::after{inset:.02in}' in print_styles
    assert '.delivery-print-sheet-v203 .notes' not in css
    assert '.delivery-print-sheet-v203.is-landscape .notes' not in css
    assert '.delivery-print-sheet-v203 .check-cell {\n  font-size: 12.25px;' in css
    assert 'text-align: center;' in css[css.index('.delivery-print-sheet-v203 th:nth-child(7)'):css.index('.delivery-print-sheet-v203 th:nth-child(8)')]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.213 - Denser Delivery Sheets and Stable Remake Frames' in changelog


def test_v214_fuller_pages_gray_bands_and_repeating_footer() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    pagination = app[app.index('function paginatePrintSheetRows('):app.index('function printSheetBodyMarkup', app.index('function paginatePrintSheetRows('))]
    sheet_markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert '? (pages.length ? 28 : 27)' in pagination
    assert ': (pages.length ? 28 : 26)' in pagination
    assert 'const pageFilterDetails = `<p class="sheet-filter-summary"' in sheet_markup
    assert 'const firstPageSignoff = continuation' in sheet_markup
    assert '<footer class="sheet-footer printed-at">Printed at:' in sheet_markup
    assert '.delivery-print-sheet-v203 .sheet-footer {' in css
    assert 'left: .4in;' in css[css.index('.delivery-print-sheet-v203 .sheet-footer {'):css.index('.delivery-print-sheet-v203 .sheet-filter-summary {', css.index('.delivery-print-sheet-v203 .sheet-footer {'))]
    assert '.delivery-print-sheet-v203 .sheet-footer{left:0;bottom:0}' in print_styles
    assert '.delivery-print-sheet-v203 th:nth-child(7) {' in css
    assert '.delivery-print-sheet-v203 td:nth-child(7) {' in css
    assert '-webkit-print-color-adjust:exact;print-color-adjust:exact' in print_styles
    assert 'background: #dfe3e8;' in css
    assert '.delivery-print-sheet-v203 .sheet-footer {' in css
    assert 'text-align: center;' in css[css.index('.delivery-print-sheet-v203 th:nth-child(7)'):css.index('.delivery-print-sheet-v203 th:nth-child(8)')]
    assert 'print-color-adjust: exact;' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.214 - Fuller Page Capacity and Repeating Print Footer' in changelog


def test_v215_date_first_branded_header_and_alternating_rows() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    sheet_markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    row_markup = app[app.index('function printSheetBodyMarkup('):app.index('/** Return the exact visual sheet markup', app.index('function printSheetBodyMarkup('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert 'function printSheetDateLabel(value)' in app
    assert 'function printSheetRouteLabel(routeGroups = selectedPrintRouteGroups())' in app
    assert 'dateLabel: printSheetDateLabel(list.deliveryDate || "")' in app
    assert 'routeLabel: printSheetRouteLabel()' in app
    assert 'class="sheet-brand-mark"><img src="${escapeHtml(logoUrl)}"' in sheet_markup
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260817-v0.324' in sheet_markup
    assert 'class="sheet-date-title"' in sheet_markup
    assert 'class="sheet-location-title"' in sheet_markup
    assert 'class="print-data-row ${stripeClass}"' in row_markup
    assert 'border-bottom: 2px solid #000;' in css
    assert 'border-top: 2px solid #000;' in css
    assert '.delivery-print-sheet-v203 .print-data-row.is-even td {' in css
    assert 'filter: grayscale(1) contrast(1.22);' in css
    assert '.delivery-print-sheet-v203 .sheet-brand-mark img {' in css
    assert 'filter: grayscale(1) contrast(1.22);' in css
    assert 'border-bottom: 2px solid #000;' in css
    assert 'border-top: 2px solid #000;' in css
    assert '.delivery-print-sheet-v203 .print-data-row.is-even td {' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.215 - Date-First Branded Print Header and Alternating Rows' in changelog


def test_v216_supplied_logo_clean_header_and_stacked_filters() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    logo = ROOT / "static/images/barefoot-company-builders-firstsource-print-logo.png"

    sheet_markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert logo.exists() and logo.stat().st_size > 0
    assert 'src="${escapeHtml(logoUrl)}"' in sheet_markup
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260817-v0.324' in sheet_markup
    assert 'function localPrintPackageStylesheetUrls()' in app
    assert '.delivery-print-sheet-v203.rush .sheet-header {' in css
    assert '.delivery-print-sheet-v203.remake .sheet-header {' in css
    assert '.delivery-print-sheet-v203 .sheet-totals {' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary {' in css
    assert 'border-bottom: 2px solid #000;' in css
    assert 'border-top: 2px solid #000;' in css
    assert 'border-bottom: 0;' in css[css.index('.delivery-print-sheet-v203 .sheet-header {'):css.index('.delivery-print-sheet-v203 .sheet-brand-title {')]
    assert 'display: block;' in css[css.index('.delivery-print-sheet-v203 .sheet-totals {'):css.index('.delivery-print-sheet-v203 .sheet-footer {')]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.216 - Supplied Print Logo and Cleaner Header Metadata' in changelog


def test_v217_full_weekday_dates_and_route_first_titles() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    date_helper = app[app.index('function formatDisplayDate('):app.index('/**\n * Purpose: Normalize the format date time', app.index('function formatDisplayDate('))]
    route_helper = app[app.index('function printSheetRouteLabel('):app.index('/** Convert one loaded row', app.index('function printSheetRouteLabel('))]
    sheet_markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert 'weekday: "long"' in date_helper
    assert 'month: "long"' in date_helper
    assert 'day: "numeric"' in date_helper
    assert 'year: "numeric"' in date_helper
    assert '.join(" | ")' in route_helper
    assert 'function printSheetTitleLabel(routeGroups = selectedPrintRouteGroups())' in route_helper
    assert 'DELIVERY LIST`' in route_helper
    assert 'titleLabel: printSheetTitleLabel()' in app
    assert 'class="sheet-location-title">${escapeHtml(titleLabel)}' in sheet_markup
    assert 'class="sheet-date-title">${escapeHtml(dateLabel)}' in sheet_markup
    assert '.delivery-print-sheet-v203 .sheet-location-title {' in css
    assert '.delivery-print-sheet-v203 .sheet-date-title {' in css
    assert '.delivery-print-sheet-v203 .sheet-location-title {' in css
    assert '.delivery-print-sheet-v203 .sheet-date-title {' in css
    assert 'const minimum = isRange ? 370 : 230;' in app
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.217 - Full Weekday Dates and Route-First Delivery Titles' in changelog


def test_v218_reliable_print_logo_and_tightened_header():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    logo = ROOT / "static/images/barefoot-company-builders-firstsource-print-logo.png"

    markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert logo.is_file() and logo.stat().st_size > 1000
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260817-v0.324' in markup
    assert 'new URL(' in markup
    assert 'Continuation sheet' not in markup
    assert 'white-space: nowrap;' in css
    assert '.delivery-print-sheet-v203 .sheet-location-row.is-medium .sheet-location-title' in css
    assert '.delivery-print-sheet-v203 .sheet-location-row.is-long .sheet-location-title' in css
    assert 'font-size: 20px;' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary {' in css
    assert 'white-space: nowrap;' in css
    assert '.delivery-print-sheet-v203 .sheet-location-row.is-medium .sheet-location-title' in css
    assert '.delivery-print-sheet-v203 .sheet-location-row.is-long .sheet-location-title' in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.218 - Reliable Print Logo and Tightened Branded Header' in changelog


def test_v219_shared_preview_print_styles_and_portrait_zoom():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'printPreviewZoom: 0.9' in app
    assert '<strong id="printPreviewZoomLabel">90%</strong>' in html
    assert 'state.printPreviewZoom = 0.9;' in app
    assert 'function localPrintPackageStylesheetUrls()' in app
    assert 'static/css/styles.css?v=20260817-v0.324' in app
    assert 'static/css/print.css?v=20260817-v0.324' in app
    assert '<link rel="stylesheet" href="${escapeHtml(stylesheetUrl)}">' in app
    assert 'document.fonts && document.fonts.ready' in app
    assert 'await Promise.all(imageLoads);' in app
    assert '.delivery-print-sheet-v203 .copy-box > span {' in css
    assert 'margin-top: 24px;' in css
    assert 'white-space: nowrap;' in css[css.rindex('/* v0.219 shared preview/print header alignment'):]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.219 - Shared Preview and Print Styling' in changelog

if __name__ == "__main__":
    test_index_local_assets_exist()
    test_page_stylesheets_are_present_and_balanced()
    test_version_numbers_are_not_embedded_in_asset_filenames()
    test_single_javascript_bundle_is_loaded()
    test_python_packages_are_organized()
    test_deployment_files_are_organized()
    test_admin_control_center_modal_structure()
    test_v161_scan_timestamp_rack_status_and_rack_control_centers()
    test_v162_scan_typography_and_control_center_layering_repair()
    test_v163_modal_hidden_state_and_close_repair()
    test_v164_simplified_gui_headers_and_automation_action()
    test_v165_manual_edit_history_and_rack_override()
    test_v166_manual_route_and_admin_gui_refinement()
    test_v167_manual_route_and_new_order_workspace()
    test_v168_manual_edit_exact_row_capture_repair()
    test_v169_manual_edit_glass_type_filters()
    test_v205_range_calendar_known_glass_and_user_preset_persistence()
    test_v214_fuller_pages_gray_bands_and_repeating_footer()
    test_v215_date_first_branded_header_and_alternating_rows()
    test_v216_supplied_logo_clean_header_and_stacked_filters()
    test_v217_full_weekday_dates_and_route_first_titles()
    test_v218_reliable_print_logo_and_tightened_header()
    test_v206_compact_print_controls_instant_preset_builder_and_calendar_repair()
    test_v207_custom_range_stable_initial_filters_and_lookup_glass_library()
    test_v208_exact_glass_preview_state_and_centered_header_controls()
    test_v209_system_default_landscape_totals_and_preset_redesign()
    test_v210_deterministic_initial_airport_route()
    test_v211_letter_preview_parity_and_filter_summary()
    test_v212_adaptive_filters_columns_and_route_state()
    test_v213_dense_rows_route_check_and_remake_frame()
    test_v199_multi_order_preset_gui_and_live_preview()
    test_v200_live_preview_all_filters_preset_builder_and_output_selector()
    test_v201_print_calendar_all_glass_and_preview_stability()
    test_v202_exact_print_sessions_item_selection_output_presets_and_scroll_preview()
    test_v203_print_header_date_layout_direct_print_and_exact_preview()
    test_v193_guarded_cross_delivery_date_scanning()
    test_v194_exact_manual_scans_result_colors_sound_and_all_scans_history()
    test_v195_print_export_filter_workspace_and_exact_preview()
    test_v196_scanner_panel_context_selectors()
    test_v197_print_export_document_preview_control_center()
    test_v198_route_first_print_filters_quick_date_and_smart_search()
    test_scan_time_pill_qty_headers_and_table_are_width_safe()
    test_v158_core_page_polish_and_scan_geometry()
    test_v154_admin_reject_management_and_scan_ribbon()
    test_v204_print_preview_geometry_and_visual_polish()
    print("Static structure checks passed.")



def test_v0220_print_filter_polish_and_repeating_metadata():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'pageFilterDetails = `<p class="sheet-filter-summary"' in app
    assert 'Checked By: <i class="write-line checked-line"></i>' in app
    assert 'Date: <i class="write-line date-line"></i>' not in app
    assert 'printGlassCategoryForLabel' in app
    assert 'printGlassCategoryMarkup' in app
    assert 'state: showHealthState ? (count > 0 ? "alert" : "clear") : ""' in app
    assert '? (pages.length ? 28 : 27)' in app
    assert ': (pages.length ? 28 : 26)' in app

    assert '.print-filter-chip-v197.is-route-airport' in css
    assert '.print-filter-chip-v197.is-route-greenville' in css
    assert '.print-glass-category-v220.is-mirror' in css
    assert '.print-glass-category-v220.is-tempered' in css
    assert '.print-glass-category-v220.is-annealed' in css
    assert '.print-filter-chip-v197.has-alert::before' in css
    assert '.print-filter-chip-v197.is-clear::before' in css
    assert 'content: "✓";' in css

    assert 'Grouped by Mirror, Tempered, and Annealed for faster selection' not in html
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.220 - Print Filter Visual Hierarchy and Compact Signoff' in changelog


def test_v0221_idle_route_and_catalog_detail_recovery():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert "function deliveryCatalogRevisionKey(list = {})" in app
    assert "function mergeDeliveryCatalogWithLoadedDetails(refreshedLists)" in app
    assert "state.lists = mergeDeliveryCatalogWithLoadedDetails(refreshedLists);" in app
    assert "sameRevision && previous._printItemsLoaded && Array.isArray(previous.items)" in app
    assert "merged._printItemsLoaded = false;" in app
    assert "function restorePrintWorkspaceAfterInactivity({ refreshIfHealthy = false } = {})" in app
    assert "printWorkspaceRecoveryPromise" in app
    assert 'window.addEventListener("pageshow"' in app
    assert 'document.addEventListener("dls:delivery-list-catalog-synced"' in app
    assert 'if (printWorkspaceNeedsDetailReload()) void restorePrintWorkspaceAfterInactivity();' in app
    assert 'restorePrintWorkspaceAfterInactivity({ refreshIfHealthy: true })' in app
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.221 - Idle Route and Print Row State Recovery' in changelog

def test_v0222_enlarged_branded_delivery_sheet_headers():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert "v0.222 enlarged branded delivery-sheet headers" in css
    assert ".sheet-header:not(.sheet-header-compact) .sheet-brand-mark" in css
    assert "width: 1.19in;" in css
    assert "font-size: 29px;" in css
    assert ".sheet-header-compact .sheet-brand-mark" in css
    assert "width: 1.01in;" in css
    assert "font-size: 22px;" in css
    assert "? (pages.length ? 28 : 27)" in app
    assert ": (pages.length ? 28 : 26)" in app
    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.222 - Enlarged Branded Delivery-Sheet Headers" in changelog




def test_v0223_fuller_page_capacity_and_centered_compact_columns():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    print_css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert '? (pages.length ? 28 : 27)' in app
    assert ': (pages.length ? 28 : 26)' in app
    assert 'v0.223 table-adjacent signoff and fuller verified page capacity' in print_css
    assert '.delivery-print-sheet-v203 .qty-col { width: 5.8%; }' in print_css
    assert '.delivery-print-sheet-v203 .dimensions-col { width: 20.2%; }' in print_css
    assert '.delivery-print-sheet-v203.is-landscape .qty-col { width: 5.8%; }' in print_css
    assert '.delivery-print-sheet-v203.is-landscape .dimensions-col { width: 22.2%; }' in print_css
    assert '.delivery-print-sheet-v203 :is(th, td):nth-child(2)' in print_css
    assert '.delivery-print-sheet-v203 :is(th, td):nth-child(4)' in print_css
    assert 'text-align: center;' in print_css[print_css.rindex('/* v0.223 table-adjacent signoff'): ]
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.223 - Table-Adjacent Signoff and Fuller Delivery Pages' in changelog


def test_v0224_unavailable_filters_and_aligned_borderless_signoff():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    print_css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'disabled = false' in app
    assert 'availabilityClass = disabled ? "is-unavailable"' in app
    assert 'disabled: count <= 0' in app
    assert 'disabled: !showHealthState && count <= 0' in app
    assert 'showHealthState || Number(attentionCounts.get(value) || 0) > 0' in app
    assert 'class="sheet-header-signoff"' in app
    assert '${firstPageSignoff}\n    </header>' in app
    assert 'class="sheet-table-signoff"' not in app
    assert 'v0.224 unavailable filter states and aligned print signoff' in print_css
    assert '.print-filter-chip-v197.is-unavailable' in print_css
    assert 'font-size: 11.5px;' in print_css
    assert '.delivery-print-sheet-v203 .sheet-header-signoff .copy-box' in print_css
    signoff_css = print_css[print_css.rindex('/* v0.224 unavailable filter states'):]
    assert 'border: 0;' in signoff_css
    assert 'font-size: 16px;' in signoff_css
    assert 'font-size: 14px;' in signoff_css
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.224 - Unavailable Filter States and Aligned Print Signoff' in changelog



def test_v0225_grouped_date_history_and_landscape_density():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    pagination = app[app.index('function paginatePrintSheetRows('):app.index('function printSheetBodyMarkup', app.index('function paginatePrintSheetRows('))]
    assert '? (pages.length ? 28 : 27)' in pagination
    assert ': (pages.length ? 28 : 26)' in pagination
    assert 'PRINT_DATE_HISTORY_BATCH_WEEKS = 2' in app
    assert 'function printQuickDateWeekLabel(startKey)' in app
    assert 'function loadMorePrintQuickDateHistory()' in app
    assert '<optgroup label="${escapeHtml(printQuickDateWeekLabel(weekKey))}">' in app
    assert '.print-date-load-more-v225' in css
    assert 'print-preset-modal-v209' in html
    assert '## v0.225 - Grouped Delivery Date History and Unified Preset Workspace' in changelog


def test_v0226_automatic_all_choices_newest_dates_and_filter_readability():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'function syncPrintAllRouteChoice(container, changed)' in app
    assert 'enabledDetails.every((input) => input.checked)' in app
    assert 'syncPrintAllRouteChoice(els.printRouteOptions, changed);' in app
    assert 'routeDetails.every((input) => input.checked)' in app
    assert 'detailInputs.every((input) => input.checked)' in app
    assert 'const orderedWeekKeys = [...grouped.keys()].sort((a, b) => b.localeCompare(a));' in app
    assert '.sort((a, b) => b.localeCompare(a))' in app
    assert 'font-size: 10.5px;' in css[css.rindex('/* v0.226 automatic All selections'):]
    assert 'print-glass-category-v220.is-tempered' in css
    assert '--print-chip-active-end: #2f7d49;' in css
    assert 'width: 1.30in;' in css
    assert 'width: 1.12in;' in css
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.226 - Automatic All Selections and Newest-First Delivery Dates' in changelog


def test_v0227_health_state_attention_and_preset_control_center():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'state: showHealthState ? (count > 0 ? "alert" : "clear") : ""' in app
    assert ':is(.is-attention-remake, .is-attention-rush, .is-attention-reject).has-alert' in css
    assert ':is(.is-attention-remake, .is-attention-rush, .is-attention-reject).is-clear' in css
    assert '--print-chip-soft-end: #f7cbd1;' in css
    assert '--print-chip-soft-end: #cfeeda;' in css

    preset_html = html[html.index('id="printPresetModal"'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    assert 'Create Delivery List Preset' in preset_html
    assert 'printPresetDescriptionInput' not in preset_html
    assert 'printPresetDefaultToggle' in preset_html
    assert 'printPresetLiveSummary' not in preset_html
    assert 'printPresetOutputSettings' in preset_html
    assert 'printPresetSaveOnlyBtn' in preset_html
    assert 'Visibility' not in preset_html
    assert 'id="printPresetPreview"' not in preset_html
    assert 'Step 1' not in preset_html
    assert 'Step 2' not in preset_html

    assert 'renderPrintPresetLiveSummary' not in app
    assert 'async function confirmPrintPresetSave({ apply = true } = {})' in app
    assert 'addOptionalUiEventListener(els.printPresetSaveOnlyBtn' in app
    assert 'const setAsDefault = Boolean(els.printPresetDefaultToggle?.checked);' in app
    assert 'PRINT_DEFAULT_PRESET_STORAGE_KEY' in app
    assert 'function defaultPrintPresetName()' in app
    assert 'if (setAsDefault) setDefaultPrintPresetName(cleanName);' in app
    assert 'const initialPreset = defaultPrintPresetName();' in app

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.227 - Health-State Attention Filters and Preset Control Center' in changelog




def test_v0228_create_preset_viewport_positioning_repair():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    preset_html = html[html.index('class="print-preset-backdrop-v199'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    assert 'print-preset-backdrop-v227 print-preset-backdrop-v228' in preset_html
    assert 'print-preset-modal-v227 print-preset-modal-v228' in preset_html

    repair_css = css[css.rindex('/* v0.228 Create Preset viewport positioning') :]
    assert '.print-preset-modal-v228' in repair_css
    assert 'position: fixed;' in repair_css
    assert 'inset: 12px;' in repair_css
    assert 'transform: none;' in repair_css
    assert 'overscroll-behavior: contain;' in repair_css
    assert 'grid-template-rows: auto auto auto auto;' in repair_css
    assert 'inset: 5px;' in repair_css

    assert 'const workspace = els.printPresetModal.querySelector(".print-preset-workspace-v227");' in app
    assert 'if (workspace) workspace.scrollTop = 0;' in app
    assert 'focus({ preventScroll: true })' in app

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.228 - Create Preset Viewport Positioning Repair' in changelog


def test_v0229_compact_polished_create_preset_workspace():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    preset_html = html[html.index('class="print-preset-backdrop-v199'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    assert 'print-preset-backdrop-v229' in preset_html
    assert 'print-preset-modal-v229' in preset_html
    assert 'print-preset-workspace-v229' in preset_html

    polish_css = css[css.rindex('/* v0.229 compact Create Preset polish') :]
    assert 'width: min(1240px, calc(100vw - 48px));' in polish_css
    assert 'height: min(780px, calc(100vh - 48px));' in polish_css
    assert '.print-preset-choice-v227.is-route-airport' in polish_css
    assert '.print-preset-choice-v227.is-status-complete' in polish_css
    assert '.print-preset-choice-v227.is-attention-remake' in polish_css
    assert '.print-preset-choice-v227.is-glass-tempered' in polish_css
    assert 'font-size: 12px;' in polish_css
    assert 'font-size: 13px;' in polish_css

    assert 'function printPresetChoiceVisualClass(name, value, label = value)' in app
    assert 'is-glass-${printGlassCategoryForLabel(label)}' in app

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.229 - Compact Polished Create Preset Workspace' in changelog


def test_v0230_create_preset_flow_repair_and_subtle_palette():
    root = Path(__file__).resolve().parents[1]
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # v0.232 retains the v0.230 flow repair instead of stacking another
    # competing override layer. Keep the repaired content-sized rows covered.
    repair_css = css[css.rindex('/* v0.232 expanded Create Preset workspace') :]
    assert 'grid-template-rows: minmax(0, 1fr) auto auto;' in repair_css
    assert 'min-height: max-content;' in repair_css
    assert 'grid-row: 3;' in repair_css
    assert 'overflow-y: hidden;' in repair_css
    assert '@media (max-height: 839px)' in repair_css
    assert 'width: min(1180px, calc(100vw - 40px));' in repair_css
    assert 'height: min(860px, calc(100vh - 20px));' in repair_css

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.230 - Create Preset Flow Repair and Subtle Control Palette' in changelog

def test_v0231_neutral_preset_hierarchy_and_grouped_glass_library():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    preset_html = html[html.index('class="print-preset-backdrop-v199'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    assert 'print-preset-backdrop-v232' in preset_html
    assert 'print-preset-modal-v232' in preset_html
    assert 'print-preset-workspace-v232' in preset_html
    assert 'print-preset-live-summary-card-v227' not in preset_html
    options_position = preset_html.index('print-preset-options-card-v227')
    actions_position = preset_html.index('print-preset-actions-card-v227')
    assert options_position < actions_position
    main_html = preset_html[preset_html.index('<main'):preset_html.index('</main>')]
    assert 'print-preset-options-card-v227' not in main_html

    assert 'PRINT_PRESET_GLASS_CATEGORY_DEFINITIONS' in app
    glass_definitions = app[app.index('const PRINT_PRESET_GLASS_CATEGORY_DEFINITIONS'):app.index('function printPresetGlassChoiceMarkup')]
    assert glass_definitions.index('value: "annealed"') < glass_definitions.index('value: "tempered"') < glass_definitions.index('value: "mirror"')
    assert 'data-preset-glass-category' in app
    assert 'category.hidden = categoryVisible === 0;' not in app

    polish_css = css[css.rindex('/* v0.232 expanded Create Preset workspace') :]
    assert 'background: #fff;' in polish_css
    assert 'border: 2px solid #295a88;' in polish_css
    assert 'background: #e9f0f7;' in polish_css
    assert '.print-preset-glass-category-v232' in polish_css
    assert 'margin-top: auto;' in polish_css
    assert 'grid-template-columns: repeat(3, minmax(0, 1fr));' in polish_css
    assert 'grid-template-rows: auto auto auto minmax(0, 1fr);' in polish_css

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.231 - Neutral Preset Selection and Grouped Glass Library' in changelog


def test_v0232_expanded_preset_workspace_and_restrained_category_colors():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    preset_html = html[html.index('class="print-preset-backdrop-v199'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    assert 'print-preset-backdrop-v232' in preset_html
    assert 'print-preset-modal-v232' in preset_html
    assert 'print-preset-workspace-v232' in preset_html
    assert 'printPresetDescriptionInput' not in preset_html
    assert '>Description<' not in preset_html
    assert 'printPresetDescriptionInput' not in app

    polish_css = css[css.rindex('/* v0.232 expanded Create Preset workspace') :]
    assert 'height: min(860px, calc(100vh - 20px));' in polish_css
    assert 'overflow-y: hidden;' in polish_css
    assert '@media (max-height: 839px)' in polish_css
    assert 'grid-template-columns: repeat(3, minmax(0, 1fr));' in polish_css
    assert 'grid-template-rows: auto auto auto minmax(0, 1fr);' in polish_css
    assert '.print-preset-choice-v227.is-route-airport' in polish_css
    assert '.print-preset-choice-v227.is-route-greenville' in polish_css
    assert '.print-preset-glass-category-v232.is-annealed' in polish_css
    assert '.print-preset-glass-category-v232.is-tempered' in polish_css
    assert '.print-preset-glass-category-v232.is-mirror' in polish_css
    assert 'background: #e4f2e8;' in polish_css
    assert 'background: #eee9f7;' in polish_css

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.232 - Expanded Preset Workspace and Restrained Category Colors' in changelog



def test_v0233_create_preset_scroll_ownership_and_bottom_containment():
    root = Path(__file__).resolve().parents[1]
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    preset_html = html[html.index('class="print-preset-backdrop-v199'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    assert 'print-preset-backdrop-v233' in preset_html
    assert 'print-preset-modal-v233' in preset_html
    assert 'print-preset-workspace-v233' in preset_html

    scroll_css = css[css.rindex('/* v0.233 Create Preset scroll ownership') :]
    assert 'overflow-y: auto;' in scroll_css
    assert 'grid-template-rows: max-content max-content max-content;' in scroll_css
    assert 'scrollbar-gutter: stable;' in scroll_css
    assert 'min-height: max-content;' in scroll_css
    assert 'height: auto;' in scroll_css
    assert '.print-preset-actions-card-v227' in scroll_css
    assert 'margin-top: 0;' in scroll_css

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.233 - Create Preset Scroll and Bottom Containment Repair' in changelog


def test_v0234_create_preset_simplification_and_theme_alignment():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    preset_html = html[html.index('class="print-preset-backdrop-v199'):html.index('<!-- SECTION: Interactive statistics chart modal -->')]
    removed_copy = [
        "Save it for later or save and apply it now.",
        "Presets remember these filters and print settings for future delivery lists.",
        "Glass types include the Lookup Manager product-name library.",
        "Name the preset and choose whether it should open by default.",
        "Current filters and output settings.",
        "Choose scan state.",
        "Choose attention type.",
        "Choose destination.",
        "Choose product type.",
    ]
    for text in removed_copy:
        assert text not in html
        assert text not in app

    assert 'print-preset-modal-v234' in preset_html
    assert 'print-preset-workspace-v234' in preset_html
    assert 'id="printPresetLiveSummary"' not in preset_html
    assert 'Preset Summary' not in preset_html
    assert 'data-preset-glass-search' not in app
    assert 'applyPrintPresetGlassSearch' not in app
    assert preset_html.index('print-preset-options-card-v227') < preset_html.index('print-preset-actions-card-v227')

    ownership_css = css[css.rindex('/* v0.234 Create Preset simplification') :]
    assert 'grid-template-columns: minmax(0, 1.82fr) minmax(270px, .72fr);' in ownership_css
    assert 'background: linear-gradient(135deg, #0b4e82' in ownership_css
    assert '.print-preset-options-card-v227' in ownership_css
    assert '.print-preset-actions-card-v227' in ownership_css

    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.234 - Create Preset Simplification and Theme Alignment' in changelog



def test_v0235_startup_safe_create_preset_event_wiring():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert "renderPrintPresetLiveSummary" not in app
    assert "function wireOptionalStartupFeature(featureName, setup)" in app
    assert "function addOptionalUiEventListener(target, eventName, handler, options)" in app
    assert "function wirePrintPresetEvents()" in app
    assert 'wireOptionalStartupFeature("Create Preset", wirePrintPresetEvents);' in app
    assert 'typeof handler !== "function"' in app
    assert "The rest of the webapp is still available." in app

    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.235 - Startup-Safe Create Preset Event Wiring" in changelog


def test_v0236_print_filter_cleanup_and_persistent_smart_search():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    print_panel = html[html.index('id="printOptionsPanel"'):html.index('id="printPresetModalBackdrop"')]
    for removed_text in (
        "Grouped by Mirror, Tempered, and Annealed for faster selection",
        "Airport includes every outbound item. Select destination routes for focused lists.",
        "Find priority or changed pieces",
        "Select one or more scan states",
    ):
        assert removed_text not in print_panel

    assert 'id="printGlassSearch"' not in print_panel
    assert "printGlassSearch" not in app
    assert "applyPrintGlassSearch" not in app
    assert "print-glass-search-empty-v197" not in app
    assert "print-compact-search-v197" not in print_panel

    assert 'class="print-search-result-info-v236"' in app
    assert 'class="print-search-result-meta-v236"' in app
    assert "formatDisplayDate(entry.deliveryDate" in app
    add_block = app[app.index("function addPrintSelectedOrder"):app.index("function removePrintSelectedOrder")]
    assert add_block.count("renderPrintSearchSuggestions();") == 2
    assert add_block.count("focus({ preventScroll: true })") == 2
    assert "hidePrintSearchSuggestions();" not in add_block
    assert 'els.printSearchInput.value = ""' not in add_block

    assert ".print-search-result-info-v236" in css
    assert ".print-search-result-meta-v236" in css
    assert "min-height: 24px;" in css
    assert "width: auto;" in css

    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.236 - Print Filter Cleanup and Persistent Smart Search" in changelog



def test_v0237_persistent_smart_search_and_dynamic_glass_family_presets():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    event_block = app[app.index('els.printSearchSuggestions?.addEventListener("click"'):app.index('els.printSelectedOrdersList?.addEventListener("click"')]
    assert "event.stopPropagation();" in event_block
    document_click_block = app[app.index('document.addEventListener("click", (event) => {', app.index('els.printSearchSuggestions?.addEventListener("click"')):app.index('els.printRouteOptions?.addEventListener("change"')]
    assert "clickedSmartSearch" in document_click_block
    assert "eventPath.includes(els.printSearchSuggestions)" in document_click_block
    assert "min-width: 74px;" in css
    assert "min-height: 30px;" in css
    assert "font-size: 9.5px;" in css

    assert 'data-preset-glass-family="${escapeHtml(value)}"' in app
    assert "glassFamilies: Object.freeze([])" in app
    assert "state.printGlassFamilies" in app
    assert "state.printGlassRuleTypes" in app
    assert "printGlassMatchesFamilyRule" in app
    assert "hasPrintGlassSelectionRule" in app
    assert "A semantic family preset may legitimately match zero products on one date." in app
    assert "glassFamilies: allGlass ? [] : glassFamilies" in app
    assert ".print-preset-glass-family-v237" in css

    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.237 - Persistent Smart Search and Dynamic Glass-Family Presets" in changelog



def test_v0238_print_workspace_interaction_polish():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    for marker in (
        "print-options-panel-v238",
        "print-options-hero-v238",
        "print-filter-pane-v238",
        "print-preview-pane-v238",
        "print-preset-backdrop-v238",
        "print-preset-modal-v238",
        "print-preset-hero-v238",
        "print-preset-workspace-v238",
    ):
        assert marker in html

    assert "@media (hover: hover)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".print-filter-pane-v238 .print-filter-chip-v197:hover:not(.is-unavailable)" in css
    assert ".print-options-panel-v238 button:focus-visible" in css
    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.238 - Print Workspace Interaction Polish" in changelog


def test_v0239_stable_surfaces_and_business_week_labels():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert ".print-options-hero-v238::after" not in css
    assert ".print-preset-hero-v238::after" not in css
    assert ".print-preset-hero-v238::before" not in css
    assert ".print-filter-pane-v238 .print-filter-section-v197:hover" not in css
    assert ".print-preset-modal-v238 .print-preset-card-v227:hover" not in css
    assert ".print-preview-pane-v238 .print-preview-toolbar-v197:hover" not in css
    assert "Ready to create a reusable print setup." not in css

    assert "Monday-Friday business-week range" in app
    week_range_block = app[app.index("function printQuickDateWeekRange"):app.index("function printQuickDateWeekLabel")]
    assert "printQuickDateShift(start, 4)" in week_range_block
    assert "printQuickDateShift(start, 6)" not in week_range_block

    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.239 - Stable Workspace Surfaces and Business-Week Labels" in changelog




def test_v0240_consistent_header_rings_compact_preset_and_control_focus():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    for marker in (
        "print-options-panel-v240",
        "print-options-hero-v240",
        "print-preset-modal-v240",
        "print-preset-hero-v240",
        "print-preset-workspace-v240",
    ):
        assert marker in html

    ownership_css = css[css.rindex("/* v0.240 consistent header rings") :]
    assert ".print-options-hero-v240::after" in ownership_css
    assert ".print-preset-hero-v240::after" in ownership_css
    assert "border: 28px solid rgba(255, 255, 255, .075);" in ownership_css
    assert "background: linear-gradient(118deg, #071a49" in ownership_css
    assert "height: min(900px, calc(100vh - 20px));" in ownership_css
    assert "overflow-y: hidden;" in ownership_css
    assert "@media (max-width: 900px), (max-height: 720px)" in ownership_css
    assert ".print-preset-filter-row-v227.is-attention .print-preset-choice-v227:hover" in ownership_css
    assert ".print-preset-modal-v240 label:has(input:focus-visible)" in ownership_css
    assert ".print-options-panel-v240 .print-search-field-v197:focus-within" in ownership_css
    assert "box-shadow: none;" in ownership_css

    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.240 - Consistent Header Rings and Compact Preset Workspace" in changelog



def test_v0241_preset_deletion_and_default_name():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    script = (root / "static/js/app.js").read_text(encoding="utf-8")
    assert 'const PRINT_SYSTEM_DEFAULT_PRESET_NAME = "Default";' in script
    assert 'const PRINT_LEGACY_SYSTEM_DEFAULT_PRESET_NAME = "System Default";' in script
    assert 'data-custom-delete-action="print-preset"' in script
    assert 'async function deletePrintPreset(name)' in script
    assert 'custom-option-delete' in script
    assert '>Default</option>' in script
    assert 'System Default · All Items' not in script
    assert 'static/js/app.js?v=20260817-v0.324' in html


def test_v0241_shared_close_button_and_glass_columns():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    print_css = (root / "static/css/print.css").read_text(encoding="utf-8")
    script = (root / "static/js/app.js").read_text(encoding="utf-8")
    assert 'class="print-options-close-v197 gui-close-button"' in html
    assert 'id="printPresetModalClose" class="gui-close-button"' in html
    assert 'gui-close-button:is(#_sharedCloseA, *)' in shared
    assert 'background: linear-gradient(180deg, #e65f6e' in shared
    assert 'grid-template-columns: minmax(0, 1fr);' in print_css
    assert 'print-preset-glass-check-v241' in script
    assert 'grid-template-columns: minmax(0, 1fr) 18px;' in print_css



def test_v0242_preset_delete_dialog_and_success_feedback():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    delete_block = app[app.index("async function deletePrintPreset(name)"):app.index("/** Apply one saved preset")]
    assert "window.confirm" not in delete_block
    assert "await confirmWebAppAction" in delete_block
    assert 'confirmLabel: "Delete Preset"' in delete_block
    assert 'playAppSound("save")' in delete_block
    assert "showActionFeedback" in delete_block
    assert 'title: "Preset deleted"' in delete_block
    assert "## v0.242 - Preset Dialog and Adaptive Glass Layout Polish" in changelog


def test_v0242_adaptive_glass_controls_and_save_icon():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "print-preset-modal-v242" in html
    assert "print-preset-save-icon-v242" in html
    assert ">ϟ<" not in html
    assert 'data-preset-copies type="text" inputmode="numeric"' in app
    assert 'data-preset-copies type="number"' not in app
    assert ".print-preset-modal-v242 .print-preset-glass-category-v232" in css
    assert "align-self: start;" in css
    assert "height: auto;" in css
    assert "white-space: normal;" in css
    assert "overflow-wrap: anywhere;" in css
    assert "font-size: 11.5px;" in css
    assert "grid-template-columns: minmax(0, 1fr) 20px;" in css
    assert ".print-preset-save-icon-v242::before" in css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "static/css/print.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html



def test_v0243_formatted_xlsx_and_raw_csv_exports():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")
    logo = root / "static/images/barefoot-company-builders-firstsource-print-logo.png"

    assert logo.is_file() and logo.stat().st_size > 1000
    assert 'function buildFormattedPrintWorkbookBytes(' in app
    assert 'function exportFormattedPrintXlsx(' in app
    assert 'function exportRawPrintCsv(' in app
    assert 'PRINT_XLSX_CONTENT_TYPE' in app
    assert 'PRINT_XLSX_LOGO_PATH = "static/images/barefoot-company-builders-firstsource-print-logo.png?v=20260817-v0.324"' in app
    assert 'one formatted worksheet per normal' in readme
    assert '"List ID", "Line Item ID", "Order", "Item", "Job", "Customer"' in app
    assert '<drawing r:id="rId1"/>' in app
    assert '<pageSetup paperSize="1" orientation="${orientation}" fitToWidth="1" fitToHeight="0"' in app
    assert 'if (selectedMode === "xlsx") await exportFormattedPrintXlsx(localPreview);' in app
    assert 'else exportRawPrintCsv(localPreview);' in app
    submit_start = app.index('async function submitPrintOptions(')
    submit_end = app.index('async function importTempDeliveryFolder()', submit_start)
    submit = app[submit_start:submit_end]
    assert '/api/export/package.xlsx' not in submit
    assert '/api/export/package.csv' not in submit
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.243 - Formatted Excel Export and Shared Webapp Controls' in changelog


def test_v0243_shared_primary_and_close_button_system():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")

    assert 'button.app-primary-button' in shared
    assert '--shared-primary-top: #2e6aa5;' in shared
    assert '--shared-primary-shadow:' in shared
    assert 'background: linear-gradient(180deg, var(--shared-primary-top)' in shared
    assert 'id="printOptionsSubmit" class="print-primary-action-v197 app-primary-button is-print"' in html
    assert 'button.gui-close-button' in shared
    assert '--shared-close-size: 49px;' in shared
    assert 'width: var(--shared-close-size) !important;' in shared
    assert 'height: var(--shared-close-size) !important;' in shared
    assert 'border-radius: 11px !important;' in shared
    assert 'background: linear-gradient(180deg, #e65f6e' in shared
    assert 'background-color: #fff !important;' in shared
    assert 'old-bay-review-dismiss gui-close-button' in app
    assert 'automation-update-toast-close gui-close-button' in app


def test_v0244_beveled_primary_actions_and_larger_close_controls():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    for button_id in (
        "headerGlobalSearchBtn",
        "globalPrintExportBtn",
        "scanRackCompleteBtn",
        "scanRackPrintBtn",
        "rackPackingHistoryBtn",
        "bayCheckBtn",
    ):
        tag_start = html.rfind("<button", 0, html.index(f'id="{button_id}"'))
        tag_end = html.index(">", html.index(f'id="{button_id}"'))
        assert "app-primary-button" in html[tag_start:tag_end]

    assert "0 3px 0 var(--shared-primary-edge)" in shared
    assert "background: linear-gradient(180deg, var(--shared-primary-top)" in shared
    assert "#rackPackingHistoryBtn.app-primary-button" in racks
    assert "pointer-events: auto !important;" in racks
    assert "--shared-close-size: 49px;" in shared
    assert "button.gui-close-button" in shared
    assert "::before" in shared
    assert "background-color: #2f4865 !important;" in shared
    assert "background: linear-gradient(180deg, #e65f6e" in shared
    assert "background-color: #fff !important;" in shared
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert "## v0.244 - Beveled Actions and Rack GUI Visual Identity" in changelog

def test_v0244_rack_detail_and_history_header_identity():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")

    assert 'class="operations-modal-visual-icon"' in html
    assert "function rackSetVisualHue(value)" in app
    assert "function rackSetVisualIcon(value)" in app
    assert "function applyRackOperationsVisual(rack)" in app
    assert "function applyRackHistoryOperationsVisual()" in app
    assert 'els.operationsModal.dataset.rackIcon = "history";' in app
    assert "applyRackOperationsVisual(rack);" in app
    assert "applyRackHistoryOperationsVisual();" in app
    assert 'style="--rack-set-hue:${escapeHtml(setHue)}"' in app

    ownership = racks[racks.rindex("RACK MODAL POLISH AND ICON OWNERSHIP") :]
    assert '.operations-modal-panel[data-kind="rack-details"] .operations-modal-heading::after' in ownership
    assert '.operations-modal-panel[data-kind="rack-history"] .operations-modal-heading::after' in ownership
    assert "border: 28px solid rgba(255, 255, 255, .095);" in ownership
    assert '.operations-modal-panel[data-rack-icon="truck"]' in ownership
    assert '.operations-modal-panel[data-rack-icon="history"]' in ownership
    assert '.operations-modal-panel[data-rack-icon="aluminum"]' in ownership
    assert '.operations-modal-panel[data-rack-icon="steel"]' in ownership
    assert '.operations-modal-panel[data-rack-icon="coral"]' in ownership
    assert '.rack-set-card[data-rack-icon="truck"]' in ownership
    assert ".rack-modal-date-group:hover" in ownership

def test_v0245_final_shared_controls_and_requested_action_migration():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'static/css/shared-ui.css?v=20260817-v0.324' in html
    assert html.index('static/css/shared-ui.css?v=20260817-v0.324') > html.index('static/css/shell.css?v=20260731-v0.192')
    for button_id in (
        "headerGlobalSearchBtn",
        "bayCheckBtn",
        "rackEditOpenBtn",
        "bayManualSubmitBtn",
        "bayUndoBtn",
        "bayRedoBtn",
        "bayLayoutUndoBtn",
        "bayLayoutRedoBtn",
        "scanRackPrintBtn",
    ):
        tag_start = html.rfind("<button", 0, html.index(f'id="{button_id}"'))
        tag_end = html.index(">", html.index(f'id="{button_id}"'))
        assert "app-primary-button" in html[tag_start:tag_end]

    assert 'Physical floor view' not in app
    assert 'Open Manage Items</button>' not in app
    assert 'class="app-primary-button admin-pager-primary" data-admin-import-page=' in app
    assert ':is(#_sharedPrimaryA, *):is(#_sharedPrimaryB, *):is(#_sharedPrimaryC, *)' in shared
    assert ':focus:not(:disabled)' not in shared
    assert ':focus-visible:not(:disabled)' in shared
    assert 'color: #fff !important;' in shared
    assert 'background: linear-gradient(180deg, #3c78b2' in shared
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.247 - CSS Ownership Cleanup and Stable Shared Controls' in changelog

def test_v0245_close_geometry_and_rack_icon_separation():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")

    assert '--shared-close-size: 49px;' in shared
    assert 'body button.gui-close-button:is(#_sharedCloseA, *)' in shared
    assert 'content: "" !important;' in shared
    assert '-webkit-mask: url("data:image/svg+xml' in shared
    assert 'width: var(--shared-close-icon-size) !important;' in shared
    assert 'height: var(--shared-close-icon-size) !important;' in shared
    assert 'background: linear-gradient(180deg, #e65f6e' in shared
    assert 'rack-set-card' not in shared
    assert 'body .rack-set-card .rack-set-icon::before' in racks
    assert 'body .rack-set-card .rack-set-icon::after' in racks
    assert 'body .operations-modal-panel[data-rack-icon="coral"] .operations-modal-visual-icon::before' in racks
    assert 'Coral means a glass holding bay' in racks
    assert 'if (/coral/.test(label)) return 39;' in app
    assert 'if (/coral/.test(label)) return "coral";' in app

def test_v0246_square_close_buttons_and_distinct_rack_set_icons():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")

    assert 'inline-size: var(--shared-close-size) !important;' in shared
    assert 'aspect-ratio: 1 / 1 !important;' in shared
    assert 'left: 50% !important;' in shared
    assert 'top: 50% !important;' in shared
    assert 'transform: translate(-50%, -50%) !important;' in shared
    assert 'background-color: #2f4865 !important;' in shared
    assert 'data-rack-icon="${escapeHtml(setIcon)}"' in app
    assert 'rack-set-icon ${escapeHtml(setClass)}' not in app
    for token in ('return "lr";', 'return "rr";', 'return "showers";', 'return "mirror";', 'return "bfs-mirror";', 'return "framed-mirror";', 'return "crl";', 'return "spacer";'):
        assert token in app
    assert '.rack-set-card[data-rack-icon="showers"] .rack-set-icon::before' in racks
    assert '.rack-set-card[data-rack-icon="mirror"] .rack-set-icon::before' in racks
    assert '.operations-modal-panel[data-rack-icon="showers"] .operations-modal-visual-icon::before' in racks
    assert '.operations-modal-panel[data-rack-icon="mirror"] .operations-modal-visual-icon::before' in racks


def test_v0247_css_ownership_and_stable_shared_controls():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    styles = (root / "static/css/styles.css").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    print_css = (root / "static/css/print.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")
    admin = (root / "static/css/admin.css").read_text(encoding="utf-8")
    bays = (root / "static/css/bays.css").read_text(encoding="utf-8")
    rejects = (root / "static/css/rejects.css").read_text(encoding="utf-8")

    assert '.gui-close-button' not in styles
    assert 'v0.241 preset deletion' not in styles
    assert 'PRINT / EXPORT AND CREATE PRESET OWNERSHIP - v0.247' in print_css
    assert 'RACK MODAL POLISH AND ICON OWNERSHIP - v0.247' in racks
    assert 'rack-set-card' not in shared
    assert '.operations-modal-visual-icon' not in shared
    assert 'background-color: #2f4865 !important;' in shared
    assert ':focus-visible' in shared
    assert 'gui-close-button:is(#_sharedCloseA, *)' in shared
    assert '.delivery-automation-close,' in admin
    assert 'width: 38px;' not in admin[admin.rindex('/* ADMIN CLOSE-BUTTON POSITIONING - v0.247 */'):]
    assert 'BAY GUI CLOSE-BUTTON POSITIONING - v0.247' in bays
    assert 'REJECT GUI CLOSE-BUTTON POSITIONING - v0.247' in rejects
    assert '<button id="scanRackPrintBtn" class="app-primary-button"' in html
    assert 'static/css/print.css?v=20260817-v0.324' in html
    assert 'static/css/racks.css?v=20260817-v0.324' in html
    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'static/css/bays.css?v=20260817-v0.324' in html
    assert 'static/css/shared-ui.css?v=20260817-v0.324' in html


def test_v0248_bay_rack_pager_and_update_review_polish():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    styles = (root / "static/css/styles.css").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    bays = (root / "static/css/bays.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")
    admin = (root / "static/css/admin.css").read_text(encoding="utf-8")
    scan = (root / "static/css/scan.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")

    assert 'Physical floor view' not in app
    assert 'Open Manage Items</button>' not in app
    assert 'Showing all ${countable.length} physical bays' not in app
    assert 'Search and filter controls are tucked into one compact bar.' not in app
    assert 'id="bayActiveFilterBar" aria-live="polite" hidden' in html
    assert 'els.bayActiveFilterBar.hidden = !shouldShowSummary;' in app
    assert '--app-icon-primary-width: 26px;' in bays
    assert '--app-primary-min-height: 30px;' in bays
    assert '.bay-map-helper-v17' not in bays

    assert 'class="admin-import-run-pager-actions"' in app
    assert 'justify-items: center;' in admin
    assert '--app-primary-min-height: 32px;' in admin
    assert 'admin-pager-primary' not in shared

    assert 'body .rack-set-card .rack-set-icon::after' in racks
    assert 'content: none !important;' in racks
    assert '.rack-set-card[data-rack-icon="showers"] .rack-set-icon::before' in racks
    assert '.rack-set-card[data-rack-icon="coral"] .rack-set-icon::before' in racks

    assert '.scan-update-review-control' not in styles
    assert '.line-update-review-prompt-shell' not in styles
    assert 'v0.248 New/updated review notification ownership' in scan
    assert 'class="scan-update-reviewed-button app-primary-button"' in html
    assert 'UPDATE_PROMPT_TIMEOUT_MS = 10000' in app
    assert 'data-update-prompt-time' in app
    assert 'currentPromptTimer = window.setTimeout(closeUpdatePrompt, UPDATE_PROMPT_TIMEOUT_MS);' in app
    assert 'APPLICATION_VERSION = "324"' in contract


def test_v0249_guided_racks_scan_header_and_week_grouping():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    bays = (root / "static/css/bays.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")
    scan = (root / "static/css/scan.css").read_text(encoding="utf-8")
    admin = (root / "static/css/admin.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")

    date_pos = html.index('id="deliveryDateSelect"')
    station_pos = html.index('id="stationProfileDisplay"')
    stage_pos = html.index('id="deliveryStageSelect"')
    assert date_pos < station_pos < stage_pos
    assert '<span>Assigned station</span>' not in html
    assert 'function scanStageLabel(list)' in app
    for label in ('return "Staging";', 'return "Outbound";', 'return "Indian Trail";', 'return "CPU";', 'return "DTC";', 'return "Greenville";'):
        assert label in app
    assert 'function groupedDeliveryDateOptions(groups, optionHtml)' in app
    assert 'deliveryBusinessWeekLabel' in app
    assert 'els.deliveryDateSelect.innerHTML = groupedDeliveryDateOptions' in app
    assert 'els.deleteDateSelect.innerHTML = groupedDeliveryDateOptions' in app

    assert '--shared-close-size: 49px;' in shared
    assert '--shared-close-icon-size: 20px;' in shared
    assert 'button[data-bay-action="layout"]' in bays
    assert 'grid-template-columns: repeat(5, minmax(0, 1fr)) !important;' in bays
    assert 'background: var(--bay-action-surface) !important;' in bays
    assert 'class="rack-manager-create-grid"' in app
    assert 'rack-manager-create-icon rack-set-create-icon' in app
    assert 'rack-manager-create-icon rack-create-icon' in app
    assert '.rack-manager-create-card' in racks
    assert '.rack-manager-group-icon' in racks
    assert 'grid-template-columns: 120px minmax(150px, 1fr) 120px;' in scan
    assert '--app-primary-min-height: 28px;' in admin
    assert 'statusPill.hidden = !Boolean(profile.showStatus);' in app
    assert 'APPLICATION_VERSION = "324"' in contract


def test_v0250_numeric_dates_centered_scan_and_bay_status_clarity():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    scan = (root / "static/css/scan.css").read_text(encoding="utf-8")
    home = (root / "static/css/home.css").read_text(encoding="utf-8")
    bays = (root / "static/css/bays.css").read_text(encoding="utf-8")
    print_css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")

    assert 'function formatNumericDeliveryDate(value)' in app
    assert 'return `${parsed.getMonth() + 1}/${parsed.getDate()}/${parsed.getFullYear()}`;' in app
    assert 'function deliveryDateGroupsByBusinessWeek(groups)' in app
    assert 'class="home-delivery-week"' in app
    assert 'formatNumericDeliveryDate(group.date)' in app
    assert 'formatNumericDeliveryDate(date)' in app

    assert 'grid-template-columns: 120px minmax(150px, 1fr) 120px;' in scan
    assert 'text-align-last: center;' in scan
    assert 'class="app-primary-button" type="submit">Sign in</button>' in html
    assert '--shared-primary-bottom: #05265c;' in shared

    assert '.home-delivery-week-heading' in home
    assert 'grid-template-columns: repeat(5, minmax(0, 1fr)) !important;' in bays
    assert 'bay-state.status-available' in bays
    assert 'bay-state.status-occupied' in bays
    assert 'bay-state.status-preassigned' in bays
    assert '<b>${escapeHtml(occupied)}/${escapeHtml(totalBays)}</b>' in app
    assert 'left: 7px !important;' in bays

    assert 'v0.250 Print / Export category-gradient button system' not in print_css
    assert '--print-chip-gradient-end' not in print_css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html


def test_v0251_flat_bay_actions_and_compact_scan_selectors():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    scan = (root / "static/css/scan.css").read_text(encoding="utf-8")
    bays = (root / "static/css/bays.css").read_text(encoding="utf-8")
    print_css = (root / "static/css/print.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")

    assert 'v0.251 Compact, optically centered Scan context controls' in scan
    assert 'grid-template-columns: 120px minmax(150px, 1fr) 120px;' in scan
    assert 'width: 120px;' in scan
    assert 'height: 38px;' in scan
    assert 'line-height: 1.25;' in scan
    assert 'position: absolute;' in scan
    assert 'translate: 0 -50%;' in scan

    assert 'v0.251 Single-row Bay Map action controls without category gradients' in bays
    assert 'grid-template-columns: repeat(5, minmax(74px, 1fr)) !important;' in bays
    assert 'grid-template-rows: 54px !important;' in bays
    assert 'background: var(--bay-action-surface) !important;' in bays
    assert 'grid-template-columns: repeat(3, minmax(0, 1fr)) !important;' not in bays[bays.index('/* v0.251 Single-row Bay Map action controls'): ]
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr)) !important;' not in bays[bays.index('/* v0.251 Single-row Bay Map action controls'): ]

    assert 'v0.250 Print / Export category-gradient button system' not in print_css
    assert '--print-chip-gradient-end' not in print_css
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html


def test_v0252_uniform_bay_actions_and_sidebar_aligned_primary_buttons():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    bays = (root / "static/css/bays.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    current_bay_owner = bays[bays.index('/* v0.251 Single-row Bay Map action controls'):]
    assert 'grid-template-columns: repeat(5, minmax(74px, 1fr)) !important;' in current_bay_owner
    assert 'grid-template-rows: 54px !important;' in current_bay_owner
    assert 'grid-column: auto !important;' in current_bay_owner
    assert 'grid-row: 1 !important;' in current_bay_owner
    assert 'height: 54px !important;' in current_bay_owner
    assert 'min-height: 54px !important;' in current_bay_owner
    assert 'max-height: 54px !important;' in current_bay_owner

    assert '--shared-primary-top: #12467f;' in shared
    assert '--shared-primary-mid: #0a3568;' in shared
    assert '--shared-primary-bottom: #05265c;' in shared
    assert '--shared-primary-border: #041f4d;' in shared
    assert 'background: linear-gradient(180deg, #1b5896 0%, #0d427c 46%, #07306c 100%) !important;' in shared
    assert 'background: linear-gradient(180deg, #0a3568 0%, #041f4d 100%) !important;' in shared

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/bays.css?v=20260817-v0.324' in html
    assert 'static/css/shared-ui.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.253 - Statistics Dashboard Hierarchy and Chart Explorer Polish' in changelog



def test_v0256_statistics_data_plumbing_remains_available_after_inline_workspace_upgrade():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")

    assert 'function glassQuantitiesForStatistics(overviewLists)' in app
    assert 'function selectedRangeRemakeStats(overviewLists = [])' in app
    assert 'function statisticsChartDataset(metric = state.homeChartMetric)' in app
    assert 'function renderStatisticsPage()' in app
    assert 'function renderStatisticsAnalytics()' in app
    assert 'statistics-chart-modal-v0256' not in statistics_css


def test_v0256_application_revision_does_not_change_the_five_migration_schema_contract():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations_path = ROOT / "database" / "migrations.py"

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'Frontend-only releases must advance APPLICATION_VERSION without changing this value.' in contract

    if migrations_path.is_file():
        migrations = migrations_path.read_text(encoding="utf-8")
        versions = [int(value) for value in re.findall(r"Migration\(\s*(\d+)\s*,", migrations)]
        assert versions == sorted(set(versions))
        assert versions == list(range(1, max(versions) + 1))
        assert max(versions) == 5

        contract_version = int(re.search(r"CURRENT_SCHEMA_VERSION\s*=\s*(\d+)", contract).group(1))
        assert contract_version == max(versions)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    assert 'Current SQLite schema contract: **5**.' in readme
    assert '## v0.256 - Calm Statistics Dashboard and Progressive Chart Explorer' in changelog



def test_v0257_statistics_remains_a_dedicated_page_and_home_is_not_overloaded():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    home_css = (ROOT / "static" / "css" / "home.css").read_text(encoding="utf-8")

    home_section = html[html.index('id="homePage"'):html.index('id="statisticsPage"')]
    statistics_section = html[html.index('id="statisticsPage"'):html.index('id="scanPage"')]

    assert 'data-page-target="statistics"' in html
    assert 'id="overviewStats"' not in home_section
    assert 'id="overviewStats"' in statistics_section
    assert 'v0.257 Dedicated Statistics page extraction' in home_css


def test_v0258_inline_live_statistics_workspace_replaces_modal_and_avoids_duplicate_data():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    statistics_section = html[html.index('id="statisticsPage"'):html.index('id="scanPage"')]
    assert 'class="page-view statistics-page statistics-page-v0258"' in html
    assert 'id="statisticsAnalyticsWorkspace"' in statistics_section
    assert 'id="statisticsChartCanvas"' in statistics_section
    assert 'id="statisticsMiniCharts"' in statistics_section
    assert 'data-statistics-view="bar"' in statistics_section
    assert 'data-statistics-view="line"' in statistics_section
    assert 'data-statistics-view="donut"' in statistics_section
    assert 'data-statistics-view="table"' in statistics_section
    assert 'value="incomplete"' in statistics_section
    assert 'value="stage-open"' in statistics_section
    assert 'value="date-completion"' in statistics_section
    assert 'value="actions"' in statistics_section
    assert 'id="statsChartModal"' not in html
    assert 'statsChartBackdrop' not in html
    assert 'statistics-workflow-card-v0257' not in statistics_section
    assert 'statistics-attention-card-v0257' not in statistics_section

    assert 'function renderStatisticsAnalytics()' in app
    assert 'function statisticsLineChartHtml(dataset, entries)' in app
    assert 'function statisticsDataTableHtml(dataset, entries, total)' in app
    assert 'function renderStatisticsMiniCharts()' in app
    assert 'function statisticsDateBuckets(overviewLists = [])' in app
    assert 'renderStatisticsChartModal' not in app
    assert 'openStatisticsChartModal' not in app
    assert 'closeStatisticsChartModal' not in app
    assert 'homeChartMetric: "glass"' in app
    assert 'homeChartView: "donut"' in app
    assert 'homeChartLimit: "10"' in app

    assert '.statistics-analytics-workspace-v0258' in statistics_css
    assert '.statistics-chart-line-path' in statistics_css
    assert '.statistics-data-table-v0258' in statistics_css
    assert '.statistics-support-grid-v0258' in statistics_css
    assert '.statistics-chart-modal' not in statistics_css
    assert 'body button.app-primary-button' in shared_css

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/statistics.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.258 - Inline Live Statistics Analytics Workspace' in changelog


def test_v0259_statistics_chart_density_sidebar_icon_and_stable_native_range_control():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'data-page-target="statistics"' in html
    assert '<span class="top-nav-icon statistics"></span>' in html
    assert '.top-nav-icon.statistics {' in statistics_css
    assert '-webkit-mask:' in statistics_css[statistics_css.index('.top-nav-icon.statistics {'):statistics_css.index('.statistics-page-v0258 {')]

    assert 'id="overviewRangeSelect" data-native-select="true" aria-label="Statistics date range"' in html
    assert 'select#overviewRangeSelect' in statistics_css
    assert 'background-color: #0a4478 !important;' in statistics_css
    assert 'background-color: #11518e !important;' in statistics_css
    assert '.statistics-range-control-v0258 .custom-select-trigger {' not in statistics_css

    assert 'const rowHeight = 28;' in app
    assert 'const size = 280;' in app
    assert 'const height = 300;' in app
    assert 'min-height: 48px;' in statistics_css
    assert 'min-height: 330px;' in statistics_css
    assert 'max-height: 400px;' in statistics_css

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/statistics.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.259 - Dense Statistics Workspace and Stable Range Control' in changelog



def test_v0260_compact_glass_first_statistics_breakage_reporting_and_progressive_data_reveal():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    statistics_section = html[html.index('id="statisticsPage"'):html.index('id="scanPage"')]
    assert '<option value="glass" selected>Glass type quantity</option>' in statistics_section
    assert 'data-statistics-view="donut" aria-pressed="true"' in statistics_section
    assert 'id="statsChartLimitSelect"' in statistics_section
    assert '<option value="10" selected>Top 10</option>' in statistics_section
    assert 'id="statsChartShowMoreBtn"' in statistics_section
    assert '>Show more data<' in statistics_section
    assert 'id="statsIncludeExternalRemakes" type="checkbox"' in statistics_section
    assert 'value="breakage-machines"' in statistics_section
    assert 'value="breakage-glass"' in statistics_section
    assert 'value="breakage-reasons"' in statistics_section
    assert 'value="breakage-rate"' in statistics_section

    assert 'homeChartMetric: "glass"' in app
    assert 'homeChartView: "donut"' in app
    assert 'homeChartLimit: "10"' in app
    assert 'statisticsIncludeExternalRemakes: false' in app
    assert 'function statisticsNextDisplayLimit(currentValue = state.homeChartLimit)' in app
    assert 'state.homeChartLimit = statisticsNextDisplayLimit(state.homeChartLimit);' in app
    assert 'function statisticsStageShortLabel(stageOrCategory)' in app
    for label in ('"Staging"', '"Outbound"', '"Inbound"', '"CPU"', '"Greenville"', '"DTC"'):
        assert label in app
    assert 'function statisticsBreakageGlassRows(includeExternal = state.statisticsIncludeExternalRemakes)' in app
    assert 'const SPANISH_UI_V260 = new Map([' in app
    assert '["Show more data", "Mostrar más datos"]' in app
    assert 'function selectedRangeBreakageStats()' in app
    assert 'Breakage cost by machine' in app
    assert 'Internal breakage by machine' in app
    assert 'Breakage by glass type' in app
    assert 'statistics-data-table-v0258 is-breakage-v0260' in app
    assert 'statistics-breakage-metrics-v0263' in app

    assert 'const rowHeight = 28;' in app
    assert 'const size = 280;' in app
    assert 'const height = 300;' in app
    assert 'font-size: 8px;' in statistics_css
    assert 'max-height: none;' in statistics_css
    assert '.statistics-show-more-row-v0260' in statistics_css
    assert '.statistics-remake-toggle-v0260' in statistics_css

    assert 'GLASS_COST_PER_SQFT = {' in store
    for label, rate in (
        ('"3/8 Clear": 1.83', 1.83),
        ('"1/2 Clear": 2.11', 2.11),
        ('"1/4 Clear": 0.96', 0.96),
        ('"3/8 UltraClear": 4.78', 4.78),
        ('"1/4 Mirror": 2.60', 2.60),
        ('"1/8 Clear": 2.47', 2.47),
        ('"1/4 French Antique Mirror": 20.93', 20.93),
        ('"1/4 Summer Cloud Antique Mirror": 20.93', 20.93),
        ('"1/4 Dark Cloud Antique Mirror": 20.93', 20.93),
        ('"1/4 Rainbow Antique Mirror": 20.93', 20.93),
        ('"1/4 Hollywood Antique Mirror": 20.93', 20.93),
        ('"1/4 Woodford Antique Mirror": 20.93', 20.93),
    ):
        assert label in store
    assert 'def dimensions_square_feet(value: Any) -> float:' in store
    assert '"internalByMachine": internal_machine_rows' in store
    assert '"externalRemakesByGlass": bucket_rows(external_by_glass, "glassType")' in store
    assert '"producedTotals": produced_totals' in store
    assert '"internalPiecesPercent"' in store
    assert '"withExternalPiecesPercent"' in store

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '## v0.260 - Compact Glass-First Statistics and Breakage Analytics' in changelog



def test_v0261_admin_managed_glass_costs_feed_statistics_without_schema_change():
    """v0.261 keeps breakage pricing editable through the existing Lookup Manager storage."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.261 - Admin-Managed Glass Material Costs' in changelog

    assert '"glass_cost": {}' in store
    assert '"glassCosts": sorted(' in store
    assert 'lookup_type not in {"product", "route", "process", "glass_cost"}' in store
    assert "WHERE is_active = 1 AND type = 'glass_cost'" in store
    assert 'glass_cost_profile(raw_product, effective_glass_costs)' in store
    assert 'for label, rate in effective_glass_costs.items()' in store
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract

    assert 'manualEditLookups: { products: [], routes: [], processes: [], glassCosts: [] }' in app
    assert 'if (clean === "glass_cost") return "glassCosts";' in app
    assert '["glass_cost", "Glass costs", glassCostTotal]' in app
    assert 'id="lookupCostInput"' in app
    assert 'Save glass cost' in app
    assert 'request.rate = rate;' in app
    assert 'if (type === "glass_cost") await loadHomeReportSummary();' in app
    assert 'item.rate !== null && item.rate !== ""' in app
    assert 'grid-template-columns: repeat(4, minmax(0, 1fr));' in admin_css
    assert '.lookup-manager-list.glass-costs .lookup-type-icon' in admin_css
    assert 'Products, routes, process options, and glass cost per SQFT.' in html


def test_v0262_combined_breakage_reason_drilldown_and_custom_statistics_range():
    """v0.262 keeps breakage readable while adding machine/reason accountability and custom dates."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    statistics_section = html[html.index('id="statisticsPage"'):html.index('id="scanPage"')]
    assert '<option value="custom">Custom range…</option>' in statistics_section
    assert 'id="statisticsDateCalendar"' in statistics_section
    assert 'print-date-calendar-v201 print-date-calendar-v203 print-date-calendar-v205 statistics-date-calendar-v0262' in statistics_section
    assert 'id="statisticsCalendarLeftGrid"' in statistics_section
    assert 'id="statisticsCalendarRightGrid"' in statistics_section
    assert 'id="statisticsCalendarApply" class="primary app-primary-button"' in statistics_section

    assert 'value="breakage-machines">Machine breakage overview</option>' in statistics_section
    assert 'value="breakage-glass">Glass type breakage overview</option>' in statistics_section
    assert 'value="breakage-reasons">Reject reasons by machine</option>' in statistics_section
    for retired in ('breakage-machine-pieces', 'breakage-machine-sqft', 'breakage-machine-cost', 'breakage-glass-pieces', 'breakage-glass-sqft', 'breakage-glass-cost'):
        assert retired not in statistics_section
    assert 'id="statisticsBreakageMeasureControl"' in statistics_section
    assert 'id="statsBreakageMeasureSelect"' in statistics_section
    assert '<option value="sqft" selected>Square feet</option>' in statistics_section
    assert '<option value="pieces">Pieces</option>' in statistics_section
    assert '<option value="estimatedCost">Cost</option>' in statistics_section
    assert 'id="statisticsExternalRemakesControl"' in statistics_section
    assert 'hidden>' in statistics_section[statistics_section.index('id="statisticsExternalRemakesControl"'):statistics_section.index('id="statsChartResetBtn"')]

    assert 'statisticsBreakageMeasure: "sqft"' in app
    assert 'statisticsCustomDateFrom: ""' in app
    assert 'statisticsCustomDateTo: ""' in app
    assert 'function openStatisticsDateCalendar()' in app
    assert 'function renderStatisticsDateCalendar()' in app
    assert 'function applyStatisticsCalendarRange()' in app
    assert 'if (state.overviewRange === "custom") {' in app
    assert 'return `?dateFrom=${encodeURIComponent(dateFrom)}&dateTo=${encodeURIComponent(dateTo)}`;' in app
    assert 'dateRangeCalendarMonthButtons(leftMonth, today, availableDates, start, end, "data-statistics-calendar-date")' in app
    assert 'const breakageMeasureVisible = ["breakage-machines", "breakage-glass"].includes(state.homeChartMetric);' in app
    assert 'const externalRemakesVisible = ["breakage-machines", "breakage-glass", "breakage-rate"].includes(state.homeChartMetric);' in app
    assert 'breakageMeasureOverride || state.statisticsBreakageMeasure || "sqft"' in app
    assert 'title: "Reject reasons by machine"' in app
    assert 'statistics-breakage-drill-grid-v0262' in app
    assert 'is-combined-v0262' in app
    assert 'is-reasons-v0262' in app
    assert 'data-statistics-measure="${escapeHtml(card.measure || "")}"' in app
    assert 'if (button.dataset.statisticsMeasure) state.statisticsBreakageMeasure = button.dataset.statisticsMeasure;' in app
    assert '<th>Machine / location</th><th>Reject events</th><th>Pieces</th><th>SQFT</th><th>Estimated cost</th><th>Glass broken</th><th>Top reasons</th>' in app
    assert '<th>Glass type</th><th>Pieces</th><th>SQFT</th><th>Estimated cost</th><th>Top machines</th><th>Top reasons</th>' in app
    assert '<AppVersion>0.268</AppVersion>' in app

    assert 'internal_by_machine_reason' in store
    assert 'internal_by_machine_glass' in store
    assert 'internal_by_glass_machine' in store
    assert 'internal_by_glass_reason' in store
    assert 'internal_reason_machine_glass' in store
    assert 'def reason_rows(values: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:' in store
    assert '"reasons"] = reason_rows(internal_by_machine_reason.get(machine, {}))' in store
    assert '"glassTypes"] = bucket_rows(internal_by_machine_glass.get(machine, {}), "glassType")' in store
    assert '"machines"] = bucket_rows(internal_by_glass_machine.get(glass_type, {}), "machine")' in store
    assert '"internalReasonsByMachine": internal_reason_rows' in store
    assert 'event_count=1' in store

    assert '.statistics-date-calendar-v0262' in statistics_css
    assert '.statistics-remake-toggle-v0262' in statistics_css
    assert '.statistics-control-icon-v0258.is-measure' in statistics_css
    assert '.statistics-data-table-v0258.is-breakage-v0260.is-combined-v0262' in statistics_css
    assert '.statistics-data-table-v0258.is-breakage-v0260.is-reasons-v0262' in statistics_css
    assert '.statistics-breakage-drill-grid-v0262' in statistics_css

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/statistics.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.262 - Combined Breakage Accountability and Custom Statistics Range' in changelog


def test_v0263_restores_statistics_typography_and_reorganizes_breakage_tables():
    """v0.263 restores readable text and groups breakage accountability into clear blocks."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/statistics.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.263 - Statistics Readability and Breakage Table Hierarchy' in changelog

    assert '.statistics-analytics-title-v0258 h2 {' in statistics_css
    assert 'font-size: 21px;' in statistics_css
    assert '.statistics-data-table-v0258 {' in statistics_css
    assert 'font-size: 12px;' in statistics_css
    assert '.statistics-chart-category-label,' in statistics_css
    assert 'font-size: 13px;' in statistics_css
    assert '.statistics-chart-donut-total {' in statistics_css
    assert 'font-size: 30px;' in statistics_css
    assert 'max-height: none;' in statistics_css

    assert 'statistics-breakage-table-header-v0263' in app
    assert 'statistics-breakage-metrics-v0263' in app
    assert 'statistics-breakage-detail-list-v0263' in app
    assert 'statistics-breakage-coverage-v0263' in app
    assert 'statistics-breakage-frequency-v0263' in app
    assert 'Machine breakage accountability' in app
    assert 'Glass type breakage accountability' in app
    assert '<th>Breakage totals</th>' in app
    assert '<th>Frequency</th><th>Breakage totals</th>' in app
    assert '<th>Pieces</th><th>SQFT</th><th>Cost</th><th>Rejects</th>' not in app

    assert '.statistics-breakage-table-header-v0263' in statistics_css
    assert '.statistics-breakage-metrics-v0263' in statistics_css
    assert '.statistics-breakage-detail-list-v0263' in statistics_css
    assert '.statistics-breakage-coverage-v0263' in statistics_css
    assert '.statistics-breakage-frequency-v0263' in statistics_css



def test_v0264_statistics_visibility_scan_selector_and_review_scroll_polish():
    """v0.264 avoids nested table scrolling and keeps chart/scan labels fully readable."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/statistics.css?v=20260817-v0.324' in html
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.264 - Statistics Chart Visibility and Scan Review Polish' in changelog

    assert 'const longestLabelLength = Math.max(...entries.map((entry) => String(entry.label || "").length), 0);' in app
    assert 'Math.ceil(longestLabelLength * 7.2) + 28' in app
    assert '${escapeHtml(entry.label)}</text>' in app
    assert 'truncateChartLabel(entry.label, 22)' not in app
    assert 'const centerRadius = 58;' in app
    assert 'const totalFontSize = Math.max(14, Math.min(30' in app
    assert 'style="font-size:${totalFontSize}px"' in app

    assert '.statistics-chart-canvas-v0258 .statistics-data-table-shell-v0258 {' in statistics_css
    assert 'max-height: none;' in statistics_css
    assert 'overflow-y: visible;' in statistics_css
    assert '.statistics-chart-donut-total {' in statistics_css
    assert 'font-size: 30px;' in statistics_css

    assert 'grid-template-columns: 132px minmax(140px, 1fr) 132px;' in scan_css
    assert 'width: 132px;' in scan_css
    assert 'padding: 0 20px 0 7px;' in scan_css
    assert 'right: 7px;' in scan_css

    assert 'function nudgeUpdateReviewRowsIntoView()' in app
    assert 'const nudge = Math.min(120, Math.max(0, rect.top - 72));' in app
    assert 'window.scrollBy({ top: nudge, left: 0, behavior: "smooth" });' in app
    assert 'document.getElementById("listPanel")?.scrollIntoView({ behavior: "smooth", block: "start" });' not in app



def test_v0265_scan_stage_review_scope_markers_and_bay_group_edit_position():
    """v0.265 keeps update review per-user while adding stage markers and Airport order propagation."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    operations = (ROOT / "backend/operations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.265 - Scan Stage Review Scope and Bay Group Header Polish' in changelog

    assert 'pendingUpdateStages: new Map()' in app
    assert 'function customSelectUpdateIndicatorTitle(select, option, indicatorCount)' in app
    assert 'select?.id === "deliveryStageSelect"' in app
    assert 'state.pendingUpdateStages.get(String(list.id || ""))' in app
    assert 'const dateItemKeys = new Map();' in app
    assert 'function pendingUpdateMarkerLists(lists = state.lists)' in app
    assert 'const activeDateLists = state.lists.filter' in app
    assert 'dateItemKeys.get(deliveryDate).add(order || itemNo ? `${order}|${itemNo}`' in app
    assert 'acknowledgement?.acknowledgedListIds' in app
    assert 'refreshPendingUpdateDates({ force: true })' in app
    # v0.271 removes the grouped-bay pencil from the physical Bay Map.
    assert 'style="top:8px!important;bottom:auto!important;"' not in app

    assert 'def _airport_review_scope(stage: Any, scanner: Any) -> bool:' in operations
    assert 'scanner_text == "airport rd"' in operations
    assert 'stage_text.startswith("staging")' in operations
    assert 'stage_text.startswith("outbound")' in operations
    assert '"scope": "airport-delivery-date-batch" if airport_scope else "selected-stage"' in operations
    assert 'INSERT OR IGNORE INTO line_update_receipts' in operations
    assert '"acknowledgedListIds": sorted(value for value in target_list_ids if value)' in operations
    assert '"order": str(row["order_no"] or "")' in operations
    assert '"item": str(row["item_no"] or "")' in operations

    assert 'grid-template-columns: minmax(132px, 0.95fr) minmax(104px, 0.72fr) minmax(148px, 1.08fr);' in scan_css
    assert '.scan-page .scanner-panel-context-select-v196 .custom-select-value-indicator {' in scan_css
    assert 'position: absolute;' in scan_css
    assert 'text-overflow: clip;' in scan_css



def test_v0266_update_review_sync_scope_timeout_and_scan_selector_fit():
    """v0.266 keeps update markers current and makes Airport review authoritative by import batch/date."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    operations = (ROOT / "backend/operations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.266 - Update Review Synchronization and Scan Selector Polish' in changelog

    assert 'UPDATE_PROMPT_TIMEOUT_MS = 10000' in app
    assert 'animation: line-update-prompt-timeout-v248 10s linear forwards;' in scan_css
    assert 'const isScanContextSelect = isScanDateSelect || isScanStageSelect;' in app
    assert 'isScanStageSelect\n      ? rect.width' in app
    assert 'is-scan-context-menu' in app
    assert '.custom-select-menu.is-scan-context-menu {' in scan_css
    assert 'font-size: 15px;' in scan_css
    assert 'font-size: clamp(17px, 1.32vw, 19px);' in scan_css

    assert 'WITH latest_update_batch AS (' in operations
    assert 'SELECT source_hash, created_at, change_token' in operations
    assert 'ORDER BY id DESC' in operations
    assert 'Only the newest import/update batch for the selected stage is eligible' in operations
    assert 'n.source_hash = lub.source_hash' in operations
    assert 'n.created_at = lub.created_at' in operations
    assert "lower(COALESCE(lub.source_hash, '')) <> 'manual-entry'" in operations
    assert 'review_batches = {' in operations
    assert 'AND n.delivery_date = ?' in operations
    assert 'AND n.source_hash = ?' in operations
    assert 'occurrence_clause = " AND n.source_hash = ?"' in operations
    assert 'occurrence_clause = " AND n.source_hash = ? AND n.change_token = ?"' in operations
    broad_block = operations[operations.index('review_batches = {'):operations.index('seen_at = utc_now()', operations.index('review_batches = {'))]
    assert 'li.order_no = ?' not in broad_block
    assert 'li.item_no = ?' not in broad_block
    assert '"scope": "airport-delivery-date-batch" if airport_scope else "selected-stage"' in operations
    assert 'INSERT OR IGNORE INTO line_update_receipts' in operations



def test_v0267_scan_selector_menu_alignment_and_delivery_week_width():
    """v0.267 keeps scan dropdown rows single-line and gives week headers enough width."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.267 - Scan Selector Alignment and Delivery Week Readability' in changelog

    assert '`${formatNumericDeliveryDate(start)} - ${formatNumericDeliveryDate(end)}`' in app
    assert 'const isScanDateSelect = select.id === "deliveryDateSelect";' in app
    assert 'const isScanStageSelect = select.id === "deliveryStageSelect";' in app
    assert '? Math.max(rect.width, 244)' in app
    assert '? rect.width' in app

    assert 'width: min(100%, 480px);' in scan_css
    assert 'grid-template-columns: minmax(154px, 0.92fr) minmax(110px, 0.68fr) minmax(176px, 1.02fr);' in scan_css
    assert 'button.custom-select-trigger.has-indicator {' in scan_css
    assert 'padding-right: 49px;' in scan_css
    assert 'grid-template-columns: minmax(0, 1fr) 20px 18px !important;' in scan_css
    assert '.custom-select-menu.is-scan-context-menu .custom-select-option-check {' in scan_css
    assert 'grid-column: 3;' in scan_css
    assert '[data-select-id="deliveryDateSelect"] .custom-select-group' in scan_css
    assert 'white-space: nowrap;' in scan_css


def test_v0268_stage_selector_is_compact_indicator_is_round_and_bay_pencil_is_smaller():
    """v0.268 keeps the Scan Stage compact and preserves a true circular update marker."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.268 - Compact Stage Selector and Bay Edit Icon Polish' in changelog

    assert 'width: min(100%, 480px);' in scan_css
    assert 'grid-template-columns: minmax(154px, 0.92fr) minmax(110px, 0.68fr) minmax(176px, 1.02fr);' in scan_css
    assert 'button.custom-select-trigger.has-indicator {' in scan_css
    assert 'padding-right: 49px;' in scan_css
    assert 'width: 18px;' in scan_css
    assert 'height: 18px;' in scan_css
    assert 'aspect-ratio: 1 / 1;' in scan_css
    assert 'box-sizing: border-box;' in scan_css
    assert 'grid-template-columns: minmax(0, 1fr) 20px 18px !important;' in scan_css

    # v0.271 supersedes the v0.268 pencil by routing bay edits through Edit Bays.
    assert 'bay-section-edit-btn bay-section-edit-btn-v268' not in app
    assert '.bay-section-edit-btn-v268::before {' in scan_css
    assert 'transform: scale(0.75) !important;' in scan_css

    # Stage remains trigger-width while Date retains the separate week-header width.
    assert 'const isScanStageSelect = select.id === "deliveryStageSelect";' in app
    assert '? Math.max(rect.width, 244)' in app
    assert '? rect.width' in app



def test_v0269_scan_update_copy_rack_history_shared_buttons_and_rack_set_visuals():
    """v0.269 clarifies update notices and keeps transport/UI history without a schema migration."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    racks_css = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend/operations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/css/racks.css?v=20260817-v0.324' in html
    assert 'static/css/shared-ui.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.269 - Scan Update Clarity, Rack Transport History, and Rack Set Visuals' in changelog

    # Scan notification semantics: stage creation is distinct from an existing
    # delivery list receiving new orders. The order itself is not called updated.
    assert 'UPDATE_PROMPT_TIMEOUT_MS = 10000' in app
    assert 'eyebrow: "New stage"' in app
    assert 'title: "New stage added"' in app
    assert 'eyebrow: "Delivery list updated"' in app
    assert 'title: `${newOrders} new order${newOrders === 1 ? "" : "s"} added`' in app
    assert 'summary: `${newOrders} new order' in app
    assert 'updated: "New Orders"' in app
    assert 'data-filter="updated" type="button">New Orders' in html
    assert 'animation: line-update-prompt-timeout-v248 10s linear forwards;' in scan_css
    assert '.scan-update-review-control[data-update-kind="new-stage"]' in scan_css
    assert 'content: "NEW STAGE";' in scan_css
    assert 'content: "NEW ORDERS";' in scan_css
    assert 'border-left: 6px solid #0f5797;' in scan_css

    # Backend exposes enough list context to classify a true newly-created stage.
    assert 'dl.revision AS list_revision' in operations
    assert 'is_new_stage = bool(' in operations
    assert '"isNewStage": is_new_stage' in operations
    assert 'updated_line_count == 0' in operations
    assert 'new_line_count == len(values)' in operations

    # Cleared rack assignments remain available as muted historical locations.
    assert 'WITH rack_history AS (' in store
    assert 'ROW_NUMBER() OVER (' in store
    assert 'item["lastRackCode"]' in store
    assert 'item["lastRackRemovedAt"]' in store
    assert 'function locationIsRackHistory(item)' in app
    assert 'Previously transported in ${String(item.lastRackName || item.lastRackCode || historyLocation).trim()}' in app
    assert '.location-badge.is-rack-history' in scan_css
    assert '.location-history-stack-v269' in scan_css
    assert 'function rackHistoryLocationLabel(item)' in app
    assert 'content: " prior";' in scan_css

    # Shared blue buttons use one text size/height and Manual Scan Submit uses it.
    assert 'min-height: 38px !important;' in shared_css
    assert 'font-size: 13px !important;' in shared_css
    manual_scan = html[html.index('id="manualScanForm"'):html.index('</form>', html.index('id="manualScanForm"'))]
    assert 'class="app-primary-button" type="submit">Submit</button>' in manual_scan

    # Rack-set visuals use existing metadata rather than a migration.
    assert 'RACK_SET_VISUALS_METADATA_KEY = "rack_set_visuals_v1"' in store
    assert 'def rack_set_visuals(self, con: Any)' in store
    assert 'def save_rack_set_visual(' in store
    assert 'system_metadata_value(con, RACK_SET_VISUALS_METADATA_KEY)' in store
    assert 'self.save_rack_set_visual(con, rack_type, visual_icon, visual_color)' in store
    assert 'const RACK_SET_ICON_LIBRARY = [' in app
    assert 'rackSetIconLibraryHtml(set.icon || "rack", "rackSetModalIcon")' in app
    assert 'id="rackSetModalColor" type="color"' in app
    assert 'setIcon: document.getElementById("rackSetModalIcon")?.value || "rack"' in app
    assert 'setColor: document.getElementById("rackSetModalColor")?.value || nextRackSetVisualColor()' in app
    assert '.rack-set-icon-library-v269 {' in racks_css
    assert '.rack-set-visual-icon-v269[data-rack-icon="truck"]::before' in racks_css
    assert '.rack-set-color-control-v269 {' in racks_css

    # Old Bay notification lasts twenty seconds and visibly counts down.
    assert 'const timeoutMs = 20000;' in app
    assert 'Closes in 20s' in app
    assert 'animation: old-bay-review-timeout-v269 20s linear forwards;' in bays_css
    assert '.old-bay-review-time-v269 {' in bays_css



def test_v0270_rack_creation_workspaces_are_guided_and_return_to_manager():
    """v0.270 gives both rack creation flows a polished guided workspace and an explicit way back."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'static/css/racks.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.270 - Guided Rack Creation Workspaces' in changelog

    assert 'class="admin-form rack-modal-form rack-config-form-v270 rack-individual-form-v270"' in app
    assert 'class="admin-form rack-modal-form rack-config-form-v270 rack-set-form-v269 rack-set-form-v270"' in app
    assert app.count('data-rack-form-back') >= 4
    assert 'function returnToRackManager()' in app
    assert 'openAdminModal("racks");' in app
    assert 'function syncRackFormPreview()' in app
    assert 'function syncRackSetFormPreview()' in app
    assert 'function rackSetFormChoices(selected = "")' in app
    assert 'Create Rack Set' in app
    assert 'Create Rack' in app

    assert '/* v0.270 Guided rack creation forms' in racks_css
    assert '.rack-config-hero-v270' not in racks_css
    assert '.rack-config-layout-v270' in racks_css
    assert '.rack-config-preview-v270' in racks_css
    assert '.rack-config-actions-v270' in racks_css



def test_v0271_rack_creation_visuals_deletion_and_bay_map_cleanup():
    js = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")

    assert "rackSetColorPickerHtml(setColor)" in js
    assert 'data-rack-set-color-choice=' in js
    assert "rack-set-icon-choice-art-v271" in js
    assert '#adminModal[data-kind="rackSetForm"] button.rack-set-icon-choice-v269' in racks_css
    assert "background: #ffffff !important" in racks_css
    assert ".rack-set-color-palette-v271" in racks_css
    assert 'class="app-primary-button" data-rack-form-back>Cancel</button>' in js
    assert "Rack Configuration" not in js[js.index("function rackFormModalHtml()"):js.index("function permissionLabel", js.index("function rackFormModalHtml()"))]
    assert 'class="bay-section-edit-btn bay-section-edit-btn-v268"' not in js
    assert '#adminModal[data-kind="racks"] .rack-manager-rows' in racks_css
    assert "max-height: none !important" in racks_css
    assert "overflow: visible !important" in racks_css
    assert "COALESCE(qty, 0) > 0" in store
    assert "Rack definition deleted" in store
    assert "Rack code(s) already exist" in store
    assert "visuals.pop(rack_type.lower(), None)" in store
    assert 'data.get("rackCodes")' in store
    assert 'body: JSON.stringify({ rackCodes: racks.map((rack) => rack.code) })' in js
    assert 'APPLICATION_VERSION = "324"' in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION = 11" in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")



def test_v0272_rack_manager_collapses_icons_fit_and_packing_history_is_weekly():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'static/css/racks.css?v=20260817-v0.324' in html
    assert 'static/css/shared-ui.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '## v0.272 - Rack Manager Collapse and Packing Snapshot History' in changelog

    assert 'expandedRackManagerGroups: new Set()' in app
    assert 'details class="rack-manager-group rack-manager-group-v272"' in app
    assert 'data-rack-manager-group=' in app
    assert 'View racks' in app and 'Hide racks' in app
    assert 'rack-manager-expand-hint-v272' in racks_css

    for icon in ('glasscart', 'pallet', 'dolly', 'crate', 'warehouse'):
        assert f'["{icon}",' in app
        assert f'data-rack-icon="{icon}"' in racks_css
    assert 'grid-template-rows: 44px minmax(12px, auto) !important' in racks_css

    assert 'const PACKING_HISTORY_DAYS_PER_PAGE = 25;' in app
    assert 'function packingHistoryWeekGroups' in app
    assert 'deliveryBusinessWeekLabel(weekKey)' in app
    assert 'details class="packing-history-week-v272"' in app
    assert 'data-packing-history-preview=' in app
    assert 'data-packing-history-print=' in app
    assert 'Print Snapshot' in app
    assert 'async function openPackingHistoryPreview' in app
    assert 'sandbox=""' in app
    assert 'packing-history-pagination-v272' in racks_css
    assert 'overflow: visible !important' in racks_css

    # Current CSS ownership keeps confirmation geometry in the global shell
    # stylesheet; shared-ui.css remains reserved for reusable control styling.
    assert '.action-confirm-dialog' in styles_css
    assert '.action-confirm-close' in styles_css
    assert 'position: absolute' in styles_css[styles_css.index('.action-confirm-close'):styles_css.index('.action-confirm-close') + 260]
    assert 'right: 12px' in styles_css[styles_css.index('.action-confirm-close'):styles_css.index('.action-confirm-close') + 260]



def test_v0273_packing_history_preview_actions_aframe_cart_and_bay_edit_shortcut():
    """v0.273 keeps history compact/readable and restores a tiny direct Bay group editor shortcut."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/racks.css?v=20260817-v0.324' in html
    assert 'static/css/bays.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.273 - Packing Snapshot Layout and Bay Edit Shortcut' in changelog

    assert 'packing-history-page-summary-copy-v273' in app
    assert 'print days <i aria-hidden="true">&middot;</i>' in app
    assert 'min-height: 0 !important;' in racks_css
    assert 'z-index: 20000 !important;' in racks_css
    assert 'flex-wrap: nowrap !important;' in racks_css
    assert '#operationsModal[data-kind="rack-history"] .packing-history-row-actions-v272 > button' in racks_css

    preview_start = app.index('async function openPackingHistoryPreview')
    preview_end = app.index('function rackHistoryDefaultFilters', preview_start)
    preview = app[preview_start:preview_end]
    assert preview.count('data-packing-preview-close') == 3  # top-right X plus delegated/focus references
    assert '<button type="button" class="secondary" data-packing-preview-close>Close</button>' not in preview
    assert 'data-packing-preview-print=' in preview

    assert '["glasscart", "A-frame glass cart"]' in app
    assert 'M11 2h2l5.45 13H21v2h-2.2' in racks_css

    assert 'bay-section-edit-btn bay-section-edit-btn-v273' in app
    assert 'data-bay-editor-open="${escapeHtml(section.label)}"' in app
    assert '.bay-section-edit-btn-v273' in bays_css
    assert 'width: 18px !important;' in bays_css
    assert 'height: 18px !important;' in bays_css
    assert 'width: 9px !important;' in bays_css
    assert 'right: 30px !important;' in bays_css


def test_v0230_authoritative_aw_removals_and_update_preview():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    migrations = (root / "database/migrations.py").read_text(encoding="utf-8")
    store = (root / "backend/store.py").read_text(encoding="utf-8")
    import_safety = (root / "backend/import_safety.py").read_text(encoding="utf-8")
    sql_importer = (root / "automation/sql_delivery_export/import_delivery_folder.py").read_text(encoding="utf-8")
    crystal_importer = (root / "automation/crystal_delivery_export/import_delivery_folder.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '"snapshot_json"' in contract
    assert 'v230_removed_import_lines' in migrations
    assert "change_type IN ('new', 'updated', 'removed')" in migrations

    assert '"is_deleted": 1' in import_safety
    assert '"manual_only": 0' in import_safety
    assert 'Once A+W supplies the same business line, source data owns it.' in import_safety
    assert '"removedLineCount": 0' in import_safety
    assert '"removedPieceQty": 0' in import_safety
    assert 'changes.append((line_id, "removed", dict(snapshot)))' in import_safety
    assert 'snapshot_json' in import_safety
    assert "status = 'Removed'" in import_safety
    assert "status = 'Cancelled'" in import_safety
    assert 'COALESCE(li.is_deleted, 0) = 0' in store
    assert '"removedCount": len(removed_items)' in store
    assert 'LEFT JOIN line_items li ON li.id = n.line_item_id' in store

    assert 'install_safe_delivery_import(store)' in sql_importer
    assert 'install_safe_delivery_import(store)' in crystal_importer
    assert 'removedLineCount' in sql_importer
    assert 'removedPieceQty' in sql_importer

    assert 'Removed Items' in app
    assert 'function deliveryListUpdatePreviewHtml(payload = {})' in app
    assert 'quantityChangeHtmlForRow' in app
    assert 'admin-import-stage-actions-v230' in app
    assert 'list?.removedItemCount' in app
    assert 'new, updated, or removed' in app
    assert 'Keep a removal-only stage in Delivery List Management' in app

    polish_css = css[css.rindex('/* v0.275 authoritative A+W removals') :]
    assert '.delivery-update-preview-v230' in polish_css
    assert '.delivery-update-preview-group.is-removed' in polish_css
    assert '.qty-change.is-removed' in polish_css
    assert '.admin-import-stage-actions-v230' in polish_css
    assert '.admin-update-preview-icon' in polish_css

    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.275 - Authoritative A+W Removals and Update Preview' in changelog


def test_v0231_authoritative_sql_reconciliation_repair():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")
    controller = (root / "backend/automation_control.py").read_text(encoding="utf-8")
    store = (root / "backend/store.py").read_text(encoding="utf-8")
    safety = (root / "backend/import_safety.py").read_text(encoding="utf-8")
    automation_safety = (
        root / "automation/sql_delivery_export/delivery_import_safety.py"
    ).read_text(encoding="utf-8")
    importer = (
        root / "automation/sql_delivery_export/import_delivery_folder.py"
    ).read_text(encoding="utf-8")
    runner = (
        root / "automation/sql_delivery_export/Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.276 - Authoritative SQL Reconciliation Repair' in changelog

    assert 'if ($Mode -eq "Custom")' in runner
    assert '$forceImportDates = @($sourceDates)' in runner
    assert 'forcing authoritative scanner reconciliation' in runner
    assert '"runner": runtime_runner' in controller

    assert 'def scanner_stage_drift(' in importer
    assert 'source_data_drift, drift_list_ids = scanner_stage_drift(' in importer
    assert 'COALESCE(manual_only, 0) = 0' in importer
    assert 'A+W data, generated stages, and all active source-owned scanner rows match.' in importer

    assert 'stale_list_rows = [' in store
    assert 'summary["retired"] = remaining_line_count == 0' in store
    assert 'summary["retainedManualLineCount"] = remaining_line_count' in store
    assert 'Optional and custom route stages can disappear completely' in store

    for safety_source in (safety, automation_safety):
        assert 'IMPORT_PREVIEW_RETENTION_DAYS = 365' in safety_source
        assert 'def _preview_retention_cutoff_iso()' in safety_source
        assert 'before = _snapshot_delivery_date(self, delivery_date) if delivery_date else {}' in safety_source
        assert 'Historical delivery dates are retained for Delivery List Management preview.' in safety_source


def test_v0232_manual_automation_startup_and_live_log_repair():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")
    controller = (root / "backend/automation_control.py").read_text(encoding="utf-8")
    runner = (
        root / "automation/sql_delivery_export/Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.277 - Manual Automation Startup and Live Log Repair' in changelog

    assert 'AUTOMATION_RUNTIME_FILES = (' in controller
    assert 'def _sync_runtime_scripts(' in controller
    assert '"runner": runtime_runner' in controller
    assert 'synchronizedRuntimeFiles' in controller
    assert '"-NonInteractive"' in controller
    assert '"-LogPath"' in controller
    assert '[string]$LogPath = ""' in runner
    assert 'PowerShell automation runner accepted the request.' in runner
    assert 'startup failures are visible' in runner


def test_v0233_import_notice_schema_recovery_and_duplicate_source_protection():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    migrations = (root / "database/migrations.py").read_text(encoding="utf-8")
    store = (root / "backend/store.py").read_text(encoding="utf-8")
    importer = (
        root / "automation/sql_delivery_export/import_delivery_folder.py"
    ).read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.278 - Import Notice Schema Recovery' in changelog

    assert 'v233_repair_removed_import_notice_schema' in migrations
    assert 'def _migration_007_v233_repair_removed_import_notice_schema' in migrations
    assert 'CASE WHEN json_valid(snapshot_json)' in migrations
    assert "change_type IN ('new', 'updated', 'removed')" in migrations
    assert 'def select_latest_delivery_source_files(' in store
    assert 'candidate_paths, ignored_files = select_latest_delivery_source_files(all_paths)' in store
    assert '"ok": not failed_files' in store
    assert 'and not failed_rows' in importer

    import sys

    sys.path.insert(0, str(root))
    from database.migrations import _migration_007_v233_repair_removed_import_notice_schema

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            INSERT INTO users (id) VALUES (1);
            CREATE TABLE line_update_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_item_id TEXT NOT NULL,
                list_id TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                change_type TEXT NOT NULL CHECK (change_type IN ('new', 'updated')),
                change_token TEXT NOT NULL,
                source_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(line_item_id, change_type, change_token)
            );
            CREATE TABLE line_update_receipts (
                notice_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                seen_at TEXT NOT NULL,
                PRIMARY KEY (notice_id, user_id)
            );
            INSERT INTO line_update_notices (
                id, line_item_id, list_id, delivery_date, change_type,
                change_token, source_hash, created_at
            ) VALUES (5, 'line-5', 'list-5', '2026-08-03', 'updated', 'token-5', 'hash-5', '2026-08-05T15:00:00+00:00');
            INSERT INTO line_update_receipts (notice_id, user_id, seen_at)
            VALUES (5, 1, '2026-08-05T15:01:00+00:00');
            """
        )
        _migration_007_v233_repair_removed_import_notice_schema(connection)

        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(line_update_notices)").fetchall()
        }
        assert "snapshot_json" in columns
        preserved = connection.execute(
            "SELECT id, source_hash, snapshot_json FROM line_update_notices WHERE id = 5"
        ).fetchone()
        assert dict(preserved) == {"id": 5, "source_hash": "hash-5", "snapshot_json": "{}"}
        receipt = connection.execute(
            "SELECT notice_id, user_id FROM line_update_receipts WHERE notice_id = 5"
        ).fetchone()
        assert tuple(receipt) == (5, 1)
        connection.execute(
            """
            INSERT INTO line_update_notices (
                line_item_id, list_id, delivery_date, change_type,
                change_token, source_hash, snapshot_json, created_at
            ) VALUES (?, ?, ?, 'removed', ?, '', ?, ?)
            """,
            ('removed-line', 'removed-list', '2026-08-03', 'removed-token', '{"qty":2}', '2026-08-05T15:02:00+00:00'),
        )
    finally:
        connection.close()


def test_v0234_runtime_notice_schema_guard_and_single_source_import():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    migrations = (root / "database/migrations.py").read_text(encoding="utf-8")
    importer = (
        root / "automation/sql_delivery_export/import_delivery_folder.py"
    ).read_text(encoding="utf-8")
    backend_safety = (root / "backend/import_safety.py").read_text(encoding="utf-8")
    automation_safety = (
        root / "automation/sql_delivery_export/delivery_import_safety.py"
    ).read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.279 - Runtime Import Schema Guard and Single-Source Reconciliation' in changelog

    assert 'v234_authoritative_import_schema_guard' in migrations
    assert 'def _migration_008_v234_authoritative_import_schema_guard' in migrations
    assert 'def _ensure_line_update_notice_schema(store: Any) -> bool:' in backend_safety
    assert 'def _ensure_line_update_notice_schema(store: Any) -> bool:' in automation_safety
    assert 'InitializeStore=false' in automation_safety
    assert 'schemaRepairApplied' in importer
    assert 'def import_selected_workbook(' in importer
    assert '"sql_authoritative_sync"' in importer
    assert 'prefer_canonical=True' in importer
    assert 'store.import_delivery_folder(' not in importer

    import importlib.util
    import sys
    import tempfile

    module_path = root / "automation/sql_delivery_export/delivery_import_safety.py"
    specification = importlib.util.spec_from_file_location("v234_delivery_import_safety", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "scanner.db"
        connection = sqlite3.connect(database_path)
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            INSERT INTO users (id) VALUES (1);
            CREATE TABLE line_update_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_item_id TEXT NOT NULL,
                list_id TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                change_type TEXT NOT NULL CHECK (change_type IN ('new', 'updated')),
                change_token TEXT NOT NULL,
                source_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(line_item_id, change_type, change_token)
            );
            CREATE TABLE line_update_receipts (
                notice_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                seen_at TEXT NOT NULL,
                PRIMARY KEY (notice_id, user_id)
            );
            INSERT INTO line_update_notices (
                id, line_item_id, list_id, delivery_date, change_type,
                change_token, source_hash, created_at
            ) VALUES (9, 'line-9', 'list-9', '2026-08-03', 'updated', 'token-9', 'hash-9', '2026-08-05T15:00:00+00:00');
            INSERT INTO line_update_receipts (notice_id, user_id, seen_at)
            VALUES (9, 1, '2026-08-05T15:01:00+00:00');
            """
        )
        connection.commit()
        connection.close()

        class Store:
            def connect(self):
                value = sqlite3.connect(database_path)
                value.row_factory = sqlite3.Row
                value.execute("PRAGMA foreign_keys = ON")
                return value

        store = Store()
        assert module._ensure_line_update_notice_schema(store) is True
        repaired = store.connect()
        try:
            columns = {
                str(row["name"])
                for row in repaired.execute("PRAGMA table_info(line_update_notices)").fetchall()
            }
            assert "snapshot_json" in columns
            preserved = repaired.execute(
                "SELECT id, source_hash, snapshot_json FROM line_update_notices WHERE id = 9"
            ).fetchone()
            assert dict(preserved) == {"id": 9, "source_hash": "hash-9", "snapshot_json": "{}"}
            receipt = repaired.execute(
                "SELECT notice_id, user_id FROM line_update_receipts WHERE notice_id = 9"
            ).fetchone()
            assert tuple(receipt) == (9, 1)
            repaired.execute(
                """
                INSERT INTO line_update_notices (
                    line_item_id, list_id, delivery_date, change_type,
                    change_token, source_hash, snapshot_json, created_at
                ) VALUES ('removed-line', 'removed-list', '2026-08-03', 'removed',
                          'removed-token', '', '{"qty":2}', '2026-08-05T15:02:00+00:00')
                """
            )
            repaired.commit()
        finally:
            repaired.close()


def test_v0235_authoritative_manual_duplicate_retirement():
    """A+W owns a colliding order/item while unrelated manual work remains."""
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    safety_source = (root / "backend/import_safety.py").read_text(encoding="utf-8")
    automation_safety = (
        root / "automation/sql_delivery_export/delivery_import_safety.py"
    ).read_text(encoding="utf-8")
    importer_source = (
        root / "automation/sql_delivery_export/import_delivery_folder.py"
    ).read_text(encoding="utf-8")
    runner = (
        root / "automation/sql_delivery_export/Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    controller = (root / "backend/automation_control.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.280 - Authoritative Manual Duplicate Retirement' in changelog

    for source in (safety_source, automation_safety):
        assert 'manual_source_collision = bool(record.get("manual"))' in source
        assert '"duplicateManualLineCount": 0' in source
        assert '"duplicateManualPieceQty": 0' in source
        assert 'Duplicate manual line replaced by authoritative A+W source' in source

    assert 'duplicate_manual_found = False' in importer_source
    assert 'expected_order_items_by_list' in importer_source
    assert '"duplicateManualLineCount": summary.get("duplicateManualLineCount", 0)' in importer_source
    assert 'duplicate manual line(s) retired' in runner
    assert '"duplicateManualLineCount": int(item.get("duplicateManualLineCount") or 0)' in controller

    import importlib.util

    module_path = root / "backend/import_safety.py"
    specification = importlib.util.spec_from_file_location("v236_import_safety", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(
            """
            CREATE TABLE delivery_lists (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                stage TEXT NOT NULL,
                scanner TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE line_items (
                id TEXT PRIMARY KEY,
                list_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                barcode TEXT NOT NULL DEFAULT '',
                order_no TEXT NOT NULL,
                item_no TEXT NOT NULL,
                qty INTEGER NOT NULL,
                scanned_qty INTEGER NOT NULL DEFAULT 0,
                dimensions TEXT NOT NULL DEFAULT '',
                customer TEXT NOT NULL DEFAULT '',
                route TEXT NOT NULL DEFAULT '',
                source_route TEXT NOT NULL DEFAULT '',
                job TEXT NOT NULL DEFAULT '',
                product TEXT NOT NULL DEFAULT '',
                process_state TEXT NOT NULL DEFAULT '',
                queue_state TEXT NOT NULL DEFAULT '',
                suggested_bay TEXT NOT NULL DEFAULT '',
                priority_delivery_date TEXT NOT NULL DEFAULT '',
                priority_direct_to_truck INTEGER NOT NULL DEFAULT 0,
                created_at_utc TEXT NOT NULL DEFAULT '',
                updated_at_utc TEXT NOT NULL DEFAULT '',
                is_deleted INTEGER NOT NULL DEFAULT 0,
                deleted_at_utc TEXT NOT NULL DEFAULT '',
                deleted_by_user_id INTEGER,
                manual_only INTEGER NOT NULL DEFAULT 0,
                manual_source TEXT NOT NULL DEFAULT '',
                protect_from_aw_import INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL
            );
            INSERT INTO delivery_lists (
                id, label, delivery_date, stage, scanner, status, revision
            ) VALUES (
                'list-1', 'Outbound', '2026-08-03', 'Outbound', 'Airport Rd', 'active', 1
            );
            INSERT INTO line_items (
                id, list_id, source_id, barcode, order_no, item_no, qty,
                dimensions, customer, route, source_route, job, product, process_state
            ) VALUES (
                'source-1', 'list-1', 'src-1', 'B1', '100', '001', 1,
                '10 x 10', 'Customer', 'AIR', 'AIR', 'Job', 'Glass', 'Remake'
            );
            INSERT INTO line_items (
                id, list_id, source_id, barcode, order_no, item_no, qty,
                dimensions, customer, route, source_route, job, product,
                manual_only, manual_source
            ) VALUES (
                'manual-duplicate', 'list-1', 'manual-1', 'B2', '100', '001', 1,
                '10 x 10', 'Customer', 'AIR', 'manual', 'Job', 'Glass',
                1, 'manual-entry'
            );
            INSERT INTO line_items (
                id, list_id, source_id, barcode, order_no, item_no, qty,
                dimensions, customer, route, source_route, job, product,
                manual_only, manual_source, protect_from_aw_import
            ) VALUES (
                'manual-protected', 'list-1', 'manual-protected', 'B4', '100', '001', 1,
                '10 x 10', 'Customer', 'AIR', 'manual', 'Protected Job', 'Glass',
                1, 'manual-entry', 1
            );
            INSERT INTO line_items (
                id, list_id, source_id, barcode, order_no, item_no, qty,
                dimensions, customer, route, source_route, job, product,
                manual_only, manual_source
            ) VALUES (
                'manual-unique', 'list-1', 'manual-2', 'B3', '999', '001', 2,
                '20 x 20', 'Other', 'CPU', 'manual', 'Manual Job', 'Glass',
                1, 'manual-entry'
            );
            """
        )

        class Store:
            @staticmethod
            def import_order_item_key(source_id, order_no, item_no):
                return f"{source_id}|{order_no}|{str(item_no).zfill(3)}"

            @staticmethod
            def import_business_key(row):
                def value(name, default=""):
                    if isinstance(row, dict):
                        return row.get(name, default)
                    try:
                        return row[name]
                    except (KeyError, TypeError, IndexError):
                        return default

                fields = (
                    "order_no", "item_no", "qty", "dimensions",
                    "customer", "route", "job", "product",
                )
                return "|".join(str(value(name, "") or "") for name in fields)

            @staticmethod
            def get_bay_auto_assign_settings_con(_connection):
                return {}

            @staticmethod
            def clone_item_for_list(_item, list_id, _index, _settings=None):
                return {
                    "id": "source-1",
                    "list_id": list_id,
                    "source_id": "src-1",
                    "barcode": "B1",
                    "order_no": "100",
                    "item_no": "001",
                    "qty": 1,
                    "scanned_qty": 0,
                    "dimensions": "10 x 10",
                    "customer": "Customer",
                    "route": "AIR",
                    "source_route": "AIR",
                    "job": "Job",
                    "product": "Glass",
                    "process_state": "",
                    "queue_state": "",
                    "suggested_bay": "",
                    "priority_delivery_date": "",
                    "priority_direct_to_truck": 0,
                }

            @staticmethod
            def available_line_item_id(_connection, desired_id, _list_id, _source_id, _index):
                return desired_id

        def metadata_upsert(
            _connection,
            _list_id,
            _label,
            _delivery_date,
            _stage,
            _scanner,
            _items,
            _replace_items,
        ):
            return {"created": False}

        summary = module._safe_reconcile_delivery_list(
            Store(),
            metadata_upsert,
            connection,
            "list-1",
            "Outbound",
            "2026-08-03",
            "Outbound",
            "Airport Rd",
            [{}],
        )
        active_rows = connection.execute(
            """
            SELECT id, order_no, item_no, process_state, manual_only, manual_source, protect_from_aw_import
            FROM line_items
            WHERE COALESCE(is_deleted, 0) = 0
            ORDER BY id
            """
        ).fetchall()

        assert summary["removedLineCount"] == 1
        assert summary["removedPieceQty"] == 1
        assert summary["duplicateManualLineCount"] == 1
        assert summary["duplicateManualPieceQty"] == 1
        assert summary["removedLineIds"] == ["manual-duplicate"]
        assert [item["changeType"] for item in summary["changeItems"]] == ["updated", "removed"]
        assert summary["changeItems"][0]["lineItemId"] == "source-1"
        assert summary["changeItems"][1]["lineItemId"] == "manual-duplicate"
        new_snapshot = module._change_item_payload(
            {"id": "new-1", "order_no": "200", "item_no": "001", "qty": 2},
            "new",
        )
        assert new_snapshot["changeType"] == "new"
        assert new_snapshot["lineItemId"] == "new-1"
        assert new_snapshot["qty"] == 2
        assert [row["id"] for row in active_rows] == ["manual-protected", "manual-unique", "source-1"]
        source_row = next(row for row in active_rows if row["id"] == "source-1")
        manual_row = next(row for row in active_rows if row["id"] == "manual-unique")
        protected_row = next(row for row in active_rows if row["id"] == "manual-protected")
        assert int(source_row["manual_only"] or 0) == 0
        assert str(source_row["manual_source"] or "") == ""
        assert "Remake" not in str(source_row["process_state"] or "")
        assert "Updated Line" in str(source_row["process_state"] or "")
        assert int(manual_row["manual_only"] or 0) == 1
        assert str(manual_row["manual_source"] or "") == "manual-entry"
        assert int(protected_row["protect_from_aw_import"] or 0) == 1

        connection.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action) VALUES ('line_item', 'source-1', 'mark_remake_sdi')"
        )
        assert module._active_manual_priority_labels(connection, "source-1") == {"Remake"}
        connection.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action) VALUES ('line_item', 'source-1', 'clear_rush_remake_sdi')"
        )
        assert module._active_manual_priority_labels(connection, "source-1") == set()
    finally:
        connection.close()


def test_v236_protected_manual_orders_and_remake_diagnostics():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    safety = (ROOT / "backend" / "import_safety.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'v236_protected_manual_orders' in migrations
    assert 'protect_from_aw_import' in operations
    assert 'protected_manual' in safety
    assert '_active_manual_priority_labels' in safety
    assert 'for priority_label in ("Rush", "Remake")' not in safety
    assert 'protect_from_aw_import' in importer
    assert 'SQL remake detail' in runner
    assert 'Protect from A+W import' in app


def test_v237_historical_status_filter_is_documented_but_no_longer_active():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    runner = (
        ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.282 - A+W Report Eligibility and Removed Scheduling Rows' in changelog

    # v0.282's 460/status-and-batch rule remains in the historical changelog only.
    # The maintained exporter must not use production progress as membership.
    assert 'function Get-DeliveryEligibilitySettings' not in runner
    assert 'function Get-DeliveryRowEligibility' not in runner
    assert 'AllowedOrderStatuses' not in runner
    assert 'AllowedItemStatuses' not in runner
    assert 'RequireProductionBatch' not in runner
    assert 'MaxExcludedPercent' not in runner
    assert 'v0.237-status-and-schedule-membership-1' not in runner
    assert 'v0.245-raw-date-plus-approved-exclusions-1' in runner
    assert 'Status and production progress are diagnostic only' in runner
    assert 'sourceSelectionRule = [string]$script:LastEligibilityRule' in runner


def test_v238_sqlite_migration_registry_repairs_a_schema8_database():
    from database import migrations as migration_module

    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations_text = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'def validate_migration_registry()' in migrations_text
    assert 'v236_protected_manual_orders' in migrations_text
    assert 'Database did not reach the expected schema version.' in migrations_text
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.283 - SQLite Migration Registry Startup Repair' in changelog

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        migration_module.ensure_migration_table(connection)
        connection.execute(
            "CREATE TABLE line_items (id TEXT PRIMARY KEY, manual_only INTEGER NOT NULL DEFAULT 0)"
        )
        connection.execute(
            "CREATE TABLE manual_delivery_entries (id INTEGER PRIMARY KEY, manual_only INTEGER NOT NULL DEFAULT 0)"
        )
        for version in range(1, 9):
            migration = migration_module.migration_by_version(version)
            connection.execute(
                """
                INSERT INTO schema_migrations
                    (version, name, checksum, applied_at_utc, execution_ms, app_version)
                VALUES (?, ?, ?, '2026-08-05T00:00:00+00:00', 0, '237')
                """,
                (migration.version, migration.name, migration.checksum),
            )
        connection.commit()

        applied = migration_module.run_sqlite_migrations(connection, object())

        assert applied == [9, 10]
        assert max(migration_module.installed_migrations(connection)) == 10
        line_columns = {row["name"] for row in connection.execute("PRAGMA table_info(line_items)")}
        manual_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(manual_delivery_entries)")
        }
        assert "protect_from_aw_import" in line_columns
        assert "protect_from_aw_import" in manual_columns
        row = connection.execute(
            "SELECT app_version FROM schema_migrations WHERE version = 10"
        ).fetchone()
        assert row is not None
        assert row["app_version"] == "247"
    finally:
        connection.close()


def test_v239_manual_and_scheduled_automation_runs_are_isolated():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    runner = (
        ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.284 - Manual and Scheduled Automation Run Isolation' in changelog

    assert '"gui_summary": working_root / "State" / "web-gui-summary.json"' in controller
    assert '"run_lock": working_root / "State" / "run.lock"' in controller
    assert 'def _runtime_lock_busy' in controller
    assert 'def _refresh_runtime_scripts_if_safe' in controller
    assert '"-SummaryPath"' in controller
    assert '"-RequestId"' in controller
    assert '"-FailIfBusy"' in controller
    assert '_read_json_file(Path(summary_path_text))' in controller
    assert 'summary_request_id != request_id' in controller
    assert 'self._refresh_runtime_scripts_if_safe(startup_config)' in controller
    assert 'self._runtime_paths(config)["last_run"]' not in controller.split('def _finish_run', 1)[1].split('def _run_schedule_script', 1)[0]

    assert '[string]$SummaryPath = ""' in runner
    assert '[string]$RequestId = ""' in runner
    assert '[switch]$FailIfBusy' in runner
    assert '$script:SkipSummary = $false' in runner
    assert 'The manual request was not started.' in runner
    assert 'without replacing the active run summary' in runner
    assert 'requestId = [string]$RequestId' in runner
    assert 'runOrigin = $(if' in runner
    assert '-and -not $script:SkipSummary' in runner

    assert 'Scheduled task' in app
    assert 'Manual request' in app
    assert 'One date: ${last.dateFrom}' in app


def test_v240_powershell_excluded_row_log_is_parser_safe():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    runner = (
        ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.285 - PowerShell Eligibility Log Parser Repair' in changelog

    assert 'Verified A+W exclusions for {0}: {1}' in runner
    assert '-f $dateKey, $excludedDetail' in runner
    assert 'Verified A+W exclusions for $dateKey: $excludedDetail' not in runner

    # PowerShell parses `$name:` as a scoped-variable expression. Reject that
    # unsafe form anywhere in a double-quoted runner string.
    import re
    scoped_names = {"script", "global", "local", "private", "env", "using"}
    variable_colons = re.findall(r'\$(?!\()([A-Za-z_][A-Za-z0-9_]*):', runner)
    unsafe = [name for name in variable_colons if name.lower() not in scoped_names]
    assert unsafe == []


def test_v241_active_scan_refresh_complete_change_preview_and_eye_icons():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    safety = (ROOT / "backend" / "import_safety.py").read_text(encoding="utf-8")
    automation_safety = (
        ROOT / "automation" / "sql_delivery_export" / "delivery_import_safety.py"
    ).read_text(encoding="utf-8")
    runner = (
        ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.286 - Active Scan Refresh and Complete Change Preview' in changelog

    assert 'list.revision,' in app
    assert 'function dlsAutomationActiveDetailIsStale(list = {})' in app
    assert 'function dlsAutomationRefreshActiveListDetail(listId)' in app
    assert 'window.setTimeout(() => dlsAutomationRefreshActiveListDetail(activeListId), 0);' in app
    assert 'catalogRevision !== loadedRevision' in app
    assert 'catalogItemCount !== loadedItemCount' in app
    assert 'catalogTotalQty !== loadedTotalQty' in app

    assert 'function adminUpdatePreviewIconHtml()' in app
    assert '<svg class="admin-update-preview-icon"' in app
    assert '>${adminUpdatePreviewIconHtml()}</button>' in app
    assert 'admin-update-preview-icon" aria-hidden="true"></span><b>' not in app
    assert '.admin-update-preview-icon {' in css
    assert 'stroke: currentColor;' in css
    assert '.admin-update-preview-button {' in css
    assert 'width: 36px;' in css

    for safety_source in (safety, automation_safety):
        assert 'def _change_item_payload(' in safety_source
        assert '"changeItems": []' in safety_source
        assert '_change_item_payload(cloned, "new")' in safety_source
        assert '_change_item_payload(changed_row, "updated"' in safety_source
        assert '_change_item_payload(row, "removed"' in safety_source

    assert 'preview_source = "notices" if items else "none"' in store
    assert 'stage_summary.get("changeItems") or []' in store
    assert '("new", "newLineIds")' in store
    assert '("updated", "updatedLineIds")' in store
    assert '("removed", "removedLineIds")' in store
    assert 'SELECT * FROM line_items WHERE id IN' in store
    assert '"expectedChangedCount": expected_changed_count' in store
    assert '"previewSource": preview_source' in store
    assert 'notices_and_import_history' in store
    assert 'expectedChangedCount: payloads.reduce' in app
    assert 'This legacy import recorded ${escapeHtml(expectedChangedCount)} changed lines' in app
    assert 'A no-change rerun cannot reconstruct missing historical rows' in app

    assert 'A+W source selection for {0}: {1} raw line item(s)' in runner
    assert ') -f\n        $dateKey,' in runner


def test_v242_live_totals_manual_breakdown_retained_preview_and_scan_coherence():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    importer = (
        ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py"
    ).read_text(encoding="utf-8")
    runner = (
        ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert changelog.startswith('# Delivery List Scanner Changelog\n\n## v0.299 - Stable Manual Delivery List Expansion')

    assert 'AS manual_piece_qty' in store
    assert 'AS protected_manual_piece_qty' in store
    assert 'AS source_total_qty' in store
    assert '"sourceTotalQty": int(row["source_total_qty"] or 0)' in store
    assert '"manualPieceQty": int(row["manual_piece_qty"] or 0)' in store
    assert '"sourceRemakePieceQty"' in store
    assert '"manualRemakePieceQty"' in store

    assert 'def active_list_summary_map(store: Any)' in importer
    assert 'def active_stage_summaries(' in importer
    assert 'def merge_live_stage_totals(' in importer
    assert '"stageSummaries": live_stage_summaries' in importer
    assert '"listIds": list_ids' in importer
    assert 'Scanner staging total for {0}: {1} A+W piece(s) + {2} manual piece(s)' in runner
    controller = (ROOT / 'backend' / 'automation_control.py').read_text(encoding='utf-8')
    assert '"listIds": list_ids' in controller
    assert '"changedListIds": changed_list_ids' in controller

    assert 'const liveTotal = list?.totalQty;' in app
    assert '<td><strong>${escapeHtml(updatedQty)} pcs</strong></td>' in app
    assert '<strong>${escapeHtml(stagingUpdatedQty)} pcs</strong>' in app
    assert 'const retainedPreviewCountForRow = (row, list) =>' in app
    assert 'const managementRows = managementRowsForGroup' in app
    assert 'data-admin-list-update-preview="${escapeHtml(routeRow.previewListIds.join' in app
    assert 'Preview ${escapeHtml(routeRow.label)} changes' in app
    assert 'dlsAutomationActiveDetailIsStale(activeSummary)' in app
    assert 'touchesActiveDate' in app
    assert 'window.addEventListener("focus", refreshVisibleActiveList);' in app
    assert 'manualRemakeAll' in app
    assert 'A+W + ${manualRemakeAll} manual' in app
    assert '.admin-import-qty-breakdown {' in css


def test_v242_no_change_results_keep_live_stage_totals_and_preview_ids():
    import importlib.util

    module_path = ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py"
    spec = importlib.util.spec_from_file_location("v242_import_delivery_folder", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakeStore:
        def get_delivery_lists(self):
            return [
                {
                    "id": "2026-08-03-staging-airport",
                    "label": "8/3 Airport Staging",
                    "deliveryDate": "2026-08-03",
                    "stage": "Staging",
                    "scanner": "Airport Rd",
                    "totalQty": 129,
                    "itemCount": 112,
                    "sourceTotalQty": 121,
                    "manualPieceQty": 8,
                    "manualLineCount": 8,
                    "protectedManualPieceQty": 8,
                    "protectedManualLineCount": 8,
                    "newItemCount": 0,
                    "updatedItemCount": 0,
                    "removedItemCount": 8,
                    "removedPieceQty": 8,
                    "latestUpdateAt": "2026-08-05T18:45:02+00:00",
                }
            ]

    definitions = [
        (
            "2026-08-03-staging-airport",
            "8/3 Airport Staging",
            "Staging",
            "Airport Rd",
        )
    ]
    summaries = module.active_stage_summaries(FakeStore(), definitions)
    assert summaries == [
        {
            "listId": "2026-08-03-staging-airport",
            "label": "8/3 Airport Staging",
            "stage": "Staging",
            "stageProfile": "Airport Rd",
            "scanner": "Airport Rd",
            "totalQty": 129,
            "itemCount": 112,
            "sourceTotalQty": 121,
            "manualPieceQty": 8,
            "manualLineCount": 8,
            "protectedManualPieceQty": 8,
            "protectedManualLineCount": 8,
            "latestPreviewCount": 8,
            "latestPreviewNewCount": 0,
            "latestPreviewUpdatedCount": 0,
            "latestPreviewRemovedCount": 8,
            "latestPreviewRemovedPieceQty": 8,
            "latestPreviewAt": "2026-08-05T18:45:02+00:00",
            "changedLineCount": 0,
            "changedPieceQty": 0,
            "addedPieceQty": 0,
            "removedLineCount": 0,
            "removedPieceQty": 0,
            "created": False,
            "reactivated": False,
        }
    ]

    normalized = module.file_result(
        {
            "fileName": "Delivery List 08-03-2026.xlsx",
            "deliveryDate": "2026-08-03",
            "listIds": ["2026-08-03-staging-airport"],
            "stageSummaries": summaries,
            "totalQty": 121,
        },
        "skipped",
    )
    assert normalized["classification"] == "no_changes"
    assert normalized["listIds"] == ["2026-08-03-staging-airport"]
    assert normalized["changedListIds"] == []
    assert normalized["stageSummaries"][0]["sourceTotalQty"] == 121
    assert normalized["stageSummaries"][0]["totalQty"] == 129
    assert normalized["stageSummaries"][0]["latestPreviewRemovedCount"] == 8


def test_v245_local_superseded_order_review_uses_exact_admin_approval():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    azure_schema = (ROOT / "database" / "azure_schema.sql").read_text(encoding="utf-8")
    runner = (
        ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1"
    ).read_text(encoding="utf-8")
    importer = (
        ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py"
    ).read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    exclusions = json.loads(
        (ROOT / "automation" / "sql_delivery_export" / "verified-source-exclusions.json").read_text(
            encoding="utf-8"
        )
    )

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'v245_superseded_order_review' in migrations
    assert '_migration_010_v245_superseded_order_review' in migrations
    assert 'CREATE TABLE IF NOT EXISTS superseded_order_reviews' in migrations
    assert "CREATE TABLE dbo.superseded_order_reviews" in azure_schema

    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'data-admin-modal="supersededOrders"' in html
    assert 'id="supersededOrderReviewCount"' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.290 - Local Superseded Order Review and Exact-Key Approval' in changelog

    assert 'AllowedOrderStatuses' not in runner
    assert 'AllowedItemStatuses' not in runner
    assert 'RequireProductionBatch' not in runner
    assert 'function Get-SupersededOrderCandidates' in runner
    assert 'HeaderIdentity' in runner
    assert 'v0.245-local-header-identity-review-1' in runner
    assert 'v0.245-raw-date-plus-approved-exclusions-1' in runner
    assert 'No rows were removed without an approval.' in runner
    assert 'Status and production progress are diagnostic only' in runner
    assert r'data\superseded-source-exclusions.json' in runner
    assert 'preserveEntries' in runner
    assert 'supersededOrderCandidates = @($script:SupersededOrderCandidates | ForEach-Object { $_ })' in runner

    assert 'sync_superseded_order_candidates' in importer
    assert 'supersededOrderCandidates' in importer
    assert 'verifiedExcludedOrderItems' in importer
    assert 'supersededOrderReview' in importer

    for method in (
        'sync_superseded_order_candidates',
        'list_superseded_order_reviews',
        'decide_superseded_order_review',
        'approved_superseded_order_exclusions',
        'preserved_superseded_order_items',
        'write_superseded_order_exclusion_file',
    ):
        assert f'def {method}' in store
    assert 'AND COALESCE(li.manual_only, 0) = 0' in store
    assert "AND COALESCE(li.protect_from_aw_import, 0) = 0" in store
    assert '"preserveEntries": self.preserved_superseded_order_items()' in store

    assert '"/api/admin/superseded-order-reviews"' in server
    assert '"/api/admin/superseded-order-reviews/decision"' in server
    assert 'STORE.decide_superseded_order_review' in server
    assert 'function supersededOrderReviewModalHtml' in app
    assert 'function decideSupersededOrderReview' in app
    assert 'Approve old order removal' in app
    assert 'Keep both' in app
    assert 'Review later' in app
    assert '.superseded-review-card' in admin_css
    assert '.superseded-review-compare' in admin_css

    assert len(exclusions['entries']) == 8
    assert {
        (entry['deliveryDate'], str(entry['orderNumber']), str(entry['itemNumber']).zfill(3))
        for entry in exclusions['entries']
    } == {
        ('2026-08-03', order, item)
        for order in ('236879', '236880', '236881', '236882')
        for item in ('001', '002')
    }


def test_v245_superseded_order_review_migration_is_idempotent():
    from database.migrations import _migration_010_v245_superseded_order_review

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    _migration_010_v245_superseded_order_review(connection)
    _migration_010_v245_superseded_order_review(connection)
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(superseded_order_reviews)").fetchall()
    }
    assert {
        "candidate_key",
        "header_identity",
        "original_items_json",
        "replacement_items_json",
        "source_fingerprint",
        "decision_reason",
    }.issubset(columns)
    indexes = {
        row["name"]
        for row in connection.execute("PRAGMA index_list(superseded_order_reviews)").fetchall()
    }
    assert "idx_superseded_order_reviews_status_date" in indexes
    assert "idx_superseded_order_reviews_orders" in indexes
    connection.close()


def test_v244_non_destructive_drift_accepts_extra_unverified_source_rows(tmp_path):
    import importlib.util

    module_path = ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py"
    spec = importlib.util.spec_from_file_location("v244_import_delivery_folder", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    database_path = tmp_path / "drift.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE delivery_lists (
            id TEXT PRIMARY KEY,
            delivery_date TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE line_items (
            list_id TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL,
            dimensions TEXT NOT NULL,
            customer TEXT NOT NULL,
            route TEXT NOT NULL,
            source_route TEXT NOT NULL,
            job TEXT NOT NULL,
            product TEXT NOT NULL,
            queue_state TEXT NOT NULL,
            manual_only INTEGER NOT NULL DEFAULT 0,
            manual_source TEXT NOT NULL DEFAULT '',
            protect_from_aw_import INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO delivery_lists VALUES ('list-1', '2026-08-03', 'active');
        INSERT INTO line_items VALUES
            ('list-1', '236883', '001', 1, '10 x 20', 'Customer', '', '', 'Job A', 'Glass', '', 0, '', 0, 0),
            ('list-1', '236879', '001', 1, '10 x 20', 'Customer', '', '', 'Job A', 'Glass', '', 0, '', 0, 0);
        """
    )
    connection.commit()
    connection.close()

    class FakeStore:
        def connect(self):
            con = sqlite3.connect(database_path)
            con.row_factory = sqlite3.Row
            return con

        def clone_item_for_list(self, item, list_id, index):
            return dict(item)

    expected_item = {
        "order_no": "236883",
        "item_no": "001",
        "qty": 1,
        "dimensions": "10 x 20",
        "customer": "Customer",
        "route": "",
        "source_route": "",
        "job": "Job A",
        "product": "Glass",
        "queue_state": "",
    }
    definitions = [("list-1", "List", "Staging", "Airport", [expected_item])]

    drift, ids = module.scanner_stage_drift(
        FakeStore(),
        "2026-08-03",
        definitions,
        allow_source_removals=False,
    )
    assert not drift
    assert ids == []

    drift, ids = module.scanner_stage_drift(
        FakeStore(),
        "2026-08-03",
        definitions,
        allow_source_removals=True,
    )
    assert drift
    assert ids == ["list-1"]

    drift, ids = module.scanner_stage_drift(
        FakeStore(),
        "2026-08-03",
        definitions,
        allow_source_removals=False,
        verified_excluded_order_items={("236879", "001")},
    )
    assert drift
    assert ids == ["list-1"]


def test_v246_automatic_import_result_and_notification_recovery():
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert '$safetyDeferredDetailSnapshot = @($script:SafetyDeferredDetails | ForEach-Object { $_ })' in runner
    assert 'safetyDeferredDetails = $safetyDeferredDetailSnapshot' in runner
    assert 'supersededOrderCandidates = @($script:SupersededOrderCandidates | ForEach-Object { $_ })' in runner
    assert 'ConvertTo-Json -Depth 8' in runner
    assert '$pythonImportFailure = $null' in runner
    assert 'Scanner import verification completed without producing its result summary.' in runner
    assert 'The original automation error was preserved' in runner
    assert r'State\last-error.txt' in runner
    assert 'except Exception as exc:' in importer
    assert 'summary["supersededOrderReviewWarning"] = warning' in importer
    assert 'traceback.format_exc()' in importer
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme


def test_v247_review_queue_installation_and_simple_active_totals():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'sync_superseded_order_candidates' in store
    assert 'import backend.store as backend_store_module' in importer
    assert 'The installed backend/store.py does not provide' in importer
    assert 'Detected {0} superseded-order review candidate payload(s), but the review queue was not synchronized.' in runner
    assert 'Source/manual ownership counters were not returned by this unchanged-stage verification.' in runner
    assert '<td><strong>${escapeHtml(updatedQty)} pcs</strong></td>' in app
    assert '<strong>${escapeHtml(stagingUpdatedQty)} pcs</strong>' in app
    assert 'active total</small>' not in app
    assert '} A+W pcs</strong>${quantityBreakdownHtmlForRow' not in app
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme


def test_v248_daily_import_history_keeps_older_same_day_runs_without_latest_duplicate():
    import importlib.util

    module_path = ROOT / "backend" / "automation_control.py"
    specification = importlib.util.spec_from_file_location("v248_automation_control", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    controller_type = module.DeliveryAutomationController
    controller = controller_type.__new__(controller_type)
    controller.scanner_store = None
    older = {
        "id": 41,
        "runId": "run-early",
        "deliveryDate": "2026-08-06",
        "sourceName": "Delivery List 08-06-2026.xlsx",
        "classification": "updated",
        "rowCount": 85,
        "totalQty": 108,
        "createdCount": 0,
        "updatedCount": 2,
        "addedPieceQty": 0,
        "changedPieceQty": 2,
        "removedLineCount": 0,
        "removedPieceQty": 0,
        "importedAt": "2026-08-06T08:15:00",
    }
    newest = {
        "id": 42,
        "runId": "run-late",
        "deliveryDate": "2026-08-06",
        "sourceName": "Delivery List 08-06-2026.xlsx",
        "classification": "no_changes",
        "rowCount": 85,
        "totalQty": 108,
        "createdCount": 0,
        "updatedCount": 0,
        "addedPieceQty": 0,
        "changedPieceQty": 0,
        "removedLineCount": 0,
        "removedPieceQty": 0,
        "importedAt": "2026-08-06T09:35:18",
    }
    runtime_latest = {
        **newest,
        "id": -1,
        "runCompletedAt": "2026-08-06T09:35:20+00:00",
        "importedAt": "2026-08-06T09:35:20+00:00",
    }
    controller._database_import_history_items = lambda: [newest, older]
    controller._latest_automation_import_items = lambda: (
        [runtime_latest],
        {"completedAt": "2026-08-06T09:35:20+00:00"},
    )

    payload = controller.get_import_history(
        page=1,
        page_size=2000,
        date_from="2026-08-06",
        date_to="2026-08-06",
    )

    assert payload["totalCount"] == 2
    assert [item["id"] for item in payload["imports"]] == [42, 41]
    assert all(item["id"] != -1 for item in payload["imports"])


def test_v248_updated_change_snapshots_preserve_before_after_fields():
    import importlib.util

    module_path = ROOT / "backend" / "import_safety.py"
    specification = importlib.util.spec_from_file_location("v248_import_safety", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    before = {
        "id": "line-1",
        "order_no": "237100",
        "item_no": "001",
        "qty": 1,
        "dimensions": "30 x 40",
        "customer": "Customer A",
        "job": "Job 100",
        "product": "3/8 Clear",
        "route": "A",
        "queue_state": "Normal",
        "source_id": "old-source",
        "barcode": "OLD",
    }
    after = {
        **before,
        "qty": 2,
        "dimensions": "31 x 40",
        "route": "B",
        "queue_state": "Remake",
        "source_id": "new-source",
        "barcode": "NEW",
    }

    payload = module._change_item_payload(after, "updated", "line-1", previous_row=before)

    assert payload["previous"]["qty"] == 1
    assert payload["previous"]["dimensions"] == "30 x 40"
    assert payload["previous"]["route"] == "A"
    assert payload["previous"]["queueState"] == "Normal"
    assert payload["changedFields"] == [
        "qty",
        "dimensions",
        "route",
        "queueState",
        "sourceId",
        "barcode",
    ]


def test_v248_recent_import_polish_and_change_preview_contract():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    backend_safety = (ROOT / "backend" / "import_safety.py").read_text(encoding="utf-8")
    runtime_safety = (ROOT / "automation" / "sql_delivery_export" / "delivery_import_safety.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert '"--run-id"' in runner
    assert '"--run-started-at"' in runner
    assert 'requestId = [string]$RequestId' in runner
    assert 'parser.add_argument("--run-id"' in importer
    assert '"runId": str(run_id or "")' in importer
    assert 'row.setdefault("runId", str(args.run_id or ""))' in importer
    assert 'row.setdefault("runStartedAt", str(args.run_started_at or ""))' in importer
    assert 'clean_page_size = max(10, min(int(page_size or 20), 2000))' in controller
    assert 'const historyPageCount = Math.max(Number(firstHistoryPage.totalPages || 1), 1);' in app
    assert 'pageSize=2000' in app
    assert 'additionalHistoryPages.flatMap' in app
    assert 'return collapsed.sort((a, b)' in app
    assert 'const key = explicitRunId ? `run:${explicitRunId}`' in app
    assert 'Durable database rows carry the detailed audit facts.' in app
    assert '.slice(0, 100)' not in app[app.index('function adminImportRunGroups'):app.index('async function refreshAdminTodayImportRuns')]
    assert 'Do not collapse rows by delivery date here' in app
    assert 'String(entry.sourceName || entry.fileName || "")' in app
    assert 'delivery-update-preview-v248' in app
    assert 'data-preview-filter-button' not in app[app.index('function deliveryListUpdatePreviewHtml'):app.index('function importPreviewPayloadsFromContext')]
    assert 'data-preview-search-input' not in app[app.index('function deliveryListUpdatePreviewHtml'):app.index('function importPreviewPayloadsFromContext')]
    assert 'delivery-update-preview-diffs' in app
    assert 'Removed lines are no longer active or scannable.' not in app
    assert '.admin-import-run-browser-v248' in css
    assert '.delivery-update-preview-toolbar-v248' in css
    assert '.delivery-update-preview-order-details' in css
    assert '.delivery-update-preview-diff' in css
    assert backend_safety.splitlines()[1:] == runtime_safety.splitlines()[1:]
    assert 'previous_row: Any | None = None' in backend_safety
    assert 'comparison_fields = (' in backend_safety
    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'static/css/styles.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert changelog.startswith(
        '# Delivery List Scanner Changelog\n\n'
        '## v0.299 - Stable Manual Delivery List Expansion'
    )


def test_v249_import_history_preview_and_change_totals_contract() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'admin-import-run-browser-v249' in app
    assert 'admin-import-run-selected-copy' in app
    assert 'Updated ${escapeHtml(change.updated)} pcs' in app
    assert 'Removed ${escapeHtml(change.removed)} pcs' in app
    assert '<th>Changes</th>' in app
    assert 'const previewListIds = [...new Set(routeRows.flatMap' in app
    assert 'const hasRetainedPreview = routeRow.previewListIds.length > 0' in app
    assert 'Promise.allSettled' in app
    assert 'data-history-timestamp=' in app
    assert 'data-history-run-id=' in app
    assert 'dataset.v249Grouped' in app
    assert 'automationHistoryRunLabel' in app
    assert 'year: "numeric"' in app[app.index('function formatTimestamp(value)'):app.index('function formatDeliveryDate(value)')]
    assert 'import-history-workspace-v249' in app

    assert '.admin-import-run-browser-v249 .admin-import-run-selected-header' in css
    assert '.admin-import-run-selected-header > .admin-import-run-selected-metrics' in css
    assert '.automation-history-day-v249' in css
    assert '.automation-history-run-v249' in css
    assert '.delivery-update-preview-warning-v249' in css

    preview_method = store[store.index('def get_delivery_list_update_preview'):store.index('def admin_search_line_items', store.index('def get_delivery_list_update_preview'))]
    assert '_row_value(legacy_row' not in preview_method
    assert 'row_value(legacy_row' in preview_method
    assert 'json_extract(n.snapshot_json' not in preview_method
    assert '"newPieceQty": sum(' in store
    assert '"updatedPieceQty": sum(' in store
    assert '"newPieceQty": int(change.get("newPieceQty") or 0)' in controller
    assert '"updatedPieceQty": int(change.get("updatedPieceQty") or 0)' in controller
    assert '"newPieceQty": int_value(row.get("newPieceQty"))' in importer
    assert '"updatedPieceQty": int_value(row.get("updatedPieceQty"))' in importer
    assert 'Unable to load the delivery-list update preview' in server

    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'Current maintained release: **v0.324**' in readme
    assert changelog.startswith(
        '# Delivery List Scanner Changelog\n\n'
        '## v0.299 - Stable Manual Delivery List Expansion'
    )


def test_v250_selective_sql_sync_passes_run_identity_without_global_args(tmp_path):
    import importlib.util

    module_path = ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py"
    specification = importlib.util.spec_from_file_location("v250_import_delivery_folder", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    workbook = tmp_path / "Delivery List 08-12-2026.xlsx"
    workbook.write_bytes(b"test")
    captured = {}

    module.delivery_workbooks_by_date = lambda *_args, **_kwargs: {"2026-08-12": workbook}
    module.current_list_ids = lambda _store: set()
    module.routed_payload_for_stage_expectations = lambda _store, payload: payload
    module.scanner_stage_drift = lambda *_args, **_kwargs: (True, ["stage-1"])
    module.import_selected_workbook = lambda *_args, **kwargs: captured.update(kwargs) or {
        "classification": "updated",
        "deliveryDate": "2026-08-12",
        "fileName": workbook.name,
    }
    module.summary_from_files = lambda files, *_args, **_kwargs: {"files": files, "ok": True}

    result = module.selective_sql_sync(
        store=object(),
        folder=tmp_path,
        target_dates=["2026-08-12"],
        force_import_dates={"2026-08-12"},
        user="sql-auto-import",
        date_reader=lambda _path: "2026-08-12",
        payload_loader=lambda _path: {"deliveryDate": "2026-08-12", "items": []},
        list_builder=lambda _payload: [],
        source_hash_reader=lambda _path: "hash",
        run_id="run-v250",
        run_started_at="2026-08-06T11:30:00-04:00",
    )

    assert result["ok"] is True
    assert captured["run_id"] == "run-v250"
    assert captured["run_started_at"] == "2026-08-06T11:30:00-04:00"


def test_v250_version_and_scope_repair_contract():
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    sync_method = importer[importer.index("def selective_sql_sync"):importer.index("def main()")]
    assert 'run_id: str = ""' in sync_method
    assert 'run_started_at: str = ""' in sync_method
    assert "run_id=args.run_id" not in sync_method
    assert "run_started_at=args.run_started_at" not in sync_method
    assert "run_id=run_id" in sync_method
    assert "run_started_at=run_started_at" in sync_method
    assert "run_id=args.run_id" in importer[importer.index("def main()"):]
    assert "run_started_at=args.run_started_at" in importer[importer.index("def main()"):]
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert changelog.startswith(
        "# Delivery List Scanner Changelog\n\n"
        "## v0.299 - Stable Manual Delivery List Expansion"
    )


def test_v251_cross_stage_preview_and_durable_daily_history_contract():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert "def user_can_preview_delivery_update" in server
    assert 'roles.intersection({"admin", "supervisor"})' in server
    assert "administrative_review_permissions.issubset(granted)" in server
    preview_route = server[
        server.index('if parsed.path == "/api/admin/delivery-list-update-preview"'):
        server.index('if parsed.path == "/api/admin/line-items/search"')
    ]
    assert "self.user_can_preview_delivery_update(user, list_id)" in preview_route
    assert "STORE.user_can_access_list(user, list_id)" not in preview_route

    snapshot_method = app[
        app.index("function dlsAutomationApplyImportSnapshot"):
        app.index('document.addEventListener("dls:delivery-list-data-refreshed"')
    ]
    assert "state.adminRecentImports = latestResults.slice();" not in snapshot_method
    assert "dlsAutomationMergeRecentImports(" in snapshot_method
    assert "state.adminTodayImportLoaded = false;" in snapshot_method
    assert "refreshAdminTodayImportRuns({ render: true })" in snapshot_method

    daily_refresh = app[
        app.index("async function refreshAdminTodayImportRuns"):
        app.index("function renderAdminImportRunBrowser")
    ]
    assert "state.adminTodayImportEntries = dlsAutomationMergeRecentImports(" in daily_refresh
    assert "Preserve every already-loaded run" in daily_refresh

    preview_method = app[
        app.index("function deliveryListUpdatePreviewHtml"):
        app.index("function initializeDeliveryListUpdatePreviewControls")
    ]
    for key in ("airport", "indian-trail", "greenville", "cpu", "dtc"):
        assert f'key: "{key}"' in preview_method
    assert "delivery-update-preview-location-group" in preview_method
    assert "data-preview-stage-section" not in preview_method
    assert 'data-preview-location="${location.key}">' in preview_method
    assert 'data-preview-location="${location.key}" open' not in preview_method
    assert "if (activelyFiltering && !group.hidden) group.open = true;" in app

    assert ".delivery-update-preview-location-group" in css
    assert ".delivery-update-preview-location-body > .delivery-update-preview-list" in css
    assert ".delivery-update-preview-location-badges" in css

    assert "meaningful_latest_run_id" in controller
    assert "A different stable run ID is a different import" in controller
    assert "candidate_run_ids" in controller

    assert "static/css/admin.css?v=20260817-v0.324" in html
    assert "static/js/app.js?v=20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "<strong>0.324</strong>" in html
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "Current maintained release: **v0.324**" in readme
    assert changelog.startswith(
        "# Delivery List Scanner Changelog\n\n"
        "## v0.299 - Stable Manual Delivery List Expansion"
    )


def test_v253_complete_stage_view_route_preview_and_historical_recovery_contract():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert changelog.startswith(
        '# Delivery List Scanner Changelog\n\n'
        '## v0.299 - Stable Manual Delivery List Expansion'
    )

    assert 'const managementRowsForGroup = (group, changedStageRows) =>' in app
    assert 'Restore every stage row while collapsing only Staging/Outbound into Airport Road.' in app
    assert 'const allStageRowsForGroup = (group, changedStageRows) =>' in app
    assert '<th>Stage / Route</th>' in app
    assert 'No delivery-list stages are available.' in app
    assert 'No Updates' in app
    assert '${hasAnyChanges ? "open" : ""}' not in app
    assert 'data-admin-preview-route-group=' in app
    assert 'data-print-route-groups="airport"' in app
    assert 'const outboundSourceForDate = (deliveryDate, stageRows = []) =>' in app
    assert 'Route-level previews always read from the date\'s authoritative Outbound' in app
    assert '? String(outboundSource.list.id)' in app

    preview_method = app[
        app.index('function deliveryListUpdatePreviewHtml'):
        app.index('function initializeDeliveryListUpdatePreviewControls')
    ]
    assert 'deliveryUpdatePreviewLocationKey(item)' in preview_method
    assert 'delivery-update-preview-location-body' in preview_method
    assert 'locationItems.map(itemCardHtml)' in preview_method
    assert 'data-preview-stage-section' not in preview_method
    assert 'const route = inferredRoute(item);' in app
    assert 'if (route === "GNV") return "greenville";' in app
    assert 'if (route === "CPU") return "cpu";' in app
    assert 'if (route === "DTC") return "dtc";' in app
    assert 'const normalizedRouteGroup = String(routeGroup || "").trim().replaceAll("_", "-");' in app

    assert 'fallback_stages = {' in store
    assert '"customer-pickup": ("Customer Pickup", "Customer Pickup")' in store
    assert 'delivery_list_meta = {' in store
    assert 'created_stage_items: list[dict[str, Any]] = []' in store
    assert 'for raw_item in [*history_items, *created_stage_items]:' in store
    assert '"list": delivery_list_meta' in store

    assert 'width: 34px !important;' in css
    assert 'aspect-ratio: 1 / 1;' in css
    assert '.admin-import-stage-wrap tr.route-row-airport' in css
    assert '.delivery-update-preview-location-body > .delivery-update-preview-list' in css


def test_v254_stable_manual_delivery_list_expansion_contract():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert changelog.startswith(
        '# Delivery List Scanner Changelog\n\n'
        '## v0.299 - Stable Manual Delivery List Expansion'
    )

    assert 'adminOpenDeliveryGroups: new Set()' in app
    assert 'adminDeliveryListsNormalizedMarkup: ""' in app
    assert 'data-admin-delivery-group-key=' in app
    assert 'const groupOpen = state.adminOpenDeliveryGroups.has(group.key);' in app
    assert '${hasAnyChanges ? "open" : ""}' not in app
    assert 'function normalizeAdminDeliveryListsMarkup' in app
    assert 'function rememberOpenAdminDeliveryGroups' in app
    assert 'normalizedMarkup !== state.adminDeliveryListsNormalizedMarkup' in app
    assert 'details.classList.contains("admin-import-date-group")' in app

    assert '19. v0.299 Stable manual Delivery List Management expansion' in css
    assert '.admin-import-date-group .admin-import-stage-wrap' in css
    assert 'animation: none !important;' in css
    assert '.admin-import-date-group[open] .admin-import-stage-wrap' in css
    assert 'display: block;' in css


def test_v0255_automation_repairs_stale_project_root():
    control = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    assert 'payload["ProjectRoot"] = current_root' in control
    assert 'projectRootRepaired' in control
    assert 'previousProjectRoot' in control


def test_v0255_sql_import_verifies_complete_source_row_coverage():
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    assert 'post_import_drift, post_import_drift_ids = scanner_stage_drift(' in importer
    assert 'source-row coverage is still incomplete or mismatched' in importer
    assert 'sourceCoverageVerified' in importer


def test_v0255_delivery_management_uses_saved_total_and_signed_net_delta():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert 'const importedTotal = row.totalQty ?? row.updatedQty ?? row.newQty;' in app
    assert 'const quantityDelta = managementRow.updatedQty - managementRow.originalQty;' in app
    assert 'netQuantityDeltaHtml(stagingUpdatedQty - stagingOriginalQty)' in app
    assert 'return `<span class="qty-change is-added">+${escapeHtml(value)}</span>`;' in app


def test_v0255_superseded_candidates_notify_and_refresh_badge():
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    assert '"Superseded order review needed"' in store
    assert '"source": "superseded-order-review"' in store
    assert '"/api/admin/superseded-order-reviews/summary"' in server
    assert 'refreshSupersededReviewSummary' in app
    assert '.superseded-review-open .superseded-review-count' in css


def test_v0256_same_day_import_runs_use_one_canonical_identity_and_archive():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")

    assert 'const runStartedAt = String(entry.runStartedAt || entry.startedAt || "").trim();' in app
    assert 'if (runStartedAt) return `started:${runStartedAt}|${deliveryDate}|${sourceName}`;' in app
    assert 'const key = startedAt' in app
    assert '`started:${startedAt}`' in app
    assert 'const tabs = groups.map((group) =>' in app
    assert 'data-admin-import-page' not in app[app.index('function renderAdminImportRunBrowser'):app.index('function selectImportRun')]
    assert 'if (matchedNotificationIndexes.has(notificationIndex)) return false;' in app

    assert '"run_history_dir": working_root / "State" / "RunHistory"' in controller
    assert 'def _archived_automation_import_items' in controller
    assert 'runtime_items = [*latest_items, *archived_items]' in controller
    assert 'Canonicalize by run start + date + file' in controller

    assert '$script:RunId =' in runner
    assert '"--run-id", [string]$script:RunId' in runner
    assert 'runId = [string]$script:RunId' in runner
    assert 'State\\RunHistory' in runner


def test_v0256_delivery_update_preview_groups_route_glass_order_item_without_inner_scroll():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    preview = app[
        app.index("function deliveryListUpdatePreviewHtml"):
        app.index("async function openDeliveryListUpdatePreview")
    ]
    assert 'const previewGlassType = (item) => String(item.glassType || item.product || "").trim() || "Other Glass";' in preview
    assert 'delivery-update-preview-glass-group-v256' not in preview
    assert 'delivery-update-preview-order-group-v256' not in preview
    assert 'delivery-update-preview-order-list-v311' in preview
    assert 'delivery-update-preview-location-group-v311' in preview
    assert 'delivery-update-preview-order-meta-v313' in preview
    assert 'routeStartsOpen' in preview
    assert 'data-preview-filter-button' not in preview
    assert 'data-preview-search-input' not in preview

    assert '.delivery-update-preview-v256 .delivery-update-preview-glass-list-v256' in css
    assert 'max-height: none;' in css
    assert 'overflow: visible;' in css
    assert '.delivery-update-preview-glass-group-v256' in css
    assert '.delivery-update-preview-order-group-v256' in css
    assert '.delivery-update-preview-item-body-v256' in css


def test_v0256_version_contract():
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'static/css/admin.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert '<strong>0.324</strong>' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert changelog.startswith(
        '# Delivery List Scanner Changelog\n\n'
        '## v0.301 - Complete Same-Day Import History and Hierarchical Update Preview'
    )


def test_v0257_import_run_history_keeps_five_run_pages_without_dropping_day_history():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")

    browser = app[
        app.index("function renderAdminImportRunBrowser"):
        app.index("function selectImportRun")
    ]
    assert "const pageSize = Math.max(Number(state.adminImportRunsPerPage || 5), 1);" in browser
    assert "const visibleGroups = groups.slice(pageStart, pageStart + pageSize);" in browser
    assert 'data-admin-import-page=' in browser
    assert "of ${groups.length}" in browser
    assert "adminImportRunsPerPage: 5" in app
    assert ".admin-import-run-browser-v257 .admin-import-run-tabs" in css
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in css
    assert "maximum_rows: int = 5000" in controller
    assert 'runtime_items = [*latest_items, *archived_items]' in controller


def test_v0257_preview_uses_route_glass_order_headers_and_flat_item_rows():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    preview = app[
        app.index("function deliveryListUpdatePreviewHtml"):
        app.index("async function openDeliveryListUpdatePreview")
    ]
    assert 'const headingCountHtml = (lineCount, pieces, lineLabel = "lines")' in preview
    assert "delivery-update-preview-heading-counts-v257" in preview
    assert "delivery-update-preview-order-meta-v257" in preview
    assert "delivery-update-preview-item-row-v257" in preview
    assert "delivery-update-preview-item-number-v257" in preview
    assert "delivery-update-preview-item-qty-v257" in preview
    assert "itemDetailsHtml" not in preview
    assert "delivery-update-preview-item-v256" not in preview
    assert ".delivery-update-preview-heading-counts-v257" in css
    assert ".delivery-update-preview-item-row-v257" in css
    assert "max-height: none !important;" in css
    assert "overflow: visible !important;" in css


def test_v0257_removals_are_first_class_red_quantity_and_history_values():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")

    assert "quantityFlowChangesHtml(managementRow.addedPieceQty, managementRow.removedPieceQty)" in app
    assert "quantityFlowChangesHtml(stagingAddedQty, stagingRemovedQty)" in app
    assert 'class="qty-change is-added">+${escapeHtml(added)}' in app
    assert 'class="qty-change is-removed">-${escapeHtml(removed)}' in app
    assert 'class="is-removed ${removedPieces ? "has-value" : ""}"' in app
    assert "import-history-removed-v257" in app
    assert ".admin-import-stage-wrap tr.has-removals" in css
    assert ".import-history-removed-v257" in css
    assert "canonical_source_change_metrics" in store
    assert '"removedPieceQty": int(preferred.get("removedPieceQty") or 0)' in store
    assert '"changeType": "removed"' in store


def test_v0257_superseded_review_allows_either_candidate_as_exact_removal_target():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")

    assert 'name="superseded-remove-${escapeHtml(review.id)}"' in app
    assert "review.originalOrderNumber" in app
    assert "review.replacementOrderNumber" in app
    assert "removeOrderNumber" in app
    assert "Approve selected removal" in app
    assert "remove_order_number: str = \"\"" in store
    assert "selected_remove_order not in {original_order, replacement_order}" in store
    assert "approved_remove_order_no" in store
    assert 'str(data.get("removeOrderNumber") or "")' in server
    assert "v257_superseded_remove_choice" in migrations
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract


def test_v0257_superseded_removal_creates_durable_logical_import_history():
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    assert 'import_kind, change_summary' in store
    assert "'superseded_review'" in store or '"superseded_review"' in store
    assert '"removedOrderNumber": selected_remove_order' in store
    assert '"keptOrderNumber": kept_order' in store
    assert '"affectedStageLineCount": len(rows)' in store
    assert 'logical_metrics = self.canonical_source_change_metrics(stage_summaries)' in store
    assert '"removedPieceQty": int(logical_metrics.get("removedPieceQty") or 0)' in store


def test_v0303_import_totals_and_scan_date_selection_are_catalog_safe():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "def normalize_import_change_summary" in store
    assert "normalized.update(self.canonical_source_change_metrics(stages))" in store
    assert '"newDeliveryList": new_delivery_list' in store
    assert "if result.get(\"newDeliveryList\")" in store
    assert "change_summary = self.normalize_import_change_summary(change_summary)" in store
    assert "self._normalize_import_change_summary" in controller
    assert "function normalizeImportResultMetrics" in app
    assert "Object.prototype.hasOwnProperty.call(entry, \"newDeliveryList\")" in app
    assert "function importPreviewPayloadsFromContext" in app
    assert 'previewSource: "selected-import-run"' in app
    assert 'data-admin-preview-context="${escapeHtml(previewContextKey)}"' in app
    assert 'state.lists.some((list) => String(list.deliveryDate || "") === detailDate)' in app
    assert 'state.activeListId = desiredListId;' in app
    assert "detailRefreshListId !== previousActiveListId" in app
    assert "All rows" not in app[app.index("function deliveryListUpdatePreviewHtml"):app.index("function importPreviewPayloadsFromContext")]
    assert 'APPLICATION_VERSION = "324"' in contract
    assert "static/js/app.js?v=20260817-v0.324" in html


def test_v0304_rush_popup_isolation_and_tc22_mobile_ownership():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    import_safety = (ROOT / "backend" / "import_safety.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert "function isRushPopupNotification(notification)" in app
    assert 'if (type !== "rush") return false;' in app
    assert 'if (!isRushPopupNotification(notification)) continue;' in app
    assert 'if (!isRushPopupNotification(notification) || rushNotificationIsBlocked()) return false;' in app
    assert '"source": "operator-priority-work"' in store
    assert "def imported_nonpriority_state" in store
    assert 're.search(r"\\b(?:SDI|RUSH)\\b", text)' in store
    assert '"process_state": imported_nonpriority_state(item.get("processState", ""))' in store
    assert 'if notification_type != "rush":' in import_safety
    assert '"superseded-order-review"' in import_safety
    assert 'created_by.startswith("sql-auto")' in import_safety

    for stylesheet in (
        "styles.css", "home.css", "scan.css", "racks.css", "bays.css",
        "admin.css", "statistics.css", "rejects.css", "print.css",
    ):
        css = (ROOT / "static" / "css" / stylesheet).read_text(encoding="utf-8")
        assert "v0.304" in css, stylesheet
        assert "@media (max-width: 760px)" in css, stylesheet

    styles = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    assert "--mobile-touch-target: 44px" in styles
    assert "env(safe-area-inset-bottom)" in styles
    assert "@media (max-width: 430px)" in styles
    assert "v0.304 TC22-first Scan workspace" in scan
    assert "min-height: 52px !important" in scan

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert "20260817-v0.324" in html
    assert 'aria-label="Application version 0.324"' in html
    assert "v0.304" in readme
    assert "## v0.304 - TC22 Mobile Workspace and Rush Notification Isolation" in changelog


def test_v0306_single_page_mobile_workflow_and_dialog_repairs():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    mobile = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")

    assert 'viewport-fit=cover' in html
    assert 'static/css/mobile.css?v=20260817-v0.324' in html
    assert html.index('static/css/shared-ui.css') < html.index('static/css/mobile.css')
    assert html.index('static/css/mobile.css') < html.index('static/js/app.js')
    assert mobile.startswith("/* File: static/css/mobile.css */")
    assert "@media (max-width: 760px)" in mobile
    assert "@media (max-width: 430px)" in mobile
    assert "orientation: landscape" in mobile
    assert 'class="mobile-nav"' not in html
    assert 'data-mobile-target' not in html
    assert 'document.body.dataset.mobileView' not in app
    assert 'body[data-page="scan"] .scan-page :is(.scanner-panel, .list-panel, .mobile-list-cards, .summary-grid)' in mobile
    assert '.mobile-card-job' in mobile
    assert '.mobile-card-scan-state' in mobile
    assert '<small>Job Nr.</small>' in app
    assert 'data-label="Order / Item / Job Nr."' in app
    assert '#adminModal[data-kind="recentScans"]' in mobile
    assert '#printOptionsPanel .print-options-workspace-v197' in mobile
    assert '.app-sidebar .brand-combined-logo' in mobile
    assert '.header-actions :is(.button-icon, .language-globe-icon, .refresh-page-icon, .fullscreen-icon)' in mobile
    assert '.bay-floor-grid-v19 .physical-bay-section-v17[open]' in mobile
    assert ".slice(0, 12)" not in app
    assert html.index('id="mobileListCards"') < html.index('id="scanPanel"')
    assert 'APPLICATION_VERSION = "324"' in contract

def test_v0307_rack_review_history_creation_and_status_reliability() -> None:
    """v0.307 keeps review receipts per user and makes rack management deterministic."""
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend/operations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'static/css/racks.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert '## v0.307 - Rack Review Synchronization and Rack Manager Reliability' in changelog

    # v0.308 deliberately broadens the v0.307 Airport review propagation from
    # one import fingerprint to every current notice on that delivery date.
    # Preserve the v0.307 guarantees that receipts remain per-user and direct
    # route-stage reviews stay separate.
    assert 'def _airport_review_scope' in operations
    assert 'INSERT OR IGNORE INTO line_update_receipts' in operations
    assert '(notice_id, user_id, seen_at)' in operations
    assert '"selected-stage"' in operations
    assert 'state?.pendingUpdateStages?.delete?.(listId);' in app
    assert 'renderDeliveryListSelect();' in app

    for icon in ('glasscart', 'pallet', 'dolly', 'crate', 'warehouse'):
        assert f'"{icon}"' in store
    assert 'LOWER(TRIM(display_name)) = LOWER(TRIM(?))' in store
    assert 'Rack name {name!r} is already used by' in store
    assert 'Rack set {rack_type!r} already exists' in store
    assert 'UPPER(rack_code) IN' in store

    assert 'function rackFormDraftValidation()' in app
    assert 'function rackSetDraftValidation()' in app
    assert 'Rack code and name are available.' in app
    assert 'already exists. Add an individual rack to that set instead.' in app
    assert 'syncRackDraftValidation(form, { ok: false, message: error.message }, "[data-rack-form-validation]")' in app
    assert 'syncRackDraftValidation(form, { ok: false, message: error.message }, "[data-rack-set-validation]")' in app
    assert 'if (qty > 0) return "Incomplete";' in app
    assert '>Incomplete</option>' in app
    assert 'rack-board-state-v307' in app
    assert 'if (a === "Truck") return -1;' in app

    assert '#adminModal[data-kind="racks"] .rack-manager-grid {' in racks_css
    assert '.rack-draft-validation-v307 {' in racks_css
    assert '.rack-board-state-v307.complete {' in racks_css
    assert '.rack-board-state-v307.in-transit {' in racks_css



def test_v0308_rack_review_history_preview_and_scan_repairs() -> None:
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '"scope": "airport-delivery-date" if airport_scope else "selected-stage"' in operations
    assert "SELECT n.id, n.list_id" in operations and "AND n.delivery_date = ?" in operations
    assert "completed_at = '', departed_at = ''" in store
    assert "def _insert_rack_definition" in store
    assert "rackFormExistingSetRacksHtml" in app
    assert "rack-details-status-banner-v308" in app
    assert "delivery-update-preview-order-block-v308" in app
    assert "delivery-update-preview-location-title-v308" in app
    assert 'selectedRoute !== "airport"' in app
    preview_block = app[app.index("function deliveryListUpdatePreviewHtml"):app.index("function initializeDeliveryListUpdatePreviewControls")]
    assert '<section class="delivery-update-preview-order-group-v256' in preview_block
    assert '<details class="delivery-update-preview-order-group-v256' not in preview_block
    assert "New QTY" not in preview_block or "changeWord" in preview_block
    bay_block = app[app.index("function renderBaySection(section)"):app.index("function renderBayLayoutDropZone", app.index("function renderBaySection(section)"))]
    assert "bay-section-status status-" not in bay_block
    assert " open</i>" not in bay_block
    assert "/${escapeHtml(totalBays)} used" in bay_block
    assert '#operationsModal.is-control-center[data-kind="rack-history"]' in racks
    assert 'overflow-y: auto !important' in racks
    assert '#adminModal[data-kind="racks"] .rack-manager-grid' in racks and 'flex-direction: column !important' in racks
    assert '.delivery-update-preview-order-header-v308' in admin
    assert '.scan-page .scanner-panel:not(.bay-scanner-panel)' in scan and 'z-index: 40 !important' in scan
    assert 'row-marker.remake-marker::after' in scan
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html


def test_v0309_rack_creation_sticky_stage_and_bay_group_status_polish() -> None:
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'def _insert_rack_definition' in store
    assert 'PRAGMA table_info(racks)' in store
    assert '"completed_at": ""' in store
    assert 'not_null and default_value is None' in store
    assert 'self._insert_rack_definition(' in store
    assert 'self._insert_rack_definition(con, code, name, rack_type, sort_order)' in store

    assert '["deliveryDateSelect", "deliveryStageSelect"].includes(customSelectUi.openSelect.id)' in app
    assert 'window.requestAnimationFrame(positionCustomSelectMenu);' in app
    assert 'scanner-panel-stage-select-v196' in scan
    assert 'data-select-id="deliveryStageSelect"' in scan
    assert 'z-index: 14000 !important' in scan

    bay_block = app[app.index("function renderBaySection(section)"):app.index("function bayLayoutColumns", app.index("function renderBaySection(section)"))]
    assert 'const utilizationHue = Math.round(120 * (1 - utilizationRatio));' in bay_block
    assert '--bay-group-utilization-hue:' in bay_block
    assert 'bay-section-attention-v309' in bay_block
    assert 'bay-section-utilization-v310' in bay_block
    assert 'content: none !important' in bays
    assert '--bay-group-utilization-hue' in bays
    assert '.bay-section-attention-v309' in bays

    assert '#rackPackingHistoryBtn, #rackEditOpenBtn' in racks
    assert 'height: 36px !important' in racks
    assert 'content: none !important' in racks
    assert 'pointer-events: auto !important' in racks

    assert 'static/css/racks.css?v=20260817-v0.324' in html
    assert 'static/css/scan.css?v=20260817-v0.324' in html
    assert 'static/css/bays.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.309 - Rack Creation Compatibility, Sticky Stage, and Bay Group Status Polish' in changelog


def test_v0310_physical_bay_policy_attention_and_used_count_clarity() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract

    assert 'function bayAttentionReasons(bay)' in app
    assert 'function bayNeedsAttention(bay)' in app
    assert 'const attentionReasons = bayAttentionReasons(bay);' in app
    assert 'bay-slot-attention-v310' in app
    assert 'operationalBays.filter((bay) => bayNeedsAttention(bay)).length' in app

    bay_block = app[app.index("function renderBaySection(section)"):app.index("function bayLayoutColumns", app.index("function renderBaySection(section)"))]
    assert 'bay-section-policy-v310' in bay_block
    assert 'auto: "AUTO"' in bay_block
    assert 'manual: "MAN"' in bay_block
    assert 'bay-section-occupancy-v312' in bay_block
    assert '<strong>${escapeHtml(occupied)}</strong><span>/${escapeHtml(totalBays)}</span>' in bay_block

    assert '.bay-section-policy-v310' in bays
    assert '.bay-section-used-current-v310' in bays
    assert 'color: hsl(var(--bay-group-utilization-hue, 120)' in bays
    assert '.bay-slot-attention-v310' in bays

    assert 'static/css/bays.css?v=20260817-v0.324' in html
    assert 'static/js/app.js?v=20260817-v0.324' in html
    assert 'aria-label="Application version 0.324"' in html
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.310 - Physical Bay Policy and Attention Clarity' in changelog



def test_v311_rack_transfer_history_preview_and_bay_persistence() -> None:
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    move_start = store.index("def move_rack_contents")
    move_end = store.index("def ", move_start + 10)
    move_body = store[move_start:move_end]
    assert "completed_by" not in move_body
    assert "departed_by" not in move_body
    assert "returned_by" not in move_body
    assert "SET status = 'Open', completed_at = ''" in move_body

    seed_start = store.index("def seed_layout_bays")
    seed_end = store.index("def ", seed_start + 10)
    seed_body = store[seed_start:seed_end]
    assert "TRIM(COALESCE(bays.display_name, '')) <> '' THEN bays.display_name" in seed_body

    assert '.rack-history-control-center > [data-rack-history-panel]' in racks
    assert 'overflow-y: auto !important' in racks
    assert 'touch-action: pan-y' in racks
    assert 'right: 9px !important' in racks
    assert 'resetPageScrollPosition' in app
    assert 'overflow-anchor: none' in racks
    assert 'height: 36px !important' in racks

    assert ".scan-page .delivery-table td:nth-child(8) {\n  width: 5%" in scan
    assert ".scan-page .delivery-table td:nth-child(10) {\n  width: 12%" in scan
    assert 'td:nth-child(10) .process-pill' in scan
    assert 'white-space: nowrap !important' in scan

    preview_start = app.index("function deliveryListUpdatePreviewHtml")
    preview_end = app.index("function initializeDeliveryListUpdatePreviewControls", preview_start)
    preview = app[preview_start:preview_end]
    assert 'delivery-update-preview-glass-group-v256' not in preview
    assert 'delivery-update-preview-order-list-v311' in preview
    assert 'delivery-update-preview-item-glass-v311' in preview
    assert 'delivery-update-preview-item-size-v311' in preview
    assert 'exactGlassColorMap' in preview
    assert 'glassVisualCssVariables' in preview
    assert 'delivery-update-preview-order-meta-v313' in preview
    assert 'routeStartsOpen' in preview
    assert '.delivery-update-preview-item-row-v311' in admin
    assert 'var(--glass-type-color' in admin

    render_start = app.index("function renderBaySection")
    render_end = app.index("function bayLayoutColumns", render_start)
    render_bay = app[render_start:render_end]
    assert 'bay-section-occupancy-v312' in render_bay
    assert '<strong>${escapeHtml(occupied)}</strong><span>/${escapeHtml(totalBays)}</span>' in render_bay
    assert '/${escapeHtml(totalBays)} used' not in render_bay
    assert '.bay-section-occupancy-v312' in bays

    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index


def test_v312_compact_bay_capacity_and_managed_glass_colors() -> None:
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract

    render_bay = app[app.index("function renderBaySection(section)"):app.index("function bayLayoutColumns", app.index("function renderBaySection(section)"))]
    assert 'bay-section-occupancy-v312' in render_bay
    assert '<strong>${escapeHtml(occupied)}</strong><span>/${escapeHtml(totalBays)}</span>' in render_bay
    assert 'bay-section-occupancy-meter-v311' not in render_bay
    assert '.bay-section-occupancy-v312' in bays

    assert 'left: auto !important;' in racks
    assert 'right: 9px !important;' in racks

    assert '"glass_color": {}' in store
    assert '"glassColors": sorted(' in store
    assert 'lookup_type not in {"product", "route", "process", "glass_cost", "glass_color"}' in store
    assert 'Glass color must be a six-digit hex color' in store
    assert '"color": category' in store

    assert 'glassColors: Array.isArray(payload.glassColors)' in app
    assert 'function buildGlassVisualColorMap(extraLabels = [])' in app
    assert 'function glassVisualCssVariables(label, colorMap = null)' in app
    assert '["glass_color", "Glass colors", glassColorTotal]' in app
    assert 'id="lookupColorInput" type="color"' in app
    assert 'data-preview-glass-type=' in app
    assert '--glass-type-color:' in app
    assert '--preview-glass-hue' not in app[app.index("function deliveryListUpdatePreviewHtml"):app.index("function initializeDeliveryListUpdatePreviewControls")]
    assert '.lookup-manager-list.glass-colors' in admin
    assert 'var(--glass-type-color' in admin

    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.312 - Compact Bay Capacity and Managed Glass Color Palette' in changelog


def test_v0313_rack_action_navigation_hitbox_and_compact_update_preview() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract

    show_page_start = app.index("function resetPageScrollPosition()")
    show_page_end = app.index("function showOutboundOverrideDialog", show_page_start)
    show_page = app[show_page_start:show_page_end]
    assert 'document.querySelector(".app > main")' in show_page
    assert 'document.querySelectorAll(".page-view").forEach' in show_page
    assert 'resetPageScrollPosition();' in show_page
    assert 'requestAnimationFrame(() => {' in show_page

    assert 'overflow-anchor: none' in racks
    assert 'height: 36px !important' in racks
    assert 'content: none !important' in racks
    assert 'top: -10px !important' not in racks
    assert 'right: 9px !important' in racks

    preview_start = app.index("function deliveryListUpdatePreviewHtml")
    preview_end = app.index("function initializeDeliveryListUpdatePreviewControls", preview_start)
    preview = app[preview_start:preview_end]
    assert 'delivery-update-preview-v313' in preview
    assert 'delivery-update-preview-order-list-v311' in preview
    assert 'delivery-update-preview-item-glass-v311' in preview
    assert 'delivery-update-preview-item-size-v311' in preview
    assert 'glassVisualCssVariables' in preview
    assert 'data-preview-filter-button' not in preview
    assert 'data-preview-search-input' not in preview
    assert 'delivery-update-preview-metrics-v230' not in preview
    assert 'Glass Types</small>' not in preview
    assert '${escapeHtml(items.length)} changed line' in preview

    assert 'width: min(1100px, calc(100vw - 48px));' in admin
    assert '.delivery-update-preview-v313' in admin
    assert '.delivery-update-preview-order-meta-v313' in admin

    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.313 - Rack Action Hitbox and Compact Delivery Update Preview' in changelog


def test_v0314_rack_hitbox_all_date_transit_and_bay_editor_feedback() -> None:
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract

    assert 'function stabilizeRackHeadingActions()' in app
    assert 'function scheduleRackHeadingStabilization()' in app
    assert 'function forwardRackHeadingActionClick(event)' in app
    assert 'document.addEventListener("click", forwardRackHeadingActionClick, true)' in app
    assert '.then(() => scheduleRackHeadingStabilization())' in app
    assert '#racksPage' in racks
    assert 'overflow-anchor: none !important' in racks

    transit_start = store.index('def _indian_trail_in_transit_payload')
    transit_end = store.index('def indian_trail_outbound_totals', transit_start)
    transit_store = store[transit_start:transit_end]
    assert 'if not requested_date:' in transit_store
    assert 'SELECT DISTINCT src_dl.delivery_date' in transit_store
    assert '"deliveryDates": delivery_dates' in transit_store
    assert '"deliveryDate": resolved_date' in transit_store
    assert "IN ('INDIAN TRAIL', 'IT')" in transit_store

    assert 'fetchJson("/api/indian-trail/in-transit")' in app
    assert 'function indianTrailDateQuery() {\n  const deliveryDate = todayKey();' in app
    assert 'const key = todayKey();' in app[app.index('function renderBayRouteFlow(summary)'):app.index('function transitManifestRowHtml', app.index('function renderBayRouteFlow(summary)'))]
    assert 'fetchJson(`/api/indian-trail/in-transit${indianTrailDateQuery()}`)' not in app
    assert '<th>Delivery</th><th>Job Nr.</th>' in app
    assert 'data-progress-sound-test="transit"' not in app
    assert '.transit-manifest-header::after' in bays

    assert 'class="app-primary-button" data-bay-editor-action="save-group"' in app
    assert 'class="app-primary-button" data-bay-editor-action="add-bays"' in app
    assert 'class="app-primary-button" data-bay-editor-action="create-group"' in app
    assert 'class="app-primary-button" data-bay-editor-action="save-bay"' in app
    assert 'function setBayEditorProgress' in app
    assert 'data-bay-editor-progress' in app
    assert '.bay-editor-progress-track' in bays
    assert 'id="bayEditorNewGroupBtn" class="app-primary-button"' in index

    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.314 - Rack Hitbox, All-Date In-Transit, and Bay Editor Feedback' in changelog


def test_v0315_in_transit_rack_icon_and_numeric_dates() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'item.deliveryDate ? formatNumericDeliveryDate(item.deliveryDate) : "-"' in app
    assert 'item.deliveryDate ? formatNumericDeliveryDate(item.deliveryDate) : item.deliveryLabel || ""' in app
    assert 'return rackSetVisualIcon(rack?.type || rack?.name || rack?.code || "Rack")' in app
    assert 'function transitRackIconStyle(rack)' in app
    assert 'class="rack-set-visual-icon-v269 transit-rack-icon"' in app
    assert 'data-rack-icon="${escapeHtml(transitRackIconClass(rack))}"' in app
    assert '.transit-rack-head .transit-rack-icon.rack-set-visual-icon-v269' in bays
    assert 'border-radius: 11px !important' in bays
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.315 - In-Transit Rack Icon and Numeric Date Repair' in changelog


def test_v316_physical_transit_counts_bay_bulk_edit_and_scan_archive_compaction() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert "Rack assignments are the physical source of truth once a rack departs" in store
    transit_start = store.index("    def _indian_trail_in_transit_payload(")
    transit_end = store.index("\n    def indian_trail_outbound_totals(", transit_start)
    transit_block = store[transit_start:transit_end]
    assert "received_by_key" in transit_block
    assert "rack_map_by_item" in transit_block
    assert "if key not in inventory" not in transit_block
    assert "AND COALESCE(src_li.is_deleted, 0) = 0" not in transit_block
    assert "JOIN delivery_lists src_dl ON src_dl.id = src_li.list_id AND src_dl.status = 'active'" not in transit_block

    assert "bayEditorSelectedBayCodes: new Set()" in app
    assert 'data-bay-editor-selection-action="all"' in app
    assert 'data-bay-editor-action="save-selected"' in app
    assert "async function saveBayEditorSelectedBays()" in app
    assert 'title: "Physical bay scan history"' in app
    assert 'eyebrow: "Indian Trail activity archive"' in app
    assert "Location corrections belong here" not in app
    assert "bay-all-scans-summary-strip-v316" in app

    assert "v0.316 Physical transit counts, Bay multi-select, and compact scan archive" in bays
    assert ".bay-editor-bulk-tools-v316" in bays
    assert ".bay-all-scans-guidance-v317" in bays
    assert "static/css/bays.css?v=20260817-v0.324" in index
    assert "static/js/app.js?v=20260817-v0.324" in index



def test_v317_all_date_transit_count_bay_row_selection_and_compact_guidance() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.317 - All-Date Transit Count and Bay Selection Polish' in changelog

    summary_start = store.index("    def indian_trail_summary(")
    summary_end = store.index("\n    def admin_search_line_items(", summary_start)
    summary = store[summary_start:summary_end]
    assert 'date_in_transit_payload = self._indian_trail_in_transit_payload(con, resolved_date or delivery_date)' in summary
    assert 'in_transit_payload = self._indian_trail_in_transit_payload(con, "")' in summary
    assert '"inTransitQty": in_transit_payload.get("totalQty", 0)' in summary
    assert '"dateInTransitQty": date_in_transit_payload.get("totalQty", 0)' in summary

    assert 'function setBayEditorGroupSelection(selectAll)' in app
    assert 'function toggleBayEditorRowSelection(bayCode)' in app
    assert 'data-bay-editor-selection-action="all"' in app
    assert 'data-bay-editor-selection-action="clear"' in app
    assert 'data-bay-editor-select-row=' in app
    assert 'interactiveTarget = event.target.closest("input, select, textarea, button, a, label")' in app
    assert 'data-bay-editor-select-all' not in app

    assert 'bay-all-scans-topline-v317' in app
    assert 'bay-all-scans-guidance-v317' in app
    assert 'bay-all-scans-guidance-v159 bay-all-scans-guidance-v316' not in app
    assert '#adminModal[data-custom-view="bay-all-scans"] .bay-full-scans-modal-v159' in bays
    assert 'grid-auto-rows: max-content' in bays
    assert '.bay-all-scans-guidance-v317' in bays
    assert '.bay-editor-selection-actions-v317' in bays
    assert '.bay-editor-bay-row-v317' in bays


def test_v318_bay_operations_exact_item_management_and_priority_clarity() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.318 - Bay Operations, Exact-Item Management, and Priority Work Clarity' in changelog

    # Old Bays and Bay Scanner receive the shared decorative ring treatment, and
    # the Old Bays row surface itself owns selection rather than only the checkbox.
    assert '.stale-bay-header-v181::after' in bays
    assert '.bay-scanner-panel-v150 .bay-scanner-header-v150::after' in bays
    assert 'data-stale-assignment-row=' in app
    assert 'event.target.closest("[data-stale-assignment-row]")' in app

    # Rush priority work carries source audit metadata and keeps expanded detail
    # above the surrounding card so dates/user/item information remains visible.
    assert 'priorityPreviousDeliveryDate' in store
    assert 'priorityMarkedAt' in store
    assert 'priorityMarkedBy' in store
    assert 'for offset in range(0, len(line_ids), 500)' in store
    assert '<small>Original delivery</small>' in app
    assert '<small>Priority delivery</small>' in app
    assert '<small>Marked by</small>' in app
    assert '#sdiPanel .sdi-current-group.is-expanded' in bays
    assert 'overflow: visible !important' in bays

    # Manage Items supports job-level and exact-item selection. Moving an exact
    # assignment preserves intentionally split sibling locations.
    assert 'manageItemsSelectedIds: new Set()' in app
    assert 'data-manage-group-card=' in app
    assert 'data-manage-item-select=' in app
    assert 'data-manage-selection-action="all"' in app
    assert 'data-manage-selection-action="clear"' in app
    assert 'function manageBayLocationLabel' in app
    assert 'body: JSON.stringify({ assignmentId: assignment.id, newBayCode: targetBay, reason, ...requestContext() })' in app

    # Selected Bay resolves each sibling item against its actual latest location,
    # and audit history receives enough identity/location context to be searchable.
    assert '"selectedBayQty": selected_qty' in store
    assert '"bayGroup": item_bay_group' in store
    assert 'item.isInSelectedBay' in app
    assert 'In another bay' in app
    assert 'def _bay_assignment_audit_context' in store
    assert '"oldBayGroup": previous_context.get("bayGroup", "")' in store
    assert 'if (action === "move_bay")' in app
    assert 'if (action.startsWith("set_bay_"))' in app
    assert 'if (action.startsWith("bay_check_"))' in app


def test_v319_manage_items_readability_scanner_footer_boundary_and_transit_contrast() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.319 - Manage Items Readability and Bay Scanner Footer Boundary' in changelog

    # Manage Items gives the left job/order workspace enough room and stacks
    # exact-item location information instead of horizontally clipping it.
    assert 'grid-template-columns: minmax(560px, 1.08fr) minmax(500px, .92fr) !important;' in bays
    assert 'grid-template-areas:' in bays
    assert '"select identity status"' in bays
    assert '". location location"' in bays
    assert '#manageItemsPanel .manage-item-exact-identity strong' in bays
    assert 'white-space: normal;' in bays

    # The fixed Bay Scanner is bounded by the real application footer.
    assert 'appFooter: document.querySelector(".desktop-footer")' in app
    assert 'const footerRect = els.appFooter?.getBoundingClientRect();' in app
    assert 'footerRect.top - visiblePanelHeight - 8' in app
    assert '--bay-scanner-fixed-max-height-v319' in app
    assert '--bay-scanner-fixed-max-height-v319' in bays

    # In-transit count uses full white contrast in the scanner route pulse.
    assert '.bay-scanner-panel-v150 .bay-route-metrics-v150 .bay-panel-route-lane > span' in bays
    assert 'color: #ffffff !important;' in bays

    # Requested bay-operation action history already formats work identity from
    # the enriched v0.318 audit payload; keep the one shared renderer.
    assert 'const job = String(payload.job || "").trim();' in app
    assert 'const order = String(payload.order || "").trim();' in app
    assert 'const item = String(payload.item || "").trim();' in app
    assert 'const workRef = [jobRef, itemRef].filter(Boolean).join(" · ");' in app


def test_v320_truck_identity_lifecycle_guards_and_manage_items_scroll() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.320 - Truck Rack Consistency and Manage Items Scrolling' in changelog

    # Truck 1 retains code T for compatibility but No Rack is a distinct blank
    # location choice and every truck gets an explicit operator-facing number.
    assert 'if text == "NORACK":' in store
    assert 'return ""' in store[store.index('def normalize_rack_code'):store.index('def rack_public_label')]
    assert 'return "Truck 1"' in store
    assert 'rack_defs.append(("T", "Truck 1", "Truck", 99))' in store
    assert 'Truck / No Rack' not in app
    assert 'selectedScanRackCode: NO_RACK_SELECTION' in app
    assert 'function rackDisplayLabelFromParts' in app
    assert 'title="Edit Truck 1"' in app
    assert 'return rackLocationDisplayLabel(previousRackCode' in app
    assert 'const rackIdentity = isTruck' in app
    assert 'rack_public_label(row["rack_code"], row["rack_name"], row["rack_type"])' in store
    assert 'Truck / no rack' not in app

    # A locked rack is rejected before staging scanned_qty/rack_items mutation,
    # and the same validator protects moves/manual recovery.
    record_scan = store[store.index('            rack_code_for_scan = normalize_rack_code'):store.index('    def matching_staging_row_for_outbound')]
    lock_index = record_scan.index('rack_lock_message = rack_assignment_lock_message')
    qty_index = record_scan.index('UPDATE line_items SET scanned_qty = scanned_qty + 1')
    assert lock_index < qty_index
    assert 'rack_lock_message = rack_assignment_lock_message(rack["rack_code"], rack["status"])' in store
    validate_block = store[store.index('    def validate_rack_destination_for_item'):store.index('    def complete_rack')]
    assert 'rack_assignment_lock_message' in validate_block
    assert 'disableLocked: true' in app
    assert 'The selection was cleared.' in app

    # The left Manage Items workspace owns its own scroll region rather than
    # shrinking long job/item cards inside the modal.
    assert 'v0.320 - Manage Items left-workspace scrolling' in bays
    assert '#manageItemsPanel.manage-items-panel-v182 .manage-items-sidebar' in bays
    assert 'display: flex !important;' in bays
    assert 'overflow-y: auto !important;' in bays
    assert 'scrollbar-gutter: stable;' in bays


def test_v321_rack_card_persistence_indian_trail_feedback_and_one_order_per_bay() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    styles = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.321 - Rack Cards, Persistent Bays, and Indian Trail Scan Safety' in changelog

    # Rack lifecycle text is a content-sized absolute badge and the reset action
    # is independently anchored at the lower-right of the card.
    rack_state = racks[racks.index('.rack-board-state-v307 {'):racks.index('.rack-board-state-v307 i {')]
    assert 'position: absolute;' in rack_state
    assert 'width: fit-content;' in rack_state
    assert 'min-height: 0;' in rack_state
    assert 'white-space: nowrap;' in rack_state
    assert '.rack-overview-card-grid .rack-board-card > .rack-board-card-meta > .icon-reset' in racks
    assert 'bottom: 12px;' in racks
    assert 'right: 12px;' in racks

    # Existing bay rows stay database-authoritative after restart rather than
    # being overwritten from the bundled layout JSON.
    seed = store[store.index('    def seed_layout_bays('):store.index('    def seed_bay_auto_assign_settings(')]
    assert 'The JSON map is bootstrap-only after a bay exists' in seed
    assert "map_section = COALESCE(NULLIF(TRIM(bays.map_section), ''), excluded.map_section)" in seed
    assert 'capacity_qty = bays.capacity_qty' in seed
    assert 'active = bays.active' in seed
    assert "status = COALESCE(NULLIF(TRIM(bays.status), ''), excluded.status)" in seed
    assert 'legacy_synthetic_bay_cleanup_v321' in seed
    assert 'self.system_metadata_value(con, legacy_cleanup_key) != "done"' in seed
    assert 'self.set_system_metadata_value(con, legacy_cleanup_key, "done")' in seed

    security_start = store.index('    def seed_security_data(')
    security = store[security_start:store.index('    def seed_user_if_missing(', security_start)]
    assert 'Built-in role defaults are bootstrap values only.' in security
    assert 'if existing_role:' in security
    assert 'continue' in security
    assert 'INSERT OR IGNORE INTO role_permissions' in security

    # One physical bay may contain multiple lines from the same order but never
    # active assignments from different Order Nr. values.
    assert 'def bay_active_order_numbers' in store
    assert 'def ensure_bay_accepts_order' in store
    assert 'Each bay may contain only one Order Nr.' in store
    find_bay = store[store.index('    def find_bay_for_assignment('):store.index('    def get_bay_by_code(')]
    assert 'AND NOT EXISTS (' in find_bay
    assert "ba.status NOT IN ('Cleared', 'Cancelled')" in find_bay
    receive_start = store.index('    def _receive_indian_trail_scan_for_list(')
    receive = store[receive_start:store.index('    def move_bay_assignment(', receive_start)]
    assert 'AND order_no = ?' in receive
    validate_index = receive.index('self.ensure_bay_accepts_order(con, target_bay, row["order_no"], group_ids)')
    qty_index = receive.index('UPDATE line_items SET scanned_qty = scanned_qty + 1')
    assert validate_index < qty_index
    preassign_start = store.index('    def preassign_bay_for_outbound(')
    preassign = store[preassign_start:store.index('    def reset_stage(', preassign_start)]
    assert 'Physical bay ownership is Order Nr.-based.' in preassign
    assert 'AND COALESCE(job, \'\') = ?' not in preassign

    # Manual selection hides occupied bays and returns to Auto only after a
    # successful manual receive. The correction popup may still show its current bay.
    assert 'function bayAvailableForNewOrderAssignment' in app
    assert '.filter(bayAvailableForNewOrderAssignment)' in app
    assert 'bayAvailableForNewOrderAssignment(bay) || (preservedCode && bay.bayCode === preservedCode)' in app
    assert 'const usedManualBayAssignment = state.bayOverrideMode === "manual"' in app
    assert 'if (result.ok && usedManualBayAssignment)' in app
    assert 'state.bayOverrideMode = "auto";' in app
    assert 'state.selectedBayOverrideCode = "";' in app

    # Indian Trail success, last/recent scan, and Global Search expose physical
    # location with enough size/context to be useful on the floor.
    assert 'indian-trail-placement-destination-v321' in app
    assert 'PLACE THIS ORDER IN' in app
    assert 'font-size: clamp(34px, 5vw, 52px);' in styles
    assert 'id="lastBay"' in index
    assert '<th>Bay</th>' in index
    assert 'recent-bay-cell-v321' in app
    assert 'last-bay-location-v321' in scan
    assert 'global-result-scan-time-v321' in app
    assert 'Scanned ${escapeHtml(formatDateTime(result.lastScanTime))}' in app
    assert '"bayCode": row_value(row, "bay_code", "")' in store


def test_v322_automated_dl_import_restores_non_history_tab_scrolling() -> None:
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert ".delivery-automation-tab.is-active:not(.import-history-workspace)" in admin_css
    assert "overflow-y: auto;" in admin_css
    assert "overflow-x: hidden;" in admin_css
    assert "overscroll-behavior: contain;" in admin_css
    assert "scrollbar-gutter: stable;" in admin_css
    assert ".delivery-automation-tab.import-history-workspace.is-active {\n  overflow: hidden;\n}" in admin_css
    assert ".delivery-automation-tab.import-history-workspace.is-active .import-history-results" in admin_css
    assert 'static/css/admin.css?v=20260817-v0.324' in index
    assert 'static/js/app.js?v=20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert '<strong>0.324</strong>' in index
    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert 'Current maintained release: **v0.324**' in readme


def test_v323_automation_schedule_runtime_self_heals_before_install() -> None:
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.323 - Self-Healing Automated Import Schedule Runtime' in changelog

    # The controller deploys everything the PowerShell installer and runner need,
    # not only the four reconciliation files used by earlier browser-started runs.
    for required_name in (
        'Install-DeliveryListSqlAutomationTasks.ps1',
        'Remove-DeliveryListSqlAutomationTasks.ps1',
        'Initialize-DeliveryListSqlAutomation.ps1',
        'Show-DeliveryListSqlAutomationStatus.ps1',
        'Verify-DeliveryListSqlAutomation.ps1',
        'validate_scanner_compatibility.py',
        'build_delivery_workbook.py',
        'publish_automation_notification.py',
        'verify_delivery_import.py',
    ):
        assert f'"{required_name}"' in controller

    assert 'def _ensure_installed_runtime_config' in controller
    assert 'script_root"] / "sql-export.config.json"' in controller
    assert 'runtime["PythonPath"] = str(python_path)' in controller
    assert 'def _ensure_schedule_command_wrappers' in controller
    assert '("Run-Incremental.cmd", "Incremental")' in controller
    assert '("Run-Full.cmd", "Full")' in controller
    assert '-RunAction Configured' in controller
    assert 'def _prepare_schedule_runtime' in controller
    assert 'prepared = self._prepare_schedule_runtime(config)' in controller
    assert 'Scheduled-task script is missing after runtime refresh' in controller
    assert 'config.setdefault("Automation", {})["ScheduleEnabled"] = self._schedule_installed()' in controller
    assert 'config.setdefault("Automation", {})["ScheduleEnabled"] = True' in controller



def test_v324_persistent_manual_overrides_and_superseded_order_enforcement() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    builder = (ROOT / "automation" / "sql_delivery_export" / "build_delivery_workbook.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    verifier = (ROOT / "automation" / "sql_delivery_export" / "verify_delivery_import.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "324"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 11' in contract
    assert '20260817-v0.324' in index
    assert 'aria-label="Application version 0.324"' in index
    assert 'Current maintained release: **v0.324**' in readme
    assert '## v0.324 - Persistent Manual Overrides and Superseded Order Enforcement' in changelog

    # Approved superseded decisions remain durable even when A+W changes the
    # candidate fingerprint, and every source-owned row from that source order
    # is soft-retired from live lists/racks/bays rather than hard-deleted.
    assert 'def approved_superseded_order_exclusion_orders' in store
    assert 'approved_target_still_present' in store
    assert 'preservedApprovalCount' in store
    assert 'def _remove_approved_superseded_rows' in store
    removal_start = store.index('    def _remove_approved_superseded_rows(')
    removal_end = store.index('    def decide_superseded_order_review(', removal_start)
    removal = store[removal_start:removal_end]
    assert 'source_order == clean_remove_order' in removal
    assert "SET status = 'Removed'" in removal
    assert "SET status = 'Cancelled'" in removal
    assert 'SET is_deleted = 1' in removal
    assert 'DELETE FROM line_items' not in removal
    assert 'self.refresh_rack_destination(con, rack_id)' in removal

    # Operator edits are keyed to immutable source identity and replay only the
    # fields the operator actually changed. Explicit route edits outrank normal
    # Job Nr./customer route inference during every later import.
    assert 'def manual_import_override_entries' in store
    assert '"sourceMatchKey": manual_source_match_key' in store
    assert '"sourceOwned": manual_source_owned' in store
    assert '"manualOverrides": self.manual_import_override_entries()' in store
    assert 'def apply_persistent_import_decisions_to_payload' in store
    assert 'next_item["manualRouteOverride"] = value' in store
    assert 'def prepare_import_payload' in store
    assert 'if "manualRouteOverride" in item:' in store
    import_start = store.index('    def import_delivery_list(')
    import_block = store[import_start:store.index('    def record_scan(', import_start)]
    assert 'payload = self.prepare_import_payload(payload)' in import_block

    # The SQL exporter consumes durable order-level exclusions and manual field
    # overrides before writing a new workbook, so the file itself no longer
    # restores the raw SQL row after an approved/manual scanner decision.
    assert 'Read-VerifiedSourceOrderExclusions' in runner
    assert 'Read-VerifiedSourceManualOverrides' in runner
    assert '$verifiedByOrder.ContainsKey($orderNumber)' in runner
    assert '$manualByKey.ContainsKey($orderItemKey)' in runner
    assert 'sourceOrder = [int64]$row.OrderNumber' in runner
    assert 'sourceItem = [int]$row.ItemNumber' in runner
    assert 'v0.324-approved-order-exclusions-plus-manual-overrides-1' in runner

    # Visible manual Order/Item edits retain hidden original source identity in
    # Y/Z. The parser uses that lineage for source_id, preventing the edited row
    # from being treated as a second source row on the next round-trip.
    assert '"sourceOrder": as_int(source.get("sourceOrder") or source.get("order"))' in builder
    assert 'inline_cell("Y6", "Source Order", 2)' in builder
    assert 'inline_cell("Z6", "Source Item", 2)' in builder
    assert 'hidden="1"' in builder
    assert 'WORKBOOK_FORMAT_VERSION = "v324-ooxml-2"' in builder
    assert 'workbookFormatVersion = "v324-ooxml-2"' in runner
    assert 'source_order_no = parse_int_text(row.get("Y"))' in store
    assert 'source_item_no = parse_int_text(row.get("Z"))' in store
    assert 'f"{path.stem}:{row_number}:{source_order_no}:{source_item_no}"' in store

    # Drift and end-to-end verification use the same persistent-decision path
    # as the actual importer, avoiding false IT/CPU expectations.
    assert 'prepare_import_payload' in importer
    assert 'prepare_import_payload' in verifier
