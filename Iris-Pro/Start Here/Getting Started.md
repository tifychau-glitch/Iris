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

IRIS will walk you through connecting both during setup. You don't need to do anything beforehand.

## If something goes wrong

- **"Node.js is not installed"** — IRIS will open the download page for you. Install it, then double-click Start IRIS again.
- **"Python is not installed"** — Same thing. Install from python.org, then try again.
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
