# Automation Guide

Schedule skills to run automatically using Claude Code's headless mode.

## Headless Mode

Run any skill without an interactive session:

```bash
# Run a skill
claude -p "/weekly-review" --output-format json

# Run with custom input
claude -p "/research-lead https://linkedin.com/in/someone" --output-format json

# Run with a natural language prompt
claude -p "Give me my morning briefing" --output-format json
```

## Scheduling with Cron

### macOS (launchctl)

Create a plist file at `~/Library/LaunchAgents/com.aios.weekly-review.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aios.weekly-review</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/claude</string>
        <string>-p</string>
        <string>/weekly-review</string>
        <string>--output-format</string>
        <string>json</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/your/ai-os</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/your/ai-os/data/weekly-review.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/your/ai-os/data/weekly-review-error.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.aios.weekly-review.plist
```

### Linux/macOS (crontab)

```bash
crontab -e
```

Example schedules:

```bash
# Weekly review every Monday at 9am
0 9 * * 1 cd /path/to/ai-os && claude -p "/weekly-review" --output-format json >> data/cron.log 2>&1

# Daily email digest at 7am
0 7 * * * cd /path/to/ai-os && claude -p "/email-digest" --output-format json >> data/cron.log 2>&1

# Morning briefing at 7:30am weekdays
30 7 * * 1-5 cd /path/to/ai-os && claude -p "Give me my morning briefing" --output-format json >> data/cron.log 2>&1
```

## Batch Processing

### Fan-Out Pattern

Process multiple items in parallel:

```bash
#!/bin/bash
# batch_research.sh — Research multiple leads in parallel
while IFS= read -r url; do
    claude -p "/research-lead $url" --output-format json >> data/batch-results.json &
done < leads.txt
wait
echo "All leads processed"
```

### Sequential Pattern

Process items one at a time (when order matters or API rate limits apply):

```bash
#!/bin/bash
# sequential_process.sh
while IFS= read -r url; do
    claude -p "/research-lead $url" --output-format json >> data/batch-results.json
    sleep 5  # Rate limit buffer
done < leads.txt
```

## Recommended Schedules

| Skill | Frequency | Time | Notes |
|-------|-----------|------|-------|
| email-digest | Daily | 7:00 AM | Before you start working |
| weekly-review | Weekly | Monday 9:00 AM | Start the week informed |
| task-manager stats | Daily | 6:00 PM | End-of-day summary |

## Tips

- Always use `--output-format json` for programmatic output
- Log output to `data/` for debugging
- Test manually first: `claude -p "/skill-name"` before scheduling
- Use `cd /path/to/ai-os &&` to ensure the right working directory
- Set environment variables in the cron environment or use the full path to `.env`
