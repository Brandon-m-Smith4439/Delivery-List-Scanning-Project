@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create-DeliveryScannerShortcut.ps1"
pause
