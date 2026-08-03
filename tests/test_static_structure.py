# File: tests/test_static_structure.py

from __future__ import annotations

import re
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
        "rejects.css",
        "home.css",
        "scan.css",
        "racks.css",
        "bays.css",
        "admin.css",
        "print.css",
        "shell.css",
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
    assert scripts == ["static/js/app.js?v=20260803-v0.205"]
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
    assert "static/css/scan.css?v=20260803-v0.196" in index
    assert "static/js/app.js?v=20260803-v0.205" in index


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
        "styles": "20260803-v0.195",
        "home": "20260729-v0.181",
        "scan": "20260803-v0.196",
        "racks": "20260729-v0.180",
        "admin": "20260731-v0.193",
    }
    for name, cache_key in expected_asset_keys.items():
        assert f"static/css/{name}.css?v={cache_key}" in index
    assert "static/js/app.js?v=20260803-v0.205" in index


def test_admin_control_center_modal_structure() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'static/css/admin.css?v=20260731-v0.193' in index
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

    assert "static/css/scan.css?v=20260803-v0.196" in index
    assert "static/css/racks.css?v=20260729-v0.180" in index
    assert "static/js/app.js?v=20260803-v0.205" in index
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

    assert "static/css/scan.css?v=20260803-v0.196" in index
    assert "static/css/racks.css?v=20260729-v0.180" in index
    assert "static/css/admin.css?v=20260731-v0.193" in index
    assert "static/js/app.js?v=20260803-v0.205" in index

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

    assert "static/css/racks.css?v=20260729-v0.180" in index
    assert "static/css/admin.css?v=20260731-v0.193" in index
    assert "static/js/app.js?v=20260803-v0.205" in index
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

    assert "static/css/admin.css?v=20260731-v0.193" in index
    assert "static/css/racks.css?v=20260729-v0.180" in index
    assert "static/js/app.js?v=20260803-v0.205" in index
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
    assert "static/js/app.js?v=20260803-v0.205" in html


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
    assert 'static/css/admin.css?v=20260731-v0.193' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html


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

    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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
    assert 'static/css/scan.css?v=20260803-v0.196' in index
    assert 'static/css/admin.css?v=20260731-v0.193' in index
    assert 'static/js/app.js?v=20260803-v0.205' in index
    assert 'aria-label="Application version 0.205"' in index
    assert '<strong>0.205</strong>' in index

    assert 'v0.193 guarded cross-delivery-date scanning' in scan_css
    assert '.cross-date-scan-dialog' in scan_css
    assert '.cross-date-switch-notice' in scan_css
    assert 'v0.193 cross-delivery-date scan settings' in admin_css
    assert '.cross-date-settings-shell' in admin_css

    assert 'Current maintained release: **v0.205**' in readme
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

    assert 'APPLICATION_VERSION = "205"' in contract
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

    assert 'static/css/scan.css?v=20260803-v0.196' in index
    assert 'static/js/app.js?v=20260803-v0.205' in index
    assert 'Current maintained release: **v0.205**' in readme
    assert '## v0.194 - Exact Manual Scans and Result Feedback Repair' in changelog


def test_v195_print_export_filter_workspace_and_exact_preview() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'def summarize_print_package' in server
    assert 'parsed.path == "/api/print/package-preview"' in server
    assert 'STORE.get_print_package(' in server
    assert 'exact_filter_values("glassTypesExact")' in store
    assert 'glass_value in exact_glass_types' in store
    assert "function printSelectionFilters(" in app
    assert 'fetchJson("/api/print/package-session", {' in app
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

    assert 'APPLICATION_VERSION = "205"' in contract
    scan_heading = index[index.index('<div class="scan-heading">'):index.index('<main class="workspace">')]
    assert 'deliveryDateSelect' not in scan_heading
    assert 'deliveryStageSelect' not in scan_heading
    assert 'scan-heading-selectors-v195' not in scan_heading

    panel_start = index.index('<section class="progress-band scanner-summary-header"')
    panel_end = index.index('<section class="scan-rack-panel"', panel_start)
    panel = index[panel_start:panel_end]
    assert 'class="scanner-panel-context-row-v196"' in panel
    assert panel.index('id="deliveryStageSelect"') < panel.index('id="stationProfileDisplay"')
    assert panel.index('id="stationProfileDisplay"') < panel.index('id="deliveryDateSelect"')
    assert 'id="stageHeading"' not in panel
    assert '<span>Assigned station</span>' in panel
    assert 'id="stationSelect" hidden' in panel

    assert 'stageHeading: document.getElementById("stageHeading")' not in app
    assert '`${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}`' not in app
    assert '${escapeHtml(list.stage)}</option>`' in app
    assert 'return String(item.stage || item.label || item.scanner' in app

    assert 'v0.196 scanner-panel context selectors' in scan
    assert '.scanner-panel-context-row-v196' in scan
    assert '.scanner-panel-station-v196' in scan
    assert 'background: rgba(255, 255, 255, 0.07) !important' in scan

    assert 'static/css/scan.css?v=20260803-v0.196' in index
    assert 'static/js/app.js?v=20260803-v0.205' in index
    assert 'aria-label="Application version 0.205"' in index
    assert '<strong>0.205</strong>' in index
    assert 'Current maintained release: **v0.205**' in readme
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

    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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

    assert 'static/css/styles.css?v=20260803-v0.205' in index
    assert 'static/js/app.js?v=20260803-v0.205' in index
    assert 'aria-label="Application version 0.205"' in index
    assert '<strong>0.205</strong>' in index
    assert 'Current maintained release: **v0.205**' in readme
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

    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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

    assert 'static/css/styles.css?v=20260803-v0.205' in index
    assert 'static/js/app.js?v=20260803-v0.205' in index
    assert 'aria-label="Application version 0.205"' in index
    assert '<strong>0.205</strong>' in index
    assert 'Current maintained release: **v0.205**' in readme
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
    assert "APPLICATION_VERSION = \"205\"" in contract
    assert "static/css/styles.css?v=20260803-v0.205" in html
    assert "static/js/app.js?v=20260803-v0.205" in html


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
    assert '/api/export/package.csv?' in app

    assert 'parsed.path == "/api/export/package.csv"' in server
    assert 'def export_package_csv(' in store
    assert '.print-clear-filters-v200' in css
    assert '.print-output-format-v200 .custom-select-trigger' in css
    assert '.print-preset-builder-v200' in css
    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260803-v0.205' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html
    assert 'Current maintained release: **v0.205**' in readme


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
    assert '<option value="__custom__">Custom date range…</option>' in html
    assert 'id="printQuickDate"' not in html
    assert 'type="hidden"' in html[html.index('id="printDateFrom"') - 40:html.index('id="printDateFrom"') + 80]
    assert "function syncPrintAllGlassChoice(changed)" in app
    assert "if (allInput.checked) detailInputs.forEach((input) => { input.checked = false; });" in app
    assert 'checked: !selectAllCurrent && previousGlass.has(label)' in app
    assert 'if (!allGlass && !selectedGlass.size) return false;' in app
    assert 'function renderPrintDateCalendar()' in app
    assert 'is-today' in app
    assert 'function applyPrintCalendarSelection()' in app
    assert '.print-date-calendar-v201' in css
    assert '.print-header-date-control-v203' in css
    assert '.print-calendar-day-v201.is-today' in css
    assert 'grid-column: auto;' in css[css.index('.print-filter-chip-v197.is-status-all'):css.index('.print-options-footer-v200')]
    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260803-v0.205' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html
    assert 'Current maintained release: **v0.205**' in readme


def test_v202_exact_print_sessions_item_selection_output_presets_and_scroll_preview() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    header_start = html.index('class="print-pane-heading-v197 print-pane-heading-v203"')
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
    assert 'fetchJson("/api/print/package-session", {' in app
    assert '/api/export/package.xlsx?token=' in app
    assert '/api/export/package.csv?token=' in app

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

    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260803-v0.205' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html
    assert 'Current maintained release: **v0.205**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog


def test_v203_print_header_date_layout_direct_print_and_exact_preview() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    header_start = html.index('class="print-pane-heading-v197 print-pane-heading-v203"')
    header_end = html.index('<div class="print-filter-scroll-v197">', header_start)
    header = html[header_start:header_end]
    assert 'id="printDateQuickSelect"' in header
    assert '<option value="__custom__">Custom date range…</option>' in header
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
    assert 'function paginatePrintSheetRows(rows)' in app
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
    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260803-v0.205' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html
    assert 'Current maintained release: **v0.205**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog



def test_v204_print_preview_geometry_and_visual_polish() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'static/css/styles.css?v=20260803-v0.205' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html
    assert 'aria-label="Application version 0.205"' in html
    assert '<strong>0.205</strong>' in html
    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'Current maintained release: **v0.205**' in readme
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
    assert 'Custom date range…' in html
    assert 'printCalendarMonthButtons' in app
    assert 'resetPrintCalendarRange' in app
    assert 'if (els.printCalendarApply) els.printCalendarApply.disabled = !(start && end)' in app
    assert 'loadKnownPrintGlassTypes' in app
    assert 'deliveryScannerActivePrintPresetV205' in app
    assert 'printPresetUserToken' in app
    assert 'resetPrintFilters({ clearActivePreset: false })' in app
    assert 'applyPrintPreset(activePreset, { persist: false })' in app
    assert 'v0.205 consistent print controls, range calendar, and user preset state' in css
    assert 'APPLICATION_VERSION = "205"' in contract
    assert 'static/css/styles.css?v=20260803-v0.205' in html
    assert 'static/js/app.js?v=20260803-v0.205' in html
    assert 'Current maintained release: **v0.205**' in readme
    assert '## v0.205 - Consistent Header Controls, Range Calendar, and User Presets' in changelog

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
