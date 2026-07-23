@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Install-DeliveryListSqlAutomationTasks.ps1"
set "EXIT_CODE=%errorlevel%"
echo.
pause
exit /b %EXIT_CODE%
