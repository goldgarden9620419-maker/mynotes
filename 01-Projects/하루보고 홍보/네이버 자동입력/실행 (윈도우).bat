@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo [!] Python is not installed. Install it from https://www.python.org/downloads/ and check "Add python.exe to PATH".
  pause
  exit /b
)
echo Checking required programs... (first run takes 1-2 minutes)
py -m pip install --quiet --disable-pip-version-check --upgrade playwright pyperclip
py naver_post.py %*
pause
