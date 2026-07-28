@echo off
setlocal DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
title Build Delivery List Scanner v147 Full Project ZIP

echo ============================================================
echo  Build Delivery List Scanner v147 Full Project ZIP
echo ============================================================
echo.

set "PYTHON_EXE="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE where py.exe >nul 2>&1 && set "PYTHON_EXE=py.exe -3"
if not defined PYTHON_EXE where python.exe >nul 2>&1 && set "PYTHON_EXE=python.exe"
if not defined PYTHON_EXE goto no_python

%PYTHON_EXE% "%PROJECT_ROOT%\Build-v147-Full-Project-Package.py" --project-root "%PROJECT_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto finish

:no_python
echo ERROR: Python 3 was not found.
set "EXIT_CODE=1"

:finish
echo.
pause
exit /b %EXIT_CODE%
