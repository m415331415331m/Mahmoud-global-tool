@echo off
:: ============================================================
:: Mahmoud AI Global Tool Ultimate 2026
:: Build Script - PyInstaller
:: Produces: dist\MahmoudAITool.exe  (one-file, windowed)
:: ============================================================

title Build - Mahmoud AI Global Tool
color 0B
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║    Building Mahmoud AI Global Tool 2026          ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Make sure PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo  [*] Installing PyInstaller...
    pip install pyinstaller
)

:: Clean previous build
echo  [*] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist"  rmdir /s /q dist

:: ── Run PyInstaller ───────────────────────────────────────
echo  [*] Running PyInstaller...

pyinstaller ^
  --name="MahmoudAITool" ^
  --onefile ^
  --windowed ^
  --icon="assets\icon.ico" ^
  --add-data="assets;assets" ^
  --add-data="localization;localization" ^
  --add-data="plugins;plugins" ^
  --add-binary="tools\adb.exe;tools" ^
  --add-binary="tools\fastboot.exe;tools" ^
  --hidden-import="PySide6.QtCore" ^
  --hidden-import="PySide6.QtGui" ^
  --hidden-import="PySide6.QtWidgets" ^
  --hidden-import="PySide6.QtNetwork" ^
  --hidden-import="sqlite3" ^
  --hidden-import="psutil" ^
  --hidden-import="requests" ^
  --hidden-import="serial" ^
  --hidden-import="usb" ^
  --hidden-import="cryptography" ^
  --collect-all="PySide6" ^
  --noconfirm ^
  main.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Build Successful!                              ║
echo  ║   Output: dist\MahmoudAITool.exe                ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Open dist folder
explorer dist
pause
