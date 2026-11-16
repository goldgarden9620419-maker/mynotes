@echo off
chcp 65001 >nul
rem ============================================================
rem  Windows 시작프로그램 등록 (작업 스케줄러 사용 안 함)
rem  PC를 켜면 자금계획 상주 프로그램(트레이 + 월 10:30 자동 실행)이
rem  자동으로 뜨게 등록한다. 2026-11-16 보강: EXE가 없으면 파이썬
rem  상주 모드(.venv\pythonw.exe app.py)를 대신 등록한다 — EXE 불필요.
rem ============================================================
cd /d "%~dp0"

set "BASE=%~dp0..\자금계획_자동화"

rem --- 1순위: 빌드된 EXE (같은 폴더 → 00_프로그램) ---
set "EXE=%~dp0cashflow_automation.exe"
if not exist "%EXE%" set "EXE=%BASE%\00_프로그램\cashflow_automation.exe"
if exist "%EXE%" (
    for %%I in ("%EXE%") do set "EXE=%%~fI"
    for %%I in ("%EXE%") do set "EXEDIR=%%~dpI"
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ws = New-Object -ComObject WScript.Shell;" ^
      "$startup = [Environment]::GetFolderPath('Startup');" ^
      "$s = $ws.CreateShortcut((Join-Path $startup '에이팜건강 자금계획 자동화.lnk'));" ^
      "$s.TargetPath = '%EXE%';" ^
      "$s.WorkingDirectory = '%EXEDIR%';" ^
      "$s.Description = '(주)에이팜건강 주간 자금계획 자동화';" ^
      "$s.Save();"
    if errorlevel 1 goto :fail
    echo 시작프로그램 등록 완료 (EXE): %EXE%
    goto :done
)

rem --- 2순위: 파이썬 상주 모드 (가상환경 필요) ---
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
    echo [안내] 아직 파이썬 가상환경이 없습니다.
    echo        이 폴더의 "프로그램_시작.bat"을 먼저 한 번 실행한 뒤
    echo        이 파일을 다시 실행해 주세요.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$startup = [Environment]::GetFolderPath('Startup');" ^
  "$s = $ws.CreateShortcut((Join-Path $startup '에이팜건강 자금계획 자동화.lnk'));" ^
  "$s.TargetPath = '%~dp0.venv\Scripts\pythonw.exe';" ^
  "$s.Arguments = '\"%~dp0app.py\" --base-dir \"%BASE%\" --config \"%BASE%\00_프로그램\config.yaml\"';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.Description = '(주)에이팜건강 주간 자금계획 자동화';" ^
  "$s.Save();"
if errorlevel 1 goto :fail
echo 시작프로그램 등록 완료 (파이썬 상주 모드).

:done
echo PC를 켜면 트레이에서 자동으로 실행됩니다.
echo 지금 바로 켜려면 "프로그램_시작.bat"을 실행하세요.
pause
exit /b 0

:fail
echo [오류] 바로가기 생성에 실패했습니다.
pause
exit /b 1
