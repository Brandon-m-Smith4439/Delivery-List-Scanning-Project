@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "SCRIPT_PATH=%PROJECT_ROOT%\Setup-Floor-Folder-Import-Automation.ps1"

echo ================================================================
echo  Delivery List Scanner - Floor Folder Import Setup v132
echo ================================================================
echo.
echo This installs hourly imports from the Temp Delivery Lists folder.
echo This floor computer will NOT query A+W SQL.
echo.

if not exist "%SCRIPT_PATH%" (
  echo ERROR: Setup script was not found:
  echo %SCRIPT_PATH%
  echo.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_PATH%" -ProjectRoot "%PROJECT_ROOT%"
set "EXIT_CODE=%errorlevel%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo Floor folder-import setup FAILED.
  echo Read the error above. No scanner database was replaced by this setup.
) else (
  echo Floor folder-import setup completed successfully.
)
echo.
pause
exit /b %EXIT_CODE%
