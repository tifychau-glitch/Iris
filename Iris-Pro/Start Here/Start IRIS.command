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

# --- Check for Claude Code ---
if ! command -v claude &>/dev/null; then
    echo "  Claude Code is not installed yet."
    echo ""

    # Check if Node.js is available
    if command -v node &>/dev/null && command -v npm &>/dev/null; then
        echo "  Node.js found. Installing Claude Code..."
        echo ""
        npm install -g @anthropic-ai/claude-code 2>&1
        if command -v claude &>/dev/null; then
            echo ""
            echo "  Claude Code installed!"
            echo ""
        else
            echo ""
            echo "  [!] Install failed. Try running this manually:"
            echo "      sudo npm install -g @anthropic-ai/claude-code"
            echo ""
            echo "  Then double-click 'Start IRIS' again."
            echo ""
            read -p "  Press Enter to exit..." -r
            exit 1
        fi
    else
        echo "  To install Claude Code, you need Node.js first."
        echo ""
        echo "  Here's what to do:"
        echo "  1. Go to nodejs.org (opening it now...)"
        echo "  2. Download and install the LTS version"
        echo "  3. Double-click 'Start IRIS' again"
        echo ""
        open "https://nodejs.org"
        echo "  After installing Node.js, come back and"
        echo "  double-click 'Start IRIS' again."
        echo ""
        read -p "  Press Enter to exit..." -r
        exit 1
    fi
fi

# --- Check for Claude Code subscription ---
# claude handles its own auth — if not logged in, it'll prompt on launch

# --- First run? Install first. ---
if [ ! -f .env ]; then
    echo "  First time? Setting things up..."
    echo ""
    bash install.sh
fi

# --- Start background services (dashboard + Telegram) ---
if [ -f start.sh ]; then
    bash start.sh &
    sleep 3
else
    echo "  start.sh not found — running installer..."
    echo ""
    bash install.sh
fi

# --- Open Claude Code in a new Terminal window ---
echo ""
echo "  Opening IRIS..."
echo ""
osascript -e "tell application \"Terminal\" to do script \"cd '$IRIS_DIR' && claude\""
