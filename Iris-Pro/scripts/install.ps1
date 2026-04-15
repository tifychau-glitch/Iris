# IRIS Installer for Windows
# Run: Right-click > Run with PowerShell, or: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$IRIS_DIR = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $IRIS_DIR

$TOTAL = 8

function Step($num, $msg) { Write-Host "`n[$num/$TOTAL] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[x] $msg" -ForegroundColor Red; exit 1 }
function Ok($msg) { Write-Host "    $msg" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "  ================================"
Write-Host "  IRIS - Installing"
Write-Host "  ================================"
Write-Host ""

# --- 1. Check Python ---
Step 1 "Checking Python..."
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $pyVer = & python --version 2>&1
    Ok "$pyVer"
} else {
    Fail "Python not found. Install from https://www.python.org/downloads/ (check 'Add to PATH')"
}

# --- 2. Check Node.js ---
Step 2 "Checking Node.js..."
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nodeVer = & node --version 2>&1
    Ok "Node $nodeVer"
} else {
    Warn "Node.js not found. Claude Code CLI requires Node.js."
    Write-Host "    Install: https://nodejs.org (LTS version)"
}

# --- 3. Check/install Claude Code CLI ---
Step 3 "Checking Claude Code CLI..."
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    $claudeVer = & claude --version 2>&1
    Ok "Claude CLI: $claudeVer"
} else {
    Write-Host "    Installing Claude Code CLI..."
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        try {
            & npm install -g @anthropic-ai/claude-code 2>$null
            Ok "Installed."
        } catch {
            Warn "npm install failed. Install manually: npm install -g @anthropic-ai/claude-code"
        }
    } else {
        Warn "npm not found. Install Claude Code CLI manually after installing Node.js."
    }
}

# --- 4. Create directories ---
Step 4 "Creating directories..."
$dirs = @("memory\logs", "data", "data\capture_markers", "logs", ".tmp", "dashboard\scripts")
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}
Ok "Done."

# --- 5. Install Python dependencies ---
Step 5 "Installing Python dependencies..."
$packages = "flask python-dotenv pyyaml requests python-telegram-bot"
try {
    & python -m pip install --quiet $packages.Split(" ") 2>$null
    Ok "Done."
} catch {
    try {
        & python -m pip install --user $packages.Split(" ") 2>$null
        Ok "Installed (user mode)."
    } catch {
        Warn "pip install failed. Try: python -m pip install $packages"
    }
}

# --- 6. Create .env from template ---
Step 6 "Setting up environment..."
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Ok "Created .env from template."
    } else {
        @"
# IRIS Environment Variables
# Add your keys here or use the dashboard at http://localhost:5050/settings

# Pinecone (long-term memory)
PINECONE_API_KEY=

# Telegram Bot
TELEGRAM_BOT_TOKEN=

# OpenAI (used by mem0 for embeddings)
OPENAI_API_KEY=

# Gmail SMTP (optional)
SMTP_USER=
SMTP_PASSWORD=
"@ | Set-Content ".env"
        Ok "Created .env template."
    }
} else {
    Ok ".env already exists."
}

# --- 7. Initialize databases ---
Step 7 "Initializing databases..."
& python -c @"
import sys
sys.path.insert(0, 'dashboard')
from db import init_db
init_db()
print('    Database initialized.')
"@

# Sync connector registry
& python -c @"
import sys
sys.path.insert(0, 'dashboard')
from db import init_db, get_db
init_db()
try:
    import yaml
    from pathlib import Path
    from datetime import datetime
    reg_path = Path('dashboard/connectors.yaml')
    if reg_path.exists():
        with open(reg_path) as f:
            registry = yaml.safe_load(f).get('connectors', [])
        conn = get_db()
        now = datetime.now().isoformat()
        for c in registry:
            existing = conn.execute('SELECT id FROM connectors WHERE name = ?', (c['name'],)).fetchone()
            if not existing:
                conn.execute(
                    'INSERT INTO connectors (name, display_name, category, status, config_json, created_at, updated_at) VALUES (?, ?, ?, ''disconnected'', ''{}'', ?, ?)',
                    (c['name'], c['display_name'], c['category'], now, now))
        conn.commit()
        conn.close()
        print('    Connectors synced.')
except ImportError:
    print('    Connectors will sync on first dashboard launch.')
"@

# Create today's daily log
$today = Get-Date -Format "yyyy-MM-dd"
$todayFull = Get-Date -Format "dddd, MMMM dd, yyyy"
$logPath = "memory\logs\$today.md"
if (-not (Test-Path $logPath)) {
    @"
# Daily Log: $today

> Session log for $todayFull

---

## Events & Notes

"@ | Set-Content $logPath
    Ok "Created today's log."
}

# --- 8. Done ---
Step 8 "Setup complete."

Write-Host ""
Write-Host "  ================================"
Write-Host "  IRIS is ready."
Write-Host "  ================================"
Write-Host ""
Write-Host "  Next steps:"
Write-Host ""
Write-Host "  1. Start the dashboard:"
Write-Host "     python dashboard\app.py"
Write-Host ""
Write-Host "  2. Open in your browser:"
Write-Host "     http://localhost:5050"
Write-Host ""
Write-Host "  3. Set a password, then connect your"
Write-Host "     integrations in Settings."
Write-Host ""
Write-Host "  4. Start IRIS:"
Write-Host "     claude"
Write-Host ""
Write-Host "  ================================"
Write-Host ""

# Auto-launch dashboard
$response = Read-Host "  Start the dashboard now? [Y/n]"
if ($response -eq "" -or $response -match "^[Yy]") {
    Write-Host ""
    Write-Host "  Starting dashboard..."
    Start-Process -NoNewWindow python -ArgumentList "dashboard\app.py"
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5050/setup"
    Write-Host "  Dashboard running. Open http://localhost:5050 in your browser."
    Write-Host ""
}
