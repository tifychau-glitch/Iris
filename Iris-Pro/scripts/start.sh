#!/bin/bash
# Start IRIS — dashboard + Telegram handler
# Run: bash scripts/start.sh

cd "$(dirname "$0")/.."

echo ""
echo "  Starting IRIS..."
echo ""

# --- PM2 path (Homebrew + nvm + default locations) ---
PM2=""
for candidate in pm2 /opt/homebrew/bin/pm2 /usr/local/bin/pm2 "$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node 2>/dev/null | tail -1)/bin/pm2"; do
  if command -v "$candidate" &>/dev/null 2>&1 || [ -x "$candidate" ]; then
    PM2="$candidate"
    break
  fi
done

# Ensure logs dir exists
mkdir -p logs

if [ -n "$PM2" ]; then
  # ---- PM2 mode (always-on, auto-restarts on crash) ----
  echo "  Using PM2 for process management."

  # Stop any raw processes that may be running
  lsof -ti:5050 2>/dev/null | xargs kill 2>/dev/null
  pkill -f "telegram_handler.py" 2>/dev/null

  "$PM2" start ecosystem.config.js 2>/dev/null || "$PM2" restart ecosystem.config.js
  "$PM2" save

  echo "  Dashboard  → http://localhost:5050"
  echo "  PM2 status → pm2 status"
  echo "  PM2 logs   → pm2 logs"
  echo ""
  echo "  IRIS is running. PM2 will keep it alive automatically."

else
  # ---- Fallback: raw processes ----
  echo "  PM2 not found — running without process manager."
  echo "  Install PM2 for always-on mode: npm install -g pm2"
  echo ""

  # Kill any existing processes
  lsof -ti:5050 2>/dev/null | xargs kill 2>/dev/null
  pkill -f "telegram_handler.py" 2>/dev/null

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

  echo ""
  echo "  IRIS is running. Press Ctrl+C to stop."
  echo ""
  wait
fi
