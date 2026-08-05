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
    assert scripts == ["static/js/app.js?v=20260805-v0.228"]
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
    assert "static/js/app.js?v=20260805-v0.228" in index


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
    assert "static/js/app.js?v=20260805-v0.228" in index


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
    assert "static/js/app.js?v=20260805-v0.228" in index
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
    assert "static/js/app.js?v=20260805-v0.228" in index

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
    assert "static/js/app.js?v=20260805-v0.228" in index
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
    assert "static/js/app.js?v=20260805-v0.228" in index
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
    assert "static/js/app.js?v=20260805-v0.228" in html


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
    assert 'static/js/app.js?v=20260805-v0.228' in html


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

    assert 'APPLICATION_VERSION = "228"' in contract
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
    assert 'static/js/app.js?v=20260805-v0.228' in index
    assert 'aria-label="Application version 0.228"' in index
    assert '<strong>0.228</strong>' in index

    assert 'v0.193 guarded cross-delivery-date scanning' in scan_css
    assert '.cross-date-scan-dialog' in scan_css
    assert '.cross-date-switch-notice' in scan_css
    assert 'v0.193 cross-delivery-date scan settings' in admin_css
    assert '.cross-date-settings-shell' in admin_css

    assert 'Current maintained release: **v0.228**' in readme
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

    assert 'APPLICATION_VERSION = "228"' in contract
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
    assert 'static/js/app.js?v=20260805-v0.228' in index
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.194 - Exact Manual Scans and Result Feedback Repair' in changelog


def test_v195_print_export_filter_workspace_and_exact_preview() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "228"' in contract
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

    assert 'APPLICATION_VERSION = "228"' in contract
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
    assert 'static/js/app.js?v=20260805-v0.228' in index
    assert 'aria-label="Application version 0.228"' in index
    assert '<strong>0.228</strong>' in index
    assert 'Current maintained release: **v0.228**' in readme
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

    assert 'APPLICATION_VERSION = "228"' in contract
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

    assert 'static/css/styles.css?v=20260805-v0.228' in index
    assert 'static/js/app.js?v=20260805-v0.228' in index
    assert 'aria-label="Application version 0.228"' in index
    assert '<strong>0.228</strong>' in index
    assert 'Current maintained release: **v0.228**' in readme
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

    assert 'APPLICATION_VERSION = "228"' in contract
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

    assert 'static/css/styles.css?v=20260805-v0.228' in index
    assert 'static/js/app.js?v=20260805-v0.228' in index
    assert 'aria-label="Application version 0.228"' in index
    assert '<strong>0.228</strong>' in index
    assert 'Current maintained release: **v0.228**' in readme
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
    assert "APPLICATION_VERSION = \"212\"" in contract
    assert "static/css/styles.css?v=20260805-v0.228" in html
    assert "static/js/app.js?v=20260805-v0.228" in html


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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'Current maintained release: **v0.228**' in readme


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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'Current maintained release: **v0.228**' in readme


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

    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog



def test_v204_print_preview_geometry_and_visual_polish() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'function localPrintPackageStylesheetUrl()' in app
    assert 'static/css/styles.css?v=20260805-v0.228' in app
    assert '@page{size:${pageSize};margin:.4in}' in app
    assert 'width: 8.5in !important;' in css
    assert 'height: 11in;' in css
    assert 'width: 11in !important;' in css
    assert 'height: 8.5in;' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary' in css
    assert 'inset: .49in;' in css
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'function localPrintPackageStylesheetUrl()' in app
    assert 'static/css/styles.css?v=20260805-v0.228' in app
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260805-v0.228' in sheet_markup
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260805-v0.228' in sheet_markup
    assert 'function localPrintPackageStylesheetUrl()' in app
    assert '.delivery-print-sheet-v203.rush .sheet-header {' in css
    assert '.delivery-print-sheet-v203.remake .sheet-header {' in css
    assert '.delivery-print-sheet-v203 .sheet-totals {' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary {' in css
    assert 'border-bottom: 2px solid #000;' in css
    assert 'border-top: 2px solid #000;' in css
    assert 'border-bottom: 0;' in css[css.index('.delivery-print-sheet-v203 .sheet-header {'):css.index('.delivery-print-sheet-v203 .sheet-brand-title {')]
    assert 'display: block;' in css[css.index('.delivery-print-sheet-v203 .sheet-totals {'):css.index('.delivery-print-sheet-v203 .sheet-footer {')]
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.217 - Full Weekday Dates and Route-First Delivery Titles' in changelog


def test_v218_reliable_print_logo_and_tightened_header():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    logo = ROOT / "static/images/barefoot-company-builders-firstsource-print-logo.png"

    markup = app[app.index('function printSheetPageMarkup('):app.index('/** Render every actual print sheet', app.index('function printSheetPageMarkup('))]
    print_styles = app[app.index('function localPrintPackageStyles('):app.index('/** Build and synchronously open', app.index('function localPrintPackageStyles('))]

    assert logo.is_file() and logo.stat().st_size > 1000
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260805-v0.228' in markup
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
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.218 - Reliable Print Logo and Tightened Branded Header' in changelog


def test_v219_shared_preview_print_styles_and_portrait_zoom():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'printPreviewZoom: 0.9' in app
    assert '<strong id="printPreviewZoomLabel">90%</strong>' in html
    assert 'state.printPreviewZoom = 0.9;' in app
    assert 'function localPrintPackageStylesheetUrl()' in app
    assert 'static/css/styles.css?v=20260805-v0.228' in app
    assert '<link rel="stylesheet" href="${escapeHtml(stylesheetUrl)}">' in app
    assert 'document.fonts && document.fonts.ready' in app
    assert 'await Promise.all(imageLoads);' in app
    assert '.delivery-print-sheet-v203 .copy-box > span {' in css
    assert 'margin-top: 24px;' in css
    assert 'white-space: nowrap;' in css[css.rindex('/* v0.219 shared preview/print header alignment'):]
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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
    assert 'content: "\\2713";' in css

    assert 'Grouped by Mirror, Tempered, and Annealed for faster selection' in html
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'Current maintained release: **v0.228**' in readme
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
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.221 - Idle Route and Print Row State Recovery' in changelog

def test_v0222_enlarged_branded_delivery_sheet_headers():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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
    assert "static/css/styles.css?v=20260805-v0.228" in html
    assert "static/js/app.js?v=20260805-v0.228" in html
    assert 'aria-label="Application version 0.228"' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert "Current maintained release: **v0.228**" in readme
    assert "## v0.222 - Enlarged Branded Delivery-Sheet Headers" in changelog




def test_v0223_fuller_page_capacity_and_centered_compact_columns():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert '? (pages.length ? 28 : 27)' in app
    assert ': (pages.length ? 28 : 26)' in app
    assert 'v0.223 table-adjacent signoff and fuller verified page capacity' in css
    assert '.delivery-print-sheet-v203 .qty-col { width: 5.8%; }' in css
    assert '.delivery-print-sheet-v203 .dimensions-col { width: 20.2%; }' in css
    assert '.delivery-print-sheet-v203.is-landscape .qty-col { width: 5.8%; }' in css
    assert '.delivery-print-sheet-v203.is-landscape .dimensions-col { width: 22.2%; }' in css
    assert '.delivery-print-sheet-v203 :is(th, td):nth-child(2)' in css
    assert '.delivery-print-sheet-v203 :is(th, td):nth-child(4)' in css
    assert 'text-align: center;' in css[css.rindex('/* v0.223 table-adjacent signoff'): ]
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.223 - Table-Adjacent Signoff and Fuller Delivery Pages' in changelog


def test_v0224_unavailable_filters_and_aligned_borderless_signoff():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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
    assert 'v0.224 unavailable filter states and aligned print signoff' in css
    assert '.print-filter-chip-v197.is-unavailable' in css
    assert 'font-size: 11.5px;' in css
    assert '.delivery-print-sheet-v203 .sheet-header-signoff .copy-box' in css
    signoff_css = css[css.rindex('/* v0.224 unavailable filter states'):]
    assert 'border: 0;' in signoff_css
    assert 'font-size: 16px;' in signoff_css
    assert 'font-size: 14px;' in signoff_css
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.224 - Unavailable Filter States and Aligned Print Signoff' in changelog



def test_v0225_grouped_date_history_and_landscape_density():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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
    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.226 - Automatic All Selections and Newest-First Delivery Dates' in changelog


def test_v0227_health_state_attention_and_preset_control_center():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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
    assert 'printPresetDescriptionInput' in preset_html
    assert 'printPresetDefaultToggle' in preset_html
    assert 'printPresetLiveSummary' in preset_html
    assert 'printPresetOutputSettings' in preset_html
    assert 'printPresetSaveOnlyBtn' in preset_html
    assert 'Visibility' not in preset_html
    assert 'id="printPresetPreview"' not in preset_html
    assert 'Step 1' not in preset_html
    assert 'Step 2' not in preset_html

    assert 'function renderPrintPresetLiveSummary()' in app
    assert 'async function confirmPrintPresetSave({ apply = true } = {})' in app
    assert 'printPresetSaveOnlyBtn?.addEventListener' in app
    assert 'const setAsDefault = Boolean(els.printPresetDefaultToggle?.checked);' in app
    assert 'PRINT_DEFAULT_PRESET_STORAGE_KEY' in app
    assert 'function defaultPrintPresetName()' in app
    assert 'if (setAsDefault) setDefaultPrintPresetName(cleanName);' in app
    assert 'const initialPreset = defaultPrintPresetName();' in app

    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.227 - Health-State Attention Filters and Preset Control Center' in changelog




def test_v0228_create_preset_viewport_positioning_repair():
    root = Path(__file__).resolve().parents[1]
    app = (root / "static/js/app.js").read_text(encoding="utf-8")
    css = (root / "static/css/styles.css").read_text(encoding="utf-8")
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

    assert 'static/css/styles.css?v=20260805-v0.228' in html
    assert 'static/js/app.js?v=20260805-v0.228' in html
    assert 'aria-label="Application version 0.228"' in html
    assert '<strong>0.228</strong>' in html
    assert 'APPLICATION_VERSION = "228"' in contract
    assert 'Current maintained release: **v0.228**' in readme
    assert '## v0.228 - Create Preset Viewport Positioning Repair' in changelog
