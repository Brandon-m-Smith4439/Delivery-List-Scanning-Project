@echo off
setlocal DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
title Delivery List Scanner v146 Bay Scanner Update

echo ============================================================
echo  Delivery List Scanner v146 Bay Scanner Workflow Refinement
echo ============================================================
echo.

echo Project:
echo   %PROJECT_ROOT%
echo.

set "PYTHON_EXE="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE where py.exe >nul 2>&1 && set "PYTHON_EXE=py.exe -3"
if not defined PYTHON_EXE where python.exe >nul 2>&1 && set "PYTHON_EXE=python.exe"
if not defined PYTHON_EXE goto no_python

%PYTHON_EXE% "%PROJECT_ROOT%\Apply-v146-BayScannerWorkflowRefinement.py" --project-root "%PROJECT_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto result

:no_python
echo ERROR: Python 3 was not found.
echo Start the scanner once, then run this update again.
set "EXIT_CODE=1"

:result
echo.
if "%EXIT_CODE%"=="0" goto success
echo v146 was not installed. Read the message above.
goto finish

:success
echo v146 installed successfully.
echo Restart the scanner and press Ctrl+F5 once in the browser.

:finish
echo.
pause
exit /b %EXIT_CODE%
