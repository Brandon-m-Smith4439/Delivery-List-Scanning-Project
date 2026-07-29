@echo off
rem File: automation/sql_delivery_export/Remove-DeliveryListSqlAutomationTasks.bat
setlocal
set "SCRIPT_DIR=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Remove-DeliveryListSqlAutomationTasks.ps1"
echo.
pause
