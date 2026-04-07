# Getting Started with IRIS

## 3 Steps

### 1. Install Node.js (if you don't have it)

Go to [nodejs.org](https://nodejs.org) and click the green **"Download Node.js (LTS)"** button. Open the downloaded file and follow the installer.

### 2. Start IRIS

**Mac:** Right-click `Start IRIS.command` and select **Open**.
> The first time, macOS may show a warning. Click **Open** to allow it. This only happens once.

**Windows:** Double-click `Start IRIS.bat`.
> If Windows asks about running scripts, click **Run anyway**.

IRIS will install everything it needs automatically. This takes about a minute on the first launch.

### 3. Talk to IRIS

IRIS will introduce herself and walk you through setup. She'll ask about you, your business, and connect your integrations.

That's it. After setup, just double-click `Start IRIS` whenever you want to use IRIS.

---

## What You'll Need During Setup

IRIS will walk you through each of these — you don't need to prepare anything in advance:

- **Telegram** — IRIS reaches you here when you're away. She'll help you create a bot.
- **Upstash** (free) — This is how IRIS remembers things long-term. Free tier works.
- **OpenAI API** ($5 minimum) — Powers IRIS's memory system. Not a subscription — you pay pennies per use.

## Need Help?

**Mac:** If the launcher doesn't work, open Terminal and run:
```
cd ~/Downloads/Iris-Pro && bash install.sh
```

**Windows:** If the launcher doesn't work, open PowerShell and run:
```
cd ~\Downloads\Iris-Pro; powershell -ExecutionPolicy Bypass -File install.ps1
```

Then run:

```
claude
```
