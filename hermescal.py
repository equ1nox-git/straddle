#!/usr/bin/env python3
"""
Calendar/Reminders/Email CLI for Hermes terminal tool.
Usage:
  hermescal.py calendars
  hermescal.py events [days]
  hermescal.py reminders [--completed] [--list NAME]
  hermescal.py inbox [--account LABEL] [--limit N]
  hermescal.py send ACCOUNT TO SUBJECT BODY
  hermescal.py accounts
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import mail_hub as hub

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "calendars":
        print(json.dumps(hub.list_calendars(), indent=2))

    elif cmd == "events":
        days = int(args[1]) if len(args) > 1 else 7
        print(json.dumps(hub.get_upcoming_events(days), indent=2))

    elif cmd == "reminders":
        completed = "--completed" in args
        list_name = None
        if "--list" in args:
            list_name = args[args.index("--list") + 1]
        print(json.dumps(hub.get_reminders(completed=completed, list_name=list_name), indent=2))

    elif cmd == "inbox":
        account = None
        limit = 10
        if "--account" in args:
            account = args[args.index("--account") + 1]
        if "--limit" in args:
            limit = int(args[args.index("--limit") + 1])
        if account:
            print(json.dumps(hub.get_recent_emails(limit=limit, account=account), indent=2))
        else:
            print(json.dumps(hub.get_all_recent_emails(limit=limit), indent=2))

    elif cmd == "send":
        if len(args) < 5:
            print("Usage: send ACCOUNT TO SUBJECT BODY")
            sys.exit(1)
        account, to, subject, body = args[1], args[2], args[3], " ".join(args[4:])
        print(json.dumps(hub.send_email(to, subject, body, account=account), indent=2))

    elif cmd == "accounts":
        print(json.dumps(hub.list_accounts(), indent=2))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
