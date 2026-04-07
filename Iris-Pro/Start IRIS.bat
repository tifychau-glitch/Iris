@echo off
title IRIS
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

:: Check Claude Code CLI
claude --version >nul 2>&1
if errorlevel 1 (
    echo Installing Claude Code CLI...
    npm install -g @anthropic-ai/claude-code
)

:: First-time setup if needed
if not exist "data" (
    echo Running first-time setup...
    powershell -ExecutionPolicy Bypass -File install.ps1
)

:: Create directories if missing
if not exist "memory\logs" mkdir "memory\logs"
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"

:: Initialize database if needed
if not exist "data\projects.db" (
    python -c "import sys; sys.path.insert(0, 'dashboard'); from db import init_db; init_db()"
)

:: Start dashboard in background
echo Starting dashboard...
start /B python dashboard\app.py

:: Give it a moment
timeout /t 2 /nobreak >nul

:: Launch Claude Code
echo.
echo   ================================
echo   IRIS is starting.
echo   Dashboard: http://localhost:5050
echo   ================================
echo.
claude
