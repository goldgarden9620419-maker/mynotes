@echo off
chcp 65001 >nul
rem ============================================================
rem  (주)에이팜건강 주간 자금계획 자동화 — EXE 빌드 스크립트
rem  실행: 이 파일이 있는 폴더에서 build_exe.bat 더블클릭
rem  결과: dist\cashflow_automation.exe
rem ============================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다. python.org에서 3.11 이상을 설치하세요.
    pause
    exit /b 1
)

echo [1/3] 필요한 라이브러리를 설치합니다...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [오류] 라이브러리 설치에 실패했습니다. 네트워크를 확인하세요.
    pause
    exit /b 1
)

echo [2/3] 테스트를 실행합니다...
python -m pytest tests -q
if errorlevel 1 (
    echo [오류] 테스트가 실패했습니다. 빌드를 중단합니다.
    pause
    exit /b 1
)

echo [3/3] EXE를 빌드합니다...
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
    --name cashflow_automation ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL._tkinter_finder ^
    --collect-data tzdata ^
    app.py
if errorlevel 1 (
    echo [오류] EXE 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 빌드 완료: dist\cashflow_automation.exe
echo 이 파일을 "자금계획_자동화\00_프로그램" 폴더로 복사한 뒤
echo install_startup.bat 을 실행해 시작프로그램에 등록하세요.
pause
