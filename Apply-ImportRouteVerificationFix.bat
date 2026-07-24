@echo off
setlocal DisableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
set "PATCH_SCRIPT=%SCRIPT_DIR%Apply-ImportRouteVerificationFix.ps1"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%PATCH_SCRIPT%" goto missing

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%PATCH_SCRIPT%"
set "EXIT_CODE=%errorlevel%"
goto result

:missing
echo Patch script was not found:
echo %PATCH_SCRIPT%
set "EXIT_CODE=1"

:result
echo.
if "%EXIT_CODE%"=="0" echo Patch completed successfully.
if not "%EXIT_CODE%"=="0" echo Patch failed. Read the message above before closing this window.
pause
exit /b %EXIT_CODE%

