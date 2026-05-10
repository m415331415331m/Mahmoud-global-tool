@echo off
:: ============================================================
:: Mahmoud AI Global Tool - Run Script
:: ============================================================
title Mahmoud AI Global Tool 2026
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Add tools\ to PATH for adb/fastboot
set PATH=%~dp0tools;%~dp0tools\platform-tools;%PATH%

python main.py
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Application crashed. Check logs\ for details.
    pause
)
