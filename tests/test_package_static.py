"""Static safety and integration checks for the v121 SQL automation package."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION = ROOT / "automation" / "sql_delivery_export"


class PackageStaticTests(unittest.TestCase):
    """Reject missing files, write SQL, secrets, and unsafe replacement behavior."""

    def test_required_runtime_files_exist(self) -> None:
        required = {
            "Run-DeliveryListSqlAutomation.ps1",
            "Initialize-DeliveryListSqlAutomation.ps1",
            "Install-DeliveryListSqlAutomationTasks.ps1",
            "Remove-DeliveryListSqlAutomationTasks.ps1",
            "Show-DeliveryListSqlAutomationStatus.ps1",
            "Apply-v121-ProjectIntegration.ps1",
            "build_delivery_workbook.py",
            "import_delivery_folder.py",
            "publish_automation_notification.py",
            "validate_scanner_compatibility.py",
            "delivery_automation_control.py",
            "delivery-automation-ui.js",
            "delivery-automation-ui.css",
            "notification-center-ui.js",
            "notification-center-ui.css",
            "delivery_import_safety.py",
            "sql-export.config.json",
            "README.md",
            "EXPORTER_VERSION.txt",
        }
        missing = sorted(name for name in required if not (AUTOMATION / name).is_file())
        self.assertEqual(missing, [])

    def test_sql_is_read_only(self) -> None:
        script = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        sql_blocks = re.findall(r'@"\n(.*?)\n"@', script, flags=re.DOTALL)
        joined = "\n".join(sql_blocks).upper()
        for forbidden in (
            "INSERT INTO",
            "UPDATE ",
            "DELETE FROM",
            "MERGE ",
            "EXEC ",
            "EXECUTE ",
            "ALCIMRUN.ALCIMDB",
        ):
            self.assertNotIn(forbidden, joined)
        self.assertIn("SELECT", joined)
        self.assertIn("@DELIVERYDATE", joined)

    def test_configuration_uses_confirmed_profile_without_passwords(self) -> None:
        config = json.loads((AUTOMATION / "sql-export.config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["Version"], "v121")
        self.assertEqual(config["Automation"]["Mode"], "sql-export-and-import")
        self.assertEqual(config["Database"]["AuthenticationMode"], "Windows")
        serialized = json.dumps(config).lower()
        self.assertNotIn('"password"', serialized)
        self.assertEqual(config["Database"]["Server"], "SQLAWGLASS")
        self.assertEqual(config["Database"]["Database"], "BFSMAIN")
        self.assertEqual(config["SourceMapping"]["Schema"], "SYSADM")
        self.assertEqual(config["SourceMapping"]["HeaderTable"], "BW_AUFTR_KOPF")
        self.assertEqual(config["SourceMapping"]["ItemTable"], "BW_AUFTR_POS")
        self.assertEqual(config["SourceMapping"]["RemakeBitMask"], 128)
        self.assertEqual(config["SourceMapping"]["DimensionUnitsPerInch"], 32)
        self.assertTrue(config["Notifications"]["Enabled"])
        self.assertTrue(config["Import"]["DisableBuiltInDailyImporter"])

    def test_setup_does_not_package_core_application_files(self) -> None:
        packaged_files = {path.name for path in ROOT.rglob("*") if path.is_file()}
        forbidden = {
            "app.js",
            "styles.css",
            "index.html",
            "server.py",
            "delivery_store.py",
            "scanner_config.py",
            "delivery-scanner-pilot.db",
        }
        self.assertEqual(sorted(packaged_files.intersection(forbidden)), [])

    def test_integration_uses_backups_and_targeted_patches(self) -> None:
        integration = (AUTOMATION / "Apply-v121-ProjectIntegration.ps1").read_text(encoding="utf-8")
        self.assertIn("v121-project-integration", integration)
        self.assertIn('Copy-Item -LiteralPath (Join-Path $resolvedRoot $name)', integration)
        self.assertIn("delivery_store.py", integration)
        self.assertIn("def get_notification_history", integration)
        self.assertIn("def mark_all_notifications_read", integration)
        self.assertIn('/api/notifications/history', integration)
        self.assertIn('/api/notifications/read-all', integration)
        self.assertIn('/api/admin/delivery-automation/recent-imports', integration)
        self.assertIn('DELIVERY_AUTOMATION.get_import_history', integration)
        self.assertIn('page_size=int(params.get("pageSize"', integration)
        self.assertIn("DeliveryAutomationController(ROOT, CONFIG, STORE)", integration)
        self.assertIn("notification-center-ui.js", integration)
        self.assertIn("notification-center-ui.css", integration)
        self.assertIn("delivery_import_safety.py", integration)
        self.assertIn("install_safe_delivery_import(STORE)", integration)
        self.assertIn('"index.html", "app.js", "server.py", "delivery_store.py"', integration)
        self.assertIn("DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V121", integration)
        self.assertIn("state.adminRecentImports = detail.recentImports.slice()", integration)
        self.assertIn("reactivated_list_ids", integration)
        self.assertIn('summary["reactivated"] = stage_reactivated', integration)
        self.assertNotIn('Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery_store.py")', integration)

    def test_control_center_is_isolated_and_accessible(self) -> None:
        gui = (AUTOMATION / "delivery-automation-ui.js").read_text(encoding="utf-8")
        css = (AUTOMATION / "delivery-automation-ui.css").read_text(encoding="utf-8")
        self.assertIn("#folderImportBtn", gui)
        self.assertIn('aria-modal", "true"', gui)
        self.assertIn("Run Manually", gui)
        self.assertIn("Automatic Schedule", gui)
        self.assertIn("Status & Logs", gui)
        self.assertIn("/recent-imports", gui)
        self.assertIn("Import Audit History", gui)
        self.assertIn("New + Updated", gui)
        self.assertIn("MutationObserver", gui)
        self.assertNotIn("startRecentImportsHeartbeat", gui)
        self.assertNotIn("recentImportsHeartbeat", gui)
        self.assertIn("Import history is part of the main control center", gui)
        self.assertIn("Refresh - new results", gui)
        self.assertIn("startDeliveryCatalogHeartbeat", gui)
        self.assertIn('fetch("/api/delivery-lists"', gui)
        self.assertIn("10000", gui)
        self.assertIn('document.getElementById("adminLastUpdated")', gui)
        self.assertIn("stampLatestImportResults", gui)
        self.assertIn("stamped.importedAt = completedAt", gui)
        self.assertIn('"checkedAt": imported_at', (AUTOMATION / "delivery_automation_control.py").read_text(encoding="utf-8"))
        self.assertNotIn('return document.getElementById("adminDeliveryLists")', gui)
        self.assertIn('data-automation-tab="history"', gui)
        self.assertIn('data-automation-panel="history"', gui)
        self.assertNotIn('#importHistoryBtn', gui)
        self.assertNotIn('import-history-backdrop', gui)
        self.assertNotIn('import-history-modal', gui)
        self.assertIn("stageSummaries", gui)
        self.assertIn("Entirely new stage", gui)
        self.assertIn("Restored after deletion", gui)
        self.assertIn("delivery-automation-modal", css)
        self.assertIn("automation-recent-import-row", css)
        self.assertNotIn(".modal-panel {", css)
        self.assertIn("@media (max-width: 650px)", css)

    def test_notification_center_excludes_scans_and_signals_automation_updates(self) -> None:
        gui = (AUTOMATION / "notification-center-ui.js").read_text(encoding="utf-8")
        css = (AUTOMATION / "notification-center-ui.css").read_text(encoding="utf-8")
        self.assertIn("/api/notifications/history", gui)
        self.assertIn("/api/notifications/read-all", gui)
        self.assertIn("notification-center-bell", css)
        self.assertIn("tool-button header-utility-button notification-center-button", gui)
        self.assertNotIn("background: rgba(255, 255, 255, 0.72)", css)
        self.assertIn("Scan feedback and Rush alerts stay in their own workflows", gui)
        self.assertIn("dls:delivery-list-import-history-changed", gui)
        self.assertIn("sql-delivery-automation", gui)
        self.assertNotIn("/api/scans", gui)
        self.assertNotIn("scan_events", gui)

    def test_v121_uses_centered_toast_auto_read_and_reliable_review(self) -> None:
        gui = (AUTOMATION / "notification-center-ui.js").read_text(encoding="utf-8")
        css = (AUTOMATION / "notification-center-ui.css").read_text(encoding="utf-8")
        automation_gui = (AUTOMATION / "delivery-automation-ui.js").read_text(encoding="utf-8")
        helper = (AUTOMATION / "delivery_import_safety.py").read_text(encoding="utf-8")
        integration = (AUTOMATION / "Apply-v121-ProjectIntegration.ps1").read_text(encoding="utf-8")
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("automation-update-toast", gui)
        self.assertIn("automation-update-toast", css)
        self.assertIn("window.setTimeout(dismissToast, 20000)", gui)
        self.assertIn("left: 50%", css)
        self.assertIn("translate(-50%, 0)", css)
        self.assertIn("refresh({ markReadAfterRefresh: true })", gui)
        self.assertIn("markAllReadOnOpen", gui)
        self.assertNotIn("notification-center-mark-all", gui)
        self.assertNotIn("notification-center-mark-all", css)
        self.assertNotIn("Mark all read", gui)
        self.assertIn("dls:open-delivery-list-management-import", gui)
        self.assertIn("openDeliveryListManagementFromNotification", automation_gui)
        self.assertIn("user-line-update-banner", gui)
        self.assertIn("Mark reviewed", gui)
        self.assertIn("pendingUpdateIdsByList", gui)
        self.assertIn("JSON.stringify({ listId, noticeIds })", gui)
        self.assertIn("clearReviewedLabelsFromActiveState", gui)
        self.assertIn("/api/delivery-lists/${encodeURIComponent(listId)}?reviewed=", gui)
        self.assertIn("/api/delivery-list-updates", gui)
        self.assertIn("line_update_notices", integration)
        self.assertIn("_migration_003_v120_user_line_updates", integration)
        self.assertIn("acknowledge_user_line_updates", helper)
        self.assertIn("_pending_notifications_without_automation", helper)
        self.assertIn("LIMIT 250", helper)
        self.assertIn("Removed from latest import", helper)
        self.assertNotIn('(?:New|Updated|Removed) Line', helper)
        self.assertIn('displayMode = "toast"', runner)
        self.assertIn('target = "delivery-list-management"', runner)
        self.assertIn("function Get-AffectedImportListIds", runner)

    def test_controller_keeps_allowlisted_actions_and_import_history(self) -> None:
        controller = (AUTOMATION / "delivery_automation_control.py").read_text(encoding="utf-8")
        self.assertIn("RUN_ACTIONS", controller)
        self.assertNotIn("shell=True", controller)
        self.assertIn('config["Version"] = "v121"', controller)
        self.assertIn("def get_recent_imports", controller)
        self.assertIn('FROM imports ORDER BY id DESC', controller)
        self.assertIn("**runtime_summary", controller)

    def test_runner_reuses_existing_app_notification_api(self) -> None:
        script = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        publisher = (AUTOMATION / "publish_automation_notification.py").read_text(encoding="utf-8")
        self.assertIn("publish_automation_notification.py", script)
        self.assertIn("create_app_notification", publisher)
        self.assertNotIn("CREATE TABLE", publisher.upper())
        self.assertIn("NotifyOnNoChanges", script)
        self.assertIn("importResults = @($script:ImportResults)", script)

    def test_runner_uses_real_import_result_dates(self) -> None:
        script = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn('"--result-path", $resultPath', script)
        self.assertIn("$result.importedDates", script)
        self.assertIn("$result.failedDates", script)
        self.assertIn("$dateKey -notin $successfulDateKeys", script)
        self.assertIn("$remainingPending", script)
        self.assertIn("Scanner check completed: {0} new, {1} updated, {2} unchanged, {3} failed", script)
        self.assertIn("Failed workbook {0} ({1}): {2}", script)
        self.assertIn("last-import-result.json", script)
        self.assertIn("Repair guidance", script)
        self.assertIn("Automation run completed with warnings", script)

    def test_import_wrapper_consumes_maintained_result_collections(self) -> None:
        helper = (AUTOMATION / "import_delivery_folder.py").read_text(encoding="utf-8")
        for name in ("importedFiles", "updatedFiles", "skippedFiles", "failedFiles"):
            self.assertIn(name, helper)
        self.assertIn("classificationLabel", helper)
        self.assertIn("changedDates", helper)
        self.assertIn("from delivery_import_safety import install_safe_delivery_import", helper)
        self.assertIn("install_safe_delivery_import(store)", helper)
        self.assertIn("failedDates", helper)
        self.assertIn("--sync-request-path", helper)
        self.assertIn("selective_sql_sync", helper)
        self.assertIn('"stageSummaries"', helper)
        self.assertIn('"reactivatedListIds"', helper)
        self.assertIn("run_with_database_retry", helper)
        self.assertIn("Scanner database is busy", helper)
        self.assertIn("failed_details", helper)
        self.assertIn("\"failedFiles\": failed_details", helper)

    def test_runner_supports_folder_only_and_sql_actions(self) -> None:
        script = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("FolderImportOnly", script)
        self.assertIn("SqlExportOnly", script)
        self.assertIn("SqlExportAndImport", script)
        self.assertIn('ValidateSet("RuntimeTest", "Test", "Incremental", "Full", "Custom", "FolderImport")', script)
        self.assertIn("Configured automation mode is disabled", script)

    def test_powershell_date_parser_uses_string_array_overload(self) -> None:
        script = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn('$formats = [string[]]@(', script)

    def test_notification_payload_has_one_checked_dates_key(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        payload_start = runner.index("$payload = [ordered]@{")
        payload_end = runner.index("$request = [ordered]@{", payload_start)
        payload_block = runner[payload_start:payload_end]
        self.assertEqual(payload_block.count("checkedDates ="), 1)
        summary_start = runner.index("$summary = [ordered]@{")
        summary_end = runner.index("$path = Join-Path", summary_start)
        summary_block = runner[summary_start:summary_end]
        self.assertEqual(summary_block.count("runAction ="), 1)
        self.assertIn("$affectedListIds = @(Get-AffectedImportListIds", runner[summary_start - 150:summary_end])

    def test_network_share_publish_avoids_file_replace_on_unc_paths(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn(r'$isUncPath = $DestinationPath.StartsWith("\\")', runner)
        self.assertIn("network-share compatible path", runner)
        self.assertIn("Copy-Item -LiteralPath $partial -Destination $DestinationPath -Force", runner)

    def test_status_page_exposes_complete_live_log(self) -> None:
        controller = (AUTOMATION / "delivery_automation_control.py").read_text(encoding="utf-8")
        gui = (AUTOMATION / "delivery-automation-ui.js").read_text(encoding="utf-8")
        self.assertIn("Stream every runner line", controller)
        self.assertIn(r'"commandOutput": "\n".join(output_lines)', controller)
        self.assertNotIn("splitlines()[-40:]", controller)
        self.assertIn("Live command log", gui)
        self.assertIn("Copy Full Log", gui)
        self.assertIn("Follow newest activity", gui)
        self.assertIn("last.commandOutput", gui)

    def test_notification_publisher_uses_request_file(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        publisher = (AUTOMATION / "publish_automation_notification.py").read_text(encoding="utf-8")
        self.assertIn('"--request-file", $requestPath', runner)
        self.assertIn('parser.add_argument("--request-file"', publisher)
        self.assertIn("read_request", publisher)

    def test_setup_unblocks_and_runs_v121_integration(self) -> None:
        setup_bat = (AUTOMATION / "Setup-DeliveryListSqlAutomation.bat").read_text(encoding="utf-8")
        initialize = (AUTOMATION / "Initialize-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("Unblock-File", setup_bat)
        self.assertIn("Unblock-File", initialize)
        self.assertIn("Apply-v121-ProjectIntegration.ps1", initialize)
        self.assertIn("-gt 121", initialize)
        self.assertIn("currentScheduleEnabled", initialize)

    def test_powershell_here_string_terminators_are_standalone(self) -> None:
        for path in AUTOMATION.glob("*.ps1"):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.startswith('"@') or line.startswith("'@"):
                    self.assertIn(line, {'"@', "'@"}, f"Invalid here-string terminator in {path.name}:{line_number}")

    def test_powershell_scripts_remain_ascii_safe(self) -> None:
        for path in AUTOMATION.glob("*.ps1"):
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.isascii(), f"Non-ASCII character found in {path.name}")


class V121ImportCompletionRegressionTests(unittest.TestCase):
    """Prevent large importer summaries from making live logs appear frozen."""

    def test_importer_stdout_is_concise_and_full_result_stays_in_result_file(self) -> None:
        helper = (AUTOMATION / "import_delivery_folder.py").read_text(encoding="utf-8")
        self.assertIn("console_summary = {", helper)
        self.assertIn('write_result(args.result_path, summary)', helper)
        self.assertIn('print(json.dumps(console_summary', helper)
        self.assertNotIn('print(json.dumps(summary, indent=2', helper)
        console_block = helper[helper.index("console_summary = {"):helper.index("return 0 if summary", helper.index("console_summary = {"))]
        self.assertNotIn('"files"', console_block)

    def test_live_status_persistence_is_throttled(self) -> None:
        controller = (AUTOMATION / "delivery_automation_control.py").read_text(encoding="utf-8")
        self.assertIn("import time", controller)
        self.assertIn("time.monotonic()", controller)
        self.assertIn("lines_since_persist >= 20", controller)
        self.assertIn("now - last_persisted_at >= 0.5", controller)

    def test_runner_logs_import_result_transition_and_suppresses_pipeline_output(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("[void](Invoke-ConfiguredPython -Config $Config -Arguments @(", runner)
        self.assertIn("Scanner import verification returned. Reading the normalized result summary.", runner)


class V121NoChangeRunRegressionTests(unittest.TestCase):
    """Keep unchanged SQL checks visible without repeatedly reimporting them."""

    def test_scanner_import_accepts_empty_date_collection(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("[AllowEmptyCollection()][datetime[]]$Dates = @()", runner)
        self.assertIn("$null -eq $Dates -or $Dates.Count -eq 0", runner)

    def test_sql_import_action_verifies_all_source_dates(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("$sourceDates = @($script:SourceDates | Sort-Object -Unique)", runner)
        self.assertIn("-SelectiveSqlSync $true", runner)
        self.assertIn("forceImportDates", runner)

    def test_unchanged_dates_are_not_forced_through_import(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("if (-not $stateImported)", runner)
        self.assertNotIn('$script:ResolvedAction -eq "SqlExportAndImport" -or -not $stateImported', runner)
        helper = (AUTOMATION / "import_delivery_folder.py").read_text(encoding="utf-8")
        self.assertIn("unchanged workbooks are reported without reimporting", helper)
        self.assertIn("must_import = delivery_date in force_import_dates or bool(missing_before)", helper)


class V121WorkbookIntegrityRegressionTests(unittest.TestCase):
    """Prevent Excel repair prompts and stale corrupt workbooks."""

    def test_builder_enforces_excel_schema_order_and_complete_xml_validation(self) -> None:
        builder = (AUTOMATION / "build_delivery_workbook.py").read_text(encoding="utf-8")
        self.assertIn("def validate_worksheet_order", builder)
        self.assertIn("Worksheet element", builder)
        self.assertIn("archive.testzip()", builder)
        self.assertIn("validate_style_counts", builder)
        worksheet_start = builder.index('<worksheet xmlns="{MAIN_NS}"')
        worksheet_end = builder.index("</worksheet>", worksheet_start)
        worksheet_block = builder[worksheet_start:worksheet_end]
        self.assertLess(worksheet_block.index("<sheetPr>"), worksheet_block.index("<dimension"))

    def test_runner_records_and_checks_published_workbook_hash(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("workbookFormatVersion = \"v115-ooxml-1\"", runner)
        self.assertIn("workbookHash = $WorkbookHash", runner)
        self.assertIn("Get-FileHash -LiteralPath $destinationPath", runner)
        self.assertIn("Existing workbook is missing the v115 integrity marker", runner)


class V121DeletedListRecoveryTests(unittest.TestCase):
    """Ensure unchanged workbooks can recreate scanner lists deleted by an admin."""

    def test_import_wrapper_uses_maintained_folder_import_for_missing_stage_lists(self) -> None:
        helper = (AUTOMATION / "import_delivery_folder.py").read_text(encoding="utf-8")
        self.assertIn("def selective_sql_sync", helper)
        self.assertIn("missing_before = expected_ids.difference(existing_ids)", helper)
        self.assertIn("store.import_delivery_folder", helper)
        self.assertIn("Recovered missing scanner stage list", helper)
        self.assertNotIn("DELETE FROM IMPORTS", helper.upper())
        self.assertNotIn("DELETE FROM DELIVERY_LISTS", helper.upper())


class V121AdminHistoryAndLiveRefreshTests(unittest.TestCase):
    """Keep the existing Admin import section and scan selectors current without reload."""

    def test_import_history_is_integrated_into_the_control_center(self) -> None:
        gui = (AUTOMATION / "delivery-automation-ui.js").read_text(encoding="utf-8")
        css = (AUTOMATION / "delivery-automation-ui.css").read_text(encoding="utf-8")
        integration = (AUTOMATION / "Apply-v121-ProjectIntegration.ps1").read_text(encoding="utf-8")
        heading_block = integration.split("$deliveryManagementHeading = @'", 1)[1].split("'@", 1)[0]
        self.assertNotIn('<button class="link-button" id="importHistoryBtn" type="button">Import history</button>', heading_block)
        self.assertIn('data-automation-tab="history"', gui)
        self.assertIn('data-automation-panel="history"', gui)
        self.assertIn('class="delivery-automation-tab import-history-workspace"', gui)
        self.assertNotIn('importHistoryModal.className = "import-history-modal"', gui)
        self.assertNotIn('import-history-backdrop', gui)
        self.assertIn('id="importHistorySearch"', gui)
        self.assertIn('id="importHistoryStatusFilter"', gui)
        self.assertIn('id="importHistoryPageSize"', gui)
        self.assertIn('<option value="20">20</option>', gui)
        self.assertIn('<option value="50">50</option>', gui)
        self.assertIn('<option value="100">100</option>', gui)
        self.assertIn('data-history-page', gui)
        self.assertIn('import-history-workspace', css)
        self.assertNotIn('return document.getElementById("adminDeliveryLists")', gui)
        self.assertIn("admin-import-settings", integration)
        self.assertIn('id="importHistory"', integration)

    def test_project_bridge_refreshes_lists_and_preserves_import_result_state(self) -> None:
        integration = (AUTOMATION / "Apply-v121-ProjectIntegration.ps1").read_text(encoding="utf-8")
        self.assertIn('state.adminRecentImports = latestResults.slice()', integration)
        self.assertIn('state.lists = refreshedLists.slice()', integration)
        self.assertIn('dlsAutomationApplyDeliveryCatalog', integration)
        self.assertIn('dls:delivery-list-catalog-synced', integration)
        self.assertIn('dlsAutomationRefreshVisibleListViews', integration)
        self.assertIn('typeof renderAdmin === "function"', integration)
        self.assertIn('typeof renderAdminDeliveryLists === "function"', integration)
        self.assertIn('latestImportResults', integration)
        self.assertIn('lastCheckedAt', integration)
        self.assertIn('latest_import = DELIVERY_AUTOMATION.get_latest_import_result()', integration)
        self.assertIn('/api/admin/delivery-automation/latest-import', integration)
        self.assertNotIn('dateSelect.dispatchEvent(new Event("change"', integration.split("DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V121", 1)[1])
        self.assertNotIn('stageSelect.dispatchEvent(new Event("change"', integration.split("DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V121", 1)[1])
        self.assertIn('legacyBridgeV114', integration)
        self.assertIn('DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V(?:115|116|117|118|119|120|121)', integration)

    def test_latest_import_result_has_independent_live_refresh_path(self) -> None:
        gui = (AUTOMATION / "delivery-automation-ui.js").read_text(encoding="utf-8")
        controller = (AUTOMATION / "delivery_automation_control.py").read_text(encoding="utf-8")
        self.assertIn('api("/latest-import")', gui)
        self.assertIn('publishLatestImportResult', gui)
        self.assertIn('recentImports: results', gui)
        self.assertIn('if (adminPageIsVisible()) refreshLatestImportResult(false)', gui)
        self.assertIn('refreshLatestImportResult(true)', gui)
        self.assertIn('def get_latest_import_result', controller)
        self.assertIn('"latestImportResults": latest_items', controller)
        self.assertIn('"latestRunKey": run_key', controller)

    def test_import_history_stays_collapsed_and_does_not_auto_refresh_while_open(self) -> None:
        gui = (AUTOMATION / "delivery-automation-ui.js").read_text(encoding="utf-8")
        self.assertNotIn('const open = page === 1 && index < 2', gui)
        self.assertIn('<details class="import-history-entry automation-recent-import-row ${status.className}">', gui)
        self.assertNotIn('if (importHistoryModal && !importHistoryModal.hidden) {\n        refreshImportHistory(false);', gui)
        self.assertNotIn('window.setInterval(() => {\n      if (adminPageIsVisible()', gui)
        self.assertIn('refreshRecentImports({ refreshHistoryWindow: false })', gui)
        self.assertIn('if (name === "history")', gui)

    def test_reactivated_stages_are_classified_as_new_in_maintained_importer(self) -> None:
        integration = (AUTOMATION / "Apply-v121-ProjectIntegration.ps1").read_text(encoding="utf-8")
        self.assertIn('active_existing_list_ids', integration)
        self.assertIn('reactivated_list_ids', integration)
        self.assertIn('event_type = "import" if summary["created"] or stage_reactivated else "update"', integration)
        self.assertIn('"createdCount": sum(1 for summary in stage_summaries if summary["created"] or summary.get("reactivated"))', integration)
        self.assertIn('"reactivatedCount": result.get("reactivatedCount", 0)', integration)


    def test_append_only_scan_history_uses_non_destructive_import_reconciliation(self) -> None:
        helper = (AUTOMATION / "delivery_import_safety.py").read_text(encoding="utf-8")
        integration = (AUTOMATION / "Apply-v121-ProjectIntegration.ps1").read_text(encoding="utf-8")
        self.assertIn("def install_safe_delivery_import", helper)
        self.assertIn("safeInPlaceUpdate", helper)
        self.assertIn("Removed Line", helper)
        self.assertIn("scan_events", helper)
        self.assertIn("machine_events", helper)
        self.assertNotIn("DROP TRIGGER", helper.upper())
        self.assertNotIn("DELETE FROM scan_events", helper)
        self.assertIn("from delivery_import_safety import install_safe_delivery_import", integration)
        self.assertIn("install_safe_delivery_import(STORE)", integration)


if __name__ == "__main__":
    unittest.main()
