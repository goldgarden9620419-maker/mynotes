@echo off
chcp 65001 >nul
rem ============================================================
rem  Windows 시작프로그램 등록 (작업 스케줄러 사용 안 함)
rem  cashflow_automation.exe 바로가기를 시작프로그램 폴더에 만든다.
rem  이 파일은 EXE와 같은 폴더(00_프로그램)에 두고 실행한다.
rem ============================================================
cd /d "%~dp0"

if not exist "%~dp0cashflow_automation.exe" (
    echo [오류] 이 폴더에 cashflow_automation.exe 가 없습니다.
    echo        build_exe.bat 으로 빌드한 뒤 dist 폴더의 EXE를 여기로 복사하세요.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$startup = [Environment]::GetFolderPath('Startup');" ^
  "$s = $ws.CreateShortcut((Join-Path $startup '에이팜건강 자금계획 자동화.lnk'));" ^
  "$s.TargetPath = '%~dp0cashflow_automation.exe';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.Description = '(주)에이팜건강 주간 자금계획 자동화';" ^
  "$s.Save();"

if errorlevel 1 (
    echo [오류] 바로가기 생성에 실패했습니다.
    pause
    exit /b 1
)

echo 시작프로그램 등록 완료.
echo PC를 켜면 트레이에서 자동으로 실행됩니다.
echo 지금 바로 시작하려면 cashflow_automation.exe 를 실행하세요.
pause
