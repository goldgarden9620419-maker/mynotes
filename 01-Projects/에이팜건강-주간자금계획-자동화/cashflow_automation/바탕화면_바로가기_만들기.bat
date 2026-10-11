@echo off
chcp 65001 >nul
rem ============================================================
rem  바탕화면 바로가기 만들기 (다시 실행하면 덮어쓰며 갱신됨)
rem  바탕화면에 세 개를 만든다:
rem    1) "자금계획 폴더"       - 파일 넣는 폴더가 바로 열린다
rem                              (실제로는 Obsidian 보관함 안 폴더와 연결)
rem    2) "자금계획 지금 실행"  - 더블클릭하면 즉시 계산 (엑셀 아이콘)
rem    3) "자금계획 주간 대조"  - 계획 vs 실제 대조 파일 생성 (엑셀 아이콘)
rem  엑셀이 설치돼 있으면 실행 바로가기에 엑셀 아이콘을 입힌다
rem  (2026-10-11 사용자 요청). 엑셀이 없으면 기본 아이콘 유지.
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
  "$excel = $null;" ^
  "try { $excel = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe' -ErrorAction Stop).'(default)' } catch {};" ^
  "if (-not $excel -or -not (Test-Path $excel)) { foreach ($p in @('C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE','C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE')) { if (Test-Path $p) { $excel = $p; break } } };" ^
  "$s = $ws.CreateShortcut((Join-Path $desktop '자금계획 폴더.lnk'));" ^
  "$s.TargetPath = '%TARGET%';" ^
  "$s.Description = '주간 자금계획 파일 넣는 폴더 (Obsidian 보관함과 연결됨)';" ^
  "$s.Save();" ^
  "$b = $ws.CreateShortcut((Join-Path $desktop '자금계획 지금 실행.lnk'));" ^
  "$b.TargetPath = '%~dp0지금_실행.bat';" ^
  "$b.WorkingDirectory = '%~dp0';" ^
  "$b.Description = '폴더의 최신 파일로 자금계획 즉시 생성';" ^
  "if ($excel) { $b.IconLocation = $excel + ',0' };" ^
  "$b.Save();" ^
  "if (Test-Path '%~dp0주간대조_실행.bat') {" ^
  "  $r = $ws.CreateShortcut((Join-Path $desktop '자금계획 주간 대조.lnk'));" ^
  "  $r.TargetPath = '%~dp0주간대조_실행.bat';" ^
  "  $r.WorkingDirectory = '%~dp0';" ^
  "  $r.Description = '지난주 계획 vs 실제 입출금 대조 파일 생성';" ^
  "  if ($excel) { $r.IconLocation = $excel + ',0' };" ^
  "  $r.Save();" ^
  "}"

if errorlevel 1 (
    echo [오류] 바로가기 생성에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 바탕화면 바로가기를 만들었습니다 (기존 것은 덮어씀).
echo   1. "자금계획 폴더"       — 여기를 열어 은행·지출 파일을 넣으면 됩니다
echo   2. "자금계획 지금 실행"  — 더블클릭하면 바로 계산되고 결과 폴더가 열립니다
echo   3. "자금계획 주간 대조"  — 지난주 계획 vs 실제 대조 파일을 만듭니다
echo 실행 바로가기 2개에는 엑셀 아이콘이 적용됐습니다 (엑셀 설치 시).
echo.
pause
