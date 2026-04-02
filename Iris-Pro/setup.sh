#!/bin/bash
# Iris — One-command setup
# Run: chmod +x setup.sh && ./setup.sh

set -e

echo ""
echo "=============================="
echo "  Iris — Setup"
echo "=============================="
echo ""

# 1. Check prerequisites
if ! command -v claude &> /dev/null; then
    echo "[!] Claude Code CLI not found."
    echo "    Install it first: https://docs.anthropic.com/en/docs/claude-code"
    echo "    Then re-run this script."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 not found. Iris needs Python for Telegram and memory."
    echo "    Install: brew install python3 (macOS) or apt install python3 (Linux)"
    exit 1
fi

# 2. Create directories (safe — won't overwrite existing)
echo "[1/7] Creating directories..."
mkdir -p memory/logs
mkdir -p data
mkdir -p data/capture_markers
mkdir -p logs
mkdir -p .tmp

# 3. Install Python dependencies
echo "[2/7] Installing Python dependencies..."
pip3 install --quiet requests python-dotenv pyyaml 2>/dev/null || {
    echo "      pip install failed — trying with --user flag..."
    pip3 install --quiet --user requests python-dotenv pyyaml
}
echo "      Done."

# 4. Create .env from example (if not exists)
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[3/7] Created .env from template — you'll need to add your API keys"
    else
        echo "[3/7] No .env.example found — skipping"
    fi
else
    echo "[3/7] .env already exists — skipping"
fi

# 5. Create settings.local.json from example (if not exists)
if [ ! -f .claude/settings.local.json ]; then
    if [ -f .claude/settings.local.json.example ]; then
        cp .claude/settings.local.json.example .claude/settings.local.json
        echo "[4/7] Created .claude/settings.local.json from template"
    else
        echo "[4/7] No settings template found — skipping"
    fi
else
    echo "[4/7] .claude/settings.local.json already exists — skipping"
fi

# 6. Create today's daily log (if not exists)
TODAY=$(date +%Y-%m-%d)
TODAY_LOG="memory/logs/${TODAY}.md"
if [ ! -f "$TODAY_LOG" ]; then
    cat > "$TODAY_LOG" << EOF
# Daily Log: ${TODAY}

> Session log for $(date +'%A, %B %d, %Y')

---

## Events & Notes

EOF
    echo "[5/7] Created today's log: ${TODAY_LOG}"
else
    echo "[5/7] Today's log already exists — skipping"
fi

# 7. Check for optional memory upgrade
echo "[6/7] Checking optional upgrades..."
if [ -f setup_memory.py ]; then
    echo "      Advanced memory available (mem0 + Pinecone)"
    echo "      Iris will walk you through this during setup."
else
    echo "      No optional upgrades found."
fi

# 8. Print next steps
echo "[7/7] Setup complete!"
echo ""
echo "=============================="
echo "  Before You Start"
echo "=============================="
echo ""
echo "  You'll need three things:"
echo ""
echo "  1. Anthropic API key"
echo "     (for Iris to think)"
echo ""
echo "  2. Pinecone API key"
echo "     (for long-term memory)"
echo ""
echo "  3. Telegram bot token"
echo "     (so Iris can reach you)"
echo ""
echo "  Add your API keys to .env now,"
echo "  or Iris will walk you through it."
echo ""
echo "=============================="
echo ""
echo "  Ready? Run:"
echo "  claude"
echo ""
echo "  Then just say hi."
echo ""
echo "=============================="
echo ""
