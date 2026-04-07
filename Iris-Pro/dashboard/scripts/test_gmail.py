#!/usr/bin/env python3
"""Test Gmail SMTP credentials with a handshake (no email sent)."""
import json, os, smtplib
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

user = os.getenv("SMTP_USER", "")
password = os.getenv("SMTP_PASSWORD", "")

if not user or not password:
    print(json.dumps({"success": False, "error": "SMTP_USER or SMTP_PASSWORD not set"}))
    exit()

try:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
    server.starttls()
    server.login(user, password)
    server.quit()
    print(json.dumps({"success": True, "message": f"SMTP login OK: {user}"}))
except smtplib.SMTPAuthenticationError:
    print(json.dumps({"success": False, "error": "Authentication failed. Check app password."}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
