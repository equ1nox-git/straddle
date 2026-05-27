#!/usr/bin/env python3
"""
iCloud CalDAV + IMAP integration.
Reads credentials from env vars set in .env.
"""
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from datetime import datetime, timezone
import caldav
from icalendar import Calendar as iCal

ICLOUD_USER      = os.environ.get("ICLOUD_USER", "")
ICLOUD_PASS      = os.environ.get("ICLOUD_PASS", "")
ICLOUD_PRINCIPAL = os.environ.get("ICLOUD_PRINCIPAL", "")
CALDAV_URL       = f"https://caldav.icloud.com/{ICLOUD_PRINCIPAL}/principal/"

# ── CalDAV client ─────────────────────────────────────────────────────────────

def _client():
    return caldav.DAVClient(url=CALDAV_URL, username=ICLOUD_USER, password=ICLOUD_PASS)

def list_calendars():
    calendars = _client().principal().calendars()
    return [{"name": c.get_display_name(), "url": str(c.url)} for c in calendars]

def get_upcoming_events(days=7, calendar_name=None):
    from datetime import timedelta
    principal = _client().principal()
    calendars = principal.calendars()
    results = []
    now   = datetime.now(timezone.utc)
    until = now + timedelta(days=days)

    for cal in calendars:
        name = cal.get_display_name()
        if calendar_name and calendar_name.lower() not in name.lower():
            continue
        if "reminder" in name.lower():
            continue
        try:
            events = cal.search(start=now, end=until, event=True, expand=True)
            for ev in events:
                comp = iCal.from_ical(ev.data)
                for component in comp.walk():
                    if component.name == "VEVENT":
                        dtstart = component.get("DTSTART")
                        results.append({
                            "calendar": name,
                            "summary":  str(component.get("SUMMARY", "No title")),
                            "start":    str(dtstart.dt) if dtstart else "?",
                            "location": str(component.get("LOCATION", "")),
                        })
        except Exception as e:
            results.append({"error": f"{name}: {e}"})

    results.sort(key=lambda x: x.get("start", ""))
    return results

def get_reminders(completed=False):
    import requests as req
    from requests.auth import HTTPBasicAuth
    from xml.etree import ElementTree as ET

    principal = _client().principal()
    calendars = principal.calendars()
    results = []

    for cal in calendars:
        name = cal.get_display_name()
        if "reminder" not in name.lower():
            continue
        try:
            # iCloud doesn't support REPORT for VTODO — use PROPFIND to list items then GET each
            r = req.request(
                "PROPFIND", str(cal.url),
                auth=HTTPBasicAuth(ICLOUD_USER, ICLOUD_PASS),
                headers={"Depth": "1", "Content-Type": "application/xml"},
                data='<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getetag/></d:prop></d:propfind>',
                timeout=10
            )
            tree = ET.fromstring(r.text)
            hrefs = [el.text for el in tree.iter("{DAV:}href") if el.text and el.text.endswith(".ics")]
            for href in hrefs:
                item_url = f"https://caldav.icloud.com{href}"
                gr = req.get(item_url, auth=HTTPBasicAuth(ICLOUD_USER, ICLOUD_PASS), timeout=10)
                comp = iCal.from_ical(gr.text)
                for component in comp.walk():
                    if component.name == "VTODO":
                        status = str(component.get("STATUS", "NEEDS-ACTION"))
                        if not completed and status == "COMPLETED":
                            continue
                        results.append({
                            "summary": str(component.get("SUMMARY", "No title")),
                            "due":     str(component.get("DUE").dt) if component.get("DUE") else None,
                            "status":  status,
                        })
        except Exception as e:
            results.append({"error": str(e)})
    return results

def create_event(calendar_name, summary, start_dt, end_dt, description="", location=""):
    """
    start_dt / end_dt: datetime objects (timezone-aware recommended)
    """
    principal = _client().principal()
    calendars = principal.calendars()
    target = None
    for cal in calendars:
        if calendar_name.lower() in cal.get_display_name().lower():
            target = cal
            break
    if not target:
        return {"error": f"Calendar '{calendar_name}' not found"}

    ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//OpenSpace//EN
BEGIN:VEVENT
SUMMARY:{summary}
DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}
DESCRIPTION:{description}
LOCATION:{location}
END:VEVENT
END:VCALENDAR"""
    target.save_event(ical)
    return {"status": "created", "summary": summary, "start": str(start_dt)}

# ── IMAP / SMTP ───────────────────────────────────────────────────────────────

IMAP_HOST  = "imap.mail.me.com"
IMAP_PORT  = 993
SMTP_HOST  = "smtp.mail.me.com"
SMTP_PORT  = 587

def get_recent_emails(mailbox="INBOX", limit=10):
    results = []
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(ICLOUD_USER, ICLOUD_PASS)
        imap.select(mailbox)
        _, data = imap.search(None, "ALL")
        ids = data[0].split()
        for uid in reversed(ids[-limit:]):
            _, msg_data = imap.fetch(uid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")[:500]
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")[:500]
            results.append({
                "from":    msg.get("From"),
                "subject": msg.get("Subject"),
                "date":    msg.get("Date"),
                "snippet": body.strip(),
            })
    return results

def send_email(to, subject, body, from_name="Thomas"):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = f"{from_name} <{ICLOUD_USER}>"
    msg["To"]      = to
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(ICLOUD_USER, ICLOUD_PASS)
        smtp.send_message(msg)
    return {"status": "sent", "to": to, "subject": subject}

def list_mailboxes():
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(ICLOUD_USER, ICLOUD_PASS)
        _, folders = imap.list()
        return [f.decode().split('"/"')[-1].strip() for f in folders]


if __name__ == "__main__":
    import json
    print("=== Calendars ===")
    print(json.dumps(list_calendars(), indent=2))
    print("\n=== Upcoming (7d) ===")
    print(json.dumps(get_upcoming_events(7), indent=2))
    print("\n=== Reminders ===")
    print(json.dumps(get_reminders(), indent=2))
    print("\n=== Recent Email ===")
    print(json.dumps(get_recent_emails(limit=5), indent=2))
