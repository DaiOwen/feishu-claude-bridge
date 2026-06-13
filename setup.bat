@echo off
chcp 65001 >nul
title Feishu Claude Bridge

echo ============================================================
echo   Feishu Claude Bridge - Quick Start
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)

REM Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM Start bridge
echo [2/2] Starting bridge...
echo.
python bridge.py

pause
