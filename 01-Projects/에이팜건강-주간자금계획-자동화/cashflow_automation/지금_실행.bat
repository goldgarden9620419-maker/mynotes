@echo off
chcp 65001 >nul
rem ============================================================
rem  자금계획 지금 실행 (터미널 원클릭)
rem  더블클릭 또는 터미널에서 실행하면:
rem    1) 파이썬 확인 -> 2) 가상환경 준비(최초 1회) ->
rem    3) 폴더를 검색해 최신 입력파일로 자금계획 생성 -> 4) 결과 폴더 열기
rem  최신 파일 선택은 프로그램이 수정시각 기준으로 자동 처리한다.
rem ============================================================
cd /d "%~dp0"

set "BASE=%~dp0..\자금계획_자동화"
if not exist "%BASE%" (
    echo [오류] 자금계획_자동화 폴더를 찾을 수 없습니다: %BASE%
    pause
    exit /b 1
)

rem --- 파이썬 찾기 (py 런처 우선) ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo        https://www.python.org/downloads/ 에서 3.11 이상을 설치한 뒤 다시 실행하세요.
    echo        ^(설치 시 "Add python.exe to PATH" 체크 필수^)
    pause
    exit /b 1
)

rem --- 가상환경 준비 (최초 1회만 몇 분 걸림) ---
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [준비] 가상환경을 만들고 필요한 패키지를 설치합니다. 잠시 기다려 주세요...
    %PY% -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
    "%~dp0.venv\Scripts\python.exe" -m pip install -q -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하세요.
        pause
        exit /b 1
    )
)

echo [실행] 폴더를 검색해 최신 입력파일로 자금계획을 생성합니다...
"%~dp0.venv\Scripts\python.exe" "%~dp0app.py" --run-now --force --allow-partial ^
    --base-dir "%BASE%" --config "%BASE%\00_프로그램\config.yaml"
set RC=%ERRORLEVEL%

echo.
if %RC%==0 (
    echo [완료] 결과가 05_결과 폴더에 저장되었습니다. 폴더를 엽니다.
    start "" "%BASE%\05_결과"
) else (
    echo [실패] 자세한 내용은 실행로그를 확인하세요: %BASE%\07_실행로그
)
pause
