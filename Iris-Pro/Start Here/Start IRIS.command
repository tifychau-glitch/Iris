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
echo ""

# ---------------------------------------------------------------
# Step 4: First run — install IRIS
# ---------------------------------------------------------------
if [ ! -f .env ]; then
    echo "  First time? Setting things up..."
    echo ""
    bash install.sh
fi

# ---------------------------------------------------------------
# Step 5: Start background services (dashboard + Telegram)
# ---------------------------------------------------------------
if [ -f start.sh ]; then
    bash start.sh &
    sleep 3
else
    echo "  start.sh not found — running installer..."
    echo ""
    bash install.sh
fi

# ---------------------------------------------------------------
# Step 6: Open Claude Code in a new Terminal window
# ---------------------------------------------------------------
echo ""
echo "  Opening IRIS..."
echo ""
osascript -e "tell application \"Terminal\" to do script \"cd '$IRIS_DIR' && claude\""
