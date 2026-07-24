@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title Delivery List Scanner v135 Operations Patch

echo ============================================================
echo   Delivery List Scanner v135 Operations Patch
echo ============================================================
echo.

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE where py.exe >nul 2>nul && set "PYTHON_EXE=py.exe -3"
if not defined PYTHON_EXE where python.exe >nul 2>nul && set "PYTHON_EXE=python.exe"
if not defined PYTHON_EXE goto :no_python

%PYTHON_EXE% "%CD%\Apply-v135-OperationsPatch.py"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" goto :failed

echo.
echo Patch completed successfully.
echo Restart the Delivery List Scanner server so migration 004 and the new routes load.
goto :finish

:no_python
echo Python 3 was not found. Start the scanner once or use the same Python runtime used by Start-DeliveryScannerWebApp.bat.
set "EXIT_CODE=1"
goto :finish

:failed
echo.
echo Patch failed. No server replacement is kept unless syntax validation passed.

:finish
echo.
pause
exit /b %EXIT_CODE%
