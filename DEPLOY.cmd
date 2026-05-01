@echo off
cd /d "%~dp0"

where git.exe >nul 2>nul
if errorlevel 1 (
  if exist "C:\Program Files\Git\cmd\git.exe" set "PATH=C:\Program Files\Git\cmd;%PATH%"
)
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0DEPLOY.ps1"
echo.
pause
