@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" goto :noinstall

echo Starting... browser will open automatically.
venv\Scripts\python -m streamlit run app.py
pause
exit /b 0

:noinstall
echo [ERROR] Please run install.bat first.
pause
exit /b 1
