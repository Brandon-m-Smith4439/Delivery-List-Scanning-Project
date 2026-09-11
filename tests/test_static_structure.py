# File: tests/test_static_structure.py

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_previous_brand_logo_and_main_bay_transit_contract() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    logo = ROOT / "assets" / "barefoot-builders-firstsource-logo.webp"

    assert html.count("assets/barefoot-builders-firstsource-logo.webp") == 3
    assert "static/css/bays.css?v=20260908-v0.513" in html
    assert logo.exists()
    assert logo.stat().st_size < 100_000
    assert "function startBayTransitAnimationV467" in app
    assert "requestAnimationFrame" in app
    assert ".transit-animation-truck.has-transit-glass-v467 .transit-moving-truck" in bays
    assert ".transit-animation-truck.has-transit-glass-v467 .transit-rack-transfer" in bays


def test_main_scan_date_wide_layout_and_refresh_contract() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    mobile = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")

    table_head = re.search(r'<table class="delivery-table">\s*<thead>(.*?)</thead>', html, re.S)
    assert table_head is not None
    assert re.findall(r'data-scan-column="([^"]+)"', table_head.group(1)) == [
        "glass", "order", "item", "qty", "dimensions", "route", "location", "progress",
    ]
    assert 'id="deliveryStageSelect"' not in html
    assert 'static/css/scan.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'loadMarkerBatch' in app
    assert '/api/operations/line-flags/batch' in app
    assert 'parsed.path == "/api/operations/line-flags/batch"' in server
    modal_selector = app[app.index("const APP_MODAL_STATE_SELECTOR"):app.index("function modalNodeIsOpen")]
    assert '"#printOptionsPanel"' in modal_selector
    production_modal = app[app.index("function closeProductionExplorerV470"):app.index("function fabricationStatusHtmlV470")]
    assert production_modal.count("updateModalScrollLock();") >= 2
    assert 'const needsDateWidePayloadV485 = restartPendingLoadV512 || !state.meta?.dateWideScanV485' in app
    assert 'scanDateWideCatalogSignatureV486(state.scanDateWideDateV485)' in app
    assert 'activateScanDateV485(activeDateWideDate, false' in app
    assert 'return `<tr class="scan-order-group-v477${priorityClass}" data-order-group-v477="${escapeHtml(order)}"><td colspan="8">' in app
    assert '.delivery-table th:nth-child(8),' in scan
    assert 'parsed.path == "/api/scan/date"' in server
    assert 'def get_delivery_date_scan_bundle' in store
    assert '.full-scans-modal .all-scans-table tbody' in mobile
    assert 'grid-template-columns: minmax(0, 1fr) !important;' in mobile
    assert 'z-index: 2001 !important;' not in mobile
    assert 'z-index: 4300 !important;' not in mobile



def test_v484_aw_reject_persistence_and_direct_sync_contract() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    config = json.loads((ROOT / "automation" / "sql_delivery_export" / "sql-export.config.json").read_text(encoding="utf-8"))
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared_ui = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '"v484_aw_reject_sync"' in migrations
    assert 'CREATE TABLE IF NOT EXISTS aw_reject_events' in migrations
    assert 'CREATE TABLE IF NOT EXISTS aw_reject_source_rows' in migrations
    assert 'PROD_BREAKAGE.ROWID' in migrations
    assert 'def sync_aw_reject_rows' in store
    assert 'def list_aw_rejects' in store
    assert 'aw_rejects_by_item' in store and '"awRejects": aw_rejects' in store
    assert 'function Get-AwRejectSyncPayload' in runner
    assert 'LEFT JOIN SYSADM.KA_REKLA_GRND reason ON reason.NUMMER = pb.BREAKAGE_REASON' in runner
    assert 'LEFT JOIN SYSADM.KA_REKLA_ORT location ON location.NUMMER = pb.BREAKAGE_REGISTRATION' in runner
    assert 'b.BOOK_TYPE = 1' in runner
    assert 'v484-aw-direct-reject-1' in runner
    assert 'store.sync_aw_reject_rows' in importer
    assert 'summary["awRejectSync"] = aw_reject_sync' in importer
    assert config["RejectSync"]["Enabled"] is True
    assert config["RejectSync"]["IncrementalPastDays"] == 30
    assert config["RejectSync"]["FullPastDays"] == 365
    assert 'parsed.path == "/api/aw-rejects"' in server
    assert 'orderDetailInternalAwRejectsV485' in app_js
    assert 'production-aw-rejects-v484' in app_js
    assert 'production-aw-rejects-v484' in shared_ui
    assert 'delivery-list reconciliation will continue' in runner


def test_v486_aw_reject_rollback_refabrication_and_glass_label_probe_contract() -> None:
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")

    assert '"v486_aw_reject_operational_reset"' in migrations
    assert 'rollback_applied_at' in migrations
    assert 'rollback_scan_qty_reduced' in migrations
    assert 'operational_rollback_applied_at' in migrations
    assert 'def _apply_aw_reject_operational_rollback_con' in store
    assert "event_type, message, reason, qty_delta, created_at" in store
    assert "'reject_reset'" in store
    assert 'pendingOperationalRollbacks' in store
    assert 'src.rollback_applied_at' in store
    assert 'postImportReconciliation' in importer
    assert 'def latest_internal_reject_at' in store
    assert 'evidence_after=identity["lastRejectedAt"]' in store
    assert 'evidence_after=item.get("lastRejectedAt")' in store
    assert 'def _evidence_is_after' in production
    assert 'return float(asset.modified_at or 0) > cutoff' in production
    assert 'Predates latest Internal Reject' in production
    assert 'def invalidate_fabrication' in production
    assert 'STORE.latest_internal_reject_at(order, item)' in server
    assert 'Needs Refabrication' in app
    assert 'fabricationStatusKeyV474(order = "", item = "", job = "", evidenceAfter = "", revision = "")' in app

    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED' in probe
    assert 'SELECT TOP (150) *' in probe
    assert 'TRY_CONVERT' not in probe
    assert '02-label-candidate-columns.csv' in probe
    assert '03-ranked-label-candidates.csv' in probe
    assert '04-label-module-references.csv' in probe
    assert '06-sample-index.csv' in probe
    assert '07-core-production-columns.csv' in probe
    assert 'return $rows.ToArray()' in probe
    assert 'return @($rows)' not in probe


def test_v483_bde_probe_verified_reject_contract_and_lookup_discovery() -> None:
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWBdeBreakage.ps1").read_text(encoding="utf-8-sig")

    # Windows PowerShell enumerates DataTable output unless the function emits
    # the table as a single pipeline object. The unary comma keeps .Rows intact.
    assert "return ,$table" in probe
    assert "DeliveryScanner-AWBdeProbe-v483" in probe
    assert "TRY_CONVERT" not in probe
    assert "^AUFNR$" in probe
    assert "[PROD_BREAKAGE]" in probe
    assert "[UV_BOOK_HISTORY_EX]" in probe
    assert "pb.[IS_BREAKAGE] = 1" in probe
    assert "uvx.[MENSAJE] = 'Reject'" in probe
    assert "DATEADD(second, -1, pb.[BREAKAGEDATE])" in probe
    assert "DATEADD(second, 1, pb.[BREAKAGEDATE])" in probe
    assert "CASE WHEN uvx.[PARTE] = pb.[BOM_ID] THEN 0 ELSE 1 END" in probe
    assert "kb.[STATUS_ID] = pb.[BREAKAGE_REASON]" in probe
    assert "DATEADD(second, -10, pb.[BREAKAGEDATE])" in probe
    assert "DATEADD(second, 10, pb.[BREAKAGEDATE])" in probe
    assert "09-book-history-near-prod-breakage.csv" in probe
    assert "10-book-history-code-$StatusCode-near-prod-breakage.csv" in probe
    assert "11-ka-prod-bruch-reason-for-order-item.csv" in probe
    assert "12-uv-book-history-ex-order-item.csv" in probe
    assert "14-verified-reject-evidence.csv" in probe
    assert "15-prod-breakage-code-summary.csv" in probe
    assert "16-breakage-module-references.csv" in probe
    assert "17-breakage-lookup-candidate-columns.csv" in probe
    assert "18-breakage-code-lookup-hits.csv" in probe
    assert "WHERE $candidateCodeSql IN (137, 5)" in probe
    assert "13-verified-breakage-index.csv" in probe
    assert "09-book-history-via-prod-breakage.csv" not in probe


def test_v0476_visual_order_machine_colors_waterjet_alias_and_lookup_modal_contract() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    production = (ROOT / "backend/production_files.py").read_text(encoding="utf-8")
    config = (ROOT / "backend/config.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    shared = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    admin = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'production_root / "Completed  WJ"' in config
    assert 'def _resolve_root_alias' in production
    assert 'Resolved configured path to:' in production
    assert '"machineColors"' in production and '"machineColors"' in store
    assert 'lookup:machine' in app and 'machineLookupManagerHtmlV521' in app
    assert 'data-production-settings-tab-v476="machines"' not in app
    assert 'productionMachineColorV476' in app and 'machineDefinitionsV521' in app
    assert 'productionSketchVisualV476' in app and 'Open Sketch' in app
    assert 'globalSearchProgressMarkupV476' in app and 'progressStageIconKindV476' in app
    assert 'scan-progress-stack-v476' in scan
    assert 'production-order-detail-v476' in shared
    assert 'lookup-editor-backdrop-v476' in admin and '.lookup-editor-modal-shell-v476 > .lookup-editor-surface-v470.is-editor-open-v470' in admin
    assert 'global-result-progress-flow-v476' in styles

def test_v0475_compact_progress_order_details_and_share_diagnostics() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    styles = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    assert "globalSearchProgressTextV475" in app
    assert "scanProgressPairV475" in app and "scan-progress-stack-v475" in scan
    assert "app-primary-button global-result-action-v475" in app
    assert "global-result-actions-v475" in styles
    assert "production-order-overview-v519" in app and "production-order-summary-v476" in shared
    assert "progressStages" in store and '"_progressStages": {}' in store
    assert "Folder not found; parent is reachable" in production


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
        "inventory.css",
        "scan.css",
        "racks.css",
        "bays.css",
        "admin.css",
        "print.css",
        "shell.css",
        "mobile.css",
        "theme.css",
    }
    assert {path.name for path in css_dir.glob("*.css")} == expected
    for path in css_dir.glob("*.css"):
        content = path.read_text(encoding="utf-8")
        assert content.count("{") == content.count("}"), path


def test_v0423_static_assets_cache_and_large_json_is_compact_and_compressed() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")

    assert 'request_path.startswith(("/static/", "/assets/", "/sounds/"))' in server
    assert 'public, max-age=31536000, immutable' in server
    assert 'separators=(",", ":")' in server
    assert 'gzip.compress(body, compresslevel=4, mtime=0)' in server
    assert 'self.send_header("Content-Encoding", "gzip")' in server
    assert 'self.send_header("Vary", "Accept-Encoding")' in server
    assert 'def send_head(self):' in server
    assert '_compressed_asset_cache' in server
    assert 'gzip.compress(source.read_bytes(), compresslevel=6, mtime=0)' in server

def test_v0472_statistics_report_payloads_are_isolated_by_active_range() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")

    # Preserve the v0.472 correctness contract even though the supplied newer
    # branch had temporarily dropped these range-isolation guards.
    assert 'homeReportSummaryRangeKey: ""' in app
    assert 'homeReportSummaryRequestToken: 0' in app
    assert 'function homeReportRangeKeyV472()' in app
    assert 'function activeHomeReportSummaryV472()' in app
    assert 'state.homeReportSummaryRangeKey === homeReportRangeKeyV472()' in app
    assert 'const requestToken = Number(state.homeReportSummaryRequestToken || 0) + 1;' in app
    assert 'homeReportRangeKeyV472() === requestKey' in app
    assert 'state.homeReportSummaryRangeKey = requestKey;' in app
    assert 'activeHomeReportSummaryV472()?.glassQuantityByType' in app
    assert 'activeHomeReportSummaryV472()?.glassSizeFrequencyByType' in app


def test_v0473_recent_production_index_statistics_and_scan_grouping_contract() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    production_files = (ROOT / "backend/production_files.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.476 - Visual Order Review, Machine Colors, and Waterjet Path Resolution' in changelog

    # Production-file discovery stays off the request thread and only indexes the
    # configured recent working window. Denver and Waterjet evidence are exact-item
    # .egl/.nce files rather than generic files elsewhere in the order folder.
    assert 'production-file-index.json' in production_files
    assert 'def refresh_async' in production_files
    assert 'lookbackDays' in production_files
    assert 'asset.extension == ".nce"' in production_files
    assert 'asset.extension == ".egl"' in production_files
    assert 'def _recent_cutoff' in production_files
    assert 'def _probe_root' in production_files
    assert 'Mapped drive not reachable; use a UNC path if needed' in production_files
    assert 'def _known_recent_directories' in production_files
    assert 'os.scandir' in production_files
    assert 'lookbackDays' in store
    assert 'production_files.refresh_async()' in store
    assert 'parsed.path == "/api/admin/production-files"' in server
    assert 'parsed.path == "/api/admin/production-files/refresh"' in server
    assert 'include_production = str(params.get("production", ["1"])[0]).lower() not in {"0", "false", "no"}' in server
    assert 'id="productionLookbackDaysV473"' in app
    assert 'Unavailable · ${availabilityError}' in app
    assert 'scheduleProductionFileSettingsPollV473' in app
    assert '.production-index-status-v472.is-checking' in admin_css

    # Column sorting remains inside each glass-type section. v0.477 adds only a
    # lightweight visual order header; the old collapsible v0.472 rows stay gone.
    assert 'sortScanItems(group.items)' in app
    assert 'renderOrderGroupedRowsV477(groupItems)' in app
    assert 'scanOrderGroupHeaderV477' in app
    assert 'renderScanOrderGroupsV472' not in app
    assert 'data-toggle-scan-order-v472' not in app
    assert '.scan-order-group-row-v472' not in scan_css

    # A report payload is tagged with the exact date range that requested it; an
    # older/slower response cannot populate a newly selected Statistics range.
    assert 'homeReportSummaryRangeKey: ""' in app
    assert 'homeReportSummaryRequestToken: 0' in app
    assert 'function homeReportRangeKeyV472()' in app
    assert 'function activeHomeReportSummaryV472()' in app
    assert 'state.homeReportSummaryRangeKey === homeReportRangeKeyV472()' in app
    assert 'const requestToken = Number(state.homeReportSummaryRequestToken || 0) + 1;' in app
    assert 'homeReportRangeKeyV472() === requestKey' in app
    assert 'state.homeReportSummaryRangeKey = requestKey;' in app
    assert 'activeHomeReportSummaryV472()?.glassQuantityByType' in app
    assert 'activeHomeReportSummaryV472()?.glassSizeFrequencyByType' in app

    assert 'orderProductionFiles' in app
    assert '.production-order-files-v472' in shared_css
    assert 'globalSearchRequestId' in app



def test_version_numbers_are_not_embedded_in_asset_filenames() -> None:
    versioned = []
    for folder in (ROOT / "static" / "css", ROOT / "static" / "js"):
        versioned.extend(path.name for path in folder.iterdir() if re.search(r"-v\d+", path.name))
    assert not versioned


def test_single_javascript_bundle_is_loaded() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script\s+src="([^"]+)"', index)
    assert scripts == ["static/js/app.js?v=20260910-v0.527"]
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
        "production_files.py",
        "sketch_geometry.py",
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
        "time_utils.py",
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
    assert '<td colspan="8">' in app
    assert 'class="internal-reject-detail-tail-v154" colspan="3"' not in app
    assert ".internal-reject-incident-strip-v154" in scan_css
    assert ".reject-edit-form-v154" in rejects_css



def test_admin_control_center_modal_structure() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'static/css/admin.css?v=20260910-v0.527' in index
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



def test_v164_simplified_gui_headers_and_automation_action() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    racks = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")

    assert "static/css/admin.css?v=20260910-v0.527" in index
    assert "static/css/racks.css?v=20260908-v0.510" in index
    assert "static/js/app.js?v=20260910-v0.527" in index
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
    assert "static/js/app.js?v=20260910-v0.527" in html


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
    assert 'static/css/admin.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html



def test_v195_print_export_filter_workspace_and_exact_preview() -> None:
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
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
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.203 - Print Layout Completion and Direct Preview Printing' in changelog




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
    assert 'static/css/styles.css?v=20260910-v0.527' in app
    assert '@page{size:${pageSize};margin:.4in}' in app
    assert 'width: 8.5in !important;' in css
    assert 'height: 11in;' in css
    assert 'width: 11in !important;' in css
    assert 'height: 8.5in;' in css
    assert '.delivery-print-sheet-v203 .sheet-filter-summary' in css
    assert 'inset: .49in;' in css
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.211 - Letter Preview Parity and Printed Filter Summary' in changelog



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
    assert 'barefoot-company-builders-firstsource-print-logo.png?v=20260908-v0.510' in markup
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
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'static/css/print.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'Current maintained release: **v0.527**' in readme
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
    assert 'static/css/styles.css?v=20260910-v0.527' in app
    assert 'static/css/print.css?v=20260910-v0.527' in app
    assert '<link rel="stylesheet" href="${escapeHtml(stylesheetUrl)}">' in app
    assert 'document.fonts && document.fonts.ready' in app
    assert 'await Promise.all(imageLoads);' in app
    assert '.delivery-print-sheet-v203 .copy-box > span {' in css
    assert 'margin-top: 24px;' in css
    assert 'white-space: nowrap;' in css[css.rindex('/* v0.219 shared preview/print header alignment'):]
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'static/css/print.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.219 - Shared Preview and Print Styling' in changelog


def test_v0451_priority_ribbon_multi_term_search_and_transit_transfer() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.451 - Priority Ribbon Fit, Smart Search Composition, and Transit Loading Motion' in changelog

    # Supplemental flag rows must override the shared 54px line-item cell height.
    assert 'v0.451 Priority ribbon row collapse' in scan_css
    assert 'tr.priority-line-ribbon-row-v441 > td {' in scan_css
    assert 'height: 22px !important;' in scan_css
    assert 'min-height: 20px;' in scan_css

    # Global Search normalizes dimension separators, performs AND matching, and
    # resolves flags through the existing priority annotation path.
    assert 'def global_search_terms(query: str) -> list[str]:' in store
    assert 'def global_search_sql_terms(terms: list[str]) -> list[str]:' in store
    assert 'def global_search_result_matches(result: dict[str, Any], terms: list[str]) -> bool:' in store
    assert 'return all(term in corpus for term in terms)' in store
    assert 'annotated_results = self.attach_priority_search_annotations(cleaned_results)' in store
    assert 'if self.global_search_result_matches(result, terms)' in store
    assert 'priority_candidate = \"(LOWER(COALESCE(li.process_state' in store

    # The progress meter still terminates at the truck endpoints. v0.452 keeps
    # the same transfer hooks while simplifying the endpoint artwork.
    assert 'transit-rack-transfer-outbound' in app
    assert 'transit-rack-transfer-inbound' in app
    assert 'v0.451 Transit endpoint alignment + rack loading/unloading' in bays_css
    assert 'width: calc(100% - 60px) !important;' in bays_css
    assert 'animation: bay-transit-shuttle-v447 14s linear infinite !important;' in bays_css


def test_v0453_indian_trail_popup_layout_and_glass_transfer_motion() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.453 - Indian Trail Placement Popup Layout and Bay Map Glass Motion' in changelog

    # Combined glass profiles receive aliases and colors in one lightweight load.
    # A source row can keep its stored color for future uncombine, but while it is
    # combined it cannot overwrite the target profile's configured display color.
    assert '"glassAliases": lookups.get("glassAliases", [])' in server
    assert 'glassAliases: Array.isArray(payload?.glassAliases)' in app
    assert 'const isCombinedSource = Boolean(rawKey && targetKey && rawKey !== targetKey);' in app
    assert 'if (!color || isCombinedSource) return;' in app
    assert 'const effectiveColors = new Map();' in app
    assert 'effectiveColors.get(targetKey)' in app

    # Historical rack surfaces are neutral gray, not their active rack-set color.
    assert 'const rackPrior = rackState?.key === "prior";' in app
    assert 'rackPrior ? "#94A1AD"' in app
    assert '.location-rack-state-stack-v448.is-prior > .location-rack-cell-v349' in scan_css
    assert '--rack-location-color: #94a1ad !important;' in scan_css

    # IT prerequisite reconciliation produces explicit synthetic scan events and
    # the UI labels their timestamp as Scan Override IT instead of ON TIME/LATE.
    assert '"Scan Override IT"' in store
    assert '"scan_override_it"' in store
    assert "AND se.event_type <> 'scan_override_it'" in store
    assert '("airport_staging", "staging")' in store
    assert '("airport_outbound", "outbound")' in store
    assert 'missingPrerequisites' in store
    assert 'const indianTrailOverride = scanStation.toLowerCase() === "scan override it";' in app
    assert 'SCAN OVERRIDE IT:' in app
    assert '.last-scan-pill-v157.is-it-override-v452' in scan_css

    # The placement popup is wider, cleaner, and keeps the big bay hero while
    # moving the correction controls into a readable footer/control-row layout.
    assert 'const infoLabel = spanish ? "Orden escaneada" : "Scanned order";' in app
    assert 'indian-trail-placement-copy-v453' in app
    assert 'indian-trail-placement-meta-pill-v453' in app
    assert 'indian-trail-placement-controls-v453' in app
    assert 'indian-trail-placement-footer-v453' in app
    assert '#indianTrailPlacementShell.indian-trail-placement-shell {' in styles_css
    assert 'indian-trail-placement-meta-pill-v453' in styles_css
    assert 'indian-trail-placement-controls-v453' in styles_css
    assert 'indian-trail-placement-footer-v453' in styles_css

    # Endpoint pause motion is still only light-blue vertical glass, but now it
    # moves in the intended direction at each truck endpoint.
    assert 'transit-rack-transfer-outbound' in app
    assert 'transit-rack-transfer-inbound' in app
    assert '@keyframes bay-transit-glass-load-v453' in bays_css
    assert '@keyframes bay-transit-glass-unload-v453' in bays_css
    assert 'left: 18px;' in bays_css
    assert 'right: 20px;' in bays_css
    assert 'background: linear-gradient(180deg, #dff5ff 0%, #9bd5f2 100%);' in bays_css


def test_v0455_scan_style_ownership_notification_layout_and_unified_chart_calendar() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.455 - Scan Style Ownership Repair and Unified Analytics Calendar Range' in changelog

    # The actual opaque child button, not only the surrounding TD, now yields
    # to the darkened Lookup Manager color band.
    assert 'v0.455 Authoritative glass-group header surface' in scan_css
    assert '> button[data-toggle-glass-group] {' in scan_css
    assert 'background: transparent !important;' in scan_css
    assert 'var(--glass-type-color)' in scan_css
    assert '> button[data-toggle-glass-group] > strong {' in scan_css
    assert 'color: #fff !important;' in scan_css

    # The v0.453 receive markup now ships with an explicit authoritative layout
    # so generic legacy popup rules cannot flatten the metadata/footer structure.
    assert 'v0.455: authoritative Indian Trail receive layout' in styles_css
    assert '#indianTrailPlacementShell.indian-trail-placement-shell {' in styles_css
    assert 'width: min(1040px, calc(100vw - 28px)) !important;' in styles_css
    assert 'indian-trail-placement-meta-v453' in styles_css
    assert 'indian-trail-placement-controls-v453' in styles_css
    assert 'indian-trail-placement-footer-v453' in styles_css
    assert 'grid-template-columns: minmax(300px, 420px) auto !important;' in styles_css

    metric_start = index.index('<select id="statsChartMetricSelect">')
    metric_end = index.index('</select>', metric_start)
    metric_markup = index[metric_start:metric_end]
    assert '<optgroup label="Delivery lists">' not in metric_markup
    assert '<optgroup label="Delivery dates">' not in metric_markup

    # One two-month calendar range now lives in the analytics toolbar and applies
    # to every view; the v0.454 table-only date control/state has been removed.
    assert 'id="statisticsChartRangeButton"' in index
    assert 'id="statisticsChartRangeText"' in index
    assert 'Chart date range' in index
    assert 'id="statisticsTableDateControl"' not in index
    assert 'id="statsTableDateSelect"' not in index
    assert 'function statisticsActiveRangeKeysV455()' in app
    assert 'function syncStatisticsChartRangeControlV455()' in app
    assert 'statisticsTableRangeSnapshot' not in app
    assert 'applyStatisticsTableDateV454' not in app
    assert 'const numericLimit = state.homeChartView === "table" ? 0' in app

    assert 'v0.455 Analytics calendar range + repaired visual ownership' in statistics_css
    assert '.statistics-chart-range-picker-v455 {' in statistics_css
    assert '.statistics-chart-range-button-v455 {' in statistics_css
    assert '.statistics-chart-range-picker-v455 .statistics-date-calendar-v0262 {' in statistics_css

    # Bar view still expands into normal page flow without internal vertical scroll.
    assert '.statistics-chart-canvas-v0258 .statistics-chart-bar-viewport {' in statistics_css
    assert 'max-height: none !important;' in statistics_css
    assert 'overflow: visible !important;' in statistics_css
    assert 'style="width:100%;min-width:0"' in app


def test_v0456_shell_statistics_home_scan_and_inbound_polish() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    shell_css = (ROOT / "static/css/shell.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    home_css = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.456 - Shared Shell Continuity and Statistics Visual Polish' in changelog

    # Footer and Statistics header share the application shell/workspace language.
    assert 'v0.456 Footer/sidebar color continuity' in shell_css
    assert 'linear-gradient(180deg, #062c68 0%, #041f4d 52%, #05265c 100%)' in shell_css
    assert 'v0.456 Statistics visual polish and shared workspace geometry' in statistics_css
    assert 'height: 116px !important;' in statistics_css
    assert '.statistics-command-header-v0258.app-page-header-v357::after {' in statistics_css

    # Priority cards are standalone and the analytics controls are normalized.
    assert 'statistics-priority-grid-standalone-v456' in index
    assert 'statistics-card-v0258 statistics-priority-panel-v0258' not in index
    assert 'height: 42px !important;' in statistics_css
    assert '--pie-1: #1769e0;' in statistics_css

    # Statistics range presentation is numeric while still using the same calendar path.
    assert 'formatNumericDeliveryDate(range.dateFrom)' in app
    assert 'formatNumericDeliveryDate(state.statisticsCustomDateFrom)' in app
    assert 'formatNumericDeliveryDate(start)' in app
    assert 'formatNumericDeliveryDate(end)' in app

    # v0.456 established repeat motion and white Open Stage hover text; v0.457
    # supersedes the forced restart helper with a flash-free [open] animation.
    assert 'restartHomeDeliveryExpandAnimationV456' not in app
    assert '@keyframes home-delivery-expand-v457' in home_css
    assert '.delivery-date-group-v367[open] .delivery-stage-list' in home_css
    assert '.delivery-stage-open-v368 > span' in home_css
    assert 'color: #fff !important;' in home_css

    # Scan uses canonical precomputed glass gradient stops instead of a flat strip.
    assert '--glass-type-header-start' in app
    assert '--glass-type-header-mid' in app
    assert '--glass-type-header-end' in app
    assert 'v0.456 Canonical glass header gradient' in scan_css
    assert 'var(--glass-type-header-start' in scan_css
    assert 'var(--glass-type-header-end' in scan_css

    # Indian Trail popup is materially smaller and Done owns a styled action surface.
    assert 'v0.456 Compact Indian Trail receive confirmation' in styles_css
    assert 'width: min(720px, calc(100vw - 24px)) !important;' in styles_css
    assert 'min-height: 32px !important;' in styles_css
    assert 'background: linear-gradient(180deg, #2faa6b 0%, #1d814f 100%) !important;' in styles_css


def test_v0457_user_names_header_scale_statistics_scan_notification_and_transit() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    shared_css = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    home_css = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.457 - User Display Names, Header Scale, and Floor UI Refinement' in changelog

    # Edit Users saves Display Name through the existing audited profile update.
    assert 'data-user-display-name=' in app
    assert 'displayName,' in app
    assert 'display_name: str | None = None' in store
    assert 'display_name_supplied = display_name is not None' in store
    assert 'UPDATE users SET display_name = ? WHERE id = ?' in store
    assert 'display_name=data.get("displayName")' in server

    # All non-Home shared workspace headers gain ~20% height in the final layer.
    assert '.page-view:not(.home-page) .app-page-header-v357' in shared_css
    assert 'height: 139px !important;' in shared_css
    assert 'min-height: 139px !important;' in shared_css

    # Statistics no longer repeats the dataset/range sentence and its filter row
    # gives search more space while keeping Reset compact.
    assert 'id="statisticsChartSubtitle"' not in index
    assert 'Piece quantity by glass type for the selected reporting range.' not in app
    assert 'display: flex !important;' in statistics_css
    assert 'flex: 2.2 1 320px;' in statistics_css
    assert 'flex: 0 0 76px;' in statistics_css

    # Home expansion replays through native open state with no forced reflow helper.
    assert 'restartHomeDeliveryExpandAnimationV456' not in app
    assert '@keyframes home-delivery-expand-v457' in home_css
    assert 'clip-path: none !important;' in home_css

    # Scan uses the more restrained canonical gradient plus a framed group edge.
    assert 'const headerStart = blendHex("#0B2A42", .56);' in app
    assert 'const headerMid = blendHex("#153B55", .34);' in app
    assert 'v0.457 Smoothed Scan glass-section headers' in scan_css
    assert 'border-right: 1px solid rgba(8,33,52,.28) !important;' in scan_css

    # Indian Trail receive data is reordered/enriched and the compact shell grows
    # only enough to accommodate the additional verification fields.
    assert 'is-job-v457' in app
    assert 'is-customer-v457' in app
    assert 'is-dimensions-v457' in app
    assert 'is-qty-v457' in app
    assert 'width: min(828px, calc(100vw - 26px)) !important;' in styles_css
    assert 'grid-template-columns: minmax(115px, 1.05fr) minmax(190px, 1.75fr)' in styles_css

    # Bay Map uses sequential panes with a loading pause before outbound travel
    # and an unloading pause after the truck flips at Indian Trail.
    assert 'transit-rack-transfer-outbound' in app
    assert 'transit-rack-transfer-inbound' in app
    assert 'animation: bay-transit-shuttle-v457 16s linear infinite !important;' in bays_css
    assert '@keyframes bay-transit-glass-load-v457' in bays_css
    assert '@keyframes bay-transit-glass-unload-v457' in bays_css
    assert '--glass-pane-index-v457' in bays_css


def test_v0459_proportional_shuttle_canonical_chart_colors_and_compact_glass_headers() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.459 - Proportional Transit Load, Canonical Chart Colors, and Compact Glass Headers' in changelog

    # Bay Map load density and endpoint dwell derive from the live in-transit qty.
    assert 'function bayTransitAnimationProfileV459(pieceCount = 0)' in app
    assert 'const visiblePanes = Math.min(pieces, 120);' in app
    assert 'const paneMotionSeconds = 1.35;' in app
    assert 'const postLoadDwellSeconds = 2.8;' in app
    assert 'const cycleSeconds = (loadSeconds * 2) + (postLoadDwellSeconds * 2)' in app
    assert 'const transitAnimation = bayTransitAnimationProfileV459(inTransitQty);' in app
    assert 'is-waiting-for-glass-v459' in app
    assert 'Waiting for outbound glass' in app
    assert 'transit-wait-cloud-v459' in app
    assert 'var(--transit-cycle-duration-v459, 16.7s)' in bays_css
    assert '@keyframes bay-transit-shuttle-v459' in bays_css
    assert '@keyframes bay-transit-wait-dot-v459' in bays_css
    assert 'animation-delay: .28s;' in bays_css
    assert 'animation-delay: .56s;' in bays_css

    # Statistics glass colors come from the canonical shared Lookup Manager resolver
    # and repaint after a late lightweight lookup response.
    assert 'function statisticsGlassColorV459(label, colorMap = null)' in app
    assert 'glassAliasTargetV360(clean) || clean' in app
    assert 'color: statisticsGlassColorV459(row.label, glassColorMap)' in app
    assert 'statisticsGlassColorV459(row.label, breakageGlassColorMap)' in app
    assert 'if (state.page === "statistics") renderStatisticsPage();' in app
    assert 'return normalizeGlassVisualColor(entry?.color)' in app
    assert 'background: var(--chart-color, #dceafa) !important;' in statistics_css

    # Statistics header is slightly darker, but stays in the maintained blue family.
    assert 'linear-gradient(135deg, #e7f2fb 0%, #d8e8f6 62%, #c2daee 100%)' in statistics_css

    # Scan glass headers mirror the approved compact reference without an icon.
    assert 'glass-group-title-v459' in app
    assert 'glass-group-progress-v459' in app
    assert 'glass-group-toggle-v459' in app
    assert 'v0.459 Compact reference-style glass section headers' in scan_css
    assert 'min-height: 42px !important;' in scan_css
    assert 'grid-template-columns: minmax(0, 1fr) auto auto !important;' in scan_css
    assert 'border-radius: 7px !important;' in scan_css



def test_v0460_explicit_clear_glass_identity_new_marker_and_static_sheen() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.460 - Explicit Clear-Glass Identity and Scan Header Readability' in changelog

    # Backend/API reporting never exposes an ambiguous standalone Clear type.
    assert 'def canonical_clear_glass_label(value: Any) -> str:' in store
    assert '"3/8 Clear Annealed": 1.83' in store
    assert '"1/2 Clear Annealed": 2.11' in store
    assert '"1/4 Clear Annealed": 0.96' in store
    assert '"3/8 UltraClear Annealed": 4.78' in store
    assert '"1/8 Clear Annealed": 2.47' in store
    assert '"3/8 Clear": 1.83' not in store
    assert '"glassType": canonical_clear_glass_label' in store
    assert 'resolved = canonical_clear_glass_label(resolved) or resolved' in store
    assert 'canonical_clear_glass_label,' in server
    assert 'return canonical_clear_glass_label(raw) or "Other Glass"' in server

    # Browser grouping applies the same rule after maintained combine aliases.
    assert 'function canonicalClearGlassLabelV460(value = "")' in app
    assert 'const sourceRaw = String(item?.product || item?.job' in app
    assert 'const backendCanonical = String(item?.glassType || "").trim();' in app
    assert 'return canonicalClearGlassLabelV460(combined) || combined;' in app
    assert 'const canonical = canonicalClearGlassLabelV460(aliasTarget) || aliasTarget;' in app
    assert 'valuePlaceholder: "3/8 Clear Annealed"' in app

    # New stays readable inside white-text glass headers and the sheen is fixed.
    assert 'v0.460 Clear-glass/new-marker clarity + static glass-header sheen' in scan_css
    assert '.scan-page .glass-group-title-v459 .new-line-marker' in scan_css
    assert 'color: #111827 !important;' in scan_css
    assert 'rgba(255,255,255,.105) 46%' in scan_css
    assert '@keyframes' not in scan_css[scan_css.index('v0.460 Clear-glass/new-marker clarity + static glass-header sheen'):]



def test_v0462_compact_glass_header_new_badge_and_static_sheen() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.462 - Compact Glass Headers, Stronger Sheen, and NEW Badge Ink Ownership' in changelog

    # The group badge no longer uses a span, so v0.454's broad white span rule
    # cannot own its text color after the page is rendered.
    assert '<mark class="new-line-marker group-marker glass-group-new-v462"' in app
    assert 'mark.glass-group-new-v462' in scan_css
    v462_css = scan_css[scan_css.index('v0.462 Compact glass header density'):]
    assert 'color: #111827 !important;' in v462_css
    assert '-webkit-text-fill-color: #111827 !important;' in v462_css
    assert 'min-height: 36px !important;' in v462_css
    assert 'rgba(255,255,255,.245)' in v462_css
    assert 'animation:' not in v462_css


def test_v0463_glass_group_owns_full_table_row_height() -> None:
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert '20260908-v0.510' in index
    assert 'Current maintained release: **v0.527**' in readme
    v463 = scan_css[scan_css.index('v0.463/v0.464 Glass-group row owns its full table height'):]
    assert 'tr.glass-group-row.glass-tone-group {' in v463
    assert 'height: 43px !important;' in v463
    assert 'tr.glass-group-row.glass-tone-group > td {' in v463
    assert 'padding: 0 !important;' in v463
    assert 'height: 41px !important;' in v463
    assert 'min-height: 41px !important;' in v463


def test_v0464_glass_group_header_height_retune() -> None:
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.464 - Glass Group Header Height Retune' in changelog

    band = scan_css[scan_css.index('v0.463/v0.464 Glass-group row owns its full table height'):]
    assert 'height: 43px !important;' in band
    assert 'height: 41px !important;' in band
    assert 'min-height: 41px !important;' in band
    assert 'padding: 0 !important;' in band

def test_v0466_filter_counts_and_glass_contrast() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.466 - Filter Count Cleanup and Glass Selection Contrast' in changelog

    # Scan filter counts are bare values, including dynamic Glass Type counts.
    assert 'id="countRemaining">0</span>' in index
    assert 'id="countUpdated">0</span>' in index
    assert 'id="countIndianTrailRoute">0</span>' in index
    assert 'All Glass Types <span>${totalItems}</span>' in app
    assert '${escapeHtml(label)} <span>${escapeHtml(count)}</span>' in app
    assert 'els.countComplete.textContent = String(workflowStatusCountsV514.complete);' in app
    assert 'els.countRushes.textContent = `${rushAll}`;' in app
    assert 'els.countErrors.textContent = `${stats.errorCount}`;' in app

    # Contrast uses the actual filled-glass color rather than one threshold, and
    # count pills deliberately own dark ink on a pale background.
    assert 'whiteContrastV466' in app
    assert 'darkContrastV466' in app
    assert 'const selectedInk = whiteContrastV466 >= darkContrastV466 ? "#FFFFFF" : "#10243A";' in app
    assert 'v0.466 Filter counts + glass-selection contrast' in scan_css
    assert 'background: rgba(255,255,255,.92) !important;' in scan_css
    assert 'color: #10243a !important;' in scan_css
    assert 'v0.466 Print / Export glass-selection contrast' in styles_css
    assert 'print-filter-chip-v197.glass-tone-chip:has(input:checked):not(.is-glass-all) > b' in styles_css



def test_v0469_unified_priority_work_intake_and_printouts() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.469 - Unified Priority Work Intake and Printable Rush / Remake Paperwork' in changelog

    # One visible request workflow owns Rush, Remake, and combined work. Missing
    # Glass remains available as paperwork/reason, not as a fourth request type.
    assert 'data-priority-request-mode="rush"' in index
    assert 'data-priority-request-mode="remake"' in index
    assert 'data-priority-request-mode="both"' in index
    assert 'data-priority-request-mode="missing"' not in index
    assert 'id="priorityIntakeLookupStatus"' in index
    assert 'id="priorityIntakeDeliveryDate"' in index
    assert 'id="priorityIntakePrintRushBtn"' in index
    assert 'id="priorityIntakePrintRemakeBtn"' in index
    assert 'id="priorityIntakePrintMissingBtn"' in index
    assert 'Missing Glass' in store

    # Existing jobs resolve first and use the same submit route as future work.
    assert 'def _priority_work_target_rows_con' in store
    assert 'def priority_work_lookup' in store
    assert 'def submit_priority_work' in store
    assert 'def _apply_priority_work_existing' in store
    assert 'return ["Remake", "Rush"]' in store
    assert 'priorityIntakeDeliveryDate' in app
    assert 'schedulePriorityWorkLookup' in app
    assert 'renderPriorityWorkLookupStatus' in app
    assert 'fetchJson(`/api/indian-trail/priority-work-lookup?' in app
    assert 'fetchJson("/api/indian-trail/priority-work"' in app
    assert 'parsed.path == "/api/indian-trail/priority-work-lookup"' in server
    assert 'parsed.path == "/api/indian-trail/priority-work"' in server

    # Printable paperwork works before or after import and Work Center exposes
    # combined requests without reviving Missing Glass Rush as a category.
    assert 'function printPriorityWorkSheet' in app
    assert 'data-priority-print-request' in app
    assert 'Rush + Remake' in app
    assert 'Missing Glass Sheet' in app
    assert 'priority-work-print-actions-v469' in bays_css
    assert 'priority-work-section-v347.is-both' in bays_css
    assert '"kind": "missing_glass_rush"' not in store[store.index('def priority_banner_annotations'):store.index('def attach_priority_search_annotations')]
    assert '"kind": "both"' in store[store.index('def priority_banner_annotations'):store.index('def attach_priority_search_annotations')]


def test_v0470_production_workflow_lookup_statistics_and_visual_contract() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    shared_css = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    production_files = (ROOT / "backend/production_files.py").read_text(encoding="utf-8")
    config = (ROOT / "backend/config.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.470 - Production File Awareness, Focused Lookup Editing, and Floor Workflow Polish' in changelog

    # Production file integration stays isolated/read-only and exposes the three
    # order-detail actions plus a fail-safe fabrication gate before Staging.
    assert 'class ProductionFileService' in production_files
    assert 'hardware_lists_dir' in config and 'completed_wj_dir' in config
    assert 'def fabrication_status' in production_files
    assert 'def fabrication_scan_preflight' in store
    assert 'staging_fabrication_blocked' in store
    assert 'parsed.path == "/api/production-files/hardware"' in server
    assert 'parsed.path == "/api/production-files/asset"' in server
    assert 'parsed.path == "/api/production-files/open"' in server
    assert 'data-order-v470=' in app
    assert 'production-fab-status-v470' in app
    assert 'data-production-preview-asset-v470' in app
    assert 'data-production-print-asset-v470' in app
    assert 'data-production-open-asset-v470' in app
    assert '.production-explorer-panel-v470' in shared_css

    # Bay Map actions moved to cards and the Hardware entry is present.
    assert 'data-bay-action="hardware"' in index
    assert 'bay-tool-card-v470 is-hardware' in index
    assert '.bay-tool-card-grid-v470' in bays_css
    assert 'v0.470 Bay Map shuttle layer/order correction' in bays_css
    assert 'Outbound truck faces right, so its rear door is on the left' in app

    # Lookup Manager uses a full-width library with focused add/edit overlay.
    assert 'lookup-manager-v470' in app
    assert 'data-lookup-add-v470' in app
    assert 'lookup-editor-backdrop-v470' in app
    assert '.lookup-manager-v470' in admin_css
    assert '.lookup-editor-backdrop-v470' in admin_css

    # Scan filtering/visual status and Statistics common-size mode are wired.
    assert 'is-error-active-v470' in app
    assert 'Err' in app and 'New' in app and 'IR' in app and 'RM' in app
    assert 'v0.470 Scan table proportions, error signal, rack transit color' in scan_css
    assert 'statistics-glass-size-control-v470' in statistics_css
    assert 'Most common sizes · ${selected.glassType}' in app
    assert 'glassSizeFrequencyByType' in app


def test_v0471_statistics_common_size_selector_recovers_dynamic_options() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.471 - Reliable Common Glass Size Selection' in changelog

    # Dynamic custom-select menus must refresh even if backend options arrive
    # after the menu has already been opened on an empty native select.
    assert 'function customSelectOptionSignature(select)' in app
    assert 'optionSignatureV471' in app
    assert 'renderCustomSelectOptions(select, optionsHost, query);' in app

    # Statistics communicates loading/no-data instead of exposing a blank menu,
    # retries a missing report on page entry, and recovers when the metric is
    # selected before its report-only dataset has arrived.
    assert 'homeReportSummaryLoading: false' in app
    assert 'Loading glass types…' in app
    assert 'No glass-size data in this range' in app
    assert 'els.statsGlassSizeTypeSelect.disabled = !sizeTypes.length;' in app
    assert 'if (!activeHomeReportSummaryV472()) void loadHomeReportSummary();' in app
    assert 'state.homeChartMetric === "glass-sizes"' in app



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
    assert 'static/css/print.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.221 - Idle Route and Print Row State Recovery' in changelog


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
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'Current maintained release: **v0.527**' in readme
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
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'static/css/print.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.230 - Create Preset Flow Repair and Subtle Control Palette' in changelog


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
    assert 'static/js/app.js?v=20260910-v0.527' in html


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
    assert 'APPLICATION_VERSION = "527"' in contract
    assert "Current maintained release: **v0.527**" in readme
    assert "static/css/print.css?v=20260910-v0.527" in html
    assert "static/js/app.js?v=20260910-v0.527" in html




def test_v0244_beveled_primary_actions_and_larger_close_controls():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    shared = (root / "static/css/shared-ui.css").read_text(encoding="utf-8")
    racks = (root / "static/css/racks.css").read_text(encoding="utf-8")
    contract = (root / "database/contract.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    changelog = (root / "README_CHANGELOG.md").read_text(encoding="utf-8")

    for button_id in (
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
    assert 'APPLICATION_VERSION = "527"' in contract
    assert "Current maintained release: **v0.527**" in readme
    assert "## v0.244 - Beveled Actions and Rack GUI Visual Identity" in changelog


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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'static/css/bays.css?v=20260908-v0.513' in html
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.253 - Statistics Dashboard Hierarchy and Chart Explorer Polish' in changelog




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
    assert 'value="stage-open"' in statistics_section
    assert 'value="actions"' in statistics_section
    # v0.454 removes the duplicate Delivery-list and Delivery-date metric groups.
    assert 'value="incomplete"' not in statistics_section
    assert 'value="date-completion"' not in statistics_section
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/statistics.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/statistics.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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
        ('"3/8 Clear Annealed": 1.83', 1.83),
        ('"1/2 Clear Annealed": 2.11', 2.11),
        ('"1/4 Clear Annealed": 0.96', 0.96),
        ('"3/8 UltraClear Annealed": 4.78', 4.78),
        ('"1/4 Mirror": 2.60', 2.60),
        ('"1/8 Clear Annealed": 2.47', 2.47),
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '## v0.260 - Compact Glass-First Statistics and Breakage Analytics' in changelog




def test_v0263_restores_statistics_typography_and_reorganizes_breakage_tables():
    """v0.263 restores readable text and groups breakage accountability into clear blocks."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static/css/statistics.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/statistics.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/statistics.css?v=20260910-v0.527' in html
    assert 'static/css/scan.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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




def test_v0267_scan_selector_menu_alignment_and_delivery_week_width():
    """v0.267 keeps scan dropdown rows single-line and gives week headers enough width."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/scan.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/scan.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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




def test_v0270_rack_creation_workspaces_are_guided_and_return_to_manager():
    """v0.270 gives both rack creation flows a polished guided workspace and an explicit way back."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static" / "css" / "racks.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'static/css/racks.css?v=20260908-v0.510' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
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
    assert 'class="app-primary-button app-cancel-button app-cancel-action-v343" data-rack-form-back>' in js
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
    assert 'APPLICATION_VERSION = "527"' in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION = 20" in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")




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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.276 - Authoritative SQL Reconciliation Repair' in changelog

    assert 'if ($Mode -eq "Custom")' in runner
    # v0.502 supersedes the old manual-force-all-dates repair: every date is
    # still verified, but unchanged dates are no longer rewritten on every click.
    assert '$forceImportDates = @($script:PendingImportDates | Sort-Object -Unique)' in runner
    assert '$forceImportDates = @($sourceDates)' not in runner
    assert 'only changed/drifted dates will be rewritten' in runner
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/styles.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
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



def test_v0256_delivery_update_preview_groups_route_glass_order_item_without_inner_scroll():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")

    preview = app[
        app.index("function deliveryListUpdatePreviewHtml"):
        app.index("async function openDeliveryListUpdatePreview")
    ]
    assert 'const previewGlassColorMap = buildGlassVisualColorMap(' in preview
    assert 'item.product || item.glassType || item.glass' in preview
    assert 'delivery-update-preview-glass-group-v256' not in preview
    assert 'delivery-update-preview-order-group-v256' not in preview
    assert 'delivery-update-preview-order-list-v311' in preview
    assert 'delivery-update-preview-location-group-v311' in preview
    assert 'delivery-update-preview-order-identity-v311' in preview
    assert 'routeStartsOpen' in preview
    assert 'data-preview-filter-button' not in preview
    assert 'data-preview-search-input' not in preview

    assert '.delivery-update-preview-v256 .delivery-update-preview-glass-list-v256' in css
    assert 'max-height: none;' in css
    assert 'overflow: visible;' in css
    assert '.delivery-update-preview-glass-group-v256' in css
    assert '.delivery-update-preview-order-group-v256' in css
    assert '.delivery-update-preview-item-body-v256' in css



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
    assert 'sharedNumberedPagerMarkup(state.adminImportRunPage, totalPages, "data-admin-import-page")' in browser
    assert "of ${groups.length}" in browser
    assert "adminImportRunsPerPage: 5" in app
    assert ".admin-import-run-browser-v257 .admin-import-run-tabs" in css
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in css
    assert "maximum_rows: int = 5000" in controller
    assert 'runtime_items = [*latest_items, *archived_items]' in controller



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
    assert "Approve removal of order" in app
    assert "remove_order_number: str = \"\"" in store
    assert "selected_remove_order not in {original_order, replacement_order}" in store
    assert "approved_remove_order_no" in store
    assert 'str(data.get("removeOrderNumber") or "")' in server
    assert "v257_superseded_remove_choice" in migrations
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract


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
    assert 'state.activeListId = desiredListId;' not in app[:app.index("function dlsAutomationApplyImportSnapshot")]
    assert 'state.deliveryDateSelectSignatureV487 = "";' in app[:app.index("function dlsAutomationApplyImportSnapshot")]
    assert "detailRefreshListId !== previousActiveListId" in app
    assert "All rows" not in app[app.index("function deliveryListUpdatePreviewHtml"):app.index("function importPreviewPayloadsFromContext")]
    assert 'APPLICATION_VERSION = "527"' in contract
    assert "static/js/app.js?v=20260910-v0.527" in html



def test_v0306_single_page_mobile_workflow_and_dialog_repairs():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    mobile = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")

    assert 'viewport-fit=cover' in html
    assert 'static/css/mobile.css?v=20260909-v0.517' in html
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
    assert 'APPLICATION_VERSION = "527"' in contract

def test_v0307_rack_review_history_creation_and_status_reliability() -> None:
    """v0.307 keeps review receipts per user and makes rack management deterministic."""
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    racks_css = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend/operations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/racks.css?v=20260908-v0.510' in index
    assert 'static/js/app.js?v=20260910-v0.527' in index
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




def test_v316_physical_transit_counts_bay_bulk_edit_and_scan_archive_compaction() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
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
    assert "static/css/bays.css?v=20260908-v0.513" in index
    assert "static/js/app.js?v=20260910-v0.527" in index




def test_v325_compact_bay_labels_stage_aware_location_history_and_short_rack_routes() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'function bayLocationDisplayLabel(code = "", name = "")' in app
    assert 'text = text.replace(/^BAY\\s+/i, "").trim();' in app
    assert 'return match ? `Bay ${match[1]}` : "";' in app
    assert 'function scanLocationPresentation(item)' in app
    assert 'if (indianTrailStage)' in app
    assert 'Previously stored in ${previousBay}; the bay assignment has been removed.' in app
    assert 'Previously transported in ${currentRack}; this item has been received downstream.' in app
    assert 'if (item?.received === true || Number(item?.receivedQty || 0) > 0) return false;' in app
    assert 'recent-location-cell-v325' in app
    assert 'placementBayShort' in app

    assert 'if (/green|gnv/i.test(text)) return "GNV";' in app
    assert 'if (/indian|trail|^it$/i.test(text)) return "IT";' in app
    assert 'text.includes("green") || text === "gnv"' in app
    assert '${escapeHtml(rackDestinationLabel(value))}</option>' in app

    assert 'WITH bay_history AS (' in store
    assert 'item["lastBayCode"] = str(bay_history["bay_code"] or "")' in store
    assert 'AS last_bay_code' in store
    assert 'AS last_bay_assignment_status' in store
    assert '"lastBayCode": row_value(row, "last_bay_code", "")' in store
    assert '"lastRackCode": row_value(row, "last_rack_code", "")' in store

    assert '.last-bay-location-v321.is-history' in css
    assert '.recent-location-cell-v325.is-history' in css
    assert '.location-badge.is-location-history' in css
    assert '<small>Location</small>' in html
    assert '<th>Location</th>' in html

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'static/css/scan.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.325 - Compact Bay Labels and Stage-Aware Location History' in changelog




def test_v329_simplified_scan_sort_rack_route_and_visual_fidelity() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # Headers are now the sort control; no funnel button or column-filter popup remains.
    assert 'class="scan-column-sort-v329" type="button" data-scan-sort="glass"' in html
    assert 'data-scan-column-filter=' not in html
    assert 'scanColumnFilters' not in app
    assert 'openScanColumnFilterMenu' not in app
    assert 'scan-column-filter-menu-v328' not in scan
    assert '.scan-column-sort-v329 {' in scan

    # Add Qty shares the canonical blue button style.
    assert 'class="app-primary-button" data-scan-quantity-add>Add Qty</button>' in app

    # Rack header status is high contrast and route is a sibling cell using shortened destination labels.
    assert 'id="operationsModalRackRoute" class="operations-modal-rack-route-v329"' in html
    assert 'routeLabel.textContent = "Route";' in app
    assert 'rackRoute: resolvedDestination ? rackDestinationLabel(resolvedDestination) : "Not set"' in app
    assert '.operations-modal-rack-route-v329 {' in racks
    assert '.operations-modal-rack-status-v326.in-transit :is(small, strong) { color: #235f9a !important; }' in racks

    # Every icon offered by the new grouped-set picker survives into overview/modal rendering.
    for icon in ("glasscart", "pallet", "dolly", "crate", "warehouse"):
        assert f'body .rack-set-card[data-rack-icon="{icon}"] .rack-set-icon::before' in racks
        assert f'body .operations-modal-panel[data-rack-icon="{icon}"] .operations-modal-visual-icon::before' in racks
    assert 'const setAccent = setColor || `hsl(${setHue} 48% 42%)`;' in app
    assert '--rack-set-accent:${setAccent}' in app
    assert 'border-color: var(--rack-set-accent) !important;' in racks

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.329 - Simplified Scan Sorting and Rack Visual Fidelity' in changelog



def test_v330_removed_scan_column_filter_cleanup_cannot_break_startup() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # v0.329 removed the column-filter implementation. No listener may retain
    # a reference to that deleted API or startup event binding will throw.
    assert "closeScanColumnFilterMenu" not in app
    assert "openScanColumnFilterMenu" not in app
    assert "scanColumnFilters" not in app
    assert 'data-scan-column-filter=' not in html

    # Header sorting remains the supported interaction.
    assert 'class="scan-column-sort-v329" type="button" data-scan-sort="glass"' in html

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.330 - Scan Startup Regression Fix' in changelog


def test_v331_scan_page_sort_runtime_and_route_coloring() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # The Scan page must retain the sorting helper used by getPagedItems().
    assert "function sortScanItems(items)" in app
    assert "sortScanItems(group.items)" in app
    assert "closeScanColumnFilterMenu" not in app
    assert "openScanColumnFilterMenu" not in app

    # The individual-rack Route cell derives its visual class from the route,
    # not from the rack set/material accent.
    assert 'rackRouteClass: rackDestinationClass(resolvedDestination)' in app
    assert 'els.operationsModalRackRoute.className = `operations-modal-rack-route-v329 is-${rackRouteClass}`;' in app
    for route_class, color in {
        "indian-trail": "#176b2d",
        "cpu": "#56339a",
        "greenville": "#0a6f79",
        "dtc": "#a02a68",
    }.items():
        selector = f'.operations-modal-rack-route-v329.is-{route_class} {{'
        assert selector in racks
        section = racks[racks.index(selector):racks.index(selector) + 260]
        assert f"--rack-route-text: {color};" in section

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.331 - Scan Page Render and Route Status Color Fix' in changelog




def test_v334_packing_history_icons_flag_sort_and_admin_history_scroll() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # Packing-history heading uses direct inline SVG with explicit centered
    # dimensions; snapshot paper spacing remains intentionally separated.
    assert ".packing-history-intro-icon-v333 > svg {" in racks
    assert "width: 24px;" in racks
    assert "height: 24px;" in racks
    assert "margin-left: -5px;" in racks
    assert "grid-template-columns: 40px minmax(0, 1fr);" in racks
    assert "gap: 13px;" in racks
    assert "transform: translateX(-3px);" in racks

    # Flag sorting is based only on visible Flag-column markers. The first
    # ascending click puts any flagged item ahead of rows with no flags.
    assert "function scanFlagLabels(item)" in app
    assert 'item.manualOnly ? "Manual scan only" : ""' in app
    assert 'if (key === "flags") {' in app
    assert "const leftHasFlags = leftFlags.length > 0;" in app
    assert "return (leftHasFlags ? -1 : 1) * direction;" in app
    flag_helper = app[app.index("function scanFlagLabels(item)"):app.index("function syncScanTableHeaders()") ]
    assert "item.processState" not in flag_helper
    assert "item.queueState" not in flag_helper

    # v0.335 intentionally supersedes v0.334's whole-tab scrolling after operator
    # feedback: controls remain pinned and the history-result list owns overflow.
    v335_admin = admin[admin.index("/* v0.335 Admin Action History pinned controls and owned result scrolling"):]
    assert "#adminModalHistory.modal-action-history:not([hidden]) {" in v335_admin
    assert "overflow: hidden !important;" in v335_admin
    assert "#adminModalHistory .modal-action-history-list {" in v335_admin
    assert "overflow-y: auto !important;" in v335_admin
    assert "#operationsModal .modal-action-history-list {" in styles

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.334 - Packing History Icons, Flag Sorting, and Action History Scrolling' in changelog


def test_v335_pinned_admin_history_flag_runtime_route_initialization_filters_and_excel_polish() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # Edit Racks Action History keeps controls visible while its result list owns scrolling.
    v335_admin = admin[admin.index("/* v0.335 Admin Action History pinned controls and owned result scrolling"):]
    assert "#adminModalHistory.modal-action-history:not([hidden]) {" in v335_admin
    assert "overflow: hidden !important;" in v335_admin
    assert "grid-template-rows: auto auto minmax(0, 1fr);" in v335_admin
    assert "#adminModalHistory .modal-action-history-list {" in v335_admin
    assert "overflow-y: auto !important;" in v335_admin
    assert "scrollbar-gutter: stable;" in v335_admin

    # Flag sorting uses the actual visible Internal Reject counter and has no dangling helper.
    flag_helper = app[app.index("function scanFlagLabels(item)"):app.index("function syncScanTableHeaders()") ]
    assert 'Number(item.internalRejectCount || 0) > 0 ? "Internal Reject" : ""' in flag_helper
    assert "isInternalRejectItem(" not in app
    assert "return (leftHasFlags ? -1 : 1) * direction;" in flag_helper

    # Initial rack-modal setup carries the resolved route class immediately.
    modal_open = app[app.index("function openOperationsModal({"):app.index("function closeOperationsModal(")]
    assert 'rackRouteClass = ""' in modal_open
    assert "...(rackRouteClass ? { rackRouteClass } : {})" in modal_open

    # Detailed print selections no longer collapse merely because every detail is selected.
    print_sync = app[app.index("function syncPrintAllGlassChoice"):app.index("function normalizePrintRouteGroups")]
    assert ".every((input) => input.checked)" not in print_sync
    preset_sync = app[app.index("function handlePrintPresetBuilderChange"):app.index("async function confirmPrintPresetSave")]
    assert ".every((input) => input.checked)" not in preset_sync

    # Excel export reserves logo space and keeps the image's natural aspect ratio.
    sheet_writer = app[app.index("function xlsxSheetDocument"):app.index("function xlsxStylesDocument")]
    assert 'const merges = ["C1:H1", "C2:H2", "C3:E3", "F3:H3", "C4:H4", "A5:E5", "F5:H5"]' in sheet_writer
    assert '<printOptions horizontalCentered="1"/>' in sheet_writer
    assert 'Page &amp;P of &amp;N' in sheet_writer
    drawing_writer = app[app.index("function xlsxDrawingDocument"):app.index("let xlsxCrcTable = null")]
    assert "<xdr:oneCellAnchor>" in drawing_writer
    assert 'noChangeAspect="1"' in drawing_writer
    assert "const maxWidth = Math.round(2.35 * emuPerInch);" in drawing_writer
    assert "const maxHeight = Math.round(0.95 * emuPerInch);" in drawing_writer
    assert "<AppVersion>0.339</AppVersion>" in app

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.335 - Pinned Action History, Reliable Flag Sorting, and Polished Excel Export' in changelog


def test_v336_all_scans_quantity_edit_racks_visibility_icon_date_alignment_and_excel_header() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    admin = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # Last Scan no longer owns the persistent multi-quantity follow-up UI.
    assert 'id="lastScanQuantityActions"' not in html
    assert "lastScanQuantityActions" not in app
    assert "renderLastScanQuantityActions" not in app

    # v0.337 supersedes the v0.336 All Scans follow-up control. Multi-quantity
    # completion remains available only in the immediate successful scan notice.
    assert "function scanQuantityDeliveryDateIsActive" in app
    assert "cleanDate >= printCalendarDateKey(new Date())" in app
    assert "scanQuantityRemaining(item) > 0" in app
    assert "function scanQuantityBoostMarkup(entry, item, context = {})" in app
    assert "function allScansQuantityBoostMarkup(entry, item)" not in app
    assert "all-scans-quantity-boost-v336" not in app
    assert "quantityActionItemIds" not in app
    assert ".all-scans-quantity-boost-v336" not in scan

    # Edit Racks must not lay out hidden Action History beside Rack Manager.
    assert "#adminModalHistory.modal-action-history:not([hidden]) {" in admin
    assert "#adminModalHistory[hidden] {" in admin
    assert "display: none !important;" in admin[admin.rindex("#adminModalHistory[hidden] {"):]

    # Packing History uses one centered inline SVG; there is no competing intro
    # pseudo-element that can offset the icon inside its background.
    assert '<span class="packing-history-intro-icon-v333" aria-hidden="true"><svg viewBox="0 0 24 24"' in app
    assert ".packing-history-intro-icon-v333 > svg {" in racks
    assert ".packing-history-intro-icon-v333::before" not in racks

    # Date selector copy is deliberately left aligned.
    v336_print = print_css[print_css.index("/* v0.336 Print / Export date selector alignment"):]
    assert "text-align: left !important;" in v336_print
    assert "justify-content: flex-start !important;" in v336_print

    # Formatted workbook header rows 1-4 use consistent borderless styles.
    styles_writer = app[app.index("function xlsxStylesDocument"):app.index("function xlsxDrawingDocument")]
    assert 'fontId="6" fillId="2" borderId="0"' in styles_writer
    assert 'fontId="3" fillId="5" borderId="0"' in styles_writer
    assert "<AppVersion>0.339</AppVersion>" in app

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.336 - All Scans Quantity Completion and UI Consistency Fixes' in changelog


def test_v337_notification_only_quantity_all_scans_header_cleanup_and_rack_hit_target_repair() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    # Multi-quantity completion is notification-only. All Scans shows the
    # maintained scanned/total quantity but no changer controls.
    assert "function scanQuantityBoostMarkup(entry, item, context = {})" in app
    assert "function allScansQuantityBoostMarkup(entry, item)" not in app
    recent_start = app.index("function recentScansModalHtml()")
    recent_end = app.index("function renderMeta()", recent_start)
    recent = app[recent_start:recent_end]
    assert "data-scan-quantity-add" not in recent
    assert "data-scan-quantity-all" not in recent
    assert "all-scans-quantity-boost-v336" not in scan

    # All Scans no longer shows the green-dot Live audit status pill.
    profile = app[app.index("recentScans: {"):app.index("};", app.index("recentScans: {"))]
    assert "showStatus: false" in profile
    assert "Live audit data" not in profile

    # Packing History owns one centered direct SVG and shifts the full badge a
    # few pixels left without an overlapping pseudo icon.
    assert ".packing-history-intro-icon-v333 > svg {" in racks
    assert "margin-left: -5px;" in racks
    assert ".packing-history-intro-icon-v333::before" not in racks

    # Rack heading repair checks actual header overlap/hit testing after async
    # refresh and after the final modal closes instead of forwarding clicks.
    assert "function rackHeadingActionNeedsRepair()" in app
    assert "document.elementFromPoint(x, topY)" in app
    assert 'topHit?.closest?.(".app-header")' in app
    assert "function scheduleRackHeadingHitTargetRepair()" in app
    assert 'if (wasLocked && !modalIsOpen && state.page === "racks") scheduleRackHeadingHitTargetRepair();' in app
    assert "scheduleRackHeadingHitTargetRepair();" in app[app.index("async function refreshRacksPage()"):app.index("function renderRackSelects()") ]
    assert "click forwarding" not in app[app.index("function resetPageScrollPosition()"):app.index("function showPage(page)")]
    assert "v0.337 Packing-history badge alignment and Rack heading hit-target stability" in racks

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.337 - Notification-Only Multi-Quantity and Rack Hit-Target Stabilization' in changelog



def test_v0350_rack_display_and_priority_request_regression():
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'function normalizeRackDisplayName(name = "", type = "")' in app
    assert 'text.replace(/\\bracks?\\b/gi' in app
    assert 'if (numberFirst) text = `${numberFirst[2].trim()} ${Number(numberFirst[1])}`;' in app
    assert 'return normalizeRackDisplayName(cleanName, type) || cleanCode;' in app
    assert 'const pieces = qty > 0 ? `${qty}PC${qty === 1 ? "" : "s"}` : "";' in app

    assert 'const rackMenuScale = 0.791;' in app
    assert 'Math.round(rect.width * rackMenuScale)' in app
    assert 'Math.floor(availableVertical * rackMenuScale)' in app
    assert 'is-rack-select-menu-v351' in app
    assert '.custom-select-menu.is-rack-select-menu-v351' in racks

    assert 'rack-location-editor-v350' in app
    assert 'line-rack-location-display-v350' in app
    assert '.rack-location-editor-v350 .custom-select-trigger' in scan
    assert 'opacity: 0;' in scan

    assert 'name="priorityNewRequestType" value="Rush"' in index
    assert 'name="priorityNewRequestType" value="Remake"' in index
    assert 'name="priorityNewRequestType" value="Both"' in index
    assert 'data-priority-request-mode="missing"' not in index
    assert 'priority-new-request-type-v350' in bays
    assert 'data-priority-new-mode=' not in index
    assert 'function setPriorityNewRequestMode(mode = "rush")' in app

    assert 'static/js/app.js?v=20260910-v0.527' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'Current maintained release: **v0.527**' in readme



def test_v0351_rack_color_route_old_bay_and_missing_glass_workflow() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'function rackSetDisplayColor(value)' in app
    assert 'const rackMenuScale = 0.791;' in app
    assert 'is-rack-select-menu-v351' in app
    assert '.custom-select-menu.is-rack-select-menu-v351' in racks
    assert 'font-size: 12px !important;' in scan
    assert 'data-rack-color=' in app


def test_v0352_transport_history_selection_old_bay_and_missing_glass_rework() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.352 - Rack Route Selection, Historical Locations, Stable Row Selection, Old Bay Normalization, and Missing Glass Rework' in changelog

    # Closed Transportation Method gets the same leading route pill as opened options.
    assert 'rack-selected-option-v352' in app
    assert 'rack-select-option-route-v345' in app
    assert 'rack-selected-option-summary-v352' in app
    assert '.rack-selected-option-v352' in racks
    grouped = app[app.index('function groupedRackOptionsHtml('):app.index('function rackCodeForScan(')]
    assert ': rackOptionLabel(rack);' in grouped

    # Location labels stay uppercase and selected rows survive refreshes.
    assert 'text-transform: uppercase !important;' in scan[scan.index('v0.352 stable Location labels'): ]
    assert 'const previousSelectedId = String(state.selectedId || "");' in app
    assert 'const selectedStillExists = previousSelectedId' in app

    # All Scans uses event-time assignment history and records explicit rack moves.
    modal = app[app.index('function recentScansModalHtml()'):app.index('function renderMeta()')]
    assert '<th>Location</th>' in modal
    assert 'scanEventLocationPresentation(entry)' in modal
    assert 'eventRackCode' in store
    assert 'eventBayCode' in store
    assert 'ri.added_at' in store and '<= se.created_at' in store
    assert '"rack_move"' in store
    assert 'Moved from {previous_label} to {next_label}' in store

    # The old v0.352 Missing Glass selection panel is intentionally retired in
    # v0.469; its durable priority behavior now lives in the central intake.
    stale = app[app.index('function renderStaleBayPanel('):app.index('async function snoozeStaleBayOrders(')]
    assert 'data-stale-select-group=' in stale
    assert 'data-stale-snooze-group=' in stale
    assert 'stale-bay-neighbors-v352' in stale
    for control_id in ['priorityIntakeJob', 'priorityIntakeLookupStatus', 'priorityIntakeDeliveryDate', 'priorityIntakeReason', 'priorityIntakeResponsible', 'priorityIntakeSubmitBtn']:
        assert f'id="{control_id}"' in html
    assert 'id="sdiForm"' not in html
    assert 'data-priority-request-mode="both"' in html




def test_v0354_all_scans_modal_performance_errors_live_color_and_workflow_alignment() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.354 - Normalized All Scans, Smooth GUIs, Visible Rack Errors, Live Rack Color, and Workflow Repair' in changelog

    # All Scans owns all ten columns instead of shrinking Location in isolation.
    modal = app[app.index('function recentScansModalHtml()'):app.index('function renderMeta()')]
    for column in [
        'all-scans-col-event', 'all-scans-col-source', 'all-scans-col-item',
        'all-scans-col-qty', 'all-scans-col-customer', 'all-scans-col-location',
        'all-scans-col-details', 'all-scans-col-user', 'all-scans-col-time',
        'all-scans-col-check',
    ]:
        assert f'class="{column}"' in modal
    assert 'locationColumnCh' in modal
    assert 'table-layout: fixed !important;' in scan
    assert 'all-scans-col-check { width: 54px; }' in scan
    assert 'all-scans-col-location { width: calc(var(--all-scans-location-ch' in scan
    assert 'overflow-x: auto !important;' in scan

    # Operator GUIs avoid expensive live compositing and hidden refresh work.
    assert 'v0.354 MODAL PERFORMANCE OWNERSHIP' in styles
    assert 'body.modal-scroll-locked :is(.app-header, .app-sidebar)' in styles
    assert 'filter: none !important;' in styles[styles.index('v0.354 MODAL PERFORMANCE OWNERSHIP'):]
    assert 'body.modal-scroll-locked [class*="backdrop"]' in styles
    assert 'body.modal-scroll-locked .custom-select-menu' in styles
    polling = app[app.index('function startPolling()'):app.index('function stopPolling()')]
    assert 'appModalUiIsOpen()' in polling
    notifications = app[app.index('async function pollUserNotifications()'):app.index('function startNotificationPolling()')]
    assert 'appModalUiIsOpen()' in notifications
    assert 'if (document.hidden || appModalUiIsOpen()) return;' in app
    language = app[app.index('function syncLanguageMutationObserver()'):app.index('function isMobileSidebarLayout()')]
    assert 'const shouldObserve = state.language === "es";' in language
    assert 'languageUi.observer.disconnect();' in language
    assert 'if (node.querySelector?.("select")) enhanceCustomSelects(node);' in app
    assert 'resultsObserver.observe(results, { childList: true });' in app

    # Inline rack assignment failures become visible popup feedback, and rack
    # lifecycle changes repaint Scan Location immediately.
    inline_error = app[app.index('function showInlineError('):app.index('function showFloatingNotice(')]
    assert 'if (!needsReview) return;' in inline_error
    assert 'showActionFeedback({' in inline_error
    rack_change_handler = app[app.index('document.addEventListener("change", (event) => {', app.index('data-line-rack-select')):]
    assert 'showInlineError(error.message, true)' in rack_change_handler
    for function_name in ['completeRack', 'uncompleteRack', 'returnRack', 'markRackNotOnTheWay']:
        start = app.index(f'async function {function_name}(')
        end = app.find('\nasync function ', start + 1)
        section = app[start:end if end != -1 else len(app)]
        assert 'if (state.page === "scan") renderScanPage();' in section
    rack_refresh = app[app.index('async function ensureRacksLoaded('):app.index('function renderScanRackTools()')]
    assert 'if (state.page === "scan") renderScanPage();' in rack_refresh
    process_scan = app[app.index('async function processScanInternal('):app.index('async function submitManualScan()')]
    assert 'void ensureRacksLoaded(true).catch(() => {});' in process_scan

    # Old Bays keeps severity on the order card, not every item row. Accounted
    # lines are green/neutral and only actual missing quantities are warnings.
    stale = app[app.index('function renderStaleBayPanel('):app.index('async function snoozeStaleBayOrders(')]
    assert 'missingQty ? "MISSING" : "ACCOUNTED"' in stale
    assert 'stale-bay-line-missing-v353 ${missingQty ? "has-missing" : "is-clear"}' in stale
    stale_css = bays[bays.index('.stale-bay-line-v353 {'):bays.index('.stale-bay-order-summary-v353 {')]
    assert 'box-shadow: none;' in stale_css
    assert '.stale-bay-line-missing-v353.has-missing strong' in bays
    assert '.stale-bay-line-state-v353.is-missing b' in bays

    # Missing Glass retains exact header/row alignment after the v0.355 rebuild.
    shared_grid = '#sdiPanel .missing-glass-workflow-v355 .missing-glass-ledger-v355 > header,\n#sdiPanel .missing-glass-workflow-v355 .missing-glass-line-v355'
    assert shared_grid in bays
    assert 'grid-template-columns: 28px 112px minmax(180px, 1fr) 98px 58px 66px 58px 88px;' in bays
    assert '#sdiPanel .missing-glass-workflow-v355 .custom-select-trigger' in bays
    assert 'height: 38px !important;' in bays[bays.index('#sdiPanel .missing-glass-workflow-v355 .custom-select-trigger'):]




def test_v0356_missing_item_cards_old_bay_print_move_rack_selector_and_manage_text() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    racks = (ROOT / "static/css/racks.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.356 - Missing Glass Item Selector, Old Bay Investigation Print, Shared Move Rack Selector, and Manage Items Readability' in changelog

    selection = app[app.index('function renderSdiItemSelection()'):app.index('function currentPriorityItems(')]
    for token in ['missing-glass-item-card-v356', 'missing-glass-item-metrics-v356', 'missing-glass-item-status-v356', 'missing-glass-selector-v356', 'data-sdi-line-item-id=']:
        assert token in selection
    assert '#sdiPanel .missing-glass-item-card-v356' in bays
    assert 'grid-template-columns: 30px 110px minmax(155px, 1fr) 92px 170px 84px;' in bays

    # Investigation printing mirrors Bay -> Order -> Glass instead of the legacy flat worksheet.
    report = server[server.index('def render_stale_bay_report('):server.index('def render_print_package(')]
    for token in ['class="bay-section"', 'order_class = "order-card', 'class="glass-ledger"', 'class="order-state', 'Physically verified', 'Investigation notes']:
        assert token in report
    assert 'Age colors deepen from orange to dark red; purple identifies an active snooze.' in report

    # Move Rack delegates to the exact same body-mounted custom-select system as Scan.
    transfer = app[app.index('function chooseRackTransferDestination('):app.index('async function moveRackContents(')]
    assert 'groupedRackOptionsHtml(destinations' in transfer
    assert 'enhanceCustomSelect(destinationSelect);' in transfer
    assert 'syncCustomSelect(destinationSelect);' in transfer
    assert 'rack-transfer-combobox-menu' not in transfer
    assert '.rack-transfer-dialog-field-v356 .custom-select-shell' in racks

    # Manage Items receives one readable text scale without changing functional IDs.
    assert '#manageItemsPanel .manage-items-workspace-v355 { font-size: 12px; }' in bays
    assert '#manageItemsPanel .manage-inventory-job-identity-v355 strong { font-size: 15px !important; }' in bays
    assert '#manageItemsPanel .manage-inventory-line-v355 strong { font-size: 12px !important; }' in bays



def test_v0360_dark_mode_history_is_preserved_after_removal() -> None:
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v0.360 - Home Greeting, Lighter Stage Progress, and Per-User Dark Mode" in changelog
    assert "Appearance" in changelog


def test_v0361_dark_mode_history_is_preserved() -> None:
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v0.361 - Today's Delivery Command Surface and Dark Mode 2.0" in changelog
    assert "Dark mode" in changelog


def test_v0362_compact_home_history_is_preserved() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    home_markup = html[html.index('<!-- SECTION: Home operations hub'):html.index('<!-- SECTION: Dedicated statistics', html.index('<!-- SECTION: Home operations hub'))]
    assert 'home-stage-command-v362' in home_markup
    assert 'home-stage-simple-header-v362' in home_markup
    assert 'home-stage-greeting-v362' in home_markup
    assert 'home-stage-date-simple-v362' in home_markup
    assert 'home-stage-grid-v362' in home_markup
    assert 'homeStageSummary: document.getElementById("homeStageSummary")' not in app
    assert "## v0.362 - Compact Home Progress and Dark Navy Mode 3.0" in changelog
    assert "v0.362 Compact Today's Delivery + Forward View restoration" in home



def test_v0364_home_light_blue_and_forward_view_rebalance() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.364 - Lighter Today Surface, Larger Greeting, and Forward View Rebalance' in changelog

    assert 'v0.364 Home color alignment and Forward View rebalance' in home
    assert 'linear-gradient(120deg, #eaf3fb 0%, #dceaf7 56%, #cfdfef 100%)' in home
    assert 'font-size: 30px !important;' in home
    assert 'font-size: 23px !important;' in home
    assert 'min-height: 91px !important;' in home
    assert 'background: linear-gradient(180deg, #ffffff 0%, #f3f8fd 100%) !important;' in home

def test_v0365_home_first_view_and_destination_icon_cards() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.365 - Home First-View Hierarchy, Forward View Order, and Destination Icon Cards' in changelog

    home_markup = html[html.index('<!-- SECTION: Home operations hub'):html.index('<!-- SECTION: Dedicated statistics', html.index('<!-- SECTION: Home operations hub'))]
    assert '<h1 class="home-time-greeting-v360 home-stage-greeting-v362" id="homeGreeting">' in home_markup
    assert 'home-stage-command-v365' in home_markup
    assert 'home-forward-view-v365' in home_markup
    assert 'home-destination-section-v365' in home_markup
    assert 'home-destination-cards-v365' in home_markup
    assert home_markup.index('home-stage-command-v365') < home_markup.index('home-forward-view-v365') < home_markup.index('home-destination-section-v365') < home_markup.index('homeDeliveryExplorer')

    for token in [
        'v0.365 Home first-view hierarchy and destination cards',
        'font-size: 38px !important;',
        'font-size: 27px !important;',
        '.home-stage-command-v365 .today-stage-name b',
        '.home-destination-cards-v365 .home-quick-action-icon-v358',
        'grid-template-columns: repeat(6, minmax(145px, 1fr));',
    ]:
        assert token in home



def test_v0366_home_matches_reference_layout() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.366 - Screenshot-Matched Home Operations Hub' in changelog

    markup = html[html.index('<!-- SECTION: Home operations hub'):html.index('<!-- SECTION: Dedicated statistics')]
    for token in ['home-reference-v366', 'home-stage-reference-v366', 'home-forward-reference-v366', 'home-destination-reference-v366', 'home-delivery-library-v366']:
        assert token in markup

    for token in [
        'v0.366 Screenshot-led Home reference layout',
        'grid-template-columns: repeat(4, minmax(0, 1fr)) !important;',
        'min-height: 108px !important;',
        'min-height: 150px !important;',
        '.home-stage-reference-v366 .today-stage-name > i::before',
        '.home-destination-reference-v366 .home-quick-action-v358::after',
        '.home-delivery-library-v366 .home-finder-toolbar-v358 .search-box',
    ]:
        assert token in home


def test_v0367_home_delivery_library_progress_refinement() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.367 - Home Delivery Library Progress and Interaction Refinement' in changelog

    assert 'The next delivery dates, workload, open pieces, and current completion.' not in html
    assert 'Jump straight to the tools used most often on the floor.' not in html
    assert 'v0.367 Home refinement' in home
    assert 'min-height: 130px !important;' in home
    assert 'right: -16px !important;' in home
    assert '.delivery-list-card-v367' in home
    assert '.delivery-stage-icon-v367' in home
    assert '.delivery-stage-progress-track-v367' in home
    assert '.home-library-date-v367' in home
    assert 'delivery-list-card delivery-list-card-v367' in app
    assert 'delivery-stage-progress-track-v367' in app
    assert 'home-library-date-v367' in app
    assert '<span class="home-library-date-v367"><small>${escapeHtml(weekday)}</small>' in app
    assert 'delivery-card-metrics' not in app[app.index('function deliveryListCard'):app.index('function renderTodayProgress')]


def test_v0368_delivery_library_header_stage_cards_and_inbound_presentation() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.368 - Delivery Library Header, Stage Cards, and Inbound Presentation' in changelog

    # Date summaries own a large progress bar and a purpose-built piece summary.
    assert 'home-date-progress-track-v368' in home
    assert 'height: 17px;' in home
    assert 'home-date-piece-summary-v368' in home
    assert 'Total pieces' in app

    # Expanded stages use one stable identity -> progress -> action layout.
    assert 'delivery-list-card-v368' in home
    assert 'grid-template-columns: minmax(205px, .72fr) minmax(360px, 1.45fr) 104px !important;' in home
    assert 'delivery-stage-identity-v368' in app
    assert 'delivery-stage-progress-track-v368' in app
    assert 'delivery-stage-open-v368' in app

    # Received remains the internal category, while Home presents it as Inbound.
    assert 'if (category === "received") return labels.receivingStage;' in app
    assert '["Inbound", "Entrada"]' in app
    assert 'Inbound mirrors Outbound diagonally' in home
    assert "M7 5 17 15.1V8h2v11H8v-2h7.1L5 7 7 5Z" in home



def test_v0369_delivery_library_stage_progress_is_contained_under_title() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in html
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.369 - Contained Delivery Library Stage Progress' in changelog

    card_block = app[app.index('function deliveryListCard'):app.index('function renderTodayProgress')]
    assert 'delivery-list-card-v369' in card_block
    assert 'delivery-stage-identity-v369' in card_block
    assert 'delivery-stage-copy-v369' in card_block
    # Progress now lives inside the stage copy so it is underneath the title.
    assert card_block.index('delivery-stage-copy-v369') < card_block.index('delivery-stage-progress-v369') < card_block.index('delivery-stage-open-v369')

    assert 'v0.369 Expanded Delivery Library stage containment' in home
    assert '.home-delivery-library-v366 .delivery-list-card-v369' in home
    assert 'grid-template-columns: minmax(0, 1fr) auto !important;' in home
    assert '.home-delivery-library-v366 .delivery-stage-progress-v369' in home
    assert 'width: 100%;' in home
    assert 'max-width: 100%;' in home



def test_v0374_supplied_home_header_image_integration() -> None:
    """v0.374 uses the approved PNG in the Home hero instead of CSS-drawn art."""
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'static/css/home.css?v=20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'home-delivery-header-v0374.png' in home
    assert 'background-size: contain !important' in home
    assert 'Current maintained release: **v0.527**' in readme
    assert (ROOT / 'static/images/home-delivery-header-v0374.png').is_file()


def test_v0375_transparent_home_artwork_and_page_entry_motion() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'static/css/home.css?v=20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert 'home-delivery-header-v0375-transparent.png' in home
    assert 'appPageEnterV0375' in home
    assert '.page-view.is-page-entering-v0375' in home
    assert 'prefers-reduced-motion: reduce' in home
    assert 'preparePageEnterTransitionV0376' in app
    assert 'activePageView' in app
    assert (ROOT / 'static/images/home-delivery-header-v0375-transparent.png').is_file()


def test_v0376_stable_fade_bay_entry_and_larger_home_artwork() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/home.css?v=20260908-v0.510' in index
    assert 'static/css/bays.css?v=20260908-v0.513' in index
    assert 'aria-label="Application version 0.527"' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.376 - Stable Page Fades, Bay Transit Entry, and Larger Home Artwork' in changelog

    assert 'v0.376 Stable opacity-only page transitions + larger Home artwork' in home
    assert '.page-view.is-page-fading-v0376' in home
    # Keep the v0.376 page-transition block opacity-only. Later feature-specific
    # animations (including v0.456 Delivery Library expansion) may use transforms.
    v376_home = home[home.index('v0.376 Stable opacity-only page transitions'):home.index('v0.377 Rebalanced faded Home artwork')]
    assert 'transform: translateY' not in v376_home
    assert 'width: min(1050px, 69vw) !important;' in home
    assert 'height: 250px !important;' in home
    assert '#bayFlowPanel.is-route-fading-v0376' in home
    assert 'prefers-reduced-motion: reduce' in home

    assert 'preparePageEnterTransitionV0376(view)' in app
    assert 'view.hidden = false;' in app
    assert 'startPageEnterTransitionV0376(activePageView)' in app
    assert 'els.bayFlowPanel?.classList.remove("is-entering");' in app
    assert app.index('els.bayFlowPanel?.classList.remove("is-entering");') < app.index('restartBayTruckAnimation();', app.index('if (page === "bays")'))
    assert 'revealBayFlowEntryV0376();' in app
    assert '#bayFlowPanel:not(.is-entering) .transit-moving-truck' in bays



def test_v0377_rebalanced_faded_home_artwork_overlap() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/home.css?v=20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.377 - Rebalanced Background Home Artwork' in changelog

    assert 'v0.377 Rebalanced faded Home artwork with gentle stage overlap' in home
    assert 'width: min(800px, 56vw) !important;' in home
    assert 'height: 210px !important;' in home
    assert 'opacity: .52 !important;' in home
    assert 'min-height: 145px !important;' in home
    assert '.home-stage-reference-v366 .home-stage-grid-v362' in home
    assert 'z-index: 2 !important;' in home[home.index('v0.377 Rebalanced faded Home artwork'): ]
    assert 'home-delivery-header-v0375-transparent.png' in home



def test_v0378_forward_view_progress_and_piece_summary_polish() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/home.css?v=20260908-v0.510' in index
    assert 'static/js/app.js?v=20260910-v0.527' in index
    assert 'aria-label="Application version 0.527"' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.378 - Forward View Progress and Piece Summary Polish' in changelog

    block = app[app.index('function renderHomeHub()'):app.index('function focusHomeDeliveryDate')]
    assert 'home-timeline-card-v378' in block
    assert 'home-timeline-progress-v378' in block
    assert 'home-timeline-pieces-v378' in block
    assert 'home-timeline-summary-v378' in block
    assert '<small>open</small>' not in block
    assert 'stats.remainingQty' not in block
    assert 'Number(airport.percent || 0) > 0' in block

    assert 'v0.378 Forward View progress-first card polish' in home
    assert '.home-timeline-card-v378' in home
    assert 'height: 18px !important;' in home
    assert '.home-timeline-pieces-v378' in home
    assert 'font-size: 17px !important;' in home




def test_v0380_home_stage_actions_soft_glass_racks_filters_and_contrast() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.380 - Home Stage Actions, Softer Glass Colors, Rack Glass Rows, and Filter Readability' in changelog

    today = app[app.index('function renderTodayProgress'):app.index('function renderHomeStageFilter')]
    # v0.381 intentionally removes the temporary v0.380 Open Stage affordance;
    # the rest of the v0.380 glass/readability work remains regression-covered.
    assert 'today-stage-open-v380' not in today
    assert '<span>Open stage</span>' not in today

    assert '--glass-type-accent:rgba(${red},${green},${blue},.50)' in app
    assert '--glass-type-soft:rgba(${red},${green},${blue},.024)' in app
    assert '--glass-type-soft-strong:rgba(${red},${green},${blue},.052)' in app
    assert 'v0.380 Restrained Lookup Manager glass language and contrast cleanup' in styles
    assert 'background: linear-gradient(135deg, var(--glass-type-soft-strong) 0%, #fff 80%) !important;' in styles

    assert 'width: min(990px, calc(100vw - 54px)) !important;' in scan
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr)) !important;' in scan
    assert 'All Glass Types' in app
    assert 'data-glass-filter="all"].is-active' in scan
    assert 'color: #fff !important;' in scan[scan.index('data-glass-filter="all"].is-active'):]

    rack = app[app.index('const renderRackItem'):app.index('const renderRackItems')]
    assert 'rack-item-glass-v380 glass-tone-inline' in rack
    assert '<small>Glass Type</small>' in rack
    assert 'body .rack-item.glass-tone-card' in styles

    bay = app[app.index('function renderBaySlotButton'):app.index('function bayTypeSections')]
    assert 'glass-tone-bay-v380' not in bay
    assert 'glassToneAttributes(bayGlass)' not in bay
    assert 'v0.380 Legacy glass-color replacement and Bay contrast polish' in bays
    assert '--glass-accent: var(--glass-type-accent) !important;' in bays
    assert 'border-left-color: #b9c9d7 !important;' not in bays
    assert 'button:hover:not(:disabled),' in bays
    assert 'color: #fff !important;' in bays[bays.index('Known dark-hover contrast repair'):]


def test_v0381_bay_restore_rack_glass_all_scans_and_selection_polish() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.381 - Home Stage Cleanup, Bay Color Restore, Rack/Scan Glass Identity, and Selection Polish' in changelog

    today = app[app.index('function renderTodayProgress'):app.index('function renderHomeStageFilter')]
    assert 'today-stage-open-v380' not in today
    assert 'v0.380 Today\'s Delivery compact Open Stage affordances' not in home

    physical_bay = app[app.index('function renderBaySlotButton'):app.index('function bayTypeSections')]
    selected_bay = app[app.index('function selectedBayJobItemsHtml'):app.index('function renderBaySlotButton')]
    assert 'glass-tone-bay-v380' not in physical_bay
    assert 'glassToneAttributes(bayGlass)' not in physical_bay
    assert 'class="glass-tone-inline"' not in selected_bay
    assert 'border-left-color: #b9c9d7 !important;' not in bays

    rack_details = app[app.index('function compactRackItemHtml'):app.index('function rackTransferOptions')]
    assert 'rack-modal-line-v381 rack-modal-line-v382' in rack_details
    assert 'rack-modal-glass-type-v381 rack-modal-glass-type-v382 glass-tone-inline' in rack_details
    assert '<small>Glass Type</small>' in rack_details
    assert 'v0.381 Rack detail glass identity and Print / Export contrast cleanup' in styles

    assert 'label: "All Glass Types"' in app
    assert '.print-filter-chip-v197.is-glass-all:has(input:checked)' in styles
    assert 'background: linear-gradient(180deg, #316faa 0%, #245d92 100%) !important;' in styles
    assert 'data-glass-filter="all"].is-active > span' in scan
    assert 'background: rgba(255,255,255,.16) !important;' in scan

    assert 'width: 100% !important;' in scan[scan.index('v0.381 Scan selection, equal glass cells'):]
    assert 'all-scans-col-glass' in app
    assert '<th>Glass Type</th>' in app
    assert 'all-scans-glass-type-v381 glass-tone-inline' in app
    assert 'all-scans-col-glass { width: 150px; }' in scan

    selection = app[app.index('const row = event.target.closest("#listRows tr[data-id], #mobileListCards [data-id]")'):]
    assert 'isClearingCurrentSelection' in selection
    assert 'state.selectedId = isClearingCurrentSelection ? null : clickedId;' in selection
    assert 'outline: 1px solid rgba(84, 137, 198, .38) !important;' in scan



def test_v0382_scan_selection_filters_rack_details_bay_cards_and_forward_cleanup() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.382 - Stable Scan Selection, Glass Filter Clarity, Rack Detail Cleanup, and Bay Stage Polish' in changelog

    backend = app[app.index('function applyBackendPayload'):app.index('async function loadDeliveryLists')]
    assert 'selectionFallbackId = ""' in backend
    assert 'fallbackStillExists' in backend
    assert 'state.lastScan?.item?.id || null' not in backend
    scan_process = app[app.index('const payload = await fetchJson("/api/scans"'):app.index('function submitManualScan')]
    assert 'selectionFallbackId: payload.lastScan?.ok ? payload.lastScan?.item?.id : ""' in scan_process
    assert 'async function activateList(listId, navigate = true, { selectionFallbackId = "", stageSpecific = false } = {})' in app
    assert 'selectionFallbackId: result.ok ? result.lastScan?.item?.id : ""' in app

    # v0.465 replaces the old app-blue check badge with the saved glass color.
    assert 'v0.465 Scan glass-filter selection uses the saved glass color' in scan
    selection_block = scan[scan.index('v0.465 Scan glass-filter selection uses the saved glass color'):scan.index('v0.385 Rack selector parity')]
    assert 'content: none !important;' in selection_block
    assert 'var(--glass-type-color) 100%) !important;' in selection_block

    rack = app[app.index('function compactRackItemHtml'):app.index('function rackTransferOptions')]
    assert 'rack-modal-line-v381 rack-modal-line-v382' in rack
    assert 'glass-tone-card' not in rack
    assert '<small>Customer</small>' in rack
    assert 'rack-modal-glass-type-v382 glass-tone-inline' in rack
    assert 'v0.382 Individual Rack detail readability' in styles
    assert 'background: transparent !important;' in styles[styles.index('v0.382 Individual Rack detail readability'):]

    bay_flow = app[app.index('function renderBayRouteFlow'):app.index('function transitManifestRowHtml')]
    assert 'Open Stage' in bay_flow
    assert 'Open list' not in bay_flow
    assert 'v0.382 Bay Map stage-card icon and action polish' in bays
    assert '--bay-stage-icon' in bays

    home_timeline = app[app.index('function homeAirportStagingStats'):app.index('function focusHomeDeliveryDate')]
    assert 'Staging source' not in home_timeline
    assert 'home-timeline-summary-v382' in home_timeline
    assert 'v0.382 Forward View source-label cleanup' in home


def test_v0383_rack_print_glass_and_forward_view_polish() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.383 - Rack Detail Balance, Print Glass Selection, and Forward View Layout' in changelog

    rack = app[app.index('function compactRackItemHtml'):app.index('function rackTransferOptions')]
    assert '<small>Delivery</small>' not in rack
    assert 'rack-modal-job-v383' in rack
    assert 'rack-modal-glass-type-v383' in rack
    assert 'minmax(220px, 1.65fr)' in styles
    assert 'v0.383 Rack detail balance and unmistakable Print / Export glass selection' in styles

    assert 'v0.465 Print / Export glass selection' in styles
    print_selection = styles[styles.index('v0.465 Print / Export glass selection'):styles.index('All Glass Types remains visually stronger')]
    assert '.print-filter-chip-v197.glass-tone-chip:has(input:checked)::after' in print_selection
    assert 'content: none !important;' in print_selection
    assert 'var(--glass-type-color) 100%) !important;' in print_selection
    assert '.print-filter-chip-v197.is-glass-all:has(input:checked)' in styles
    assert 'color: #fff !important;' in styles[styles.index('v0.383 Rack detail balance'): ]

    timeline = app[app.index('function renderHomeHub'):app.index('function focusHomeDeliveryDate')]
    assert 'home-timeline-stage-count-v383' in timeline
    assert 'home-timeline-summary-v383' in timeline
    assert 'home-timeline-pieces-v383' in timeline
    assert 'Airport Rd pieces' not in timeline
    assert 'v0.383 Forward View stage count and compact piece total' in home
    assert 'justify-content: flex-end !important;' in home[home.index('v0.383 Forward View stage count'): ]


def test_v0384_compact_forward_view_and_left_piece_total() -> None:
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.384 - Compact Forward View and Left-Aligned Piece Total' in changelog

    assert 'v0.384 Compact Forward View and left-aligned piece total' in home
    v384 = home[home.index('v0.384 Compact Forward View and left-aligned piece total'):]
    assert 'min-height: 119px !important;' in v384
    assert 'justify-content: flex-start !important;' in v384
    assert 'margin-left: 0 !important;' in v384
    assert 'margin-right: auto !important;' in v384

    timeline = app[app.index('function renderHomeHub'):app.index('function focusHomeDeliveryDate')]
    assert 'home-timeline-stage-count-v383' in timeline
    assert 'home-timeline-pieces-v383' in timeline
    assert 'Airport Rd pieces' not in timeline



# Website Version 3 functional regressions retained during the v0.423 integration.

def test_v328_admin_superseded_and_automation_control_polish() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    assert '"supersededOrders": ({"superseded_order_review"}, ("superseded_order_",))' in store
    assert 'action.startsWith("superseded_order_")' in app
    assert 'await loadModalActionHistory("supersededOrders", "admin").catch(() => {});' in app
    assert 'superseded-review-recommendation-v328' in app
    assert 'superseded-review-removal-choice-v328' in app
    assert 'Approve removal of order ${escapeHtml(selectedRemoveOrder)}' in app
    assert '.superseded-review-recommendation-v328' in admin
    assert '.superseded-review-choice-v328' in admin

    assert 'automation-schedule-row-v328' in app
    assert '.automation-schedule-row-v328' in admin
    assert 'automation-status-workspace-v328' in app
    assert '.automation-log-panel-v332' in admin
    assert '.automation-log-viewport-v332' in admin

    assert 'page_mode: str = "rows"' in automation
    assert 'clean_page_mode not in {"rows", "business_week", "control_center"}' in automation
    assert 'week_groups: dict[date, list[dict[str, Any]]]' in automation
    assert 'page_mode=params.get("pageMode", ["rows"])[0]' in server
    assert 'pageMode: "control_center"' in app
    assert 'id="importHistoryPageSize"' not in app
    assert '>Previous</button>' in app
    assert '>Next</button>' in app


def test_v328_business_week_import_history_paging_keeps_complete_week() -> None:
    import importlib.util

    module_path = ROOT / "backend" / "automation_control.py"
    specification = importlib.util.spec_from_file_location("v328_automation_control", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    controller_class = module.DeliveryAutomationController
    controller = controller_class.__new__(controller_class)
    controller.scanner_store = None
    database_items = [
        {"id": 1, "runId": "run-tuesday", "runStartedAt": "2026-08-18T13:00:00+00:00", "importedAt": "2026-08-18T13:00:01+00:00", "deliveryDate": "2026-08-19", "sourceName": "a.xlsx", "classification": "updated"},
        {"id": 2, "runId": "run-tuesday", "runStartedAt": "2026-08-18T13:00:00+00:00", "importedAt": "2026-08-18T13:00:02+00:00", "deliveryDate": "2026-08-20", "sourceName": "b.xlsx", "classification": "no_changes"},
        {"id": 3, "runId": "run-monday", "runStartedAt": "2026-08-17T12:00:00+00:00", "importedAt": "2026-08-17T12:00:01+00:00", "deliveryDate": "2026-08-21", "sourceName": "c.xlsx", "classification": "new"},
        {"id": 4, "runId": "run-friday", "runStartedAt": "2026-08-21T12:00:00+00:00", "importedAt": "2026-08-21T12:00:01+00:00", "deliveryDate": "2026-08-24", "sourceName": "d.xlsx", "classification": "updated"},
        {"id": 5, "runId": "run-prior", "runStartedAt": "2026-08-14T12:00:00+00:00", "importedAt": "2026-08-14T12:00:01+00:00", "deliveryDate": "2026-08-17", "sourceName": "e.xlsx", "classification": "no_changes"},
    ]
    controller._database_import_history_items = lambda: database_items
    controller._latest_automation_import_items = lambda: ([], {})
    controller._archived_automation_import_items = lambda: []
    controller._history_search_text = lambda item: " ".join(str(value) for value in item.values()).lower()

    current_week = controller.get_import_history(page=1, page_mode="business_week")
    prior_week = controller.get_import_history(page=2, page_mode="business_week")
    legacy_rows = controller.get_import_history(page=1)

    assert current_week["weekStart"] == "2026-08-17"
    assert current_week["weekEnd"] == "2026-08-21"
    assert current_week["pageItemCount"] == 4
    assert {row["id"] for row in current_week["recentImports"]} == {1, 2, 3, 4}
    assert prior_week["weekStart"] == "2026-08-10"
    assert prior_week["pageItemCount"] == 1
    assert legacy_rows["pageMode"] == "rows"
    assert legacy_rows["weekStart"] == ""
    assert legacy_rows["weekEnd"] == ""


def test_v329_admin_log_history_and_superseded_evidence_refinement() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    assert 'automationLog.addEventListener("scroll"' in app
    assert 'distanceFromBottom > 48' in app
    assert 'automationLogFollow.checked = false' in app
    assert 'scrollbar-gutter: stable;' in admin
    assert 'overflow-y: scroll;' in admin

    assert 'day.open = false;' in app
    assert 'category.open = false;' in app
    assert 'run.open = false;' in app
    assert 'label: "No New / Updated Lists"' in app
    assert 'label: "New / Updated / Exceptions"' in app
    assert '.automation-history-category' in admin

    recommendation_index = app.index('superseded-review-recommendation-v328')
    evidence_index = app.index('<details class="superseded-review-evidence-details-v328" open>', recommendation_index)
    choice_index = app.index('<div class="superseded-review-removal-choice-v328"', evidence_index)
    assert recommendation_index < evidence_index < choice_index
    assert '<summary>Item evidence <span>' in app


def test_v330_superseded_dimensions_log_reachability_and_admin_launchers() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Superseded evidence must use the same 1/32-inch source convention as the
    # maintained SQL workbook formatter without mutating stored review payloads.
    assert 'const SUPERSEDED_DIMENSION_UNITS_PER_INCH = 32;' in app
    assert 'function formatSupersededDimensionUnit' in app
    assert 'return `${formatSupersededDimensionUnit(widthUnits, unitsPerInch)} × ${formatSupersededDimensionUnit(heightUnits, unitsPerInch)}`;' in app
    assert 'const dimensions = supersededReviewDimensions(item);' in app
    assert 'source units' not in app[app.index('function supersededReviewItemRows'):app.index('function supersededOrderReviewCardHtml')]

    # The live log scrolls after layout, keeps wheel input local, and reserves
    # bottom space so the final wrapped line can be fully scrolled into view.
    assert 'function scrollLiveAutomationLogToNewest()' in app
    assert 'window.requestAnimationFrame(() =>' in app
    assert 'automationLog.addEventListener("wheel"' in app
    assert 'if (name === "status" && autoFollowLog)' in app
    assert 'event.stopPropagation();' in app
    assert 'padding: 14px 16px 8px;' in admin
    assert 'scroll-padding-block: 14px 42px;' in admin
    assert 'height: 34px;' in admin

    # Every dashboard control that opens an Admin GUI uses the shared launcher
    # marker, including the Automation Control Center entry point.
    assert index.count('data-admin-gui-launch') == 13
    # v0.349 removes the last dynamic overview launcher; all dashboard Admin GUI
    # launchers now live in the maintained index markup and share the marker there.
    assert app.count('data-admin-gui-launch') == 0
    assert 'id="folderImportBtn" class="link-button admin-automation-link" data-admin-gui-launch' in index
    assert '#adminPage [data-admin-gui-launch] {' in admin
    assert '#adminPage [data-admin-gui-launch]:hover:not(:disabled)' in admin
    assert '.superseded-review-open.has-pending-review[data-admin-gui-launch]' in admin


def test_v331_live_log_viewport_and_subtle_launcher_highlight() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # v0.331 established that the Status grid owns the remaining height. v0.332
    # supersedes the old details/pre implementation with a dedicated child
    # viewport while preserving that bounded final grid row.
    assert 'grid-template-rows: auto auto auto minmax(0, 1fr);' in admin
    assert '.automation-log-panel-v332 {' in admin
    assert '.automation-log-viewport-v332 {' in admin
    assert '.automation-log-details' not in admin

    # Launcher polish must be a stationary fade, not the previous sweeping sheen.
    launcher_start = admin.index('#adminPage [data-admin-gui-launch]::after')
    launcher_end = admin.index('#adminPage [data-admin-gui-launch]:active:not(:disabled)', launcher_start)
    launcher_effect = admin[launcher_start:launcher_end]
    assert 'opacity: 0.18;' in launcher_effect
    assert 'opacity: 0.34;' in launcher_effect
    assert 'transition: opacity 160ms ease;' in launcher_effect
    assert 'translateX(' not in launcher_effect


def test_v332_bounded_live_log_and_full_updater_diagnostics() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The log is now a true bounded viewport. Text content no longer owns
    # scrolling, and an explicit end marker keeps the final wrapped line clear
    # of the modal edge.
    assert 'class="automation-log-panel-v332"' in app
    assert 'id="automationLogViewport"' in app
    assert 'id="automationLogEnd"' in app
    assert 'id="automationJumpLogBtn"' in app
    assert '<details class="automation-log-details"' not in app
    assert 'function scrollLiveAutomationLogToNewest()' in app
    assert app.count('window.requestAnimationFrame(() =>') >= 2
    assert 'automationLogResizeObserver = new ResizeObserver' in app
    assert 'distanceFromBottom > 48' in app
    assert '.automation-log-panel-v332 {' in admin
    assert 'grid-template-rows: auto auto minmax(0, 1fr);' in admin
    assert '.automation-log-viewport-v332 {' in admin
    assert 'overflow-y: scroll;' in admin
    assert 'scrollbar-gutter: stable;' in admin
    assert '.automation-log-end-v332 {' in admin
    assert 'height: 34px;' in admin
    assert '.automation-log-details' not in admin

    # Controller diagnostics are written into the exact same per-run log before
    # PowerShell starts, and the runner preserves those preamble lines.
    assert 'def _append_run_log_line' in automation
    assert 'CONTROLLER | {message}' in automation
    assert 'Web request accepted.' in automation
    assert 'Installed runtime synchronization completed.' in automation
    assert 'Launching PowerShell process.' in automation
    assert 'PowerShell process exited with code' in automation
    assert 'if (-not (Test-Path -LiteralPath $requestedLogPath -PathType Leaf))' in runner
    assert '$script:PendingLogLines = New-Object System.Collections.Generic.List[string]' in runner
    assert '$script:PendingLogLines.ToArray()' in runner

    # Every major updater phase emits ordered STEP records, while DEBUG records
    # expose timing, process, file, source-selection, retention, and import detail.
    assert 'ValidateSet("DEBUG", "INFO", "WARN", "ERROR")' in runner
    assert 'function Write-AutomationStep' in runner
    assert 'function Write-AutomationDebug' in runner
    assert 'STEP {0:D2}' in runner
    assert 'Launching Python subprocess.' in runner
    assert 'Python subprocess finished.' in runner
    assert 'PowerShell automation runner accepted the request' in runner
    assert 'Reading and validating automation configuration.' in runner
    assert 'Testing A+W SQL connectivity and mapped source columns.' in runner
    assert 'Processing A+W export for delivery date' in runner
    assert 'Running scanner verification/import for the selected SQL dates.' in runner
    assert 'Applying automation retention cleanup.' in runner
    assert 'Writing the final run summary and immutable history record.' in runner
    assert 'Preparing parameterized A+W query for' in runner
    assert 'A+W SQL query completed for' in runner
    assert 'Computed authoritative source fingerprint for' in runner
    assert 'Workbook/state comparison for' in runner
    assert 'Staging payload ready for' in runner
    assert 'Published workbook verification for' in runner
    assert 'Cleaned staging files for' in runner
    assert 'Automation runner exiting.' in runner

    # The Python importer also streams fine-grained reconciliation progress so
    # those internal operations appear in the live PowerShell/controller log.
    assert 'def progress(message: str) -> None:' in importer
    assert 'print(f"[IMPORT] {message}", flush=True)' in importer
    assert 'Loading maintained scanner configuration and backend store modules.' in importer
    assert 'Synchronizing superseded-order review candidates' in importer
    assert 'Authoritative scanner reconciliation starting' in importer
    assert 'Writing normalized importer result' in importer
    assert 'Importer finished in' in importer


def test_v333_route_history_cross_stage_delete_loading_and_preview_polish() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Import History uses the same maintained route vocabulary as Delivery List
    # Management and chooses Outbound as the authoritative Airport/all-order copy.
    assert 'const DELIVERY_ROUTE_GROUP_DEFINITIONS = Object.freeze([' in app
    assert 'function condenseImportStageSummariesByRoute' in app
    assert 'definition.key === "airport" && category === "outbound"' in app
    assert 'All orders for this delivery date' in app
    assert 'automation-import-route-table-v333' in app
    assert 'Before</span>' in app
    assert 'Changes</span>' in app
    assert 'After</span>' in app
    assert '.automation-import-route-table-v333 {' in admin

    # Edit Delivery Lists opens before the catalog request finishes and both the
    # catalog shell and selected stage show explicit loading feedback.
    immediate_open = 'openAdminModal(modalKind, { body: adminDeliveryListModalLoadingHtml() });'
    catalog_call = 'loadAdminDeliveryListCatalogPage(1, "", { showLoading: false })'
    handler_start = app.index('} else if (modalKind === "deliveryLists" || modalKind === "deliveryActions") {')
    handler_end = app.index('} else {\n        openAdminModal(modalKind);', handler_start)
    handler = app[handler_start:handler_end]
    assert immediate_open in handler
    assert catalog_call in handler
    assert 'loadDeliveryLists(state.activeListId)' not in handler
    assert handler.index(immediate_open) < handler.index(catalog_call)
    assert 'Loading delivery lists...' in app
    assert 'Loading editable rows...' in app

    # Deletion follows the existing sibling resolver so one logical order/item
    # cannot survive in another stage for the same delivery date.
    delete_start = store.rindex('    def delete_line_item(self, line_item_id: str, user: str) -> dict[str, Any]:')
    delete_end = store.index('    def delete_delivery_list(', delete_start)
    delete_body = store[delete_start:delete_end]
    assert 'siblings = self.manual_edit_sibling_rows(con, row)' in delete_body
    assert 'DELETE FROM line_items WHERE id IN' in delete_body
    assert 'deletedLineItemCount' in delete_body
    assert 'affectedListIds' in delete_body
    assert 'Delete order item from every stage?' in app
    assert 'Delete From All Stages' in app

    # Whole-list preview disclosure follows route count, while the order/item
    # content is simplified to the requested left-to-right hierarchy.
    assert 'const populatedLocationCount = [...locationItemsByKey.values()].filter((rows) => rows.length > 0).length;' in app
    assert 'const routeStartsOpen = populatedLocationCount === 1;' in app
    preview_start = app.index('function deliveryListUpdatePreviewHtml(')
    preview_end = app.index('function initializeDeliveryListUpdatePreviewControls()', preview_start)
    preview = app[preview_start:preview_end]
    for label in ('Order Nr.', 'Job Nr.', 'Customer', 'Flags', 'Item Nr.', 'Dimensions', 'Quantity'):
        assert label in preview
    assert 'delivery-update-preview-order-totals-v311' not in preview
    assert 'delivery-update-preview-item-change-v311' not in preview
    assert '<small>Glass Type</small>' in preview
    assert 'delivery-update-preview-order-identity-v311' in admin
    assert 'grid-template-columns: minmax(105px, .65fr) minmax(120px, .8fr) minmax(220px, 1.65fr) minmax(120px, .75fr);' in admin
    assert 'grid-template-columns: minmax(68px, .55fr) minmax(150px, 1.35fr) minmax(125px, 1.25fr) minmax(58px, .45fr);' in admin


def test_v334_automation_filters_icons_and_weekly_edit_paging() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'data-portable-support-link-v355' in index

    # Automation options use one crisp vector icon system and Import History
    # Refresh keeps its icon while its text/loading state changes.
    assert '.automation-tab-icon::before {' in admin
    assert '.automation-card-icon::before {' in admin
    assert 'mask-image: url(' in admin
    assert 'automation-refresh-button-v334' in app
    assert 'data-import-history-refresh-label' in app
    assert 'function setImportHistoryRefreshButtonState' in app
    assert '#importHistoryRefreshBtn:hover:not(:disabled) .automation-refresh-icon-v334' in admin

    # Search is multi-token and route-aware, date bounds are normalized, and
    # stale browser requests are aborted rather than overwriting newer filters.
    assert 'query_terms = [term for term in clean_query.split() if term]' in automation
    assert 'if not all(term in search_text for term in query_terms):' in automation
    for route_name in ('airport road', 'indian trail', 'greenville', 'customer pickup', 'deliver to customer'):
        assert route_name in automation
    assert 'function normalizeImportHistoryDateRange' in app
    assert 'importHistoryAbortController?.abort();' in app
    assert 'signal: importHistoryAbortController.signal' in app

    # Edit Delivery Lists pages by business week and consistently uses compact
    # numeric dates; the selected stage and manual row results are also paged.
    assert 'paginateByWeek: true' in app
    assert 'deliveryDateGroupsByBusinessWeek(listsByDeliveryDate(sortedRows))' in app
    assert 'data-admin-delivery-week-page' in app
    assert 'admin-delivery-week-v334' in app
    assert 'formatNumericDeliveryDate(group.date)' in app
    assert 'return `${formatNumericDeliveryDate(list.deliveryDate)} - ${list.stage || "Stage"}`;' in app
    assert 'manual-edit-search-button-v334' in app
    assert 'data-manual-edit-page' in app
    assert 'async function goToManualEditPage(page)' in app
    assert 'data-manual-edit-load-more' not in app


def test_v334_import_history_search_and_date_filters_work_together() -> None:
    import importlib.util

    module_path = ROOT / "backend" / "automation_control.py"
    specification = importlib.util.spec_from_file_location("v334_automation_control", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    controller_class = module.DeliveryAutomationController
    controller = controller_class.__new__(controller_class)
    controller.scanner_store = None
    controller._database_import_history_items = lambda: [
        {
            "id": 33401,
            "runId": "run-airport",
            "runStartedAt": "2026-08-14T10:00:00+00:00",
            "importedAt": "2026-08-14T10:00:10+00:00",
            "deliveryDate": "2026-08-14",
            "sourceName": "Delivery List 08-14-2026.xlsx",
            "classification": "updated",
            "stageSummaries": [{"stage": "Outbound", "scanner": "Airport Rd"}],
        },
        {
            "id": 33402,
            "runId": "run-it",
            "runStartedAt": "2026-08-15T10:00:00+00:00",
            "importedAt": "2026-08-15T10:00:10+00:00",
            "deliveryDate": "2026-08-15",
            "sourceName": "Delivery List 08-15-2026.xlsx",
            "classification": "no_changes",
            "stageSummaries": [{"stage": "Receiving", "scanner": "Indian Trail"}],
        },
    ]
    controller._latest_automation_import_items = lambda: ([], {})
    controller._archived_automation_import_items = lambda: []

    airport = controller.get_import_history(
        page=1,
        page_size=20,
        query="Airport 8/14",
        date_from="2026-08-14",
        date_to="2026-08-14",
    )
    indian_trail = controller.get_import_history(
        page=1,
        page_size=20,
        query="Indian Trail 8/15",
        date_from="2026-08-15",
        date_to="2026-08-15",
    )
    outside_range = controller.get_import_history(
        page=1,
        page_size=20,
        query="Airport",
        date_from="2026-08-15",
        date_to="2026-08-15",
    )

    assert [item["id"] for item in airport["imports"]] == [33401]
    assert [item["id"] for item in indian_trail["imports"]] == [33402]
    assert outside_range["imports"] == []


def test_v335_import_activity_filters_three_week_edit_window_and_preview_shape() -> None:
    import importlib.util

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Import History filtering and paging now use the same activity-date helper.
    assert 'def history_activity_date(item: dict[str, Any]) -> date:' in automation
    assert 'activity_date = history_activity_date(item)' in automation
    assert 'if filter_start and activity_date < filter_start:' in automation
    assert 'if filter_end and activity_date > filter_end:' in automation
    assert '"dateBasis": "import_activity"' in automation
    assert '<span>From date</span><input id="importHistoryDateFrom"' in app
    assert '<span>Through date</span><input id="importHistoryDateTo"' in app
    assert 'Filters use import activity dates and can be combined.' in app

    # Edit Delivery Lists opens on the relative three-week operating window,
    # then pages older history three weeks at a time with generic pager labels.
    assert 'const ADMIN_DELIVERY_LIST_WEEKS_PER_PAGE = 3;' in app
    assert 'function adminDeliveryListWeekPages' in app
    assert 'byKey.get(nextKey)' in app
    assert 'byKey.get(currentKey)' in app
    assert 'byKey.get(previousKey)' in app
    assert '>Previous</button>' in app
    assert '>Next</button>' in app
    assert '.replace(/^Last Week/, "Previous Week")' in app

    # The delivery preview is narrower and restores Glass Type immediately after
    # the item number, while the Edit Delivery Lists header no longer shows the
    # generic green status dot.
    preview_start = app.index('function deliveryListUpdatePreviewHtml(')
    preview_end = app.index('function initializeDeliveryListUpdatePreviewControls()', preview_start)
    preview = app[preview_start:preview_end]
    assert preview.index('<small>Item Nr.</small>') < preview.index('<small>Glass Type</small>') < preview.index('<small>Dimensions</small>') < preview.index('<small>Quantity</small>')
    assert 'width: min(780px, calc(100vw - 48px));' in admin
    assert '#adminModal[data-kind="deliveryLists"] .admin-modal-health-pill i' in admin

    # Functional proof: a workbook for 8/14 imported on 8/18 belongs to the
    # 8/18 activity filter, not the 8/14 delivery-date filter.
    module_path = ROOT / "backend" / "automation_control.py"
    specification = importlib.util.spec_from_file_location("v335_automation_control", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    controller = module.DeliveryAutomationController.__new__(module.DeliveryAutomationController)
    controller.scanner_store = None
    controller._database_import_history_items = lambda: [{
        "id": 33501,
        "runId": "run-335",
        "runStartedAt": "2026-08-18T14:10:00-04:00",
        "importedAt": "2026-08-18T14:10:05-04:00",
        "deliveryDate": "2026-08-14",
        "sourceName": "Delivery List 08-14-2026.xlsx",
        "classification": "updated",
        "stageSummaries": [{"stage": "Outbound", "scanner": "Airport Rd"}],
    }]
    controller._latest_automation_import_items = lambda: ([], {})
    controller._archived_automation_import_items = lambda: []

    activity_day = controller.get_import_history(date_from="2026-08-18", date_to="2026-08-18")
    delivery_day = controller.get_import_history(date_from="2026-08-14", date_to="2026-08-14")
    assert [item["id"] for item in activity_day["imports"]] == [33501]
    assert delivery_day["imports"] == []
    assert activity_day["filters"]["dateBasis"] == "import_activity"


def test_v336_filter_aware_history_paging_and_admin_context_polish() -> None:
    import importlib.util
    from datetime import date, timedelta

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The Control Center owns a dynamic paging mode: unfiltered content is a
    # fixed three-week operating window; filtered content pages by 25 dates.
    assert 'pageMode: "control_center"' in app
    assert 'clean_page_mode not in {"rows", "business_week", "control_center"}' in automation
    assert 'dates_per_page = 25' in automation
    assert 'page 1 = Next Week + This Week + Previous Week' in automation
    assert '"filteredPaging": filters_active if clean_page_mode == "control_center" else False' in automation
    assert 'import-history-paging-bar-v338' in app
    assert '>Previous</button>' in app
    assert '>Next</button>' in app

    # Edit Delivery Lists exposes page count/range at the top without the old
    # redundant modal health labels. Preview glass cells use Lookup colors.
    assert 'adminDeliveryListHeaderPager' in app
    assert 'admin-delivery-list-paging-bar-v338' in app
    assert 'Live delivery data' not in app
    assert 'Unsaved changes protected' not in app
    assert 'delivery-update-preview-item-glass-v336' in app
    assert 'previewGlassVisualCssVariables(glassType, previewGlassColorMap)' in app
    assert '.delivery-update-preview-item-glass-v336 {' in admin
    assert 'var(--glass-type-color' in admin

    # Functional proof for the two history modes.
    module_path = ROOT / "backend" / "automation_control.py"
    specification = importlib.util.spec_from_file_location("v336_automation_control", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    controller = module.DeliveryAutomationController.__new__(module.DeliveryAutomationController)
    controller.scanner_store = None
    controller._latest_automation_import_items = lambda: ([], {})
    controller._archived_automation_import_items = lambda: []

    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    week_offsets = [1, 0, -1, -2, -3, -4, -5]
    history_rows = []
    for index_value, offset in enumerate(week_offsets, start=1):
        activity = current_monday + timedelta(days=(offset * 7) + 1)
        history_rows.append({
            "id": 33600 + index_value,
            "runId": f"window-{index_value}",
            "runStartedAt": f"{activity.isoformat()}T10:00:00+00:00",
            "importedAt": f"{activity.isoformat()}T10:00:05+00:00",
            "deliveryDate": activity.isoformat(),
            "sourceName": f"Window {index_value}.xlsx",
            "classification": "updated",
            "stageSummaries": [{"stage": "Outbound", "scanner": "Airport Rd"}],
        })
    controller._database_import_history_items = lambda: history_rows

    first_page = controller.get_import_history(page=1, page_mode="control_center")
    second_page = controller.get_import_history(page=2, page_mode="control_center")
    assert first_page["pageUnit"] == "weeks"
    assert len(first_page["imports"]) == 3
    assert len(second_page["imports"]) == 3
    assert first_page["pageStart"] == (current_monday - timedelta(days=7)).isoformat()
    assert first_page["pageEnd"] == (current_monday + timedelta(days=11)).isoformat()

    filtered_rows = []
    for index_value in range(30):
        activity = today - timedelta(days=index_value)
        filtered_rows.append({
            "id": 33700 + index_value,
            "runId": f"filtered-{index_value}",
            "runStartedAt": f"{activity.isoformat()}T10:00:00+00:00",
            "importedAt": f"{activity.isoformat()}T10:00:05+00:00",
            "deliveryDate": activity.isoformat(),
            "sourceName": f"Airport Filter {index_value}.xlsx",
            "classification": "updated",
            "stageSummaries": [{"stage": "Outbound", "scanner": "Airport Rd"}],
        })
    # A second run on the newest date proves that rows are not the page limit.
    filtered_rows.append({
        "id": 33999,
        "runId": "filtered-extra",
        "runStartedAt": f"{today.isoformat()}T12:00:00+00:00",
        "importedAt": f"{today.isoformat()}T12:00:05+00:00",
        "deliveryDate": today.isoformat(),
        "sourceName": "Airport Filter Extra.xlsx",
        "classification": "updated",
        "stageSummaries": [{"stage": "Outbound", "scanner": "Airport Rd"}],
    })
    controller._database_import_history_items = lambda: filtered_rows
    filtered_page = controller.get_import_history(page=1, page_mode="control_center", query="Airport")
    filtered_page_two = controller.get_import_history(page=2, page_mode="control_center", query="Airport")
    assert filtered_page["filteredPaging"] is True
    assert filtered_page["pageUnit"] == "dates"
    assert filtered_page["pageDateCount"] == 25
    assert len(filtered_page["imports"]) == 26
    assert filtered_page_two["pageDateCount"] == 5
    assert filtered_page["totalPages"] == 2


def test_v337_week_grouping_shared_admin_paging_and_manual_order_fanout() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Import History keeps the v0.336 data paging rules, but the visible results
    # are now separated into the same operating-week bands as the Home selector
    # and Edit Delivery Lists.
    assert 'automation-history-week-v337' in app
    assert 'automation-history-week-heading-v337' in app
    assert 'adminDeliveryListWeekLabel(weekKey)' in app
    assert 'automation-history-week-days-v337' in admin

    # One shared numbered pager is used across every requested Admin history /
    # delivery-list surface. Individual callers retain their own page sizes.
    assert 'function sharedNumberedPagerMarkup(' in app
    for marker in (
        'data-history-page',
        'data-admin-delivery-week-page',
        'data-manual-edit-page',
        'data-action-history-page',
        'data-admin-import-page',
        'data-rack-history-page',
    ):
        assert marker in app
    assert 'app-numbered-pager-v337' in admin
    assert 'state.adminImportRunsPerPage || 5' in app

    # Create New Order explains the destination in advance and the backend uses
    # the explicit route choice instead of silently adding whichever stage was
    # open in the editor.
    assert 'manual-order-modal-v338' in app
    assert 'Airport Road · Staging + Outbound' in app
    assert 'syncManualOrderCreateRoutePreview' in app
    assert 'manual-order-create-destination-v338' in admin
    assert 'def _manual_order_airport_stage_role' in operations
    assert 'def _route_matches_stage' in operations
    assert 'missing_airport_roles' in operations
    assert 'target_lists = [*airport_targets, *route_targets]' in operations
    create_start = operations.index('def create_manual_order(')
    create_end = operations.index('def record_packing_print(', create_start)
    create_body = operations[create_start:create_end]
    assert 'target_lists.append(selected)' not in create_body
    assert 'Airport Staging, Airport Outbound, and {route_label}' in create_body
    assert '"airportStageRoles": sorted(airport_roles)' in create_body

    # Lightweight behavioral proof for the stage classifiers that control the
    # fan-out contract without requiring the full scanner database fixture.
    import importlib.util

    module_path = ROOT / "backend" / "operations.py"
    specification = importlib.util.spec_from_file_location("v337_operations", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    service = module.OperationsFeatureService
    assert service._manual_order_airport_stage_role("Staging", "Airport Rd") == "staging"
    assert service._manual_order_airport_stage_role("Outbound", "Airport Rd") == "outbound"
    assert service._route_matches_stage("IT", "Receiving", "Indian Trail") is True
    assert service._route_matches_stage("CPU", "Customer Pickup", "CPU") is True
    assert service._route_matches_stage("DTC", "DTC", "Deliver to Customer") is True
    assert service._route_matches_stage("GNV", "Greenville", "Greenville") is True
    assert service._route_matches_stage("IT", "Outbound", "Airport Rd") is False


def test_v338_unified_header_paging_scroll_ownership_and_create_order_dialog() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Both requested browsers use the same Action-History pager classes and
    # place the pager before their independently scrollable content regions.
    assert 'id="adminDeliveryListHeaderPager"' in app
    assert 'class="modal-action-history-pager app-numbered-pager-v337" id="adminDeliveryListHeaderPager"' in app
    assert 'class="modal-action-history-pager app-numbered-pager-v337" id="importHistoryPager"' in app
    assert app.index('id="importHistoryPager"') < app.index('id="importHistoryResults"')
    assert 'id="importHistoryPageSummary"' not in app
    assert 'id="importHistoryTopPageSummary"' not in app

    # One explicit scroll owner per browser prevents hovered cards/details from
    # trapping wheel input or visually passing behind the controls header.
    assert 'function wireOwnedVerticalScroll(element)' in app
    assert 'wireOwnedVerticalScroll(target);' in app
    assert 'wireOwnedVerticalScroll(importHistoryModal.querySelector("#importHistoryResults"));' in app
    assert '#adminModal[data-kind="deliveryLists"] #adminModalBody {' in admin
    assert 'overflow: hidden !important;' in admin
    assert '#adminModal[data-kind="deliveryLists"] #adminDeliveryListModalResults {' in admin
    assert '.delivery-automation-tab.import-history-workspace.is-active #importHistoryResults {' in admin
    assert 'touch-action: pan-y;' in admin

    # Create Order is a separate dialog rather than an expandable section in
    # the already dense Manual Edit workspace.
    assert 'id="manualOrderCreatePanel"' not in app
    assert 'function openManualOrderCreateModal()' in app
    assert 'manual-order-modal-v338' in app
    assert 'manual-order-modal-backdrop-v338' in admin
    assert 'manual-edit-create-order-button-v338' in app
    assert 'data.listId = form.dataset.listId' in app
    assert 'Airport Road · Staging + Outbound' in app


def test_v339_fast_edit_catalog_shared_import_search_and_cancel_polish() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Edit Delivery Lists no longer launches by hydrating the rich global list
    # catalog. It has a dedicated server-backed three-week catalog API and the
    # browser renders page/range metadata returned by that API.
    assert 'if parsed.path == "/api/admin/delivery-list-catalog":' in server
    assert 'def get_admin_delivery_list_catalog(' in store
    method_start = store.index('    def get_admin_delivery_list_catalog(', store.index('class SQLiteDeliveryStore'))
    method_end = store.index('    def get_delivery_list_update_preview(', method_start)
    catalog_body = store[method_start:method_end]
    assert 'selected_week_keys' in catalog_body
    assert 'WHERE dl.id IN ({placeholders})' in catalog_body
    assert 'self.list_timing_metrics(' not in catalog_body
    assert 'async function loadAdminDeliveryListCatalogPage(' in app
    assert 'fetchJson(`/api/admin/delivery-list-catalog?${params.toString()}`)' in app
    open_branch_start = app.index('} else if (modalKind === "deliveryLists" || modalKind === "deliveryActions") {')
    open_branch_end = app.index('      } else {', open_branch_start)
    open_branch = app[open_branch_start:open_branch_end]
    assert 'loadAdminDeliveryListCatalogPage(1, "", { showLoading: false })' in open_branch
    assert 'loadDeliveryLists(state.activeListId)' not in open_branch

    # Manual Edit starts its first page and supporting lookups concurrently,
    # while the slow-changing lookup library is briefly reused between opens.
    assert 'runManualEditModalSearch(true, 1, ensureManualEditLookupsLoaded())' in app
    assert 'parallelPreflight ? Promise.resolve(parallelPreflight)' in app
    assert 'manualEditLookupLibraryLoadedAt' in app
    assert '5 * 60 * 1000' in app

    # Import History now uses the same labeled filter/search control hierarchy
    # as shared Action History tabs instead of its former search-box variant.
    assert 'modal-action-history-filters import-history-toolbar import-history-action-filters-v339' in app
    assert 'class="modal-action-history-filter-search"' in app
    assert '<span>Search history</span>' in app
    assert 'import-history-filter-grid-v339' in admin

    # Create Order Cancel has its own complete secondary interaction treatment.
    assert 'manual-order-cancel-button-v339' in app
    assert '.manual-order-cancel-button-v339 {' in admin
    assert '.manual-order-cancel-button-v339:hover' in admin
    assert 'manual-order-cancel-icon-v339' in admin


def test_v340_permission_review_dedicated_account_role_dialogs_and_admin_search() -> None:
    import ast

    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The All Delivery Lists control is now a conventional search input with a
    # quiet clear action instead of the old animated Admin search treatment.
    assert 'class="admin-standard-search-v340"' in app
    assert 'data-admin-delivery-search-clear' in app
    assert '.admin-standard-search-v340 {' in admin
    assert '.admin-standard-search-clear-v340 {' in admin
    assert 'modal-search-slide' not in admin[admin.index('/* v0.340 Permission review'):]

    # Required Create Order markers are explicit, accessible red accents.
    assert app.count('class="required-mark-v340"') >= 7
    assert '.required-mark-v340 {' in admin
    assert 'color: #c72a3f;' in admin

    # User and Role creation are focused child dialogs with dedicated blue
    # launchers; the Admin preview simply shows the first ten accounts.
    assert 'data-open-create-role' in app
    assert 'function roleCreateDialogHtml()' in app
    assert 'role-create-modal-v340' in app
    assert 'data-open-create-user' in app
    assert 'function userCreateDialogHtml()' in app
    assert 'user-create-modal-v340' in app
    assert '.admin-child-modal-v340 {' in admin
    assert '.role-manager-create-button-v340' in admin
    assert '.user-manager-create-button-v340' in admin
    assert 'const previewLimit = 10;' in app
    assert 'admin-preview-more-button' not in app

    # Parse the maintained permission constants without importing backend/store
    # (the source snapshot intentionally omits several runtime dependencies).
    module = ast.parse(store)
    permissions = []
    aliases = {}
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "PERMISSIONS" for target in node.targets):
            permissions = ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "LEGACY_PERMISSION_ALIASES" for target in node.targets):
            aliases = ast.literal_eval(node.value)

    expected_split_permissions = {
        "edit_delivery_list_items",
        "create_delivery_list_orders",
        "delete_delivery_list_items",
        "delete_delivery_lists",
        "review_superseded_orders",
        "manage_user_access",
        "manage_user_assignments",
        "manage_customer_emails",
        "manage_cross_date_scanning",
        "manage_bay_scanner_rules",
        "manage_bay_auto_assigner",
    }
    assert expected_split_permissions.issubset(set(permissions))
    assert "edit_delivery_lists" not in permissions
    assert "view_bay_reports" not in permissions
    assert aliases["edit_delivery_lists"] == "edit_delivery_list_items"
    assert aliases["view_bay_reports"] == "view_reports"
    assert 'PERMISSION_BACKFILL_SOURCES = {' in store
    assert 'newly_introduced_permissions' in store

    # Security-sensitive endpoints use the split authorities rather than the
    # original broad edit/role aliases. Creating a user crosses two domains and
    # therefore requires both profile and assignment authority.
    assert 'self.require_permission("create_delivery_list_orders")' in server
    assert 'self.require_permission("delete_delivery_list_items")' in server
    assert 'self.require_permission("delete_delivery_lists")' in server
    assert 'self.require_permission("review_superseded_orders")' in server
    assert 'self.require_permission("manage_user_assignments")' in server
    assert 'self.require_permission("manage_customer_emails")' in server
    assert 'self.require_permission("manage_cross_date_scanning")' in server
    assert 'self.require_permission("manage_bay_scanner_rules")' in server
    assert 'self.require_permission("manage_bay_auto_assigner")' in server
    assert 'self.require_all_permissions("manage_users", "manage_user_assignments")' in server

    # Action History is authorized by the requested GUI context rather than by
    # one global any-Admin permission gate.
    assert 'ACTION_HISTORY_CONTEXT_PERMISSIONS = {' in server
    assert 'context_permissions = ACTION_HISTORY_CONTEXT_PERMISSIONS.get(context, ("view_admin",))' in server
    assert 'user = self.require_any_permission(*context_permissions)' in server

    # Audit the actual maintained gates: every canonical permission must have a
    # route/UI authorization avenue and no browser/server gate may depend on a
    # retired alias after the v0.340 cleanup.
    used_permissions: set[str] = set()
    for match in re.finditer(r'require_(?:any_|all_)?permissions?\(([^\n]*?)\)', server):
        used_permissions.update(re.findall(r'"([a-z][a-z0-9_]*)"', match.group(1)))
    context_block = server[server.index("ACTION_HISTORY_CONTEXT_PERMISSIONS"):server.index("PRINT_PACKAGE_SESSION_TTL_SECONDS")]
    used_permissions.update(
        value
        for value in re.findall(r'"([a-z][a-z0-9_]*)"', context_block)
        if value in permissions or value in aliases
    )
    used_permissions.update(re.findall(r'hasPermission\("([a-z][a-z0-9_]*)"\)', app))
    for match in re.finditer(r'hasAnyPermission\(\[([^\]]*)\]\)', app):
        used_permissions.update(re.findall(r'"([a-z][a-z0-9_]*)"', match.group(1)))
    for match in re.finditer(r'data-permission-any="([^"]+)"', index):
        used_permissions.update(value.strip() for value in match.group(1).split(","))

    known = set(permissions) | set(aliases)
    assert not (used_permissions - known), f"Unknown permission gates: {sorted(used_permissions - known)}"
    assert not (used_permissions & set(aliases)), f"Legacy aliases still gated directly: {sorted(used_permissions & set(aliases))}"
    assert not (set(permissions) - used_permissions), f"Canonical permissions without a maintained gate: {sorted(set(permissions) - used_permissions)}"


def test_v341_role_save_session_admin_modal_and_management_print_repair() -> None:
    """Protect the v0.341 non-lockout security and Admin workflow repairs."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")


    # Role permission changes are already re-read on every authenticated request;
    # saving a role must never invalidate live sessions as a side effect.
    update_start = store.index('    def update_role_permissions(')
    update_end = store.index('    def user_from_row(', update_start)
    update_body = store[update_start:update_end]
    assert 'DELETE FROM sessions' not in update_body
    assert 'admin_role_locked = clean_role.casefold() == "admin"' in update_body
    assert 'clean_permissions = list(PERMISSIONS)' in update_body
    assert '"sessionRefreshRequired": False' in update_body

    # Existing production databases also repair Admin on startup, so newly added
    # capabilities cannot leave the recovery role with partial access.
    seed_start = store.index('    def seed_security_data(')
    seed_end = store.index('    def seed_user_if_missing(', seed_start)
    seed_body = store[seed_start:seed_end]
    assert 'if role_name == "Admin":' in seed_body
    assert 'for permission in PERMISSIONS:' in seed_body
    assert '"Admin": PERMISSIONS' in store

    # 403 is an action-level denial; only a true 401 session failure changes the
    # browser authentication state and shows Sign In.
    fetch_start = app.index('async function fetchJson(')
    fetch_end = app.index('async function detectBackend()', fetch_start)
    fetch_body = app[fetch_start:fetch_end]
    forbidden_block = fetch_body[fetch_body.index('if (response.status === 403)'):fetch_body.index('if (response.status === 401')]
    assert 'showLogin(' not in forbidden_block
    assert 'You do not have access to perform that action.' in forbidden_block
    assert 'showLogin("Your session has ended. Please sign in again.")' in fetch_body

    # Admin Role Manager is visually and functionally protected instead of
    # presenting editable checkboxes that imply Admin can be reduced.
    assert 'is-system-admin-v341' in app
    assert 'role-system-lock-v341' in app
    assert 'role-admin-lock-note-v341' in app
    assert 'rolePermissionCategoryHtml(role.name, category, selected, adminRoleLocked)' in app
    assert '.role-permission-card.is-system-admin-v341' in admin

    # Child create dialogs must sit above #adminModal's z-index:10010 layer.
    assert '.admin-child-modal-backdrop-v340 {\n  z-index: 10050;' in admin
    assert '.admin-child-modal-v340 {\n  z-index: 10060;' in admin

    # Remove the duplicate compact identity metadata from the dashboard preview.
    preview_start = app.index('function renderAdminUsersTable(')
    preview_end = app.index('return `\n    <div class="user-manager-cards"', preview_start)
    preview_body = app[preview_start:preview_end]
    assert '<small>${escapeHtml(user.username)}${user.email ?' not in preview_body

    # Fresh import history retains an exact Outbound ID and Print / Export can
    # hydrate that list directly before the general catalog heartbeat catches up.
    assert 'const listId = String(list?.id || row?.listId || "").trim();' in app
    assert 'const missingIds = [...wanted].filter((id) => !knownIds.has(id));' in app
    assert 'fetchJson(`/api/delivery-lists/${encodeURIComponent(id)}`)' in app
    assert 'if (!listsByDeliveryDate().length && !(context.fixedListIds && (context.listIds || []).length))' in app


def test_v342_sql_automation_binds_and_validates_live_scanner_store() -> None:
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert "def _scanner_store_identity" in automation
    assert 'payload["ScannerStore"] = scanner_identity' in automation
    assert 'payload["ProjectRoot"] = str(self.project_root)' in automation
    assert 'payload["ScannerStore"] = scanner_identity' in automation

    assert '--expected-store-mode' in importer
    assert '--expected-store-database' in importer
    assert 'def validate_store_identity' in importer
    assert 'Scanner-store identity mismatch. Refusing to import' in importer
    assert 'scanner_store_identity = validate_store_identity(store, args)' in importer
    assert 'summary["scannerStore"] = scanner_store_identity' in importer

    assert '$env:DLS_DATABASE_PATH = $expectedStoreDatabase' in runner
    assert '"--expected-store-mode", $expectedStoreMode' in runner
    assert '"--expected-store-database", $expectedStoreDatabase' in runner
    assert 'Scanner import store confirmed.' in runner

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract


def test_v343_preview_role_duplicate_and_customer_email_rework() -> None:
    """Protect the v0.343 Admin polish and duplicate-safety contracts."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    safety = (ROOT / "automation" / "sql_delivery_export" / "delivery_import_safety.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Lookup Manager glass color variables now live on the whole item article;
    # semantic New/Updated classes no longer force a generic green/blue row.
    assert 'data-preview-change-type="${type}"${glassVisualStyle ? ` style="${escapeHtml(glassVisualStyle)}"` : ""}' in app
    assert '--glass-type-row:' in app
    assert 'background: linear-gradient(90deg, var(--glass-type-row-strong' in admin
    assert '.delivery-update-preview-item-glass-v336' in admin

    # Role identity/actions stay fixed while every permission is reachable from a
    # dedicated nested scroller with a definite modal viewport.
    assert '.role-create-modal-v340 {\n  height: min(840px, calc(100vh - 34px));' in admin
    assert 'grid-template-rows: auto minmax(0, 1fr) auto;' in admin
    assert '.role-create-modal-v340 .role-create-permission-list {' in admin
    assert 'overflow-y: auto;' in admin

    # Cancel actions use the shared icon treatment, including scan override paths.
    assert 'app-cancel-icon-v343' in app
    assert 'app-cancel-icon-v343' in index
    assert 'data-outbound-override-cancel><span class="app-cancel-icon-v343"' in app
    assert 'data-cross-date-cancel><span class="app-cancel-icon-v343"' in app

    # Customer Emails is now a tabbed operational center without changing the
    # existing form IDs relied on by the maintained API event handlers.
    for tab in ('rules', 'test', 'activity'):
        assert f'data-customer-email-panel="{tab}"' in app
    assert 'data-customer-email-rule-search' in app
    assert 'data-customer-email-activity-filter' in app
    assert 'id="customerEmailContactForm"' in app
    assert 'id="customerEmailCcForm"' in app
    assert 'id="customerEmailTestForm"' in app
    assert '.customer-email-workspace-v343' in admin

    # Duplicate identity is normalized and guarded at import validation, stage
    # insertion, protected-manual reconciliation, manual creation, and manual edit.
    assert 'def logical_order_item_key(' in store
    assert 'Duplicate logical items are blocked before delivery-list publication.' in store
    assert 'Duplicate Order Nr. / Item Nr. {order_item_key} cannot be inserted' in store
    assert 'protected_manual_keys' in store
    assert 'if "order_no" in business_updates or "item_no" in business_updates:' in store
    assert 'Choose a different Order Nr. / Item Nr. before saving.' in store
    assert 'CAST(li.order_no AS INTEGER) = CAST(? AS INTEGER)' in operations
    assert 'if order_item_key in protected_manual_keys:' in safety
    assert 'effective_expected_rows' in importer


def test_v344_review_first_candidates_and_admin_modal_polish() -> None:
    """Protect the v0.344 review-first duplicate flow and Admin GUI repairs."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Static permission categories size to their full contents while the outer
    # library remains the one scrolling viewport.
    assert '.role-create-modal-v340 .role-create-permission-category.is-static {' in admin
    assert 'grid-template-rows: auto auto;' in admin
    assert 'overflow: visible;' in admin
    assert 'grid-auto-rows: max-content;' in admin

    # Open routes and separate orders receive explicit visual hierarchy.
    assert '.delivery-update-preview-v311 .delivery-update-preview-location-group-v311[open] > summary {' in admin
    assert 'content: "Viewing";' in admin
    assert '.delivery-update-preview-v311 .delivery-update-preview-order-list-v311 {' in admin
    assert 'gap: 14px;' in admin

    # Customer Emails no longer exposes the removed hero or Delivery Setup tab;
    # Global CC sits with the rule editor and activity opens its own high layer.
    assert 'data-customer-email-panel="delivery"' not in app
    assert 'customer-email-hero-v343' not in app
    assert 'customer-email-rules-left-v344' in app
    assert 'customer-email-readiness-v344' in app
    assert 'email-activity-detail-shell-v344' in app
    assert '.email-activity-detail-shell-v344 {' in admin
    assert 'z-index: 10220;' in admin

    # Customer Route creation is isolated in a child dialog rather than another
    # inline rule form inside the manager.
    assert 'data-open-customer-route-create' in app
    assert 'customerRouteCreateModalV344' in app
    assert 'customer-route-create-modal-v344' in app
    assert '.customer-route-create-modal-v344 {' in admin

    # Candidate review persistence must happen before selective reconciliation.
    preflight = importer.index('Synchronizing superseded-order review candidates before delivery-list reconciliation.')
    reconcile = importer.index('summary = selective_sql_sync(')
    assert preflight < reconcile
    assert 'No delivery-list reconciliation was started.' in importer
    assert 'No pending candidate is removed automatically.' in importer

    # Cancel actions retain their shared hook but use the rebuilt lightweight X.
    assert '.app-cancel-icon-v343::before' in admin
    assert '-webkit-mask: none !important;' in admin


def test_v345_shared_admin_tabs_dense_preview_and_lookup_revamp() -> None:
    """Protect the v0.345 dense-preview and shared Admin-tab contracts."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Preview glass colors are intentionally quieter and route headers use their
    # own full route palette. Orders also receive a route-colored dot.
    assert 'function previewGlassVisualCssVariables' in app
    assert 'previewGlassVisualCssVariables(glassType, previewGlassColorMap)' in app
    assert '--preview-route-color:' in admin
    assert '.delivery-update-preview-order-header-v311::before' in admin
    assert 'min-height: 34px;' in admin

    # Customer Email and Lookup subsections now share the existing Admin tab rail.
    assert 'function configureAdminModalSectionTabsV345' in app
    assert 'customerEmail:rules' in app
    assert 'lookup:glass_profile' in app
    assert 'customer-email-tabs-v343' not in app
    assert 'data-customer-email-tab' not in app
    assert 'data-lookup-manager-type' not in app

    # Customer rule editing no longer exposes a redundant Cancel action.
    customer_email_start = app.index('function customerEmailRulesModalHtml()')
    customer_email_end = app.index('/** Re-render the Customer Email workspace', customer_email_start)
    customer_email_html = app[customer_email_start:customer_email_end]
    assert 'data-customer-email-cancel-edit' not in customer_email_html

    # Lookup Manager no longer renders its old hero/KPI or nested type-tab UI.
    lookup_start = app.index('function lookupManagerModalHtml()')
    lookup_end = app.index('/**\n * Purpose: Synchronize the contextual Lookup Manager fields', lookup_start)
    lookup_html = app[lookup_start:lookup_end]
    assert 'lookup-manager-hero' not in lookup_html
    assert 'lookup-manager-kpis' not in lookup_html
    assert 'lookup-type-tabs' not in lookup_html
    assert 'lookup-manager-v345' in lookup_html

    # Create Role stretches the permission library through the remaining viewport.
    assert 'height: min(920px, calc(100vh - 18px));' in admin
    assert '.role-create-modal-v340 .role-create-permission-list {' in admin

    # Customer Routes retain separate creation while gaining route-aware card polish.
    assert 'data-route-code="${escapeHtml(routeCode)}"' in app
    assert 'data-route-code="${escapeHtml(routeCode)}"' in app
    assert 'font-size: 12px !important;' in admin


def test_v346_admin_configuration_stage_station_and_cross_date_revamp() -> None:
    """Protect the v0.346 configuration workspace and stage-preset contracts."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Create Role consumes the full remainder between identity and action rows.
    assert '.role-create-modal-v340 .role-create-modal-permissions-v340,\n.role-create-modal-v340 .role-create-permission-list {\n  height: 100%;' in admin
    assert 'grid-template-rows: auto minmax(0, 1fr) auto;' in admin

    # Customer Route rows are isolated and use the larger launcher plus new SVG actions.
    assert 'min-width: 248px;' in admin
    assert 'min-height: 50px;' in admin
    assert 'font-size: 14px !important;' in admin
    assert 'customer-route-list-heading-v346' in app
    assert 'class="icon-only icon-save" data-save-customer-route-rule=' in app
    assert 'class="icon-only icon-trash danger" data-remove-customer-route-rule=' in app
    assert 'grid-auto-rows: max-content;' in admin

    # Lookup Manager gains first-class Stations/Stages, professional SVG actions,
    # and an administrator removal path for every original lookup library.
    assert 'insertTab("lookup:station", "Stations"' in app
    assert 'insertTab("lookup:stage_definition", "Stages"' in app
    assert 'function stationLookupManagerHtmlV346()' in app
    assert 'function stageDefinitionManagerHtmlV346()' in app
    assert 'function lookupActionIconHtmlV346(kind)' in app
    assert 'data-remove-lookup-type' in app
    assert '"/api/admin/manual-edit-lookups/remove"' in server
    assert "source = 'manual-hidden'" in store
    for lookup_type in ('"product"', '"route"', '"process"', '"glass_cost"', '"glass_color"'):
        assert lookup_type in store

    # Stage identity is configurable while maintained presets own operational logic.
    assert 'STAGE_PRESET_CATALOG' in store
    assert 'DEFAULT_STAGE_DEFINITIONS' in store
    assert 'def stage_definition_for_preset(' in store
    assert 'def get_stage_definitions(' in store
    assert 'def refresh_stage_definition_cache(' in store
    assert 'affectedDeliveryLists' in store
    assert 'scan_stage_category(' in store
    assert 'self._stage_preset(stage, scanner)' in operations
    assert 'preset == "airport_staging"' in operations
    assert 'preset == "airport_outbound"' in operations

    # Cross-Date Scanning keeps its established form contract inside the rebuilt UI.
    assert 'cross-date-settings-v346' in app
    assert 'cross-date-settings-form-v346' in app
    assert 'id="crossDateScanMode"' in app
    assert 'id="crossDatePastDays"' in app
    assert 'id="crossDateFutureDays"' in app
    assert '.cross-date-settings-v346' in admin


def test_v347_route_lookup_cross_date_and_reject_setup_polish() -> None:
    """Protect v0.347 Admin presentation changes without altering saved-data contracts."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Customer Route cards use their full route color as a gradient rather than a left stripe.
    assert 'function customerRouteVisualColorV347(routeCode = "")' in app
    assert 'style="--customer-route-color:${escapeHtml(customerRouteVisualColorV347(routeCode))}"' in app
    assert '.customer-route-list-v344 .customer-route-rule-row::before {\n  display: none !important;' in admin
    assert 'color-mix(in srgb, var(--customer-route-color, #315f9e) 13%, #ffffff)' in admin
    assert 'customer-route-heading-icon-v347' in app

    # Glass-oriented lookup libraries are grouped and the live preview glyph was rebuilt.
    assert 'function lookupGlassFamilyV347(item = {})' in app
    assert 'function lookupGlassGroupsV347(items = [])' in app
    assert 'data-lookup-group' in app
    assert '["Annealed", "Mirror", "Tempered"]' in app
    assert 'lookup-preview-icon-v347' in app
    assert 'The importer applies Updated Line when A+W changes an existing source line' in app
    assert 'next_state = state_text if re.search(r"\\bUpdated Line\\b"' in store
    assert '"manual_edit",' in store
    assert 'showSaveConfirmation(payload.message ||' in app

    # Cross-Date keeps the established settings contract even though v0.350
    # places it inside the combined Scan Page Settings workspace.
    cross_start = app.index('function crossDateSettingsTabHtmlV350()')
    cross_end = app.index('function mixedDestinationSettingsHtmlV350()', cross_start)
    cross = app[cross_start:cross_end]
    assert 'id="crossDateScanMode"' in cross
    assert 'id="crossDatePastDays"' in cross
    assert 'id="crossDateFutureDays"' in cross
    assert 'function crossDateScanSettingsModalHtml()' in app
    for removed in ('Scanner safety', 'Audited on every switch', 'Preserved safeguards', 'One unique safe match can switch automatically', 'The scanner still checks the current delivery list first', 'Limits are measured from the currently selected delivery date.', 'Choose the operator experience for one safe cross-date match.'):
        assert removed not in cross

    # Reject Settings is a new bounded two-library workspace using the existing API hooks.
    assert 'function rejectSettingsIconV347(kind)' in app
    assert 'reject-settings-shell-v347' in app
    assert 'reject-settings-grid-v347' in app
    assert 'reject-catalog-add-v347' in app
    assert 'class="icon-only icon-trash danger" type="button" data-reject-catalog-remove=' in app
    assert 'data-reject-catalog-form=' in app
    assert 'data-reject-catalog-remove=' in app
    assert '#adminModal[data-kind="rejectSettings"] #adminModalBody' in admin


def test_v348_route_grouping_cpu_orange_and_readability_polish() -> None:
    """Protect v0.348 route grouping, CPU identity, and readability changes."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    bays = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # CPU retains the intended orange identity and the v0.348 route grouping
    # helpers remain available; v0.350 promotes route selection to tabs.
    assert 'CPU: "#d77a1f"' in app
    assert '--preview-route-color: #d77a1f;' in admin
    assert 'function customerRouteSortedRulesV348()' in app
    assert 'function customerRouteRuleGroupsHtmlV348(editable = false, limit = 0,' in app
    assert 'function customerRouteTabsHtmlV350(activeRoute = "CPU"' in app
    assert 'customer-route-tab-content-v350' in app
    assert '.customer-route-group-v348 {' in admin
    assert '.customer-route-stat-v348 {' in admin

    # Route icon alignment and custom dropdown effects remain contained inside
    # the route field/card instead of spilling onto the route gradient.
    assert 'transform: translate(3px, 4px);' in admin  # retained historical rule; v0.349 overrides it later
    assert '.customer-route-rule-row .customer-route-route-field .custom-select-shell {' in admin
    assert 'overflow: clip;' in admin
    assert 'box-shadow: inset 0 0 0 1px rgba(45, 111, 168, .12) !important;' in admin

    # Email/manifest typography is intentionally larger, while preview orders
    # regain only a small amount of height after the prior density pass.
    assert '#adminModal[data-kind="customerEmails"] .customer-email-activity-copy-v343 strong {' in admin
    assert 'font-size: 12px;' in admin
    assert 'v0.348 In-Transit / Delivery Manifest readability' in bays
    assert '.transit-manifest-panel .transit-glass-table {' in bays
    assert 'font-size: .84rem;' in bays
    assert 'min-height: 52px;' in admin
    assert 'font-size: 15px;' in admin


def test_v349_admin_consolidation_and_safe_editing() -> None:
    """Protect v0.349 route, glass, email, reject, user, and Bay Scanner contracts."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Customer Routes preserve the v0.349 neutral editable-row treatment and
    # route infrastructure even though v0.350 replaces collapsed overview groups
    # with direct route tabs.
    assert 'function customerRouteRuleGroupsHtmlV348(editable = false, limit = 0,' in app
    assert 'customer-route-group-summary-v349' in app
    assert '.customer-route-group-rules-v348 .customer-route-rule-row,' in admin
    assert 'background: #ffffff !important;' in admin
    assert 'transform: translate(5px, 6px);' in admin
    assert 'customer-route-create-launch-v349' in app

    # Email Activity may delete drafts only, preserving non-draft history.
    assert 'def delete_customer_email_draft(' in store
    assert 'Only unsent email drafts can be deleted' in store
    assert '/api/admin/customer-emails/draft/delete' in server
    assert 'data-delete-email-draft' in app

    # Glass type/cost/color use one active editor and one backend write contract.
    assert 'function glassProfileManagerHtmlV349()' in app
    assert 'insertTab("lookup:glass_profile", "Glass Types"' not in app  # workspace tab owns Glass Types
    assert 'insertTab("lookup:glass_cost"' not in app
    assert 'insertTab("lookup:glass_color"' not in app
    assert 'def upsert_glass_profile(' in store
    assert 'def remove_glass_profile(' in store
    assert '/api/admin/manual-edit-lookups/glass-profile' in server
    assert 'function glassVisualLookupKeyV349' in app
    assert 'transform: translate(4px, 4px);' in admin

    # Preview order hierarchy is neutral and connected outside the order cards.
    assert '.delivery-update-preview-v311 .delivery-update-preview-order-block-v311:not(:last-child)::after' in admin
    assert 'background: #7e8d9b;' in admin
    assert 'padding-left: 20px;' in admin

    # User directory and reject reason editing have first-class v0.349 controls.
    assert 'user-manager-filter-panel-v349' in app
    assert 'data-clear-user-manager-filters' in app
    assert 'data-reject-catalog-edit="${escapeHtml(kind)}"' in app
    assert 'def update_reject_catalog(' in operations
    assert '/api/rejects/catalog/update' in server

    # The v0.349 Bay Scanner renderer/API surface remains maintained; v0.350
    # consolidates its controls with Bay Auto Assignment under a new tab model.
    assert 'function renderBayScannerRulesModalV349()' in app
    assert 'bay-scanner-management-v349' in admin
    assert '/api/admin/bay-scanner-rules' in server
    assert 'bayScannerRulesActiveTab: "rules"' in app
    assert 'title: "Bay Rules & Auto Assignment"' in app
    assert 'Bay Rules &amp; Auto Assignment' in index


def test_v350_route_glass_reject_and_scanner_configuration_consolidation() -> None:
    """Protect v0.350 route tabs, canonical glass profiles, reject editing, and scanner settings consolidation."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Customer Route overview and manager use the same CPU/DTC/GRN-first tab
    # model. v0.354 keeps all rules in the overview DOM and lets CSS provide the
    # ten-row scroll threshold instead of a separate Show More control.
    assert 'const CUSTOMER_ROUTE_PRIMARY_TABS_V350 = Object.freeze(["CPU", "DTC", "GNV"]);' in app
    assert 'function customerRouteTabLabelV350(routeCode = "")' in app
    assert 'if (route === "GNV") return "GRN";' in app
    assert 'function customerRouteTabsHtmlV350(activeRoute = "CPU"' in app
    assert 'const visibleRules = routeRules.slice(0, 10);' not in app
    assert 'data-customer-route-show-more-v350' not in app
    assert 'data-customer-route-overview-tab-v350' in app
    assert '.customer-route-tab-rail-v350 {' in admin
    assert '.customer-route-tab-rail-v350.is-overview {' in admin

    # Glass settings keep the Annealed / Mirror / Tempered family navigation,
    # while distinct mirror products remain separately configurable profiles.
    assert 'function glassProfileCanonicalLabelV350(value = "")' in app
    assert 'if (/\\bmirror\\b/i.test(normalized)) {' in app
    assert 'const annealedAlias = /\\b(?:anneal(?:ed)?|ann)\\b/gi;' in app
    assert 'const temperedAlias = /\\b(?:temper(?:ed)?|temp)\\b/gi;' in app
    assert 'return `${base} ${tempered ? "Tempered" : "Annealed"}`;' in app
    assert 'const families = ["Annealed", "Mirror", "Tempered"]' in app
    assert 'data-glass-family-tab-v350' in app
    assert 'data.get("values")' in server
    assert 'def remove_glass_profile(self, value: str, user: str, values: Any = None)' in store
    assert '.glass-profile-family-tabs-v350 {' in admin

    # Both reject libraries use editable icon-only actions in one row.
    assert 'data-reject-catalog-edit="${escapeHtml(kind)}"' in app
    assert 'class="icon-only icon-pencil" type="button" data-reject-catalog-edit=' in app
    assert 'class="icon-only icon-trash danger" type="button" data-reject-catalog-remove=' in app
    assert '.reject-catalog-row-actions-v349 {' in admin
    assert 'if clean_kind not in {"reason", "location"}:' in (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")

    # Scanner administration is consolidated without changing the existing
    # endpoint contracts or permission-aware Action History contexts.
    assert 'title: "Scan Page Settings"' in app
    assert 'insertTab("scanPage:mixedDestination", "Mixed Destination"' in app
    assert 'id="crossDateScanSettingsForm"' in app
    assert 'id="bayOverrideWindowForm"' in app
    assert 'title: "Bay Rules & Auto Assignment"' in app
    assert 'insertTab("bayConfig:rules", "Scanner Rules"' not in app  # base tab is reused
    assert 'insertTab("bayConfig:auto", "Auto Assignment"' in app
    assert 'data-admin-modal="bayAutoAssigner"' not in index
    assert 'Bay Rules &amp; Auto Assignment' in index
    assert 'Scan Page Settings' in index
    assert '"bayScannerRules": ("manage_bay_scanner_rules", "manage_bay_auto_assigner")' in server
    assert '"crossDateScanning": ("manage_cross_date_scanning", "manage_bay_scanner_rules")' in server


def test_v351_admin_visual_polish_mirror_restoration_and_scroll_ownership() -> None:
    """Protect the v0.351 admin polish, distinct Mirror profiles, and history scroll fix."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Customer Routes: larger overview plus shared route-color cues in overview/full manager.
    assert 'customer-route-overview-panel-v351' in index
    assert 'customer-route-tab-rail-v351' in app
    assert 'customer-route-overview-rule-v351' in app
    assert 'customer-route-modern-v351' in app
    assert '.customer-route-overview-panel-v351 {' in admin
    assert 'font-size: 12px;' in admin

    # Lookup Manager: centered preview, persistent edit icon, and revamped searches.
    assert 'lookup-library-search-v351' in app
    assert 'data-lookup-search-clear-v351' in app
    assert '#adminModal[data-kind="lookups"] .lookup-preview-icon-v347 svg {' in admin
    assert 'transform: none !important;' in admin
    assert '#adminModal[data-kind="lookups"] .lookup-use-button:hover' in admin

    # Mirror is a family of independently configurable products, not one collapsed row.
    assert 'if (/\\bmirror\\b/i.test(normalized)) {' in app
    assert 'if (/\\bmirror\\b/i.test(canonical)) return "Mirror";' in app
    assert 'if (/\\bmirror\\b/i.test(normalized)) return "Mirror";' not in app
    for mirror_name in (
        '1/4 Mirror',
        '1/4 French Antique Mirror',
        '1/4 Summer Cloud Antique Mirror',
        '1/4 Dark Cloud Antique Mirror',
        '1/4 Rainbow Antique Mirror',
        '1/4 Hollywood Antique Mirror',
        '1/4 Woodford Antique Mirror',
    ):
        assert mirror_name in store

    # Reworked settings and reject layouts preserve existing functional contracts.
    assert 'scan-page-mixed-destination-v351' in app
    assert 'id="bayOverrideWindowForm"' in app
    assert 'id="bayDestinationOverrideMinutes"' in app
    # The v0.351 Bay Auto Assigner contract remains available through the
    # v0.352 simplified workspace rather than retaining the superseded shell.
    assert 'bay-auto-assigner-shell-v352' in app
    assert 'id="bayAutoAssignerForm"' in app
    assert '.reject-catalog-row-actions-v349 {' in admin
    assert 'flex-direction: row !important;' in admin

    # Action History explicitly owns wheel/trackpad scrolling over all descendants.
    assert 'function wireOwnedVerticalScroll(element)' in app
    assert 'wireOwnedVerticalScroll(refs?.root);' in app
    assert 'wireOwnedVerticalScroll(details);' in app
    assert '#adminModalHistory.modal-action-history' in admin


def test_v352_bounded_routes_practical_auto_assignment_and_gui_typography() -> None:
    """Protect v0.352 dashboard bounds, preassignment simplification, and readable Admin typography."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Customer Route readability remains, but the dashboard card is no longer
    # promoted to a full-width desktop section.
    assert 'customer-route-overview-panel-v351 customer-route-overview-panel-v352' in index
    assert '.customer-route-overview-panel-v351 {' in admin
    assert 'grid-column: span 4 !important;' in admin
    assert '@media (max-width: 1180px)' in admin

    # Auto Assignment exposes only the decisions that affect the maintained
    # Outbound-to-Indian Trail preassignment path.
    assert 'bay-auto-assigner-shell-v352' in app
    assert 'What Auto Assignment actually does' in app
    assert 'Auto vs. manual placement' in app
    assert 'bay-auto-policy-list-v352' in app
    assert 'data-bay-auto-field=' not in app
    assert 'function autoAssignTypeOptions(' not in app
    assert 'CPU route' not in app[app.index('function bayAutoAssignerModalHtml()'):app.index('async function refreshBayAutoAssigner', app.index('function bayAutoAssignerModalHtml()'))]
    assert 'standardBayType: current.standardBayType || "Standard"' in app
    assert 'cpuBayType: current.cpuBayType || "CPU"' in app
    assert 'preassigns Indian Trail orders during an' in store
    preassign = store[store.index('def preassign_bay_for_outbound'):store.index('def reset_stage', store.index('def preassign_bay_for_outbound'))]
    assert 'bay = self.find_bay_for_assignment(con, bay_type)' in preassign
    assert 'or self.find_bay_for_assignment(con, "Standard")' not in preassign
    assert 'manual placement required' in preassign

    # Customer Email Center and the shared Admin modal system use one readable
    # body/supporting scale instead of feature-specific 8-10px operational text.
    assert '--shared-gui-body-size: 13px;' in shared
    assert '--shared-gui-supporting-size: 12px;' in shared
    assert 'v0.352 FULL-GUI TYPOGRAPHY OWNERSHIP' in shared
    assert '.delivery-automation-modal' in shared
    assert '.notification-center-panel' in shared
    assert '#adminModal[data-kind="customerEmails"] .customer-email-editor-v343 header strong' in admin
    assert '#adminModal[data-kind="customerEmails"] .customer-email-search-v343 input' in admin
    assert '.email-activity-detail-v344 :where(p, small, span, em)' in admin


def test_v353_exact_route_geometry_canonical_glass_and_portable_workflow_guidance() -> None:
    """Protect v0.353 compact-card sizing, glass de-duplication, mobile source, and configuration guidance."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    mobile = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Route card takes Lookup Manager width while size containment lets Customer
    # Emails determine the shared desktop row height.
    assert 'customer-route-overview-panel-v353' in index
    v353_css = admin[admin.index('v0.353 exact compact-card geometry'):]
    assert 'grid-column: span 6 !important;' in v353_css
    assert 'contain: size;' in v353_css
    assert 'grid-template-rows: auto minmax(0, 1fr);' in v353_css
    assert '.customer-route-overview-panel-v353 .customer-route-overview-customers-v350 {' in v353_css
    assert 'overflow-y: auto;' in v353_css

    # Default/discovered aliases share one punctuation/spacing-insensitive glass identity.
    assert 'function glassProfileIdentityKeyV353(value = "")' in app
    assert '.replace(/[^a-z0-9]+/gi, "")' in app
    assert 'const key = glassProfileIdentityKeyV353(canonicalLabel);' in app
    assert 'sourceNames.length > 1' in app
    assert '? "combined"' in app
    assert 'const maintainedDefault = source.sources.has("default");' in app

    # The supplied mobile stylesheet is now first-class maintained source and
    # handheld application GUIs inherit a readable text floor.
    assert mobile.startswith('/* File: static/css/mobile.css */')
    assert 'v0.353: align handheld Admin/Operations GUIs' in mobile
    assert '#adminModal:not([hidden])' in mobile
    assert 'static/css/mobile.css?v=20260909-v0.517' in index

    # Lookup Manager explains the portable hierarchy without changing preset IDs.
    assert 'A Station is a scan/work area, not a workflow step.' in app
    assert 'A Stage is a workflow step created for each delivery date.' in app
    assert '["airport_staging", "Staging", "General staging behavior for all applicable orders"]' in app
    assert '["airport_outbound", "Outbound / Shipping", "Shipping gates and transport workflow"]' in app


def test_v354_route_overview_density_scroll_chaining_and_admin_kpi_removal() -> None:
    """Protect v0.354 route-row normalization, ten-row growth, scroll chaining, and dashboard cleanup."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The route card stays at Lookup Manager width but grows naturally until ten
    # CPU-sized rows; fewer-row tabs cannot stretch individual entries.
    assert 'customer-route-overview-panel-v354' in index
    assert 'customer-email-overview-panel-v354' in index
    v354_css = admin[admin.index('v0.354 Customer Route overview density') :]
    assert 'grid-column: span 6 !important;' in v354_css
    assert '--customer-route-overview-row-height-v354: 56px;' in v354_css
    assert 'max-height: 632px;' in v354_css
    assert 'grid-auto-rows: var(--customer-route-overview-row-height-v354);' in v354_css
    assert 'align-content: start;' in v354_css
    assert 'overscroll-behavior-y: auto;' in v354_css
    assert '.customer-email-overview-panel-v354 {' in v354_css

    # All route rows remain in the overview; the ten-row CSS bound introduces
    # scrolling only when the selected route actually has more than ten rules.
    assert 'const visibleRules = routeRules.slice(0, 10);' not in app
    assert 'routeRules.map((rule)' in app
    assert 'data-customer-route-show-more-v350' not in app

    # The obsolete four-stat Admin KPI strip is removed without removing the
    # summary API request, whose data still feeds import and superseded-review state.
    assert 'id="adminSummary"' not in index
    assert 'adminSummary: document.getElementById("adminSummary")' not in app
    assert 'miniStat("Active Delivery Lists"' not in app
    assert 'miniStat("Scans Today"' not in app
    assert 'miniStat("Line Items"' not in app
    assert 'miniStat("Active Users"' not in app
    assert 'fetchJson("/api/admin/summary")' in app


def test_v355_portable_presentation_preserves_stable_engine_identity() -> None:
    """Protect v0.355 cosmetic portability without renaming workflow identifiers."""
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    shell = (ROOT / "static" / "css" / "shell.css").read_text(encoding="utf-8")
    mobile = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Presentation data reuses the existing lookup table and exposes only
    # non-sensitive display context publicly; Admin writes remain permission gated.
    assert 'DEFAULT_PRESENTATION_PROFILE: dict[str, Any]' in store
    assert '"stationAliases": {}' in store
    assert '"supportEmail": "brandon.m.smith@bldr.com"' in store
    assert '"useDefaultBrandLogo": True' in store
    assert "WHERE type = 'presentation_profile' AND value = 'default'" in store
    assert 'if parsed.path == "/api/presentation-profile":' in server
    assert 'STORE.get_presentation_context()' in server
    assert 'if parsed.path == "/api/admin/presentation-profile":' in server
    assert 'self.require_permission("manage_lookup_values")' in server

    # Stable engine identifiers remain untouched while the browser resolves
    # operator-facing station/stage/route names from one presentation layer.
    for preset in ('airport_staging', 'airport_outbound', 'indian_trail', 'greenville', 'cpu', 'dtc'):
        assert f'"{preset}"' in store
    assert 'function stationDisplayLabelV355(station)' in app
    assert 'function roleDisplayLabelV355(roleName = "")' in app
    assert 'const receivingRole = internalName.match(/^Indian Trail\\s+(Operator|Lead|Manager)$/i);' in app
    assert 'function workflowPresentationV355()' in app
    assert 'function portableOperationalTextV355(value = "")' in app
    assert 'data-station-alias-v355' in app
    assert 'id="stationAliasEditorV470"' in app
    assert 'class="icon-only icon-save" title="Save station display name"' in app
    assert 'data-edit-station-alias-v470' in app
    assert 'Internal station binding' in app
    assert 'Use the stable route code. Change the visible route wording in the Routes tab.' in app

    # Station display-name edits do not use the legacy physical-station rename
    # action; that backend identity remains available only to older explicit flows.
    station_block = app[app.index('function stationLookupManagerHtmlV346()'):app.index('function stagePresetOptionsV346')]
    assert 'id="stationAliasEditorV470"' in station_block
    assert 'class="icon-only icon-save"' in station_block
    assert 'data-edit-station-alias-v470' in station_block
    assert 'data-rename-station' not in station_block

    # Company/app identity is configurable, including a safe text-brand fallback
    # for another company without requiring a new logo file.
    assert 'presentationProfileManagerHtmlV355' in app
    assert 'presentationSupportEmailV355' in app
    assert 'presentationUseInstalledLogoV355' in app
    assert 'data-portable-logo-v355' in index
    assert 'data-portable-support-link-v355' in index
    assert 'portable-text-brand-v355' in shell
    assert 'portable-text-brand-v355' in mobile
    assert 'presentation-checkbox-row-v355' in admin

    # Company-specific BFS wording is no longer required by authentication/user UI.
    assert 'Sign in with your email or assigned username to continue.' in index
    assert 'Enter a valid email address' in store
    assert 'Enter a valid BFS email address' not in store

    # Core receiving and Bay Auto Assignment presentation follows configured aliases.
    assert '${escapeHtml(portable.receivingSite)}' in app
    assert '${escapeHtml(portable.outboundStage)}' in app


def test_v0357_reverts_lookup_manager_cosmetic_overhaul():
    """v0.357 must restore the v0.355 Lookup Manager visual implementation exactly."""
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static/css/mobile.css").read_text(encoding="utf-8")
    app_js = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert "v0.356 Lookup Manager visual system" not in admin_css
    assert "lookup-v356-" not in admin_css
    assert "v0.356 Lookup Manager mobile polish" not in mobile_css
    assert "lookup-manager-v356" not in mobile_css
    assert "lookup-manager-v356" not in app_js


def test_v0358_presentation_logo_exclusively_owns_sidebar_branding():
    """v0.358 hides sidebar text/initials whenever the installed Presentation logo is active."""
    app_js = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    shell_css = (ROOT / "static/css/shell.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static/css/mobile.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")


    assert 'document.body.classList.toggle("portable-text-brand-v355", !useInstalledLogo);' in app_js
    assert 'document.body.classList.toggle("portable-installed-logo-v358", useInstalledLogo);' in app_js
    assert 'body.portable-installed-logo-v358 .app-sidebar .portable-sidebar-brand-v355' in shell_css
    assert '[data-portable-brand-initials-v355]' in shell_css
    assert '[data-portable-label-v355="companyName"]' in shell_css
    assert '[data-portable-label-v355="applicationName"]' in shell_css
    assert 'body.portable-installed-logo-v358 .app-sidebar .portable-sidebar-brand-v355' in mobile_css
    # Logo-disabled portability remains intact.
    assert 'body.portable-text-brand-v355 .portable-sidebar-brand-v355' in shell_css
    assert 'body.portable-text-brand-v355 .app-sidebar .portable-sidebar-brand-v355' in mobile_css


def test_v0359_complete_spanish_ui_coverage_and_generated_document_localization():
    """v0.359 keeps current UI, dynamic attributes, errors, dates, and print documents bilingual."""
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The maintained language pack covers representative current workspaces and
    # surfaced errors rather than only the original shell/navigation labels.
    for english, spanish in (
        ('Customer route rules', 'Reglas de rutas de clientes'),
        ('Auto assignment flow', 'Flujo de asignación automática'),
        ('Search customer email activity', 'Buscar actividad de correo del cliente'),
        ('Import run history', 'Historial de ejecuciones de importación'),
        ('Choose a bay before receiving the item.', 'Elija una bahía antes de recibir el artículo.'),
        ('Authentication required', 'Se requiere autenticación.'),
        ('Permission denied', 'Permiso denegado.'),
        ('Runtime refresh is waiting for the active automation run to finish.', 'La actualización en tiempo de ejecución está esperando a que termine la automatización activa.'),
    ):
        assert english in app
        assert spanish in app

    # Spanish mode owns all user-visible/accessibility attributes, including
    # mobile table labels, and keeps translating them after dynamic updates.
    assert 'const attributes = ["placeholder", "title", "aria-label", "alt", "data-label"]' in app
    assert '"[placeholder], [title], [aria-label], [alt], [data-label]' in app
    assert 'attributeFilter: ["placeholder", "title", "aria-label", "alt", "data-label", "label", "value"]' in app

    # Date/time formatters and already-rendered English date strings follow the
    # selected locale during a live language switch.
    assert 'return state.language === "es" ? "es-US" : "en-US";' in app
    assert 'function translateEnglishLocaleDateV359(value)' in app
    assert 'toLocaleDateString(appLocale()' in app
    assert 'toLocaleTimeString(appLocale()' in app
    assert 'toLocaleString(appLocale())' in app

    # Native confirmations and separate popup/print documents do not bypass the
    # main DOM translation observer.
    assert 'window.confirm(localizedUiValue("Disable both delivery-list automation scheduled tasks' in app
    assert 'function translateStandaloneDocumentV359(doc)' in app
    assert 'translateStandaloneDocumentV359(win.document);' in app
    assert 'translateStandaloneDocumentV359(printWindow.document);' in app


def test_v0360_reversible_glass_profile_combining_and_alias_resolution():
    """v0.360 combines duplicate glass names without rewriting historical product text."""
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static/css/mobile.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # UI keeps one profile and lets administrators choose same-family aliases.
    assert 'function glassProfileCombinePanelV360' in app
    assert 'function glassProfileCombinePanelV360' in app
    assert 'data-glass-combine-save-v360' in app
    assert 'data-glass-combine-alias-v360' in app
    assert '.filter((profile) => profile.family === target.family)' in app
    assert 'function saveGlassProfileCombinationV360' in app
    assert '/api/admin/manual-edit-lookups/glass-profile/combine' in app

    # Alias resolution is shared by normal glass labels/colors, not only the modal.
    assert 'function glassAliasTargetV360' in app
    assert 'const combined = glassAliasTargetV360(sourceRaw) || backendCanonical || sourceRaw;' in app
    assert 'return canonicalClearGlassLabelV460(combined) || combined;' in app
    assert 'const aliasTarget = glassAliasTargetV360(source.value) || source.value;' in app
    assert 'const label = glassAliasTargetV360(rawLabel) || rawLabel;' in app

    # Backend persists aliases in the existing generic table and reporting consumes them.
    assert 'def combine_glass_profiles' in store
    assert "VALUES ('glass_alias', ?, ?, '', '', 1, 'manual', ?, ?)" in store
    assert 'effective_glass_aliases' in store
    assert 'glass_cost_profile(raw_product, effective_glass_costs, effective_glass_aliases)' in store
    assert '"glassAliases": glass_aliases' in store
    assert 'glassAliases: Array.isArray(payload?.glassAliases)' in app
    assert 'STORE.combine_glass_profiles' in server
    assert 'glass-profile/combine' in server
    assert 'historical line-item' in app.lower()

    # Desktop/mobile styling and Spanish coverage ship with the workflow.
    assert '.glass-combine-panel-v360' in admin_css
    assert '.glass-combine-panel-v360' in mobile_css
    assert '["Combine selected", "Combinar seleccionados"]' in app
    assert 'Already combined into' in app
    assert 'Ya combinado en' in app


def test_v0361_stable_superseded_filters_and_header_glass_multi_select_combine():
    """v0.361 removes filter repaint flashes and makes Glass Type combine a library-level multi-select workflow."""
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static/css/mobile.css").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Superseded filters no longer replace the entire Admin modal body.
    assert 'function renderSupersededReviewFilterV361()' in app
    assert 'data-superseded-review-list-v361' in app
    superseded_handler = app[app.index('const supersededFilterButton = event.target.closest("[data-superseded-filter]")'):]
    superseded_handler = superseded_handler[:superseded_handler.index('const supersededDecisionButton')]
    assert 'renderSupersededReviewFilterV361();' in superseded_handler
    assert 'els.adminModalBody.innerHTML = supersededOrderReviewModalHtml()' not in superseded_handler
    assert '.superseded-review-tabs button:active' in admin_css
    assert '-webkit-tap-highlight-color: transparent' in admin_css

    # Combine starts from the Glass Type Library header and rows become selectable.
    assert 'data-glass-combine-mode-v361' in app
    assert 'Combine Glass Types' in app
    assert 'data-glass-combine-select-v361' in app
    assert 'data-glass-combine-apply-v361' in app
    assert 'function toggleGlassProfileCombineSelectionV361' in app
    assert 'function syncGlassProfileCombineSelectionUiV361' in app
    assert 'function saveSelectedGlassProfilesV361' in app
    assert 'selectedProfiles[0]' in app
    assert 'profile.family !== target.family' in app
    assert '/api/admin/manual-edit-lookups/glass-profile/combine' in app
    assert '.is-combine-selectable-v361' in admin_css
    assert '.is-combine-keep-v361' in admin_css
    assert '.glass-library-header-actions-v361' in mobile_css

    # Per-row action buttons no longer expose the broken v0.360 combine entry point.
    row_block = app[app.index('function glassProfileRowHtmlV349'):app.index('function glassProfileCombinePanelV360')]
    assert 'data-glass-profile-combine-v360' not in row_block
    assert 'data-glass-profile-edit-v349' in row_block
    assert 'data-glass-profile-remove-v349' in row_block


def test_v0362_language_safe_combine_and_library_uncombine():
    """v0.362 keeps interactive combine text language-aware and adds reversible library-level uncombine."""
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static/css/mobile.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The click-time selection labels must respect the active language rather
    # than invoking the Spanish translator unconditionally.
    combine_sync = app[app.index('function syncGlassProfileCombineSelectionUiV361'):app.index('/** v0.361: Toggle one Glass Type Library row')]
    assert 'localizedUiValue(keep ? "Keep" : selected ? "Merge" : "Select")' in combine_sync
    assert 'localizedUiValue(keep ? "Canonical profile"' in combine_sync
    assert 'translatedUiValue(keep ? "Keep"' not in combine_sync

    # Uncombine is a first-class header action and multi-select mode.
    assert 'data-glass-uncombine-mode-v362' in app
    assert 'Uncombine Glass Types' in app
    assert 'data-glass-uncombine-select-v362' in app
    assert 'data-glass-uncombine-apply-v362' in app
    assert 'function toggleGlassProfileUncombineSelectionV362' in app
    assert 'function syncGlassProfileUncombineSelectionUiV362' in app
    assert 'function uncombineSelectedGlassProfilesV362' in app
    assert '/api/admin/manual-edit-lookups/glass-profile/uncombine' in app
    assert '.is-uncombine-selectable-v362' in admin_css
    assert '.is-uncombine-selected-v362' in admin_css
    assert 'Uncombine shares the touch-first Glass Type selection geometry' in mobile_css

    # Backend separation is atomic, audited, schema-neutral, and never rewrites
    # historical line-item product values.
    assert 'def uncombine_glass_profiles' in store
    assert "UPDATE admin_lookup_values SET is_active = 0, source = 'manual-hidden'" in store
    assert '"uncombine_glass_profiles"' in store
    assert 'STORE.uncombine_glass_profiles' in server
    assert 'glass-profile/uncombine' in server

    # Both new interaction modes have Spanish coverage while English remains
    # the source markup for the normal English UI.
    assert '["Uncombine Glass Types", "Separar tipos de vidrio"]' in app
    assert '["Uncombine selected", "Separar seleccionados"]' in app
    assert '["Select at least one combined glass type to uncombine.", "Seleccione al menos un tipo de vidrio combinado para separar."]' in app



def test_v0424_global_search_polish_and_bay_manual_quantity() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    bays = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    mobile = (ROOT / "static/css/mobile.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.424 - Global Search Polish and Bay Manual Quantity' in changelog

    assert 'id="headerGlobalSearchBtn"' not in index
    assert 'headerGlobalSearchBtn:' not in app
    assert 'els.headerGlobalSearchBtn?.addEventListener' not in app
    assert 'header-search header-search-v424' in index
    assert 'v0.424 Global Search polish' in styles
    assert 'width: min(680px, 100%) !important;' in styles
    assert 'grid-template-columns: minmax(0, 1fr) !important;' in mobile[mobile.rindex('v0.424: the live global search'):]

    assert 'id="bayManualQtyInput" type="number" min="1" max="999"' in index
    assert 'aria-label="Manual scan quantity"' in index
    assert 'Qty applies when adding pieces to a bay.' in index
    assert 'v0.424 Bay Scanner manual quantity' in bays
    assert 'grid-template-columns: minmax(0, 1fr) 70px 104px !important;' in bays
    assert 'async function runBayScan(barcode, { isManual = false, scanQty = 1,' in app
    assert 'scanQty: isManual ? requestedScanQty : 1,' in app
    assert 'return runBayScan(cleanBarcode, { isManual, scanQty: requestedScanQty, outboundOverride: true' in app
    manual_block = app[app.index('async function submitManualBayScan()'):app.index('function selectedBayAssignment()')]
    assert 'const scanQty = adding ? Math.trunc(Number(els.bayManualQtyInput?.value || 1)) : 1;' in manual_block
    assert 'runBayScan(reference.barcode, { isManual: true, scanQty })' in manual_block
    assert 'els.bayManualQtyInput.value = "1";' in manual_block


def test_v0425_global_search_result_card_hierarchy_and_priority_metadata() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.425 - Global Search Result Card Cleanup' in changelog

    # Search payload carries the exact changed delivery date plus aggregated
    # priority flags across stage copies without introducing a schema change.
    assert '"priorityDeliveryDate": str(row_value(row, "priority_delivery_date", "") or "")' in store
    assert 'result["rush"] = bool(result.get("_rush"))' in store
    assert 'result["remake"] = bool(result.get("_remake"))' in store

    # Global Search waits for the shared glass-color library and renders the
    # requested four-row card hierarchy in the requested left-to-right order.
    search_block = app[app.index('async function runGlobalSearch()'):app.index('function globalSearchProcessClass')]
    assert 'ensureGlassVisualLookupLibrary().catch(() => [])' in search_block
    render_block = app[app.index('function renderGlobalSearchResults(results)'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'global-result-primary-v426' in render_block
    assert 'global-result-order-v426' in render_block
    assert 'Job:</b>' in render_block
    assert 'global-result-customer-v426' in render_block
    assert 'global-result-glass-v426' in render_block
    assert 'global-result-size-v426' in render_block
    assert 'Qty:</b>' in render_block
    assert 'global-result-glass-text-v426' in render_block
    assert 'glassToneAttributes(glassLabel)' in render_block
    assert 'DD:</b>' in render_block
    assert '<em>Changed to</em>' in render_block
    assert 'globalSearchPriorityFlagsV425(result)' in render_block
    assert 'Route:</b>' in render_block
    assert 'Progress:</b>' in render_block
    assert 'global-result-progress-v513' in render_block
    assert 'globalSearchProgressStepsV513(result, fabrication)' in app
    assert 'formatOperationalTimestampV511(stage.timestamp)' in app
    assert '["Changed to", "Cambió a"]' in app

    assert 'v0.426 Compact text-only Global Search results' in styles
    assert 'padding: 6px 9px !important;' in styles
    assert 'gap: 0 !important;' in styles
    assert '.global-result-flag-v425.is-rush' in styles
    assert '.global-result-flag-v425.is-remake' in styles
    assert '.global-result-stage-v426' in styles


def test_v0426_global_search_compact_text_rows() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.426 - Compact Text Global Search Results' in changelog

    render_block = app[app.index('function renderGlobalSearchResults(results)'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'global-result-line-v426' in render_block
    assert 'global-result-primary-v426' in render_block
    assert 'global-result-glass-v426' in render_block
    assert 'global-result-delivery-v426' in render_block
    assert 'global-result-stage-cell-v430' in render_block
    assert 'Job:</b>' in render_block
    assert 'Qty:</b>' in render_block
    assert 'Route:</b>' in render_block
    assert 'Progress:</b>' in render_block
    assert 'globalSearchPriorityFlagsV425(result)' in render_block
    assert 'glassToneAttributes(glassLabel)' in render_block
    assert 'globalSearchProgressMarkupV476(result, fabricationV474)' in render_block
    assert 'global-result-progress-step-v513' in app
    assert 'formatOperationalTimestampV511(stage.timestamp)' in app

    compact = styles[styles.index('v0.426 Compact text-only Global Search results'):]
    assert 'padding: 6px 9px !important;' in compact
    assert 'gap: 0 !important;' in compact
    assert 'border-radius: 0 !important;' in compact
    assert 'box-shadow: none !important;' in compact
    assert 'transform: none !important;' in compact
    assert 'text-decoration-color: var(--glass-type-color) !important;' in compact
    assert 'background: transparent !important;' in compact
    assert 'font-size: 9.5px !important;' in compact


def test_v0427_global_search_labels_and_twenty_result_cap() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.427 - Compact Global Search Labels and 20 Results' in changelog

    render_block = app[app.index('function renderGlobalSearchResults(results)'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert '.slice(0, 20)' in render_block
    assert store.count('return cleaned_results[:20]') == 1
    assert 'if self.global_search_result_matches(result, terms)' in store
    assert '<b class="global-result-inline-label-v427">Size:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">Qty:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">Type:</b>' in render_block
    assert 'global-result-type-v427' in render_block
    assert 'glassToneAttributes(glassLabel)' in render_block

    assert 'v0.427: keep the compact glass row text-first' in styles
    assert '.global-result-inline-label-v427' in styles
    assert '.global-result-type-v427' in styles
    assert 'text-decoration-color: var(--glass-type-color) !important;' in styles


def test_v0428_global_search_consistent_compact_polish() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.428 - Consistent Compact Global Search Polish' in changelog

    render_block = app[app.index('function renderGlobalSearchResults(results)'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert '.slice(0, 20)' in render_block
    assert '<b class="global-result-inline-label-v427">Customer:</b>' in render_block
    assert 'global-result-progress-v513' in render_block
    assert 'globalSearchProgressMarkupV476(result, fabricationV474)' in render_block
    assert '<b class="global-result-inline-label-v427">Job:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">DD:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">Route:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">Progress:</b>' in render_block

    assert 'v0.428 Consistent compact Global Search polish' in styles
    assert 'box-shadow: inset 2px 0 0 #d9e4ef !important;' in styles
    assert 'border-left: 1px solid #dce4ed !important;' in styles
    assert 'background: #f3f7fb !important;' in styles
    assert '["Customer:", "Cliente:"]' in app
    assert '["Scanned:", "Escaneado:"]' in app
    assert '["ON TIME:", "A TIEMPO:"]' in app
    assert '["LATE:", "TARDE:"]' in app


def test_v0429_global_search_polished_record_strips() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.429 - Polished Compact Smart Search Record Strips' in changelog

    render_block = app[app.index('function renderGlobalSearchResults(results)'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert '.slice(0, 20)' in render_block
    assert 'global-result-primary-v426' in render_block
    assert 'global-result-glass-v426' in render_block
    assert 'global-result-delivery-v426' in render_block
    assert 'global-result-stage-cell-v430' in render_block
    assert '<b class="global-result-inline-label-v427">Size:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">Type:</b>' in render_block
    assert '<b class="global-result-inline-label-v427">Route:</b>' in render_block
    assert 'function globalSearchPriorityFlagsV425(result)' in app

    polished = styles[styles.index('v0.429 Polished compact Smart Search record strips'):]
    assert 'font-size: 14.5px !important;' in polished
    assert 'font-size: 11.75px !important;' in polished
    assert 'border-top: 1px solid #eef2f6 !important;' in polished
    assert 'gap: 10px !important;' in polished
    assert 'background: var(--glass-type-color) !important;' in polished
    assert '.global-result-glass-text-v426::before' in polished
    assert '.global-result-status::before' in polished
    assert 'border-radius: 3px !important;' in polished
    assert 'background: #fff7e3 !important;' in polished
    assert 'background: #fff1f1 !important;' in polished


def test_v0430_global_search_color_cells_and_focus_recall() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.430 - Color-Coded Smart Search Cells and Focus Recall' in changelog

    search_block = app[app.index('async function runGlobalSearch()'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'state.globalSearchLastQuery = query;' in search_block
    assert 'state.globalSearchLastResults = results;' in search_block
    assert 'globalSearchStageColorV430(result)' in search_block
    assert 'globalSearchRouteColorV430(result.route)' in search_block
    assert 'is-scanned-v430' in search_block
    assert 'global-result-cell-v430' in search_block
    assert 'global-result-type-cell-v430' in search_block
    assert 'global-result-route-cell-v430' in search_block
    assert 'global-result-flag-cell-v430' in app
    assert 'global-result-stage-cell-v430' in search_block
    assert '.slice(0, 20)' in search_block

    listeners = app[app.index('els.headerGlobalSearchInput?.addEventListener("input"'):app.index('els.homeListSearch?.addEventListener("input"')]
    assert 'addEventListener("focus"' in listeners
    assert 'state.globalSearchLastQuery === query' in listeners
    assert 'els.headerGlobalSearchResults.hidden = false;' in listeners
    assert 'runGlobalSearch().catch' in listeners

    polished = styles[styles.index('v0.430 Color-coded Smart Search cells and scanned-stage gradients'):]
    assert '.global-result-record-v430.is-scanned-v430' in polished
    assert 'var(--global-stage-color)' in polished
    assert 'global-result-type-cell-v430' in polished
    assert 'var(--glass-type-color)' in polished
    assert 'global-result-route-cell-v430' in polished
    assert 'var(--global-route-color)' in polished
    assert 'global-result-flag-cell-v430.is-rush' in polished
    assert 'global-result-flag-cell-v430.is-remake' in polished
    assert 'margin: 0 0 3px !important;' in polished


def test_v0431_smart_search_neutral_records_stable_recall_and_forward_stage_counters() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.431 - Smart Search Color Ownership, Stable Recall, and Forward View Stage Counters' in changelog

    search = app[app.index('async function runGlobalSearch()'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'const stageColor = hasScan ? globalSearchStageColorV430(result) : "#94a3b8";' in search
    assert 'global-result-route-cell-v430' in search
    assert 'global-result-stage-cell-v430' in search
    assert '.slice(0, 20)' in search

    listeners = app[app.index('els.headerGlobalSearchInput?.addEventListener("input"'):app.index('const rackHeaderAction')]
    assert '!event.target.closest(".header-search")' in listeners
    assert '!event.target.closest(".global-search")' not in listeners

    polished = styles[styles.index('v0.431 Neutral Smart Search records + independent semantic cells'):]
    assert 'background: #ffffff !important;' in polished
    assert '.global-result-route-cell-v430' in polished
    assert 'var(--global-route-color)' in polished
    assert '.is-unscanned-v430 .global-result-stage-cell-v430' in polished
    assert 'background: linear-gradient(180deg, #f1f4f7 0%, #e8edf2 100%) !important;' in polished
    assert 'box-shadow: 0 2px 5px rgba(20, 42, 67, .065) !important;' in polished

    assert 'function homeForwardStageCountersV431' in app
    assert '["staged", "STG"]' in app
    assert '["outbound", "OUT"]' in app
    assert '["received", "IN"]' in app
    assert '["pickup", "CPU"]' in app
    assert '["greenville", "GNV"]' in app
    assert '["dtc", "DTC"]' in app
    assert 'home-forward-stage-counters-v431' in app
    assert 'home-forward-stage-counter-v431' in app

    # v0.457 keeps the older global replay helper removed and also removes the
    # v0.456 Home-only forced reflow. Native [open] state now replays cleanly.
    assert 'void details.offsetWidth;' not in app
    assert 'replayExpandableListAnimation(details);' not in app
    assert 'restartHomeDeliveryExpandAnimationV456(details);' not in app
    home_polish = home[home.index('v0.431 Forward View per-stage counters + stable Delivery Library expansion'):]
    assert '@keyframes home-delivery-expand-v431' in home_polish
    assert 'opacity:' not in home_polish[home_polish.index('@keyframes home-delivery-expand-v431'):home_polish.index('@media (prefers-reduced-motion: reduce)')]
    assert 'grid-template-columns: repeat(3, minmax(0, 1fr)) !important;' in home_polish


def test_v0432_smart_search_readability_delivery_toggle_and_forward_icons() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    home = (ROOT / "static/css/home.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.432 - Smart Search Readability, Stable Delivery Dropdowns, and Forward View Icons' in changelog

    search = app[app.index('function globalSearchRouteColorV430'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert '["IT", "INDIAN TRAIL", "INDIAN-TRAIL"]' in search
    assert 'return "#3aa667";' in search
    assert 'global-result-route-cell-v430' in search
    assert '<b class="global-result-inline-label-v427">Flags:</b>' in search
    assert ': "None";' in search
    assert 'is-both' in search
    assert '["Flags:", "Indicadores:"]' in app
    assert '["None", "Ninguna"]' in app

    polish = styles[styles.index('v0.432 Smart Search readability + true semantic cells'):]
    assert 'font-size: 12.75px !important;' in polish
    assert 'font-size: 14.75px !important;' in polish
    assert 'span.global-result-route-v425.global-result-route-cell-v430' in polish
    assert 'border-style: solid !important;' in polish
    assert 'box-shadow: inset 3px 0 0 var(--global-route-color) !important;' in polish
    assert '.global-result-flag-cell-v430.is-none' in polish
    assert '.global-result-flag-cell-v430.is-both' in polish
    assert '.is-unscanned-v430 .global-result-stage-v426' in polish
    assert 'background: transparent !important;' in polish
    assert 'box-shadow: inset 3px 0 0 #9aa8b7 !important;' in polish

    toggle_listener = app[app.index('document.addEventListener("toggle"'):app.index('els.loginForm?.addEventListener("submit"')]
    assert 'replayExpandableListAnimation(details);' not in toggle_listener
    assert 'Home Delivery Library uses one CSS-owned expansion animation.' in toggle_listener

    home_polish = home[home.index('v0.432 Forward View icons, stable library toggle, and larger Home greeting'):]
    assert '--forward-stage-icon:' in home_polish
    assert '.home-forward-stage-counter-v431 > i::before' in home_polish
    assert 'font-size: 11.5px !important;' in home_polish
    assert '.home-forward-stage-counter-v431.outbound' in home_polish
    assert '.home-forward-stage-counter-v431.received' in home_polish
    assert '.home-forward-stage-counter-v431.pickup' in home_polish
    assert '.home-forward-stage-counter-v431.greenville' in home_polish
    assert '.home-forward-stage-counter-v431.dtc' in home_polish
    assert 'font-size: 48px !important;' in home_polish
    assert 'font-size: 30px !important;' in home_polish


def test_v0433_smart_search_matches_reference_card_layout() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.433 - Smart Search Reference-Style Redesign' in changelog

    search = app[app.index('function globalSearchIconV433'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'global-result-reference-card-v433' in search
    assert 'global-result-leading-icon-v433' in search
    assert 'global-result-primary-v433' in search
    assert 'global-result-glass-v433' in search
    assert 'global-result-chips-v433' in search
    assert 'globalSearchIconV433("calendar")' in search
    assert 'globalSearchIconV433("flag")' in search
    assert 'globalSearchIconV433("route")' in search
    assert 'globalSearchIconV433("clock")' in search
    assert '<b class="global-result-inline-label-v427">Job:</b>' in search
    assert '.slice(0, 20)' in search

    polish = styles[styles.index('v0.433 Smart Search reference-card layout'):]
    assert 'grid-template-columns: 48px minmax(0, 1fr) !important;' in polish
    assert 'font-size: 19px !important;' in polish
    assert 'border-bottom: 1px solid #e3e9f0 !important;' in polish
    assert '.global-result-type-chip-v433' in polish
    assert '.global-result-dd-chip-v433' in polish
    assert 'span.global-result-route-v425.global-result-route-cell-v430' in polish
    assert '.global-result-stage-cell-v430' in polish
    assert 'background: #ffffff !important;' in polish
    assert 'width: min(980px, 100%) !important;' in polish


def test_v0434_smart_search_reference_cards_are_compact() -> None:
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.434 - Compact Smart Search Reference Cards' in changelog

    compact = styles[styles.index('v0.434 Compact Smart Search reference cards'):]
    assert 'grid-template-columns: 34px minmax(0, 1fr) !important;' in compact
    assert 'margin: 0 0 4px !important;' in compact
    assert 'padding: 8px 10px !important;' in compact
    assert 'width: 32px !important;' in compact
    assert 'height: 32px !important;' in compact
    assert 'grid-template-columns: minmax(122px, .72fr) minmax(150px, 1fr) minmax(165px, 1.12fr) !important;' in compact
    assert 'font-size: 15.5px !important;' in compact
    assert 'font-size: 11.4px !important;' in compact
    assert 'min-height: 22px !important;' in compact
    assert 'min-height: 23px !important;' in compact
    assert 'gap: 5px !important;' in compact


def test_v0435_smart_search_is_larger_and_stage_coded() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.435 - Larger Smart Search and Stage-at-a-Glance Results' in changelog

    search = app[app.index('function globalSearchStageKeyV435'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'airport_staging: "staging"' in search
    assert 'airport_outbound: "outbound"' in search
    assert 'indian_trail: "received"' in search
    assert 'cpu: "cpu"' in search
    assert 'greenville: "greenville"' in search
    assert 'dtc: "dtc"' in search
    assert 'stageIconV435' in search
    assert 'global-result-stage-${escapeHtml(stageKeyV435)}-v435' in search
    assert 'globalSearchIconV433(stageIconV435)' in search
    assert 'staging: `<svg' in search
    assert 'outbound: `<svg' in search
    assert 'received: `<svg' in search
    assert 'cpu: `<svg' in search
    assert 'greenville: `<svg' in search
    assert 'dtc: `<svg' in search

    polish = styles[styles.index('v0.435 Larger Smart Search + stage-at-a-glance cards'):]
    assert 'width: min(960px, 100%) !important;' in polish
    assert 'min-height: 60px !important;' in polish
    assert 'font-size: 19.5px !important;' in polish
    assert 'grid-template-columns: 40px minmax(0, 1fr) !important;' in polish
    assert 'font-size: 17.25px !important;' in polish
    assert '.global-result-reference-card-v433.is-scanned-v430' in polish
    assert 'color-mix(in srgb, var(--global-stage-color) 9%, #ffffff)' in polish
    assert '.global-result-reference-card-v433.is-unscanned-v430' in polish
    assert 'background: #ffffff !important;' in polish
    assert '.global-result-leading-stage-icon-v435' in polish



def test_v0436_smart_search_is_wider_not_taller_and_job_gets_more_room() -> None:
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.436 - Wider Smart Search Without Added Header Height' in changelog

    polish = styles[styles.index('v0.436 Wider Smart Search without added header height'):]
    assert 'grid-template-columns: minmax(260px, 1fr) minmax(640px, 980px) minmax(260px, 1fr) !important;' in polish
    assert 'width: min(980px, 100%) !important;' in polish
    assert 'min-height: 56px !important;' in polish
    assert 'min-height: 54px !important;' in polish
    assert 'height: 54px !important;' in polish
    assert 'font-size: 18px !important;' in polish
    assert 'grid-template-columns: minmax(140px, .52fr) minmax(250px, 1.25fr) minmax(220px, 1fr) !important;' in polish
    assert 'gap: 10px !important;' in polish
    assert '@media (max-width: 780px)' in polish
    assert 'height: 48px !important;' in polish



def test_v0437_global_search_is_shorter_and_less_wide() -> None:
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.437 - Reduced Global Search Footprint' in changelog

    polish = styles[styles.index('v0.437 Reduced Global Search footprint'):]
    assert 'width: min(690px, 100%) !important;' in polish
    assert 'max-width: 690px !important;' in polish
    assert 'minmax(520px, 690px)' in polish
    assert 'min-height: 36px !important;' in polish
    assert 'min-height: 34px !important;' in polish
    assert 'height: 34px !important;' in polish
    assert 'font-size: 17px !important;' in polish
    assert 'min-height: 42px !important;' in polish
    assert 'height: 42px !important;' in polish


def test_v0438_search_width_identity_spacing_and_unscanned_icon() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.438 - Wider Identity Space and Distinct Unscanned Icon' in changelog

    polish = styles[styles.index('v0.438 Wider Smart Search + tighter identity row'):]
    assert 'width: min(795px, 100%) !important;' in polish
    assert 'max-width: 795px !important;' in polish
    assert 'minmax(590px, 795px)' in polish
    assert 'grid-template-columns: minmax(112px, .42fr) minmax(220px, 1.24fr) minmax(240px, 1.38fr) !important;' in polish
    assert 'gap: 6px !important;' in polish
    assert 'min-height: 36px !important;' not in polish  # v0.438 must not alter v0.437 height

    search = app[app.index('function globalSearchIconV433'):app.index('function globalSearchPriorityFlagsV425')]
    assert 'unscanned: `<svg' in search
    assert 'M7 4H4v3' in search
    renderer = app[app.index('function renderGlobalSearchResults'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert ': "unscanned";' in renderer




def test_v0439_lookup_stage_label_paired_scan_time_and_richer_stage_colors() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.439 - Lookup Stage Labels and Paired Scan Status' in changelog

    search = app[app.index('function globalSearchStageColorV430'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'function globalSearchStageDisplayNameV439' in search
    assert 'state.manualEditLookups?.stages' in search
    assert 'configuredStageByPresetV355' in search
    assert 'function globalSearchScanDateTimeV439' in search
    assert 'minute: "2-digit"' in search
    assert 'second:' not in search
    # v0.440 combines the previously paired v0.439 Stage/Scanned cells into one cell.
    assert 'global-result-stage-scan-cell-v440' in search
    assert 'globalSearchProgressStepsV513' in search
    assert 'stage.lastScanTime || stage.lastScannedAt || ""' in search
    assert 'staging: "#4d74e6"' in search
    assert 'outbound: "#d89a1f"' in search

    polish = styles[styles.index('v0.439 Lookup stage labels + paired scan status + richer stage accents'):]
    assert '.global-result-stage-scan-v439' in polish
    assert 'margin-left: auto !important;' in polish
    assert 'white-space: nowrap !important;' in polish
    assert 'color-mix(in srgb, var(--global-stage-color) 18%, #ffffff)' in polish
    assert 'color-mix(in srgb, var(--global-stage-color) 22%, #ffffff)' in polish



def test_v0440_combined_stage_scan_cell_and_clearer_card_stage_wash() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.440 - Combined Stage Status and Clearer Stage-Tinted Search Results' in changelog

    renderer = app[app.index('function renderGlobalSearchResults'):app.index('Purpose: Build the date-aware Indian Trail API suffix')]
    assert 'global-result-stage-scan-cell-v440' in renderer
    assert 'global-result-progress-v513' in renderer
    assert 'globalSearchProgressMarkupV476(result, fabricationV474)' in renderer
    assert 'global-result-progress-step-v513' in app
    assert 'globalSearchStageDisplayNameV439' in app
    assert 'formatOperationalTimestampV511(stage.timestamp)' in app
    assert 'global-result-stage-scan-v439' not in renderer
    assert 'global-result-scan-time-v426 global-result-chip-v433' not in renderer

    polish = styles[styles.index('v0.440 Combined Stage/Scanned cell + clearer stage-tinted result cards'):]
    assert '.global-result-stage-scan-cell-v440' in polish
    assert 'color-mix(in srgb, var(--global-stage-color) 16%, #ffffff)' in polish
    assert 'color-mix(in srgb, var(--global-stage-color) 10%, #ffffff)' in polish
    assert 'box-shadow: inset 3px 0 0' in polish
    assert '.global-result-reference-card-v433.is-unscanned-v430' in polish
    assert 'background: #ffffff !important;' in polish


def test_v0441_priority_ribbons_date_move_trace_and_rack_location_continuity() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.441 - Priority Ribbons, Rush Date Trace Rows, and Rack Location Continuity' in changelog

    # Backend exposes exact line-level priority metadata and keeps date-move
    # references traceable without duplicating physical quantities in SQLite.
    assert 'def priority_banner_annotations' in store
    assert 'action in {"mark_rush_sdi", "mark_remake_sdi"}' in store
    annotation_block = store[store.index('def priority_banner_annotations'):store.index('def attach_priority_search_annotations')]
    assert '"kind": "missing_glass_rush"' not in annotation_block
    assert '"kind": "both"' in annotation_block
    assert '"label": "Rush + Remake"' in annotation_block
    assert '"reason": "Imported A+W RM marker"' in store
    assert 'reference["priorityBanner"] = annotation' in store
    assert 'item["priorityBanner"] = annotation' in store
    assert 'is_rush_item(priority_item) or is_remake_item(priority_item)' in store

    # The original date remains as a disabled gray trace row and the requested
    # date receives a full read-only reference row with its own priority ribbon.
    assert 'function priorityDateMovedOutV441' in app
    assert 'item?.priorityBanner || isRushItem(item || {}) || isRemakeItem(item || {})' in app
    assert 'function priorityBannerMetaV441' in app
    assert 'function priorityItemRibbonV441' in app
    assert 'Original ${formatDisplayDate(originalDate)} line kept inactive for tracking' in app
    assert 'Moved here from ${formatDisplayDate(originalDate)} · Active on ${formatDisplayDate(targetDate)}' in app
    assert 'priority-date-moved-target-row-v441' in app
    assert 'is-priority-date-moved-source-v441' in app
    assert 'data-priority-moved-reference=' in app
    assert 'data-priority-moved-source=' in app

    # Indian Trail now falls back to transport-rack text when a receiving bay is
    # not present, so the existing rack color is never an unlabeled color block.
    location = app[app.index('function scanLocationPresentation'):app.index('function locationLabel')]
    assert 'const inboundRackCode = String(currentItem.rackCode || "").trim().toUpperCase();' in location
    assert 'rackLocationDisplayLabel(inboundRackCode, currentItem.rackName, currentItem.rackType)' in location
    assert 'Transported to Indian Trail in ${inboundRack}.' in location
    assert 'const inboundPreviousRack = rackHistoryLocationLabel(currentItem);' in location

    # Priority ribbons and inactive/target rows have dedicated compact styling.
    assert '.priority-line-ribbon-v441' in scan_css
    assert '.priority-line-ribbon-v441.is-remake' in scan_css
    assert '.priority-line-ribbon-v441.is-both' in scan_css
    assert '.is-priority-date-moved-source-v441' in scan_css
    assert '.priority-date-moved-target-row-v441' in scan_css

    # RM markers are contained in both the delivery-list Flags cell and Smart
    # Search so no pseudo-element/overflow dot can appear beside the black cell.
    assert 'td:nth-child(7) .row-marker.remake-marker' in scan_css
    assert '.row-marker.remake-marker::after' in scan_css
    assert 'span.global-result-flag-v425.global-result-flag-cell-v430.is-remake' in styles
    assert 'global-result-flag-cell-v430.is-remake::after' in styles



def test_v0442_indian_trail_bay_visibility_and_status_aware_manual_selector() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.442 - Indian Trail Bay Visibility and Status-Aware Placement' in changelog

    # Active bay assignment status is surfaced so the frontend can distinguish
    # a PRE reservation from a physically received Indian Trail location.
    assert 'ba.status AS bay_status' in store
    assert 'item["bayStatus"] = str(bay["bay_status"] or "")' in store
    location = app[app.index('function scanLocationPresentation'):app.index('function locationLabel')]
    assert 'const currentBayStatus = String(currentItem.bayStatus || "").trim().toLowerCase();' in location
    assert 'const physicallyReceivedHere = Number(currentItem.scanned || 0) > 0' in location
    assert 'kind: "preassigned"' in location
    assert 'Preassigned to ${currentBay}; scan Indian Trail to confirm the physical bay.' in location
    assert 'location-preassigned-v442' in app

    # Manual bay selection shows every live bay with a compact state badge and
    # a successful one-scan manual override resets visible + internal state.
    assert 'function bayTargetStatusMetaV442' in app
    assert 'occupied: { abbr: "OCC", label: "Occupied" }' in app
    assert 'preassigned: { abbr: "PRE", label: "Pre Assigned" }' in app
    assert '.filter((bay) => bay?.active !== false && bayCategoryKind(bay) !== "spacer")' in app
    assert 'data-bay-status-badge=' in app
    assert 'text = text.replace(/-{2,}/g, "-");' in app
    assert 'function resetScanBayOverrideToAutoV443' in app
    assert 'resetScanBayOverrideToAutoV443' in app
    assert '.bay-target-status-badge-v442.is-occupied' in styles
    assert '.bay-target-status-badge-v442.is-preassigned' in styles

    # Location layout reserves readable space for PRE/PRIOR and individual Rack
    # date counts use the same content typography with singular/plural support.
    assert 'td.location-cell { width: 11% !important; }' in scan_css
    assert '.location-history-prior-v442' in scan_css
    assert '.location-badge.has-explicit-prior-v442::after' in scan_css
    assert 'rack-modal-date-count-v442' in app
    assert 'line${rows.length === 1 ? "" : "s"}' in app
    assert '.rack-details-modal-v184 .rack-modal-date-count-v442' in styles


def test_v0443_exact_print_preview_stage_icons_and_manual_bay_refresh() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.444 - Exact Print Preview, Stage Icons, and Reliable Indian Trail Manual Bay Receipt' in changelog

    # Smart Search uses the exact Home/Delivery Library stage glyph paths.
    icons = app[app.index('function globalSearchIconV433'):app.index('function globalSearchPriorityFlagsV425')]
    assert 'M6.5 17.5 17.5 6.5M11 6.5h6.5V13' in icons
    assert 'M6.5 6.5 17.5 17.5M17.5 11v6.5H11' in icons
    assert 'M12 12a3.6 3.6 0 1 0 0-7.2' in icons
    assert 'M4.5 20V9.5L12 5l7.5 4.5V20' in icons

    # Screen preview and popup print share page markup and physical Letter geometry.
    assert 'print-preview-page-shell-v443' in app
    assert 'printSheetPageMarkup(sheet, chunk' in app
    assert 'static/css/print.css?v=20260910-v0.527' in app
    assert '.print-preview-page-shell-v443 {' in print_css
    assert 'width: 8.5in;' in print_css
    assert 'height: 11in;' in print_css
    assert 'padding: .4in;' in print_css
    assert 'height: 10.2in !important;' in print_css
    assert 'height: 7.7in !important;' in print_css

    # Historical rack markers stack instead of squeezing rack name + PRIOR side-by-side.
    vertical = scan_css[scan_css.index('v0.443 vertical historical rack marker'):]
    assert 'grid-template-columns: minmax(0, 1fr) !important;' in vertical
    assert 'grid-template-rows: auto auto !important;' in vertical

    # Delivery-list bay lookup follows line-item ownership and receive rebinds stale assignment metadata.
    assert 'JOIN line_items bay_li ON bay_li.id = ba.line_item_id' in store
    assert 'WHERE bay_li.list_id = ? AND ba.status NOT IN' in store
    assert 'SET delivery_list_id = ?, bay_id = ?, assigned_qty = ?, status = ?' in store
    assert 'last["item"]["bayStatus"] = "Received"' in store

    # Non-available bays stay visible but cannot be selected for manual placement.
    assert 'const selectable = status.kind === "available" || status.kind === "manual";' in app
    assert '${selectable ? "" : "disabled"}' in app
    assert 'function refreshScanBayOverrideAfterReceiveV443' in app
    assert 'resetScanBayOverrideToAutoV443();' in app
    assert 'await refreshScanBayOverrideAfterReceiveV443()' in app
    assert '.custom-select-option.bay-target-option-v442:disabled' in styles


def test_v0445_indian_trail_workflow_restoration_is_preset_safe() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.445 - Indian Trail Workflow Restoration and Preset-Safe Stage Routing' in changelog

    # Frontend routing consumes stable server/list presets. Renaming the visible
    # receiving stage must not make processScanInternal fall through to /api/scans.
    assert 'function stagePresetFromValuesV445' in app
    assert 'function scanContextPresetV445' in app
    assert 'state.meta?.stagePreset || ""' in app
    process_start = app.index('async function processScanInternal')
    process_scan = app[process_start:process_start + 9500]
    assert 'isIndianTrailScanContext()' in process_scan
    assert 'fetchJson("/api/indian-trail/receive"' in process_scan
    assert '/indian trail/i.test(`${state.meta' not in process_scan

    # Backend list identity and all maintained cross-stage SQL use stable behavior
    # presets/current aliases rather than one literal operator-facing label.
    assert 'def stage_logic_preset(' in store
    assert 'def stage_name_aliases_for_preset(' in store
    assert 'def stage_where_clause(' in store
    assert '"stagePreset": stage_preset' in store
    assert 'stage_where_clause("out_dl.stage", "airport_outbound")' in store
    assert 'stage_where_clause("dl.stage", "indian_trail")' in store
    assert "LIKE '%Indian Trail%'" not in store
    assert "LIKE '%Outbound%'" not in store
    assert "LIKE '%Staging%'" not in store

    # Manual bays are valid operator targets, while occupied/preassigned bays
    # remain visible but disabled. Successful receipt keeps the one-scan Auto reset.
    assert 'status.kind === "available" || status.kind === "manual"' in app
    assert 'resetScanBayOverrideToAutoV443();' in app
    assert 'await refreshScanBayOverrideAfterReceiveV443()' in app


def test_v0446_six_stage_audit_location_hierarchy_and_same_order_bay_recommendation() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.446 - Six-Stage Audit, Bay Location Hierarchy, and Same-Order Bay Suggestions' in changelog

    # Core browser stage behavior uses stable presets across all six workflows.
    stage_category = app[app.index('function stageCategory(list)'):app.index('const DELIVERY_ROUTE_GROUP_DEFINITIONS')]
    for preset in ('airport_staging', 'airport_outbound', 'indian_trail', 'greenville', 'cpu', 'dtc'):
        assert preset in stage_category
    assert 'record.stagePreset || ""' in app
    assert 'stage.stagePreset || ""' in app

    # Historical rack metadata sits outside/above the rack surface, while PRE is
    # a narrow right-side rail and received Bay colors come from Bay family data.
    assert 'location-history-stack-v446' in app
    assert '<b class="location-history-prior-v442">PRIOR</b>${wrapRackLocation(baseBadge)}' in app
    assert 'location-preassigned-bay-v446' in app
    assert 'PRE ${escapeHtml(bayReference)}' in app
    assert 'function bayLocationPaletteV446' in app
    assert 'presentation.kind === "bay"' in app
    assert 'bay-location-accent-v446' in app
    assert 'b.bay_type' in store
    assert 'b.bay_category' in store
    assert 'b.map_section AS bay_map_section' in store
    assert 'item["bayType"] = str(bay["bay_type"] or "")' in store
    assert 'item["bayCategory"] = str(bay["bay_category"] or "")' in store
    assert '.location-history-stack-v446 > .location-history-prior-v442' in scan_css
    assert 'writing-mode: horizontal-tb !important;' in scan_css
    assert '.location-preassigned-bay-v442.location-preassigned-bay-v446' in scan_css
    assert 'writing-mode: vertical-rl;' in scan_css
    assert '.location-badge.bay.bay-location-accent-v446' in scan_css

    # Manual Bay is a one-scan override and returns the selector itself to Auto.
    reset = app[app.index('function resetScanBayOverrideToAutoV443'):app.index('function renderScanBayOverrideTools')]
    assert 'state.selectedBayOverrideCode = "";' in reset
    assert 'els.scanBayOverrideSelect.value = "";' in reset
    assert 'resetScanBayOverrideToAutoV443();' in app
    assert 'await refreshScanBayOverrideAfterReceiveV443()' in app

    # An order already occupying a Bay is explicitly preferred in the override picker.
    assert '"existingOrderBayCode": str(existing_group_assignment["bay_code"] or "")' in store
    assert 'const existingOrderBayCode = String(payload.existingOrderBayCode || "").trim();' in app
    assert 'Same-order bay recommended' in app
    assert 'const preferredBayCode = existingOrderBayCode || payload.preassignedBayCode' in app

    # Inbound arrow starts upper-left and terminates with its arrowhead bottom-right.
    icons = app[app.index('function globalSearchIconV433'):app.index('function globalSearchPriorityFlagsV425')]
    assert 'M6.5 6.5 17.5 17.5M17.5 11v6.5H11' in icons


def test_v0447_delivery_timing_override_stack_and_bidirectional_transit() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.447 - Delivery Timing Status and Bidirectional Transit Flow' in changelog

    # Delivery-list and Smart Search scan timing share the same effective-date
    # classification. Late timing gets its own red treatment; on-time remains neutral.
    assert 'function scanTimingMetaV447' in app
    assert 'late ? "LATE:" : "ON TIME:"' in app
    assert 'function scanTimePillMarkupV447' in app
    assert 'global-result-progress-v513' in app
    assert 'formatOperationalTimestampV511(stage.timestamp)' in app
    assert '.last-scan-pill-v157.is-late-v447' in scan_css

    # Receive override state is persisted from audit data and stacks vertically
    # inside the narrow Inbound Stage cell instead of clipping horizontally.
    assert 'item["inboundOverrideLabel"] = ""' in store
    assert 'audit_payload.get("outboundOverride")' in store
    assert '"OUTBOUND OVERRIDE" if outbound_override_used' in store
    assert 'function processPillMarkupV447' in app
    assert 'is-stacked-v447' in app
    assert '.process-pill.is-stacked-v447' in scan_css

    # The route meter owns the full center-lane width and the truck pauses/turns
    # at both endpoints in one infinite Outbound <-> Inbound shuttle animation.
    assert 'width: calc(100% + 36px) !important;' in bays_css
    assert 'animation: bay-transit-shuttle-v447 14s linear infinite !important;' in bays_css
    assert '@keyframes bay-transit-shuttle-v447' in bays_css
    assert 'transform: translateY(-55%) scaleX(-1);' in bays_css
    assert '47%' in bays_css and '96%' in bays_css


def test_v0448_rack_state_labels_bay_refresh_and_authoritative_timing() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.448 - Rack Lifecycle Location States, Persistent Bay Refresh, and Timing Accuracy' in changelog

    # Rack lifecycle state lives above the rack surface. PRIOR is only selected
    # when the location presentation is historical after downstream receipt.
    assert 'function rackLocationStateV448' in app
    assert 'presentation.historical) return { key: "prior", label: "PRIOR" }' in app
    assert 'label: "ON THE WAY"' in app
    assert 'label: "COMPLETE"' in app
    assert 'label: "INCOMPLETE"' in app
    assert 'location-rack-state-stack-v448' in app
    assert '.location-rack-state-stack-v448.is-on-the-way' in scan_css
    assert '.location-rack-state-stack-v448.is-complete' in scan_css
    assert '.location-rack-state-stack-v448.is-incomplete' in scan_css

    # An Inbound rack is not marked PRIOR until a physical receive exists.
    assert 'const inboundReceived = Number(currentItem.scanned || 0) > 0' in app
    assert 'historical: inboundReceived' in app

    # Fresh list reads resolve active/Received Bay ownership across sibling stage
    # copies, preferring Received over PreAssigned so refresh cannot revert to rack.
    assert 'WITH bay_candidates AS (' in store
    assert 'PARTITION BY target.id' in store
    assert "WHEN ba.status = 'Received' THEN 0" in store
    assert 'bay_by_item = {row["target_id"]: row for row in bay_rows}' in store

    # Timeliness is piece-level, undo/rescan safe, and respects moved delivery dates.
    assert 'li.priority_delivery_date' in store
    assert 'ORDER BY li.id, se.created_at DESC, se.id DESC' in store
    assert 'event_qty = min(max(int(event["qty"] or 0), 0), remaining)' in store
    assert '"timedQty": timed_qty' in store
    assert 'function timingMetricListsV448' in app
    assert 'const timingLists = timingMetricListsV448(lists);' in app
    assert 'entries: timingMetricListsV448(overviewLists)' in app


def test_v0449_indian_trail_override_reconciliation_inline_bay_and_sticky_stage() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.449 - Indian Trail Override Reconciliation and Inline Bay Correction' in changelog

    # IT override now reconciles both missing prerequisite stage copies and
    # records exactly what was auto-advanced instead of leaving stage progress at zero.
    assert 'def reconcile_indian_trail_override_stages(' in store
    assert '"airport_staging", "stagingQtyAdded", "Staging"' in store
    assert '"airport_outbound", "outboundQtyAdded", "Outbound"' in store
    assert 'Indian Trail override reconciled missing {label} prerequisite.' in store
    assert 'prerequisite_reconciliation = self.reconcile_indian_trail_override_stages(' in store
    assert '"prerequisiteReconciliation": prerequisite_reconciliation' in store

    # Physical receipt clears all matching active rack copies and preserves a
    # useful historical reason for the former transport rack.
    assert 'def clear_transport_racks_for_indian_trail_receive(' in store
    assert 'reason = "Overridden by IT" if overridden else "Received at Indian Trail"' in store
    assert 'item["lastRackRemovalReason"] = str(rack_history["rack_item_reason"] or "")' in store
    assert 'removalReason.includes("overridden by it")' in app
    assert 'label: "OVERRIDDEN BY IT"' in app
    assert '.location-rack-state-stack-v448.is-overridden-by-it' in scan_css

    # Received Bay state exposes its assignment identity and can be edited
    # inline without changing the physical state back to generic Moved.
    assert 'ba.id AS bay_assignment_id' in store
    assert 'item["bayAssignmentId"] = int(bay["bay_assignment_id"] or 0)' in store
    assert 'previous_status in {"Received", "Moved"}' in store
    assert 'function canAssignBayLocationV449()' in app
    assert 'function bayLocationEditorV449(item, displayLocation)' in app
    assert 'data-line-bay-select-v449' in app
    assert 'async function assignLineItemToBayV449(' in app
    assert 'reason: "Changed from Inbound Scan page"' in app
    assert '.line-bay-location-control-v449' in scan_css

    # Old mismatch text and sticky Stage selector both stay usable/readable.
    assert 'process-pill-lines-v449' in app
    assert 'is-stage-sequence-v449' in app
    assert '.process-pill-lines-v449 > .is-indented-v449' in scan_css
    assert '.scan-page #scanProgressBand {' in scan_css
    assert 'z-index: 60000 !important;' in scan_css




def test_v0465_exact_print_preview_glass_selection_and_filter_grouping() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.465 - Exact Print Preview Parity and Filter Selection Polish' in changelog

    # Preview owns the same Letter paper and .4in printable geometry as the real
    # print job, but its visible page edge no longer shrinks the content box.
    assert 'v0.465 Exact preview geometry + Lookup-color glass selection' in print_css
    assert 'outline: 1px solid #aab5c2 !important;' in print_css
    assert 'border: 0 !important;' in print_css
    assert 'height: 10.2in !important;' in print_css
    assert 'height: 7.7in !important;' in print_css
    assert '.check-cell {' in print_css

    # Exact glass filters fill with the Lookup Manager color rather than a blue
    # check badge, with deterministic readable ink for light/dark saved colors.
    assert '--glass-type-selected-ink:' in app
    assert 'const selectedInk = whiteContrastV466 >= darkContrastV466 ? "#FFFFFF" : "#10243A";' in app
    assert 'v0.465 Scan glass-filter selection uses the saved glass color' in scan_css
    assert 'background: linear-gradient(135deg,' in scan_css
    assert 'var(--glass-type-color) 100%) !important;' in scan_css
    assert 'content: none !important;' in scan_css[scan_css.index('v0.465 Scan glass-filter selection uses the saved glass color'):]
    assert 'v0.465 Print / Export glass selection' in styles_css
    assert 'var(--glass-type-selected-ink, #fff)' in styles_css

    # New/Updated and Errors are Status filters everywhere; Attention stays
    # dedicated to Rush, Remake, and Internal Rejects.
    assert 'status: Object.freeze(["remaining", "partial", "complete", "updated", "errors"])' in app
    assert 'attention: Object.freeze(["remakes", "rushes", "internal-rejects", "priority"])' in app
    status_section = index[index.index('aria-label="Status filters"'):index.index('aria-label="Attention filters"')]
    attention_section = index[index.index('aria-label="Attention filters"'):index.index('aria-label="Route filters"')]
    assert 'data-filter="updated"' in status_section
    assert 'data-filter="errors"' in status_section
    assert 'data-filter="updated"' not in attention_section
    assert 'data-filter="errors"' not in attention_section
    assert '["updated", "New/Updated"]' in app
    assert '["error", "Errors"]' in app
    assert 'function printPresetStatusValuesV465' in app
    assert 'function printPresetAttentionValuesV465' in app
    assert 'item_status_keys_v465' in store
    assert 'not (item_status_keys_v465(item) & exact_statuses)' in store

    # Route and Glass Type now span the same full-width Scan filter row.
    assert 'scan-filter-route-section-v465' in index
    assert '.scan-page .scan-filter-route-section-v465,' in scan_css
    route_owner = scan_css.index('.scan-page .scan-filter-route-section-v465,')
    assert 'grid-column: 1 / -1 !important;' in scan_css[route_owner:route_owner + 180]


def test_v0467_page_size_filter_counts_and_sequenced_truck_loading() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.467 - Paging Density, Filter Count Readability, and Sequenced Truck Loading' in changelog

    # Delivery-list paging defaults to 50 and exposes a 200-row maximum in both
    # synchronized selectors without changing Home's separate list paging.
    assert 'pageSize: 50,' in app
    assert 'state.pageSize = Number(els.pageSize.value) || 50;' in app
    assert 'state.pageSize = Number(els.pageSizeBottom.value) || 50;' in app
    top_page_size = index[index.index('id="pageSize"'):index.index('</select>', index.index('id="pageSize"'))]
    bottom_page_size = index[index.index('id="pageSizeBottom"'):index.index('</select>', index.index('id="pageSizeBottom"'))]
    assert '<option selected>50</option>' in top_page_size
    assert '<option>200</option>' in top_page_size
    assert '<option selected>50</option>' in bottom_page_size
    assert '<option>200</option>' in bottom_page_size

    # Filter numerals are slightly larger while preserving compact controls.
    assert 'v0.467 Larger filter-count numerals' in scan_css
    assert 'font-size: 11.5px !important;' in scan_css[scan_css.index('v0.467 Larger filter-count numerals'):]
    assert 'v0.467 Larger Print / Export filter-count numerals' in print_css
    assert 'font-size: 12.5px !important;' in print_css[print_css.index('v0.467 Larger Print / Export filter-count numerals'):]

    # Positive-load transit is now exact-time, pane-by-pane motion. The last pane
    # finishes before the fixed two-second departure dwell begins, and glass is
    # painted behind the truck instead of fading over the cab/roof.
    assert 'const postLoadDwellSeconds = 2.8;' in app
    assert 'function startBayTransitAnimationV467' in app
    assert 'const outboundDepartMs = loadMs + postLoadDwellMs;' in app
    assert 'const sequenceIndex = Math.max(outboundPanes.length - 1 - index, 0);' in app
    assert 'const startMs = sequenceIndex * paneStaggerMs;' in app
    assert 'const sequenceIndex = Math.max(inboundPanes.length - 1 - index, 0);' in app
    assert 'const startMs = inboundReadyMs + (sequenceIndex * paneStaggerMs);' in app
    assert 'has-transit-glass-v459 has-transit-glass-v467' in app
    assert 'v0.467 Individual pane loading + exact truck departure timing' in bays_css
    assert 'z-index: 3 !important;' in bays_css
    assert 'z-index: 6 !important;' in bays_css
    assert 'animation: none !important;' in bays_css[bays_css.index('v0.467 Individual pane loading + exact truck departure timing'):]


def test_v0468_whole_list_edit_preview_cleanup_and_shared_icon_actions() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static/css/print.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend/store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.468 - Whole Delivery List Editing and Shared Action Consistency' in changelog

    # Manual Edit now owns one logical delivery date and advances explicit
    # progress rather than exposing implementation-stage copies.
    assert 'MANUAL_EDIT_WHOLE_LIST_VALUE_V468 = "__whole_delivery_list__"' in app
    assert 'manualEditScopeV468: "whole"' in app
    assert 'id="manualEditModalStage" type="hidden"' in app
    assert 'data-manual-progress-item-v527' in app
    assert 'data-manual-progress-order-v527' in app
    assert 'data-manual-progress-list-v527' in app
    assert '/api/admin/delivery-progress' in app
    assert 'params.set("wholeList", "1")' in app
    assert 'params.set("deliveryDate", manualEditDeliveryDateForList(listId))' in app
    assert 'data-manual-edit-scope="${wholeListMode ? "whole" : "stage"}"' in app
    assert 'Use Progress to advance the item, order, or complete list' in app
    assert '"wholeList": query_values.get("wholeList"' in server
    assert 'whole_delivery_date = str(filters.get("deliveryDate")' in store
    assert 'logical_matches.setdefault(logical_identity(match), match)' in store
    assert 'data.pop("scanned", None)' in store
    assert 'data.pop("location", None)' in store
    assert '"editScope": "whole" if edit_scope == "whole" else "stage"' in store

    # Selected All Glass is explicitly white at the final Print stylesheet layer.
    assert 'v0.468 All Glass Types selected-label ownership' in print_css
    assert '.is-glass-all:has(input:checked) > span' in print_css
    assert '-webkit-text-fill-color: #fff !important;' in print_css

    # The compact Delivery List Changes header no longer paints the empty circle.
    assert 'v0.468 Delivery-list change preview + Whole Delivery List edit scope' in admin_css
    assert '.delivery-update-preview-v313 .delivery-update-preview-header-v313::after' in admin_css
    assert 'content: none !important;' in admin_css

    # Save/Delete icon buttons have one late-loaded shared profile, including the
    # Manual Edit hover state that previously flashed white.
    assert 'v0.470 Shared edit / save / delete icon action profile' in shared_css
    assert 'button.icon-only.icon-pencil' in shared_css
    assert 'button.icon-only.icon-save' in shared_css
    assert 'button.icon-only.icon-trash' in shared_css
    assert 'background: #155caa !important;' in shared_css
    assert 'background: #a92434 !important;' in shared_css


def test_v0474_fast_production_intelligence_and_order_details_contract() -> None:
    production = (ROOT / "backend/production_files.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    admin_css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static/css/bays.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    contract = (ROOT / "database/contract.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.474 - Fast Production Intelligence and Order Details' in changelog

    # Background indexing stays metadata-only; item/machine parsing is lazy and
    # exact-page aware for order-level sketch PDFs.
    assert 'def _sketch_page_assignments(' in production
    assert 'number.zfill(2)' in production
    assert '"pageNumber": page_index + 1' in production
    assert 'Not Fabricated - {self._machine_name(assigned_code)}' in production
    assert 'asset.extension == ".egl"' in production
    assert 'asset.extension == ".nce"' in production

    # Search/Order Details paint database data first, then hydrate production
    # state without placing PDF/network work in the synchronous search path.
    assert '/api/production-files/status-batch' in server
    assert 'page_number = max(0, int(params.get("page", ["0"])[0] or 0))' in server
    assert 'hydrateFabricationStatusesV474' in app
    assert '>Scan Page</button>' in app
    assert '>Order Details</button>' in app
    assert 'app-primary-button global-result-action-v475' in app
    assert 'data-open-order-detail-v474' in app
    assert 'production=0' in app
    assert '/api/orders/production-detail' in app
    assert 'data-production-page-v474' in app
    assert 'scanRowClickV474' in app
    assert 'Not Fabricated - ${compactMachineLabelV475' in app
    assert 'scanProgressPairV475' in app
    assert '.process-pill.not-fabricated-v474' in scan_css

    # Focused Lookup editing owns its modal layer, and Bay Map cards/animation
    # retain the restored visual identities and mirrored inbound endpoint.
    assert 'is-lookup-editor-open-v474' in app
    assert '#adminModal.is-lookup-editor-open-v474' in admin_css
    assert '--gui-close-position: absolute;' in admin_css
    assert 'grid-template-columns: minmax(0, 1fr) !important;' in admin_css
    assert 'inboundLeft' in app
    assert 'v0.474 Bay tool accents + mirrored Indian Trail unload stack' in bays_css
    assert 'global-result-action-v475' in styles_css


def test_v0477_scan_progress_order_grouping_and_fast_sketch_contract() -> None:
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    production = (ROOT / "backend/production_files.py").read_text(encoding="utf-8")
    scan_css = (ROOT / "static/css/scan.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static/css/shared-ui.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static/css/styles.css").read_text(encoding="utf-8")

    assert 'label: "Not Scanned"' in app
    assert 'workflowProgressStageRankV477' in app
    assert 'kind: "fabrication"' in app
    assert 'is-complete-v477' in app
    assert 'groupScanItemsByOrderV477' in app
    assert 'View order details' in app
    assert 'data-item-v477' in app
    assert 'data-order-detail-item-v477' in app
    assert 'focusOrderDetailItemV477' in app
    assert 'const chunkSize = context === "prewarm" ? 40 : 10' in app
    assert 'sketchPages' in production
    assert 'def _schedule_persist_index' in production
    assert '.scan-order-group-v477' in scan_css
    assert '.is-prior-pending-v475' in scan_css
    assert '.production-order-item-v476.is-focused-v477' in shared_css
    assert 'minmax(300px, 340px)' in shared_css
    assert 'global-result-action-v475' in styles_css


def test_v485_aw_internal_reject_mapping_external_remake_and_egl_history_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert 'CURRENT_SCHEMA_VERSION = 20' in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert 'data-automation-tab="rejects"' in app
    assert 'A+W Rejects' in app and 'automationRejectSyncEnabled' in app
    assert 'automationRejectIncrementalPastDays' in app and 'automationRejectFullPastDays' in app
    assert 'Manage Reject Data' in html
    assert 'data-reject-aw-mapping-save' in app and 'data-reject-history-relabel' in app
    assert '/api/rejects/mappings/update' in server and '/api/rejects/bulk-relabel' in server
    assert 'reject_value_mappings' in store and 'reject_value_mappings' in migrations
    assert 'manual_override_json' in operations and 'source_type == "aw"' in operations
    assert 'External Remake' in importer and 'External Remake' in app
    assert 'eglHistory' in production and 'historicalEglCount' in production
    assert '_historical_egl_match' in production and 'lastSeenAt' in production
    assert '.reject-history-table-v485' in admin and '.automation-aw-reject-settings-v485' in admin
    assert 'SPANISH_UI_V485' in app and 'Rehecho externo' in app


def test_v487_aw_reject_reporting_performance_live_logs_and_label_probe_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    azure = (ROOT / "database" / "azure_schema.sql").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    rejects_css = (ROOT / "static" / "css" / "rejects.css").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'v487_reject_reporting_performance' in migrations
    assert 'idx_reject_events_rejected_at_v487' in migrations and 'idx_reject_events_rejected_at_v487' in azure
    assert 'idx_aw_reject_source_rows_row_event_v487' in migrations
    assert 'skippedUnchanged' in store and 'unchangedSourceRows' in store
    assert 'resolved_machine' in store
    assert 'aw_machine' in operations and 'aw_work_type' in operations
    assert 'status["commandLine"]' in controller and 'f"COMMAND | {command_line}"' in controller
    assert 'last_run = live_status if running and live_status' in controller
    assert 'COMMAND | Python |' in runner
    assert 'durationMs' in importer
    for name in (
        '08-order-label-controls.csv',
        '09-optimization-record.csv',
        '10-optimization-sequence-plates.csv',
        '11-aw-order-label-view.csv',
        '12-print-jobs-near-optimization.csv',
        '13-pool-label-payload-candidates.csv',
        '14-print-pipeline-module-references.csv',
    ):
        assert name in probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert 'reject-timeline-source-evidence-v487' in app
    assert '.reject-timeline-source-evidence-v487' in rejects_css


def test_v488_reject_only_manual_sync_aw_mapping_fix_and_import_history_performance() -> None:
    import importlib.util

    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    admin = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    controller_text = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '"reject-sync-only": "RejectSyncOnly"' in controller_text
    assert 'Check A+W Rejects' in app and 'reject-sync-only' in app
    assert 'RejectSyncOnly' in runner and '-RejectOnly $true' in runner
    assert 'No delivery rows require reconciliation; synchronizing the A+W reject payload independently.' in runner
    assert '"--reject-only"' in importer and 'Reject-only mode requested; delivery-list reconciliation is intentionally skipped.' in importer

    settings_start = app.index('function rejectSettingsModalHtml()')
    settings_end = app.index('async function loadRejectSettingsModal()', settings_start)
    settings = app[settings_start:settings_end]
    assert 'const awMappings = state.rejectCatalog.awMappings || [];' in settings
    assert 'awMappings.map' in settings
    assert 'historyReasons: Array.isArray(catalog.historyReasons)' in app
    assert 'awMappings: Array.isArray(catalog.awMappings)' in app
    assert app.count('awMappings: Array.isArray(catalog.awMappings) ? catalog.awMappings : []') >= 2
    assert app.count('awMappings: Array.isArray(payload.awMappings) ? payload.awMappings : []') >= 1

    assert 'if clean_page_mode != "control_center":' in controller_text
    assert 'database_limit = 5000 if filters_requested or clean_page_mode != "control_center" else 1500' in controller_text
    assert 'archive_limit = 2000 if filters_requested or clean_page_mode != "control_center" else 250' in controller_text
    assert '_import_history_archive_cache' in controller_text
    assert 'importHistoryRenderLimit = 80' in app
    assert 'data-import-history-show-more' in app
    assert '.import-history-progressive-more-v488' in admin
    assert 'publishDeliveryCatalog(payload.lists, "import-history", true)' not in app
    assert 'publishDeliveryCatalog(payload.lists, "latest-import-catalog", force)' not in app

    for name in (
        '15-pool-job-file-records.csv',
        '16-pool-output-family-context.csv',
        '17-pool-output-module-references.csv',
        '18-order-item-label-objects.csv',
    ):
        assert name in probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert 'STRING_AGG' not in probe

    # Functional proof: Control Center Import History must not fetch the full
    # delivery-list catalog just to render audit rows.
    module_path = ROOT / "backend" / "automation_control.py"
    specification = importlib.util.spec_from_file_location("v488_automation_control", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    controller = module.DeliveryAutomationController.__new__(module.DeliveryAutomationController)

    class StoreThatMustNotLoadCatalog:
        def get_delivery_lists(self, *args, **kwargs):
            raise AssertionError("Import History requested the full delivery-list catalog")

    controller.scanner_store = StoreThatMustNotLoadCatalog()
    controller._database_import_history_items = lambda: []
    controller._latest_automation_import_items = lambda: ([], {})
    controller._archived_automation_import_items = lambda *args, **kwargs: []
    payload = controller.get_import_history(page=1, page_mode="control_center")
    assert payload["lists"] == []

    controller._latest_automation_import_items = lambda: ([], {})
    latest_payload = controller.get_latest_import_result()
    assert "lists" not in latest_payload


def test_v489_reject_paging_and_aw_actor_accuracy_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    rejects_css = (ROOT / "static" / "css" / "rejects.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'current_week_start - timedelta(days=7)' in operations
    assert '"totalCount": total_count' in operations and '"totalPages": total_pages' in operations
    assert 'rejected_by=params.get("rejectedBy"' in server
    assert 'params.set("page"' in app and 'rejectHistoryPageSize: 50' in app
    assert 'This week + last week' in html and 'rejectPagination' in html
    assert '.reject-pagination-v489' in rejects_css
    assert 'timeline_employee' in store and 'actorCorrections' in store
    assert 'WHEN ISNULL(book.MITARB_ID, \'\') <> \'\' THEN book.MITARB_ID' in runner
    explicit_order = runner.index('CASE WHEN b.ORIGIN = 0 THEN 0 ELSE 1 END')
    bom_order = runner.index('CASE WHEN b.BOMID = pb.BOM_ID THEN 0 ELSE 1 END')
    assert explicit_order < bom_order
    assert 'Current maintained release: **v0.527**' in readme


def test_v490_cutting_labels_output_capture_probe_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert '20260908-v0.510' in app
    assert 'Current maintained release: **v0.527**' in readme

    assert '[string]$OptimizationNumber = ""' in probe
    assert '[switch]$CaptureCuttingLabels' in probe
    assert 'Production Manager -> Optimization Overview -> select optimization -> Output' in probe
    assert "'Cutting Labels'" in probe
    assert "'Residue Plate Labels'" in probe
    assert "'Series from quantity'" in probe
    assert 'KA_FORMULARE' in probe and 'KA_PRINT_DETAIL' in probe and 'BW_PRINT_JOBS' in probe
    assert 'REPORT_GRUPPE' in probe and 'PRINT_DEF' in probe and 'DRUCK_STRING' in probe
    for name in (
        '19-selected-optimization-output-context.csv',
        '20-output-report-definition-columns.csv',
        '21-cutting-label-ui-text-hits.csv',
        '22-ka-formulare-report-catalog.csv',
        '23-ka-print-detail-report-catalog.csv',
        '24-output-report-module-references.csv',
        '25-cutting-label-capture-baseline.csv',
        '26-cutting-label-new-print-jobs.csv',
        '27-cutting-label-new-pool-rows.csv',
        '28-cutting-label-new-pool-log.csv',
    ):
        assert name in probe
    assert 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED' in probe
    assert 'INSERT INTO SYSADM' not in probe
    assert 'UPDATE SYSADM' not in probe
    assert 'DELETE FROM SYSADM' not in probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe


def test_v492_screen_only_label_capture_and_aw_actor_window_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    label_probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    reject_probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWBdeBreakage.ps1").read_text(encoding="utf-8-sig")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme

    # A+W can commit PROD_BREAKAGE and the explicit reject booking a few seconds
    # apart. Actor selection stays tightly bounded and uses source codes + origin
    # before timestamp proximity; LASTCHANGEUSER remains fallback only.
    assert 'DATEADD(second, -60, pb.BREAKAGEDATE)' in runner
    assert 'DATEADD(second, 60, pb.BREAKAGEDATE)' in runner
    reason_rank = runner.index('CASE WHEN ISNULL(b.BREAKAGE_REASON, -1) = ISNULL(pb.BREAKAGE_REASON, -2) THEN 0 ELSE 1 END')
    location_rank = runner.index('CASE WHEN ISNULL(b.BREAKAGE_CAUSER, -1) = ISNULL(pb.BREAKAGE_REGISTRATION, -2) THEN 0 ELSE 1 END')
    explicit_rank = runner.index('CASE WHEN b.ORIGIN = 0 THEN 0 ELSE 1 END')
    time_rank = runner.index('ABS(DATEDIFF(second, b.SCANTIME, pb.BREAKAGEDATE))', explicit_rank)
    assert reason_rank < location_rank < explicit_rank < time_rank
    assert 'actorSecondsFromBreakage = [int]$row.ActorSecondsFromBreakage' in runner
    assert '19-reject-actor-candidates.csv' in reject_probe

    # Cutting Labels discovery must use the safe Screen preview, never require
    # Execute. SQL deltas and local temp-file metadata are both captured because
    # report preview may be rendered entirely client-side.
    assert '[switch]$CaptureCuttingLabelsScreen' in label_probe
    assert 'Click SCREEN in A+W now with only Cutting Labels selected.' in label_probe
    assert 'Do not click Execute.' in label_probe
    assert '29-cutting-label-screen-temp-files.csv' in label_probe
    assert '30-aw-business-pro-processes.csv' in label_probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in label_probe



def test_v493_crystal_reports_cutting_label_source_probe_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert '20260908-v0.510' in app
    assert 'Current maintained release: **v0.527**' in readme

    # The live preview is Crystal Reports inside Citrix, so discovery now targets
    # report/template definitions and the exact optimization/order source data
    # rather than assuming a local preview file is authoritative.
    assert 'Crystal Reports' in readme
    assert "'Crystal', '.rpt', 'RPT'" in probe
    assert "'Etik', 'Etikett', 'Label', 'Schneid', 'Zuschnitt'" in probe
    assert 'ReferencesCrystal' in probe and 'ReferencesRpt' in probe
    assert 'Select-Object -First 40' in probe
    assert 'return $hits.ToArray()' in probe

    for name in (
        '31-crystal-report-candidate-columns.csv',
        '32-crystal-report-text-hits.csv',
        '33-crystal-report-module-references.csv',
        '34-selected-optimization-label-data.csv',
        '35-selected-optimization-production-route.csv',
        '36-barcode-label-candidate-columns.csv',
    ):
        assert name in probe

    assert 'SYSADM.PROD_OPTI_SEQUENCE' in probe
    assert 'SYSADM.PROD_JOBITEM' in probe
    assert 'SYSADM.AWV_TD_ORDER_HEADER' in probe
    assert 'SYSADM.AWV_TD_ORDER_ITEM' in probe
    assert 'BatchJobNumber' in probe
    assert 'CustomerReference' in probe
    assert 'WeightPerPiece' in probe and 'SurfacePerPiece' in probe
    assert 'SYSADM.ZW_AUFTR_ZEIT' in probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED' in probe
    assert 'INSERT INTO SYSADM' not in probe
    assert 'UPDATE SYSADM' not in probe
    assert 'DELETE FROM SYSADM' not in probe


def test_v494_schema_aware_crystal_label_projection_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert '20260908-v0.510' in app
    assert 'Current maintained release: **v0.527**' in readme
    assert 'Get-LiveObjectColumnSet' in probe
    assert 'Get-OptionalColumnSelectSql' in probe
    assert "-ObjectName 'AWV_TD_ORDER_ITEM'" in probe
    assert "-ColumnName 'PI_SURFACEPERPIECE'" in probe
    assert "-FallbackSql 'bp.PP_QM'" in probe
    assert 'LEFT JOIN SYSADM.BW_AUFTR_POS bp' in probe
    assert 'bp.PP_GEWICHT AS RawOrderWeight' in probe
    assert 'bp.PP_QM AS RawOrderSurfaceArea' in probe
    assert 'i.PI_SURFACEPERPIECE AS SurfacePerPiece' not in probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED' in probe


def test_v495_exact_cutting_label_report_and_source_chain_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '20260908-v0.510' in index
    assert '20260908-v0.510' in app
    assert 'Current maintained release: **v0.527**' in readme
    assert "Prodman_CuttingLabel_Optimisation.rpt" in probe
    assert "SYSADM.DR_REPORTE" in probe
    assert "SYSADM.DR_DRUCKPUNKTE" in probe
    assert "SYSADM.DR_DRUCK" in probe
    assert "SYSADM.KA_PRINT_DETAIL" in probe
    for name in (
        '37-cutting-label-report-record.csv',
        '38-cutting-label-output-report-siblings.csv',
        '39-cutting-label-dr-druck-config.csv',
        '40-cutting-label-ka-print-config.csv',
        '41-cutting-label-report-path-settings.csv',
        '42-selected-optimization-source-rows.csv',
        '43-selected-order-barcode-evidence.csv',
        '44-selected-optimization-production-candidates.csv',
    ):
        assert name in probe
    assert 'OUTER APPLY (' in probe
    assert 'candidate.AUFNR=seq.AUFNR AND candidate.POSNR=seq.POSNR' in probe
    assert 'ON ji.OPTIMIZATION=seq.OPTIMIZATION' not in probe
    assert 'SYSADM.BW_AUFTR_POS_EX' in probe
    assert 'SYSADM.BW_AUFTR_STKL' in probe
    assert 'SYSADM.FS_BOOK_HISTORY' in probe
    assert 'SYSADM.BW_ALCIM_RECEIVE' in probe
    assert 'SYSADM.PROD_JOBPRODSEQ' in probe
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED' in probe
    assert 'INSERT INTO SYSADM' not in probe
    assert 'UPDATE SYSADM' not in probe
    assert 'DELETE FROM SYSADM' not in probe


def test_v496_optimization_lifecycle_and_cutting_probe_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert '20260908-v0.510' in index
    assert '20260908-v0.510' in app
    assert 'Current maintained release: **v0.527**' in readme
    assert 'DeliveryScanner-AWGlassLabelProbe-v498' in probe
    assert '45-selected-optimization-lifecycle.csv' in probe
    assert '46-recent-optimization-status-summary.csv' in probe
    assert '47-optimization-status-candidate-columns.csv' in probe
    assert '48-optimization-status-text-hits.csv' in probe
    assert '49-selected-optimization-sequence-raw.csv' in probe
    assert '50-selected-order-jobitems-raw.csv' in probe
    assert '51-selected-order-batch-status.csv' in probe
    assert '52-selected-order-production-bookings.csv' in probe
    assert '53-optimization-status-module-references.csv' in probe
    assert "FROM SYSADM.PROD_OPTIMIZATION o" in probe
    assert "FROM SYSADM.PROD_OPTI_STATISTICS s" in probe
    assert "FROM SYSADM.PROD_OPTI_SEQUENCE seq" in probe
    assert "LEFT JOIN SYSADM.PROD_JOB j ON j.JOBNUMBER=ji.JOBNUMBER" in probe
    assert "FROM SYSADM.FS_BOOK_HISTORY b" in probe
    assert "Optimized" in probe and "Released" in probe and "Booked" in probe
    assert "COUNT(*) AS [RowCount]" in probe
    assert ") AS q" in probe
    assert "GROUP BY q.SourceObject, q.StatusCode, q.OptimizationMode, q.AggregateId" in probe
    assert "COUNT(*) AS RowCount" not in probe
    assert "SELECT-only" in readme


def test_v498_aw_cutting_progress_and_label_context_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    azure = (ROOT / "database" / "azure_schema.sql").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'v498_aw_cutting_progress' in migrations
    assert 'aw_cutting_generations' in migrations and 'aw_cutting_generations' in azure
    assert 'def sync_aw_cutting_rows' in store
    assert 'def aw_cutting_state' in store
    assert 'Get-AwCuttingSyncPayload' in runner
    assert 'v499-aw-production-1' in runner
    assert 'cuttingSync = $script:AwCuttingSyncPayload' in runner
    assert 'PROD_JOBITEM' in runner and 'KEYINDEX' in runner and 'PROD_JOB' in runner
    assert 'SYSADM.PROD_OPTIMIZATION' in runner and 'SYSADM.PROD_OPTI_STATISTICS' in runner
    assert 'SYSADM.PROD_OPTI_SEQUENCE' in runner
    assert 'COALESCE(NULLIF(ji.OPTIMIZATION, 0), seq.OPTIMIZATION)' in runner
    assert 'b.BOOK_TYPE = 0' in runner and 'b.WORK_TYPE = 10' in runner and 'b.REG_POINT = 1000' in runner
    assert 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED' in runner
    assert 'INSERT INTO SYSADM' not in runner
    assert 'UPDATE SYSADM' not in runner
    assert 'DELETE FROM SYSADM' not in runner
    assert 'store.sync_aw_cutting_rows' in importer
    assert 'awCuttingSync' in importer
    assert 'cuttingProgressPresentationV498' in app
    assert 'orderDetailCuttingLabelV498' in app
    assert 'Reconstructed A+W Cutting Label preview' in app
    assert 'cutting-progress-spinner-v498' in css
    assert 'AW_OPTI_STATUS_OPTIMIZED = 100' in store
    assert 'AW_OPTI_STATUS_RELEASED = 200' in store
    assert 'AW_OPTI_STATUS_BOOKED = 500' in store
    assert 'optimization_status == AW_OPTI_STATUS_BOOKED' in store
    assert 'optimization_status == AW_OPTI_STATUS_RELEASED' in store
    assert 'batch_status == 500' not in store[store.index('def aw_cutting_state'):store.index('def get_order_detail')]
    assert '20260908-v0.510' in index and '20260908-v0.510' in app
    assert 'Current maintained release: **v0.527**' in readme



def test_v499_unified_aw_sync_production_settings_and_bounded_query_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    config = (ROOT / "automation" / "sql_delivery_export" / "sql-export.config.json").read_text(encoding="utf-8")
    control = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'v499-aw-production-1' in runner
    assert 'Get-AwRejectSyncPayload -Config $script:Config -RunMode $Mode -ForceEnabled (-not [string]::IsNullOrWhiteSpace([string]$RequestId))' in runner
    assert 'Get-AwCuttingSyncPayload -Config $script:Config -DirectPayloads $script:DirectImportPayloads -ForceEnabled $forceProductionRefresh -SkipPlan $cuttingSkipPlan' in runner
    assert 'DENSE_RANK() OVER (PARTITION BY ji.AUFNR,ji.POSNR' in runner
    assert 'GenerationRank <= @GenerationHistoryDepth' in runner
    assert 'CuttingBookingRanked AS (' in runner
    assert 'b.SCANTIME >= DATEADD(day,-@CutLookbackDays,GETDATE())' in runner
    assert 'OPTION (RECOMPILE)' in runner
    assert 'Reading A+W Batch/Optimization/Cutting state' in runner
    assert 'ProductionSync' in config and '"QueryBatchSize": 60' in config
    assert 'productionScheduledEnabled' in control
    assert 'productionCuttingBookingLookbackDays' in control
    assert 'data-automation-tab="production"' in app
    assert 'Batch, Optimization &amp; Cutting' in app
    assert 'Prodman_CuttingLabel_Optimisation.rpt' in app
    probe = (ROOT / 'scripts' / 'diagnostics' / 'Probe-AWGlassLabels.ps1').read_text(encoding='utf-8-sig')
    assert '[switch]$LocateCrystalReport' in probe
    assert '54-cutting-label-crystal-file-locations.csv' in probe
    assert 'Check A+W Rejects' not in app[app.index('<div class="automation-action-grid">'):app.index('<div class="automation-section-heading">', app.index('<div class="automation-action-grid">') + 1)]
    assert 'Complete A+W sync' in app
    assert 'automationScheduleRejectSync' in app
    assert 'automationScheduleProductionSync' in app
    assert 'automation-aw-production-settings-v499' in app
    assert 'automation-production-note-v499' in css
    assert 'Current maintained release: **v0.527**' in readme


def test_v500_reject_accuracy_startup_and_cutting_label_reconstruction_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'retry_pending_rollbacks: bool = False' in store
    assert 'pending_clause = " OR src.rollback_applied_at=\'\'" if retry_pending_rollbacks else ""' in store
    assert 'ensure_aw_internal_reject_mirrors(retry_pending_rollbacks=True)' in importer
    assert 'Source event {event_key}' in store
    assert '"reject_reset"' in store[store.index('def event_from_row'):store.index('def list_meta')]
    assert 'scanRejectResetPresentationV500' in app
    assert 'A+W reject' in app and 'pc reset' in app
    assert 'internalRejectItems.reduce' in app
    assert 'pieceCount(internalRejectItems)' not in app
    assert 'production-cutting-label-reconstruction-v500' in app
    assert 'function code39BarcodeSvgV500(value = "")' in app
    assert 'T200231506001000' in app
    assert 'production-cutting-label-code39-v500' in app
    assert 'canonicalBarcode(cleanOrder, cleanItem)' in app
    assert 'Process-after-cutting formula still under investigation' in app
    assert '.production-cutting-label-route-v500' in css
    assert '.production-cutting-label-barcode-v500' in css
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    assert '55-selected-order-crystal-header-anchors.csv' in probe
    assert '56-selected-order-crystal-item-anchors.csv' in probe
    assert '57-crystal-screenshot-field-candidates.csv' in probe
    assert 'h.AH_NAME1 AS CustomerName' in probe
    assert 'h.BEST_TEXT1 AS SgBestText1' in probe
    assert 'h.OR_TOUR AS RouteText' in probe
    assert '## v0.500 -' in changelog


def test_v501_piece_cutting_labels_and_fabrication_consistency_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '"state": "unknown"' in store[store.index('def aw_cutting_state'):store.index('def get_order_detail')]
    assert 'inferredFromFabrication' in store
    assert 'downstream_fabrication' in store
    assert 'labelContext' in store
    assert 'head.AH_NAME1' in runner
    assert 'head.BEST_TEXT1' in runner
    assert 'head.OR_TOUR' in runner
    assert 'pos.PROD_BEZ1' in runner
    assert 'version="v501-aw-production-2"' in runner
    assert 'function orderDetailCuttingLabelsV501' in app
    assert 'usableAwLabelTextV501' in app
    assert 'NO A+W DATA' in app
    assert 'cuttingLabelPieceHtmlV507' in app
    assert 'data-cutting-label-piece-select-v507' in app
    assert 'production-cutting-label-piece-counter-v501' in app
    assert 'orderDetailCuttingLabelsV501(item, payload)' in app
    probe = (ROOT / 'scripts' / 'diagnostics' / 'Probe-AWGlassLabels.ps1').read_text(encoding='utf-8-sig')
    assert '58-selected-order-cutting-bridge-v501.csv' in probe
    assert '59-selected-order-optimization-sequence-v501.csv' in probe
    assert '60-selected-order-process-after-cutting-v501.csv' in probe
    assert '.production-cutting-label-set-v501' in css
    assert '.production-cutting-piece-v501' in css
    assert '## v0.501 -' in changelog


def test_v502_manual_sync_observability_cut_evidence_and_compact_label_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # The Python importer must stream its flushed progress lines into the same
    # authoritative command log instead of buffering until process exit.
    assert '$commandOutput = New-Object System.Collections.Generic.List[string]' in runner
    assert '& $pythonPath @allArguments 2>&1 | ForEach-Object {' in runner
    assert 'Write-AutomationLog -Message ("Python: {0}" -f $outputLine)' in runner
    assert '$commandOutput = @(& $pythonPath @allArguments 2>&1)' not in runner

    # Manual runs verify every source date but no longer force-write every date.
    assert '$forceImportDates = @($script:PendingImportDates | Sort-Object -Unique)' in runner
    assert 'only changed/drifted dates will be rewritten' in runner
    assert '$forceImportDates = @($sourceDates)' not in runner

    # Optimization and Plate status use indexed per-generation lookups. Ranking
    # both complete A+W tables through CTEs caused the real SQL Server to time out.
    assert 'WHERE o.OPTIMIZATION=ji.ResolvedOptimization' in runner
    assert 'WHERE s.OPTIMIZATION=ji.ResolvedOptimization' in runner
    assert 'WHERE p.OPTIMIZATION=ji.ResolvedOptimization AND p.PLATENR=ji.ResolvedPlateNumber' in runner
    assert 'CandidateOptimizations AS (' not in runner
    assert 'PlateRanked AS (' not in runner
    assert 'OptimizationPlateCut' in runner and 'OptimizationPlateStockBooked' in runner
    assert 'version="v502-aw-production-3"' in runner
    assert 'optimization_plate_cut' in store
    assert 'prod_jobitem_cut_quantity' in store
    assert 'cutEvidence' in store

    # Blank Optimization input must be resolved from the newest Order/Item
    # generation so the probe continues past the old output-34 gate.
    assert 'Auto-resolved current Optimization' in probe
    assert 'COALESCE(NULLIF(ji.OPTIMIZATION,0), seq.OPTIMIZATION)' in probe
    assert '58-selected-order-cutting-bridge-v501.csv' in probe
    assert '59-selected-order-optimization-sequence-v501.csv' in probe
    assert '60-selected-order-process-after-cutting-v501.csv' in probe

    # Order Details renders a small physical-label thumbnail, not a 440px card,
    # and the operator can expand that exact same label into a native-size modal.
    assert 'cuttingLabelGenerationPlanV502' in app
    assert 'data-cutting-label-maximize-v502' in app
    assert 'openCuttingLabelPreviewV502' in app
    assert 'production-cutting-label-frame-v502' in app
    assert 'Process-after-cutting formula still under investigation' in app  # compatibility comment only
    assert '.production-cutting-label-set-v502' in css
    assert 'width:min(100%,268px)' in css
    assert 'width:246px' in css
    assert 'width:436px' in css and 'height:519px' in css
    assert '.cutting-label-preview-v502' in css
    assert '## v0.502 -' in changelog


def test_v503_automation_stale_run_recovery_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'def _recover_stale_browser_run' in controller
    assert 'No active automation process or shared runtime lock was found.' in controller
    assert 'runtime_lock_busy = bool(config and self._runtime_lock_busy(config))' in controller
    assert 'running = browser_process_running or runtime_lock_busy' in controller
    assert 'recoveredStaleRun' in controller
    assert 'gui_run = self._recover_stale_browser_run(config, gui_run)' in controller
    assert 'const running = Boolean(dashboard.running);' in app
    assert 'dashboard.running || last.running' not in app
    assert '20260908-v0.510' in index and '20260908-v0.510' in app
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.503 - Automation Stale-Run Recovery and Live Liveness Truth' in changelog


def test_v504_recent_cutting_coverage_status_460_and_aw_label_parity_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    config = (ROOT / "automation" / "sql_delivery_export" / "sql-export.config.json").read_text(encoding="utf-8")
    control = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Order Details enrichment must outlive the normal delivery-list incremental
    # window without widening the actual delivery import itself.
    assert 'OrderLookbackDays' in runner
    assert 'DATUM_LIEFER_PLAN >= DATEADD(day,-@OrderLookbackDays' in runner
    assert 'Expanded A+W production coverage' in runner
    assert 'version="v507-aw-production-5"' in runner
    assert 'recent delivery/production order(s)' in runner
    assert '"OrderLookbackDays": 14' in config
    assert 'productionOrderLookbackDays' in control
    assert 'automationProductionOrderLookback' in app

    # Preserve every sequence/plate member and the planned A+W route needed for
    # piece-level Crystal-label reconstruction.
    assert 'ResolvedSequenceRows AS (' in runner
    assert 'OptimizationSequenceRowId' in runner
    assert 'OptimizationSheetCount' in runner
    assert 'ShapeNumber' in runner
    assert 'FROM SYSADM.ZW_AUFTR_ZEIT z' in runner
    assert 'ProcessProductDescription' in runner
    assert 'processRows=' in runner
    assert 'sequenceAssignments' in store
    assert 'optimizationSheetCount' in store
    assert 'processRows' in store
    assert 'shapeNumber' in store

    # Live Order 238076 / Item 1 establishes raw status 460 as another A+W
    # Booked state while keeping the raw source code auditable.
    assert 'AW_OPTI_STATUS_BOOKED_CODES = frozenset({460, 500})' in store
    assert 'optimization_status in AW_OPTI_STATUS_BOOKED_CODES' in store
    assert 'statusCode === 460' in app and 'statusCode === 500' in app
    assert '460/500 Booked' in app

    # A+W label parity: only CPU/DTC route headings, right-aligned production
    # metadata, planned process route, vertical remake, and plate/sequence footer.
    assert 'function cuttingLabelRouteTextV504' in app
    assert 'CUSTOMER PICK UP' in app and 'DELIVERY TO CUSTOMER' in app
    assert 'function cuttingLabelProcessRowsV504' in app
    assert 'production-cutting-label-production-meta-v504' in app
    assert 'production-cutting-label-remake-v504' in app
    assert 'A+W optimization plate / sequence' in app
    assert '.production-cutting-label-v504' in css
    assert '.production-cutting-label-production-meta-v504' in css
    assert '.production-cutting-label-remake-v504' in css
    assert 'writing-mode:vertical-rl' in css
    assert '## v0.504 -' in changelog


def test_v505_production_count_email_and_crystal_marker_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    probe = (ROOT / "scripts" / "diagnostics" / "Probe-AWGlassLabels.ps1").read_text(encoding="utf-8-sig")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract

    # Production Count is first-seen/import activity rather than delivery-date
    # inventory. Yield Percentage remains auditable but is excluded from all
    # Internal Reject statistics derived by this report.
    assert 'def is_yield_percentage_reject_reason' in store
    assert "FROM line_update_notices n" in store
    assert "production_activity_by_kind" in store
    assert '"newProduction": new_production_activity' in store
    assert '"internalRejects": internal_reject_activity' in store
    assert '"externalRemakes": external_remake_activity' in store
    assert '"yieldPercentageExcluded": yield_percentage_excluded' in store
    assert "statistical_reject_rows" in store

    # Statistics exposes a compact three-way activity view and an explicit daily
    # email-draft workflow which always re-queries today's authoritative range.
    assert 'id="statisticsProductionActivity"' in index
    assert 'id="statisticsDailyProductionEmailBtn"' in index
    assert 'function renderStatisticsProductionActivityV506' in app
    assert 'function dailyProductionEmailDraftV506' in app
    assert 'function draftDailyProductionEmailV506' in app
    assert 'NEW ORDERS BY GLASS:' in app
    assert 'INTERNAL REJECTS:' in app
    assert 'EXTERNAL REMAKES:' in app
    assert 'Yield Percentage excluded:' in app
    assert 'fullParams.length > 7000' in app
    assert '.statistics-production-count-v505' in statistics_css
    assert '.statistics-email-preview-v505' in statistics_css

    # Supplied A+W labels now establish the two special process markers and the
    # SHAPE placement. Unknown Dim_LengthInfo edge-length formulas remain
    # evidence-driven and receive dedicated diagnostics rather than guessed UI.
    assert 'production-cutting-label-process-marker-v505' in app
    assert '/back\\s+mit(?:re|er)/i' in app
    assert '/diamon(?:d)?\\s+fusion/i' in app
    assert 'production-cutting-label-shape-v505' in app
    assert '.production-cutting-label-process-marker-v505' in shared_css
    assert '.production-cutting-label-shape-v505' in shared_css
    for output_no in range(61, 66):
        assert f'{output_no}-' in probe
    assert 'Dim_LengthInfo' in probe
    assert '## v0.505 -' in changelog


def test_v506_piece_by_glass_production_count_and_formatted_email_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '"byGlass": by_glass' in store
    assert 'row["glassType"] = glass_label' in store
    assert '"sqft": round(sqft, 2)' in store
    assert 'id="statisticsProductionActivity"' in index
    assert 'Actual new-piece counts by glass type' in index
    assert 'function renderStatisticsProductionActivityV506' in app
    assert 'statistics-production-glass-row-v506' in app
    assert 'function dailyProductionEmailDraftV506' in app
    assert 'Copy formatted email' in app
    assert '"text/html": new Blob' in app
    assert 'ClipboardItem' in app
    assert 'New Orders' in app and 'Internal Rejects' in app and 'External Remakes' in app
    assert '.statistics-production-glass-row-v506' in css
    assert '.statistics-email-preview-render-v506' in css
    assert '## v0.506 -' in changelog


def test_v507_runtime_performance_aw_cutting_coverage_and_order_detail_split_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    azure = (ROOT / "database" / "azure_schema.sql").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    admin_css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert '"v507_runtime_read_indexes"' in migrations
    assert 'idx_line_items_active_order_item_v507' in migrations and 'idx_aw_cutting_order_item_recent_v507' in migrations
    assert 'idx_delivery_lists_active_date_revision_v507' in azure

    assert 'def get_delivery_lists_compact' in store
    assert 'def get_delivery_list_summaries' in store
    assert 'compact = str(params.get("compact", ["0"])[0]).lower()' in server
    assert '/api/delivery-lists?compact=1' in app
    load_catalog_block = app[app.index('async function loadDeliveryLists('):app.index('function setActiveList(', app.index('async function loadDeliveryLists('))]
    assert 'fetchJson("/api/delivery-lists?compact=1")' in load_catalog_block
    assert 'fetchJson("/api/delivery-lists")' not in load_catalog_block
    assert 'detailRows=0' in app
    assert 'include_activity_rows' in store
    assert 'getter = getattr(store, "get_delivery_lists_compact", None)' in importer
    assert 'get_delivery_list_summaries' in importer

    assert 'def get_order_production_detail' in store
    assert 'parsed.path == "/api/orders/production-detail"' in server
    assert '/api/orders/detail?order=${encodeURIComponent(order)}&production=0' in app
    assert '/api/orders/production-detail?order=${encodeURIComponent(order)}' in app
    assert 'orderDetailCorePendingV507' in app and 'orderDetailProductionPendingV507' in app
    assert 'data-order-sketch-src-v507' in app and 'IntersectionObserver' in app
    assert 'data-cutting-label-piece-select-v507' in app
    assert '.production-cutting-piece-selector-v507' in shared

    assert 'COALESCE(j.LASTCHANGEDATE,j.CREATIONDATE)' in runner
    assert 'OptimizationStatusSource' in runner
    assert 'optimizationStatusSource' in store
    assert 'requestedOrderCount' in runner and 'missingOrderSample' in runner
    assert 'version="v507-aw-production-5"' in runner
    assert '$directPayloadSnapshot = @($DirectPayloads | ForEach-Object { $_ })' in runner
    assert 'foreach ($envelope in $directPayloadSnapshot)' in runner
    assert 'foreach ($envelope in @($DirectPayloads))' not in runner
    assert '$Object -is [System.Collections.IDictionary]' in runner
    assert 'return $Object[$Name]' in runner
    assert '$processAttachedGenerations' in runner
    assert 'ShapeDisplayRanked AS (' in runner and 'ISNULL(sh.TYPE,0)=0' in runner
    assert 'shapeParameterUnitsPerInch=32' in runner and 'shapeParameters=@(' in runner
    assert 'shapeParameterUnitsPerInch' in store and 'shapeParameters' in store
    assert 'cuttingLabelEdgeCalloutsV507' in app and 'Number(cutting.shapeNumber || 0) !== 13' in app
    assert '.production-cutting-label-edge-dims-v507' in shared
    assert 'coverage=' in importer

    assert 'con.execute("PRAGMA journal_mode = WAL")' in store
    connect_block = store[store.index('    def connect(self) -> sqlite3.Connection:'):store.index('    def health(self)', store.index('    def connect(self) -> sqlite3.Connection:'))]
    assert 'journal_mode = WAL' not in connect_block
    assert 'if (state.page === "bays") await refreshBayRouteSummary();' in app
    assert 'if (state.page === "scan") await activateList' not in app[app.index('function startPolling()'):app.index('function stopPolling()')]
    assert 'requestIdleCallback' in app

    # Settings workspaces must paint a modal immediately. Network-backed editors
    # receive a visible busy state, including Users/Roles when their directory has
    # not warmed yet; Statistics likewise shows a first-load status instead of a
    # misleading empty-data card.
    assert 'function adminModalLoadingHtmlV507' in app
    assert 'function finishDeferredAdminModalOpenV507' in app
    assert app.count('openAdminModal(modalKind, { body: adminModalLoadingHtmlV507(modalKind) });') >= 10
    for settings_endpoint in (
        '/api/admin/users',
        '/api/admin/roles',
        '/api/admin/customer-route-rules',
        '/api/admin/customer-emails',
        '/api/admin/bay-scanner-rules',
        '/api/admin/bay-auto-assigner',
        '/api/admin/cross-date-scan-settings',
        '/api/admin/production-files',
    ):
        assert settings_endpoint in app
    assert 'callerOwnsDeferredHydration = options?.body != null' in app
    assert 'els.adminModalBody.innerHTML = adminModalLoadingHtmlV507(kind);' in app
    assert '.catch((error) => failDeferredAdminModalOpenV507(kind, error));' in app
    assert '.admin-modal-loading-v507' in admin_css and '.admin-modal-loading-spinner-v507' in admin_css
    assert 'statistics-chart-loading-v507' in app
    assert '.statistics-chart-loading-v507' in statistics_css and '.statistics-chart-loading-spinner-v507' in statistics_css
    reject_settings_listener = 'event.target.closest?.(\'[data-admin-modal="rejectSettings"]\')'
    assert reject_settings_listener not in app
    # v0.507 cleanup removed the only exact shadowed named-function duplicate
    # found in app.js; keep the operator-facing bay label helper single-owned.
    assert app.count('function bayLocationDisplayLabel(') == 1

    integrity = (ROOT / "database" / "integrity.py").read_text(encoding="utf-8")
    assert 'lineItemSourceIdentityDetails' in integrity
    assert 'source_identity_collision' in integrity
    assert 'records were preserved' in integrity

    assert '20260908-v0.510' in index
    assert '## v0.507 - Runtime Performance Recovery, A+W Cutting Coverage, and Legacy Cleanup' in changelog


def test_shared_help_tutorial_and_close_button_contracts() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    time_utils = (ROOT / "database" / "time_utils.py").read_text(encoding="utf-8")

    for element_id in (
        "helpCenterBtn", "helpCenterPanel", "helpCenterCloseBtn", "helpStartTutorialBtn",
        "helpChatForm", "helpChatInput", "pageTutorialCoach", "pageTutorialCloseBtn",
        "pageTutorialBackBtn", "pageTutorialNextBtn",
    ):
        assert f'id="{element_id}"' in index
    for page in ("home", "statistics", "scan", "racks", "rejects", "bays", "admin"):
        assert f"  {page}: Object.freeze(" in app
    assert "function helpAssistantAnswer" in app
    assert "function startPageTutorial" in app
    assert "function positionTutorialCoach" in app
    assert "scheduleTutorialPosition" in app
    assert ".help-center-panel" in shared
    assert ".page-tutorial-coach" in shared
    assert 'class="app-secondary-button" id="pageTutorialBackBtn"' in index
    assert 'button.className = "app-secondary-button";' in app
    assert "button.app-secondary-button" in shared
    assert "@media (max-width: 620px)" in shared
    assert "20260908-v0.510" in index

    # Every visible X created by the three runtime-only preview dialogs must use
    # the same shared close component as static application dialogs.
    assert 'class="gui-close-button" data-production-email-close-v506' in app
    assert 'class="production-sketch-lightbox-close-v479 gui-close-button"' in app
    assert 'class="gui-close-button" data-cutting-label-close-v502' in app

    assert 'CURRENT_SCHEMA_VERSION = 20' in (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert '"v507_normalize_external_timestamps"' in migrations
    assert "def normalize_utc_timestamp" in time_utils


def test_v509_mobile_workflow_contracts() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    mobile = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert "CURRENT_SCHEMA_VERSION = 20" in contract
    assert "20260908-v0.510" in index
    assert 'pageSize: window.matchMedia("(max-width: 760px)").matches ? 10 : 50' in app
    assert 'homePageSize: window.matchMedia("(max-width: 760px)").matches ? 5 : 25' in app
    assert "const historyReasons = state.rejectCatalog.historyReasons || [];" in app
    assert "const historyLocations = state.rejectCatalog.historyLocations || [];" in app
    assert "els.adminModalBody.scrollTop = 0;" in app
    assert 'let helpChatPage = "";' in app
    assert "if (body) body.scrollTop = 0;" in app
    assert "authoritative handheld workflow and touch-layout pass" in mobile
    assert ".bay-map-page .bay-right-rail" in mobile
    assert "order: -1 !important" in mobile
    assert '.scan-page .scanner-panel:not(.bay-scanner-panel) .recent-table' in mobile
    assert "mobile tutorial and assistant actions use the shared blue control" in mobile
    assert ".page-tutorial-coach :is(.app-primary-button, .app-secondary-button)" in mobile
    assert "column-gap: 12px !important;" in mobile
    assert "html body #adminModal.admin-modal-panel:not([hidden])" in mobile
    assert "## v0.509 - Mobile Tutorial and Shared Control Polish" in changelog
    assert "## v0.508 - Complete Handheld Workflow and Safe Change Packaging" in changelog


def test_future_chat_change_guide_preserves_data_and_zip_structure() -> None:
    guide = (ROOT / "docs" / "FUTURE_CHAT_CHANGE_GUIDE.md").read_text(encoding="utf-8")

    assert "Increment APPLICATION_VERSION by exactly 1" in guide
    assert "Do not increment CURRENT_SCHEMA_VERSION unless" in guide
    assert "project-root-relative paths" in guide
    assert "On the TC22 profile, walk the complete operator route" in guide
    assert "Open and visually verify every affected GUI" in guide
    assert "Do not flatten files" in guide
    assert "exclude data/" in guide
    assert "overwrite/replace enabled" in guide


def test_v510_automation_handoff_and_scan_catalog_recovery_contracts() -> None:
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    controller = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert "$script:LogPath = $null" not in runner
    assert "browser-started runs pass the log watched by the web GUI" in runner
    assert "self._gui_status_lock = threading.Lock()" in controller
    assert "for attempt in range(6):" in controller
    assert "getattr(exc, \"winerror\", None) in {5, 32, 33}" in controller
    assert "def _write_gui_status(self, config: dict[str, Any], status: dict[str, Any]) -> bool:" in controller
    assert 'const stageSelect = document.getElementById("deliveryStageSelect");' not in app[:app.index("function dlsAutomationApplyImportSnapshot")]
    assert 'state.deliveryDateSelectSignatureV487 = "";' in app[:app.index("function dlsAutomationApplyImportSnapshot")]
    assert "for (let attempt = 0; attempt < 3; attempt += 1)" in app
    assert "if (!state.authenticated || attempt >= 2) break;" in app
    assert 'padStart(2, "0")' in app[:app.index("function dlsAutomationApplyImportSnapshot")]
    # An interrupted editor pass replaced digit 2 with 0 across app.js. Keep a
    # few high-value runtime sentinels here so that class of corruption cannot
    # quietly pass syntax checks again.
    assert 'airport_outbound: 20' in app
    assert 'year: "2-digit"' in app
    assert 'channel / 255' in app and '** 2.4' in app
    assert '/^T200\\d{12}$/' in app
    assert '"2": "nnwwnnnnw"' in app
    assert 'elementIndex % 2 === 0' in app
    assert 'statusCode === 200' in app
    assert 'workTypeId === 20' in app
    assert 'stages.slice(-2)' in app
    assert "## v0.510 - Automation Completion and Scan Date Recovery" in changelog


def test_v511_scan_cutting_progress_timestamps_reject_ribbon_and_label_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'function scanCuttingProgressPresentationV511' in app
    assert 'kind: "cutting"' in app
    assert 'cutting: copies.map((copy) => copy.cutting)' in app
    assert 'cutting: `<svg viewBox="0 0 24 24"' in app
    assert 'if (machine) return false;' in app[app.index('function fabricationNoFabConfirmedV481'):app.index('function compactMachineLabelV475')]
    assert 'scan-progress-flow-v481 scan-progress-flow-v485 is-paired-v486' in app
    assert 'colspan="8"' in app[app.index('const rejectIncidentRow'):app.index('const priorityRibbon = ""')]
    assert 'internal-reject-detail-tail-v154' not in app[app.index('const rejectIncidentRow'):app.index('const priorityRibbon = ""')]
    assert '/^T200\\d{12}$/' in app
    assert 'formatNumericDeliveryDate(deliveryDate)' in app[app.index('function orderDetailCuttingLabelV498'):app.index('function cuttingLabelPieceHtmlV507')]
    assert 'production-progress-time-v511' in app and '.production-progress-time-v511' in shared_css
    assert '"lastScannedAt": str(row_value(row, "last_scanned_at", "") or "")' in store
    assert 'v0.511: Scan now displays A+W Cutting' in store
    assert 'grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr)' in scan_css
    assert 'min-height: 31px !important;' in scan_css
    assert 'static/css/scan.css?v=20260910-v0.527' in index
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in index
    assert 'static/css/mobile.css?v=20260909-v0.517' in index
    assert 'grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) !important;' in mobile_css
    assert 'static/js/app.js?v=20260910-v0.527' in index
    assert '## v0.511 - Scan Cutting Progress and Label Reliability' in changelog


def test_v512_scan_reentry_order_detail_filters_and_bay_animation_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    mobile_css = (ROOT / "static" / "css" / "mobile.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert 'static/js/app.js?v=20260910-v0.527' in index
    assert 'static/css/scan.css?v=20260910-v0.527' in index
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in index
    assert 'static/css/mobile.css?v=20260909-v0.517' in index

    # A route transition must own/cancel the date-wide request instead of leaving
    # scanDateWideLoadingV485 as an unrecoverable latch.
    activate_start = app.index('function cancelScanDateWideLoadV512')
    activate_end = app.index('function scanWorkflowTargetV485', activate_start)
    activate = app[activate_start:activate_end]
    assert 'new AbortController()' in activate
    assert '}, 15000);' in activate
    assert '{ signal: controllerV512.signal }' in activate
    show_start = app.index('function showPage(page)')
    show_page = app[show_start:app.index('async function showOutboundOverrideDialog', show_start)]
    assert 'state.page === "scan" && page !== "scan" && state.scanDateWideLoadingV485' in show_page
    assert 'cancelScanDateWideLoadV512();' in show_page
    assert 'restartPendingLoadV512' in show_page

    # Sketches use the maintained deferred source path and Order Details actually
    # starts its hydrator after each dynamic dialog repaint.
    assert app.count('data-order-sketch-src-v507=') >= 2
    sketch_start = app.index('function hydrateOrderDetailSketchesV507')
    sketch_hydrator = app[sketch_start:app.index('function cuttingProgressPresentationV498', sketch_start)]
    assert 'frame.hasAttribute("src")' in sketch_hydrator
    assert 'loadFrame(frames[0]);' in sketch_hydrator
    detail_renderer = app[app.index('function renderOrderDetailV470'):app.index('function mergeOrderProductionDetailV507')]
    assert 'hydrateOrderDetailSketchesV507();' in detail_renderer

    # No Fab still owns the fabrication checkpoint slot. v0.514 intentionally
    # removes Scan-column timestamps while preserving Order Details timestamps.
    assert 'function noFabProgressStepV512' in app
    assert 'kind: "no-fab"' in app
    progress_renderer = app[app.index('function progressStepHtmlV475'):app.index('function scanProgressMarkupV475', app.index('function progressStepHtmlV475'))]
    assert 'scan-progress-time-v512' not in progress_renderer
    assert 'production-progress-time-v511' in app and '.production-progress-time-v511' in shared_css
    assert 'is-no-fab-v512' in app and '.is-no-fab-v512' in shared_css

    # v0.514 consolidates stage completion into Status. Without a Machine filter
    # it describes the entire workflow; with WaterJet/Denver selected it describes
    # that fabrication checkpoint. The retired Production Progress buttons stay gone.
    assert 'remaining: "Not Complete"' in app
    assert 'function scanWorkflowCompletionStateV514' in app
    assert 'if (filter === "remaining") return status !== "complete";' in app
    for token in ('machine-no-fab', 'machine-waterjet', 'machine-denver'):
        assert f'data-filter="{token}"' in index
    for token in ('cutting-incomplete', 'cutting-complete', 'waterjet-incomplete', 'waterjet-partial', 'waterjet-complete', 'denver-incomplete', 'denver-complete'):
        assert f'data-filter="{token}"' not in index
    assert 'aria-label="Production progress filters"' not in index
    assert 'hydrateFabricationFilterCatalogV512' in app
    assert 'rows.slice(offset, offset + 80)' in app
    assert 'hasAnyPermission(["global_search", "view_delivery_lists", "view_reports"])' in app
    assert 'require_any_permission("global_search", "view_delivery_lists", "view_reports")' in server
    assert 'filter_accessible_production_status_requests' in store
    assert 'user_can_access_stage(user' in store[store.index('def filter_accessible_production_status_requests'):store.index('def get_stations', store.index('def filter_accessible_production_status_requests'))]

    # Cutting Label is a sibling immediately right of the sketch on wide layouts
    # and the label renderer no longer emits the maximize affordance.
    assert '<div class="production-item-sketch-v476 production-item-sketch-v518">' in detail_renderer
    assert '<div class="production-item-cutting-label-v512 production-item-cutting-label-v518">' in detail_renderer
    label_renderer = app[app.index('function orderDetailCuttingLabelV498'):app.index('function cuttingLabelPieceHtmlV507')]
    assert 'data-cutting-label-maximize-v502' not in label_renderer
    assert 'grid-template-columns: minmax(330px, 370px) minmax(246px, 264px) minmax(0, 1fr)' in shared_css

    # Date is back on the left while the station retains the center grid track.
    assert 'scanner-panel-date-select-v196' in scan_css and 'grid-column: 1 !important;' in scan_css
    mobile_v512 = mobile_css[mobile_css.index('v0.512 Scan date selector returns'): ]
    assert 'grid-column: 1 !important;' in mobile_v512
    assert 'scanner-panel-station-v196' in mobile_v512 and 'grid-column: 2 !important;' in mobile_v512

    # Bay Map transfer direction is explicitly right-most-first and slower, with
    # short vertical bump frames on both travel legs.
    transit = app[app.index('function bayTransitAnimationProfileV459'):app.index('/** Start the Bay Map truck from its route origin')]
    assert 'const paneMotionSeconds = 1.35;' in transit
    assert 'Math.max(5.5, Math.min(10.5' in transit
    assert 'outboundPanes.length - 1 - index' in transit
    assert 'inboundPanes.length - 1 - index' in transit
    assert 'const bumpFrames =' in transit
    assert 'y: -59' in transit and 'y: -58.5' in transit

    assert 'priority_annotations = self.priority_banner_annotations' in store
    assert 'item["priorityBanner"] = dict(annotation)' in store
    assert '## v0.512 - Scan Re-entry, Production Filters, and Order Detail Recovery' in changelog



def test_v514_scan_search_order_detail_and_production_reporting_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    for asset in (
        'static/css/styles.css?v=20260910-v0.527',
        'static/css/statistics.css?v=20260910-v0.527',
        'static/css/scan.css?v=20260910-v0.527',
        'static/css/shared-ui.css?v=20260910-v0.527',
        'static/js/app.js?v=20260910-v0.527',
    ):
        assert asset in index

    # Scan keeps the compact cells but no longer spends row height on timestamps.
    progress_renderer = app[app.index('function progressStepHtmlV475'):app.index('function scanProgressMarkupV475', app.index('function progressStepHtmlV475'))]
    assert 'scan-progress-time-v512' not in progress_renderer
    assert '.scan-progress-time-v512' not in scan_css
    assert 'grid-template-rows: auto !important;' in scan_css

    # One completion model composes with Machine. The duplicate Production
    # Progress section/buttons are retired from markup, code labels, and styling.
    assert 'function scanWorkflowCompletionStateV514' in app
    completion = app[app.index('function scanWorkflowCompletionStateV514'):app.index('function isScanFilterActive')]
    assert 'selectedMachineFilters.length && fabricationCompletion.machine !== "No Fab"' in completion
    assert 'if (fabricationCompletion.complete) return "complete";' in completion
    assert 'return hasProgress ? "partial" : "remaining";' in completion
    assert 'production:' not in app[app.index('const SCAN_FILTER_GROUPS'):app.index('const SCAN_TABLE_COLUMNS')]
    assert 'aria-label="Production progress filters"' not in index
    assert '.scan-filter-production-section-v512' not in scan_css

    # Smart Search dedicates a full right-aligned row to the larger progress flow
    # and exposes External Remake + reason beside Customer.
    assert 'global-result-remake-meta-v514' in app
    assert 'global-result-progress-row-v514' in app
    assert '.global-result-progress-row-v514' in styles_css
    assert 'justify-content: flex-end;' in styles_css[styles_css.index('v0.514 Smart Search readability'):]
    assert 'min-width: 92px !important;' in styles_css
    assert 'font-size: 8.25px !important;' in styles_css

    # Order Details is wider, shows the complete label thumbnail beside the sketch,
    # and no longer emits the old Piece x of y / CUT summary strip.
    assert 'width: min(1580px, calc(100vw - 22px)) !important;' in shared_css
    assert 'width: min(100%, 326px) !important;' in shared_css
    cutting_piece = app[app.index('function cuttingLabelPieceHtmlV507'):app.index('function orderDetailCuttingLabelsV501')]
    assert 'production-cutting-piece-summary-v507' not in cutting_piece

    # Today is independent from chart range; the range chart exposes an auditable
    # table-by-machine with opt-in Remake/Reject/Rush and a detailed piece ledger.
    assert 'Today’s Production Count' in index
    assert 'Actual new-piece counts by glass type and machine for today.' in index
    assert '<option value="production-count">Production count by machine</option>' in index
    assert 'id="statisticsProductionIncludeRemakesV514"' in index
    assert 'id="statisticsProductionIncludeRejectsV514"' in index
    assert 'id="statisticsProductionIncludeRushesV514" type="checkbox">' in index
    assert 'id="statisticsProductionDetailedV514"' in index
    assert 'statisticsProductionIncludeRushesV514: false' in app
    assert 'function ensureTodayProductionReportV514' in app
    assert 'function ensureStatisticsProductionReportV514' in app
    assert 'function statisticsProductionMachineRowsV514' in app
    assert 'function statisticsProductionCountTableHtmlV514' in app
    assert '<th>Barcode</th><th>Process</th><th>Queue</th><th>Reason</th>' in app
    assert '.statistics-production-detail-table-v514 { min-width: 1680px; }' in statistics_css

    # Daily production reporting consistently uses compact dates and a polished
    # machine-aware email without mutating Scan hot-path data.
    assert 'return dates.map((value) => formatNumericDeliveryDate(value) || value).join(" · ");' in app
    assert 'DAILY PRODUCTION COUNT - ${displayDate}' in app
    assert 'TODAY AT A GLANCE' in app
    assert 'NEW PRODUCTION BY MACHINE' in app
    assert '"barcode": str(snapshot.get("barcode") or "").strip()' in store
    assert '"processState": str(snapshot.get("processState") or "").strip()' in store
    assert '"queueState": str(snapshot.get("queueState") or "").strip()' in store
    assert '"rush": bool(is_rush_item({' in store
    assert 'require_any_permission("global_search", "view_delivery_lists", "view_reports")' in server
    assert '## v0.514 - Workflow Filters and Production Reporting' in changelog

def test_v513_smart_search_external_remake_filters_and_badges_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    styles_css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    bays_css = (ROOT / "static" / "css" / "bays.css").read_text(encoding="utf-8")
    admin_css = (ROOT / "static" / "css" / "admin.css").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    for asset in (
        'static/css/styles.css?v=20260910-v0.527',
        'static/css/scan.css?v=20260910-v0.527',
        'static/css/admin.css?v=20260910-v0.527',
        'static/css/bays.css?v=20260908-v0.513',
        'static/css/shared-ui.css?v=20260910-v0.527',
        'static/css/mobile.css?v=20260909-v0.517',
        'static/js/app.js?v=20260910-v0.527',
    ):
        assert asset in index

    label_renderer = app[app.index('function orderDetailCuttingLabelV498'):app.index('function cuttingLabelPieceHtmlV507')]
    assert 'const remake = isExternalRemakeItem(item);' in label_renderer
    assert 'const remake = Number(cutting.keyIndex || 0) > 0;' not in label_renderer

    assert 'function globalSearchProgressStepsV513' in app
    assert 'scanCuttingProgressPresentationV511(result)' in app
    assert 'stage.lastScanTime || stage.lastScannedAt || ""' in app
    assert 'is-complete-v513' in app and 'is-no-fab-v513' in app
    assert 'global-result-progress-step-v513.is-complete-v513' in styles_css
    assert 'global-result-progress-step-v513.is-no-fab-v513' in styles_css
    assert 'def attach_cutting_search_states_v513' in store
    assert 'return self.attach_cutting_search_states_v513(matched_results)' in store

    attention = index[index.index('aria-label="Attention filters"'):index.index('aria-label="Route filters"')]
    assert attention.index('data-filter="internal-rejects"') < attention.index('data-filter="remakes"') < attention.index('data-filter="rushes"')
    assert 'External Remakes' in attention
    assert '.scan-filter-production-section-v512' not in scan_css
    assert '.scan-filter-route-section-v465 { grid-column: 1 !important; }' in scan_css
    assert '.scan-filter-machine-section-v512 { grid-column: 2 !important; }' in scan_css
    assert 'font-size: 8.4px !important;' in scan_css

    assert '#bayActionButtons.bay-tool-card-grid-v470 > .bay-tool-card-v470[data-bay-action="old-bays"]' in bays_css
    assert 'position: relative !important;' in bays_css[bays_css.index('v0.513 Old Bays attention badge containment'):]
    assert '#adminPage .superseded-review-open[data-admin-gui-launch]' in admin_css
    assert 'overflow: visible !important;' in admin_css[admin_css.index('v0.513 Superseded-review count badge visibility'):]
    assert '## v0.513 - Smart Search Production Progress and Attention Polish' in changelog


def test_v515_progress_layout_label_width_and_sketch_recovery_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    styles_css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    production_files = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'Current maintained release: **v0.527**' in readme
    for asset in (
        'static/css/styles.css?v=20260910-v0.527',
        'static/css/scan.css?v=20260910-v0.527',
        'static/css/shared-ui.css?v=20260910-v0.527',
        'static/js/app.js?v=20260910-v0.527',
    ):
        assert asset in index
    assert 'static/css/statistics.css?v=20260910-v0.527' in index

    # Smart Search keeps its dedicated wide row, but v0.515 returns the flow to
    # the natural left edge instead of making the starting point move by width.
    v515_search = styles_css[styles_css.index('v0.515 Smart Search progress alignment'):]
    assert 'justify-content: flex-start !important;' in v515_search
    assert 'width: min(100%, 1180px) !important;' in v515_search
    assert 'margin-left: 0 !important;' in v515_search
    assert 'justify-items: start !important;' in v515_search

    # Scan owns compact centered checkpoints and clearly sized workflow arrows.
    v515_scan = scan_css[scan_css.index('v0.515 Scan progress geometry'):]
    assert 'min-height: 30px !important;' in v515_scan
    assert 'height: 30px !important;' in v515_scan
    assert 'text-align: center !important;' in v515_scan
    assert 'width: 14px !important;' in v515_scan
    assert 'font-size: 16px !important;' in v515_scan

    # The physical 436px A+W label has enough scaled frame width and no side
    # margins that can overflow its border-box column. Order progress separates
    # name, state/count, and timestamp instead of colliding on one line.
    v515_shared = shared_css[shared_css.index('v0.515 Order Details label width + normalized progress'):]
    assert 'width: min(1680px, calc(100vw - 18px)) !important;' in v515_shared
    assert 'minmax(364px, 382px)' in v515_shared
    assert 'width: min(100%, 372px) !important;' in v515_shared
    assert 'width: 340px !important;' in v515_shared
    assert 'height: 405px !important;' in v515_shared
    assert 'margin: 0 auto 8px !important;' in v515_shared
    assert 'transform: scale(.775) !important;' in v515_shared
    assert 'grid-template-rows: auto auto auto !important;' in v515_shared
    assert 'grid-row: 2 !important;' in v515_shared
    assert 'grid-row: 3 !important;' in v515_shared
    assert 'font-size: 18px !important;' in v515_shared

    # Missing network sketches get one deduplicated sketch-only refresh. A
    # transient PDF read/empty parse is not persisted as durable no-sketch state.
    assert 'self._sketch_empty_cache_at: dict[str, float] = {}' in production_files
    assert 'if asset_id in self._asset_lookup and assignments' in production_files
    assert 'time.time() - empty_at < 3.0' in production_files
    assert 'self.refresh_async(["sketch"])' in production_files
    assert '"sketchRefreshPending": bool(sketch_refresh_pending)' in production_files

    # The browser bypasses its long production cache only for a genuinely
    # missing sketch and limits revalidation to two retries while Order Details
    # for that same order remains open.
    assert 'orderDetailSketchRetryV515: new Map()' in app
    assert 'function orderDetailProductionNeedsSketchRetryV515' in app
    assert 'return orderSketches.length === 0 && (items.length === 0 || !hasAnyItemSketch);' in app
    assert 'function scheduleOrderDetailSketchRetryV515' in app
    assert 'function cancelOrderDetailSketchRetryV515' in app
    assert 'previous.timer || previous.attempts >= 2' in app
    assert 'previous.attempts === 0 ? 1400 : 3600' in app
    assert 'const cachedNeedsSketchRetry' in app
    assert 'cancelOrderDetailSketchRetryV515(state.orderDetailOpenOrderV474)' in app
    assert '## v0.515 - Progress Layout and Sketch Recovery' in changelog


def test_v516_generated_sketch_aw_eastern_and_order_details_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    time_utils = (ROOT / "database" / "time_utils.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'static/css/scan.css?v=20260910-v0.527' in index
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in index
    assert 'static/js/app.js?v=20260910-v0.527' in index

    assert 'PLANT_TIME_ZONE_V516 = "America/New_York"' in app
    assert 'timeZone: PLANT_TIME_ZONE_V516' in app
    assert 'PLANT_TIME_ZONE_NAME = "America/New_York"' in time_utils
    assert 'normalize_aw_plant_timestamp' in store
    assert 'v516_aw_eastern_timestamp_contract' in migrations

    assert 'function generatedProductionSketchV516' in app
    assert 'GENERATED REFERENCE · VERIFY AGAINST A+W / SHOP DATA' in app
    assert 'productionGenerated' not in app  # no parallel asset API/source layer
    assert 'production-sketch-page-cache' in production
    assert 'def cached_sketch_page' in production
    assert 'service.cached_sketch_page(asset_id, page)' in server

    progress = app[app.index('function orderDetailProgressV476'):app.index('function normalizedOrderDetailItemV477')]
    assert 'const cuttingQty = Math.max(1' in progress
    assert '`${Math.max(0, Number(step.scanned || 0))}/${Math.max(0, Number(step.qty || 0))}`' in progress
    assert 'step.kind === "cutting" ? step.detail' not in progress
    assert 'function orderDetailAwInformationV516' in app
    assert 'cuttingGenerationAtReject' in app
    assert 'Current Batch' in app and 'Current Optimization' in app and 'Optimization Status' in app
    render = app[app.index('function renderOrderDetailV470'):app.index('function mergeOrderProductionDetailV507')]
    assert 'production-item-card-header-v521' in render
    assert 'production-item-card-header-v518' in render
    assert 'production-item-actions-v516' in app

    v516_shared = shared[shared.index('v0.516 Order Details workspace') :]
    assert 'width: min(1900px, calc(100vw - 8px)) !important;' in v516_shared
    assert 'grid-template-columns: 17px minmax(0, 1fr) auto !important;' in v516_shared
    assert 'justify-content: flex-end !important;' in v516_shared
    assert 'production-generated-sketch-v516' in v516_shared
    v516_scan = scan[scan.index('v0.516 wider compact Scan progress checkpoints') :]
    assert 'width: 98px !important;' in v516_scan
    assert 'width: 25% !important;' in v516_scan
    assert '## v0.516 -' in changelog


def test_v518_manual_fabrication_and_compact_order_details_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in index
    assert 'static/js/app.js?v=20260910-v0.527' in index

    # Manual sketch text/annotations and bounded old-order filename variants feed
    # the same machine assignment path; label evidence is a fallback, not a new DB.
    assert 'def _pdf_annotation_text' in production
    assert 'for key in ("/Contents", "/RC", "/Subj", "/T")' in production
    assert 'root.glob(f"{token}*.pdf")' in production
    assert 'candidates.update({asset.asset_id: asset for asset in self._exact_order_sketches(order, job)})' in production
    assert 'label-mirror-cutout' in production
    assert 'Mirror with an A+W cutout operation requires Waterjet' in production
    assert 'machine": "Fabrication"' in production
    assert 'def aw_fabrication_hints_for_requests' in store
    assert 'label_hint=label_hint' in store
    assert 'label_hints = STORE.aw_fabrication_hints_for_requests(raw_items)' in server
    assert 'label_hint=label_hints.get(request_key)' in server
    assert 'candidates.push({ key, order, item, job, product, lastRejectedAt' in app

    render = app[app.index('function renderOrderDetailV470'):app.index('function mergeOrderProductionDetailV507')]
    assert 'titleNode.textContent = `Order ${String(payload.order || "-")}`' in render
    assert 'productionExplorerDeliveryDateV518' in render
    assert 'productionOrderOverviewSketchV480(orderFiles, payload, productionLoaded)' in render
    assert 'production-item-card-header-v518' in render
    assert 'production-item-card-header-v521' in render
    assert 'production-item-facts-v516' not in render
    assert 'fabricationStatusHtmlV470(fabrication, item)' not in render
    assert 'production-progress-section-v518' in render
    assert 'production-item-cutting-label-v518' in render

    reject = app[app.index('function orderDetailInternalAwRejectsV485'):app.index('function orderDetailAwInformationV516')]
    assert 'formatOperationalTimestampV511(reject.breakageAt)' in reject
    for label in ('Reason', 'Machine', 'Qty', 'Rejected by', 'Batch', 'OPT', 'Status'):
        assert f'<small>{label}</small>' in reject

    v518 = shared[shared.index('v0.518 label-aware fabrication') :]
    assert 'grid-template-columns: minmax(470px, 1fr) 354px !important;' in v518
    assert 'width: 354px !important;' in v518
    assert 'width: 340px !important;' in v518
    assert 'color: var(--glass-type-color' in v518
    assert 'production-order-snapshot-v518' in v518
    assert 'production-aw-reject-v518' in v518
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.518 - Manual Fabrication Detection and Order Details Polish' in changelog


def test_v519_order_details_restored_three_column_overview_contract() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    assert 'APPLICATION_VERSION = "527"' in contract
    assert '<h2 id="productionExplorerTitleV470">Order Details</h2>' in app
    assert 'productionOrderOverviewSketchV480(orderFiles, payload, productionLoaded)' in app
    assert 'production-explorer-header-fact-v526 is-route' in app
    assert 'production-item-main-v519' in app
    assert 'grid-template-columns: minmax(320px, 350px) 282px minmax(0, 1fr)' in shared
    assert 'width: 268px !important' in shared
    assert 'grid-column: 3 !important' in shared
    assert 'width: 104px !important' in scan
    assert 'grid-template-columns: 18px minmax(0, 1fr) auto' in scan
    assert 'static/css/scan.css?v=20260910-v0.527' in html
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html


def test_v520_job_identity_print_machine_and_order_detail_compaction_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static" / "css" / "print.css").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    assert 'static/css/print.css?v=20260910-v0.527' in html
    assert 'static/css/shared-ui.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html

    # Production-file identity accepts Order Nr. OR bounded Job Nr. tokens. Exact
    # Job-number machine files are valid machine evidence, while sketches still
    # require their page-level Order.Item marker.
    assert 'def _job_identity_tokens' in production
    assert 'def _exact_sketches_for_token' in production
    assert 'self._exact_order_sketches(order, job)' in production
    assert 'asset.kind in {"program", "completed_wj"}' in production
    assert '_compact(Path(asset.name).stem) == matched_job' in production

    # Scan Filters scrolls enough to reveal the compact drawer, and Print/Export
    # preserves the original Status/Attention grid while adding Machine at right.
    assert 'function selectedPrintMachineValuesV520' in app
    assert 'function hydratePrintMachineCatalogV520' in app
    assert 'machineEvidencePendingV520' in app
    assert 'scrollScanFiltersIntoViewV520' in app
    assert 'rect.bottom > usableBottom' in app
    assert 'id="printMachineOptions"' in html
    assert '"status status attention attention machine machine"' in print_css
    assert '.print-machine-section-v520 { grid-area: machine; }' in print_css

    cutting = app[app.index('function orderDetailCuttingLabelsV501'):app.index('function productionSketchVisualV476')]
    assert 'physical piece' not in cutting
    assert 'Prior generations' not in cutting
    reject = app[app.index('function orderDetailInternalAwRejectsV485'):app.index('function orderDetailAwInformationV516')]
    assert '<small>OPT</small>' in reject
    assert '<small>Optimization</small>' not in reject
    sketch = app[app.index('function productionSketchVisualV476'):app.index('function productionOrderOverviewSketchV480')]
    assert 'production-sketch-maximize-v479' in sketch
    render = app[app.index('function renderOrderDetailV470'):app.index('function mergeOrderProductionDetailV507')]
    assert 'data-production-preview-asset-v470' in render
    assert 'production-sketch-caption-v476' not in render
    assert 'production-item-actions-v520' in render
    v520 = shared[shared.index('v0.520 Order Details compact production layout') :]
    assert 'width: min(1780px, calc(100vw - 18px)) !important;' in v520
    assert 'grid-template-columns: minmax(315px, 335px) 300px minmax(0, 1fr)' in v520
    assert 'justify-content: flex-start !important;' in v520
    assert 'grid-template-columns: 122px minmax(190px, 1.5fr)' in v520
    assert '## v0.520 -' in changelog



def test_v521_machine_library_fabrication_warm_cache_and_order_controls_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static" / "css" / "print.css").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert '## v0.521 - Machine Library, Fabrication Warm Cache, and Order Details Controls' in changelog
    assert 'aria-label="Application version 0.527"' in html
    assert '<strong>0.527</strong>' in html
    for asset in (
        'static/css/scan.css?v=20260910-v0.527',
        'static/css/print.css?v=20260910-v0.527',
        'static/css/shared-ui.css?v=20260910-v0.527',
        'static/js/app.js?v=20260910-v0.527',
    ):
        assert asset in html

    # One machine library owns matching, colors, display names, and progress rank.
    assert 'self.machine_definitions' in production
    assert '"machines": [dict(row, terms=list(row.get("terms") or [])) for row in self.machine_definitions]' in production
    assert 'def get_machine_configuration' in store
    assert 'def update_machine_configuration' in store
    assert '"update_machine_configuration"' in store
    assert 'if parsed.path == "/api/machine-configuration"' in server
    assert 'require_any_permission("manage_lookup_values", "manage_production_files")' in server
    assert 'insertTab("lookup:machine", "Machines"' in app
    assert 'function machineLookupManagerHtmlV521' in app
    assert 'Machine &amp; Production Files' not in html
    assert '>Production Files</h2>' in html
    production_modal = app[app.index('function productionFileSettingsModalHtmlV470'):app.index('function renderProductionFilesOverviewV470')]
    assert 'data-production-settings-tab-v476="machines"' not in production_modal

    # Delivery-date warmup is bounded and retains only the five most recent dates.
    assert 'fabricationDeliveryCacheV521: new Map()' in app
    assert 'fabricationDeliveryCacheLimitV521: 5' in app
    assert 'function fabricationStatusItemKeyV521' in app
    assert 'function rememberFabricationDeliveryV521' in app
    assert 'async function warmFabricationDeliveryV521' in app
    assert 'offset += 80' in app[app.index('async function warmFabricationDeliveryV521'):app.index('async function runGlobalSearch')]
    assert 'typeof warmFabricationDeliveryV521 === "function"' in app and 'warmFabricationDeliveryV521(date, projectedItems)' in app

    # Reject Machine uses A+W Location first, and the item controls/print buttons
    # use the compact v0.521 production workspace.
    reject = app[app.index('function orderDetailInternalAwRejectsV485'):app.index('function orderDetailAwInformationV516')]
    assert 'reject.location || reject.sourceLocation || reject.registrationPoint || reject.workType || reject.machine' in reject
    assert 'production-sketch-print-v521' in app
    assert 'production-label-print-v521' in app
    assert 'production-item-actions-v521' in app
    assert 'production-item-card-header-v521' in app
    assert '.production-aw-reject-v518' in shared
    assert 'font-size: 10.35px !important' in shared

    # Stage identity icons persist; configured machine colors flow to Scan/Print.
    progress = app[app.index('function progressStepHtmlV475'):app.index('function scanProgressMarkupV475')]
    assert 'globalSearchIconV433(iconKind)' in progress
    assert 'scan-machine-filter-v521' in scan
    assert 'is-machine-choice-v521' in print_css
    assert 'is-machine-all' in print_css

    # Opening Scan filters animates rather than jumping, except reduced motion.
    wire = app[app.index('function wireEvents()'):app.index('document.addEventListener("toggle"', app.index('function wireEvents()'))]
    assert 'duration = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ? 0 : 320' in wire
    assert 'window.requestAnimationFrame(animate)' in wire


def test_v522_durable_cutting_and_fabrication_progress_monitor_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")

    # Only reject/remake lifecycle evidence belongs in progress identity. Mutable
    # order facts and ordinary Cutting status changes must not erase completion.
    lifecycle = app[app.index('function fabricationRevisionV521'):app.index('function fabricationStatusKeyV474')]
    assert 'item?.lastRejectedAt' in lifecycle
    assert 'remakeGeneration' in lifecycle
    assert 'cutting.generationKey || cutting.keyIndex' in lifecycle
    assert 'sourceLastChangedAt' not in lifecycle
    assert 'cutting.batch' not in lifecycle
    assert 'def _fabrication_lifecycle_signature' in production
    assert 'cached[1].get("fabricated") is True' in production
    assert '0 if fabricated is True or not required else self.cache_seconds' in production
    assert 'reset-only-on-reject-or-remake' in store
    assert 'remembered_cutting_completion' in store

    # The existing compact catalog heartbeat drives one throttled monitor. It
    # retries unfinished Cutting/fabrication and stops requesting completed rows.
    assert 'cuttingStatusCacheV522: new Map()' in app
    assert 'productionProgressCheckedV522: new Map()' in app
    assert 'function monitorPendingProductionProgressV522' in app
    assert 'monitorPendingProductionProgressV522();' in app
    hydrate = app[app.index('async function hydrateFabricationStatusesV474'):app.index('async function hydrateFabricationFilterCatalogV512')]
    assert 'const cuttingDue = !cuttingComplete' in hydrate
    assert 'const fabricationDue = cached' in hydrate
    assert ': (!progressCheck.at || cachedAge >=' in hydrate
    assert 'progressRetryAfterSeconds' in hydrate
    assert '"cutting": cutting' in server
    assert 'data-check-fab-v522' in app


def test_v523_lifecycle_aware_production_checks_and_order_detail_cache_contracts() -> None:
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    importer = (ROOT / "automation" / "sql_delivery_export" / "import_delivery_folder.py").read_text(encoding="utf-8")
    runner = (ROOT / "automation" / "sql_delivery_export" / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8-sig")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert changelog.startswith('## v0.527 - Stable Production Checks, A+W Review Flags, and Faster Navigation')
    assert '## v0.523 - Lifecycle-Aware Production Checks and Faster Order Details' in changelog
    assert 'aria-label="Application version 0.527"' in index
    assert '<strong>0.527</strong>' in index
    assert 'static/js/app.js?v=20260910-v0.527' in index
    assert 'data/production-sketch-page-cache/*.pdf' in gitignore

    # The scanner store owns lifecycle decisions; the PowerShell reader consumes
    # only a read-only optimization plan and falls back to the full bounded query.
    assert 'def aw_cutting_sync_plan' in store
    assert '"version": "v523-cutting-sync-plan-1"' in store
    assert 'new_reject' in store and 'job_changed' in store and 'remake_changed' in store
    assert '--production-plan-only' in importer
    assert 'store.aw_cutting_sync_plan' in importer
    assert 'function Get-ScannerCuttingSkipPlan' in runner
    assert 'Get-ScannerCuttingSkipPlan -Config $script:Config' in runner
    assert 'Completed-Cutting skip planning was unavailable; running the full bounded A+W production query' in runner
    assert 'Manual/forced A+W production synchronization is bypassing the completed-Cutting skip plan.' in runner
    assert 'CREATE TABLE #SkipItems' in runner
    assert 'ISNULL(ji.KEYINDEX,0) <= skip.KeyIndex' in runner
    assert 'ISNULL(os.KEYINDEX,0) <= skip.KeyIndex' in runner
    assert 'ISNULL(sh.KEYINDEX,0) <= skip.KeyIndex' in runner
    assert 'EXISTS (SELECT 1 FROM #ProcessItems pending' in runner
    assert 'version="v523-aw-production-6"' in runner
    assert 'completedSkippedItemCount' in runner

    # Production-index revisions keep completed fabrication memory. The reject /
    # remake lifecycle key remains the mechanism that makes a piece queryable again.
    revision = app[app.index('function syncFabricationRevisionV522'):app.index('function requestFabricationBatchV522')]
    assert 'status?.fabricated !== true' in revision
    assert 'state.fabricationStatusCacheV474.clear()' not in revision

    # Order Details keeps recent payloads warm and prioritizes only the operator's
    # useful sketch frames rather than synchronously loading a whole multi-page PDF.
    core = app[app.index('function fetchOrderDetailCoreV507'):app.index('function orderDetailProductionNeedsSketchRetryV515')]
    production = app[app.index('function fetchOrderDetailProductionV507'):app.index('async function openOrderDetailV470')]
    sketches = app[app.index('function hydrateOrderDetailSketchesV507'):app.index('function cuttingProgressPresentationV498')]
    assert 'age < 120000' in core
    assert 'age < 300000' in production
    assert 'orderDetailProductionNeedsSketchRetryV515' in production
    assert 'frame.loading = "eager"' in sketches
    assert 'state.orderDetailFocusItemV477' in sketches
    assert 'rootMargin: "1200px 0px"' in sketches


def test_v524_inventory_page_api_schema_and_responsive_contract() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "inventory.css").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    migrations = (ROOT / "database" / "migrations.py").read_text(encoding="utf-8")
    azure_schema = (ROOT / "database" / "azure_schema.sql").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'static/css/inventory.css?v=20260910-v0.527' in html
    assert 'static/js/app.js?v=20260910-v0.527' in html
    assert 'data-page-target="inventory"' in html
    sidebar = html[html.index('<nav class="app-nav"'):html.index('</nav>', html.index('<nav class="app-nav"'))]
    assert sidebar.index('data-page-target="rejects"') < sidebar.index('data-page-target="inventory"') < sidebar.index('data-page-target="admin"')
    assert 'id="inventoryPage"' in html
    assert 'id="inventoryLocationSelect"' in html
    assert 'Full Inventory' in html and 'Cycle Inventory' in html
    assert 'id="inventoryHistoryPanel"' in html
    assert 'id="inventoryHistoryCloseBtn" class="gui-close-button"' in html
    assert 'id="inventoryManualCloseBtn" class="gui-close-button inventory-manual-close"' in html
    assert 'id="inventoryManualGlass"' in html and 'id="inventoryManualItemId"' in html
    assert 'id="inventoryManualQty"' in html and 'id="inventoryManualSqft"' in html
    assert 'Physical Scans' in html and 'Reconciliation' in html and 'System Snapshot' in html
    assert 'view_inventory' in store and 'scan_inventory' in store and 'manage_inventory' in store
    assert 'def start_inventory_session' in store
    assert 'def record_inventory_scan' in store
    assert 'def record_inventory_manual_entry' in store
    assert 'def export_inventory_xlsx' in store
    assert 'page_size = min(max(int(page_size or 150), 25), 250)' in store
    assert 'parsed.path == "/api/inventory/catalog"' in server
    assert 'parsed.path == "/api/inventory/export.xlsx"' in server
    assert 'parsed.path == "/api/inventory/manual-entry"' in server
    assert '"v524_inventory_snapshots"' in migrations
    assert 'CREATE TABLE IF NOT EXISTS inventory_sessions' in migrations
    assert 'CREATE TABLE IF NOT EXISTS inventory_expected_items' in migrations
    assert 'CREATE TABLE IF NOT EXISTS inventory_scans' in migrations
    assert 'CREATE TABLE IF NOT EXISTS inventory_item_mappings' in migrations
    assert 'CREATE TABLE dbo.inventory_sessions' in azure_schema
    assert 'CREATE TABLE dbo.inventory_expected_items' in azure_schema
    assert 'CREATE TABLE dbo.inventory_scans' in azure_schema
    assert 'CREATE TABLE dbo.inventory_item_mappings' in azure_schema
    assert 'G38CLR' in migrations and 'G14CLR' in migrations and '14MIRROR' in migrations
    assert 'function renderInventorySessionV524' in app
    assert 'async function loadInventoryTabV524' in app
    assert 'function openInventoryManualV524' in app
    assert '150' in app[app.index('async function loadInventoryTabV524'):app.index('function renderInventoryHistoryV524')]
    assert '.inventory-reconcile-row.is-match' in css
    assert '.inventory-reconcile-row.is-alert' in css
    assert '.inventory-reconcile-row.is-pending .inventory-difference' in css
    assert '.inventory-tabs button{flex:0 0 auto}' in css
    assert '.top-nav-icon.inventory{-webkit-mask:' in css and 'mask:url(' in css
    assert 'function inventorySetControlHiddenV524' in app
    assert 'function suspendInventoryUiV525' in app
    suspend_block = app[app.index('function suspendInventoryUiV525'):app.index('function wireInventoryEventsV524')]
    assert 'inventoryScanInput?.blur()' in suspend_block
    assert 'inventoryManualModal.hidden = true' in suspend_block
    assert 'inventoryHistoryPanel.hidden = true' in suspend_block
    assert '/api/scans' not in suspend_block and 'record_scan' not in suspend_block
    assert 'Ready for the next piece.' in app
    assert '@media (max-width:720px)' in css
    assert '@media (max-width:430px)' in css
    assert 'Current maintained release: **v0.527**' in readme
    assert changelog.startswith('## v0.527 - Stable Production Checks, A+W Review Flags, and Faster Navigation')




def test_v526_scan_cadence_date_cache_shared_controls_and_order_detail_contract() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    shared = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    scan = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static" / "css" / "print.css").read_text(encoding="utf-8")
    operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert changelog.startswith('## v0.527 - Stable Production Checks, A+W Review Flags, and Faster Navigation')
    for asset in (
        'static/css/scan.css?v=20260910-v0.527',
        'static/css/print.css?v=20260910-v0.527',
        'static/css/shared-ui.css?v=20260910-v0.527',
        'static/js/app.js?v=20260910-v0.527',
    ):
        assert asset in html
    assert 'static/css/inventory.css?v=20260910-v0.527' in html

    # Date switching reuses only signature-matching date bundles; successful
    # scans invalidate that date immediately instead of restoring stale qty.
    assert 'SCAN_DATE_CACHE_LIMIT_V526 = 5' in app
    assert 'function cachedScanDateBundleV526' in app
    assert 'function rememberScanDateBundleV526' in app
    assert 'function invalidateScanDateBundleV526' in app
    assert 'invalidateScanDateBundleV526(date)' in app
    assert 'cachedV526: true' in app
    assert 'def line_flags_many' in operations
    date_route = server[server.index('if parsed.path == "/api/scan/date"'):server.index('if parsed.path == "/api/stations"')]
    assert 'OPERATIONS.line_flags_many' in date_route
    assert 'OPERATIONS.line_flags(' not in date_route

    # Automatic Scan/prewarm fabrication retries cannot refill the queue faster
    # than ten minutes, and one date cannot run overlapping warm jobs.
    assert 'FABRICATION_AUTO_RETRY_MS_V526 = 10 * 60 * 1000' in app
    hydrate = app[app.index('async function hydrateFabricationStatusesV474'):app.index('async function hydrateFabricationFilterCatalogV512')]
    assert 'context === "scan" || context === "prewarm"' in hydrate
    assert 'progressCheck.at' in hydrate
    assert 'minimumRetrySecondsV526' in hydrate
    warm = app[app.index('async function warmFabricationDeliveryV521'):app.index('function monitorPendingProductionProgressV522')]
    assert 'state.fabricationWarmByDateV526.get(date)' in warm
    assert 'state.fabricationWarmByDateV526.set(date, run)' in warm
    monitor = app[app.index('function monitorPendingProductionProgressV522'):app.index('async function runGlobalSearch')]
    assert 'FABRICATION_AUTO_RETRY_MS_V526' in monitor

    # Shared cancel and printer controls are visual components, not per-dialog
    # copies. Order Details uses the shared printer and one ordered header row.
    assert 'body button.app-cancel-button' in shared
    assert 'body button.icon-print-btn' in shared
    assert 'class="icon-print-btn production-sketch-print-v521"' in app
    assert 'class="icon-print-btn production-label-print-v521"' in app
    assert 'production-explorer-header-meta-row-v526' in app
    detail = app[app.index('function renderOrderDetailV470'):app.index('function orderDetailProductionNeedsSketchRetryV515')]
    assert detail.index('is-job') < detail.index('is-customer') < detail.index('is-route')
    assert 'productionExplorerDeliveryDateV518' in app
    assert 'production-explorer-header-fact-v526.is-delivery' in shared

    # Pending fabrication and machine filters are driven by the configured
    # machine color. The filters use dots/tints, not legacy left-side rails.
    assert '--machine-progress-color' in app
    assert 'progressStepColorV480(step)' in app
    assert '.is-fabrication-pending-v477.is-fabrication-pending-v480' in shared
    assert 'width: 10px !important' in scan and 'align-self: center !important' in scan
    v526_scan = scan[scan.rindex('/* v0.526 machine filter polish'):] if '/* v0.526 machine filter polish' in scan else scan
    assert 'align-self: stretch' not in v526_scan
    assert '.is-machine-choice-v521::before' in print_css
    v526_print = print_css[print_css.rindex('/* v0.526 machine filter polish'):] if '/* v0.526 machine filter polish' in print_css else print_css
    assert 'inset 3px 0 0' not in v526_print


def test_v527_stable_production_checks_aw_review_and_navigation_contracts() -> None:
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    store = (ROOT / "backend" / "store.py").read_text(encoding="utf-8")
    production = (ROOT / "backend" / "production_files.py").read_text(encoding="utf-8")
    automation = (ROOT / "backend" / "automation_control.py").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    styles_css = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
    scan_css = (ROOT / "static" / "css" / "scan.css").read_text(encoding="utf-8")
    shared_css = (ROOT / "static" / "css" / "shared-ui.css").read_text(encoding="utf-8")
    print_css = (ROOT / "static" / "css" / "print.css").read_text(encoding="utf-8")
    inventory_css = (ROOT / "static" / "css" / "inventory.css").read_text(encoding="utf-8")
    statistics_css = (ROOT / "static" / "css" / "statistics.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    contract = (ROOT / "database" / "contract.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")

    assert 'APPLICATION_VERSION = "527"' in contract
    assert 'CURRENT_SCHEMA_VERSION = 20' in contract
    assert 'Current maintained release: **v0.527**' in readme
    assert changelog.startswith('## v0.527 - Stable Production Checks, A+W Review Flags, and Faster Navigation')
    for asset in (
        'static/css/styles.css?v=20260910-v0.527',
        'static/css/scan.css?v=20260910-v0.527',
        'static/css/shared-ui.css?v=20260910-v0.527',
        'static/js/app.js?v=20260910-v0.527',
    ):
        assert asset in html

    assert 'scanDatePrefetchV527: new Map()' in app
    assert 'const requestedChunkV527 = chunk.filter' in app
    assert 'if (scanPublishedV527) repaint();' in app
    assert 'function cuttingIrregularityV527' in app
    assert 'Optimization created' in app
    assert 'Batch created' not in app
    assert 'def aw_cutting_irregularities' in store
    assert 'cut_without_batch_or_optimization' in store
    assert 'cut_in_batch_without_optimization' in store
    assert 'with asset.path.open("rb") as source:' in production

    # Empty automation snapshots cannot erase the live delivery catalog while
    # manual or automatic A+W import work is running.
    assert '"lists": []' not in automation
    assert '(detail.lists.length > 0 || !(state.lists || []).length)' in app

    # Inventory completion and Manual Edit progression use bounded backend
    # workflows and expose one whole-list editor rather than stage selectors.
    assert '/api/inventory/system-complete' in server
    assert 'def complete_inventory_system_orders' in store
    assert '/api/admin/delivery-progress' in server
    assert 'def advance_delivery_progress' in store
    assert 'admin-delivery-whole-list-v527' in app
    assert 'admin-delivery-stage-row' not in app[app.index('function adminDeliveryListDateGroupHtml'):app.index('function adminDeliveryListWeekLabel')]
    assert 'id="manualEditModalStage" type="hidden"' in app
    assert 'data-manual-progress-item-v527' in app
    assert 'data-manual-progress-order-v527' in app
    assert 'data-manual-progress-list-v527' in app
    assert 'inventory-system-complete-v527' in inventory_css

    # The A+W SHEETCOUNT metric is wired into the chart dataset and its settings
    # dialog stays above the shared modal backdrop.
    dataset = app[app.index('function statisticsChartDataset'):app.index('function statisticsChartSelectionHtml')]
    inventory_complete = app[app.index('async function completeInventorySystemOrdersV527'):app.index('async function refreshInventoryPageV524')]
    assert 'if (metric === "sheet-usage")' in dataset
    assert 'if (metric === "sheet-usage")' not in inventory_complete
    assert '/api/reports/sheet-usage-settings' in server
    assert 'def get_sheet_usage_settings' in store
    assert 'optimizationSheetCount' in store
    assert 'value="sheet-usage">Stock sheets used' in html
    assert 'z-index:10091' in statistics_css

    # Production matching recognizes sketch REMAKE evidence and normalized
    # punctuation/spacing while shared controls retain their polished states.
    assert 'sketchRemake' in production
    assert 'def _matches_machine_terms' in production
    assert 'normalized_compact = re.sub(r"[^A-Z0-9]+", "", normalized)' in production
    assert 'is-hover-suppressed-v527' in app and 'is-hover-suppressed-v527' in styles_css
    assert 'grid-auto-rows: max-content !important;' in shared_css
    assert 'is-machine-choice-v521:has(input:checked)' in print_css
    assert 'background: linear-gradient' in scan_css[scan_css.rindex('v0.527'):]
    assert 'actionV527: "all-scans"' in app
    assert 'actionV527: "order-details"' in app
