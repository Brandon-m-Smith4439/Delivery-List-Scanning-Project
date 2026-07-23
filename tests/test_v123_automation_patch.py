"""Static checks for the v123 schedule fix and verification package."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOMATION = ROOT / "automation" / "sql_delivery_export"


class V123AutomationPatchTests(unittest.TestCase):
    def test_schedule_installer_delimits_variables_before_colons(self) -> None:
        script = (AUTOMATION / "Install-DeliveryListSqlAutomationTasks.ps1").read_text(encoding="utf-8")
        self.assertIn('"- ${incrementalTask}: every $interval minutes', script)
        self.assertIn('"- ${fullTask}: daily at $fullTime', script)
        self.assertNotRegex(script, r'\$incrementalTask:')
        self.assertNotRegex(script, r'\$fullTask:')

    def test_schedule_installer_runs_syntax_and_runtime_preflight(self) -> None:
        script = (AUTOMATION / "Install-DeliveryListSqlAutomationTasks.ps1").read_text(encoding="utf-8")
        self.assertIn("System.Management.Automation.Language.Parser", script)
        self.assertIn("-Mode RuntimeTest", script)
        self.assertIn("PowerShell syntax check passed", script)
        self.assertIn("Invoke-ScheduledTasksCommand", script)
        self.assertIn('@("/Query", "/TN", $taskName)', script)

    def test_end_to_end_verifier_requires_all_pipeline_stages(self) -> None:
        script = (AUTOMATION / "Verify-DeliveryListSqlAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("-RunAction SqlExportAndImport", script)
        self.assertIn("-RunAction SqlExportOnly", script)
        self.assertIn("-Mode RuntimeTest", script)
        self.assertIn("-Mode Test", script)
        for collection in ("checkedDates", "sourceDates", "publishedDates", "importedDates"):
            self.assertIn(collection, script)
        self.assertIn("last-run.json", script)
        self.assertIn("Known-date comparison differs", script)
        self.assertIn("Known-date count comparison passed", script)
        self.assertIn("forceImportDates = @($dateKey)", script)
        self.assertIn("import_delivery_folder.py", script)
        self.assertIn("classification -eq \"failed\"", script)
        self.assertIn("verify_delivery_import.py", script)

    def test_python_verifier_reuses_maintained_store_and_stage_builder(self) -> None:
        helper = (AUTOMATION / "verify_delivery_import.py").read_text(encoding="utf-8")
        self.assertIn("from scanner_config import load_config", helper)
        self.assertIn("build_delivery_lists", helper)
        self.assertIn("load_delivery_source_payload", helper)
        self.assertIn("create_store", helper)
        self.assertIn("missingListIds", helper)

    def test_patch_is_targeted_and_backed_up(self) -> None:
        script = (ROOT / "Apply-v123-AutomationPatch.ps1").read_text(encoding="utf-8")
        self.assertIn("Backups\\v123-automation-patch", script)
        self.assertIn("Install-DeliveryListSqlAutomationTasks.ps1", script)
        self.assertIn("Verify-DeliveryListSqlAutomation.ps1", script)
        self.assertNotIn("delivery-scanner-pilot.db", script)
        self.assertNotIn("sql-export.config.json\" -Destination", script)

    def test_admin_refresh_preserves_newest_no_change_timestamps(self) -> None:
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("function dlsAutomationMergeRecentImports", app)
        self.assertIn("unchanged\n    // automation checks may exist only in the newest run snapshot", app)
        self.assertIn("state.adminRecentImports = dlsAutomationMergeRecentImports(", app)
        self.assertIn("renderImportHistory(state.adminRecentImports)", app)

    def test_css_maintenance_note_requires_reuse(self) -> None:
        css_head = (ROOT / "styles.css").read_text(encoding="utf-8")[:5000]
        self.assertIn("Search for an existing selector, shared component, and design token", css_head)
        self.assertIn("Do not add a release-specific override", css_head)
        self.assertIn("Before each release, check for exact duplicate rules", css_head)

    def test_v123_release_history_and_features_remain_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        release_match = re.search(r"Current maintained release: \*\*v(\d+)\*\*", readme)
        self.assertIsNotNone(release_match)
        self.assertGreaterEqual(int(release_match.group(1)), 123)
        self.assertIn("## v123 - Schedule Installer Fix", changelog)
        self.assertRegex(index, r"styles\.css\?v=20260723-v\d+")
        self.assertRegex(index, r"app\.js\?v=20260723-v\d+")


if __name__ == "__main__":
    unittest.main()
