# Skills Guide

How to create custom skills for your AI OS.

## What is a Skill?

A skill is a self-contained workflow package in `.claude/skills/`. Each skill folder contains:

```
.claude/skills/my-skill/
├── SKILL.md          # Process definition (the instructions)
├── scripts/          # Python execution scripts (optional)
├── references/       # Supporting documentation (optional)
└── assets/           # Templates, fonts, icons (optional)
```

Skills are auto-discovered by Claude based on their description. When you ask Claude to do something, it checks all skill descriptions to find a match.

## Creating a Skill

The easiest way: use the skill-creator.

```
"Create a skill for [describe your workflow]"
```

Or manually:

```bash
python3 .claude/skills/skill-creator/scripts/init_skill.py my-skill-name
```

## Skill Anatomy

### Frontmatter (YAML header)

```yaml
---
name: my-skill
description: What this skill does. Use when user says "trigger 1", "trigger 2".
model: sonnet
context: fork
user-invocable: true
---
```

| Field | Purpose | Default |
|-------|---------|---------|
| `name` | Skill identifier (kebab-case) | Required |
| `description` | What it does + when to use it (max 1024 chars) | Required |
| `model` | Which Claude model runs it (opus/sonnet/haiku) | Inherits parent |
| `context` | `fork` runs as isolated subagent | None (runs inline) |
| `allowed-tools` | Restrict which tools the skill can use | All tools |
| `user-invocable` | Can be triggered via /name | false |
| `disable-model-invocation` | Can't auto-trigger, only manual /name | false |

### Body (Markdown)

Write the body as an imperative SOP (standard operating procedure):

1. **Objective** — One sentence: what does this achieve?
2. **Inputs** — What does it need?
3. **Steps** — In order, with script commands and expected outputs
4. **Edge cases** — What can go wrong and how to handle it

Keep under 500 lines. Move detailed docs to `references/`.

## Writing Good Descriptions

The description is Claude's only clue about whether to use your skill.

**Good:**
```yaml
description: Transform a LinkedIn URL into a research package with personalized
  outreach. Run with /research-lead or ask to research a lead.
```

**Bad:**
```yaml
description: Helps with research.
```

Formula: `[What it does] + [Use when user says "X", "Y", "Z"]`

## Script Pattern

Every Python script should:
- Have ONE job
- Accept input via CLI args
- Return JSON to stdout
- Return errors to stderr
- Handle its own errors

```python
#!/usr/bin/env python3
"""One-sentence description."""

import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    args = parser.parse_args()

    try:
        result = {"success": True, "data": {}}
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Model Routing

Route skills to cheaper models when Opus-level reasoning isn't needed:

| Model | Cost | Use For |
|-------|------|---------|
| `haiku` | Cheapest | Simple lookups, classification, formatting |
| `sonnet` | Balanced | Most automated pipelines (default) |
| `opus` | Most capable | Complex reasoning, creative work, architecture |

## Examples

See the 14 built-in skills for real examples:
- `iris-setup` — Conversational wizard (instruction-only)
- `research-lead` — Full pipeline (9 scripts, parallel execution)
- `build-website` — Creative framework (instruction-only, opus)
- `task-manager` — Database CRUD (single script)
- `gamma-slides` — API wrapper (single script)
