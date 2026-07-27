"""Regression checks for v133 Windows launchers and release markers."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLOOR_BAT = ROOT / "Setup-Floor-Folder-Import-Automation.bat"
FLOOR_PS1 = ROOT / "Setup-Floor-Folder-Import-Automation.ps1"
SHORTCUT_BAT = ROOT / "Create Desktop Shortcut.bat"
README = ROOT / "README.md"
CHANGELOG = ROOT / "README_CHANGELOG.md"
INDEX = ROOT / "index.html"
DOC = ROOT / "docs" / "FLOOR_FOLDER_IMPORT_AUTOMATION.md"


class SafeBatchLauncherTests(unittest.TestCase):
    def test_changed_release_files_exist(self) -> None:
        for path in (FLOOR_BAT, FLOOR_PS1, SHORTCUT_BAT, README, CHANGELOG, INDEX, DOC):
            self.assertTrue(path.is_file(), path)

    def test_launchers_do_not_use_parenthesized_cmd_blocks(self) -> None:
        """Project paths containing ``(5)`` must never be expanded inside CMD blocks."""
        block_pattern = re.compile(r"(?im)^\s*(?:if|for)\b[^\r\n]*\(\s*$|^\s*\)\s*else\s*\(\s*$")
        for path in (FLOOR_BAT, SHORTCUT_BAT):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(block_pattern.search(text), path)
            self.assertNotIn("setlocal EnableDelayedExpansion", text)
            self.assertIn("setlocal DisableDelayedExpansion", text)

    def test_floor_launcher_uses_quoted_paths_labels_and_visible_finish(self) -> None:
        text = FLOOR_BAT.read_text(encoding="utf-8")
        self.assertIn('set "PROJECT_ROOT=%~dp0"', text)
        self.assertIn('set "SCRIPT_PATH=%PROJECT_ROOT%\\Setup-Floor-Folder-Import-Automation.ps1"', text)
        self.assertIn('powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_PATH%" -ProjectRoot "%PROJECT_ROOT%"', text)
        self.assertIn("call :run_setup", text)
        self.assertIn(":finish", text)
        self.assertIn("pause >nul", text)
        self.assertIn("floor-folder-import-setup-launch.log", text)

    def test_shortcut_launcher_uses_quoted_paths_labels_and_visible_finish(self) -> None:
        text = SHORTCUT_BAT.read_text(encoding="utf-8")
        self.assertIn('set "SCRIPT_DIR=%~dp0"', text)
        self.assertIn('set "SHORTCUT_SCRIPT=%SCRIPT_DIR%\\Create-DeliveryScannerShortcut.ps1"', text)
        self.assertIn('powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%"', text)
        self.assertIn("call :run_shortcut_setup", text)
        self.assertIn(":finish", text)
        self.assertIn("pause >nul", text)
        self.assertIn("desktop-shortcut-launch.log", text)

    def test_parenthesized_onedrive_path_is_never_inserted_unquoted(self) -> None:
        sample = r"C:\Users\calvin.knox\OneDrive - BLDR\Desktop\Delivery-List-Scanning-Project-main (5)"
        for path in (FLOOR_BAT, SHORTCUT_BAT):
            text = path.read_text(encoding="utf-8")
            # Every command that consumes a project-derived path uses a quoted variable.
            path_variable_lines = [
                line.strip()
                for line in text.splitlines()
                if any(token in line for token in ("%PROJECT_ROOT%", "%SCRIPT_PATH%", "%SCRIPT_DIR%", "%SHORTCUT_SCRIPT%", "%LOG_DIR%", "%LOG_PATH%"))
                and not line.lstrip().lower().startswith("set ")
            ]
            for line in path_variable_lines:
                if line.lower().startswith("if defined log_path echo"):
                    continue
                for token in ("%PROJECT_ROOT%", "%SCRIPT_PATH%", "%SCRIPT_DIR%", "%SHORTCUT_SCRIPT%", "%LOG_DIR%", "%LOG_PATH%"):
                    if token in line:
                        self.assertIn(f'"{token}"', line, (sample, path, line))

    def test_powershell_setup_records_unhandled_errors(self) -> None:
        text = FLOOR_PS1.read_text(encoding="utf-8")
        self.assertIn("trap {", text)
        self.assertIn("floor-folder-import-setup-error.log", text)
        self.assertIn('Set-JsonProperty -Object $config -Name "Version" -Value "v134"', text)
        self.assertIn("v134-floor-folder-import-", text)

    def test_release_markers_are_consistent(self) -> None:
        readme = README.read_text(encoding="utf-8")
        changelog = CHANGELOG.read_text(encoding="utf-8")
        release_match = re.search(r"Current maintained release: \*\*v(\d+)\*\*", readme)
        self.assertIsNotNone(release_match)
        release = int(release_match.group(1))
        self.assertGreaterEqual(release, 134)
        self.assertTrue(changelog.startswith(f"## v{release}"))
        self.assertIn("Extract the v134 changed-files package", DOC.read_text(encoding="utf-8"))
        index = INDEX.read_text(encoding="utf-8")
        markers = re.findall(r"2026\d{4}-v(\d+)", index)
        self.assertEqual(len(markers), 6)
        self.assertEqual(set(markers), {str(release)})

    def test_batch_files_use_windows_line_endings(self) -> None:
        for path in (FLOOR_BAT, SHORTCUT_BAT):
            data = path.read_bytes()
            self.assertIn(b"\r\n", data)
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
