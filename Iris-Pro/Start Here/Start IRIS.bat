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

REM ---------------------------------------------------------------
REM Step 1: Check for Git (Claude Code requires it)
REM ---------------------------------------------------------------
where git >nul 2>&1
if errorlevel 1 (
    echo  Git is not installed. Claude Code needs it to run.
    echo.

    REM Try 1: Auto-install via winget (built into Windows 10/11)
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo  Installing Git automatically...
        echo.
        winget install Git.Git --accept-package-agreements --accept-source-agreements 2>nul

        REM Refresh PATH
        set "PATH=%ProgramFiles%\Git\cmd;%PATH%"

        where git >nul 2>&1
        if not errorlevel 1 (
            echo.
            echo  Git installed!
            echo.
            goto :git_ok
        )
    )

    REM Try 2: Manual install (winget not available or failed)
    echo  Please install Git manually:
    echo.
    echo  1. A download page is opening now...
    echo  2. Run the installer — use all the default settings
    echo  3. IMPORTANT: Restart your computer after installing
    echo  4. Double-click 'Start IRIS' again
    echo.
    start https://git-scm.com/download/win
    echo  After installing Git and restarting, come back
    echo  and double-click 'Start IRIS' again.
    echo.
    pause
    exit /b 1
)
:git_ok

REM ---------------------------------------------------------------
REM Step 2: Check for Python
REM ---------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python is not installed. IRIS needs it to run.
    echo.

    REM Try 1: Auto-install via winget (built into Windows 10/11)
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo  Installing Python automatically...
        echo.
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements 2>nul

        REM Refresh PATH
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

        python --version >nul 2>&1
        if not errorlevel 1 (
            echo.
            echo  Python installed!
            echo.
            goto :python_ok
        )
    )

    REM Try 2: Manual install (winget not available or failed)
    echo  Please install Python manually:
    echo.
    echo  1. A download page is opening now...
    echo  2. Click "Download Python"
    echo  3. Run the installer
    echo.
    echo     *** IMPORTANT ***
    echo     On the FIRST screen, check the box at the bottom
    echo     that says "Add python.exe to PATH"
    echo     If you miss this, IRIS won't be able to find Python.
    echo.
    echo  4. At the END of the installer, click
    echo     "Disable path length limit" if it appears
    echo  5. Double-click 'Start IRIS' again
    echo.
    start https://python.org/downloads
    echo  After installing Python, come back and
    echo  double-click 'Start IRIS' again.
    echo.
    pause
    exit /b 1
)
:python_ok

REM ---------------------------------------------------------------
REM Step 3: Check for Claude Code
REM ---------------------------------------------------------------
where claude >nul 2>&1
if errorlevel 1 (
    echo  Claude Code is not installed yet.
    echo  Installing now...
    echo.

    REM Try 1: Native installer (recommended by Anthropic)
    echo  Trying native installer...
    powershell -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex" 2>nul

    REM Refresh PATH so we can find claude
    set "PATH=%LOCALAPPDATA%\Programs\claude-code;%USERPROFILE%\.claude\bin;%PATH%"

    where claude >nul 2>&1
    if errorlevel 1 (
        REM Try 2: npm fallback (if user has Node.js)
        where npm >nul 2>&1
        if not errorlevel 1 (
            echo.
            echo  Native installer didn't work. Trying npm...
            echo.
            call npm install -g @anthropic-ai/claude-code 2>nul
        )
    )

    REM Final check
    where claude >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  Could not install Claude Code automatically.
        echo.
        echo  Please install it manually:
        echo  1. Open PowerShell
        echo  2. Paste: irm https://claude.ai/install.ps1 ^| iex
        echo  3. Double-click 'Start IRIS' again
        echo.
        echo  Or visit: https://claude.ai/download
        echo.
        pause
        exit /b 1
    )

    echo.
    echo  Claude Code installed!
    echo.
)

echo  [OK] Git installed
echo  [OK] Python installed
echo  [OK] Claude Code installed
echo.

REM First run? Install first.
REM Use a marker file — .env may already exist from the template
if not exist .iris-installed (
    echo.
    echo  ================================
    echo  First time? Setting up IRIS...
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

    REM Ensure .env exists (create from template if missing)
    if not exist .env (
        if exist .env.example (
            copy .env.example .env >nul
            echo  Created .env from template.
        ) else (
            echo. > .env
            echo  Created empty .env file.
        )
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

    REM Mark setup as complete
    echo installed> .iris-installed

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

REM Open Claude Code
echo  Opening IRIS...

REM Prefer Claude desktop app (cleaner chat UI) over terminal
if exist "%LOCALAPPDATA%\Programs\claude-desktop\Claude.exe" (
    start "" "%LOCALAPPDATA%\Programs\claude-desktop\Claude.exe"
    echo.
    echo  ================================
    echo  Claude is opening.
    echo  ================================
    echo.
    echo  To talk to IRIS:
    echo  1. Click the 'Code' tab in Claude
    echo  2. Set Environment to 'Local'
    echo  3. Select this folder as your project:
    echo     %cd%
    echo  4. Type your first message and press Enter
    echo.
    echo  ^(You only need to select the folder once --
    echo   Claude remembers it for next time.^)
    echo.
) else (
    REM No desktop app -- fall back to terminal
    start cmd /k "cd /d "%~dp0\.." && claude"
)

echo.
echo  ================================
echo  IRIS is running.
echo  ================================
echo.
echo  Dashboard: http://localhost:5050
echo  Close this window to stop background services.
echo.
pause
