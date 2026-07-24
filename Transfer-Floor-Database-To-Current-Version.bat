@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Delivery List Scanner - Floor Database Transfer

set "PROJECT_ROOT=%~dp0"
for %%I in ("%PROJECT_ROOT%.") do set "PROJECT_ROOT=%%~fI"
set "SCRIPT=%PROJECT_ROOT%\tools\upgrade_floor_database.py"
set "LOG_DIR=%PROJECT_ROOT%\logs"
set "LAUNCH_LOG=%LOG_DIR%\floor-database-transfer-launch.log"
set "EXIT_CODE=1"
set "DLS_FLOOR_TRANSFER_SOURCE=%~1"

cd /d "%PROJECT_ROOT%" 2>nul
if errorlevel 1 goto launch_failed

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
>"%LAUNCH_LOG%" echo [%date% %time%] Floor database transfer launcher started.
>>"%LAUNCH_LOG%" echo Project root: %PROJECT_ROOT%

cls
echo ============================================================
echo   Delivery List Scanner - Floor Database Transfer and Upgrade
echo ============================================================
echo.
echo IMPORTANT: Close the web app/server on BOTH the old and new copies.
echo The old database is copied and left untouched. The current database
echo is backed up before it is replaced and upgraded.
echo.

if not exist "%SCRIPT%" goto missing_script

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" goto run_dot_venv
if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" goto run_venv
if exist "%PROJECT_ROOT%\python\python.exe" goto run_bundled_python
where py.exe >nul 2>&1
if not errorlevel 1 goto run_py_launcher
where python.exe >nul 2>&1
if not errorlevel 1 goto run_path_python
goto missing_python

:run_dot_venv
>>"%LAUNCH_LOG%" echo Python: %PROJECT_ROOT%\.venv\Scripts\python.exe
"%PROJECT_ROOT%\.venv\Scripts\python.exe" "%SCRIPT%" --project-root "%PROJECT_ROOT%" --interactive
set "EXIT_CODE=%errorlevel%"
goto finished

:run_venv
>>"%LAUNCH_LOG%" echo Python: %PROJECT_ROOT%\venv\Scripts\python.exe
"%PROJECT_ROOT%\venv\Scripts\python.exe" "%SCRIPT%" --project-root "%PROJECT_ROOT%" --interactive
set "EXIT_CODE=%errorlevel%"
goto finished

:run_bundled_python
>>"%LAUNCH_LOG%" echo Python: %PROJECT_ROOT%\python\python.exe
"%PROJECT_ROOT%\python\python.exe" "%SCRIPT%" --project-root "%PROJECT_ROOT%" --interactive
set "EXIT_CODE=%errorlevel%"
goto finished

:run_py_launcher
>>"%LAUNCH_LOG%" echo Python: py.exe -3
py -3 "%SCRIPT%" --project-root "%PROJECT_ROOT%" --interactive
set "EXIT_CODE=%errorlevel%"
goto finished

:run_path_python
>>"%LAUNCH_LOG%" echo Python: python.exe
python "%SCRIPT%" --project-root "%PROJECT_ROOT%" --interactive
set "EXIT_CODE=%errorlevel%"
goto finished

:missing_script
echo ERROR: The database transfer tool is missing:
echo   %SCRIPT%
echo.
echo Extract the complete v128 changed-files package into the current project
echo before running this BAT again.
>>"%LAUNCH_LOG%" echo ERROR: Missing transfer tool: %SCRIPT%
set "EXIT_CODE=1"
goto finished

:missing_python
echo ERROR: Python 3 could not be found.
echo.
echo Use the same Python installation that runs Start-DeliveryScannerWebApp.bat,
echo then run this transfer again.
>>"%LAUNCH_LOG%" echo ERROR: Python 3 could not be found.
set "EXIT_CODE=1"
goto finished

:launch_failed
echo.
echo ERROR: The BAT could not open its project folder:
echo   %PROJECT_ROOT%
echo.
set "EXIT_CODE=1"
goto finished_no_log

:finished
>>"%LAUNCH_LOG%" echo [%date% %time%] Transfer process exit code: %EXIT_CODE%

:finished_no_log
echo.
if "%EXIT_CODE%"=="0" goto success_message

echo Floor database transfer did not complete.
echo Read the message above. Nothing should be replaced unless the transfer
echo reached the guarded replacement stage, and failed replacements are restored.
goto pause_before_exit

:success_message
echo Floor database transfer completed successfully.
echo Start the current web app and verify users, lists, scans, racks, and bays.

:pause_before_exit
echo.
if exist "%LAUNCH_LOG%" echo Launcher log: %LAUNCH_LOG%
echo Press any key to close this window.
pause >nul
endlocal & exit /b %EXIT_CODE%
