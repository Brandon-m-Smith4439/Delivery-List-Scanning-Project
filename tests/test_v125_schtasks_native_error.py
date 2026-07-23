"""Static checks for the v125 Task Scheduler native-command hotfix."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "automation" / "sql_delivery_export" / "Install-DeliveryListSqlAutomationTasks.ps1"


class V125ScheduledTasksNativeCommandTests(unittest.TestCase):
    def test_installer_uses_one_safe_native_command_wrapper(self) -> None:
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("function Invoke-ScheduledTasksCommand", script)
        self.assertIn('$ErrorActionPreference = "Continue"', script)
        self.assertIn("@(& $schtasksPath @Arguments 2>&1)", script)
        self.assertIn("ExitCode = $exitCode", script)
        self.assertIn("function Assert-ScheduledTasksCommandSucceeded", script)
        self.assertNotIn("& schtasks.exe", script)

    def test_missing_legacy_tasks_are_queried_before_delete(self) -> None:
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('$legacyQuery = Invoke-ScheduledTasksCommand -Arguments @("/Query", "/TN", $legacyTask)', script)
        self.assertIn("if ($legacyQuery.ExitCode -eq 0)", script)
        self.assertIn('$legacyDelete = Invoke-ScheduledTasksCommand -Arguments @("/Delete", "/TN", $legacyTask, "/F")', script)
        self.assertNotIn('/Delete /TN $legacyTask /F 2>$null', script)

    def test_all_scheduler_operations_use_wrapper(self) -> None:
        script = INSTALLER.read_text(encoding="utf-8")
        for variable in ("$incrementalCreate", "$fullCreate", "$taskQuery", "$incrementalRun"):
            self.assertIn(f"{variable} = Invoke-ScheduledTasksCommand", script)
        self.assertNotIn("& schtasks.exe", script)

    def test_patch_is_narrow_and_preserves_live_data(self) -> None:
        script = (ROOT / "Apply-v125-AutomationPatch.ps1").read_text(encoding="utf-8")
        self.assertIn("Backups\\v125-automation-patch", script)
        self.assertIn("Install-DeliveryListSqlAutomationTasks.ps1", script)
        self.assertNotIn("delivery-scanner-pilot.db", script)
        self.assertNotIn("sql-export.config.json\" -Destination", script)

    def test_release_and_cache_keys_are_v125(self) -> None:
        self.assertIn("Current maintained release: **v125**", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8").startswith("## v125"))
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("styles.css?v=20260723-v125", index)
        self.assertIn("app.js?v=20260723-v125", index)


if __name__ == "__main__":
    unittest.main()
