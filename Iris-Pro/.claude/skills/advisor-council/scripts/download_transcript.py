#!/usr/bin/env python3
"""Download YouTube transcript and save to advisor's sources directory.

Usage:
    python3 download_transcript.py "YOUTUBE_URL" "advisor_name"
    python3 download_transcript.py "YOUTUBE_URL" "advisor_name" --title "Custom Title"

Saves transcript to: context/advisors/{advisor_name}/sources/{video_title}.md
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]  # .claude/skills/advisor-council/scripts -> root
ADVISORS_DIR = PROJECT_ROOT / "context" / "advisors"


def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    name = re.sub(r'[^\w\s-]', '', name.lower())
    name = re.sub(r'[\s]+', '-', name.strip())
    return name[:80]


def get_video_info(url: str) -> dict:
    """Get video title and ID using yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "%(title)s\n%(id)s", "--no-download", url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return {"title": lines[0] if lines else "unknown", "id": lines[1] if len(lines) > 1 else "unknown"}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return {"title": "unknown-video", "id": "unknown"}


def download_transcript_ytdlp(url: str) -> str:
    """Download transcript using yt-dlp subtitle extraction."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Try auto-generated subtitles first, then manual
        for sub_flag in ["--write-auto-sub", "--write-sub"]:
            result = subprocess.run(
                ["yt-dlp", sub_flag, "--sub-lang", "en", "--skip-download",
                 "--sub-format", "vtt", "-o", f"{tmpdir}/%(id)s.%(ext)s", url],
                capture_output=True, text=True, timeout=60
            )
            # Find the subtitle file
            for f in Path(tmpdir).glob("*.vtt"):
                return parse_vtt(f.read_text())
            for f in Path(tmpdir).glob("*.en.*"):
                return f.read_text()
    return ""


def parse_vtt(vtt_text: str) -> str:
    """Parse VTT subtitle format into clean text."""
    lines = []
    seen = set()
    for line in vtt_text.split('\n'):
        line = line.strip()
        # Skip timestamps, headers, and empty lines
        if not line or '-->' in line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or re.match(r'^\d+$', line):
            continue
        # Remove VTT tags
        clean = re.sub(r'<[^>]+>', '', line)
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)
    return ' '.join(lines)


def download_transcript_api(url: str) -> str:
    """Fallback: try youtube-transcript-api if installed."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        video_id = extract_video_id(url)
        if not video_id:
            return ""
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except (ImportError, Exception):
        return ""


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: download_transcript.py YOUTUBE_URL ADVISOR_NAME [--title TITLE]"}))
        sys.exit(1)

    url = sys.argv[1]
    advisor_name = sys.argv[2].lower().replace(' ', '-')
    custom_title = None

    if "--title" in sys.argv:
        idx = sys.argv.index("--title")
        if idx + 1 < len(sys.argv):
            custom_title = sys.argv[idx + 1]

    # Create advisor sources directory
    sources_dir = ADVISORS_DIR / advisor_name / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    # Get video info
    info = get_video_info(url)
    title = custom_title or info["title"]
    filename = sanitize_filename(title) + ".md"

    # Try downloading transcript
    transcript = download_transcript_ytdlp(url)
    if not transcript:
        transcript = download_transcript_api(url)

    if not transcript:
        print(json.dumps({
            "error": "Could not download transcript. Try: pip install yt-dlp youtube-transcript-api",
            "suggestion": "You can also paste the transcript manually and save it to: " + str(sources_dir / filename)
        }))
        sys.exit(1)

    # Save transcript
    output_path = sources_dir / filename
    word_count = len(transcript.split())

    content = f"""# {title}

> Source: {url}
> Downloaded: {__import__('datetime').date.today().isoformat()}
> Words: {word_count}

---

{transcript}
"""
    output_path.write_text(content)

    print(json.dumps({
        "status": "success",
        "advisor": advisor_name,
        "file": str(output_path),
        "title": title,
        "words": word_count
    }))


if __name__ == "__main__":
    main()
