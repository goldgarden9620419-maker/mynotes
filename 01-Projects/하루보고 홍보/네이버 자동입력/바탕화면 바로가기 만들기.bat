@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo [!] Python is not installed. Install it from https://www.python.org/downloads/ and check "Add python.exe to PATH".
  pause
  exit /b
)
py naver_post.py --shortcut
pause
