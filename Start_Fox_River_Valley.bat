@echo off
setlocal
cd /d "%~dp0"
set "FRV_HOME=%CD%"
echo Fox River Valley runtime root: %FRV_HOME%
echo Observer URL: http://127.0.0.1:8765/observer.html
echo Starting observer launcher...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_observer.ps1"
echo.
pause
