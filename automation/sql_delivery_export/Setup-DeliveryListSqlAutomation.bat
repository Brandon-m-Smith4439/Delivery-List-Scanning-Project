@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

rem Files extracted from a downloaded ZIP may carry the Internet security marker.
rem Remove that marker from this trusted package before running any setup scripts.
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%SCRIPT_DIR%' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Initialize-DeliveryListSqlAutomation.ps1" -SkipProjectDocumentation
set "EXIT_CODE=%errorlevel%"
echo.
if not "%EXIT_CODE%"=="0" echo Setup failed. Read the message above before closing this window.
pause
exit /b %EXIT_CODE%
