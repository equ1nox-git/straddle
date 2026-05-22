#!/usr/bin/env python3
import os, requests, time

TOKEN        = os.environ["TELEGRAM_BOT_TOKEN"]
STRADDLE_URL = os.environ.get("STRADDLE_URL", "http://localhost:11435")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

def main():
    offset = None
    while True:
        try:
            updates = requests.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            ).json().get("result", [])
            for u in updates:
                offset   = u["update_id"] + 1
                chat_id  = u["message"]["chat"]["id"]
                text     = u["message"].get("text", "")
                if not text:
                    continue
                payload = {"messages": [{"role": "user", "content": text}]}
                if DEFAULT_MODEL:
                    payload["model"] = DEFAULT_MODEL
                ans = requests.post(
                    f"{STRADDLE_URL}/v1/chat/completions",
                    json=payload,
                    timeout=120,
                ).json()
                reply = ans["choices"][0]["message"]["content"]
                requests.post(f"{TELEGRAM_API}/sendMessage",
                              json={"chat_id": chat_id, "text": reply})
        except Exception as e:
            print(f"gateway error: {e}")
            time.sleep(5)
            continue
        time.sleep(1)

if __name__ == "__main__":
    main()
