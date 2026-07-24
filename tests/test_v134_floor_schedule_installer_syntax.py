from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "automation" / "sql_delivery_export" / "Install-DeliveryListSqlAutomationTasks.ps1"
SETUP = ROOT / "Setup-Floor-Folder-Import-Automation.ps1"


class FloorScheduleInstallerSyntaxTests(unittest.TestCase):
    def test_mode_variable_is_delimited_before_literal_colon(self) -> None:
        text = INSTALLER.read_text(encoding="utf-8-sig")
        self.assertIn('Created scheduled tasks for mode ${automationMode}:', text)
        self.assertNotIn('Created scheduled tasks for mode $automationMode:', text)

    def test_no_unsafe_plain_variable_colon_interpolation(self) -> None:
        text = INSTALLER.read_text(encoding="utf-8-sig")
        unsafe = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in re.finditer(r"\$([A-Za-z_][A-Za-z0-9_]*):", line):
                # PowerShell scope variables such as $env:WINDIR are valid.
                if match.group(1).lower() in {"env", "script", "global", "local", "private"}:
                    continue
                unsafe.append((line_number, match.group(0), line.strip()))
        self.assertEqual([], unsafe)

    def test_floor_setup_validates_installed_task_installer(self) -> None:
        text = SETUP.read_text(encoding="utf-8-sig")
        self.assertIn('(Join-Path $scriptRoot "Install-DeliveryListSqlAutomationTasks.ps1")', text)
        self.assertIn("Assert-PowerShellSyntax -Paths", text)


if __name__ == "__main__":
    unittest.main()
