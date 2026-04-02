"""
Tool: Weekly Metrics Parser
Purpose: Parse daily log files from the past 7 days and extract patterns.
Usage: python3 scripts/weekly_metrics.py [--days 7] [--logs-dir ../../memory/logs]
"""

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_LOGS_DIR = Path(__file__).parent.parent.parent.parent.parent / "memory" / "logs"


def parse_log_file(path: Path) -> dict:
    """Parse a single daily log file and extract structure."""
    if not path.exists():
        return None

    content = path.read_text()
    lines = content.strip().split("\n")

    events = []
    current_section = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:]
        elif stripped.startswith("- ") and current_section:
            events.append({
                "section": current_section,
                "content": stripped[2:]
            })

    return {
        "date": path.stem,
        "events": events,
        "event_count": len(events),
        "sections": list(set(e["section"] for e in events)),
        "raw_length": len(content)
    }


def analyze_week(logs_dir: Path, days: int = 7) -> dict:
    """Analyze the past N days of logs."""
    today = datetime.now()
    results = {
        "period": {
            "start": (today - timedelta(days=days-1)).strftime("%Y-%m-%d"),
            "end": today.strftime("%Y-%m-%d")
        },
        "days_with_logs": 0,
        "days_without_logs": 0,
        "total_events": 0,
        "daily_breakdown": [],
        "missing_days": [],
        "all_events": []
    }

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        log_path = logs_dir / f"{date_str}.md"

        parsed = parse_log_file(log_path)
        if parsed:
            results["days_with_logs"] += 1
            results["total_events"] += parsed["event_count"]
            results["daily_breakdown"].append(parsed)
            results["all_events"].extend(
                {"date": date_str, **e} for e in parsed["events"]
            )
        else:
            results["days_without_logs"] += 1
            results["missing_days"].append(date_str)

    # Extract common themes (simple keyword frequency)
    all_text = " ".join(e["content"] for e in results["all_events"])
    words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
    word_freq = {}
    for w in words:
        # Skip common stop words
        if w in {"that", "this", "with", "from", "have", "been", "were", "they",
                  "their", "about", "would", "could", "should", "which", "there",
                  "what", "when", "where", "some", "other", "more", "very", "just",
                  "also", "than", "then", "into", "only", "over", "such", "after",
                  "before", "between", "each", "during", "through", "will", "done"}:
            continue
        word_freq[w] = word_freq.get(w, 0) + 1

    results["top_themes"] = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    return results


def main():
    parser = argparse.ArgumentParser(description="Parse weekly log metrics")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze")
    parser.add_argument("--logs-dir", type=str, default=str(DEFAULT_LOGS_DIR), help="Path to logs directory")
    args = parser.parse_args()

    results = analyze_week(Path(args.logs_dir), args.days)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
