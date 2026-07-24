"""Static regression checks for the v132 floor folder-import installer."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP_BAT = ROOT / "Setup-Floor-Folder-Import-Automation.bat"
SETUP_PS1 = ROOT / "Setup-Floor-Folder-Import-Automation.ps1"
TASK_INSTALLER = ROOT / "automation" / "sql_delivery_export" / "Install-DeliveryListSqlAutomationTasks.ps1"
README = ROOT / "README.md"
CHANGELOG = ROOT / "README_CHANGELOG.md"
INDEX = ROOT / "index.html"
DOC = ROOT / "docs" / "FLOOR_FOLDER_IMPORT_AUTOMATION.md"


class FloorFolderImportSetupTests(unittest.TestCase):
    def test_release_files_exist(self) -> None:
        for path in (SETUP_BAT, SETUP_PS1, TASK_INSTALLER, README, CHANGELOG, INDEX, DOC):
            self.assertTrue(path.is_file(), path)

    def test_setup_forces_floor_mode_and_hourly_interval(self) -> None:
        text = SETUP_PS1.read_text(encoding="utf-8")
        self.assertIn('Set-JsonProperty -Object $config.Automation -Name "Mode" -Value "folder-import-only"', text)
        self.assertIn('[ValidateRange(5, 1440)][int]$IntervalMinutes = 60', text)
        self.assertIn('Set-JsonProperty -Object $config.Schedule -Name "IncrementalIntervalMinutes" -Value $IntervalMinutes', text)
        self.assertIn('Set-JsonProperty -Object $config.Import -Name "DisableBuiltInDailyImporter" -Value $true', text)
        self.assertIn('[Environment]::SetEnvironmentVariable("DLS_DAILY_IMPORT_ENABLED", "0", "User")', text)

    def test_setup_installs_missing_runtime_before_task_creation(self) -> None:
        text = SETUP_PS1.read_text(encoding="utf-8")
        self.assertIn('"Install-DeliveryListSqlAutomationTasks.ps1"', text)
        self.assertIn('Copy-Item -Destination $scriptRoot -Force', text)
        self.assertIn('$installer = Join-Path $scriptRoot "Install-DeliveryListSqlAutomationTasks.ps1"', text)
        self.assertLess(text.index('Copy-Item -Destination $scriptRoot -Force'), text.index('$installer = Join-Path $scriptRoot'))

    def test_floor_tasks_explicitly_run_folder_import_only(self) -> None:
        text = SETUP_PS1.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count('-RunAction FolderImportOnly'), 3)
        self.assertIn('"Run-Incremental.cmd"', text)
        self.assertIn('"Run-Full.cmd"', text)
        self.assertIn('"Run-Now.cmd"', text)

    def test_floor_preflight_does_not_query_sql_or_require_write_access(self) -> None:
        text = TASK_INSTALLER.read_text(encoding="utf-8")
        floor_block = text.split('if ($automationMode -eq "folder-import-only") {', 1)[1].split('\nelse {', 1)[0]
        self.assertIn('Get-ChildItem -LiteralPath $destinationFolder -File', floor_block)
        self.assertIn('validate_scanner_compatibility.py', floor_block)
        self.assertNotIn('RuntimeTest', floor_block)
        self.assertNotIn('Test-DestinationWriteAccess', floor_block)
        self.assertNotIn('SQLAWGLASS', floor_block)

    def test_central_preflight_remains_available(self) -> None:
        text = TASK_INSTALLER.read_text(encoding="utf-8")
        self.assertIn('-Mode RuntimeTest', text)
        self.assertIn('-RunAction Configured', text)
        self.assertIn('Running the SQL, workbook, destination, and scanner compatibility preflight', text)

    def test_batch_launcher_keeps_errors_visible(self) -> None:
        text = SETUP_BAT.read_text(encoding="utf-8")
        self.assertIn('powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass', text)
        self.assertIn('pause', text.lower())
        self.assertIn('exit /b %EXIT_CODE%', text)
        self.assertNotIn('set /p', text.lower())

    def test_backups_and_database_preservation_are_documented(self) -> None:
        setup = SETUP_PS1.read_text(encoding="utf-8")
        doc = DOC.read_text(encoding="utf-8")
        self.assertRegex(setup, r'Backups\\v\d+-floor-folder-import-')
        self.assertIn('The scanner database is not copied, replaced, or reset', doc)

    def test_v132_release_history_remains_documented(self) -> None:
        readme = README.read_text(encoding="utf-8")
        changelog = CHANGELOG.read_text(encoding="utf-8")
        self.assertIn('v132 adds a dedicated one-click floor-computer setup', readme)
        self.assertIn('## v132 - Floor Computer Hourly Folder-Import Setup', changelog)

    def test_setup_has_balanced_basic_delimiters(self) -> None:
        text = SETUP_PS1.read_text(encoding="utf-8")
        # Remove quoted strings and comments before a lightweight delimiter check.
        stripped = re.sub(r'(?m)#.*$', '', text)
        stripped = re.sub(r'"(?:`.|[^"`])*"', '""', stripped)
        self.assertEqual(stripped.count('{'), stripped.count('}'))
        self.assertEqual(stripped.count('('), stripped.count(')'))


if __name__ == "__main__":
    unittest.main()
