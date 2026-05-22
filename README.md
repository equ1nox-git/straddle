# Straddle

A local proxy gateway that routes OpenAI-compatible API requests to a local Ollama backend. Built to maintain uptime for frontends and messaging bots when primary models hit context limits.

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=flat-square)
![Speed](https://img.shields.io/badge/throughput-~30%20tok%2Fs-brightgreen?style=flat-square)

---

## Features

- Translates OpenAI chat completions directly to local Ollama routes
- Dynamic per-request system prompt injection
- Full support for low-latency token streaming
- Telegram bot gateway included

---

## Architecture

```
Client (Hermes WebUI / Telegram Bot)
  -> Straddle Proxy (:11435)
  -> Ollama Backend (:11434)
  -> Vulkan Compute Layer
```

Accessible locally at `http://localhost:11435` or over Tailscale at `http://b450.tail59fa06.ts.net:11435`.

Hermes WebUI dashboard: `http://b450.tail59fa06.ts.net:3000`

---

## Setup

1. Configure environment:
   ```bash
   cp .env.example .env
   # Set TELEGRAM_BOT_TOKEN if using the bot
   ```

2. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   python3 api_server.py
   # Listening at http://localhost:11435
   ```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/v1/models` | List models (OpenAI format) |
| `GET` | `/api/tags` | List models (Ollama native) |
| `POST` | `/v1/chat/completions` | Chat with system prompt injection |

Streaming: pass `"stream": true` in the request body.

---

## Configuration

**Systemd services**
```bash
systemctl --user enable --now straddle-api.service    # proxy on :11435
systemctl --user enable --now straddle-bot.service    # Telegram bot
systemctl --user enable --now hermes-webui.service    # dashboard on :3000
```

**Prompt files**

| File | Purpose |
|------|---------|
| `prompts/system_prompt.md` | Base persona injected on every request |
| `prompts/master_context.md` | Personal context layer (excluded from repo; create locally) |

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) on `localhost:11434`
- Vulkan-compatible GPU recommended

---

## License

MIT
