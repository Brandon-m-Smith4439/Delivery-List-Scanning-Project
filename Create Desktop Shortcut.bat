@echo off
setlocal EnableExtensions

title Delivery List Scanner - Create Desktop Shortcut

set "SCRIPT_DIR=%~dp0"
set "SHORTCUT_SCRIPT=%SCRIPT_DIR%Create-DeliveryScannerShortcut.ps1"

echo ============================================================
echo   Delivery List Scanner - Desktop Shortcut Setup
echo ============================================================
echo.

if not exist "%SHORTCUT_SCRIPT%" (
    echo ERROR: Shortcut setup script was not found:
    echo   %SHORTCUT_SCRIPT%
    echo.
    echo Extract the complete update into the scanner project folder and try again.
    goto :failed
)

where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Windows PowerShell could not be found on this computer.
    goto :failed
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%"
set "SHORTCUT_EXIT_CODE=%ERRORLEVEL%"

if not "%SHORTCUT_EXIT_CODE%"=="0" (
    echo.
    echo Desktop shortcut creation failed with exit code %SHORTCUT_EXIT_CODE%.
    echo Review the error shown above, then run this BAT again.
    goto :failed
)

echo.
echo Desktop shortcut creation completed successfully.
echo You can now start the scanner from the Glass Delivery Scanner shortcut.
echo.
pause
exit /b 0

:failed
echo.
echo No scanner files or database data were changed.
echo.
pause
exit /b 1
