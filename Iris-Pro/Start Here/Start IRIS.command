#!/bin/bash
# Start IRIS — double-click this file to launch
# Works on macOS. For Windows, use "Start IRIS.bat" instead.

# Navigate to the Iris-Pro root (one level up from "Start Here/")
IRIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$IRIS_DIR"

echo ""
echo "  ================================"
echo "  IRIS — Starting up"
echo "  ================================"
echo ""

# ---------------------------------------------------------------
# Step 1: Check for Git
# ---------------------------------------------------------------
# macOS usually has git via Xcode Command Line Tools. If not,
# running git triggers the installer dialog automatically.
if ! command -v git &>/dev/null; then
    echo "  Git is not installed. macOS will prompt you to install it now..."
    echo ""
    # This triggers the Xcode CLT install dialog on macOS
    xcode-select --install 2>/dev/null
    echo ""
    echo "  A dialog should have appeared to install developer tools."
    echo "  Once it finishes, double-click 'Start IRIS' again."
    echo ""
    read -p "  Press Enter to exit..." -r
    exit 1
fi

# ---------------------------------------------------------------
# Step 2: Check for Python
# ---------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    echo "  Python 3 is not installed."
    echo ""
    echo "  The easiest way to install it on Mac:"
    echo "  1. The developer tools dialog should have installed it."
    echo "  2. If not, download from python.org (opening it now...)"
    echo ""
    open "https://python.org"
    echo "  After installing Python, double-click 'Start IRIS' again."
    echo ""
    read -p "  Press Enter to exit..." -r
    exit 1
fi

# ---------------------------------------------------------------
# Step 3: Check for Claude Code
# ---------------------------------------------------------------
if ! command -v claude &>/dev/null; then
    echo "  Claude Code is not installed yet."
    echo "  Installing now..."
    echo ""

    # Try 1: Native installer (recommended by Anthropic)
    if curl -fsSL https://claude.ai/install.sh | bash 2>&1; then
        # Refresh PATH so we can find claude immediately
        export PATH="$HOME/.claude/bin:$HOME/.local/bin:$PATH"
    fi

    # Check if it worked
    if command -v claude &>/dev/null; then
        echo ""
        echo "  Claude Code installed!"
        echo ""
    else
        # Try 2: npm fallback (if user has Node.js from a previous setup)
        if command -v npm &>/dev/null; then
            echo ""
            echo "  Native installer didn't work. Trying npm..."
            echo ""
            npm install -g @anthropic-ai/claude-code 2>&1

            if command -v claude &>/dev/null; then
                echo ""
                echo "  Claude Code installed via npm!"
                echo ""
            fi
        fi

        # Final check
        if ! command -v claude &>/dev/null; then
            echo ""
            echo "  Could not install Claude Code automatically."
            echo ""
            echo "  Please install it manually:"
            echo "  1. Open Terminal"
            echo "  2. Paste: curl -fsSL https://claude.ai/install.sh | bash"
            echo "  3. Double-click 'Start IRIS' again"
            echo ""
            echo "  Or visit: https://claude.ai/download"
            echo ""
            read -p "  Press Enter to exit..." -r
            exit 1
        fi
    fi
fi

echo "  ✓ Git installed"
echo "  ✓ Python installed"
echo "  ✓ Claude Code installed"

# ---------------------------------------------------------------
# Step 4: Check Python dependencies (Flask, etc.)
# ---------------------------------------------------------------
if ! python3 -c "import flask" &>/dev/null; then
    echo ""
    echo "  Installing Python dependencies..."
    python3 -m pip install --quiet flask python-dotenv pyyaml requests python-telegram-bot 2>/dev/null || \
    python3 -m pip install --quiet --user flask python-dotenv pyyaml requests python-telegram-bot 2>/dev/null
    if python3 -c "import flask" &>/dev/null; then
        echo "  ✓ Dependencies installed"
    else
        echo "  [!] Could not install Flask. The dashboard may not start."
        echo "  Try running: python3 -m pip install flask"
    fi
else
    echo "  ✓ Dependencies installed"
fi
echo ""

# ---------------------------------------------------------------
# Step 5: First run — install IRIS
# ---------------------------------------------------------------
if [ ! -f .iris-installed ]; then
    echo "  First time? Setting things up..."
    echo ""
    # Ensure .env exists
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            echo "  Created .env from template."
        else
            touch .env
            echo "  Created empty .env file."
        fi
    fi
    bash install.sh
    echo "installed" > .iris-installed
fi

# ---------------------------------------------------------------
# Step 5: Start dashboard + Telegram in background
# ---------------------------------------------------------------

# Kill any existing dashboard on port 5050
lsof -ti:5050 2>/dev/null | xargs kill 2>/dev/null

# Start dashboard
python3 dashboard/app.py &
echo "  ✓ Dashboard starting..."

# Start Telegram handler if configured
if grep -q "^TELEGRAM_BOT_TOKEN=" .env 2>/dev/null && \
   ! grep -q "^TELEGRAM_BOT_TOKEN=$" .env 2>/dev/null && \
   ! grep -q '^TELEGRAM_BOT_TOKEN=""' .env 2>/dev/null; then
    python3 .claude/skills/telegram/scripts/telegram_handler.py &
    echo "  ✓ Telegram handler starting..."
fi

# Wait for dashboard to be ready, then open browser
sleep 2
open "http://localhost:5050"
echo "  ✓ Dashboard opened in browser"

# ---------------------------------------------------------------
# Step 6: Open Claude Code
# ---------------------------------------------------------------

# Prefer Claude desktop app (cleaner chat UI) over terminal
if [ -d "/Applications/Claude.app" ]; then
    open -a "Claude"
    echo ""
    echo "  ================================"
    echo "  IRIS is ready."
    echo "  ================================"
    echo ""
    echo "  The dashboard opened in your browser."
    echo "  Claude is opening — click the Code tab,"
    echo "  select this folder as your project:"
    echo "    $IRIS_DIR"
    echo ""
    echo "  Then type your first message to IRIS."
    echo ""
else
    # No desktop app — open Claude Code in a new Terminal window
    osascript -e "tell application \"Terminal\" to do script \"cd '$IRIS_DIR' && claude\""
    echo ""
    echo "  ================================"
    echo "  IRIS is ready."
    echo "  ================================"
    echo ""
    echo "  Dashboard: http://localhost:5050"
    echo "  IRIS conversation opened in a new window."
    echo ""
fi
