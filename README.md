# Straddle

A local OpenAI-compatible proxy that routes any client directly to Ollama with persistent prompt injection and KV cache tuning. Designed for setups where multiple clients (web UIs, mobile shortcuts, bots) need a single, consistent inference endpoint without per-client configuration.

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=flat-square)
![Speed](https://img.shields.io/badge/throughput-~30%20tok%2Fs-brightgreen?style=flat-square)

---

## Why Straddle

Most local AI proxies either target cloud providers or require per-client prompt configuration. Straddle solves three specific problems that generic proxies don't:

**1. Direct Ollama routing with KV cache preservation**
Requests are forwarded to Ollama's native `/api/chat` endpoint with a fixed `num_ctx: 8192` and `keep_alive: -1`. The context window stays stable across requests (no buffer resize on model load), and the model stays resident in VRAM between calls — eliminating cold-start latency on every request.

**2. Global system prompt injection across all clients**
`system_prompt.md` and `master_context.md` are merged into a single stable system block on every request, regardless of which client is calling. Hermes WebUI, Siri shortcuts, and any OpenAI SDK client all receive the same injected context without any client-side configuration.

**3. OpenAI-compatible server endpoint**
Exposes a `/v1/chat/completions` endpoint that any OpenAI-compatible client can target. This is distinct from tools like `hermes proxy` which act as clients to cloud OAuth providers — Straddle acts as a server, making local Ollama models accessible to clients that only speak the OpenAI API schema.

---

## Architecture

```
Client (Hermes WebUI / Siri / any OpenAI SDK)
  → Straddle :11435  (prompt injection + KV cache config)
  → Ollama   :11434  (local inference)
  → Vulkan compute layer
```

Tailscale: `http://b450.tail59fa06.ts.net:11435`

---

## Setup

```bash
git clone https://github.com/equ1nox-git/straddle.git
cd straddle
cp .env.example .env
pip install -r requirements.txt
python3 api_server.py
```

Systemd:
```bash
systemctl --user enable --now straddle-api.service
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/v1/models` | List Ollama models (OpenAI format) |
| `GET` | `/api/tags` | List Ollama models (native format) |
| `POST` | `/v1/chat/completions` | Chat completions with prompt injection |

Streaming via `"stream": true`.

---

## Prompt Files

| File | Purpose |
|------|---------|
| `prompts/system_prompt.md` | Persona and format rules |
| `prompts/master_context.md` | Personal context layer (excluded from repo) |

---

## License

MIT
