@echo off
rem File: automation/crystal_delivery_export/Show-DeliveryListAutomationStatus.bat
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Show-DeliveryListAutomationStatus.ps1"
pause
