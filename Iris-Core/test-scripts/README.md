# IRIS Core - Test Scripts

Simple test entry points to validate each piece of the IRIS Core user experience without running the full bot.

## Quick Start

**All commands run from the `Iris-Core` directory:**

```bash
cd /Users/tiffanychau/Downloads/IRIS/Iris-Core
```

Then pick a test and copy-paste the command.

---

## Available Tests

### 1. Bot Conversation Test
Tests a full Mt. Everest excavation conversation with IRIS.

**What it does:**
- Creates a test user
- Simulates opening message
- Runs 5 user inputs through IRIS
- Generates and saves a summary
- Shows upgrade prompt

**Run it:**
```bash
python3 test-scripts/test_bot_conversation.py
```

**What to look for:**
- ✓ Opening message appears
- ✓ IRIS responds to each user input
- ✓ Summary is generated
- ✓ Status shows "completed"

**Typical output:**
```
============================================================
  IRIS CORE - BOT CONVERSATION TEST
============================================================

--- Setup ---
✓ Test database and user created

--- Opening Message ---
• IRIS (opening):
Let's figure out what mountain you're actually climbing...
```

---

### 2. Calendar Generation Test
Tests PNG and ICS file creation from Mt. Everest summary.

**What it does:**
- Parses milestone data from summary
- Generates calendar PNG image
- Generates ICS calendar file
- Saves both to `data/` folder

**Run it:**
```bash
python3 test-scripts/test_calendar.py
```

**What to look for:**
- ✓ Milestones parsed correctly
- ✓ Calendar PNG generated (should be ~10KB+)
- ✓ ICS file generated (should be ~2KB+)
- ✓ Files saved to `data/test_calendar.png` and `data/test_calendar.ics`

**Typical output:**
```
--- Testing Calendar PNG Generation ---
✓ Calendar PNG generated (25342 bytes)
Saved to: .../data/test_calendar.png

--- Testing ICS File Generation ---
✓ ICS file generated (2145 bytes)
Saved to: .../data/test_calendar.ics
```

---

### 3. Email Sending Test
Tests Mt. Everest email delivery with calendar attachments.

**What it does:**
- Checks SMTP configuration (from `.env`)
- Generates calendar PNG and ICS
- Sends test email to `tiffanychau@gmail.com`
- Includes calendar as inline image and ICS as attachment

**Run it:**
```bash
python3 test-scripts/test_email.py
```

**IMPORTANT: Setup first**
Email won't work until you add credentials to `.env`:

```bash
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
```

**How to get app password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your device)
3. Google generates a 16-character password
4. Paste that password as `SMTP_PASSWORD`

**What to look for:**
- If `.env` is missing credentials: ✗ (expected, shows you what to add)
- If credentials are set: ✓ Email sent successfully
- Check your inbox for the test email with calendar attached

**Typical output:**
```
--- Email Configuration Check ---
✓ SMTP configured with user: tiffanychau@gmail.com

--- Sending Email ---
✓ Email sent successfully!
```

---

### 4. Upgrade Prompt Test
Tests the messaging that directs users to IRIS Pro.

**What it does:**
- Generates upgrade prompt variations
- Checks message format
- Verifies URL is included
- Confirms tone is appropriate (not overly salesy)

**Run it:**
```bash
python3 test-scripts/test_upgrade_prompt.py
```

**What to look for:**
- ✓ 3 different upgrade messages generated
- ✓ Each contains the upgrade URL
- ✓ Messages mention "IRIS Pro"
- ✓ Format check passes (natural tone, no hard sell)

**Typical output:**
```
--- Testing Upgrade Messages ---
Generating 3 different upgrade prompts:

--- Upgrade Message 1 ---
Your mountain is defined. Want help climbing it?

IRIS Pro builds your calendar around this goal...
```

---

### 5. Full Journey Test
Runs all tests in sequence to simulate complete user experience.

**What it does:**
- Runs conversation test
- Runs calendar test
- Runs email test
- Runs upgrade test
- Shows pass/fail summary

**Run it:**
```bash
python3 test-scripts/test_full_journey.py
```

**What to look for:**
- All 4 tests show ✓
- Summary shows "ALL TESTS PASSED"

**Typical output:**
```
--- Running: Bot Conversation ---
✓ Bot Conversation passed

--- Running: Calendar Generation ---
✓ Calendar Generation passed

--- Running: Email Sending ---
✓ Email Sending passed

--- Running: Upgrade Prompt ---
✓ Upgrade Prompt passed
```

---

## Test Database

All tests use a **separate test database** so they don't interfere with your real data.

- **Test DB location:** `data/iris_core_test.db`
- **Real DB location:** `data/iris_core.db`

Tests automatically reset the test database each time they run.

**If you want to start fresh:** Just delete `data/iris_core_test.db` and run a test.

---

## Troubleshooting

**Error: "Claude CLI failed" or "Something went wrong on my end"**
- Check that you have `ANTHROPIC_API_KEY` set in `.env`
- Make sure you have the Claude CLI installed (`which claude`)

**Error: "SMTP credentials not configured"**
- Add to `.env`: `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL`
- See Email Sending Test section above for how to get app password

**Error: "Test database locked"**
- Another test is running
- Wait a moment and try again
- Or delete `data/iris_core_test.db` manually

**Email not arriving**
- Check spam folder
- Verify app password is correct (not regular Gmail password)
- Try sending to your own email address

---

## Quick Reference

| Test | Command | What it tests |
|------|---------|--------------|
| Conversation | `python3 test-scripts/test_bot_conversation.py` | IRIS responses, summary generation |
| Calendar | `python3 test-scripts/test_calendar.py` | PNG + ICS file generation |
| Email | `python3 test-scripts/test_email.py` | Email delivery with attachments |
| Upgrade | `python3 test-scripts/test_upgrade_prompt.py` | Upgrade messaging |
| All | `python3 test-scripts/test_full_journey.py` | Complete user experience |

---

## Next Steps

Once all tests pass:
1. Clone this to `Iris-Core-Test` for your permanent test environment
2. Update this folder when you deploy new versions of Iris-Core
3. Run tests whenever you make changes to core functionality

See main `IRIS-Pro/README.md` for how to set up the test clone.
