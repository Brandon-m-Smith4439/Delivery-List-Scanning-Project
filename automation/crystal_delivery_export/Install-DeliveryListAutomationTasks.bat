@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Install-DeliveryListAutomationTasks.ps1"
if errorlevel 1 (
    echo.
    echo Task installation failed.
    pause
    exit /b 1
)
pause
