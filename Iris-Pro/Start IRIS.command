#!/bin/bash
# Start IRIS — double-click this file to launch
# Works on macOS. For Windows, use "Start IRIS.bat" instead.

IRIS_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$IRIS_DIR"

# First run? Install first.
if [ ! -f .env ]; then
    echo ""
    echo "  ================================"
    echo "  First time? Let's set up IRIS."
    echo "  ================================"
    echo ""
    bash install.sh
fi

# Start background services (dashboard + Telegram)
if [ -f start.sh ]; then
    bash start.sh &
    sleep 3
else
    echo ""
    echo "  start.sh not found — running installer to fix..."
    echo ""
    bash install.sh
fi

# Open Claude Code in a new Terminal window
echo ""
echo "  Opening IRIS conversation..."
echo ""
osascript -e "tell application \"Terminal\" to do script \"cd '$IRIS_DIR' && claude\""
