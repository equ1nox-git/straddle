# ⚡ Straddle

> A lightweight local AI proxy that bridges any OpenAI-compatible client to Ollama, injecting system prompts and streaming completions without touching client code.

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=flat-square)
![Speed](https://img.shields.io/badge/throughput-~30%20tok%2Fs-brightgreen?style=flat-square)

---

## Overview

Straddle sits between your clients and Ollama. It translates OpenAI API calls, injects a persistent system prompt on every request, and handles streaming completions. No model switching required on the client side.

Accessible locally at `http://localhost:11435` or over Tailscale at `http://b450.tail59fa06.ts.net:11435`.

---

## Features

- **OpenAI-compatible API** at `:11435` — drop-in for any client that speaks OpenAI's schema
- **Persistent prompt injection** — `system_prompt.md` and `master_context.md` prepended to every request
- **Streaming completions** — full SSE with proper `[DONE]` termination, compatible with Hermes WebUI, Siri, and any OpenAI SDK
- **KV cache tuning** — `num_ctx: 8192` and `keep_alive: -1` keep models resident in VRAM between requests
- **Telegram gateway** — optional bot that routes messages through the same proxy

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                        │
│  Hermes WebUI │  Siri Shortcut  │  Telegram  │  curl   │
└──────────┬────────────┬──────────────┬─────────────────┘
           │            │              │
           └────────────▼──────────────┘
                        │
              ┌─────────▼──────────┐
              │   Straddle :11435  │  FastAPI proxy
              │  POST /v1/chat/    │  + prompt injection
              │  GET  /v1/models   │  + SSE streaming
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │   Ollama  :11434   │  Local inference
              │  Vulkan compute    │  GPU-accelerated
              │  ~30 tok/s output  │  29/29 layers
              └────────────────────┘
```

---

## Setup

**1. Clone and configure**
```bash
git clone https://github.com/equ1nox-git/straddle.git
cd straddle
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN if using the bot
```

**2. Install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Run**
```bash
python3 api_server.py
# Listening at http://localhost:11435
curl http://localhost:11435/v1/models
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/models` | List models (OpenAI format) |
| `GET` | `/api/tags` | List models (Ollama native) |
| `POST` | `/v1/chat/completions` | Chat with system prompt injection |

Streaming: pass `"stream": true` in the request body.

---

## Telegram Gateway

```bash
# Requires TELEGRAM_BOT_TOKEN in .env
python3 telegram_gateway.py
```

Or via systemd:
```bash
systemctl --user enable --now straddle-bot.service
```

---

## Configuration

**Systemd services**
```bash
systemctl --user enable --now straddle-api.service
systemctl --user enable --now straddle-bot.service
systemctl --user status straddle-api straddle-bot
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
- Vulkan-compatible GPU recommended for hardware-accelerated inference

---

## License

MIT
