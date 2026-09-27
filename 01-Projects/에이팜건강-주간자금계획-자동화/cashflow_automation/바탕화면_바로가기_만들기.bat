@echo off
chcp 65001 >nul
rem ============================================================
rem  바탕화면 바로가기 만들기 (최초 1회만 더블클릭)
rem  바탕화면에 두 개를 만든다:
rem    1) "자금계획 폴더"      - 파일 넣는 폴더가 바로 열린다
rem                             (실제로는 Obsidian 보관함 안 폴더와 연결)
rem    2) "자금계획 지금 실행" - 더블클릭하면 즉시 계산
rem ============================================================
cd /d "%~dp0"

for %%I in ("%~dp0..\자금계획_자동화") do set "TARGET=%%~fI"
if not exist "%TARGET%" (
    echo [오류] 자금계획_자동화 폴더를 찾을 수 없습니다: %TARGET%
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$s = $ws.CreateShortcut((Join-Path $desktop '자금계획 폴더.lnk'));" ^
  "$s.TargetPath = '%TARGET%';" ^
  "$s.Description = '주간 자금계획 파일 넣는 폴더 (Obsidian 보관함과 연결됨)';" ^
  "$s.Save();" ^
  "$b = $ws.CreateShortcut((Join-Path $desktop '자금계획 지금 실행.lnk'));" ^
  "$b.TargetPath = '%~dp0지금_실행.bat';" ^
  "$b.WorkingDirectory = '%~dp0';" ^
  "$b.Description = '폴더의 최신 파일로 자금계획 즉시 생성';" ^
  "$b.Save();"

if errorlevel 1 (
    echo [오류] 바로가기 생성에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 바탕화면에 두 개가 생겼습니다.
echo   1. "자금계획 폴더"      — 여기를 열어 은행·지출 파일을 넣으면 됩니다
echo   2. "자금계획 지금 실행" — 더블클릭하면 바로 계산되고 결과 폴더가 열립니다
echo.
echo 파일을 바로가기 아이콘 위로 끌어다 놓아도 폴더 안으로 들어갑니다.
pause
