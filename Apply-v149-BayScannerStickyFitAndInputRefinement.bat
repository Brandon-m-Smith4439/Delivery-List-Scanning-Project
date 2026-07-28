@echo off
setlocal DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
title Delivery List Scanner - v149 Bay Scanner Refinement
set "PATCH_EXIT=1"

echo ======================================================
echo  Delivery List Scanner v149 Bay Scanner Update
echo ======================================================
echo.
echo Project: %PROJECT_ROOT%
echo.

set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  echo ERROR: Python 3 was not found.
  echo Install Python 3 or run this update from the scanner computer.
  goto patch_finished
)

%PYTHON_CMD% "%PROJECT_ROOT%\Apply-v149-BayScannerStickyFitAndInputRefinement.py" --project-root "%PROJECT_ROOT%"
if errorlevel 1 goto patch_failed

set "PATCH_EXIT=0"
echo.
echo v149 installed successfully.
echo Restart the scanner and press Ctrl+F5 once in the browser.
goto patch_finished

:patch_failed
echo.
echo The v149 update did not complete. Review the message above.

:patch_finished
echo.
pause
exit /b %PATCH_EXIT%
