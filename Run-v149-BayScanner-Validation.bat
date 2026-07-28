@echo off
setlocal DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
title Delivery List Scanner - Validate v149
set "VALIDATION_EXIT=1"

echo ================================================
echo  Validate Delivery List Scanner v149
echo ================================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  echo ERROR: Python 3 was not found.
  goto validation_finished
)

%PYTHON_CMD% "%PROJECT_ROOT%\Validate-v149-BayScanner.py" --project-root "%PROJECT_ROOT%"
set "VALIDATION_EXIT=%errorlevel%"

if "%VALIDATION_EXIT%"=="0" (
  echo.
  echo Validation passed.
) else (
  echo.
  echo Validation failed. Review the messages above.
)

:validation_finished
echo.
pause
exit /b %VALIDATION_EXIT%
