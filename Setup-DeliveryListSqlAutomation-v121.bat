@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%automation\sql_delivery_export\Setup-DeliveryListSqlAutomation.bat"
exit /b %errorlevel%
