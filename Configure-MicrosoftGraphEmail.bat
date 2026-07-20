@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0Configure-MicrosoftGraphEmail.ps1' -ErrorAction SilentlyContinue; & '%~dp0Configure-MicrosoftGraphEmail.ps1'"
if errorlevel 1 (
    echo.
    echo Microsoft Graph email setup did not complete.
    pause
    exit /b 1
)
echo.
pause
