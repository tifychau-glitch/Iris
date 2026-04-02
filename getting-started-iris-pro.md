# Getting Started with IRIS Pro

If you used IRIS Core, you know her for accountability. IRIS Pro is the full version — she can also create content, manage research, prep meetings, handle emails, build decks, and a lot more.

Here is how to get her running.

---

## What You Need Before You Start

- The IRIS Pro zip file from your purchase
- A Claude Code subscription (download at claude.ai/download if you don't have one yet)
- A Telegram account (free at telegram.org)

---

## Setup Steps

**1. Find the zip file.**
It came with your purchase confirmation. Download it to your computer.

**2. Unzip it.**
On a Mac, just double-click the file. A folder will appear.

**3. Open Claude Code.**
If you don't have it, go to claude.ai/download and install it first.

**4. Open the IRIS Pro folder in Claude Code.**
In Claude Code, open the folder you just unzipped. The whole folder — not a file inside it.

**5. Type "Hi."**
That's it. IRIS will introduce herself and take it from there.

---

## The 3 Things IRIS Needs to Work

IRIS will walk you through each one, step by step. Here is what to expect.

**Connection 1: Anthropic**
This is how IRIS thinks. Go to console.anthropic.com, create a free account, and generate an API key. IRIS will create a file called `.env` on your computer. Open that file in any text editor — TextEdit, VS Code, Notepad, whatever you have — and paste the key next to `ANTHROPIC_API_KEY=`. Save the file.

Do not paste keys into the chat. They go in the `.env` file only.

**Connection 2: Pinecone**
This is how IRIS remembers things across conversations. Go to pinecone.io and sign up for a free account. Get your API key and paste it into the same `.env` file next to `PINECONE_API_KEY=`. Save.

**Connection 3: Telegram**
This is how IRIS reaches you when you step away from your computer. Open Telegram and search for @BotFather. Type `/newbot` and follow the prompts to give your bot a name. BotFather will give you a token. Paste it into the `.env` file next to `TELEGRAM_BOT_TOKEN=`. Save.

---

## Once All 3 Are Connected

IRIS will ask you a few questions about yourself and your business. Answer them in the chat. This is how she learns what you are working on.

After that, she is fully online. She will reach you through Telegram for check-ins and follow-ups. You can also open Claude Code any time to use her skills directly.

---

## What Comes Next

When you are ready, IRIS can connect to more tools — research databases, email, slide builders, and others. Just ask her and she will walk you through it.

---

That is the whole setup. Most people are up and running in under 10 minutes.
