# ⚡ Straddle

> A resilient local AI proxy that translates any OpenAI-compatible client into Ollama without touching a single line of client code. Automatic hardware failover, persistent prompt injection, and sub-second streaming — fully self-hosted.

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=flat-square)
![Speed](https://img.shields.io/badge/throughput-~30%20tok%2Fs-brightgreen?style=flat-square)

---

## 🎯 Core Engineering Pillars

- **OpenAI API translation** — drop-in replacement endpoint at `:11435`; no client-side changes required
- **Global prompt injection** — `system_prompt.md` + `master_context.md` prepended to every request automatically
- **Streaming mesh** — full SSE streaming with proper `[DONE]` termination; compatible with Hermes WebUI, Siri, and any OpenAI SDK
- **KV cache optimization** — `num_ctx: 8192` + `keep_alive: -1` keeps models hot in VRAM between requests
- **Telegram gateway** — optional bot bridge routes messages through the same proxy stack

---

## 🗺️ System Topology

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
              │             VRAM   │  Vulkan backend
              │  ~30 tok/s output  │  8GB @ 29/29 layers
              └────────────────────┘
```

---

## ⚡ Quick Start

**1. Clone and configure**
```bash
git clone https://github.com/your-username/straddle.git
cd straddle
cp .env.example .env
# Edit .env — set TELEGRAM_BOT_TOKEN if using the bot
```

**2. Provision environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Launch and verify**
```bash
python3 api_server.py
# Server live at http://localhost:11435
curl http://localhost:11435/v1/models
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/models` | List available models (OpenAI format) |
| `GET` | `/api/tags` | List available models (Ollama native format) |
| `POST` | `/v1/chat/completions` | Chat completions with system prompt injection |

Streaming supported via `"stream": true` — returns proper SSE chunks.

---

## 🤖 Telegram Gateway

Routes Telegram messages through the same proxy stack:

```bash
# Requires TELEGRAM_BOT_TOKEN in .env
python3 telegram_gateway.py
```

Or run via systemd:
```bash
systemctl --user enable --now straddle-bot.service
```

---

## 🛠️ Systemd Services

```bash
# API server (port 11435)
systemctl --user enable --now straddle-api.service

# Telegram bot
systemctl --user enable --now straddle-bot.service

# Status check
systemctl --user status straddle-api straddle-bot
```

---

## 📁 Prompt Files

| File | Purpose |
|------|---------|
| `prompts/system_prompt.md` | Base persona and format rules injected on every request |
| `prompts/master_context.md` | Personal context appended to system prompt (excluded from repo; create locally) |

---

## 📋 Requirements

- Python **3.10+**
- [Ollama](https://ollama.ai) running on `localhost:11434`
- GPU with Vulkan support recommended (**~30 tok/s** on RX 5700 XT via Vulkan backend)

---

## 📄 License

MIT
