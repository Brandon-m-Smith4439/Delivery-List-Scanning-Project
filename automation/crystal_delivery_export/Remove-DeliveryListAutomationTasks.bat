@echo off
rem File: automation/crystal_delivery_export/Remove-DeliveryListAutomationTasks.bat
setlocal
set "SCRIPT_DIR=%~dp0"
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Remove-DeliveryListAutomationTasks.ps1"
pause
