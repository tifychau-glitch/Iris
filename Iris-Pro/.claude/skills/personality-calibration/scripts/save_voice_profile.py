#!/usr/bin/env python3
"""
Save, read, and update iris_voice_profile on core-state.json.

Voice profile is the single stable personality Iris uses with this user.
Runtime mode flex (gentle/steady/direct) is handled elsewhere.

Usage:
    save_voice_profile.py --setup-complete --directness-ceiling moderate \\
        --win-acknowledgment named_directly --shutdowns "shame,vague_feedback" \\
        --motivators "truth,progress" --swearing-ok true \\
        --assessments "Enneagram: 3w4"

    save_voice_profile.py --observe humor playful
    save_voice_profile.py --observe slip_handling name_it
    save_voice_profile.py --get
    save_voice_profile.py --reset
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_STATE_PATH = REPO_ROOT / "memory" / "core-state.json"

DEFERRED_FIELDS = ["humor", "slip_handling", "decision_style", "open_feedback"]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load():
    with open(CORE_STATE_PATH) as f:
        return json.load(f)


def _save(state):
    state["_meta"]["version"] = state["_meta"].get("version", 0) + 1
    state["_meta"]["last_updated_at"] = _now()
    state["_meta"]["last_confirmed_at"] = _now()
    state["_meta"]["source_of_last_write"] = "user_explicit"
    with open(CORE_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def _parse_list(raw):
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def cmd_setup_complete(args):
    state = _load()
    profile = {
        "directness_ceiling": args.directness_ceiling,
        "win_acknowledgment": args.win_acknowledgment,
        "shutdowns": _parse_list(args.shutdowns),
        "motivators": _parse_list(args.motivators),
        "swearing_ok": args.swearing_ok.lower() == "true",
        "assessments": [x.strip() for x in args.assessments.split("|") if x.strip()] if args.assessments else [],
        "warmth": args.warmth or "warm",
        "humor": "unknown",
        "decision_style": "unknown",
        "mode_triggers": {
            "gentle": ["venting", "illness", "overwhelm_language"],
            "direct": ["repeat_slips_3plus", "user_invited_honesty"],
        },
        "notes": args.notes or "",
        "calibration_progress": {
            "setup_complete": True,
            "pending_observations": list(DEFERRED_FIELDS),
            "first_conversation_at": _now(),
            "conversation_count": 0,
        },
        "last_calibrated_at": _now(),
    }
    state["iris_voice_profile"] = profile
    _save(state)
    print(json.dumps(profile, indent=2))


def cmd_observe(args):
    field, value = args.observe
    if field not in DEFERRED_FIELDS:
        print(f"Error: '{field}' is not a deferred field. Must be one of {DEFERRED_FIELDS}", file=sys.stderr)
        sys.exit(1)
    state = _load()
    profile = state.get("iris_voice_profile")
    if not profile:
        print("Error: no iris_voice_profile exists. Run --setup-complete first.", file=sys.stderr)
        sys.exit(1)

    if field == "open_feedback":
        existing = profile.get("notes", "")
        profile["notes"] = (existing + "\n" + value).strip() if existing else value
    else:
        profile[field] = value

    pending = profile.setdefault("calibration_progress", {}).setdefault("pending_observations", [])
    if field in pending:
        pending.remove(field)
    profile["last_calibrated_at"] = _now()
    _save(state)
    print(json.dumps({"field": field, "value": value, "pending_remaining": pending}, indent=2))


def cmd_get(_args):
    state = _load()
    profile = state.get("iris_voice_profile")
    if not profile:
        print("{}")
        return
    print(json.dumps(profile, indent=2))


def cmd_reset(_args):
    state = _load()
    if "iris_voice_profile" in state:
        del state["iris_voice_profile"]
        _save(state)
    print('{"status": "reset"}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--setup-complete", action="store_true")
    p.add_argument("--observe", nargs=2, metavar=("FIELD", "VALUE"))
    p.add_argument("--get", action="store_true")
    p.add_argument("--reset", action="store_true")

    p.add_argument("--directness-ceiling", choices=["soft", "moderate", "blunt"])
    p.add_argument("--win-acknowledgment", choices=["named_directly", "quietly_noted", "situational"])
    p.add_argument("--warmth", choices=["warm", "neutral", "reserved"])
    p.add_argument("--shutdowns", type=str, help="Comma-separated")
    p.add_argument("--motivators", type=str, help="Comma-separated")
    p.add_argument("--swearing-ok", type=str, choices=["true", "false"])
    p.add_argument("--assessments", type=str, help="Pipe-separated (use | between assessments, since entries contain commas)")
    p.add_argument("--notes", type=str)

    args = p.parse_args()

    if args.setup_complete:
        required = ["directness_ceiling", "win_acknowledgment", "swearing_ok"]
        missing = [r for r in required if getattr(args, r) is None]
        if missing:
            print(f"Error: --setup-complete requires {missing}", file=sys.stderr)
            sys.exit(1)
        cmd_setup_complete(args)
    elif args.observe:
        cmd_observe(args)
    elif args.get:
        cmd_get(args)
    elif args.reset:
        cmd_reset(args)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
