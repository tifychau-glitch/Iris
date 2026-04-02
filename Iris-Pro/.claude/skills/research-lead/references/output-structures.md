# Expected Output Structures

JSON structures for each analysis type in the research-lead pipeline.

## Lead Profile

```json
{
  "person_profile": "Single paragraph summary",
  "company_profile": "Single paragraph company overview",
  "operational_focus": ["scaling challenges they discuss", "ops topics they post about"],
  "operational_achievements": [
    {
      "achievement": "Scaled RevOps team from 2 to 15 in 18 months",
      "source": "LinkedIn experience section"
    }
  ]
}
```

`operational_achievements` only includes building/scaling/transforming accomplishments. No hobbies, awards, or theater.

## Pain & Gain (Operational)

```json
{
  "quick_brief": {
    "one_line": "Role at company showing key signal",
    "primary_pain": "Biggest operational dysfunction",
    "ai_risk": "Risk if they automate without diagnosing"
  },
  "scale_complexity": [...],
  "internal_operational_gaps": [...],
  "ai_transformation_signals": [...],
  "pattern_interrupt_hooks": [
    {
      "id": "hook_01",
      "type": "hiring",
      "fact": "Hiring 3 RevOps roles",
      "evidence": "LinkedIn job posts",
      "op_angle": "Hiring this many ops roles signals pipeline/data chaos",
      "allowed": true,
      "why_allowed": "Grounded in hiring evidence, operational relevance"
    },
    {
      "id": "hook_02",
      "type": "leader_fact",
      "fact": "Went to USC",
      "evidence": "LinkedIn education",
      "op_angle": "Shared education",
      "allowed": false,
      "why_allowed": "Weak personal trivia — not operational"
    }
  ],
  "archetype_classification": {
    "primary_archetype": "Declared Change | Active Execution | Latent Operational Friction",
    "reasoning": "...",
    "confidence": "high | medium | low"
  }
}
```

DM generation ONLY uses hooks where `allowed: true`. This filters out theater automatically.

## DM Sequence

```json
{
  "archetype": "Declared Change",
  "hook_selected": {
    "id": "hook_01",
    "type": "hiring",
    "fact": "Hiring 3 RevOps roles"
  },
  "dm1": {
    "message": "Max 300 characters",
    "character_count": 250
  },
  "dm2": {
    "message": "Max 300 characters",
    "character_count": 280
  },
  "dm3": {
    "message": "Max 300 characters",
    "character_count": 290
  }
}
```
