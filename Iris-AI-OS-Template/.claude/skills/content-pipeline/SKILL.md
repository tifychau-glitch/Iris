---
name: content-pipeline
description: Automated LinkedIn content creation pipeline. YouTube transcript to LinkedIn posts and carousel PDFs. Run with /content-pipeline or ask to run the LinkedIn pipeline.
model: sonnet
context: fork
user-invocable: true
---

# Content Pipeline

Transform YouTube transcripts into LinkedIn posts and carousel PDFs.

## Objective

Take a YouTube video transcript and produce:
1. 3-5 LinkedIn text posts (different angles/formats)
2. 1-2 carousel PDFs (slide-based visual content)

All content written in the user's voice using `context/my-voice.md`.

## Inputs Required

- YouTube video URL or transcript text
- `context/my-voice.md` (voice guide — MANDATORY)
- `context/my-business.md` (business context)

## Execution Steps

### Step 1: Get Transcript

If given a YouTube URL, extract the transcript:
- Use YouTube Analytics MCP (`get_video_transcript`) if configured
- Or ask user to paste the transcript

### Step 2: Chunk and Analyze

Break the transcript into key themes/segments:
- Identify 3-5 distinct insights or stories
- For each, note: the core idea, supporting example, lesson/takeaway
- Rank by LinkedIn engagement potential (controversial > practical > inspirational)

### Step 3: Read Voice Guide

**MANDATORY** — Read `context/my-voice.md` before writing anything.
- Match the user's tone, phrases, and style
- Avoid anti-patterns listed in the voice guide

### Step 4: Write LinkedIn Posts

For each insight, write a post in one of these formats:

**Story Post** (~800-1200 chars)
- Hook (first line — must stop the scroll)
- Story/example from the video
- Lesson/insight
- CTA or question

**Insight Post** (~400-600 chars)
- Bold statement or contrarian take
- 3-5 supporting points
- Punchline

**List Post** (~600-800 chars)
- "X things I learned about [topic]:"
- Numbered list with one-line items
- Closing thought

### Step 5: Create Carousel Content

For the best 1-2 insights, create carousel slide content:

- Slide 1: Hook/title (large text, minimal)
- Slides 2-8: One point per slide (key phrase + supporting sentence)
- Last slide: Summary + CTA

Output as markdown that can be converted to PDF or used with Gamma.

### Step 6: Quality Check

For each piece of content:
- [ ] Does it sound like the user (not AI)?
- [ ] Is the hook strong enough to stop scrolling?
- [ ] Is there a clear takeaway?
- [ ] Is it the right length for the format?
- [ ] Would the user actually post this?

### Step 7: Save Output

Save all content to `.tmp/content-pipeline/[date]/`:
- `posts.md` — All LinkedIn posts
- `carousel-1.md` — Carousel slide content
- `carousel-2.md` — Second carousel (if created)

## Rules

- ALWAYS read the voice guide before writing
- Never use generic AI phrases (see content-writer skill for anti-patterns)
- Each post should be a complete, standalone piece
- Don't just summarize the video — extract insights that work as independent content
- Carousels need visual hierarchy: big text for key phrases, small text for supporting points
