@echo off
REM Start IRIS — double-click this file to launch
REM Works on Windows. For Mac, use "Start IRIS.command" instead.

REM Navigate to the Iris-Pro root (one level up from "Start Here\")
cd /d "%~dp0\.."

echo.
echo  ================================
echo  IRIS — Starting up
echo  ================================
echo.

REM --- Check for Claude Code ---
where claude >nul 2>&1
if errorlevel 1 (
    echo  Claude Code is not installed yet.
    echo.

    REM Check if Node.js is available
    where node >nul 2>&1
    if errorlevel 1 (
        echo  To install Claude Code, you need Node.js first.
        echo.
        echo  Here's what to do:
        echo  1. Go to nodejs.org ^(opening it now...^)
        echo  2. Download and install the LTS version
        echo  3. Double-click 'Start IRIS' again
        echo.
        start https://nodejs.org
        pause
        exit /b 1
    )

    echo  Node.js found. Installing Claude Code...
    echo.
    call npm install -g @anthropic-ai/claude-code

    where claude >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [!] Install failed. Try running this in Command Prompt:
        echo      npm install -g @anthropic-ai/claude-code
        echo.
        echo  Then double-click 'Start IRIS' again.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo  Claude Code installed!
    echo.
)

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ================================
    echo  Python is not installed.
    echo  ================================
    echo.
    echo  Download Python from python.org
    echo  Make sure to check "Add to PATH" during install.
    echo.
    start https://python.org
    pause
    exit /b 1
)

REM First run? Install first.
if not exist .env (
    echo.
    echo  ================================
    echo  First time? Let's set up IRIS.
    echo  ================================
    echo.

    REM Create directories
    if not exist memory\logs mkdir memory\logs
    if not exist data mkdir data
    if not exist logs mkdir logs
    if not exist .tmp mkdir .tmp
    if not exist dashboard\scripts mkdir dashboard\scripts

    REM Install Python dependencies
    echo  Installing dependencies...
    python -m pip install --quiet flask python-dotenv pyyaml requests python-telegram-bot 2>nul
    if errorlevel 1 (
        echo  [!] pip install failed. Trying with --user flag...
        python -m pip install --quiet --user flask python-dotenv pyyaml requests python-telegram-bot
    )

    REM Create .env from template
    if exist .env.example (
        copy .env.example .env >nul
        echo  Created .env from template.
    ) else (
        echo. > .env
        echo  Created empty .env file.
    )

    REM Initialize databases
    echo  Initializing databases...
    python -c "import sys; sys.path.insert(0,'dashboard'); from db import init_db; init_db(); print('    Databases initialized.')"

    REM Sync connectors
    python -c "import sys; sys.path.insert(0,'dashboard'); from db import init_db, get_db; init_db(); exec(open('dashboard/connectors.yaml').read()) if False else None" 2>nul
    python -c "import sys,yaml; sys.path.insert(0,'dashboard'); from db import init_db,get_db; from datetime import datetime; init_db(); f=open('dashboard/connectors.yaml'); r=yaml.safe_load(f); conn=get_db(); now=datetime.now().isoformat(); [conn.execute('INSERT OR IGNORE INTO connectors (name,display_name,category,status,config_json,created_at,updated_at) VALUES (?,?,?,\"disconnected\",\"{}\",?,?)',(c['name'],c['display_name'],c['category'],now,now)) for c in r.get('connectors',[])]; conn.commit(); conn.close(); print('    Connectors synced.')" 2>nul

    REM Configure hooks
    if exist scripts\configure_hooks.py (
        echo  Configuring hooks...
        python scripts\configure_hooks.py 2>nul
    )

    REM Create today's daily log
    for /f "tokens=*" %%d in ('python -c "from datetime import datetime; print(datetime.now().strftime('%%Y-%%m-%%d'))"') do set TODAY=%%d
    if not exist "memory\logs\%TODAY%.md" (
        echo # Daily Log: %TODAY% > "memory\logs\%TODAY%.md"
        echo. >> "memory\logs\%TODAY%.md"
        echo --- >> "memory\logs\%TODAY%.md"
        echo. >> "memory\logs\%TODAY%.md"
        echo ## Events ^& Notes >> "memory\logs\%TODAY%.md"
        echo  Created today's log.
    )

    echo.
    echo  ================================
    echo  IRIS installed. Starting...
    echo  ================================
    echo.
)

REM Start dashboard
echo  Starting dashboard...
start /b python dashboard\app.py

REM Wait for dashboard to be ready
timeout /t 3 /nobreak >nul

REM Start Telegram handler if configured
findstr /r "^TELEGRAM_BOT_TOKEN=." .env >nul 2>&1
if not errorlevel 1 (
    start /b python .claude\skills\telegram\scripts\telegram_handler.py
    echo  Telegram handler running.
) else (
    echo  Telegram not configured — connect via dashboard Settings.
)

REM Open browser
echo  Opening dashboard...
start http://localhost:5050

REM Open Claude Code in a new Command Prompt window
echo  Opening IRIS conversation...
start cmd /k "cd /d "%~dp0" && claude"

echo.
echo  ================================
echo  IRIS is running.
echo  ================================
echo.
echo  Dashboard: http://localhost:5050
echo  IRIS conversation opened in a new window.
echo  Close this window to stop background services.
echo.
pause
