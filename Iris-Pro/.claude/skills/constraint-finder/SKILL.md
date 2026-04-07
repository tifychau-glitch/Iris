---
name: constraint-finder
description: Diagnoses the real bottleneck behind missed commitments — clarity, task sizing, emotional resistance, energy, calendar mismatch, perfectionism, or decision overload. Uses accountability data to identify patterns, then delivers a diagnosis in Iris's voice.
model: sonnet
---

# Constraint Finder

Most people think their problem is discipline. Usually it isn't.

This skill reads accountability data (excuse categories, time-of-day patterns, avoidance categories) and diagnoses the actual constraint. The data collection is deterministic (Python script). The interpretation uses AI to deliver it in Iris's voice.

## When to Use

- User keeps missing commitments and doesn't know why
- Weekly review reveals a pattern
- User says "I don't know what's wrong" or "I keep failing"
- After 7+ days of data in the accountability engine

## How It Works

1. `diagnose.py` pulls structured data from `iris_accountability.db`
2. Script classifies the constraint based on data patterns
3. Iris interprets the diagnosis and delivers it conversationally

## Run Diagnosis

```bash
python3 .claude/skills/constraint-finder/scripts/diagnose.py
```

Returns JSON with:
- `primary_constraint` — the main bottleneck type
- `confidence` — how confident the diagnosis is (based on data volume)
- `evidence` — the specific data points that led to this conclusion
- `suggestion` — a concrete next step

## Constraint Types

| Type | Pattern Signal |
|------|---------------|
| `clarity` | >40% of missed tasks have category 'unclear_task' |
| `sizing` | High promise count but low completion across categories |
| `avoidance` | >40% excuse category is 'avoidance', same categories repeat |
| `energy` | Completions cluster in AM, misses cluster in PM (or vice versa) |
| `calendar` | High commitment count + low completion = overcommitted |
| `perfectionism` | Tasks get completed but very late, or started but not finished |
| `decision_overload` | Many pending/open commitments simultaneously |

## Rules

- Minimum 7 days of data before running diagnosis (less = unreliable)
- Present as observation, not judgment: "The data says X" not "You have a problem with X"
- Always include a concrete next step, not just the diagnosis
- This is where AI earns its keep — the script collects data, Iris interprets it
