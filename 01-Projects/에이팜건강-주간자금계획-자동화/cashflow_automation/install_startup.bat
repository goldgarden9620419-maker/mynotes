@echo off
chcp 65001 >nul
rem ============================================================
rem  Windows 시작프로그램 등록 (작업 스케줄러 사용 안 함)
rem  cashflow_automation.exe 바로가기를 시작프로그램 폴더에 만든다.
rem  이 파일이 어디 있든 EXE를 알아서 찾는다 (2026-11-16 보강):
rem    1) 이 파일과 같은 폴더  2) ..\자금계획_자동화\00_프로그램
rem ============================================================
cd /d "%~dp0"

set "EXE=%~dp0cashflow_automation.exe"
if not exist "%EXE%" set "EXE=%~dp0..\자금계획_자동화\00_프로그램\cashflow_automation.exe"
if not exist "%EXE%" (
    echo [오류] cashflow_automation.exe 를 찾을 수 없습니다.
    echo        찾아본 곳: 이 폴더, ..\자금계획_자동화\00_프로그램
    echo        EXE가 있는 폴더에 이 파일을 복사해 실행해도 됩니다.
    pause
    exit /b 1
)
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

if errorlevel 1 (
    echo [오류] 바로가기 생성에 실패했습니다.
    pause
    exit /b 1
)

echo 시작프로그램 등록 완료: %EXE%
echo PC를 켜면 트레이에서 자동으로 실행됩니다.
echo 지금 바로 시작하려면 cashflow_automation.exe 를 실행하세요.
pause
