@echo off
rem File: automation/sql_delivery_export/Verify-DeliveryListSqlAutomation.bat
setlocal
set "SCRIPT_DIR=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Verify-DeliveryListSqlAutomation.ps1"
set "EXIT_CODE=%errorlevel%"
echo.
if not "%EXIT_CODE%"=="0" echo Verification failed. Read the error above and review C:\DeliveryListAutomation\Logs.
if "%EXIT_CODE%"=="0" echo Verification passed.
pause
exit /b %EXIT_CODE%
