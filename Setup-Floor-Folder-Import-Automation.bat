@echo off
setlocal DisableDelayedExpansion

title Delivery List Scanner - Floor Folder Import Setup v133

set "PROJECT_ROOT=%~dp0"
if not defined PROJECT_ROOT goto :missing_project_root
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "SCRIPT_PATH=%PROJECT_ROOT%\Setup-Floor-Folder-Import-Automation.ps1"
set "LOG_DIR=%PROJECT_ROOT%\logs"
set "LOG_PATH=%LOG_DIR%\floor-folder-import-setup-launch.log"

call :run_setup
set "EXIT_CODE=%ERRORLEVEL%"
goto :finish

:run_setup
echo ================================================================
echo  Delivery List Scanner - Floor Folder Import Setup v133
echo ================================================================
echo.
echo This installs hourly imports from the Temp Delivery Lists folder.
echo This floor computer will NOT query A+W SQL.
echo.

if not exist "%SCRIPT_PATH%" goto :missing_script
where powershell.exe >nul 2>&1
if errorlevel 1 goto :missing_powershell

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
>"%LOG_PATH%" echo Floor folder-import setup launcher started on %DATE% at %TIME%.
>>"%LOG_PATH%" echo Project root: "%PROJECT_ROOT%"
>>"%LOG_PATH%" echo PowerShell script: "%SCRIPT_PATH%"

echo Starting PowerShell setup...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_PATH%" -ProjectRoot "%PROJECT_ROOT%"
set "SETUP_EXIT_CODE=%ERRORLEVEL%"
>>"%LOG_PATH%" echo PowerShell exit code: %SETUP_EXIT_CODE%
exit /b %SETUP_EXIT_CODE%

:missing_script
echo ERROR: Setup script was not found.
echo Expected file: "%SCRIPT_PATH%"
echo.
echo Extract the complete v133 update into the scanner project folder and try again.
exit /b 2

:missing_powershell
echo ERROR: Windows PowerShell could not be found on this computer.
exit /b 3

:missing_project_root
echo ERROR: The current scanner project folder could not be determined.
set "EXIT_CODE=4"
goto :finish

:finish
if not defined EXIT_CODE set "EXIT_CODE=1"
echo.
if "%EXIT_CODE%"=="0" echo Floor folder-import setup completed successfully.
if not "%EXIT_CODE%"=="0" echo Floor folder-import setup FAILED with exit code %EXIT_CODE%.
if not "%EXIT_CODE%"=="0" echo Read the error above. No scanner database was replaced by this setup.
if defined LOG_PATH echo Launcher log: "%LOG_PATH%"
echo.
echo Press any key to close this window.
pause >nul
exit /b %EXIT_CODE%
