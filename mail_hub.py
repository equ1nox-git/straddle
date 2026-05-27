#!/usr/bin/env python3
"""
Multi-account email + iCloud CalDAV/Reminders integration.
Credentials from env vars (.env).
"""
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from datetime import datetime, timezone
import caldav
from icalendar import Calendar as iCal

# ── iCloud CalDAV credentials ──────────────────────────────────────────────────
ICLOUD_USER      = os.environ.get("ICLOUD_USER", "")
ICLOUD_PASS      = os.environ.get("ICLOUD_PASS", "")
ICLOUD_PRINCIPAL = os.environ.get("ICLOUD_PRINCIPAL", "")
CALDAV_URL       = f"https://caldav.icloud.com/{ICLOUD_PRINCIPAL}/principal/"

# ── Mail accounts ──────────────────────────────────────────────────────────────
# Each entry: (label, email, password, imap_host, imap_port, smtp_host, smtp_port)
MAIL_ACCOUNTS = [
    {
        "label":     "iCloud",
        "email":     os.environ.get("ICLOUD_EMAIL",  "tom.mb99@icloud.com"),
        "password":  os.environ.get("ICLOUD_PASS",   ""),
        "imap_host": "imap.mail.me.com",
        "imap_port": 993,
        "smtp_host": "smtp.mail.me.com",
        "smtp_port": 587,
    },
    {
        "label":     "Gmail",
        "email":     os.environ.get("GMAIL_EMAIL",   "tmb129129@gmail.com"),
        "password":  os.environ.get("GMAIL_PASS",    ""),
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
    },
    {
        "label":     "Yahoo",
        "email":     os.environ.get("YAHOO_EMAIL",   "tmb199922@yahoo.com"),
        "password":  os.environ.get("YAHOO_PASS",    ""),
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
    },
]

def _account(label=None):
    """Return account dict by label (case-insensitive). Default: iCloud."""
    if label is None:
        return MAIL_ACCOUNTS[0]
    label = label.lower()
    for acc in MAIL_ACCOUNTS:
        if acc["label"].lower() == label:
            return acc
    raise ValueError(f"Unknown account: {label}. Available: {[a['label'] for a in MAIL_ACCOUNTS]}")

# ── CalDAV client ──────────────────────────────────────────────────────────────

def _caldav_client():
    return caldav.DAVClient(url=CALDAV_URL, username=ICLOUD_USER, password=ICLOUD_PASS)

def list_calendars():
    calendars = _caldav_client().principal().calendars()
    return [{"name": c.get_display_name(), "url": str(c.url)} for c in calendars]

def get_upcoming_events(days=7, calendar_name=None):
    from datetime import timedelta
    principal = _caldav_client().principal()
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

MAC_REMINDERS_CACHE = "/tmp/reminders_mac.json"
MAC_CACHE_MAX_AGE   = 600  # 10 min

def _read_mac_cache(list_name=None, completed=False):
    import json, time, os
    if not os.path.exists(MAC_REMINDERS_CACHE):
        return None
    if time.time() - os.path.getmtime(MAC_REMINDERS_CACHE) > MAC_CACHE_MAX_AGE:
        return None
    try:
        data = json.loads(open(MAC_REMINDERS_CACHE).read())
        if list_name:
            data = [r for r in data if list_name.lower() in r.get("list","").lower()]
        return data
    except Exception:
        return None

def get_reminders(completed=False, list_name=None):
    # Try MacBook osascript cache first (more up-to-date than CalDAV)
    cached = _read_mac_cache(list_name=list_name, completed=completed)
    if cached is not None:
        return cached

    import requests as req
    from requests.auth import HTTPBasicAuth
    from xml.etree import ElementTree as ET

    principal = _caldav_client().principal()
    calendars = principal.calendars()
    results = []

    for cal in calendars:
        name = cal.get_display_name()
        if list_name and list_name.lower() not in name.lower():
            continue
        try:
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
                            "list":    name,
                            "summary": str(component.get("SUMMARY", "No title")),
                            "due":     str(component.get("DUE").dt) if component.get("DUE") else None,
                            "status":  status,
                        })
        except Exception as e:
            results.append({"error": str(e)})
    return results

def create_event(calendar_name, summary, start_dt, end_dt, description="", location=""):
    """start_dt / end_dt: timezone-aware datetime objects."""
    principal = _caldav_client().principal()
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

# ── Multi-account IMAP / SMTP ──────────────────────────────────────────────────

def _fetch_email(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="replace")[:500]
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="replace")[:500]
    return {
        "from":    msg.get("From"),
        "subject": msg.get("Subject"),
        "date":    msg.get("Date"),
        "snippet": body.strip(),
    }

def get_recent_emails(mailbox="INBOX", limit=10, account=None):
    acc = _account(account)
    results = []
    with imaplib.IMAP4_SSL(acc["imap_host"], acc["imap_port"]) as imap:
        imap.login(acc["email"], acc["password"])
        imap.select(mailbox)
        _, data = imap.search(None, "ALL")
        ids = data[0].split()
        for uid in reversed(ids[-limit:]):
            _, msg_data = imap.fetch(uid, "(RFC822)")
            for part in msg_data:
                if isinstance(part, tuple) and isinstance(part[1], bytes):
                    msg = email.message_from_bytes(part[1])
                    result = _fetch_email(msg)
                    result["account"] = acc["label"]
                    results.append(result)
                    break
    return results

def get_all_recent_emails(mailbox="INBOX", limit=5):
    """Fetch recent emails from all configured accounts."""
    results = []
    for acc in MAIL_ACCOUNTS:
        if not acc["password"]:
            continue
        try:
            emails = get_recent_emails(mailbox=mailbox, limit=limit, account=acc["label"])
            results.extend(emails)
        except Exception as e:
            results.append({"account": acc["label"], "error": str(e)})
    return results

def send_email(to, subject, body, from_name="Thomas", account=None):
    acc = _account(account)
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = f"{from_name} <{acc['email']}>"
    msg["To"]      = to
    with smtplib.SMTP(acc["smtp_host"], acc["smtp_port"]) as smtp:
        smtp.starttls()
        smtp.login(acc["email"], acc["password"])
        smtp.send_message(msg)
    return {"status": "sent", "account": acc["label"], "to": to, "subject": subject}

def list_mailboxes(account=None):
    acc = _account(account)
    with imaplib.IMAP4_SSL(acc["imap_host"], acc["imap_port"]) as imap:
        imap.login(acc["email"], acc["password"])
        _, folders = imap.list()
        return [f.decode().split('"/"')[-1].strip() for f in folders]

def list_accounts():
    return [{"label": a["label"], "email": a["email"], "configured": bool(a["password"])} for a in MAIL_ACCOUNTS]


if __name__ == "__main__":
    import json
    print("=== Accounts ===")
    print(json.dumps(list_accounts(), indent=2))
    print("\n=== Calendars ===")
    print(json.dumps(list_calendars(), indent=2))
    print("\n=== Upcoming (7d) ===")
    print(json.dumps(get_upcoming_events(7), indent=2))
    print("\n=== Reminders ===")
    print(json.dumps(get_reminders(), indent=2))
    print("\n=== Recent Email (all accounts) ===")
    print(json.dumps(get_all_recent_emails(limit=3), indent=2))
