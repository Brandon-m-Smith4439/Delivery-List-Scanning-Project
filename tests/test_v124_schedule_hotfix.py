"""Static checks for the v124 schedule-installer compatibility hotfix."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "automation" / "sql_delivery_export"
CRYSTAL = ROOT / "automation" / "crystal_delivery_export"


class V124ScheduleHotfixTests(unittest.TestCase):
    def test_legacy_scheduler_delimits_task_names_before_colons(self) -> None:
        script = (CRYSTAL / "Install-DeliveryListAutomationTasks.ps1").read_text(encoding="utf-8")
        self.assertIn('"- ${incrementalTask}: every $interval minutes', script)
        self.assertIn('"- ${fullTask}: daily at $fullTime', script)
        self.assertNotRegex(script, r"\$incrementalTask:")
        self.assertNotRegex(script, r"\$fullTask:")

    def test_sql_installer_validates_current_entry_points_only(self) -> None:
        script = (SQL / "Install-DeliveryListSqlAutomationTasks.ps1").read_text(encoding="utf-8")
        self.assertIn("$syntaxFileNames = @(", script)
        for name in (
            "Run-DeliveryListSqlAutomation.ps1",
            "Initialize-DeliveryListSqlAutomation.ps1",
            "Install-DeliveryListSqlAutomationTasks.ps1",
            "Remove-DeliveryListSqlAutomationTasks.ps1",
            "Show-DeliveryListSqlAutomationStatus.ps1",
            "Verify-DeliveryListSqlAutomation.ps1",
        ):
            self.assertIn(f'"{name}"', script)
        self.assertNotIn('Get-ChildItem -LiteralPath $scriptRoot -Filter "*.ps1"', script)
        self.assertIn("maintained SQL automation scripts", script)

    def test_patch_replaces_both_installed_scheduler_scripts(self) -> None:
        script = (ROOT / "Apply-v124-AutomationPatch.ps1").read_text(encoding="utf-8")
        self.assertIn("Backups\\v124-automation-patch", script)
        self.assertIn("Install-DeliveryListSqlAutomationTasks.ps1", script)
        self.assertIn("Install-DeliveryListAutomationTasks.ps1", script)
        self.assertNotIn("delivery-scanner-pilot.db", script)
        self.assertNotRegex(script, r"Copy-Item[^\n]+sql-export\.config\.json")

    def test_no_invalid_task_variable_colon_forms_remain(self) -> None:
        paths = [
            SQL / "Install-DeliveryListSqlAutomationTasks.ps1",
            CRYSTAL / "Install-DeliveryListAutomationTasks.ps1",
        ]
        invalid = re.compile(r"\$(?:incrementalTask|fullTask):")
        for path in paths:
            self.assertIsNone(invalid.search(path.read_text(encoding="utf-8")), path)

    def test_v124_compatibility_fix_remains_documented(self) -> None:
        changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## v124 - Legacy Scheduler Parser Hotfix", changelog)


if __name__ == "__main__":
    unittest.main()
