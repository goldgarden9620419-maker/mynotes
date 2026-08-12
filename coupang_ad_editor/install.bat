@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  쿠팡 광고 자동 제작 시스템 - 설치
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYCMD=python"
    ) else (
        echo [오류] Python이 설치되어 있지 않습니다.
        echo https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치한 뒤
        echo "Add python.exe to PATH"를 체크하고 다시 실행해주세요.
        pause
        exit /b 1
    )
)

echo [1/3] 가상환경 생성 중...
%PYCMD% -m venv venv
if not exist "venv\Scripts\python.exe" (
    echo [오류] 가상환경 생성에 실패했습니다.
    pause
    exit /b 1
)

echo [2/3] pip 업데이트 중...
venv\Scripts\python -m pip install --upgrade pip

echo [3/3] 라이브러리 설치 중 (몇 분 걸릴 수 있습니다)...
venv\Scripts\python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [오류] 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인해주세요.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  설치 완료! run.bat 을 실행하면 프로그램이 시작됩니다.
echo  (FFmpeg는 최초 실행 시 자동으로 다운로드됩니다)
echo ============================================
pause
