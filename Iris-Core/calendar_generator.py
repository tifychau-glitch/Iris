"""
IRIS Core -- Calendar deliverables for Mt. Everest summaries.
Generates a sample weekly calendar PNG (controlled calendar style)
and ICS file from milestone data.
"""

import io
import re
import logging
from datetime import datetime, timedelta, date, time as dtime
from typing import Optional

logger = logging.getLogger(__name__)


def parse_milestones(summary: str, start_date: Optional[date] = None) -> dict:
    """Extract milestone data from a Mt. Everest summary.

    Returns dict with keys: goal, why, ceiling, milestones (dict with
    'twelve_month', 'ninety_day', 'this_month' text + computed dates).
    """
    if start_date is None:
        start_date = date.today()

    data = {"goal": "", "why": "", "ceiling": "", "milestones": {}}

    # Extract sections
    for line in summary.split("\n"):
        line = line.strip()
        upper = line.upper()
        if upper.startswith("THE GOAL:"):
            data["goal"] = line.split(":", 1)[1].strip()
        elif upper.startswith("WHY THIS GOAL:"):
            data["why"] = line.split(":", 1)[1].strip()
        elif upper.startswith("THE CEILING:"):
            data["ceiling"] = line.split(":", 1)[1].strip()

    # Extract milestones section
    milestone_section = ""
    in_milestones = False
    for line in summary.split("\n"):
        if line.strip().upper().startswith("MILESTONES"):
            in_milestones = True
            continue
        if in_milestones:
            milestone_section += line + "\n"

    # Parse milestone lines
    twelve_month = ""
    ninety_day = ""
    this_month = ""

    for line in milestone_section.split("\n"):
        line_lower = line.strip().lower()
        if line_lower.startswith("12 month"):
            twelve_month = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line_lower.startswith("90 day"):
            ninety_day = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line_lower.startswith("this month"):
            this_month = line.split(":", 1)[1].strip() if ":" in line else ""

    data["milestones"] = {
        "this_month": {
            "text": this_month,
            "date": start_date + timedelta(days=30),
        },
        "ninety_day": {
            "text": ninety_day,
            "date": start_date + timedelta(days=90),
        },
        "twelve_month": {
            "text": twelve_month,
            "date": start_date + timedelta(days=365),
        },
    }

    return data


# ---- Weekly time block generation ----

def _build_weekly_blocks(data: dict) -> list:
    """Build a sample week of time blocks based on Mt. Everest data.

    Uses the controlled calendar framework:
    1. Non-negotiables first
    2. 5 money-making blocks
    3. Reflection / learning
    4. Weekly planning
    5. Buffer time

    Returns list of dicts with: day (0=Mon), start_hour, end_hour,
    label, category, color, description.
    """
    goal = data["goal"]
    this_month = data["milestones"]["this_month"]["text"]
    ninety_day = data["milestones"]["ninety_day"]["text"]

    blocks = []

    # -- Non-negotiables (green) --
    blocks.append({
        "day": 0, "start_hour": 6, "end_hour": 7,
        "label": "Morning Routine",
        "category": "non-negotiable",
        "color": "#059669", "bg": "#ecfdf5",
        "description": "Protected personal time",
    })
    blocks.append({
        "day": 2, "start_hour": 6, "end_hour": 7,
        "label": "Morning Routine",
        "category": "non-negotiable",
        "color": "#059669", "bg": "#ecfdf5",
        "description": "Protected personal time",
    })
    blocks.append({
        "day": 4, "start_hour": 6, "end_hour": 7,
        "label": "Morning Routine",
        "category": "non-negotiable",
        "color": "#059669", "bg": "#ecfdf5",
        "description": "Protected personal time",
    })
    blocks.append({
        "day": 1, "start_hour": 18, "end_hour": 19.5,
        "label": "Family / Personal",
        "category": "non-negotiable",
        "color": "#059669", "bg": "#ecfdf5",
        "description": "Non-negotiable personal time",
    })
    blocks.append({
        "day": 3, "start_hour": 18, "end_hour": 19.5,
        "label": "Family / Personal",
        "category": "non-negotiable",
        "color": "#059669", "bg": "#ecfdf5",
        "description": "Non-negotiable personal time",
    })

    # -- Daily 15-min morning review (orange) --
    for d in range(5):
        blocks.append({
            "day": d, "start_hour": 7, "end_hour": 7.25,
            "label": "Daily Review",
            "category": "planning",
            "color": "#ea580c", "bg": "#fff7ed",
            "description": "15 min: review today's plan before starting",
        })

    # -- Money-making blocks (blue) - 5 per week --
    money_desc = f"Directly moves toward: {goal[:60]}" if goal else "Revenue-generating activity"
    thirty_day_note = f" | 30-day target: {this_month[:50]}" if this_month else ""

    blocks.append({
        "day": 0, "start_hour": 8, "end_hour": 10,
        "label": "Money Block: Outreach",
        "category": "money",
        "color": "#2563eb", "bg": "#eff6ff",
        "description": f"Prospecting, outreach, lead generation{thirty_day_note}",
    })
    blocks.append({
        "day": 1, "start_hour": 8, "end_hour": 10,
        "label": "Money Block: Sales",
        "category": "money",
        "color": "#2563eb", "bg": "#eff6ff",
        "description": f"Sales conversations, follow-ups, closing{thirty_day_note}",
    })
    blocks.append({
        "day": 2, "start_hour": 8, "end_hour": 10,
        "label": "Money Block: Build",
        "category": "money",
        "color": "#2563eb", "bg": "#eff6ff",
        "description": f"Product/service development. {money_desc}",
    })
    blocks.append({
        "day": 3, "start_hour": 8, "end_hour": 10,
        "label": "Money Block: Partnerships",
        "category": "money",
        "color": "#2563eb", "bg": "#eff6ff",
        "description": f"Networking, partnerships, deal sourcing{thirty_day_note}",
    })
    blocks.append({
        "day": 4, "start_hour": 8, "end_hour": 10,
        "label": "Money Block: Content",
        "category": "money",
        "color": "#2563eb", "bg": "#eff6ff",
        "description": f"Content that generates leads. {money_desc}",
    })

    # -- Deep work / execution (purple) --
    blocks.append({
        "day": 0, "start_hour": 10.5, "end_hour": 12.5,
        "label": "Deep Work",
        "category": "execution",
        "color": "#7c3aed", "bg": "#f5f3ff",
        "description": "Focused execution on 30-day milestone",
    })
    blocks.append({
        "day": 2, "start_hour": 10.5, "end_hour": 12.5,
        "label": "Deep Work",
        "category": "execution",
        "color": "#7c3aed", "bg": "#f5f3ff",
        "description": "Focused execution on 30-day milestone",
    })
    blocks.append({
        "day": 4, "start_hour": 10.5, "end_hour": 12.5,
        "label": "Deep Work",
        "category": "execution",
        "color": "#7c3aed", "bg": "#f5f3ff",
        "description": "Focused execution on 30-day milestone",
    })

    # -- Admin / operations (gray, afternoon) --
    blocks.append({
        "day": 1, "start_hour": 13, "end_hour": 14.5,
        "label": "Admin / Ops",
        "category": "admin",
        "color": "#6b7280", "bg": "#f3f4f6",
        "description": "Email, admin, operations (batched, not reactive)",
    })
    blocks.append({
        "day": 3, "start_hour": 13, "end_hour": 14.5,
        "label": "Admin / Ops",
        "category": "admin",
        "color": "#6b7280", "bg": "#f3f4f6",
        "description": "Email, admin, operations (batched, not reactive)",
    })

    # -- Reflection + learning (teal) --
    blocks.append({
        "day": 4, "start_hour": 14, "end_hour": 15,
        "label": "Reflection + Journal",
        "category": "reflection",
        "color": "#0d9488", "bg": "#f0fdfa",
        "description": "Review wins, document lessons, content ideas",
    })
    blocks.append({
        "day": 3, "start_hour": 15, "end_hour": 16,
        "label": "Learning Block",
        "category": "learning",
        "color": "#0d9488", "bg": "#f0fdfa",
        "description": "Intentional skill development with immediate application",
    })

    # -- Weekly planning (Sunday, orange) --
    blocks.append({
        "day": 6, "start_hour": 9, "end_hour": 12,
        "label": "Weekly Planning",
        "category": "planning",
        "color": "#ea580c", "bg": "#fff7ed",
        "description": "3-hour weekly planning block. Review, plan, design the week.",
    })

    # -- Buffer / white space (light gray) --
    blocks.append({
        "day": 0, "start_hour": 12.5, "end_hour": 13,
        "label": "Buffer",
        "category": "buffer",
        "color": "#9ca3af", "bg": "#f9fafb",
        "description": "Protected white space. Not available for booking.",
    })
    blocks.append({
        "day": 1, "start_hour": 10.5, "end_hour": 11,
        "label": "Buffer",
        "category": "buffer",
        "color": "#9ca3af", "bg": "#f9fafb",
        "description": "Protected white space. Not available for booking.",
    })
    blocks.append({
        "day": 2, "start_hour": 12.5, "end_hour": 13,
        "label": "Buffer",
        "category": "buffer",
        "color": "#9ca3af", "bg": "#f9fafb",
        "description": "Protected white space. Not available for booking.",
    })
    blocks.append({
        "day": 3, "start_hour": 10.5, "end_hour": 11,
        "label": "Buffer",
        "category": "buffer",
        "color": "#9ca3af", "bg": "#f9fafb",
        "description": "Protected white space. Not available for booking.",
    })
    blocks.append({
        "day": 4, "start_hour": 12.5, "end_hour": 13,
        "label": "Buffer",
        "category": "buffer",
        "color": "#9ca3af", "bg": "#f9fafb",
        "description": "Protected white space. Not available for booking.",
    })

    return blocks


# ---- PNG rendering ----

def _load_fonts():
    """Load fonts with fallback chain."""
    from PIL import ImageFont

    sizes = {"title": 24, "subtitle": 14, "day": 13, "block": 10, "label": 9, "footer": 10}
    fonts = {}

    for key, size in sizes.items():
        try:
            fonts[key] = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except (IOError, OSError):
            try:
                fonts[key] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
            except (IOError, OSError):
                fonts[key] = ImageFont.load_default()

    return fonts


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate_calendar_png(summary: str, start_date: Optional[date] = None) -> bytes:
    """Generate a weekly calendar PNG with time blocks in controlled calendar style.

    White background, colored time blocks, looks like a real calendar.
    Returns PNG image as bytes.
    """
    from PIL import Image, ImageDraw

    if start_date is None:
        start_date = date.today()

    data = parse_milestones(summary, start_date)
    blocks = _build_weekly_blocks(data)
    fonts = _load_fonts()

    # Canvas
    WIDTH = 1200
    HEIGHT = 960
    BG = "#ffffff"

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # Colors
    TEXT_DARK = "#111827"
    TEXT_MUTED = "#6b7280"
    BORDER = "#e5e7eb"
    HEADER_BG = "#f9fafb"

    # Layout constants
    LEFT_MARGIN = 70       # Time labels column
    TOP_MARGIN = 130       # Header area
    DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    NUM_DAYS = 7
    COL_W = (WIDTH - LEFT_MARGIN - 20) // NUM_DAYS
    HOUR_START = 6         # 6 AM
    HOUR_END = 20          # 8 PM
    NUM_HOURS = HOUR_END - HOUR_START
    ROW_H = (HEIGHT - TOP_MARGIN - 50) // NUM_HOURS

    # -- Header --
    draw.text((LEFT_MARGIN, 20), "YOUR CONTROLLED CALENDAR", fill=TEXT_MUTED, font=fonts["label"])

    goal_text = data["goal"][:80] + ("..." if len(data["goal"]) > 80 else "")
    draw.text((LEFT_MARGIN, 38), goal_text, fill=TEXT_DARK, font=fonts["title"])

    # Week label
    monday = start_date - timedelta(days=start_date.weekday())
    sunday = monday + timedelta(days=6)
    week_label = f"Sample week starting {monday.strftime('%B %d, %Y')}"
    draw.text((LEFT_MARGIN, 68), week_label, fill=TEXT_MUTED, font=fonts["subtitle"])

    # Legend
    legend_items = [
        ("#059669", "Non-Negotiable"),
        ("#2563eb", "Money-Making"),
        ("#7c3aed", "Deep Work"),
        ("#ea580c", "Planning"),
        ("#0d9488", "Learning"),
        ("#9ca3af", "Buffer"),
    ]
    lx = LEFT_MARGIN
    for color, label in legend_items:
        draw.rounded_rectangle([lx, 92, lx + 10, 102], radius=2, fill=color)
        draw.text((lx + 14, 92), label, fill=TEXT_MUTED, font=fonts["label"])
        tw = draw.textlength(label, font=fonts["label"])
        lx += tw + 30

    # -- Day headers --
    for d in range(NUM_DAYS):
        x = LEFT_MARGIN + d * COL_W
        # Header background
        draw.rectangle([x, TOP_MARGIN - 24, x + COL_W, TOP_MARGIN], fill=HEADER_BG, outline=BORDER)
        # Day name centered
        tw = draw.textlength(DAY_NAMES[d], font=fonts["day"])
        draw.text((x + (COL_W - tw) / 2, TOP_MARGIN - 20), DAY_NAMES[d], fill=TEXT_DARK, font=fonts["day"])

    # -- Grid lines --
    for h in range(NUM_HOURS + 1):
        y = TOP_MARGIN + h * ROW_H
        # Hour label
        hour = HOUR_START + h
        if hour <= HOUR_END:
            if hour == 0:
                label = "12 AM"
            elif hour < 12:
                label = f"{hour} AM"
            elif hour == 12:
                label = "12 PM"
            else:
                label = f"{hour - 12} PM"
            draw.text((8, y - 5), label, fill=TEXT_MUTED, font=fonts["label"])

        # Horizontal line
        draw.line([(LEFT_MARGIN, y), (LEFT_MARGIN + NUM_DAYS * COL_W, y)], fill=BORDER, width=1)

    # Vertical lines
    for d in range(NUM_DAYS + 1):
        x = LEFT_MARGIN + d * COL_W
        draw.line([(x, TOP_MARGIN - 24), (x, TOP_MARGIN + NUM_HOURS * ROW_H)], fill=BORDER, width=1)

    # -- Draw time blocks --
    for block in blocks:
        d = block["day"]
        sh = block["start_hour"] - HOUR_START
        eh = block["end_hour"] - HOUR_START

        if sh < 0 or eh > NUM_HOURS:
            continue

        x1 = LEFT_MARGIN + d * COL_W + 2
        x2 = LEFT_MARGIN + (d + 1) * COL_W - 2
        y1 = TOP_MARGIN + int(sh * ROW_H) + 1
        y2 = TOP_MARGIN + int(eh * ROW_H) - 1

        bg_rgb = _hex_to_rgb(block["bg"])
        color_rgb = _hex_to_rgb(block["color"])

        # Block background
        draw.rounded_rectangle([x1, y1, x2, y2], radius=4, fill=bg_rgb)
        # Left accent bar
        draw.rounded_rectangle([x1, y1, x1 + 3, y2], radius=2, fill=color_rgb)

        # Block label
        block_height = y2 - y1
        label = block["label"]

        if block_height >= 20:
            # Truncate label to fit
            max_chars = int((x2 - x1 - 10) / 5.5)
            if len(label) > max_chars:
                label = label[:max_chars - 2] + ".."
            draw.text((x1 + 7, y1 + 4), label, fill=color_rgb, font=fonts["block"])

        # Time range (if block is tall enough)
        if block_height >= 36:
            s_hr = int(block["start_hour"])
            s_min = int((block["start_hour"] % 1) * 60)
            e_hr = int(block["end_hour"])
            e_min = int((block["end_hour"] % 1) * 60)
            s_ampm = "a" if s_hr < 12 else "p"
            e_ampm = "a" if e_hr < 12 else "p"
            s_disp = s_hr if s_hr <= 12 else s_hr - 12
            e_disp = e_hr if e_hr <= 12 else e_hr - 12
            time_str = f"{s_disp}"
            if s_min:
                time_str += f":{s_min:02d}"
            time_str += f"{s_ampm}-{e_disp}"
            if e_min:
                time_str += f":{e_min:02d}"
            time_str += f"{e_ampm}"
            draw.text((x1 + 7, y1 + 17), time_str, fill=TEXT_MUTED, font=fonts["label"])

    # -- Footer --
    draw.text(
        (LEFT_MARGIN, HEIGHT - 30),
        "Sample calendar generated by IRIS  |  heyitsiris.com  |  Personalize this in IRIS Pro",
        fill="#9ca3af",
        font=fonts["footer"],
    )

    # -- Pro tease banner --
    banner_y = HEIGHT - 50
    draw.rounded_rectangle(
        [WIDTH - 340, banner_y - 4, WIDTH - 20, banner_y + 18],
        radius=4, fill="#eff6ff",
    )
    draw.text(
        (WIDTH - 332, banner_y),
        "Want this built for YOUR schedule?  Get IRIS Pro",
        fill="#2563eb", font=fonts["label"],
    )

    # Export
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()


def _draw_wrapped_text(
    draw, x, y, text, font, max_width, fill, line_height=18, max_lines=5
):
    """Draw text wrapped to fit within max_width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        tw = draw.textlength(test, font=font)
        if tw <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines[:max_lines]):
        if i == max_lines - 1 and len(lines) > max_lines:
            line = line[:len(line) - 3] + "..."
        draw.text((x, y + i * line_height), line, fill=fill, font=font)


# ---- ICS generation ----

def generate_ics(summary: str, start_date: Optional[date] = None) -> str:
    """Generate an ICS calendar file with weekly time blocks + milestone events.

    Returns ICS content as string.
    """
    from icalendar import Calendar, Event, Alarm

    if start_date is None:
        start_date = date.today()

    data = parse_milestones(summary, start_date)
    blocks = _build_weekly_blocks(data)
    milestones = data["milestones"]
    goal = data["goal"]

    cal = Calendar()
    cal.add("prodid", "-//IRIS//Controlled Calendar//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "IRIS - Your Controlled Calendar")

    # Find the Monday of the start week
    monday = start_date - timedelta(days=start_date.weekday())

    # Add weekly time blocks as events
    for block in blocks:
        event = Event()
        event.add("summary", block["label"])

        block_date = monday + timedelta(days=block["day"])
        s_hr = int(block["start_hour"])
        s_min = int((block["start_hour"] % 1) * 60)
        e_hr = int(block["end_hour"])
        e_min = int((block["end_hour"] % 1) * 60)

        event.add("dtstart", datetime.combine(block_date, dtime(s_hr, s_min)))
        event.add("dtend", datetime.combine(block_date, dtime(e_hr, e_min)))
        event.add("description", block["description"])

        # Weekly recurrence for most blocks
        if block["category"] != "buffer":
            event.add("rrule", {"freq": "weekly"})

        cal.add_component(event)

    # Add milestone events (all-day)
    milestone_configs = [
        ("this_month", "30-Day Milestone"),
        ("ninety_day", "90-Day Milestone"),
        ("twelve_month", "12-Month Milestone"),
    ]

    for key, label in milestone_configs:
        ms = milestones[key]
        if not ms["text"]:
            continue

        event = Event()
        event.add("summary", f"IRIS: {label} - {goal[:50]}")
        event.add("dtstart", ms["date"])
        event.add(
            "description",
            f"{label}\n\n{ms['text']}\n\nGoal: {goal}\n\n"
            f"Generated by IRIS - heyitsiris.com",
        )
        event.add("transp", "TRANSPARENT")

        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"IRIS milestone tomorrow: {label}")
        alarm.add("trigger", timedelta(days=-1))
        event.add_component(alarm)

        cal.add_component(event)

    return cal.to_ical().decode("utf-8")
