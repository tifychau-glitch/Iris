#!/bin/bash
# IRIS Installer — One command to a working system
# Run: chmod +x install.sh && ./install.sh

set -e

IRIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$IRIS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
DIM='\033[0;90m'
RESET='\033[0m'

step() { echo -e "\n${GREEN}[$1/$TOTAL]${RESET} $2"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
fail() { echo -e "${RED}[x]${RESET} $1"; exit 1; }
ok()   { echo -e "    ${DIM}$1${RESET}"; }

TOTAL=10

echo ""
echo "  ================================"
echo "  IRIS — Installing"
echo "  ================================"
echo ""

# --- 1. Check Python 3 ---
step 1 "Checking Python 3..."
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    ok "$PY_VERSION"
else
    fail "Python 3 not found. Install: brew install python3 (macOS) or apt install python3 (Linux)"
fi

# --- 2. Check Node.js (needed for Claude Code CLI) ---
step 2 "Checking Node.js..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    ok "Node $NODE_VERSION"
else
    warn "Node.js not found. Claude Code CLI requires Node.js."
    echo "    Install: https://nodejs.org or brew install node (macOS)"
    echo "    You can continue, but Claude CLI won't work until Node is installed."
fi

# --- 3. Check/install Claude Code CLI ---
step 3 "Checking Claude Code CLI..."
if command -v claude &>/dev/null; then
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "installed")
    ok "Claude CLI: $CLAUDE_VERSION"
else
    echo "    Installing Claude Code CLI..."
    if command -v npm &>/dev/null; then
        npm install -g @anthropic-ai/claude-code 2>/dev/null && ok "Installed." || {
            warn "npm install failed. Install manually: npm install -g @anthropic-ai/claude-code"
        }
    else
        warn "npm not found. Install Claude Code CLI manually:"
        echo "    npm install -g @anthropic-ai/claude-code"
    fi
fi

# --- 4. Create directories ---
step 4 "Creating directories..."
mkdir -p memory/logs
mkdir -p data
mkdir -p data/capture_markers
mkdir -p logs
mkdir -p .tmp
mkdir -p dashboard/scripts
ok "Done."

# --- 5. Install Python dependencies ---
step 5 "Installing Python dependencies..."

# Detect if we need a venv (Ubuntu 24+ / externally managed)
USE_VENV=false
if python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
    pip3 install --quiet --dry-run flask 2>/dev/null || USE_VENV=true
fi

PACKAGES="flask python-dotenv pyyaml requests python-telegram-bot"

if [ "$USE_VENV" = true ]; then
    if [ ! -d "venv" ]; then
        echo "    Creating virtual environment (system pip restricted)..."
        python3 -m venv venv || fail "Failed to create venv. Install: apt install python3-venv"
    fi
    source venv/bin/activate
    pip install --quiet $PACKAGES
    ok "Installed in venv. Activate with: source venv/bin/activate"
else
    pip3 install --quiet $PACKAGES 2>/dev/null || \
    pip3 install --quiet --user $PACKAGES 2>/dev/null || \
    pip install --quiet $PACKAGES 2>/dev/null || {
        warn "pip install failed. Try: pip3 install $PACKAGES"
    }
    ok "Done."
fi

# --- 6. Create .env from template ---
step 6 "Setting up environment..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        ok "Created .env from template."
    else
        cat > .env << 'ENVEOF'
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
ENVEOF
        ok "Created .env template."
    fi
else
    ok ".env already exists."
fi

# --- 7. Initialize databases ---
step 7 "Initializing databases..."
python3 -c "
import sys
sys.path.insert(0, 'dashboard')
from db import init_db
init_db()
print('    Database initialized.')
"

# Sync connector registry
python3 -c "
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
                    'INSERT INTO connectors (name, display_name, category, status, config_json, created_at, updated_at) VALUES (?, ?, ?, \"disconnected\", \"{}\", ?, ?)',
                    (c['name'], c['display_name'], c['category'], now, now))
        conn.commit()
        conn.close()
        print('    Connectors synced.')
except ImportError:
    print('    Connectors will sync on first dashboard launch.')
"

# Create today's daily log
TODAY=$(date +%Y-%m-%d)
TODAY_LOG="memory/logs/${TODAY}.md"
if [ ! -f "$TODAY_LOG" ]; then
    cat > "$TODAY_LOG" << EOF
# Daily Log: ${TODAY}

> Session log for $(date +'%A, %B %d, %Y')

---

## Events & Notes

EOF
    ok "Created today's log."
fi

# --- 8. Configure hooks ---
step 8 "Configuring hooks..."
python3 scripts/configure_hooks.py 2>/dev/null || warn "Hook configuration skipped (non-critical)."

# --- 9. Create start.sh ---
step 9 "Creating start script..."
cat > scripts/start.sh << 'STARTEOF'
#!/bin/bash
# Start IRIS — dashboard + Telegram handler
# Run: bash scripts/start.sh

cd "$(dirname "$0")/.."

echo ""
echo "  Starting IRIS..."
echo ""

# Kill any existing processes on port 5050
lsof -ti:5050 2>/dev/null | xargs kill 2>/dev/null

# Dashboard
python3 dashboard/app.py &
DASH_PID=$!
echo "  Dashboard running at http://localhost:5050 (PID: $DASH_PID)"

# Telegram handler (if token configured)
if grep -q "^TELEGRAM_BOT_TOKEN=" .env 2>/dev/null && \
   ! grep -q "^TELEGRAM_BOT_TOKEN=$" .env 2>/dev/null && \
   ! grep -q '^TELEGRAM_BOT_TOKEN=""' .env 2>/dev/null; then
    python3 .claude/skills/telegram/scripts/telegram_handler.py &
    TG_PID=$!
    echo "  Telegram handler running (PID: $TG_PID)"
else
    echo "  Telegram not configured — skipping handler."
    echo "  Connect via dashboard Settings, then restart."
fi

# Open dashboard in browser
sleep 2
if command -v open &>/dev/null; then
    open "http://localhost:5050"
elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:5050"
fi

echo ""
echo "  IRIS is running."
echo ""
STARTEOF
chmod +x scripts/start.sh
ok "Created scripts/start.sh"

# --- 10. Done ---
step 10 "Setup complete."

echo ""
echo "  ================================"
echo "  IRIS is ready."
echo "  ================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Start IRIS:"
echo "     bash scripts/start.sh"
echo ""
echo "  2. Open in your browser:"
echo "     http://localhost:5050"
echo ""
echo "  3. Set a password, then connect your"
echo "     integrations in Settings."
echo ""
echo "  4. Open Claude Code:"
echo "     claude"
echo ""
echo "  ================================"
echo ""

# Auto-launch if not already running
if ! lsof -ti:5050 &>/dev/null 2>&1; then
    read -p "  Start IRIS now? [Y/n] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        echo ""
        bash scripts/start.sh
    fi
fi
