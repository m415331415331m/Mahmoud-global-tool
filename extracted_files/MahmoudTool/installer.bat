@echo off
:: ============================================================
:: Mahmoud AI Global Tool Ultimate 2026
:: Installer Script for Windows
:: ============================================================

title Mahmoud AI Global Tool - Installer
color 0A

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║    Mahmoud AI Global Tool Ultimate 2026          ║
echo  ║    Professional Android Maintenance Tool         ║
echo  ║    Installer v2.0                                ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── Check Python ─────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found! Please install Python 3.12+
    echo  Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER% found

:: ── Check pip ─────────────────────────────────────────────
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] pip not found!
    pause
    exit /b 1
)
echo  [OK] pip found

:: ── Create virtual environment ────────────────────────────
echo.
echo  [*] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo  [OK] Virtual environment ready

:: ── Activate venv ─────────────────────────────────────────
call venv\Scripts\activate.bat

:: ── Upgrade pip ───────────────────────────────────────────
echo  [*] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: ── Install requirements ──────────────────────────────────
echo  [*] Installing requirements (this may take a few minutes)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install requirements
    pause
    exit /b 1
)
echo  [OK] All packages installed

:: ── Create required directories ───────────────────────────
echo  [*] Creating application directories...
if not exist "data"     mkdir data
if not exist "logs"     mkdir logs
if not exist "firmware" mkdir firmware
if not exist "backups"  mkdir backups
if not exist "plugins"  mkdir plugins

:: ── Download ADB if not present ───────────────────────────
if not exist "tools\adb.exe" (
    echo  [*] Downloading platform-tools (ADB + Fastboot)...
    mkdir tools 2>nul
    powershell -Command ^
      "Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile 'tools\platform-tools.zip'"
    if exist "tools\platform-tools.zip" (
        powershell -Command ^
          "Expand-Archive -Path 'tools\platform-tools.zip' -DestinationPath 'tools' -Force"
        copy "tools\platform-tools\adb.exe"      "tools\adb.exe"      >nul 2>&1
        copy "tools\platform-tools\fastboot.exe" "tools\fastboot.exe" >nul 2>&1
        echo  [OK] ADB and Fastboot downloaded
    ) else (
        echo  [WARN] Could not download platform-tools. Place adb.exe in tools\
    )
)

:: ── Create Desktop Shortcut ───────────────────────────────
echo  [*] Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT=%USERPROFILE%\Desktop\Mahmoud AI Tool.lnk
powershell -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%SCRIPT_DIR%run.bat'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'Mahmoud AI Global Tool 2026'; $s.Save()"
echo  [OK] Desktop shortcut created

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Installation Complete!                         ║
echo  ║   Run: run.bat  or double-click the shortcut     ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
