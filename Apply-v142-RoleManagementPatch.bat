@echo off
setlocal DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
title Delivery List Scanner - v142 Role Management Patch

echo ============================================================
echo  Delivery List Scanner v142 - Role Management Backend Patch
echo ============================================================
echo.
echo This adds custom role creation to the current server and store.
echo Existing roles, users, permissions, scans, and database data are preserved.
echo.

where py.exe >nul 2>&1
if errorlevel 1 goto use_python
py.exe -3 "%PROJECT_ROOT%\Apply-v142-RoleManagementPatch.py" --project-root "%PROJECT_ROOT%"
set "PATCH_EXIT=%ERRORLEVEL%"
goto patch_finished

:use_python
where python.exe >nul 2>&1
if errorlevel 1 goto no_python
python.exe "%PROJECT_ROOT%\Apply-v142-RoleManagementPatch.py" --project-root "%PROJECT_ROOT%"
set "PATCH_EXIT=%ERRORLEVEL%"
goto patch_finished

:no_python
echo ERROR: Python was not found on this computer.
echo Start the scanner once, then retry this patch from the same project folder.
set "PATCH_EXIT=1"

:patch_finished
echo.
if "%PATCH_EXIT%"=="0" goto patch_success
echo The v142 role-management patch did not complete.
echo No project files should remain partially changed; review the message above.
goto patch_pause

:patch_success
echo The v142 role-management patch completed successfully.
echo Restart the scanner server, then hard-refresh the browser with Ctrl+F5.

:patch_pause
echo.
pause
exit /b %PATCH_EXIT%
