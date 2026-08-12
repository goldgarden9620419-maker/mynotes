@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "ZIPURL=https://github.com/goldgarden9620419-maker/mynotes/archive/refs/heads/claude/coupang-ad-automation-system-nrz0sl.zip"
set "TMPDIR=%TEMP%\cae_update"
set "SRCDIR=%TMPDIR%\mynotes-claude-coupang-ad-automation-system-nrz0sl\coupang_ad_editor"

echo ============================================
echo  Coupang Ad Editor - Auto Update
echo ============================================
echo.

rmdir /s /q "%TMPDIR%" 2>nul
mkdir "%TMPDIR%"

echo [1/4] Downloading latest version...
curl -L -s -o "%TMPDIR%\update.zip" "%ZIPURL%"
if not exist "%TMPDIR%\update.zip" goto :fail

echo [2/4] Extracting...
tar -xf "%TMPDIR%\update.zip" -C "%TMPDIR%"
if not exist "%SRCDIR%\app.py" goto :fail

echo [3/4] Copying new files...
echo update.bat>"%TMPDIR%\exclude.txt"
xcopy /e /y /q "%SRCDIR%\*" "%~dp0" /EXCLUDE:%TMPDIR%\exclude.txt >nul
if errorlevel 1 goto :fail

echo [4/4] Installing new libraries if needed...
if exist "venv\Scripts\python.exe" venv\Scripts\python -m pip install -r requirements.txt --quiet

rmdir /s /q "%TMPDIR%" 2>nul
echo.
echo ============================================
echo  Update complete! Run run.bat to start.
echo ============================================
pause
exit /b 0

:fail
echo.
echo [ERROR] Update failed. Check internet connection and try again.
rmdir /s /q "%TMPDIR%" 2>nul
pause
exit /b 1
