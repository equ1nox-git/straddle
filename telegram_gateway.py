#!/usr/bin/env python3
import os, requests, time
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
URL = f"https://api.telegram.org/bot{TOKEN}"
def main():
    offset = None
    while True:
        updates = requests.get(f"{URL}/getUpdates", params={"offset": offset, "timeout": 30}).json().get("result", [])
        for u in updates:
            offset = u["update_id"] + 1
            chat_id = u["message"]["chat"]["id"]
            text = u["message"].get("text", "")
            ans = requests.post("http://localhost:11435/v1/chat/completions", json={"messages": [{"content": text}]}).json()
            requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": ans["choices"][0]["message"]["content"]})
        time.sleep(1)
if __name__ == '__main__': main()
