# Straddle

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=flat-square)

An OpenAI-compatible inference gateway for self-hosted Ollama. Single endpoint for all clients, persistent system prompt injection, live data context (email, calendar), and API key authentication.

---

## Features

**Unified endpoint.** One address for every client — web UI, scripts, API calls. No per-client Ollama configuration.

**System prompt injection.** Edit `prompts/system_prompt.md` once. Every request receives it automatically.

**Live data context.** Incoming messages are pattern-matched and enriched with real data before reaching the model — inbox summaries, calendar events, reminders — without any tool-calling roundtrip.

**KV cache stability.** Requests forward to Ollama with a fixed `num_ctx` and `keep_alive: -1`. The model stays resident in VRAM; no cold-start reload between requests.

**API key auth.** All inference endpoints require `X-API-Key` header. Health check remains public.

---

## Architecture

```
  Clients (WebUI / scripts / API)
           │
           ▼
  ┌─────────────────────────┐
  │     Straddle :11435     │
  │                         │
  │  auth  →  X-API-Key     │
  │  inject → system prompt │
  │  enrich → email / cal   │
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │      Ollama :11434      │
  │   local inference       │
  └─────────────────────────┘
```

---

## Quick start

```bash
git clone https://github.com/equ1nox-git/straddle.git
cd straddle
cp .env.example .env        # fill in required values
pip install -r requirements.txt
python3 api_server.py
```

Test:
```bash
curl http://localhost:11435/                          # health (no key needed)

curl http://localhost:11435/v1/models \
  -H "X-API-Key: your-key"

curl http://localhost:11435/v1/chat/completions \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"hello"}]}'
```

---

## Configuration

All settings via `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama backend |
| `STRADDLE_HOST` | `127.0.0.1` | Bind address — use Tailscale IP to expose on mesh only |
| `STRADDLE_PORT` | `11435` | Listen port |
| `STRADDLE_API_KEY` | _(empty)_ | Required `X-API-Key` value; auth disabled if unset |
| `DEFAULT_MODEL` | _(empty)_ | Fallback model when client sends none |
| `NUM_CTX` | `8192` | Fixed context window — prevents KV buffer resize between requests |
| `KEEP_ALIVE` | `-1` | `-1` = keep model loaded forever, `0` = unload after each request |
| `PROMPTS_DIR` | `./prompts` | Directory for `system_prompt.md` and `master_context.md` |

---

## Prompt files

| File | Purpose |
|---|---|
| `prompts/system_prompt.md` | Base instructions injected on every request |
| `prompts/master_context.md` | Additional context appended after system prompt |

Both are optional and excluded from the repo — create locally.

---

## Live data injection

Straddle pattern-matches the last user message and prepends real data as a pre-resolved context block before forwarding to Ollama. No tool calls, no round-trips.

| Pattern | Data fetched |
|---|---|
| "list my emails", "last 5 emails" | Inbox via `himalaya` (iCloud / Gmail / Yahoo) |
| "send email to …" | Sends via SMTP, returns status |
| "what do I have this week", "upcoming events" | CalDAV events via iCloud |
| "reminders", "what's coming up" | Apple Reminders via CalDAV |

Credentials for email and calendar are read from `.env` — never hardcoded.

---

## API

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/` | — | Health check |
| `GET` | `/v1/models` | ✓ | List models (OpenAI format) |
| `GET` | `/api/tags` | ✓ | List models (Ollama native) |
| `POST` | `/v1/chat/completions` | ✓ | Chat with injection and streaming |

---

## Systemd (user service)

```bash
# enable and start
systemctl --user enable --now straddle.service

# status / logs
systemctl --user status straddle
journalctl --user -u straddle -f
```

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) running locally

---

## License

MIT
