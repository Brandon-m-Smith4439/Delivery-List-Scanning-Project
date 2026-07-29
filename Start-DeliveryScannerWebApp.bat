@echo off
rem File: Start-DeliveryScannerWebApp.bat
setlocal

rem Remove the downloaded-file security marker from the PowerShell launcher, then run it.
rem This prevents Windows from asking Run once every time an extracted release is started.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$script = Join-Path '%~dp0' 'Start-DeliveryScannerWebApp.ps1'; Unblock-File -LiteralPath $script -ErrorAction SilentlyContinue; & $script"
set "DLS_EXIT_CODE=%ERRORLEVEL%"

if not "%DLS_EXIT_CODE%"=="0" (
    echo.
    echo Delivery List Scanner did not start successfully.
    echo Review the logs folder beside this BAT file for the exact error.
    pause
)

exit /b %DLS_EXIT_CODE%
