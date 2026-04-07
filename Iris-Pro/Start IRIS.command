#!/bin/bash
# ============================================================
# IRIS — Double-click to start
# ============================================================

IRIS_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$IRIS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[0;90m'
RESET='\033[0m'

# Ensure common paths are available
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"

clear
echo ""
echo -e "${BOLD}  ┌─────────────────────────────┐${RESET}"
echo -e "${BOLD}  │          I R I S             │${RESET}"
echo -e "${BOLD}  └─────────────────────────────┘${RESET}"
echo ""

# ============================================================
# Dependency checks — guide the user through anything missing
# ============================================================

MISSING=false

# ---- Python 3 (ships with macOS, but just in case) ----
if ! command -v python3 &>/dev/null; then
    echo -e "  ${YELLOW}Python 3 is needed.${RESET}"
    echo -e "  Open Terminal and run: ${CYAN}xcode-select --install${RESET}"
    echo ""
    MISSING=true
fi

# ---- Node.js ----
if ! command -v node &>/dev/null; then
    echo -e "  ${YELLOW}Node.js is needed.${RESET}"
    echo ""
    echo -e "  1. Go to ${CYAN}https://nodejs.org${RESET}"
    echo -e "  2. Click the green ${BOLD}\"Download Node.js (LTS)\"${RESET} button"
    echo -e "  3. Open the downloaded file and follow the installer"
    echo -e "  4. Come back and double-click this file again"
    echo ""
    read -p "  Press Enter to open nodejs.org in your browser..." -r
    open "https://nodejs.org" 2>/dev/null
    MISSING=true
fi

if [ "$MISSING" = true ]; then
    echo ""
    echo -e "  ${DIM}Install what's listed above, then double-click this file again.${RESET}"
    echo ""
    read -p "  Press Enter to close..." -r
    exit 0
fi

# ---- Claude Code CLI ----
if ! command -v claude &>/dev/null; then
    echo -e "  ${DIM}Installing Claude Code...${RESET}"

    # Try without sudo first, then with
    npm install -g @anthropic-ai/claude-code 2>/dev/null
    if ! command -v claude &>/dev/null; then
        echo ""
        echo -e "  ${DIM}Need your Mac password to finish installing:${RESET}"
        sudo npm install -g @anthropic-ai/claude-code 2>/dev/null
    fi

    # Re-check PATH after install
    export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"

    if ! command -v claude &>/dev/null; then
        echo ""
        echo -e "  ${YELLOW}Couldn't install Claude Code automatically.${RESET}"
        echo -e "  Open Terminal and run:"
        echo -e "  ${CYAN}sudo npm install -g @anthropic-ai/claude-code${RESET}"
        echo -e "  Then double-click this file again."
        echo ""
        read -p "  Press Enter to close..." -r
        exit 1
    fi

    echo -e "  ${GREEN}Claude Code installed.${RESET}"
fi

# ============================================================
# First-time setup (runs once, silently)
# ============================================================

if [ ! -f "data/projects.db" ] || [ ! -f ".env" ]; then
    echo ""
    echo -e "  ${DIM}First launch — preparing IRIS...${RESET}"

    # Create directories
    mkdir -p memory/logs data data/capture_markers logs .tmp dashboard/scripts 2>/dev/null

    # Install Python packages quietly
    python3 -m pip install --quiet flask python-dotenv pyyaml requests \
        python-telegram-bot mem0ai upstash-vector 2>/dev/null || \
    pip3 install --quiet --user flask python-dotenv pyyaml requests \
        python-telegram-bot mem0ai upstash-vector 2>/dev/null || true

    # Create .env from template
    if [ ! -f .env ] && [ -f .env.example ]; then
        cp .env.example .env
    fi

    # Initialize databases
    python3 -c "
import sys; sys.path.insert(0, 'dashboard')
from db import init_db; init_db()
" 2>/dev/null

    # Create today's log
    TODAY=$(date +%Y-%m-%d)
    if [ ! -f "memory/logs/${TODAY}.md" ]; then
        cat > "memory/logs/${TODAY}.md" << EOF
# Daily Log: ${TODAY}

> Session log for $(date +'%A, %B %d, %Y')

---

## Events & Notes

EOF
    fi

    echo -e "  ${GREEN}Ready.${RESET}"
fi

# ============================================================
# Launch IRIS
# ============================================================

echo ""
echo -e "  ${BOLD}Starting IRIS...${RESET}"
echo -e "  ${DIM}(This window needs to stay open while IRIS is running)${RESET}"
echo ""

# Launch Claude Code in the IRIS directory
cd "$IRIS_DIR"
claude

# When Claude exits
echo ""
echo -e "  ${DIM}Session ended. You can close this window.${RESET}"
echo ""
read -p "  Press Enter to close..." -r
