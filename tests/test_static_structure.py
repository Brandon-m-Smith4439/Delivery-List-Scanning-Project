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
        "shared-ui.css",
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
    assert scripts == ["static/js/app.js?v=20260811-v0.273"]
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
    assert "static/css/scan.css?v=20260811-v0.273" in index
    assert "static/js/app.js?v=20260811-v0.273" in index


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
        "styles": "20260811-v0.273",
        "home": "20260811-v0.273",
        "scan": "20260811-v0.273",
        "racks": "20260811-v0.273",
        "admin": "20260811-v0.273",
    }
    for name, cache_key in expected_asset_keys.items():
        assert f"static/css/{name}.css?v={cache_key}" in index
    assert "static/js/app.js?v=20260811-v0.273" in index


def test_admin_control_center_modal_structure() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'static/css/admin.css?v=20260811-v0.273' in index
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

    assert "static/css/scan.css?v=20260811-v0.273" in index
    assert "static/css/racks.css?v=20260811-v0.273" in index
    assert "static/js/app.js?v=20260811-v0.273" in index
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

    assert "static/css/scan.css?v=20260811-v0.273" in index
    assert "static/css/racks.css?v=20260811-v0.273" in index
    assert "static/css/admin.css?v=20260811-v0.273" in index
    assert "static/js/app.js?v=20260811-v0.273" in index

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

    assert "static/css/racks.css?v=20260811-v0.273" in index
    assert "static/css/admin.css?v=20260811-v0.273" in index
    assert "static/js/app.js?v=20260811-v0.273" in index
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

    assert "static/css/admin.css?v=20260811-v0.273" in index
    assert "static/css/racks.css?v=20260811-v0.273" in index
    assert "static/js/app.js?v=20260811-v0.273" in index
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
    assert "static/js/app.js?v=20260811-v0.273" in html


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
    assert 'static/css/admin.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html


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

    assert 'APPLICATION_VERSION = "273"' in contract
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
    assert 'static/css/scan.css?v=20260811-v0.273' in index
    assert 'static/css/admin.css?v=20260811-v0.273' in index
    assert 'static/js/app.js?v=20260811-v0.273' in index
    assert 'aria-label="Application version 0.273"' in index
    assert '<strong>0.273</strong>' in index

    assert 'v0.193 guarded cross-delivery-date scanning' in scan_css
    assert '.cross-date-scan-dialog' in scan_css
    assert '.cross-date-switch-notice' in scan_css
    assert 'v0.193 cross-delivery-date scan settings' in admin_css
    assert '.cross-date-settings-shell' in admin_css

    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
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

    assert 'static/css/scan.css?v=20260811-v0.273' in index
    assert 'static/js/app.js?v=20260811-v0.273' in index
    assert 'Current maintained release: **v0.273**' in readme
    assert '## v0.194 - Exact Manual Scans and Result Feedback Repair' in changelog


def test_v195_print_export_filter_workspace_and_exact_preview() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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

    assert 'APPLICATION_VERSION = "273"' in contract
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

    assert 'static/css/scan.css?v=20260811-v0.273' in index
    assert 'static/js/app.js?v=20260811-v0.273' in index
    assert 'aria-label="Application version 0.273"' in index
    assert '<strong>0.273</strong>' in index
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
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

    assert 'static/css/print.css?v=20260811-v0.273' in index
    assert 'static/js/app.js?v=20260811-v0.273' in index
    assert 'aria-label="Application version 0.273"' in index
    assert '<strong>0.273</strong>' in index
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
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

    assert 'static/css/print.css?v=20260811-v0.273' in index
    assert 'static/js/app.js?v=20260811-v0.273' in index
    assert 'aria-label="Application version 0.273"' in index
    assert '<strong>0.273</strong>' in index
    assert 'Current maintained release: **v0.273**' in readme
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
    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html


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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme


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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme


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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog



def test_v204_print_preview_geometry_and_visual_polish() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/styles.css?v=20260811-v0.273' in app
    assert '@page{size:${pageSize};margin:.4in}' in app
    assert 'width: 8.5in !important;' in css
    assert 'height: 11in;' in css
    assert 'width: 11in !important;' in css
    assert 'height: 8.5in;' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary' in css
    assert 'inset: .49in;' in css
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/styles.css?v=20260811-v0.273' in app
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260811-v0.273' in sheet_markup
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260811-v0.273' in sheet_markup
    assert 'function localPrintPackageStylesheetUrls()' in app
    assert '.delivery-print-sheet-v203.rush .sheet-header {' in css
    assert '.delivery-print-sheet-v203.remake .sheet-header {' in css
    assert '.delivery-print-sheet-v203 .sheet-totals {' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary {' in css
    assert 'border-bottom: 2px solid #000;' in css
    assert 'border-top: 2px solid #000;' in css
    assert 'border-bottom: 0;' in css[css.index('.delivery-print-sheet-v203 .sheet-header {'):css.index('.delivery-print-sheet-v203 .sheet-brand-title {')]
    assert 'display: block;' in css[css.index('.delivery-print-sheet-v203 .sheet-totals {'):css.index('.delivery-print-sheet-v203 .sheet-footer {')]
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260811-v0.273' in markup
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/styles.css?v=20260811-v0.273' in app
    assert 'static/css/print.css?v=20260811-v0.273' in app
    assert '<link rel="stylesheet" href="${escapeHtml(stylesheetUrl)}">' in app
    assert 'document.fonts && document.fonts.ready' in app
    assert 'await Promise.all(imageLoads);' in app
    assert '.delivery-print-sheet-v203 .copy-box > span {' in css
    assert 'margin-top: 24px;' in css
    assert 'white-space: nowrap;' in css[css.rindex('/* v0.219 shared preview/print header alignment'):]
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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
    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/styles.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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

    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert "<strong>0.273</strong>" in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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

    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert "<strong>0.273</strong>" in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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

    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert "<strong>0.273</strong>" in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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
    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert "<strong>0.273</strong>" in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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

    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert "<strong>0.273</strong>" in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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

    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html
    assert 'aria-label="Application version 0.273"' in html
    assert "<strong>0.273</strong>" in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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
    assert 'static/js/app.js?v=20260811-v0.273' in html


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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
    assert "static/css/print.css?v=20260811-v0.273" in html
    assert "static/js/app.js?v=20260811-v0.273" in html



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
    assert 'PRINT_XLSX_LOGO_PATH = "static/images/barefoot-company-builders-firstsource-print-logo.png?v=20260811-v0.273"' in app
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert "Current maintained release: **v0.273**" in readme
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

    assert 'static/css/shared-ui.css?v=20260811-v0.273' in html
    assert html.index('static/css/shared-ui.css?v=20260811-v0.273') > html.index('static/css/shell.css?v=20260731-v0.192')
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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'static/css/print.css?v=20260811-v0.273' in html
    assert 'static/css/racks.css?v=20260811-v0.273' in html
    assert 'static/css/admin.css?v=20260811-v0.273' in html
    assert 'static/css/bays.css?v=20260811-v0.273' in html
    assert 'static/css/shared-ui.css?v=20260811-v0.273' in html


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
    assert 'APPLICATION_VERSION = "273"' in contract


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
    assert 'APPLICATION_VERSION = "273"' in contract


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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html


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
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html


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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'static/css/bays.css?v=20260811-v0.273' in html
    assert 'static/css/shared-ui.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/statistics.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/statistics.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'static/css/admin.css?v=20260811-v0.273' in html
    assert 'Current maintained release: **v0.273**' in readme
    assert '## v0.261 - Admin-Managed Glass Material Costs' in changelog

    assert '"glass_cost": {}' in store
    assert '"glassCosts": sorted(' in store
    assert 'lookup_type not in {"product", "route", "process", "glass_cost"}' in store
    assert "WHERE is_active = 1 AND type = 'glass_cost'" in store
    assert 'glass_cost_profile(raw_product, effective_glass_costs)' in store
    assert 'for label, rate in effective_glass_costs.items()' in store
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract

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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/statistics.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
    assert '## v0.262 - Combined Breakage Accountability and Custom Statistics Range' in changelog


def test_v0263_restores_statistics_typography_and_reorganizes_breakage_tables():
    """v0.263 restores readable text and groups breakage accountability into clear blocks."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/statistics.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/statistics.css?v=20260811-v0.273' in html
    assert 'static/css/scan.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/scan.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/scan.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'AND n.created_at = ?' in operations
    assert 'manual_clause = " AND n.change_token = ?"' in operations
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/scan.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/scan.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/scan.css?v=20260811-v0.273' in html
    assert 'static/css/racks.css?v=20260811-v0.273' in html
    assert 'static/css/shared-ui.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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

    assert 'static/css/racks.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'Current maintained release: **v0.273**' in readme
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
    assert 'APPLICATION_VERSION = "273"' in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION = 5" in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")



def test_v0272_rack_manager_collapses_icons_fit_and_packing_history_is_weekly():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'static/css/racks.css?v=20260811-v0.273' in html
    assert 'static/css/shared-ui.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
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

    assert '.action-confirm-dialog' in shared_css
    assert '--gui-close-position: absolute' in shared_css
    assert '--gui-close-right: 14px' in shared_css



def test_v0273_packing_history_preview_actions_aframe_cart_and_bay_edit_shortcut():
    """v0.273 keeps history compact/readable and restores a tiny direct Bay group editor shortcut."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "273"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 5' in contract
    assert 'static/css/racks.css?v=20260811-v0.273' in html
    assert 'static/css/bays.css?v=20260811-v0.273' in html
    assert 'static/js/app.js?v=20260811-v0.273' in html
    assert 'aria-label="Application version 0.273"' in html
    assert '<strong>0.273</strong>' in html
    assert 'Current maintained release: **v0.273**' in readme
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
