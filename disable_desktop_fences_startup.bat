@echo off
setlocal
cd /d "%~dp0"
"%~dp0dist\desktop_fences_lite_v6.exe" --disable-startup
if errorlevel 1 (
  echo Failed to disable startup.
  pause
  exit /b 1
)
echo Desktop Fences Lite v6 startup has been disabled.
pause

