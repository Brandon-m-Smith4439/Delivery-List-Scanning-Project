@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo   Delivery List Scanner - Floor Database Transfer and Upgrade
echo ============================================================
echo.
echo IMPORTANT: Close the web app/server on BOTH the old and new copies.
echo The old database is copied and left untouched. The current database
echo is backed up before it is replaced and upgraded.
echo.

set "SOURCE_DB=%~1"
if not defined SOURCE_DB (
    set /p "SOURCE_DB=Paste the old project folder or old database path: "
)
if not defined SOURCE_DB (
    echo.
    echo No source path was entered.
    pause
    exit /b 1
)

set "SCRIPT=%~dp0tools\upgrade_floor_database.py"
if not exist "%SCRIPT%" (
    echo.
    echo Missing transfer tool: %SCRIPT%
    pause
    exit /b 1
)

set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "%~dp0venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "%~dp0python\python.exe" set "PYTHON_EXE=%~dp0python\python.exe"

if defined PYTHON_EXE (
    "%PYTHON_EXE%" "%SCRIPT%" --project-root "%~dp0" --source "%SOURCE_DB%"
    set "EXIT_CODE=%errorlevel%"
    goto finished
)

where py.exe >nul 2>&1
if not errorlevel 1 (
    py -3 "%SCRIPT%" --project-root "%~dp0" --source "%SOURCE_DB%"
    set "EXIT_CODE=%errorlevel%"
    goto finished
)

where python.exe >nul 2>&1
if not errorlevel 1 (
    python "%SCRIPT%" --project-root "%~dp0" --source "%SOURCE_DB%"
    set "EXIT_CODE=%errorlevel%"
    goto finished
)

echo.
echo Python 3 could not be found. Use the same Python installation that runs
echo Start-DeliveryScannerWebApp.bat, then run this transfer again.
set "EXIT_CODE=1"

:finished
echo.
if "%EXIT_CODE%"=="0" (
    echo Floor database transfer completed successfully.
    echo Start the current web app and verify users, lists, scans, racks, and bays.
) else (
    echo Floor database transfer did not complete. Read the message above.
    echo The tool creates/restores verified backups whenever a target change begins.
)
echo.
pause
exit /b %EXIT_CODE%
