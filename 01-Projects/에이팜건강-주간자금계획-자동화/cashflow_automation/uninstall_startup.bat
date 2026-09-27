@echo off
chcp 65001 >nul
rem ============================================================
rem  Windows 시작프로그램 등록 해제
rem ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$startup = [Environment]::GetFolderPath('Startup');" ^
  "$lnk = Join-Path $startup '에이팜건강 자금계획 자동화.lnk';" ^
  "if (Test-Path $lnk) { Remove-Item $lnk; Write-Host '시작프로그램 등록을 해제했습니다.' }" ^
  "else { Write-Host '등록된 바로가기가 없습니다.' }"
pause
