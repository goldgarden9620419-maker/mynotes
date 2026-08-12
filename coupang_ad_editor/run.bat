@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [안내] 먼저 install.bat 을 실행해 설치를 완료해주세요.
    pause
    exit /b 1
)

echo 프로그램을 시작합니다. 브라우저가 자동으로 열립니다...
venv\Scripts\python -m streamlit run app.py --server.headless false
pause
