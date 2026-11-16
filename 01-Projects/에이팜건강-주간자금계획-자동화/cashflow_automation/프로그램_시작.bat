@echo off
chcp 65001 >nul
rem ============================================================
rem  자금계획 상주 프로그램 시작 (트레이 + 월 10:30 자동 실행)
rem  EXE 없이 파이썬으로 바로 상주 모드를 켠다 (2026-11-16).
rem  더블클릭하면 창 없이 백그라운드로 떠서 트레이 아이콘이 생긴다.
rem ============================================================
cd /d "%~dp0"

set "BASE=%~dp0..\자금계획_자동화"
if not exist "%BASE%" (
    echo [오류] 자금계획_자동화 폴더를 찾을 수 없습니다: %BASE%
    pause
    exit /b 1
)

rem --- 가상환경 준비 (지금_실행.bat과 같은 과정, 최초 1회만 걸림) ---
if not exist "%~dp0.venv\Scripts\python.exe" (
    set "PY="
    where py >nul 2>nul && set "PY=py -3"
    if not defined PY where python >nul 2>nul && set "PY=python"
    if not defined PY (
        echo [오류] Python이 설치되어 있지 않습니다. 지금_실행.bat을 먼저 실행해 주세요.
        pause
        exit /b 1
    )
    echo [준비] 가상환경을 만듭니다...
    %PY% -m venv "%~dp0.venv"
)
if not exist "%~dp0.venv\install.ok" (
    echo [준비] 필요한 패키지를 설치합니다. 잠시 기다려 주세요...
    "%~dp0.venv\Scripts\python.exe" -m pip install -q -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [오류] 패키지 설치 실패 — 인터넷 연결 확인 후 다시 실행하세요.
        pause
        exit /b 1
    )
    echo ok> "%~dp0.venv\install.ok"
)

set PYTHONUTF8=1
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py" ^
    --base-dir "%BASE%" --config "%BASE%\00_프로그램\config.yaml"

echo.
echo 자금계획 상주 프로그램을 시작했습니다.
echo 잠시 후 화면 오른쪽 아래 트레이에 아이콘이 생기는지 확인하세요.
echo (이미 떠 있던 경우에도 문제없습니다 — 아이콘 우클릭으로 상태 확인)
pause
