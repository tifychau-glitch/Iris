"""
IRIS Core -- Email delivery for Mt. Everest summaries.
Uses Gmail SMTP to send the user their goal summary with calendar deliverables.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.header import Header
from email import encoders
from typing import Optional

import config

logger = logging.getLogger(__name__)


def send_mt_everest_email(
    to_email: str,
    summary: str,
    calendar_png: Optional[bytes] = None,
    calendar_ics: Optional[str] = None,
) -> bool:
    """
    Send the Mt. Everest summary to the user's email.
    Optionally includes calendar PNG (inline) and ICS file (attachment).
    Returns True on success, False on failure.
    """
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured -- skipping email")
        return False

    # Extract goal line for subject
    goal_line = ""
    for line in summary.split("\n"):
        if line.startswith("THE GOAL:"):
            goal_line = line.replace("THE GOAL:", "").strip()
            break

    subject = "Your Mt. Everest"
    if goal_line:
        short_goal = goal_line[:60] + ("..." if len(goal_line) > 60 else "")
        subject = f"Your Mt. Everest -- {short_goal}"

    # Build HTML email
    html_body = _build_html(summary, has_calendar=calendar_png is not None)

    # Use 'related' as the outer type so inline images work
    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, 'utf-8')
    msg["From"] = Header(config.FROM_EMAIL, 'utf-8')
    msg["To"] = Header(to_email, 'utf-8')

    # HTML + inline images container
    html_related = MIMEMultipart("related")

    # Alternative container (plain text + HTML)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(summary, "plain"))
    alt.attach(MIMEText(html_body, "html"))
    html_related.attach(alt)

    # Embed calendar PNG as inline image
    if calendar_png:
        img_part = MIMEImage(calendar_png, _subtype="png")
        img_part.add_header("Content-ID", "<calendar-roadmap>")
        img_part.add_header("Content-Disposition", "inline", filename="mt-everest-roadmap.png")
        html_related.attach(img_part)

    msg.attach(html_related)

    # Attach ICS file
    if calendar_ics:
        ics_part = MIMEBase("text", "calendar", method="PUBLISH")
        ics_part.set_payload(calendar_ics.encode("utf-8"))
        encoders.encode_base64(ics_part)
        ics_part.add_header(
            "Content-Disposition",
            "attachment",
            filename="mt-everest-milestones.ics",
        )
        msg.attach(ics_part)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.FROM_EMAIL, to_email, msg.as_string())
        logger.info(f"Mt. Everest email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def _build_html(summary: str, has_calendar: bool = False) -> str:
    """Convert the plain text summary into a clean HTML email."""
    # Split into sections and format
    lines = summary.strip().split("\n")
    html_sections = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Section headers (THE GOAL:, WHY THIS GOAL:, etc.)
        if ":" in line and line.split(":")[0].isupper():
            label, _, value = line.partition(":")
            value = value.strip()
            if value:
                html_sections.append(
                    f'<div style="margin-bottom: 24px;">'
                    f'<div style="font-size: 11px; letter-spacing: 1px; color: #888; '
                    f'text-transform: uppercase; margin-bottom: 6px;">{label}</div>'
                    f'<div style="font-size: 16px; color: #e0e0e0; line-height: 1.5;">{value}</div>'
                    f'</div>'
                )
            else:
                html_sections.append(
                    f'<div style="font-size: 11px; letter-spacing: 1px; color: #888; '
                    f'text-transform: uppercase; margin-bottom: 6px; margin-top: 24px;">{label}</div>'
                )
        else:
            # Regular content line (milestone items, etc.)
            html_sections.append(
                f'<div style="font-size: 16px; color: #e0e0e0; line-height: 1.5; '
                f'margin-bottom: 4px; padding-left: 12px;">{line}</div>'
            )

    body = "\n".join(html_sections)

    # Calendar section (embedded PNG)
    calendar_html = ""
    if has_calendar:
        calendar_html = """
        <div style="border-top: 1px solid #222; margin-top: 40px; padding-top: 32px;">
            <div style="font-size: 20px; font-weight: 600; color: #fff; margin-bottom: 16px;">
                Your 12-Month Roadmap
            </div>
            <div style="margin-bottom: 16px;">
                <img src="cid:calendar-roadmap" alt="Mt. Everest 12-Month Roadmap"
                     style="width: 100%; max-width: 560px; border-radius: 8px;" />
            </div>
        </div>
        """

    # ICS note (only if calendar is attached)
    ics_note = ""
    if has_calendar:
        ics_note = """
        <div style="background: #141414; border: 1px solid #222; border-radius: 8px;
                    padding: 16px 20px; margin-top: 24px;">
            <div style="font-size: 14px; color: #e0e0e0; margin-bottom: 4px;">
                Import your milestones
            </div>
            <div style="font-size: 13px; color: #888; line-height: 1.5;">
                I've attached an ICS file to this email. It's compatible with
                Google Calendar, Outlook, and Apple Calendar. Just download
                and import it to see your milestones on your calendar.
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
    <div style="max-width: 560px; margin: 0 auto; padding: 48px 32px;">
        <div style="font-size: 24px; font-weight: 600; color: #fff; margin-bottom: 8px;">
            Your Mt. Everest
        </div>
        <div style="font-size: 14px; color: #666; margin-bottom: 40px;">
            Defined with IRIS
        </div>
        <div style="border-top: 1px solid #222; padding-top: 32px;">
            {body}
        </div>
        {calendar_html}
        {ics_note}
        <div style="border-top: 1px solid #222; margin-top: 40px; padding-top: 24px; font-size: 14px; color: #666; line-height: 1.6;">
            This is your north star. Keep it somewhere you'll see it.
        </div>
    </div>
</body>
</html>"""
