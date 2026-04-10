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

"Start IRIS" checks three things in order. If any are missing, it tries to install them automatically. If auto-install doesn't work, it opens the download page and tells you exactly what to do.

1. **Git** — Mac usually has it. On Windows, IRIS tries to install it automatically. If it can't, it opens the download page. Use all default settings and restart your computer after.
2. **Python** — Mac usually has it. On Windows, IRIS tries to install it automatically. If it can't, it opens the download page. **The most important thing: on the first screen of the Python installer, check the box at the bottom that says "Add python.exe to PATH."** If you miss this, IRIS can't find Python even though it's installed. At the end of the installer, click "Disable path length limit" if it appears — that's safe and prevents issues later.
3. **Claude Code** — installed automatically (no action needed from you). Uses the native installer from Anthropic.

After installing anything, just double-click "Start IRIS" again. It picks up where it left off.

## If something goes wrong

- **"Git is not installed"** — Download from the page that opens, install with default settings, restart your computer, try again.
- **"Python is not installed"** — Download from the page that opens. **Check "Add to PATH"** on the first screen. Click "Disable path length limit" at the end. Try again.
- **Python is installed but IRIS says it's not** — You probably missed the "Add to PATH" checkbox. Uninstall Python, reinstall, and this time check that box on the first screen.
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
