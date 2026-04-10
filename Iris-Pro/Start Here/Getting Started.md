# Getting Started with IRIS

## Step 1: Double-click "Start IRIS"

- **Mac:** Double-click `Start IRIS.command`
- **Windows:** Double-click `Start IRIS.bat`

That's it. IRIS handles the rest.

## What happens when you click it

**First time:**
1. Checks if Claude Code is installed (installs it if needed)
2. Installs IRIS dependencies
3. Opens the dashboard in your browser
4. Opens IRIS in a terminal window
5. IRIS introduces herself and walks you through setup (~10 minutes)

**Every time after:**
1. Starts the dashboard + Telegram handler
2. Opens IRIS in a terminal window
3. Pick up where you left off

## What you'll need

- **A Claude Code subscription** ($20/month from claude.ai)
- **A Telegram account** (free — IRIS uses this to check in with you outside the computer)

You don't need to install anything manually. "Start IRIS" checks for everything and either installs it automatically or opens the download page for you. Just follow the prompts.

## If something needs to be installed

"Start IRIS" checks three things in order. If any are missing, it helps you install them:

1. **Git** — Mac usually has it. Windows doesn't — the installer opens the download page and tells you to restart your computer after.
2. **Python** — Mac usually has it. Windows users may need to download it — make sure to check "Add to PATH" during the install.
3. **Claude Code** — installed automatically (no action needed from you). Uses the native installer from Anthropic, falls back to npm if needed.

After installing anything, just double-click "Start IRIS" again. It picks up where it left off.

## If something goes wrong

- **"Git is not installed"** — Download from the page that opens, install, restart your computer, try again.
- **"Python is not installed"** — Download from the page that opens. Check "Add to PATH". Try again.
- **"Could not install Claude Code"** — Follow the manual instructions shown on screen, or visit claude.ai/download.
- **Dashboard won't open** — Try going to http://localhost:5050 in your browser manually.
- **Telegram isn't responding** — Make sure you completed the Telegram setup in the dashboard Settings page.

## What's in this folder

You only need to care about one thing: **Start IRIS**. Everything else is internal.

If you're curious:
- `Start IRIS` — the one button you click
- `IRIS.md` — IRIS's operating manual (you don't need to read this)
- `dashboard/` — the web dashboard code
- `context/` — your business profile (filled in during setup)
- `memory/` — IRIS's memory of your conversations
