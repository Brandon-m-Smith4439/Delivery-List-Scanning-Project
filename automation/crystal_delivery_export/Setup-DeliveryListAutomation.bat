@echo off
rem File: automation/crystal_delivery_export/Setup-DeliveryListAutomation.bat
setlocal
set "SCRIPT_DIR=%~dp0"
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Initialize-DeliveryListAutomation.ps1"
if errorlevel 1 (
    echo.
    echo Setup failed. Review the message above and C:\DeliveryListAutomation\Logs.
    pause
    exit /b 1
)
pause
