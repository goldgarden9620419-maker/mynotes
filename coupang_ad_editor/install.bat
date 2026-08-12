@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  Coupang Ad Editor - Install
echo ============================================
echo.

set "PYCMD=python"
python --version >nul 2>nul
if not errorlevel 1 goto :found

set "PYCMD=py -3"
py -3 --version >nul 2>nul
if not errorlevel 1 goto :found

echo [ERROR] Python not found.
echo https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치한 뒤
echo "Add python.exe to PATH" 를 체크하고 다시 실행해주세요.
pause
exit /b 1

:found
echo Using Python:
%PYCMD% --version
echo.

echo [1/3] Creating virtual environment...
%PYCMD% -m venv venv
if not exist "venv\Scripts\python.exe" goto :venvfail

echo [2/3] Upgrading pip...
venv\Scripts\python -m pip install --upgrade pip

echo [3/3] Installing libraries... 5-15 min
venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto :pipfail

echo.
echo ============================================
echo  Install complete! Run run.bat to start.
echo  (FFmpeg auto-downloads on first run)
echo ============================================
pause
exit /b 0

:venvfail
echo [ERROR] Failed to create venv.
pause
exit /b 1

:pipfail
echo [ERROR] Library install failed. Check internet connection.
pause
exit /b 1
