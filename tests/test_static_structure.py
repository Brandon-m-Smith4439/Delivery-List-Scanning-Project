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
        if not path_text or "://" in path_text or path_text.startswith("#"):
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
    assert scripts == ["static/js/app.js?v=20260729-v161"]
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
    assert "static/css/scan.css?v=20260729-v162" in index
    assert "static/js/app.js?v=20260729-v161" in index


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
        "styles": "20260729-v158",
        "home": "20260729-v159",
        "scan": "20260729-v161",
        "racks": "20260729-v161",
        "admin": "20260729-v160",
    }
    for name, cache_key in expected_asset_keys.items():
        assert f"static/css/{name}.css?v={cache_key}" in index
    assert "static/js/app.js?v=20260729-v161" in index


def test_admin_control_center_modal_structure() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'static/css/admin.css?v=20260729-v162' in index
    for element_id in (
        "adminModalEyebrow",
        "adminModalDescription",
        "adminModalStatusText",
        "adminModalContextLabel",
    ):
        assert f'id="{element_id}"' in index
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "ADMIN_MODAL_PROFILES" in app
    assert "applyAdminModalProfile(kind, options)" in app
    for kind in (
        "deliveryLists", "deliveryActions", "manualEdit", "users", "roles",
        "sessions", "stations", "customerRoutes", "customerEmails", "lookups",
        "rejectSettings", "bayScannerRules", "bayAutoAssigner", "racks",
        "rackForm", "rackSetForm", "recentScans",
    ):
        assert f"{kind}: {{" in app
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    assert "v160 Administration Control Center modal system" in css
    assert ".admin-modal-context-strip" in css


def test_v161_scan_timestamp_rack_status_and_rack_control_centers() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")

    assert "static/css/scan.css?v=20260729-v162" in index
    assert "static/css/racks.css?v=20260729-v162" in index
    assert "static/js/app.js?v=20260729-v161" in index
    for element_id in (
        "operationsModalDescription",
        "operationsModalStatusText",
        "operationsModalContextLabel",
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

    assert "static/css/scan.css?v=20260729-v162" in index
    assert "static/css/racks.css?v=20260729-v162" in index
    assert "static/css/admin.css?v=20260729-v162" in index
    assert "static/js/app.js?v=20260729-v161" in index

    assert ".last-scan-pill-v157 > :is(span, b, em)" in scan
    assert "font-size: 11.5px" in scan
    assert "width: 8%;\n  min-width: 0;" in scan
    assert "grid-template-rows: minmax(118px, auto) 54px minmax(0, 1fr) !important" in admin
    assert "#adminModal > .admin-control-center-header" in admin
    assert "grid-row: 3" in admin
    assert "width: 42px !important" in admin
    assert "grid-template-rows: minmax(126px, auto) 50px minmax(0, 1fr) !important" in racks
    assert "#operationsModal.is-control-center > .operations-modal-heading" in racks
    assert "#operationsModal.is-control-center #operationsModalBody" in racks
    assert "color: #fff !important" in racks


def test_v163_modal_hidden_state_and_close_repair() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    assert "static/css/racks.css?v=20260729-v163" in index
    assert "static/css/admin.css?v=20260729-v163" in index
    assert "static/js/app.js?v=20260729-v163" in index
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
    test_scan_time_pill_qty_headers_and_table_are_width_safe()
    test_v158_core_page_polish_and_scan_geometry()
    test_v154_admin_reject_management_and_scan_ribbon()
    print("Static structure checks passed.")
