@echo off
setlocal
cd /d "%~dp0"
"%~dp0dist\desktop_fences_lite_v6.exe" --enable-startup
if errorlevel 1 (
  echo Failed to enable startup.
  pause
  exit /b 1
)
echo Desktop Fences Lite v6 will start automatically after Windows login.
pause

