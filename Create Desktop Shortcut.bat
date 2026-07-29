@echo off
rem File: Create Desktop Shortcut.bat
setlocal DisableDelayedExpansion

title Delivery List Scanner - Create Desktop Shortcut

set "SCRIPT_DIR=%~dp0"
if not defined SCRIPT_DIR goto :missing_project_root
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "SHORTCUT_SCRIPT=%SCRIPT_DIR%\scripts\windows\Create-DeliveryScannerShortcut.ps1"
set "LOG_DIR=%SCRIPT_DIR%\logs"
set "LOG_PATH=%LOG_DIR%\desktop-shortcut-launch.log"

call :run_shortcut_setup
set "EXIT_CODE=%ERRORLEVEL%"
goto :finish

:run_shortcut_setup
echo ============================================================
echo   Delivery List Scanner - Desktop Shortcut Setup
echo ============================================================
echo.

if not exist "%SHORTCUT_SCRIPT%" goto :missing_script
where powershell.exe >nul 2>&1
if errorlevel 1 goto :missing_powershell

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
>"%LOG_PATH%" echo Desktop shortcut launcher started on %DATE% at %TIME%.
>>"%LOG_PATH%" echo Project root: "%SCRIPT_DIR%"
>>"%LOG_PATH%" echo PowerShell script: "%SHORTCUT_SCRIPT%"

echo Starting desktop shortcut setup...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%"
set "SHORTCUT_EXIT_CODE=%ERRORLEVEL%"
>>"%LOG_PATH%" echo PowerShell exit code: %SHORTCUT_EXIT_CODE%
exit /b %SHORTCUT_EXIT_CODE%

:missing_script
echo ERROR: Shortcut setup script was not found.
echo Expected file: "%SHORTCUT_SCRIPT%"
echo.
echo Extract the complete update into the scanner project folder and try again.
exit /b 2

:missing_powershell
echo ERROR: Windows PowerShell could not be found on this computer.
exit /b 3

:missing_project_root
echo ERROR: The current scanner project folder could not be determined.
set "EXIT_CODE=4"
goto :finish

:finish
if not defined EXIT_CODE set "EXIT_CODE=1"
echo.
if "%EXIT_CODE%"=="0" echo Desktop shortcut creation completed successfully.
if "%EXIT_CODE%"=="0" echo You can now start the scanner from the Glass Delivery Scanner shortcut.
if not "%EXIT_CODE%"=="0" echo Desktop shortcut creation FAILED with exit code %EXIT_CODE%.
if not "%EXIT_CODE%"=="0" echo No scanner files or database data were changed.
if defined LOG_PATH echo Launcher log: "%LOG_PATH%"
echo.
echo Press any key to close this window.
pause >nul
exit /b %EXIT_CODE%
