#!/bin/bash
# Start IRIS — double-click this file to launch
# Works on macOS. For Windows, use "Start IRIS.bat" instead.

cd "$(dirname "$0")"

# First run? Install first.
if [ ! -f .env ]; then
    echo ""
    echo "  ================================"
    echo "  First time? Let's set up IRIS."
    echo "  ================================"
    echo ""
    bash install.sh
    exit $?
fi

# Already installed — start IRIS
if [ -f start.sh ]; then
    bash start.sh
else
    # start.sh missing (older install) — run install to regenerate it
    echo ""
    echo "  start.sh not found — running installer to fix..."
    echo ""
    bash install.sh
fi
