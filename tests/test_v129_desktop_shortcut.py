from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAT = ROOT / "Create Desktop Shortcut.bat"
PS1 = ROOT / "Create-DeliveryScannerShortcut.ps1"


def test_shortcut_files_exist() -> None:
    assert BAT.is_file()
    assert PS1.is_file()


def test_batch_launcher_is_quoted_and_keeps_results_visible() -> None:
    text = BAT.read_text(encoding="utf-8")
    assert 'set "SHORTCUT_SCRIPT=%SCRIPT_DIR%Create-DeliveryScannerShortcut.ps1"' in text
    assert 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%"' in text
    assert 'set "SHORTCUT_EXIT_CODE=%ERRORLEVEL%"' in text
    assert text.count("pause") >= 2
    assert "No scanner files or database data were changed." in text


def test_powershell_uses_maintained_launcher_only() -> None:
    text = PS1.read_text(encoding="utf-8")
    assert 'Join-Path $projectRoot "Start-DeliveryScannerWebApp.bat"' in text
    assert "Start Delivery Scanner Web App.bat" not in text
    assert "publish\\Delivery List Scanner.exe" not in text


def test_powershell_handles_redirected_desktop_and_sensitive_paths() -> None:
    text = PS1.read_text(encoding="utf-8")
    assert '$Shell.SpecialFolders.Item("Desktop")' in text
    assert "DesktopDirectory" in text
    assert "$env:USERPROFILE" in text
    assert "$env:ComSpec" in text
    assert "'/d /c \"\"{0}\"\"' -f $launcherPath" in text
    assert "$shortcut.WorkingDirectory = $projectRoot" in text


def test_powershell_verifies_created_shortcut() -> None:
    text = PS1.read_text(encoding="utf-8")
    assert "$shortcut.Save()" in text
    assert "$verified = $shell.CreateShortcut($shortcutPath)" in text
    assert "unexpected program" in text
    assert "expected scanner launcher command" in text
    assert "unexpected working directory" in text
    assert "exit 1" in text


def test_release_metadata_advanced() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "README_CHANGELOG.md").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Current maintained release: **v129**" in readme
    assert changelog.startswith("## v129 - Reliable Desktop Shortcut Creation")
    assert "20260724-v129" in index
    assert "20260724-v128" not in index
