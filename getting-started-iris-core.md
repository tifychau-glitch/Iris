# Getting Started with IRIS Core

IRIS is ready to go. You just need to set a few things up first — it takes about 10 minutes, and IRIS walks you through most of it.

---

## What You Need Before You Start

- The IRIS Core zip file from your purchase
- A Claude Code subscription (download at claude.ai/download if you don't have one yet)
- A Telegram account

That's it. Everything else, IRIS will explain as you go.

---

## Setup Steps

**1. Find the zip file.**
It was attached to your purchase confirmation or download page. It should be in your Downloads folder.

**2. Unzip it.**
On a Mac, double-click the zip file. A new folder called IRIS Core will appear.

**3. Open Claude Code.**
If you already have it, great. If not, download it at claude.ai/download and install it.

**4. Open the IRIS Core folder in Claude Code.**
In Claude Code, go to File > Open Folder and select the IRIS Core folder you just unzipped.

**5. Say hi.**
In the chat at the bottom, type "Hi" and hit enter. IRIS will introduce herself and take it from there.

---

## What IRIS Will Walk You Through

IRIS connects to 3 services. She'll guide you through each one, in order.

**Connection 1: Anthropic**
This is how IRIS thinks.

- Go to console.anthropic.com
- Create an account and generate an API key
- IRIS will create a file called `.env` in your folder
- Open that file with any text editor (TextEdit, VS Code, Notepad — anything works)
- Paste your key next to `ANTHROPIC_API_KEY=` and save

**Connection 2: Pinecone**
This is how IRIS remembers things over time.

- Go to pinecone.io
- Create a free account and grab your API key
- Open the `.env` file again
- Paste your key next to `PINECONE_API_KEY=` and save

**Connection 3: Telegram**
This is how IRIS reaches you for check-ins.

- Open Telegram on your phone or desktop
- Search for @BotFather
- Type `/newbot` and follow the prompts to name your bot
- Copy the token BotFather gives you at the end
- Open the `.env` file again
- Paste your token next to `TELEGRAM_BOT_TOKEN=` and save

One important note: paste your keys into the `.env` file only. Do not paste them into the chat. The chat sends messages to a server. The `.env` file stays on your computer.

---

## After Setup

Once all 3 connections are live, IRIS will ask you a few questions. What you're working on. What you're trying to change. What you keep putting off.

After that, she moves to Telegram. That's where your daily check-ins happen going forward.

---

## Stuck?

If something is not working, the most common fix is double-checking that each key was pasted correctly in the `.env` file with no extra spaces. IRIS will also let you know if something did not connect properly.
